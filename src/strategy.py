"""
Trading Strategy Module
Implements various trading strategies with signal generation.
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any

from .indicators import TechnicalIndicators, add_all_indicators


class Signal(Enum):
    """Trading signal types."""
    BUY = 1
    SELL = -1
    HOLD = 0


class BaseStrategy(ABC):
    """Abstract base class for trading strategies."""
    
    def __init__(self, name: str, params: Dict[str, Any] = None):
        """
        Initialize strategy.
        
        Args:
            name: Strategy name
            params: Strategy parameters
        """
        self.name = name
        self.params = params or {}
    
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals for the given data.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with added 'signal' column
        """
        pass
    
    def get_params(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return self.params


class MACrossoverStrategy(BaseStrategy):
    """
    Moving Average Crossover Strategy.
    
    Generates BUY signal when fast MA crosses above slow MA.
    Generates SELL signal when fast MA crosses below slow MA.
    """
    
    def __init__(self, fast_period: int = 10, slow_period: int = 50, use_ema: bool = False):
        """
        Initialize MA Crossover strategy.
        
        Args:
            fast_period: Fast moving average period
            slow_period: Slow moving average period
            use_ema: Use EMA instead of SMA
        """
        super().__init__(
            name="MA Crossover",
            params={
                'fast_period': fast_period,
                'slow_period': slow_period,
                'use_ema': use_ema
            }
        )
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.use_ema = use_ema
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate crossover signals."""
        df = df.copy()
        ti = TechnicalIndicators
        
        if self.use_ema:
            df['fast_ma'] = ti.ema(df['close'], self.fast_period)
            df['slow_ma'] = ti.ema(df['close'], self.slow_period)
        else:
            df['fast_ma'] = ti.sma(df['close'], self.fast_period)
            df['slow_ma'] = ti.sma(df['close'], self.slow_period)
        
        # Generate signals
        df['signal'] = Signal.HOLD.value
        
        # Crossover detection
        df['prev_fast'] = df['fast_ma'].shift(1)
        df['prev_slow'] = df['slow_ma'].shift(1)
        
        # BUY: Fast crosses above Slow
        buy_condition = (df['prev_fast'] <= df['prev_slow']) & (df['fast_ma'] > df['slow_ma'])
        df.loc[buy_condition, 'signal'] = Signal.BUY.value
        
        # SELL: Fast crosses below Slow
        sell_condition = (df['prev_fast'] >= df['prev_slow']) & (df['fast_ma'] < df['slow_ma'])
        df.loc[sell_condition, 'signal'] = Signal.SELL.value
        
        # Clean up temp columns
        df = df.drop(columns=['prev_fast', 'prev_slow'])
        
        return df


class RSIStrategy(BaseStrategy):
    """
    RSI (Relative Strength Index) Strategy.
    
    Generates BUY signal when RSI crosses below oversold threshold.
    Generates SELL signal when RSI crosses above overbought threshold.
    """
    
    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        """
        Initialize RSI strategy.
        
        Args:
            period: RSI calculation period
            oversold: Oversold threshold (buy signal)
            overbought: Overbought threshold (sell signal)
        """
        super().__init__(
            name="RSI",
            params={
                'period': period,
                'oversold': oversold,
                'overbought': overbought
            }
        )
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate RSI signals."""
        df = df.copy()
        ti = TechnicalIndicators
        
        df['rsi'] = ti.rsi(df['close'], self.period)
        df['prev_rsi'] = df['rsi'].shift(1)
        
        df['signal'] = Signal.HOLD.value
        
        # BUY: RSI crosses above oversold threshold (exiting oversold)
        buy_condition = (df['prev_rsi'] <= self.oversold) & (df['rsi'] > self.oversold)
        df.loc[buy_condition, 'signal'] = Signal.BUY.value
        
        # SELL: RSI crosses below overbought threshold (exiting overbought)
        sell_condition = (df['prev_rsi'] >= self.overbought) & (df['rsi'] < self.overbought)
        df.loc[sell_condition, 'signal'] = Signal.SELL.value
        
        df = df.drop(columns=['prev_rsi'])
        
        return df


class MACrossoverRSIStrategy(BaseStrategy):
    """
    Combined MA Crossover + RSI Strategy.
    
    Uses MA Crossover for trend direction and RSI for confirmation.
    BUY: Fast MA > Slow MA AND RSI < overbought
    SELL: Fast MA < Slow MA AND RSI > oversold
    """
    
    def __init__(self, 
                 fast_period: int = 10, 
                 slow_period: int = 50,
                 rsi_period: int = 14,
                 rsi_oversold: int = 30,
                 rsi_overbought: int = 70):
        """
        Initialize combined strategy.
        
        Args:
            fast_period: Fast MA period
            slow_period: Slow MA period
            rsi_period: RSI period
            rsi_oversold: RSI oversold threshold
            rsi_overbought: RSI overbought threshold
        """
        super().__init__(
            name="MA Crossover + RSI",
            params={
                'fast_period': fast_period,
                'slow_period': slow_period,
                'rsi_period': rsi_period,
                'rsi_oversold': rsi_oversold,
                'rsi_overbought': rsi_overbought
            }
        )
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate combined signals."""
        df = df.copy()
        ti = TechnicalIndicators
        
        # Calculate indicators
        df['fast_ma'] = ti.sma(df['close'], self.fast_period)
        df['slow_ma'] = ti.sma(df['close'], self.slow_period)
        df['rsi'] = ti.rsi(df['close'], self.rsi_period)
        
        # Previous values for crossover detection
        df['prev_fast'] = df['fast_ma'].shift(1)
        df['prev_slow'] = df['slow_ma'].shift(1)
        
        df['signal'] = Signal.HOLD.value
        
        # BUY: Golden cross (fast crosses above slow) with RSI confirmation
        buy_condition = (
            (df['prev_fast'] <= df['prev_slow']) & 
            (df['fast_ma'] > df['slow_ma']) & 
            (df['rsi'] < self.rsi_overbought)
        )
        df.loc[buy_condition, 'signal'] = Signal.BUY.value
        
        # SELL: Death cross (fast crosses below slow) with RSI confirmation
        sell_condition = (
            (df['prev_fast'] >= df['prev_slow']) & 
            (df['fast_ma'] < df['slow_ma']) & 
            (df['rsi'] > self.rsi_oversold)
        )
        df.loc[sell_condition, 'signal'] = Signal.SELL.value
        
        # Clean up
        df = df.drop(columns=['prev_fast', 'prev_slow'])
        
        return df


class BollingerBandsStrategy(BaseStrategy):
    """
    Bollinger Bands Mean Reversion Strategy.
    
    BUY: Price touches or crosses below lower band
    SELL: Price touches or crosses above upper band
    """
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        """
        Initialize Bollinger Bands strategy.
        
        Args:
            period: Moving average period
            std_dev: Number of standard deviations for bands
        """
        super().__init__(
            name="Bollinger Bands",
            params={
                'period': period,
                'std_dev': std_dev
            }
        )
        self.period = period
        self.std_dev = std_dev
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate Bollinger Bands signals."""
        df = df.copy()
        ti = TechnicalIndicators
        
        upper, middle, lower = ti.bollinger_bands(df['close'], self.period, self.std_dev)
        df['bb_upper'] = upper
        df['bb_middle'] = middle
        df['bb_lower'] = lower
        
        df['signal'] = Signal.HOLD.value
        
        # BUY: Price crosses below lower band
        buy_condition = df['close'] <= df['bb_lower']
        df.loc[buy_condition, 'signal'] = Signal.BUY.value
        
        # SELL: Price crosses above upper band
        sell_condition = df['close'] >= df['bb_upper']
        df.loc[sell_condition, 'signal'] = Signal.SELL.value
        
        return df



class MACDStrategy(BaseStrategy):
    """
    MACD (Moving Average Convergence Divergence) Strategy.
    
    BUY: MACD line crosses above Signal line (Histogram > 0)
    SELL: MACD line crosses below Signal line (Histogram < 0)
    """
    
    def __init__(self, fast_period: int = 12, 
                 slow_period: int = 26, 
                 signal_period: int = 9,
                 **kwargs):
        """
        Initialize MACD strategy.
        """
        super().__init__(
            name="MACD",
            params={
                'fast_period': fast_period,
                'slow_period': slow_period,
                'signal_period': signal_period
            }
        )
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate MACD signals."""
        df = df.copy()
        ti = TechnicalIndicators
        
        macd, signal, hist = ti.macd(df['close'], 
                                    self.fast_period, 
                                    self.slow_period, 
                                    self.signal_period)
        
        df['macd'] = macd
        df['macd_signal'] = signal
        df['macd_hist'] = hist
        
        # Previous values for crossover
        df['prev_hist'] = df['macd_hist'].shift(1)
        
        df['signal'] = Signal.HOLD.value
        
        # BUY: Histogram turns positive (MACD crosses above Signal)
        buy_condition = (df['prev_hist'] <= 0) & (df['macd_hist'] > 0)
        df.loc[buy_condition, 'signal'] = Signal.BUY.value
        
        # SELL: Histogram turns negative (MACD crosses below Signal)
        sell_condition = (df['prev_hist'] >= 0) & (df['macd_hist'] < 0)
        df.loc[sell_condition, 'signal'] = Signal.SELL.value
        
        df = df.drop(columns=['prev_hist'])
        
        return df


class VWAPStrategy(BaseStrategy):
    """
    VWAP (Volume Weighted Average Price) Strategy.
    
    BUY: Price crosses above VWAP
    SELL: Price crosses below VWAP
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            name="VWAP",
            params=kwargs
        )
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate VWAP signals."""
        df = df.copy()
        ti = TechnicalIndicators
        
        if 'volume' not in df.columns:
            return df
            
        df['vwap'] = ti.vwap(df['high'], df['low'], df['close'], df['volume'])
        
        df['prev_close'] = df['close'].shift(1)
        df['prev_vwap'] = df['vwap'].shift(1)
        
        df['signal'] = Signal.HOLD.value
        
        # BUY: Price crosses above VWAP
        buy_condition = (df['prev_close'] <= df['prev_vwap']) & (df['close'] > df['vwap'])
        df.loc[buy_condition, 'signal'] = Signal.BUY.value
        
        # SELL: Price crosses below VWAP
        sell_condition = (df['prev_close'] >= df['prev_vwap']) & (df['close'] < df['vwap'])
        df.loc[sell_condition, 'signal'] = Signal.SELL.value
        
        df = df.drop(columns=['prev_close', 'prev_vwap'])
        
        return df


class BollingerRSIStrategy(BaseStrategy):
    """
    Bollinger Bands + RSI Mean Reversion Strategy.
    
    BUY: Price < Lower Band AND RSI < Oversold
    SELL: Price > Upper Band AND RSI > Overbought
    """
    
    def __init__(self, 
                 period: int = 20, 
                 std_dev: float = 2.0,
                 rsi_period: int = 14,
                 rsi_oversold: int = 30,
                 rsi_overbought: int = 70,
                 **kwargs):
        super().__init__(
            name="Bollinger + RSI",
            params={
                'period': period,
                'std_dev': std_dev,
                'rsi_period': rsi_period,
                'rsi_oversold': rsi_oversold,
                'rsi_overbought': rsi_overbought
            }
        )
        self.period = period
        self.std_dev = std_dev
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        ti = TechnicalIndicators
        
        # Calculate indicators
        upper, middle, lower = ti.bollinger_bands(df['close'], self.period, self.std_dev)
        df['bb_upper'] = upper
        df['bb_lower'] = lower
        
        df['rsi'] = ti.rsi(df['close'], self.rsi_period)
        
        df['signal'] = Signal.HOLD.value
        
        # BUY: Price below lower band AND RSI oversold
        buy_condition = (df['close'] <= df['bb_lower']) & (df['rsi'] < self.rsi_oversold)
        df.loc[buy_condition, 'signal'] = Signal.BUY.value
        
        # SELL: Price above upper band AND RSI overbought
        sell_condition = (df['close'] >= df['bb_upper']) & (df['rsi'] > self.rsi_overbought)
        df.loc[sell_condition, 'signal'] = Signal.SELL.value
        
        return df


def get_strategy(name: str, **kwargs) -> BaseStrategy:
    """
    Factory function to get strategy by name.
    
    Args:
        name: Strategy name ('ma_crossover', 'rsi', 'ma_rsi', 'bollinger')
        **kwargs: Strategy parameters
        
    Returns:
        Strategy instance
    """
    strategies = {
        'ma_crossover': MACrossoverStrategy,
        'rsi': RSIStrategy,
        'ma_rsi': MACrossoverRSIStrategy,
        'bollinger': BollingerBandsStrategy,
        'macd': MACDStrategy,
        'vwap': VWAPStrategy,
        'bollinger_rsi': BollingerRSIStrategy
    }
    
    if name.lower() not in strategies:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(strategies.keys())}")
    
    return strategies[name.lower()](**kwargs)
