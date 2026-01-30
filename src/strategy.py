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
    
    
    def __init__(self, name: str, params: Dict[str, Any] = None, data_timeframe: str = None):
        """
        Initialize strategy.
        
        Args:
            name: Strategy name
            params: Strategy parameters
            data_timeframe: Timeframe of the data (e.g., '1m', '1d')
        """
        self.name = name
        self.params = params or {}
        self.data_timeframe = data_timeframe
    
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
        params = self.params.copy()
        if self.data_timeframe:
            params['data_timeframe'] = self.data_timeframe
        return params


class HighSharpeTrendStrategy(BaseStrategy):
    """
    Trend-Momentum Confirmation Strategy.
    Target: Sharpe Ratio > 1.0
    
    Logic:
    1. Trend: EMA 50 > EMA 200 (Long-term Bullish structure).
    2. Regime: Price > EMA 200 (Filter out bear market dips).
    3. Momentum: RSI between 40 and 65 (Strength without exhaustion).
    4. Exit: RSI > 75 (Overbought) OR EMA Cross-under.
    """
    
    def __init__(self, fast_period: int = 50, slow_period: int = 200, rsi_period: int = 14, **kwargs):
        super().__init__(
            name="High-Sharpe Trend",
            params={'fast_period': fast_period, 'slow_period': slow_period, 'rsi_period': rsi_period},
            data_timeframe=kwargs.get('data_timeframe')
        )
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.rsi_period = rsi_period

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        ti = TechnicalIndicators
        
        # Calculate Indicators
        df['ema_fast'] = ti.ema(df['close'], self.fast_period)
        df['ema_slow'] = ti.ema(df['close'], self.slow_period)
        df['rsi'] = ti.rsi(df['close'], self.rsi_period)
        
        # Conditions
        trend_up = df['ema_fast'] > df['ema_slow']
        regime_ok = df['close'] > df['ema_slow']
        momentum_ok = (df['rsi'] >= 40) & (df['rsi'] <= 65)
        
        # Exit Logic
        exit_condition = (df['ema_fast'] < df['ema_slow']) | (df['rsi'] >= 75)
        
        # Signal Generation
        df['signal'] = Signal.HOLD.value
        
        # Vectorized Normalization: Trigger only on state change
        df['buy_trigger'] = (trend_up & regime_ok & momentum_ok).astype(int).diff()
        df.loc[df['buy_trigger'] == 1, 'signal'] = Signal.BUY.value
        
        df['sell_trigger'] = exit_condition.astype(int).diff()
        df.loc[df['sell_trigger'] == 1, 'signal'] = Signal.SELL.value
        
        return df.drop(columns=['buy_trigger', 'sell_trigger'])


class MACrossoverStrategy(BaseStrategy):
    """Moving Average Crossover with normalized signal triggering."""
    
    def __init__(self, fast_period: int = 10, slow_period: int = 50, use_ema: bool = True, **kwargs):
        super().__init__(
            name="MA Crossover", 
            params={'fast_period': fast_period, 'slow_period': slow_period, 'use_ema': use_ema},
            data_timeframe=kwargs.get('data_timeframe')
        )
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.use_ema = use_ema
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        ti = TechnicalIndicators
        
        df['fast_ma'] = ti.ema(df['close'], self.fast_period) if self.use_ema else ti.sma(df['close'], self.fast_period)
        df['slow_ma'] = ti.ema(df['close'], self.slow_period) if self.use_ema else ti.sma(df['close'], self.slow_period)
        
        df['signal'] = Signal.HOLD.value
        df['cross'] = (df['fast_ma'] > df['slow_ma']).astype(int).diff()
        
        df.loc[df['cross'] == 1, 'signal'] = Signal.BUY.value
        df.loc[df['cross'] == -1, 'signal'] = Signal.SELL.value
        
        return df.drop(columns=['cross'])


