"""
Market Analyzer Module
Analyzes market conditions (Trend, Volatility, Regime) and recommends trading strategies.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from .indicators import TechnicalIndicators

class MarketAnalyzer:
    """Analyzes market data to determine regime and recommend strategies."""
    
    def __init__(self, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series = None):
        """
        Initialize MarketAnalyzer.
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            volume: Volume data (optional)
        """
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.ti = TechnicalIndicators
        
    def analyze_market(self) -> Dict[str, Any]:
        """
        Analyze the market to determine its current state.
        
        Returns:
            Dictionary containing market analysis metrics:
            - adx: Trend Strength (0-100)
            - hurst: Market Regime (<0.5 Mean Reverting, >0.5 Trending)
            - volatility: Volatility measure (ATR / Close)
            - trend_direction: 'UP', 'DOWN', or 'SIDEWAYS'
            - momentum_exists: Boolean
        """
        # Calculate Indicators
        adx_series = self.ti.adx(self.high, self.low, self.close)
        adx_value = adx_series.iloc[-1]
        
        # Calculate Hurst Exponent on the last 100 periods (or full length if shorter)
        lookback = min(len(self.close), 100)
        hurst_value = self.ti.hurst_exponent(self.close.iloc[-lookback:])
        
        # Calculate Volatility (ATR normalized by price)
        atr_series = self.ti.atr(self.high, self.low, self.close)
        current_atr = atr_series.iloc[-1]
        volatility_ratio = current_atr / self.close.iloc[-1]
        
        # Determine Trend Direction (using simple EMA comparison)
        ema_fast = self.ti.ema(self.close, 20).iloc[-1]
        ema_slow = self.ti.ema(self.close, 50).iloc[-1]
        
        if ema_fast > ema_slow * 1.001:
            trend_direction = "UP"
        elif ema_fast < ema_slow * 0.999:
            trend_direction = "DOWN"
        else:
            trend_direction = "SIDEWAYS"
            
        return {
            "adx": round(adx_value, 2),
            "hurst": round(hurst_value, 2),
            "volatility": round(volatility_ratio * 100, 2), # Percentage
            "volatility_value": round(current_atr, 4),
            "trend_direction": trend_direction
        }
    
    def recommend_strategy(self) -> Dict[str, Any]:
        """
        Recommend a trading strategy based on market analysis.
        
        Returns:
            Dictionary with:
            - strategy: Strategy Name
            - reasoning: Explanation
            - params: Recommended Parameters
            - risks: List of potential risks
        """
        analysis = self.analyze_market()
        
        adx = analysis["adx"]
        hurst = analysis["hurst"]
        volatility = analysis["volatility"]
        
        # Decision Logic
        if (adx > 25 and hurst > 0.55) or (adx > 40):
            # Strong Trend
            strategy = "MA Crossover"
            reasoning = f"Market is strongly trending (ADX={adx}, Hurst={hurst}). Trend following strategies work best here."
            params = {"fast_period": 10, "slow_period": 50, "use_ema": True}
            risks = ["Whipsaws in sudden reversals", "Lag in entry/exit"]
            
        elif adx < 20 and hurst < 0.4:
            # Mean Reversion / Ranging
            strategy = "Bollinger Bands"
            reasoning = f"Market is ranging/mean-reverting (ADX={adx}, Hurst={hurst}). Price is likely to bounce between bands."
            params = {"period": 20, "std_dev": 2.0}
            risks = ["Breakouts against the trade", "Range expansion"]
            
        elif volatility > 2.0: # High Volatility (>2% daily move equivalent)
             # High Volatility -> Maybe use wider stops or volatility-based logic
            strategy = "Bollinger + RSI"
            reasoning = f"High volatility detected ({volatility}%). Using Bollinger Bands with RSI confirmation to filter false signals."
            params = {"period": 20, "std_dev": 2.5, "rsi_period": 14} # Wider bands
            risks = ["Extreme volatility can trigger stops"]
            
        else:
            # Default / Mixed Conditions
            strategy = "RSI"
            reasoning = "Market conditions are mixed. RSI can help identify overbought/oversold levels in this chop."
            params = {"period": 14, "oversold": 30, "overbought": 70}
            risks = ["False signals in strong trends"]
            
        return {
            "recommended_strategy": strategy,
            "analysis": analysis,
            "reasoning": reasoning,
            "parameters": params,
            "risks": risks
        }
