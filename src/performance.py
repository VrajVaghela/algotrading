"""
Performance Metrics Module
Calculate trading performance statistics and risk metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
from dataclasses import dataclass

from .backtest_engine import BacktestResult, Trade


@dataclass
class PerformanceMetrics:
    """Container for all performance metrics."""
    # Returns
    total_return: float
    total_return_pct: float
    annualized_return: float
    
    # Risk
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    calmar_ratio: float
    
    # Trade Statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_trade_duration: float
    
    # Other
    volatility: float
    exposure_time: float


class PerformanceAnalyzer:
    """Analyze backtest results and calculate performance metrics."""
    
    def __init__(self, risk_free_rate: float = 0.05):
        """
        Initialize analyzer.
        
        Args:
            risk_free_rate: Annual risk-free rate for Sharpe calculation
        """
        self.risk_free_rate = risk_free_rate
    
    def analyze(self, result: BacktestResult) -> PerformanceMetrics:
        """
        Calculate all performance metrics from backtest result.
        
        Args:
            result: BacktestResult from backtesting engine
            
        Returns:
            PerformanceMetrics with all calculations
        """
        equity_curve = result.equity_curve
        trades = result.trades
        
        # Calculate returns
        returns_metrics = self._calculate_returns(result)
        
        # Calculate risk metrics
        risk_metrics = self._calculate_risk_metrics(equity_curve)
        
        # Calculate trade statistics
        trade_stats = self._calculate_trade_stats(trades)
        
        # Calculate exposure
        exposure = self._calculate_exposure(equity_curve)
        
        return PerformanceMetrics(
            # Returns
            total_return=result.total_return,
            total_return_pct=result.total_return_pct,
            annualized_return=returns_metrics['annualized_return'],
            
            # Risk
            sharpe_ratio=risk_metrics['sharpe_ratio'],
            sortino_ratio=risk_metrics['sortino_ratio'],
            max_drawdown=risk_metrics['max_drawdown'],
            max_drawdown_pct=risk_metrics['max_drawdown_pct'],
            calmar_ratio=risk_metrics['calmar_ratio'],
            volatility=risk_metrics['volatility'],
            
            # Trade Stats
            total_trades=trade_stats['total_trades'],
            winning_trades=trade_stats['winning_trades'],
            losing_trades=trade_stats['losing_trades'],
            win_rate=trade_stats['win_rate'],
            profit_factor=trade_stats['profit_factor'],
            avg_win=trade_stats['avg_win'],
            avg_loss=trade_stats['avg_loss'],
            largest_win=trade_stats['largest_win'],
            largest_loss=trade_stats['largest_loss'],
            avg_trade_duration=trade_stats['avg_trade_duration'],
            
            # Other
            exposure_time=exposure
        )
    
    def _calculate_returns(self, result: BacktestResult) -> Dict[str, float]:
        """Calculate return metrics."""
        equity_curve = result.equity_curve
        
        # Trading days
        n_days = len(equity_curve)
        trading_days_per_year = 252
        years = n_days / trading_days_per_year
        
        # Annualized return
        total_return_decimal = result.total_return_pct / 100
        if years > 0:
            annualized_return = ((1 + total_return_decimal) ** (1 / years) - 1) * 100
        else:
            annualized_return = 0
        
        return {
            'annualized_return': annualized_return
        }
    
    def _calculate_risk_metrics(self, equity_curve: pd.DataFrame) -> Dict[str, float]:
        """Calculate risk metrics."""
        equity = equity_curve['equity']
        
        # Daily returns
        daily_returns = equity.pct_change().dropna()
        
        # Volatility (annualized)
        daily_volatility = daily_returns.std()
        annualized_volatility = daily_volatility * np.sqrt(252) * 100
        
        # Sharpe Ratio
        mean_return = daily_returns.mean()
        daily_rf = self.risk_free_rate / 252
        if daily_volatility > 0:
            sharpe = (mean_return - daily_rf) / daily_volatility * np.sqrt(252)
        else:
            sharpe = 0
        
        # Sortino Ratio (uses downside deviation)
        downside_returns = daily_returns[daily_returns < 0]
        if len(downside_returns) > 0:
            downside_std = downside_returns.std()
            if downside_std > 0:
                sortino = (mean_return - daily_rf) / downside_std * np.sqrt(252)
            else:
                sortino = 0
        else:
            sortino = 0
        
        # Maximum Drawdown
        cummax = equity.cummax()
        drawdown = equity - cummax
        max_drawdown = drawdown.min()
        max_drawdown_pct = (max_drawdown / cummax[drawdown.idxmin()]) * 100 if cummax[drawdown.idxmin()] > 0 else 0
        
        # Calmar Ratio (annualized return / max drawdown)
        n_days = len(equity_curve)
        years = n_days / 252
        total_return_decimal = (equity.iloc[-1] / equity.iloc[0] - 1)
        if years > 0:
            annualized_return = (1 + total_return_decimal) ** (1 / years) - 1
        else:
            annualized_return = 0
        
        if abs(max_drawdown_pct) > 0:
            calmar = annualized_return * 100 / abs(max_drawdown_pct)
        else:
            calmar = 0
        
        return {
            'sharpe_ratio': round(sharpe, 2),
            'sortino_ratio': round(sortino, 2),
            'max_drawdown': round(max_drawdown, 2),
            'max_drawdown_pct': round(max_drawdown_pct, 2),
            'calmar_ratio': round(calmar, 2),
            'volatility': round(annualized_volatility, 2)
        }
    
    def _calculate_trade_stats(self, trades: List[Trade]) -> Dict[str, float]:
        """Calculate trade statistics."""
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'largest_win': 0,
                'largest_loss': 0,
                'avg_trade_duration': 0
            }
        
        pnls = [t.pnl for t in trades]
        durations = [t.duration_days for t in trades]
        
        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]
        
        total_wins = sum(winning_trades) if winning_trades else 0
        total_losses = abs(sum(losing_trades)) if losing_trades else 0
        
        return {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(len(winning_trades) / len(trades) * 100, 2) if trades else 0,
            'profit_factor': round(total_wins / total_losses, 2) if total_losses > 0 else float('inf'),
            'avg_win': round(np.mean(winning_trades), 2) if winning_trades else 0,
            'avg_loss': round(np.mean(losing_trades), 2) if losing_trades else 0,
            'largest_win': round(max(pnls), 2) if pnls else 0,
            'largest_loss': round(min(pnls), 2) if pnls else 0,
            'avg_trade_duration': round(np.mean(durations), 1) if durations else 0
        }
    
    def _calculate_exposure(self, equity_curve: pd.DataFrame) -> float:
        """Calculate exposure time (% of time in market)."""
        if 'position_value' not in equity_curve.columns:
            return 0
        
        in_market = (equity_curve['position_value'].abs() > 0).sum()
        total_bars = len(equity_curve)
        
        return round(in_market / total_bars * 100, 2) if total_bars > 0 else 0
    
    def get_drawdown_series(self, equity_curve: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate drawdown series for charting.
        
        Returns:
            DataFrame with date and drawdown_pct columns
        """
        equity = equity_curve['equity']
        cummax = equity.cummax()
        drawdown_pct = ((equity - cummax) / cummax) * 100
        
        return pd.DataFrame({
            'date': equity_curve['date'],
            'drawdown_pct': drawdown_pct
        })
    
    def get_monthly_returns(self, equity_curve: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate monthly returns for heatmap.
        
        Returns:
            DataFrame with year, month, and return columns
        """
        df = equity_curve.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        # Resample to monthly
        monthly = df['equity'].resample('M').last()
        monthly_returns = monthly.pct_change() * 100
        
        # Create pivot table
        result = pd.DataFrame({
            'year': monthly_returns.index.year,
            'month': monthly_returns.index.month,
            'return': monthly_returns.values
        }).dropna()
        
        return result


def calculate_metrics(result: BacktestResult, risk_free_rate: float = 0.05) -> PerformanceMetrics:
    """
    Convenience function to calculate all performance metrics.
    
    Args:
        result: BacktestResult from backtesting
        risk_free_rate: Annual risk-free rate
        
    Returns:
        PerformanceMetrics
    """
    analyzer = PerformanceAnalyzer(risk_free_rate)
    return analyzer.analyze(result)


def metrics_to_dict(metrics: PerformanceMetrics) -> Dict[str, Any]:
    """Convert PerformanceMetrics to dictionary for JSON serialization."""
    return {
        'returns': {
            'total_return': round(metrics.total_return, 2),
            'total_return_pct': round(metrics.total_return_pct, 2),
            'annualized_return': round(metrics.annualized_return, 2)
        },
        'risk': {
            'sharpe_ratio': metrics.sharpe_ratio,
            'sortino_ratio': metrics.sortino_ratio,
            'max_drawdown': metrics.max_drawdown,
            'max_drawdown_pct': metrics.max_drawdown_pct,
            'calmar_ratio': metrics.calmar_ratio,
            'volatility': metrics.volatility
        },
        'trades': {
            'total_trades': metrics.total_trades,
            'winning_trades': metrics.winning_trades,
            'losing_trades': metrics.losing_trades,
            'win_rate': metrics.win_rate,
            'profit_factor': metrics.profit_factor,
            'avg_win': metrics.avg_win,
            'avg_loss': metrics.avg_loss,
            'largest_win': metrics.largest_win,
            'largest_loss': metrics.largest_loss,
            'avg_trade_duration': metrics.avg_trade_duration
        },
        'exposure_time': metrics.exposure_time
    }