class RSIStrategy(BaseStrategy):
    """
    RSI (Relative Strength Index) Strategy.
    
    Generates BUY signal when RSI crosses below oversold threshold.
    Generates SELL signal when RSI crosses above overbought threshold.
    """
    
    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70, **kwargs):
        """
        Initialize RSI strategy.
        
        Args:
            period: RSI calculation period
            oversold: Oversold threshold (buy signal)
            overbought: Overbought threshold (sell signal)
            **kwargs: Additional arguments passed to BaseStrategy
        """
        super().__init__(
            name="RSI",
            params={
                'period': period,
                'oversold': oversold,
                'overbought': overbought
            },
            data_timeframe=kwargs.get('data_timeframe')
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
                 rsi_overbought: int = 70,
                 **kwargs):
        """
        Initialize combined strategy.
        
        Args:
            fast_period: Fast MA period
            slow_period: Slow MA period
            rsi_period: RSI period
            rsi_oversold: RSI oversold threshold
            rsi_overbought: RSI overbought threshold
            **kwargs: Additional arguments passed to BaseStrategy
        """
        super().__init__(
            name="MA Crossover + RSI",
            params={
                'fast_period': fast_period,
                'slow_period': slow_period,
                'rsi_period': rsi_period,
                'rsi_oversold': rsi_oversold,
                'rsi_overbought': rsi_overbought
            },
            data_timeframe=kwargs.get('data_timeframe')
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
    
    def __init__(self, period: int = 20, std_dev: float = 2.0, **kwargs):
        """
        Initialize Bollinger Bands strategy.
        
        Args:
            period: Moving average period
            std_dev: Number of standard deviations for bands
            **kwargs: Additional arguments passed to BaseStrategy
        """
        super().__init__(
            name="Bollinger Bands",
            params={
                'period': period,
                'std_dev': std_dev
            },
            data_timeframe=kwargs.get('data_timeframe')
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
    """MACD Histogram crossover strategy."""
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9, **kwargs):
        super().__init__(
            name="MACD", 
            params={'fast': fast, 'slow': slow, 'signal': signal},
            data_timeframe=kwargs.get('data_timeframe')
        )
        self.fast = fast
        self.slow = slow
        self.signal_period = signal
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        ti = TechnicalIndicators
        macd, signal, hist = ti.macd(df['close'], self.fast, self.slow, self.signal_period)
        df['macd_hist'] = hist
        
        df['signal'] = Signal.HOLD.value
        df['cross'] = (df['macd_hist'] > 0).astype(int).diff()
        
        df.loc[df['cross'] == 1, 'signal'] = Signal.BUY.value
        df.loc[df['cross'] == -1, 'signal'] = Signal.SELL.value
        
        return df.drop(columns=['cross'])


class VWAPStrategy(BaseStrategy):
    """VWAP Price-cross strategy."""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="VWAP",
            params={},
            data_timeframe=kwargs.get('data_timeframe')
        )
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        if 'volume' not in df.columns: return df
        df = df.copy()
        ti = TechnicalIndicators
        df['vwap'] = ti.vwap(df['high'], df['low'], df['close'], df['volume'])
        
        df['signal'] = Signal.HOLD.value
        df['cross'] = (df['close'] > df['vwap']).astype(int).diff()
        
        df.loc[df['cross'] == 1, 'signal'] = Signal.BUY.value
        df.loc[df['cross'] == -1, 'signal'] = Signal.SELL.value
        
        return df


