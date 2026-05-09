import pandas as pd
from typing import List, Dict, Optional, Tuple

class IndicatorEngine:
    @staticmethod
    def calculate_indicators(candles: List[Dict], ema_fast: int, ema_slow: int, rsi_period: int) -> pd.DataFrame:
        if not candles:
            return pd.DataFrame()
            
        df = pd.DataFrame(candles)
        df.rename(columns={'at': 'timestamp'}, inplace=True)
        
        # Core Indicators (Calculated manually with pandas to avoid pandas_ta/numba)
        df[f'EMA_{ema_fast}'] = df['close'].ewm(span=ema_fast, adjust=False).mean()
        df[f'EMA_{ema_slow}'] = df['close'].ewm(span=ema_slow, adjust=False).mean()
        
        # Standard RSI formula
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        df[f'RSI_{rsi_period}'] = 100 - (100 / (1 + rs))
        
        # Patterns
        df['bullish_engulfing'] = (df['close'].shift(1) < df['open'].shift(1)) & \
                                  (df['close'] > df['open']) & \
                                  (df['open'] < df['close'].shift(1)) & \
                                  (df['close'] > df['open'].shift(1))
                                  
        df['bearish_engulfing'] = (df['close'].shift(1) > df['open'].shift(1)) & \
                                  (df['close'] < df['open']) & \
                                  (df['open'] > df['close'].shift(1)) & \
                                  (df['close'] < df['open'].shift(1))

        df['tweezer_bottom'] = (abs(df['low'].shift(1) - df['low']) < 0.0005) & \
                               (df['close'].shift(1) < df['open'].shift(1)) & \
                               (df['close'] > df['open'])

        df['tweezer_top'] = (abs(df['high'].shift(1) - df['high']) < 0.0005) & \
                            (df['close'].shift(1) > df['open'].shift(1)) & \
                            (df['close'] < df['open'])
                            
        midpoint_prev = (df['open'].shift(1) + df['close'].shift(1)) / 2
        df['piercing_pattern'] = (df['close'].shift(1) < df['open'].shift(1)) & \
                                 (df['close'] > df['open']) & \
                                 (df['open'] < df['close'].shift(1)) & \
                                 (df['close'] > midpoint_prev)
                                 
        df['dark_cloud_cover'] = (df['close'].shift(1) > df['open'].shift(1)) & \
                                 (df['close'] < df['open']) & \
                                 (df['open'] > df['close'].shift(1)) & \
                                 (df['close'] < midpoint_prev)
        
        return df

    @staticmethod
    def find_support_resistance(df: pd.DataFrame, lookback: int = 20) -> Tuple[float, float, int, int]:
        if len(df) < lookback:
            return 0.0, 0.0, 0, 0
            
        recent = df.tail(lookback)
        resistance = recent['high'].max()
        support = recent['low'].min()
        
        touch_r = sum(1 for h in recent['high'] if abs(h - resistance) < 0.0005)
        touch_s = sum(1 for l in recent['low'] if abs(l - support) < 0.0005)
        
        return support, resistance, touch_s, touch_r

    @staticmethod
    def check_crossover(df: pd.DataFrame, fast_col: str, slow_col: str) -> Optional[str]:
        if len(df) < 2:
            return None
        prev_fast, prev_slow = df[fast_col].iloc[-2], df[slow_col].iloc[-2]
        curr_fast, curr_slow = df[fast_col].iloc[-1], df[slow_col].iloc[-1]
        if prev_fast <= prev_slow and curr_fast > curr_slow: return "up"
        if prev_fast >= prev_slow and curr_fast < curr_slow: return "down"
        return None
