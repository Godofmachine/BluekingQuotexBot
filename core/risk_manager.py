import logging
from typing import Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger("antigravity.risk_manager")

class TradeResult(BaseModel):
    id: str
    amount: float
    profit: float
    result: str  # 'win' or 'loss'
    timestamp: int

class RiskManager:
    def __init__(self, 
                 initial_amount: float,
                 martingale_enabled: bool = False,
                 max_consecutive_losses: int = 3,
                 stop_loss: float = 20.0,
                 take_profit: float = 50.0):
        self.initial_amount = initial_amount
        self.current_amount = initial_amount
        self.martingale_enabled = martingale_enabled
        self.max_consecutive_losses = max_consecutive_losses
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        
        self.consecutive_losses = 0
        self.total_profit = 0.0
        self.is_paused = False
        self.pause_reason = ""

    def process_result(self, result: str, profit: float):
        """
        Update risk parameters based on trade result.
        result: 'win' or 'loss'
        """
        self.total_profit += profit
        
        if result == 'win':
            self.consecutive_losses = 0
            self.current_amount = self.initial_amount
            logger.info(f"Trade WON. Profit: {profit}. Resetting amount to {self.current_amount}")
        else:
            self.consecutive_losses += 1
            logger.info(f"Trade LOST. Consecutive losses: {self.consecutive_losses}")
            
            if self.martingale_enabled:
                self.current_amount *= 2
                logger.info(f"Martingale active. Next trade amount: {self.current_amount}")
            else:
                self.current_amount = self.initial_amount

        # Check limits
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.is_paused = True
            self.pause_reason = "Max consecutive losses reached."
            logger.warning(self.pause_reason)
            
        if self.total_profit <= -self.stop_loss:
            self.is_paused = True
            self.pause_reason = f"Stop loss triggered: {self.total_profit}"
            logger.warning(self.pause_reason)
            
        if self.total_profit >= self.take_profit:
            self.is_paused = True
            self.pause_reason = f"Take profit reached: {self.total_profit}"
            logger.info(self.pause_reason)

    def get_next_amount(self) -> float:
        return self.current_amount

    def reset_limits(self):
        self.total_profit = 0.0
        self.consecutive_losses = 0
        self.is_paused = False
        self.pause_reason = ""
        self.current_amount = self.initial_amount
        logger.info("Risk limits reset.")
