
import sys
import os
import pandas as pd
import numpy as np

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.market_analyzer import MarketAnalyzer

def generate_trending_data(length=200):
    np.random.seed(42)
    # Random Walk with Drift
    close = [100]
    for _ in range(length-1):
        change = np.random.normal(0.5, 1) # Mean 0.5 (Drift), Std 1
        close.append(close[-1] + change)
    
    close = pd.Series(close)
    high = close + np.random.uniform(0, 1, length)
    low = close - np.random.uniform(0, 1, length)
    return high, low, close

def generate_ranging_data(length=200):
    np.random.seed(42)
    # Sine wave range
    x = np.linspace(0, 8*np.pi, length)
    trend = 100 + 5 * np.sin(x) # Smaller amplitude
    noise = np.random.normal(0, 1, length) # Less noise
    close = trend + noise
    high = close + np.random.uniform(0, 1, length)
    low = close - np.random.uniform(0, 1, length)
    return pd.Series(high), pd.Series(low), pd.Series(close)

def test_trending():
    print("\n--- Testing Trending Data ---")
    h, l, c = generate_trending_data()
    analyzer = MarketAnalyzer(h, l, c)
    result = analyzer.recommend_strategy()
    
    print(f"Analysis: ADX={result['analysis']['adx']}, Hurst={result['analysis']['hurst']}, Volatility={result['analysis']['volatility']}")
    print(f"Recommendation: {result['recommended_strategy']}")
    print(f"Reasoning: {result['reasoning']}")
    
    # Simple assertion
    if result['analysis']['adx'] > 25 and result['analysis']['hurst'] > 0.5:
         print("[PASS] ADX & Hurst identified trend.")
    else:
         print(f"[WARN] ADX/Hurst low: ADX={result['analysis']['adx']}, H={result['analysis']['hurst']}")
        
    if result['recommended_strategy'] == "MA Crossover":
         print("[PASS] Correct strategy recommended.")
    else:
         print(f"[FAIL] Unexpected strategy: {result['recommended_strategy']}")

def test_ranging():
    print("\n--- Testing Ranging Data ---")
    h, l, c = generate_ranging_data()
    analyzer = MarketAnalyzer(h, l, c)
    result = analyzer.recommend_strategy()
    
    print("Analysis:", result['analysis'])
    print("Recommendation:", result['recommended_strategy'])
    print("Reasoning:", result['reasoning'])
    
    if result['analysis']['adx'] < 25:
        print("[PASS] ADX correctly identified range (low trend strength).")
    
    if result['recommended_strategy'] in ["Bollinger Bands", "RSI"]:
         print("[PASS] Correct strategy recommended (Mean Reversion).")
    else:
         print(f"[FAIL] Unexpected strategy: {result['recommended_strategy']}")

if __name__ == "__main__":
    test_trending()
    test_ranging()
