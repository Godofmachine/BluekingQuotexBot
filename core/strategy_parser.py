import os
import re
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class StrategyConfig(BaseModel):
    ema_fast: int = Field(default=9, alias="EMA_FAST")
    ema_slow: int = Field(default=21, alias="EMA_SLOW")
    rsi_period: int = Field(default=14, alias="RSI_PERIOD")
    rsi_buy_below: int = Field(default=30, alias="RSI_BUY_BELOW")
    rsi_sell_above: int = Field(default=70, alias="RSI_SELL_ABOVE")
    timeframe: str = Field(default="1m", alias="TIMEFRAME")
    trade_duration: int = Field(default=60, alias="TRADE_DURATION")
    pair: str = Field(default="EURUSD", alias="PAIR")
    entry_rule: str = Field(default="", alias="ENTRY_RULE")
    exit_rule: str = Field(default="", alias="EXIT_RULE")
    martingale: bool = Field(default=False, alias="MARTINGALE")
    max_consecutive_losses: int = Field(default=3, alias="MAX_CONSECUTIVE_LOSSES")
    stop_loss: float = Field(default=20.0, alias="STOP_LOSS")
    take_profit: float = Field(default=50.0, alias="TAKE_PROFIT")
    trade_amount: float = Field(default=5.0, alias="TRADE_AMOUNT")
    cooldown_seconds: int = Field(default=30, alias="COOLDOWN_SECONDS")
    polling_interval: int = Field(default=1, alias="POLLING_INTERVAL")

class StrategyParser:
    @staticmethod
    def parse_file(file_path: str) -> StrategyConfig:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Strategy file not found at {file_path}")
        
        with open(file_path, "r") as f:
            content = f.read()
            
        return StrategyParser.parse_content(content)

    @staticmethod
    def parse_content(content: str) -> StrategyConfig:
        # Use regex to find KEY=VALUE pairs, handling multiline and spaces
        pattern = re.compile(r"([A-Z_]+)\s*=\s*([^\n\r]+)")
        matches = pattern.findall(content)
        
        config_dict = {}
        for key, value in matches:
            value = value.strip()
            # Try to convert to bool or int/float if applicable
            if value.lower() == "true":
                config_dict[key] = True
            elif value.lower() == "false":
                config_dict[key] = False
            else:
                try:
                    if "." in value:
                        config_dict[key] = float(value)
                    else:
                        config_dict[key] = int(value)
                except ValueError:
                    config_dict[key] = value
                    
        return StrategyConfig(**config_dict)