class BollingerRSIStrategy(BaseStrategy):
    """Mean Reversion: Price < Lower Band + RSI < 30."""
    
    def __init__(self, period: int = 20, std_dev: float = 2.0, rsi_period: int = 14, oversold: int = 30, overbought: int = 70, **kwargs):
        super().__init__(
            name="Bollinger + RSI", 
            params={'period': period, 'std_dev': std_dev, 'rsi_period': rsi_period, 'oversold': oversold, 'overbought': overbought},
            data_timeframe=kwargs.get('data_timeframe')
        )
        self.period = period
        self.std_dev = std_dev
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        ti = TechnicalIndicators
        
        upper, middle, lower = ti.bollinger_bands(df['close'], self.period, self.std_dev)
        df['bb_lower'] = lower
        df['bb_upper'] = upper
        df['rsi'] = ti.rsi(df['close'], self.rsi_period)
        
        df['signal'] = Signal.HOLD.value
        
        # Normalized triggers
        df['buy_trigger'] = ((df['close'] < df['bb_lower']) & (df['rsi'] < self.oversold)).astype(int).diff()
        df['sell_trigger'] = ((df['close'] > df['bb_upper']) & (df['rsi'] > self.overbought)).astype(int).diff()
        
        df.loc[df['buy_trigger'] == 1, 'signal'] = Signal.BUY.value
        df.loc[df['sell_trigger'] == 1, 'signal'] = Signal.SELL.value
        
        return df.drop(columns=['buy_trigger', 'sell_trigger'])


class DynamicRegimeStrategy(BaseStrategy):
    """
    Dynamic Regime Switching Strategy.
    
    Uses ADX to detect market regime (Trend vs Range).
    - High ADX (> threshold): Uses Trend Strategy (MACD)
    - Low ADX (<= threshold): Uses Range Strategy (RSI)
    """
    
    def __init__(self, 
                 adx_period: int = 14,
                 adx_threshold: int = 25,
                 **kwargs):
        """
        Initialize Dynamic Regime Strategy.
        
        Args:
            adx_period: Period for ADX calculation
            adx_threshold: Threshold to switch regimes (default 25)
            **kwargs: Additional params
        """
        super().__init__(
            name="Dynamic Regime (ADX)",
            params={
                'adx_period': adx_period,
                'adx_threshold': adx_threshold,
            },
            data_timeframe=kwargs.get('data_timeframe')
        )
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        
        # Initialize sub-strategies
        # We use standard parameters for sub-strategies for now
        self.trend_strategy = MACDStrategy(**kwargs)
        self.range_strategy = RSIStrategy(**kwargs)
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate signals based on regime."""
        df = df.copy()
        ti = TechnicalIndicators
        
        # 1. Calculate ADX to determine regime
        if 'high' not in df.columns or 'low' not in df.columns:
            # Fallback if high/low missing
            return self.range_strategy.generate_signals(df)
            
        df['adx'] = ti.adx(df['high'], df['low'], df['close'], self.adx_period)
        
        # 2. Get signals from both strategies
        trend_df = self.trend_strategy.generate_signals(df)
        range_df = self.range_strategy.generate_signals(df)
        
        # 3. Combine signals
        df['signal'] = Signal.HOLD.value
        
        # We need to align the dataframes if necessary, but here they should match
        
        # Identify regimes
        is_trend = df['adx'] > self.adx_threshold
        is_range = df['adx'] <= self.adx_threshold
        
        # Apply Trend signals where ADX is high
        df.loc[is_trend, 'signal'] = trend_df.loc[is_trend, 'signal']
        
        # Apply Range signals where ADX is low
        df.loc[is_range, 'signal'] = range_df.loc[is_range, 'signal']
        
        # Optional: Add regime column for debugging/visualization
        df['regime'] = np.where(is_trend, 'TREND', 'RANGE')
        
        return df


def get_strategy(name: str, **kwargs) -> BaseStrategy:
    """Factory function for all strategies."""
    strategies = {
        'high_sharpe': HighSharpeTrendStrategy,
        'ma_crossover': MACrossoverStrategy,
        'rsi': RSIStrategy,
        'ma_rsi': MACrossoverRSIStrategy,
        'bollinger': BollingerBandsStrategy,
        'bollinger_rsi': BollingerRSIStrategy,
        'macd': MACDStrategy,
        'vwap': VWAPStrategy,
        'dynamic_regime': DynamicRegimeStrategy
    }
    
    key = name.lower()
    if key not in strategies:
        raise ValueError(f"Strategy {name} not found. Available: {list(strategies.keys())}")
    
    return strategies[key](**kwargs)
