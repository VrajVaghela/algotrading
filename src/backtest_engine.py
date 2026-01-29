"""
Backtesting Engine Module
Simulates trading strategies on historical data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .strategy import BaseStrategy, Signal


@dataclass
class Trade:
    """Represents a single completed trade."""
    entry_date: datetime
    entry_price: float
    exit_date: datetime
    exit_price: float
    shares: float
    side: str  # 'LONG' or 'SHORT'
    pnl: float = 0.0
    pnl_percent: float = 0.0
    duration_days: int = 0
    
    def __post_init__(self):
        """Calculate PnL after initialization."""
        if self.side == 'LONG':
            self.pnl = (self.exit_price - self.entry_price) * self.shares
            self.pnl_percent = ((self.exit_price / self.entry_price) - 1) * 100
        else:  # SHORT
            self.pnl = (self.entry_price - self.exit_price) * self.shares
            self.pnl_percent = ((self.entry_price / self.exit_price) - 1) * 100
        
        self.duration_days = (self.exit_date - self.entry_date).days


@dataclass
class Position:
    """Represents an open position."""
    entry_date: datetime
    entry_price: float
    shares: float
    side: str  # 'LONG' or 'SHORT'


@dataclass
class BacktestResult:
    """Contains all results from a backtest run."""
    initial_capital: float
    final_value: float
    total_return: float
    total_return_pct: float
    trades: List[Trade]
    equity_curve: pd.DataFrame
    signals_df: pd.DataFrame
    strategy_name: str
    strategy_params: Dict[str, Any]


class BacktestEngine:
    """
    Event-driven backtesting engine.
    
    Simulates trading strategy on historical data with realistic
    position management, costs, and slippage.
    """
    
    def __init__(self,
                 initial_capital: float = 100000,
                 commission: float = 0.001,  # 0.1% per trade
                 slippage: float = 0.0005,   # 0.05% slippage
                 position_size: float = 0.95, # Use 95% of capital
                 allow_short: bool = False):
        """
        Initialize backtesting engine.
        
        Args:
            initial_capital: Starting portfolio value
            commission: Commission per trade as decimal
            slippage: Slippage per trade as decimal
            position_size: Fraction of capital to use per trade
            allow_short: Allow short selling
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.position_size = position_size
        self.allow_short = allow_short
        
        # State
        self.cash = initial_capital
        self.position: Optional[Position] = None
        self.trades: List[Trade] = []
        self.equity_history: List[Dict] = []
    
    def run(self, df: pd.DataFrame, strategy: BaseStrategy) -> BacktestResult:
        """
        Run backtest on historical data.
        
        Args:
            df: DataFrame with OHLCV data
            strategy: Trading strategy instance
            
        Returns:
            BacktestResult with all metrics and data
        """
        # Reset state
        self.cash = self.initial_capital
        self.position = None
        self.trades = []
        self.equity_history = []
        
        # Generate signals
        signals_df = strategy.generate_signals(df.copy())
        
        # Iterate through each bar
        for idx, row in signals_df.iterrows():
            date = row['date']
            close = row['close']
            signal = row['signal']
            
            # Calculate current equity
            current_equity = self._calculate_equity(close)
            
            # Process signals
            if signal == Signal.BUY.value:
                if self.position is None:
                    # Open long position
                    self._open_position(date, close, 'LONG')
                elif self.position.side == 'SHORT':
                    # Close short and open long
                    self._close_position(date, close)
                    self._open_position(date, close, 'LONG')
                    
            elif signal == Signal.SELL.value:
                if self.position is not None and self.position.side == 'LONG':
                    # Close long position
                    self._close_position(date, close)
                elif self.position is None and self.allow_short:
                    # Open short position
                    self._open_position(date, close, 'SHORT')
            
            # Record equity
            self.equity_history.append({
                'date': date,
                'equity': self._calculate_equity(close),
                'cash': self.cash,
                'position_value': self._calculate_equity(close) - self.cash,
                'close': close
            })
        
        # Close any remaining position at the end
        if self.position is not None:
            last_row = signals_df.iloc[-1]
            self._close_position(last_row['date'], last_row['close'])
        
        # Create equity curve DataFrame
        equity_df = pd.DataFrame(self.equity_history)
        
        # Calculate results
        final_value = self.cash
        total_return = final_value - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        return BacktestResult(
            initial_capital=self.initial_capital,
            final_value=final_value,
            total_return=total_return,
            total_return_pct=total_return_pct,
            trades=self.trades,
            equity_curve=equity_df,
            signals_df=signals_df,
            strategy_name=strategy.name,
            strategy_params=strategy.get_params()
        )
    
    def _open_position(self, date: datetime, price: float, side: str):
        """Open a new position."""
        # Apply slippage
        if side == 'LONG':
            entry_price = price * (1 + self.slippage)
        else:
            entry_price = price * (1 - self.slippage)
        
        # Calculate position size
        available_capital = self.cash * self.position_size
        commission_cost = available_capital * self.commission
        capital_for_shares = available_capital - commission_cost
        shares = capital_for_shares / entry_price
        
        # Deduct from cash
        self.cash -= (shares * entry_price + commission_cost)
        
        # Create position
        self.position = Position(
            entry_date=date,
            entry_price=entry_price,
            shares=shares,
            side=side
        )
    
    def _close_position(self, date: datetime, price: float):
        """Close current position."""
        if self.position is None:
            return
        
        # Apply slippage
        if self.position.side == 'LONG':
            exit_price = price * (1 - self.slippage)
        else:
            exit_price = price * (1 + self.slippage)
        
        # Calculate proceeds
        if self.position.side == 'LONG':
            proceeds = self.position.shares * exit_price
        else:  # SHORT
            proceeds = self.position.shares * (2 * self.position.entry_price - exit_price)
        
        # Deduct commission
        commission_cost = proceeds * self.commission
        proceeds -= commission_cost
        
        # Add to cash
        self.cash += proceeds
        
        # Record trade
        trade = Trade(
            entry_date=self.position.entry_date,
            entry_price=self.position.entry_price,
            exit_date=date,
            exit_price=exit_price,
            shares=self.position.shares,
            side=self.position.side
        )
        self.trades.append(trade)
        
        # Clear position
        self.position = None
    
    def _calculate_equity(self, current_price: float) -> float:
        """Calculate current total equity."""
        equity = self.cash
        
        if self.position is not None:
            if self.position.side == 'LONG':
                equity += self.position.shares * current_price
            else:  # SHORT
                equity += self.position.shares * (2 * self.position.entry_price - current_price)
        
        return equity


def run_backtest(df: pd.DataFrame,
                 strategy: BaseStrategy,
                 initial_capital: float = 100000,
                 commission: float = 0.001,
                 slippage: float = 0.0005) -> BacktestResult:
    """
    Convenience function to run a backtest.
    
    Args:
        df: OHLCV DataFrame
        strategy: Trading strategy
        initial_capital: Starting capital
        commission: Commission rate
        slippage: Slippage rate
        
    Returns:
        BacktestResult
    """
    engine = BacktestEngine(
        initial_capital=initial_capital,
        commission=commission,
        slippage=slippage
    )
    return engine.run(df, strategy)
