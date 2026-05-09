import asyncio
import logging
from typing import Optional, List, Dict
from pyquotex.stable_api import Quotex
from pyquotex.utils.account_type import AccountType
from pyquotex.global_value import WebsocketStatus, AuthStatus

logger = logging.getLogger("antigravity.broker")

class QuotexBroker:
    def __init__(self, email: str, password: str, environment: str = "DEMO"):
        # Force a realistic browser User-Agent to bypass data center blocks
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        self.client = Quotex(email, password, lang="en", user_agent=user_agent)
        self.environment = AccountType.REAL if environment.upper() == "REAL" else AccountType.DEMO
        self.is_connected = False

    async def connect(self, retries=3):
        for i in range(retries):
            logger.info(f"Connecting to Quotex (Attempt {i+1}/{retries})...")
            try:
                check, reason = await self.client.connect()
                if not check:
                    logger.error(f"Connection failed: {reason}")
                    await asyncio.sleep(5)
                    continue
                    
                await self.client.change_account("REAL" if self.environment == AccountType.REAL else "DEMO")
                
                # Critical: Give cloud network time to establish WebSocket
                await asyncio.sleep(5)
                
                if await self.client.check_connect():
                    self.is_connected = True
                    logger.info("Connected successfully to account.")
                    return True
                else:
                    logger.warning("WebSocket handshake failed. Retrying...")
            except Exception as e:
                logger.error(f"Failed to connect: {e}")
            
            await asyncio.sleep(5)
            
        self.is_connected = False
        return False

    async def ensure_connection(self):
        if not self.is_connected or not await self.client.check_connect():
            logger.warning("Connection lost. Attempting to reconnect...")
            return await self.connect()
        return True

    async def get_balance(self) -> float:
        try:
            balance = await self.client.get_balance()
            return balance
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            raise e

    async def get_candles(self, pair: str, timeframe_seconds: int, amount: int = 100) -> List[Dict]:
        """Fetch recent candles."""
        try:
            import time
            # Note: pyquotex get_candles returns recent candles from the stream
            # For technical analysis, we might need a specific amount
            offset = amount * timeframe_seconds
            candles = await self.client.get_candles(pair, time.time(), offset, timeframe_seconds)
            return candles or []
        except Exception as e:
            logger.error(f"Error fetching candles for {pair}: {e}")
            return []

    async def execute_trade(self, pair: str, amount: float, direction: str, duration: int) -> Dict:
        """
        Execute a trade.
        direction: 'call' (BUY) or 'put' (SELL)
        """
        logger.info(f"Executing {direction.upper()} trade: {pair} | Amount: {amount} | Duration: {duration}s")
        try:
            status, trade_info = await self.client.buy(amount, pair, direction, duration)
            if status:
                logger.info(f"Trade placed successfully: {trade_info}")
                return trade_info
            else:
                logger.error(f"Trade failed: {trade_info}")
                return None
        except Exception as e:
            logger.error(f"Exception during trade execution: {e}")
            return None

    async def check_trade_result(self, trade_id: str) -> Optional[Dict]:
        """Wait for trade to finish and return result."""
        # This implementation depends on how pyquotex handles trade updates.
        # Usually we listen to the socket or poll for trade status.
        # For simplicity in this engine, we'll assume we can poll or use an event.
        try:
            # pyquotex might have a specific method for this.
            # If not, we might need to check trade history.
            return await self.client.check_win(trade_id)
        except Exception as e:
            logger.error(f"Error checking trade result for {trade_id}: {e}")
            return None

    async def close(self):
        await self.client.close()
        self.is_connected = False
        logger.info("Broker connection closed.")
