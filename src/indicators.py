"""
Technical Indicators Module
Implementations of common technical analysis indicators.
"""

import pandas as pd
import numpy as np
from typing import Tuple


class TechnicalIndicators:
    """Calculate technical analysis indicators on OHLCV data."""
    
    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        """
        Simple Moving Average.
        
        Args:
            series: Price series (typically close prices)
            period: Number of periods for averaging
            
        Returns:
            SMA values
        """
        return series.rolling(window=period).mean()
    
    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """
        Exponential Moving Average.
        
        Args:
            series: Price series
            period: Number of periods for averaging
            
        Returns:
            EMA values
        """
        return series.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """
        Relative Strength Index.
        
        Measures the speed and magnitude of price changes.
        Values range from 0 to 100.
        - Above 70: Overbought
        - Below 30: Oversold
        
        Args:
            series: Price series (typically close prices)
            period: RSI period (default 14)
            
        Returns:
            RSI values (0-100)
        """
        delta = series.diff()
        
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Avoid division by zero
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.fillna(50)  # Neutral RSI for NaN values
    
    @staticmethod
    def macd(series: pd.Series, 
             fast_period: int = 12, 
             slow_period: int = 26, 
             signal_period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Moving Average Convergence Divergence.
        
        Args:
            series: Price series
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line period (default 9)
            
        Returns:
            Tuple of (MACD line, Signal line, Histogram)
        """
        fast_ema = TechnicalIndicators.ema(series, fast_period)
        slow_ema = TechnicalIndicators.ema(series, slow_period)
        
        macd_line = fast_ema - slow_ema
        signal_line = TechnicalIndicators.ema(macd_line, signal_period)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(series: pd.Series, 
                        period: int = 20, 
                        std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Bollinger Bands.
        
        Args:
            series: Price series
            period: SMA period (default 20)
            std_dev: Number of standard deviations (default 2)
            
        Returns:
            Tuple of (Upper band, Middle band, Lower band)
        """
        middle = TechnicalIndicators.sma(series, period)
        std = series.rolling(window=period).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, 
            period: int = 14) -> pd.Series:
        """
        Average True Range.
        
        Measures market volatility.
        
        Args:
            high: High prices
            low: Low prices  
            close: Close prices
            period: ATR period (default 14)
            
        Returns:
            ATR values
        """
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        On-Balance Volume.
        
        Uses volume flow to predict price changes.
        
        Args:
            close: Close prices
            volume: Volume data
            
        Returns:
            OBV values
        """
        direction = np.sign(close.diff())
        direction.iloc[0] = 0
        
        obv = (direction * volume).cumsum()
        return obv
    
    @staticmethod
    def vwap(high: pd.Series, low: pd.Series, close: pd.Series, 
             volume: pd.Series) -> pd.Series:
        """
        Volume Weighted Average Price.
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            volume: Volume data
            
        Returns:
            VWAP values
        """
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        return vwap
    
    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                   k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """
        Stochastic Oscillator.
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            k_period: %K period (default 14)
            d_period: %D period (default 3)
            
        Returns:
            Tuple of (%K, %D)
        """
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()
        
        return k, d
    
    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Average Directional Index.
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ADX period (default 14)
            
        Returns:
            ADX values (0-100)
        """
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        
        plus_dm = pd.Series(plus_dm, index=high.index)
        minus_dm = pd.Series(minus_dm, index=high.index)
        
        # Calculate smoothed TR and DM using Wilder's Smoothing (alpha = 1/period)
        # We can implement Wilder's smoothing using EWM with alpha=1/period, adjust=False
        alpha = 1 / period
        
        tr_smooth = tr.ewm(alpha=alpha, adjust=False).mean()
        plus_dm_smooth = plus_dm.ewm(alpha=alpha, adjust=False).mean()
        minus_dm_smooth = minus_dm.ewm(alpha=alpha, adjust=False).mean()
        
        # Calculate DI
        plus_di = 100 * (plus_dm_smooth / tr_smooth)
        minus_di = 100 * (minus_dm_smooth / tr_smooth)
        
        # Calculate DX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        
        # Calculate ADX (smoothed DX)
        adx = dx.ewm(alpha=alpha, adjust=False).mean()
        
        return adx

    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Average Directional Index (ADX).
        
        Measures the strength of a trend.
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ADX period (default 14)
            
        Returns:
            ADX values
        """
        plus_dm = high.diff()
        minus_dm = low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        
        plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / atr)
        minus_di = 100 * (abs(minus_dm).ewm(alpha=1/period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.ewm(alpha=1/period).mean()
        
        return adx

    @staticmethod
    def hurst_exponent(series: pd.Series, max_lag: int = 20) -> float:
        """
        Calculate Hurst Exponent.
        
        H < 0.5: Mean reverting
        H = 0.5: Random walk
        H > 0.5: Trending
        
        Args:
            series: Price series (log prices recommended)
            max_lag: Maximum lag for R/S calculation
            
        Returns:
            Hurst exponent (scalar)
        """
        lags = range(2, max_lag)
        # Use .values to avoid pandas index alignment issues
        tau = [np.sqrt(np.std(np.subtract(series[lag:].values, series[:-lag].values))) for lag in lags]
        
        # Polyfit to line
        m = np.polyfit(np.log(lags), np.log(tau), 1)
        return m[0] * 2.0


def add_all_indicators(df: pd.DataFrame, 
                       fast_ma: int = 10,
                       slow_ma: int = 50,
                       rsi_period: int = 14) -> pd.DataFrame:
    """
    Add common technical indicators to a DataFrame.
    
    Args:
        df: DataFrame with OHLCV data
        fast_ma: Fast moving average period
        slow_ma: Slow moving average period
        rsi_period: RSI period
        
    Returns:
        DataFrame with added indicator columns
    """
    ti = TechnicalIndicators
    
    # Moving Averages
    df['sma_fast'] = ti.sma(df['close'], fast_ma)
    df['sma_slow'] = ti.sma(df['close'], slow_ma)
    df['ema_fast'] = ti.ema(df['close'], fast_ma)
    df['ema_slow'] = ti.ema(df['close'], slow_ma)
    
    # Momentum
    df['rsi'] = ti.rsi(df['close'], rsi_period)
    macd, signal, hist = ti.macd(df['close'])
    df['macd'] = macd
    df['macd_signal'] = signal
    df['macd_hist'] = hist
    
    # Trend Strength
    df['adx'] = ti.adx(df['high'], df['low'], df['close'])
    
    # Volatility
    upper, middle, lower = ti.bollinger_bands(df['close'])
    df['bb_upper'] = upper
    df['bb_middle'] = middle
    df['bb_lower'] = lower
    df['atr'] = ti.atr(df['high'], df['low'], df['close'])
    
    # Volume
    if 'volume' in df.columns:
        df['obv'] = ti.obv(df['close'], df['volume'])
        df['vwap'] = ti.vwap(df['high'], df['low'], df['close'], df['volume'])
    
    return df
