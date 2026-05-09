import asyncio
import time
import logging
from datetime import datetime

logger = logging.getLogger("antigravity.wick_strategy")

class WickStrategy:
    @staticmethod
    async def wait_for_new_candle(broker, pair: str):
        """Wait until a new 1-minute candle starts (seconds == 00) and return previous candle stats"""
        # Wait until the next minute boundary
        now = datetime.now()
        sleep_time = 60 - now.second
        if sleep_time < 60:
            await asyncio.sleep(sleep_time)
            
        # Add a small buffer to ensure broker has registered the new candle
        await asyncio.sleep(1)
        
        # Fetch the closed candle (the one that just finished)
        candles = await broker.get_candles(pair, timeframe_seconds=60, amount=100)
        if not candles or len(candles) < 2:
            return None
            
        prev_candle = candles[-2] # The completely formed one
        return prev_candle

    @staticmethod
    async def monitor_wick_breakout(broker, pair: str, prev_candle: dict):
        """Monitor real-time price for 45s to see if it breaks the previous wicks"""
        upper_wick = prev_candle['high']
        lower_wick = prev_candle['low']
        
        start_time = time.time()
        timeout = 45 # 45 seconds limit
        
        while (time.time() - start_time) < timeout:
            # Get current price (can be achieved by fetching 1 tick or 1s candle)
            # We'll use get_candles(amount=100) and grab the last one
            candles = await broker.get_candles(pair, timeframe_seconds=60, amount=100)
            if candles:
                current_price = candles[-1]['close']
                
                if current_price > upper_wick:
                    return "put", current_price
                elif current_price < lower_wick:
                    return "call", current_price
            
            await asyncio.sleep(0.5) # Poll twice a second
            
        return None, None

    @staticmethod
    async def execute_5sec_trade(broker, pair: str, direction: str, amount: float):
        """Execute a 5-second trade"""
        # Note: Quotex minimum expiry is usually 5 seconds
        trade_info = await broker.execute_trade(pair, amount, direction, duration=5)
        return trade_info
