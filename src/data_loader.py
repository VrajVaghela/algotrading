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
        Handles various common naming conventions and cleaning.
        """
        # Clean up column names first
        df.columns = df.columns.str.strip().str.lower()
        
        # specific fix for "=""date""" styling from common Indian broker exports
        for col in df.columns:
            if df[col].dtype == object:
                # Remove "=""...""" pattern
                df[col] = df[col].astype(str).str.replace(r'[="]', '', regex=True)
        
        # Handle separate Date and Time columns
        if 'date' in df.columns and 'time' in df.columns:
            try:
                # Combine date and time
                df['date'] = pd.to_datetime(df['date'] + ' ' + df['time'])
                df = df.drop(columns=['time'])
            except Exception as e:
                print(f"Error combining date and time: {e}")

        # Common column name mappings
        column_mappings = {
            'datetime': 'date', 'timestamp': 'date',
            'open_price': 'open', 'o': 'open',
            'high_price': 'high', 'h': 'high',
            'low_price': 'low', 'l': 'low',
            'close_price': 'close', 'adj close': 'close', 'adj_close': 'close', 'c': 'close',
            'vol': 'volume', 'v': 'volume',
            'ticker': 'symbol'
        }
        
        # Rename columns (only if target doesn't exist to avoid duplicates)
        new_columns = {}
        for col in df.columns:
            if col in column_mappings:
                target = column_mappings[col]
                if target not in df.columns:
                     new_columns[col] = target
        
        df = df.rename(columns=new_columns)
        
        # Parse date column if exists and not already datetime
        if 'date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['date']):
            try:
                # Try explicit formats first for common Indian formats like DD-MM-YY
                df['date'] = pd.to_datetime(df['date'], dayfirst=True, errors='coerce')
            except:
                df['date'] = pd.to_datetime(df['date'])
            
            df = df.sort_values('date').reset_index(drop=True)
            # Drop rows with invalid dates
            df = df.dropna(subset=['date'])
        
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

    def detect_timeframe(self, df: pd.DataFrame) -> str:
        """
        Detect the likely timeframe of the data.
        
        Args:
            df: DataFrame with 'date' column
            
        Returns:
            String representing timeframe (e.g., '1m', '5m', '1h', '1d', '1w')
        """
        if 'date' not in df.columns or len(df) < 2:
            return 'unknown'
            
        # Calculate time differences between consecutive rows
        dates = pd.to_datetime(df['date'])
        diffs = dates.diff().dropna()
        
        if len(diffs) == 0:
            return 'unknown'
            
        # Get the most common time difference (median/mode)
        # using median is safer for occasional gaps
        median_diff = diffs.median()
        
        # Convert to seconds for easier comparison
        seconds = median_diff.total_seconds()
        
        if seconds < 60:
            return '1s'
        elif 55 <= seconds <= 65:
            return '1m'
        elif 290 <= seconds <= 310:
            return '5m'
        elif 890 <= seconds <= 910:
            return '15m'
        elif 1790 <= seconds <= 1810: 
            return '30m'
        elif 3500 <= seconds <= 3700:
            return '1h'
        elif 14000 <= seconds <= 14800: # 4 hours
            return '4h'
        elif 80000 <= seconds <= 90000: # ~1 day (allowing for variation)
            return '1d'
        elif 600000 <= seconds <= 610000: # ~1 week
            return '1w'
        else:
            # Fallback for other comparisons
            if seconds < 3600:
                return f"{int(seconds // 60)}m"
            elif seconds < 86400:
                return f"{int(seconds // 3600)}h"
            else:
                return f"{int(seconds // 86400)}d"


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
