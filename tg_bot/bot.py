import logging
from typing import Callable, Optional
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

logger = logging.getLogger("antigravity.telegram")

class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.application = None
        self.engine = None  # Will be set later to access engine stats

    async def start(self, engine):
        self.engine = engine
        self.application = ApplicationBuilder().token(self.token).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self._start_cmd))
        self.application.add_handler(CommandHandler("status", self._status_cmd))
        self.application.add_handler(CommandHandler("balance", self._balance_cmd))
        self.application.add_handler(CommandHandler("wins", self._wins_cmd))
        self.application.add_handler(CommandHandler("losses", self._losses_cmd))
        self.application.add_handler(CommandHandler("profit", self._profit_cmd))
        self.application.add_handler(CommandHandler("pause", self._pause_cmd))
        self.application.add_handler(CommandHandler("resume", self._resume_cmd))
        self.application.add_handler(CommandHandler("strategy", self._strategy_cmd))
        self.application.add_handler(CommandHandler("help", self._help_cmd))
        self.application.add_handler(CommandHandler("pairs", self._pairs_cmd))
        self.application.add_handler(CommandHandler("current", self._current_cmd))
        self.application.add_handler(CommandHandler("stats", self._stats_cmd))
        self.application.add_handler(CommandHandler("force", self._force_cmd))
        self.application.add_handler(CommandHandler("mode", self._mode_cmd))
        
        self.application.add_handler(CallbackQueryHandler(self._pair_selection_handler, pattern="^pair_"))
        self.application.add_handler(CallbackQueryHandler(self._mode_selection_handler, pattern="^mode_"))
        self.application.add_handler(CallbackQueryHandler(self._force_strategy_handler, pattern="^force_"))
        
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("Telegram bot started.")
        await self.send_notification("🚀 *Antigravity Bot Started*")

    async def stop(self):
        if self.application:
            await self.send_notification("🛑 *Antigravity Bot Shutting Down*")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

    async def send_notification(self, message: str):
        if not self.application:
            return
        try:
            await self.application.bot.send_message(
                chat_id=self.chat_id, 
                text=message, 
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

    # Command Handlers
    async def _start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Welcome to Antigravity Trading Bot! Use /help for commands.")

    async def _help_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
*Available Commands:*
/status - Show current bot status
/balance - Show account balance
/wins - Show total wins
/losses - Show total losses
/profit - Show total profit/loss
/pause - Pause trading
/resume - Resume trading
/strategy - Show current strategy
/pairs - Show all available pairs as buttons
/current - Show current selected pair
/force - Execute one wick-strategy trade immediately
/stats - Show win/loss stats for force trades only
/mode - Switch between DEMO and REAL accounts
/help - Show this message
"""
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def _status_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.engine: return
        stats = await self.engine.get_stats()
        status_msg = f"""
📊 *Dashboard*
━━━━━━━━━━━━━━
✅ *Status:* {"RUNNING" if not self.engine.is_paused else "PAUSED"}
📈 *Pair:* {stats['pair'].replace('_', '\\_')}
⏱️ *Uptime:* {stats['uptime']}
💰 *Balance:* ${stats['balance']:.2f}
💵 *Profit:* ${stats['profit']:.2f}
🏆 *Wins:* {stats['wins']}
❌ *Losses:* {stats['losses']}
📉 *Win Rate:* {stats['win_rate']:.1f}%
🔥 *Consec. Losses:* {stats['consecutive_losses']}
━━━━━━━━━━━━━━
"""
        await update.message.reply_text(status_msg, parse_mode=ParseMode.MARKDOWN)

    async def _balance_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            balance = await self.engine.broker.get_balance()
            await update.message.reply_text(f"💰 Current Balance: *${balance:.2f}*", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await update.message.reply_text(f"⚠️ *Error fetching balance:* `{str(e)}`", parse_mode=ParseMode.MARKDOWN)

    async def _wins_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        stats = self.engine.get_stats()
        await update.message.reply_text(f"🏆 Total Wins: *{stats['wins']}*", parse_mode=ParseMode.MARKDOWN)

    async def _losses_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        stats = self.engine.get_stats()
        await update.message.reply_text(f"❌ Total Losses: *{stats['losses']}*", parse_mode=ParseMode.MARKDOWN)

    async def _profit_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        stats = self.engine.get_stats()
        emoji = "📈" if stats['profit'] >= 0 else "📉"
        await update.message.reply_text(f"{emoji} Total Profit: *${stats['profit']:.2f}*", parse_mode=ParseMode.MARKDOWN)

    async def _pause_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.engine.is_paused = True
        await update.message.reply_text("⏸️ Trading paused.")

    async def _resume_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.engine.is_paused = False
        await update.message.reply_text("▶️ Trading resumed.")

    async def _strategy_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cfg = self.engine.config
        strat_msg = f"""
📜 *Current Strategy*
━━━━━━━━━━━━━━
PAIR: {cfg.pair.replace('_', '\\_')}
TIMEFRAME: {cfg.timeframe}
AMOUNT: {cfg.trade_amount}
EMA: {cfg.ema_fast}/{cfg.ema_slow}
RSI: {cfg.rsi_period} ({cfg.rsi_buy_below}/{cfg.rsi_sell_above})
MARTINGALE: {cfg.martingale}
━━━━━━━━━━━━━━
"""
        await update.message.reply_text(strat_msg, parse_mode=ParseMode.MARKDOWN)

    async def _pairs_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pairs = [
            "EURUSD_otc", "GBPUSD_otc", "USDJPY_otc",
            "AUDUSD_otc", "USDCAD_otc", "EURJPY_otc",
            "GBPJPY_otc", "XAUUSD_otc", "BTCUSD_otc"
        ]
        keyboard = []
        for i in range(0, len(pairs), 3):
            row = [InlineKeyboardButton(pair, callback_data=f"pair_{pair}") for pair in pairs[i:i+3]]
            keyboard.append(row)
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Please select a trading pair:", reply_markup=reply_markup)

    async def _pair_selection_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        pair = query.data.replace("pair_", "")
        
        if self.engine:
            self.engine.set_current_pair(pair)
            
        safe_pair = pair.replace("_", "\\_")
        await query.edit_message_text(f"✅ Trading pair changed to {safe_pair}", parse_mode=ParseMode.MARKDOWN)

    async def _current_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.engine: return
        pair = self.engine.get_current_pair()
        safe_pair = pair.replace("_", "\\_")
        await update.message.reply_text(f"🎯 Current selected pair: {safe_pair}", parse_mode=ParseMode.MARKDOWN)

    async def _stats_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.engine: return
        import os
        log_file = "storage/force_trades.log"
        if not os.path.exists(log_file):
            await update.message.reply_text("No force trades recorded yet.")
            return
            
        wins = 0
        losses = 0
        profit = 0.0
        
        with open(log_file, "r") as f:
            for line in f:
                if "WIN" in line: wins += 1
                elif "LOSS" in line: losses += 1
                
                parts = line.split(",")
                for p in parts:
                    if "Profit: " in p:
                        try:
                            val = p.split("Profit: ")[1].strip()
                            profit += float(val.replace("+", "").replace("$", ""))
                        except: pass
                        
        total = wins + losses
        win_rate = (wins/total*100) if total > 0 else 0
        
        stats_msg = f"""
⚡ *Force Trades Stats*
━━━━━━━━━━━━━━
🏆 Wins: {wins}
❌ Losses: {losses}
📉 Win Rate: {win_rate:.1f}%
💰 Total Profit: ${profit:.2f}
━━━━━━━━━━━━━━
"""
        await update.message.reply_text(stats_msg, parse_mode=ParseMode.MARKDOWN)

    async def _force_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.engine: return
        keyboard = [
            [InlineKeyboardButton("🤖 AUTO (AI Select)", callback_data="force_auto")],
            [InlineKeyboardButton("🕯️ Wick Breakout", callback_data="force_wick")],
            [InlineKeyboardButton("📈 Trend Rider", callback_data="force_trend")],
            [InlineKeyboardButton("🌊 RSI Extreme", callback_data="force_rsi")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select Force Trade Strategy:", reply_markup=reply_markup)

    async def _force_strategy_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        strategy = query.data.replace("force_", "")
        
        import asyncio
        asyncio.create_task(self.engine.execute_force_trade(strategy))
        await query.edit_message_text(f"🚀 Launching Force Trade: `{strategy.upper()}`")

    async def _mode_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("💎 DEMO", callback_data="mode_demo"),
             InlineKeyboardButton("💰 REAL", callback_data="mode_real")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select Account Mode:", reply_markup=reply_markup)

    async def _mode_selection_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        mode = query.data.replace("mode_", "").upper()
        
        if self.engine:
            success = await self.engine.switch_mode(mode)
            if success:
                await query.edit_message_text(f"✅ Account mode switched to: `{mode}`")
            else:
                await query.edit_message_text("❌ Failed to switch account mode.")

