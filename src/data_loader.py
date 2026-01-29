"""
Data Loader Module
Handles loading and processing of market data from various file formats.
"""

import pandas as pd
import zipfile
import os
from pathlib import Path
from typing import Optional, List


class DataLoader:
    """Load and process OHLCV market data from various file formats."""
    
    def __init__(self, data_dir: str = None):
        """
        Initialize the data loader.
        
        Args:
            data_dir: Directory containing data files. Defaults to project root.
        """
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent
        else:
            self.data_dir = Path(data_dir)
    
    def load_csv(self, filepath: str) -> pd.DataFrame:
        """Load data from a CSV file."""
        df = pd.read_csv(filepath)
        return self._standardize_columns(df)
    
    def load_excel(self, filepath: str, sheet_name: str = 0) -> pd.DataFrame:
        """Load data from an Excel file."""
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        return self._standardize_columns(df)
    
    def load_from_zip(self, zip_path: str, extract_to: str = None) -> pd.DataFrame:
        """
        Extract and load data from a ZIP file.
        
        Args:
            zip_path: Path to the ZIP file
            extract_to: Directory to extract files to
            
        Returns:
            DataFrame with combined data from all CSV files in the ZIP
        """
        if extract_to is None:
            extract_to = self.data_dir / 'extracted'
        
        extract_path = Path(extract_to)
        extract_path.mkdir(parents=True, exist_ok=True)
        
        # Extract ZIP contents
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        # Find and load CSV files
        dfs = []
        for root, dirs, files in os.walk(extract_path):
            for file in files:
                if file.endswith('.csv'):
                    file_path = os.path.join(root, file)
                    df = self.load_csv(file_path)
                    df['source_file'] = file
                    dfs.append(df)
        
        if not dfs:
            raise ValueError(f"No CSV files found in {zip_path}")
        
        return pd.concat(dfs, ignore_index=True)
    
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize column names to: date, open, high, low, close, volume.
        Handles various common naming conventions.
        """
        # Common column name mappings
        column_mappings = {
            'Date': 'date', 'DATE': 'date', 'Datetime': 'date', 'datetime': 'date',
            'Time': 'date', 'time': 'date', 'Timestamp': 'date', 'timestamp': 'date',
            'Open': 'open', 'OPEN': 'open', 'open_price': 'open', 'o': 'open',
            'High': 'high', 'HIGH': 'high', 'high_price': 'high', 'h': 'high',
            'Low': 'low', 'LOW': 'low', 'low_price': 'low', 'l': 'low',
            'Close': 'close', 'CLOSE': 'close', 'close_price': 'close', 
            'Adj Close': 'close', 'Adj_Close': 'close', 'c': 'close',
            'Volume': 'volume', 'VOLUME': 'volume', 'vol': 'volume', 'v': 'volume',
            'Symbol': 'symbol', 'SYMBOL': 'symbol', 'ticker': 'symbol',
        }
        
        # Rename columns
        df = df.rename(columns=column_mappings)
        
        # Ensure lowercase
        df.columns = df.columns.str.lower()
        
        # Parse date column if exists
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
        
        return df
    
    def validate_ohlcv(self, df: pd.DataFrame) -> bool:
        """
        Validate that DataFrame has required OHLCV columns.
        
        Returns:
            True if valid, raises ValueError otherwise
        """
        required_cols = ['date', 'open', 'high', 'low', 'close']
        missing = [col for col in required_cols if col not in df.columns]
        
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        # Check for NaN values in essential columns
        for col in required_cols:
            nan_count = df[col].isna().sum()
            if nan_count > 0:
                print(f"Warning: {nan_count} NaN values in {col} column")
        
        return True
    
    def get_symbols(self, df: pd.DataFrame) -> List[str]:
        """Get list of unique symbols in the data."""
        if 'symbol' in df.columns:
            return df['symbol'].unique().tolist()
        return []
    
    def filter_by_symbol(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Filter DataFrame to single symbol."""
        if 'symbol' not in df.columns:
            return df
        return df[df['symbol'] == symbol].reset_index(drop=True)
    
    def filter_by_date(self, df: pd.DataFrame, 
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Filter DataFrame by date range.
        
        Args:
            df: DataFrame with 'date' column
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)
        """
        if start_date:
            df = df[df['date'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['date'] <= pd.to_datetime(end_date)]
        return df.reset_index(drop=True)


def load_sample_data() -> pd.DataFrame:
    """
    Generate sample OHLCV data for testing when no data files available.
    Creates 252 trading days of synthetic price data.
    """
    import numpy as np
    
    np.random.seed(42)
    n_days = 252 * 2  # 2 years of trading days
    
    # Generate random walk for price
    returns = np.random.normal(0.0005, 0.02, n_days)
    prices = 100 * np.cumprod(1 + returns)
    
    # Generate OHLCV
    dates = pd.date_range(start='2024-01-01', periods=n_days, freq='B')
    
    data = {
        'date': dates,
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, n_days)),
        'high': prices * (1 + np.random.uniform(0, 0.02, n_days)),
        'low': prices * (1 - np.random.uniform(0, 0.02, n_days)),
        'close': prices,
        'volume': np.random.randint(100000, 10000000, n_days)
    }
    
    df = pd.DataFrame(data)
    
    # Ensure high is highest, low is lowest
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df
