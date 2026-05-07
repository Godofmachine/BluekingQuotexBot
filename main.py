import asyncio
import logging
import os
import signal
from dotenv import load_dotenv
from core.broker import QuotexBroker
from core.trading_engine import TradingEngine
from tg_bot.bot import TelegramNotifier

# Setup Logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("antigravity.main")

async def main():
    load_dotenv()
    
    email = os.getenv("QUOTEX_EMAIL")
    password = os.getenv("QUOTEX_PASSWORD")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    env = os.getenv("ENVIRONMENT", "DEMO")
    
    if not all([email, password, token, chat_id]):
        logger.error("Missing environment variables. Check your .env file.")
        return

    # Initialize components
    broker = QuotexBroker(email, password, environment=env)
    telegram = TelegramNotifier(token, chat_id)
    
    # Storage and Strategy paths
    strategy_path = "strategy.txt"
    storage_path = "storage/trades.json"
    os.makedirs("storage", exist_ok=True)

    engine = TradingEngine(broker, telegram, strategy_path, storage_path)

    # Start Broker
    if not await broker.connect():
        logger.error("Initial connection failed. Exiting.")
        return

    # Start Telegram
    try:
        await telegram.start(engine)
    except Exception as e:
        logger.error(f"Telegram failed to start, but continuing trading: {e}")

    # Run Engine
    try:
        await engine.run()
    except asyncio.CancelledError:
        logger.info("Main task cancelled.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        logger.info("Cleaning up...")
        await telegram.stop()
        await broker.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
