
import unittest
import pandas as pd
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data_loader import DataLoader

class TestTimeframeDetection(unittest.TestCase):
    def test_detect_1d(self):
        dates = pd.date_range(start='2024-01-01', periods=10, freq='D')
        df = pd.DataFrame({'date': dates})
        loader = DataLoader()
        self.assertEqual(loader.detect_timeframe(df), '1d')
        
    def test_detect_1m(self):
        dates = pd.date_range(start='2024-01-01', periods=10, freq='1min')
        df = pd.DataFrame({'date': dates})
        loader = DataLoader()
        self.assertEqual(loader.detect_timeframe(df), '1m')

    def test_detect_5m(self):
        dates = pd.date_range(start='2024-01-01', periods=10, freq='5min')
        df = pd.DataFrame({'date': dates})
        loader = DataLoader()
        self.assertEqual(loader.detect_timeframe(df), '5m')
        
    def test_detect_1h(self):
        dates = pd.date_range(start='2024-01-01', periods=10, freq='1h')
        df = pd.DataFrame({'date': dates})
        loader = DataLoader()
        self.assertEqual(loader.detect_timeframe(df), '1h')

if __name__ == '__main__':
    unittest.main()
