import asyncio
import logging
import json
import os
import time
import re
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
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
                    # Update risk manager if config changed
                    if not self.risk_manager:
                        self.risk_manager = RiskManager(
                            initial_amount=self.config.trade_amount,
                            martingale_enabled=self.config.martingale,
                            max_consecutive_losses=self.config.max_consecutive_losses,
                            stop_loss=self.config.stop_loss,
                            take_profit=self.config.take_profit
                        )
                    else:
                        self.risk_manager.initial_amount = self.config.trade_amount
                        self.risk_manager.martingale_enabled = self.config.martingale
                        self.risk_manager.max_consecutive_losses = self.config.max_consecutive_losses
                    
                    self.last_strategy_mtime = mtime
                    logger.info(f"Strategy reloaded: {self.config.pair}")
                    await self.telegram.send_notification(f"🔄 *Strategy Updated*\nPair: {self.config.pair}\nAmount: {self.config.trade_amount}")
            except Exception as e:
                logger.error(f"Error reloading strategy: {e}")

    def get_stats(self) -> Dict:
        uptime = str(datetime.now() - self.start_time).split('.')[0]
        wins = sum(1 for t in self.history if t.get('result') == 'win')
        losses = sum(1 for t in self.history if t.get('result') == 'loss')
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        profit = sum(t.get('profit', 0) for t in self.history)
        
        return {
            "uptime": uptime,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "profit": profit,
            "pair": self.config.pair if self.config else "N/A",
            "consecutive_losses": self.risk_manager.consecutive_losses if self.risk_manager else 0,
            "balance": 0.0 # Will be updated in loop
        }

    async def run(self):
        self.is_running = True
        logger.info("Trading engine started.")
        
        while self.is_running:
            try:
                await self.reload_strategy()
                
                if self.is_paused or (self.risk_manager and self.risk_manager.is_paused):
                    if self.risk_manager and self.risk_manager.is_paused:
                        logger.warning(f"Engine PAUSED by Risk Manager: {self.risk_manager.pause_reason}")
                        await self.telegram.send_notification(f"⚠️ *Risk Manager PAUSE*\nReason: {self.risk_manager.pause_reason}")
                        # Auto-reset after some time or wait for command? 
                        # For now, let's wait 5 mins or until manual resume
                        await asyncio.sleep(300) 
                    else:
                        await asyncio.sleep(1)
                    continue

                if not await self.broker.ensure_connection():
                    await asyncio.sleep(5)
                    continue

                # Get data
                pair = self.config.pair
                timeframe_sec = self._parse_timeframe(self.config.timeframe)
                
                candles = await self.broker.get_candles(pair, timeframe_sec)
                if not candles:
                    await asyncio.sleep(self.config.polling_interval)
                    continue

                # Calculate indicators
                df = IndicatorEngine.calculate_indicators(
                    candles, 
                    self.config.ema_fast, 
                    self.config.ema_slow, 
                    self.config.rsi_period
                )
                
                if df.empty:
                    await asyncio.sleep(1)
                    continue

                # Check for signal
                signal = self._evaluate_signal(df)
                
                if signal and (time.time() - self.last_trade_time > self.config.cooldown_seconds):
                    await self._execute_signal(signal)

                await asyncio.sleep(self.config.polling_interval)
                
            except Exception as e:
                logger.error(f"Error in engine loop: {e}")
                await asyncio.sleep(5)

    def _parse_timeframe(self, tf: str) -> int:
        if tf.endswith('m'): return int(tf[:-1]) * 60
        if tf.endswith('h'): return int(tf[:-1]) * 3600
        if tf.endswith('s'): return int(tf[:-1])
        return 60

    def _evaluate_signal(self, df: pd.DataFrame) -> Optional[str]:
        if not self.config.entry_rule:
            return self._fallback_signal(df)
            
        rule = self.config.entry_rule.lower()
        
        # Simple dynamic evaluation for EMA and RSI
        # Example: BUY when EMA_FAST crosses above EMA_SLOW and RSI < 30
        
        fast_ema = df[f'EMA_{self.config.ema_fast}'].iloc[-1]
        slow_ema = df[f'EMA_{self.config.ema_slow}'].iloc[-1]
        rsi = df[f'RSI_{self.config.rsi_period}'].iloc[-1]
        
        crossover = IndicatorEngine.check_crossover(df, f'EMA_{self.config.ema_fast}', f'EMA_{self.config.ema_slow}')
        
        is_buy = "buy" in rule
        is_sell = "sell" in rule
        
        # Check conditions in rule string
        conditions_met = True
        
        if "crosses above" in rule and crossover != "up":
            conditions_met = False
        if "crosses below" in rule and crossover != "down":
            conditions_met = False
        if "rsi <" in rule:
            limit = float(re.search(r"rsi < (\d+)", rule).group(1))
            if rsi >= limit: conditions_met = False
        if "rsi >" in rule:
            limit = float(re.search(r"rsi > (\d+)", rule).group(1))
            if rsi <= limit: conditions_met = False
            
        if conditions_met:
            return "call" if is_buy else "put"
            
        return None

    def _fallback_signal(self, df: pd.DataFrame) -> Optional[str]:
        # EMA Crossover fallback
        crossover = IndicatorEngine.check_crossover(df, f'EMA_{self.config.ema_fast}', f'EMA_{self.config.ema_slow}')
        last_rsi = df[f'RSI_{self.config.rsi_period}'].iloc[-1]
        
        if crossover == "up" and last_rsi < self.config.rsi_buy_below:
            return "call"
        if crossover == "down" and last_rsi > self.config.rsi_sell_above:
            return "put"
        return None

    async def _execute_signal(self, direction: str):
        amount = self.risk_manager.get_next_amount()
        pair = self.config.pair
        duration = self.config.trade_duration
        
        await self.telegram.send_notification(f"🔔 *SIGNAL DETECTED*\nDirection: {direction.upper()}\nPair: {pair}\nAmount: ${amount}")
        
        trade_info = await self.broker.execute_trade(pair, amount, direction, duration)
        if trade_info:
            self.last_trade_time = time.time()
            # Wait for result
            trade_id = trade_info.get('id')
            await self.telegram.send_notification(f"🎯 *Trade Executed*\nID: `{trade_id}`")
            
            # Start a task to wait for result without blocking the main loop
            asyncio.create_task(self._monitor_trade(trade_id, amount, direction))

    async def _monitor_trade(self, trade_id: str, amount: float, direction: str):
        # Wait for trade duration + a bit of buffer
        await asyncio.sleep(self.config.trade_duration + 2)
        
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
                f"{emoji} *Trade Result*\n"
                f"Result: {res_str.upper()}\n"
                f"Profit: ${profit:.2f}\n"
                f"Total Profit: ${self.risk_manager.total_profit:.2f}"
            )
        else:
            logger.error(f"Could not verify result for trade {trade_id}")
