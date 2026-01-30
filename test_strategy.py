
import pandas as pd
import numpy as np
from src.strategy import get_strategy, HighSharpeTrendStrategy

def test_high_sharpe_strategy():
    print("Testing HighSharpeTrendStrategy...")
    
    # Create dummy data
    dates = pd.date_range(start='2023-01-01', periods=300, freq='D')
    df = pd.DataFrame({
        'date': dates,
        'open': np.random.rand(300) * 100,
        'high': np.random.rand(300) * 100,
        'low': np.random.rand(300) * 100,
        'close': np.random.rand(300) * 100,
        'volume': np.random.randint(100, 1000, 300)
    })
    
    # Ensure close prices have some trend to trigger signals
    # Make a simple uptrend
    df['close'] = np.linspace(100, 200, 300) + np.random.normal(0, 5, 300)
    
    # Initialize strategy
    strategy = get_strategy('high_sharpe', fast_period=10, slow_period=50, rsi_period=14)
    print(f"Strategy initialized: {strategy.name}")
    print(f"Params: {strategy.get_params()}")
    
    # Generate signals
    try:
        result_df = strategy.generate_signals(df)
        print("Signals generated successfully.")
        print("Columns:", result_df.columns)
        
        # Check if indicators are added
        expected_cols = ['ema_fast', 'ema_slow', 'rsi', 'signal']
        missing_cols = [col for col in expected_cols if col not in result_df.columns]
        
        if missing_cols:
            print(f"FAILED: Missing columns: {missing_cols}")
        else:
            print("PASSED: All expected columns present.")
            print(result_df[['close', 'ema_fast', 'ema_slow', 'rsi', 'signal']].tail())

    except Exception as e:
        print(f"FAILED: Error generating signals: {e}")
        raise e

if __name__ == "__main__":
    test_high_sharpe_strategy()
