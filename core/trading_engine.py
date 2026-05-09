import asyncio
import logging
import json
import os
import time
import re
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from core.broker import QuotexBroker
from core.strategy_parser import StrategyParser, StrategyConfig
from core.risk_manager import RiskManager
from indicators.engine import IndicatorEngine
from tg_bot.bot import TelegramNotifier

logger = logging.getLogger("antigravity.engine")

class TradingEngine:
    def __init__(self, broker: QuotexBroker, telegram: TelegramNotifier, strategy_path: str, storage_path: str):
        self.broker = broker
        self.telegram = telegram
        self.strategy_path = strategy_path
        self.storage_path = storage_path
        
        self.config: Optional[StrategyConfig] = None
        self.risk_manager: Optional[RiskManager] = None
        self.is_running = False
        self.is_paused = False
        self.start_time = datetime.now()
        
        self.history = self._load_history()
        self.last_trade_time = 0
        self.last_strategy_mtime = 0

    def _load_history(self) -> List[Dict]:
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r") as f:
                try:
                    return json.load(f)
                except:
                    return []
        return []

    def _save_history(self):
        with open(self.storage_path, "w") as f:
            json.dump(self.history, f, indent=4)

    async def reload_strategy(self):
        mtime = os.path.getmtime(self.strategy_path)
        if mtime > self.last_strategy_mtime:
            logger.info("Strategy file updated. Reloading...")
            try:
                new_config = StrategyParser.parse_file(self.strategy_path)
                if not self.config or new_config != self.config:
                    self.config = new_config
                    if not self.risk_manager:
                        self.risk_manager = RiskManager(
                            max_consecutive_losses=self.config.max_consecutive_losses,
                            stop_loss=self.config.stop_loss,
                            take_profit=self.config.take_profit
                        )
                    self.last_strategy_mtime = mtime
                    logger.info(f"Strategy reloaded: {self.config.pair}")
                    await self.telegram.send_notification(f"🔄 *Strategy Updated*\nPair: {self.config.pair}")
            except Exception as e:
                logger.error(f"Error reloading strategy: {e}")

    async def get_stats(self) -> Dict:
        uptime = str(datetime.now() - self.start_time).split('.')[0]
        wins = sum(1 for t in self.history if t.get('result') == 'win')
        losses = sum(1 for t in self.history if t.get('result') == 'loss')
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        profit = sum(t.get('profit', 0) for t in self.history)
        
        balance = 0.0
        try:
            balance = await self.broker.get_balance()
        except:
            pass
            
        return {
            "uptime": uptime,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "profit": profit,
            "pair": self.config.pair if self.config else "N/A",
            "consecutive_losses": self.risk_manager.consecutive_losses if self.risk_manager else 0,
            "balance": balance
        }

    async def run(self):
        self.is_running = True
        logger.info("Trading engine started.")
        
        while self.is_running:
            try:
                await self.reload_strategy()
                
                # Initial balance for risk manager
                current_balance = await self.broker.get_balance()
                self.risk_manager.set_starting_balance(current_balance)
                
                # Check daily limits
                can_trade, reason = self.risk_manager.can_trade(current_balance)
                if not can_trade:
                    if not self.is_paused:
                        logger.warning(f"Engine PAUSED: {reason}")
                        await self.telegram.send_notification(f"⚠️ *Trading Paused*\nReason: {reason}")
                        self.is_paused = True
                    await asyncio.sleep(60)
                    continue
                else:
                    self.is_paused = False

                if not await self.broker.ensure_connection():
                    await asyncio.sleep(5)
                    continue

                # Fetch candles
                pair = self.config.pair
                timeframe_sec = self._parse_timeframe(self.config.timeframe)
                candles = await self.broker.get_candles(pair, timeframe_sec, amount=100)
                
                if not candles:
                    await asyncio.sleep(self.config.polling_interval)
                    continue

                # Indicators & Patterns
                df = IndicatorEngine.calculate_indicators(
                    candles, 
                    self.config.ema_fast, 
                    self.config.ema_slow, 
                    self.config.rsi_period
                )
                
                if df.empty or len(df) < 30:
                    await asyncio.sleep(1)
                    continue

                # Signal Logic
                direction, grade, expiry_min = self._evaluate_signal(df)
                
                if direction != "SKIP" and (time.time() - self.last_trade_time > self.config.cooldown_seconds):
                    stake = self.risk_manager.calculate_stake(current_balance, grade)
                    await self._execute_signal(direction, stake, expiry_min * 60, grade)

                await asyncio.sleep(self.config.polling_interval)
                
            except Exception as e:
                logger.error(f"Error in engine loop: {e}")
                await asyncio.sleep(5)

    def _parse_timeframe(self, tf: str) -> int:
        if tf.endswith('m'): return int(tf[:-1]) * 60
        if tf.endswith('h'): return int(tf[:-1]) * 3600
        if tf.endswith('s'): return int(tf[:-1])
        return 60

    def _evaluate_signal(self, df: pd.DataFrame) -> Tuple[str, Optional[str], Optional[int]]:
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # S/R
        support, resistance, touch_s, touch_r = IndicatorEngine.find_support_resistance(df)
        
        rsi = last[f'RSI_{self.config.rsi_period}']
        ema = last[f'EMA_{self.config.ema_slow}']
        
        # Patterns
        bear_engulf = last['bearish_engulfing']
        bull_engulf = last['bullish_engulfing']
        tweezer_top = last['tweezer_top']
        tweezer_bottom = last['tweezer_bottom']
        piercing = last['piercing_pattern']
        dark_cloud = last['dark_cloud_cover']
        
        # Grade A (1-min)
        if (bear_engulf or tweezer_top or dark_cloud) and rsi > 60:
            return "put", "A", 1
        if (bull_engulf or tweezer_bottom or piercing) and rsi < 40:
            return "call", "A", 1
            
        # Grade B (2-min) - Rejection at S/R
        if touch_r >= 2 and last['high'] >= resistance and last['close'] < last['open']:
            return "put", "B", 2
        if touch_s >= 2 and last['low'] <= support and last['close'] > last['open']:
            return "call", "B", 2
            
        # Grade C (5-min) - Trend following with RSI
        if rsi < 30 and last['close'] > ema:
            return "call", "C", 5
        if rsi > 70 and last['close'] < ema:
            return "put", "C", 5
            
        return "SKIP", None, None

    async def _execute_signal(self, direction: str, amount: float, duration: int, grade: str):
        pair = self.config.pair
        
        await self.telegram.send_notification(
            f"🔔 *SIGNAL DETECTED ({grade})*\n"
            f"Direction: {direction.upper()}\n"
            f"Pair: {pair}\n"
            f"Amount: ${amount}\n"
            f"Expiry: {duration//60} min"
        )
        
        trade_info = await self.broker.execute_trade(pair, amount, direction, duration)
        if trade_info:
            self.last_trade_time = time.time()
            trade_id = trade_info.get('id')
            await self.telegram.send_notification(f"🎯 *Trade Executed*\nID: `{trade_id}`")
            asyncio.create_task(self._monitor_trade(trade_id, amount, direction, duration))

    async def _monitor_trade(self, trade_id: str, amount: float, direction: str, duration: int):
        await asyncio.sleep(duration + 2)
        result = await self.broker.check_trade_result(trade_id)
        if result:
            profit = result.get('profit', 0)
            res_str = 'win' if profit > 0 else 'loss'
            self.risk_manager.process_result(res_str, profit)
            
            trade_data = {
                "id": trade_id,
                "timestamp": int(time.time()),
                "pair": self.config.pair,
                "direction": direction,
                "amount": amount,
                "profit": profit,
                "result": res_str
            }
            self.history.append(trade_data)
            self._save_history()
            
            emoji = "💰" if res_str == 'win' else "📉"
            await self.telegram.send_notification(
                f"{emoji} *Trade Result ({res_str.upper()})*\n"
                f"Profit: ${profit:.2f}\n"
                f"Total Session: ${self.risk_manager.total_profit:.2f}"
            )
