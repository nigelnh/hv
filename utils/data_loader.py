"""
Data loading and processing utilities for HV Dashboard
"""
import os
import glob
import pandas as pd
import numpy as np


def load_available_symbols():
    """
    Scan data_output folder for available stock symbols.
    
    Returns:
        list: Sorted list of symbols
    """
    data_folder = "data_output"
    # Look for Excel files with the pattern {symbol}_*.xlsx
    data_files = glob.glob(os.path.join(data_folder, "*_*.xlsx"))
    
    symbols = []
    for filepath in data_files:
        filename = os.path.basename(filepath)
        # Extract symbol (everything before the first underscore)
        symbol = filename.split('_')[0]
        if symbol not in symbols:
            symbols.append(symbol)
    
    symbols.sort()
    return symbols


def load_stock_data(symbol):
    """
    Load stock data from Excel file for a given symbol.
    
    Args:
        symbol (str): Stock symbol (e.g., 'ACB', 'VNM')
    
    Returns:
        pd.DataFrame: DataFrame with stock data including HV metrics
    """
    # Find the data file for this symbol
    data_files = glob.glob(f'data_output/{symbol}_*.xlsx')
    
    if not data_files:
        raise FileNotFoundError(f"No data file found for symbol {symbol}")
    
    # Load the most recent file
    file_path = data_files[0]
    df = pd.read_excel(file_path)
    
    # Convert tradingDate to datetime
    df['tradingDate'] = pd.to_datetime(df['tradingDate'], dayfirst=True)
    
    # Sort by date
    df = df.sort_values('tradingDate').reset_index(drop=True)
    
    # Calculate HV metrics if not present
    if 'hv_22' not in df.columns:
        df = calculate_hv_metrics(df)
    
    return df


def calculate_hv_metrics(df):
    """
    Calculate Historical Volatility metrics for different time windows.
    
    Args:
        df (pd.DataFrame): DataFrame with stock price data
    
    Returns:
        pd.DataFrame: DataFrame with added HV columns
    """
    # Calculate log returns
    df['log_return'] = np.log(df['closePriceAdjusted'] / df['closePriceAdjusted'].shift(1))
    
    # Define windows for HV calculation
    windows = {
        'hv_22': 22,    # ~1 month
        'hv_66': 66,    # ~3 months
        'hv_132': 132,  # ~6 months
        'hv_252': 252   # ~1 year
    }
    
    # Calculate annualized HV for each window
    for col_name, window in windows.items():
        df[col_name] = df['log_return'].rolling(window=window).std() * np.sqrt(252)
    
    return df


def calculate_volatility_cone(df, windows=None):
    """
    Calculate volatility cone data showing HV statistics across time windows.
    
    Args:
        df (pd.DataFrame): DataFrame with log_return column
        windows (list): List of window sizes (default: [5,10,20,30,60,90,120,180,252])
    
    Returns:
        pd.DataFrame: DataFrame with columns: window, min, max, mean, median, current
    """
    if windows is None:
        windows = [5, 10, 20, 30, 60, 90, 120, 180, 252]
    
    cone_data = {
        'window': [],
        'min': [],
        'max': [],
        'mean': [],
        'median': [],
        'current': []
    }
    
    for window in windows:
        hv = df['log_return'].rolling(window=window).std() * np.sqrt(252) * 100
        
        cone_data['window'].append(window)
        cone_data['min'].append(hv.min())
        cone_data['max'].append(hv.max())
        cone_data['mean'].append(hv.mean())
        cone_data['median'].append(hv.median())
        cone_data['current'].append(hv.iloc[-1] if len(hv) > 0 and not pd.isna(hv.iloc[-1]) else np.nan)
    
    return pd.DataFrame(cone_data)


def get_current_metrics(df):
    """
    Extract current HV metrics and statistics.
    
    Args:
        df (pd.DataFrame): DataFrame with HV metrics
    
    Returns:
        dict: Dictionary containing current values and statistics
    """
    if df.empty:
        return None
    
    # Get the most recent row with valid data
    latest_row = df.dropna(subset=['hv_252']).iloc[-1] if not df.dropna(subset=['hv_252']).empty else df.iloc[-1]
    
    # Helper to calculate delta
    def calc_delta(current, mean):
        if pd.notna(current) and pd.notna(mean):
            return current - mean
        return np.nan
    
    metrics = {
        'symbol': latest_row['symbol'],
        'latest_date': latest_row['tradingDate'],
        'current_price': latest_row['closePriceAdjusted'],
        'hv_metrics': {
            'HV 22 (1M)': {
                'current': latest_row.get('hv_22', np.nan) * 100 if pd.notna(latest_row.get('hv_22')) else np.nan,
                'mean': df['hv_22'].mean() * 100 if 'hv_22' in df.columns else np.nan,
                'min': df['hv_22'].min() * 100 if 'hv_22' in df.columns else np.nan,
                'max': df['hv_22'].max() * 100 if 'hv_22' in df.columns else np.nan,
                'delta': calc_delta(
                    latest_row.get('hv_22', np.nan) * 100 if pd.notna(latest_row.get('hv_22')) else np.nan,
                    df['hv_22'].mean() * 100 if 'hv_22' in df.columns else np.nan
                ),
            },
            'HV 66 (3M)': {
                'current': latest_row.get('hv_66', np.nan) * 100 if pd.notna(latest_row.get('hv_66')) else np.nan,
                'mean': df['hv_66'].mean() * 100 if 'hv_66' in df.columns else np.nan,
                'min': df['hv_66'].min() * 100 if 'hv_66' in df.columns else np.nan,
                'max': df['hv_66'].max() * 100 if 'hv_66' in df.columns else np.nan,
                'delta': calc_delta(
                    latest_row.get('hv_66', np.nan) * 100 if pd.notna(latest_row.get('hv_66')) else np.nan,
                    df['hv_66'].mean() * 100 if 'hv_66' in df.columns else np.nan
                ),
            },
            'HV 132 (6M)': {
                'current': latest_row.get('hv_132', np.nan) * 100 if pd.notna(latest_row.get('hv_132')) else np.nan,
                'mean': df['hv_132'].mean() * 100 if 'hv_132' in df.columns else np.nan,
                'min': df['hv_132'].min() * 100 if 'hv_132' in df.columns else np.nan,
                'max': df['hv_132'].max() * 100 if 'hv_132' in df.columns else np.nan,
                'delta': calc_delta(
                    latest_row.get('hv_132', np.nan) * 100 if pd.notna(latest_row.get('hv_132')) else np.nan,
                    df['hv_132'].mean() * 100 if 'hv_132' in df.columns else np.nan
                ),
            },
            'HV 252 (1Y)': {
                'current': latest_row.get('hv_252', np.nan) * 100 if pd.notna(latest_row.get('hv_252')) else np.nan,
                'mean': df['hv_252'].mean() * 100 if 'hv_252' in df.columns else np.nan,
                'min': df['hv_252'].min() * 100 if 'hv_252' in df.columns else np.nan,
                'max': df['hv_252'].max() * 100 if 'hv_252' in df.columns else np.nan,
                'delta': calc_delta(
                    latest_row.get('hv_252', np.nan) * 100 if pd.notna(latest_row.get('hv_252')) else np.nan,
                    df['hv_252'].mean() * 100 if 'hv_252' in df.columns else np.nan
                ),
            },
        }
    }
    
    return metrics
