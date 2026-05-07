import pandas as pd
import pandas_ta as ta
from typing import List, Dict, Optional

class IndicatorEngine:
    @staticmethod
    def calculate_indicators(candles: List[Dict], ema_fast: int, ema_slow: int, rsi_period: int) -> pd.DataFrame:
        if not candles:
            return pd.DataFrame()
            
        df = pd.DataFrame(candles)
        # Ensure correct column names for pandas_ta (usually open, high, low, close, volume)
        # pyquotex usually returns 'at', 'open', 'close', 'high', 'low'
        df.rename(columns={'at': 'timestamp'}, inplace=True)
        
        # Calculate EMA
        df[f'EMA_{ema_fast}'] = ta.ema(df['close'], length=ema_fast)
        df[f'EMA_{ema_slow}'] = ta.ema(df['close'], length=ema_slow)
        
        # Calculate RSI
        df[f'RSI_{rsi_period}'] = ta.rsi(df['close'], length=rsi_period)
        
        return df

    @staticmethod
    def check_crossover(df: pd.DataFrame, fast_col: str, slow_col: str) -> Optional[str]:
        """Returns 'up' if fast crosses above slow, 'down' if fast crosses below slow."""
        if len(df) < 2:
            return None
            
        prev_fast = df[fast_col].iloc[-2]
        prev_slow = df[slow_col].iloc[-2]
        curr_fast = df[fast_col].iloc[-1]
        curr_slow = df[slow_col].iloc[-1]
        
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            return "up"
        if prev_fast >= prev_slow and curr_fast < curr_slow:
            return "down"
            
        return None
