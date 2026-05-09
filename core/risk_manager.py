import logging
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel

logger = logging.getLogger("antigravity.risk_manager")

class RiskManager:
    def __init__(self, 
                 max_consecutive_losses: int = 3,
                 stop_loss: float = 20.0,
                 take_profit: float = 50.0,
                 max_daily_loss_pct: float = 6.0,
                 max_trades_per_day: int = 7):
        self.max_consecutive_losses = max_consecutive_losses
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_trades_per_day = max_trades_per_day
        
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.total_profit = 0.0
        self.trades_today = 0
        self.starting_balance = 0.0 # Will be set on first run
        
        self.is_paused = False
        self.pause_reason = ""

    def reset(self):
        """Reset session stats when switching accounts or starting a new day."""
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.total_profit = 0.0
        self.trades_today = 0
        self.starting_balance = 0.0
        self.is_paused = False
        self.pause_reason = ""
        logger.info("Risk Manager session stats reset.")

    def set_starting_balance(self, balance: float):
        if self.starting_balance == 0:
            self.starting_balance = balance
            logger.info(f"Starting balance set: ${balance}")

    def process_result(self, result: str, profit: float):
        self.total_profit += profit
        self.trades_today += 1
        
        if result == 'win':
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            logger.info(f"Trade WON. Profit: {profit}. Wins in a row: {self.consecutive_wins}")
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            logger.info(f"Trade LOST. Consecutive losses: {self.consecutive_losses}")

        # Check limits
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.is_paused = True
            self.pause_reason = f"Max consecutive losses reached ({self.max_consecutive_losses})."
            
        if self.total_profit <= -self.stop_loss:
            self.is_paused = True
            self.pause_reason = f"Session Stop Loss triggered: ${self.total_profit:.2f}"
            
        if self.total_profit >= self.take_profit:
            self.is_paused = True
            self.pause_reason = f"Session Take Profit reached: ${self.total_profit:.2f}"

    def can_trade(self, current_balance: float) -> Tuple[bool, str]:
        if self.is_paused:
            return False, self.pause_reason
            
        if self.starting_balance > 0:
            drawdown_pct = ((self.starting_balance - current_balance) / self.starting_balance) * 100
            if drawdown_pct >= self.max_daily_loss_pct:
                return False, f"Daily loss limit reached ({drawdown_pct:.1f}%)"
                
        if self.trades_today >= self.max_trades_per_day:
            return False, f"Max trades per day reached ({self.max_trades_per_day})"
            
        return True, "OK"

    def calculate_stake(self, balance: float, grade: str) -> float:
        # Base stake by grade
        grade_multiplier = {"A": 0.05, "B": 0.03, "C": 0.02}
        base_pct = grade_multiplier.get(grade, 0.02)
        
        multiplier = 1.0
        # Recovery after loss (30% increase per loss)
        if self.consecutive_losses > 0:
            for _ in range(self.consecutive_losses):
                multiplier *= 1.3
        else:
            # Win streak bonus (10% per win, max 2 steps)
            win_bonus = min(self.consecutive_wins, 2) * 0.10
            multiplier = 1 + win_bonus
            
        stake = balance * base_pct * multiplier
        
        # Hard limits: Max 5%, Min 1% of balance
        stake = min(stake, balance * 0.05)
        stake = max(stake, balance * 0.01)
        
        return round(stake, 2)

    def reset_limits(self):
        self.total_profit = 0.0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.trades_today = 0
        self.is_paused = False
        self.pause_reason = ""
        logger.info("Risk limits reset.")
