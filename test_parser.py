import sys
import os
sys.path.append(os.getcwd())
from src.data_loader import DataLoader
import pandas as pd

try:
    loader = DataLoader()
    print("Attempting to load CSV...")
    df = loader.load_csv('reproduce_issue.csv')
    print("Successfully loaded CSV.")
    print(df.head())
    print(df.dtypes)
except Exception as e:
    print(f"Error loading CSV: {e}")
    import traceback
    traceback.print_exc()
