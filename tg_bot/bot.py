import logging
from typing import Callable, Optional
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
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
/help - Show this message
"""
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def _status_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.engine: return
        stats = self.engine.get_stats()
        status_msg = f"""
📊 *Dashboard*
━━━━━━━━━━━━━━
✅ *Status:* {"RUNNING" if not self.engine.is_paused else "PAUSED"}
📈 *Pair:* {stats['pair']}
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
        balance = await self.engine.broker.get_balance()
        await update.message.reply_text(f"💰 Current Balance: *${balance:.2f}*", parse_mode=ParseMode.MARKDOWN)

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
PAIR: {cfg.pair}
TIMEFRAME: {cfg.timeframe}
AMOUNT: {cfg.trade_amount}
EMA: {cfg.ema_fast}/{cfg.ema_slow}
RSI: {cfg.rsi_period} ({cfg.rsi_buy_below}/{cfg.rsi_sell_above})
MARTINGALE: {cfg.martingale}
━━━━━━━━━━━━━━
"""
        await update.message.reply_text(strat_msg, parse_mode=ParseMode.MARKDOWN)
