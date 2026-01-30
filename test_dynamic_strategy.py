
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.strategy import get_strategy, Signal
from src.indicators import TechnicalIndicators

def create_sine_wave_data(periods=200):
    """Create a sine wave dataset (ranging market)."""
    x = np.linspace(0, 4*np.pi, periods)
    y = np.sin(x) * 10 + 100
    
    dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(periods)]
    
    df = pd.DataFrame({
        'date': dates,
        'open': y,
        'high': y + 0.5,
        'low': y - 0.5,
        'close': y,
        'volume': 1000
    })
    return df

def create_trend_data(periods=200):
    """Create a linear trend dataset (trending market)."""
    x = np.linspace(0, 100, periods)
    y = x + 100
    
    dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(periods)]
    
    df = pd.DataFrame({
        'date': dates,
        'open': y,
        'high': y + 0.5,
        'low': y - 0.5,
        'close': y,
        'volume': 1000
    })
    return df

def test_adx():
    print("Testing ADX calculation...")
    # Create a strong trend (ADX should be high)
    df = create_trend_data(100)
    adx = TechnicalIndicators.adx(df['high'], df['low'], df['close'], period=14)
    item = adx.iloc[-1]
    print(f"ADX on Trend: {item}")
    
    # Create a range (ADX should be low)
    df_range = create_sine_wave_data(100)
    adx_range = TechnicalIndicators.adx(df_range['high'], df_range['low'], df_range['close'], period=14)
    item_range = adx_range.iloc[-1]
    print(f"ADX on Range: {item_range}")
    
    if item > item_range:
        print("PASS: ADX correctly identifies trend vs range.")
    else:
        print("FAIL: ADX failed to distinguish trend vs range.")

def test_dynamic_strategy():
    print("\nTesting Dynamic Regime Strategy...")
    strategy = get_strategy('dynamic_regime', adx_threshold=20)
    
    # Test on mixed data
    df_range = create_sine_wave_data(100)
    df_trend = create_trend_data(100)
    
    # Concatenate to simulate regime change
    df = pd.concat([df_range, df_trend], ignore_index=True)
    
    result = strategy.generate_signals(df)
    
    print("Checking regimes...")
    regimes = result['regime'].value_counts()
    print(regimes)
    
    if 'TREND' in regimes and 'RANGE' in regimes:
        print("PASS: Strategy detected both regimes.")
    else:
        print("FAIL: Strategy did not switch regimes.")

if __name__ == "__main__":
    try:
        test_adx()
        test_dynamic_strategy()
    except Exception as e:
        print(f"ERROR: {e}")
