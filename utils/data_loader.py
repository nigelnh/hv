"""
Data loading and processing utilities for HV Dashboard
Now uses PostgreSQL database instead of Excel files
"""
import pandas as pd
import numpy as np
from utils.db_connector import (
    get_available_symbols as db_get_symbols,
    load_symbol_data,
    load_multiple_symbols_data
)


def load_available_symbols():
    """
    Get list of available stock symbols from database.
    
    Returns:
        list: Sorted list of symbols
    """
    return db_get_symbols()


def load_stock_data(symbol):
    """
    Load historical volatility data from database for a given symbol.
    
    Args:
        symbol (str): Stock symbol (e.g., 'ACB', 'VNM')
    
    Returns:
        pd.DataFrame: DataFrame with HV data
    """
    df = load_symbol_data(symbol)
    
    if df.empty:
        raise FileNotFoundError(f"No data found in database for symbol {symbol}")
    
    # Add symbol column if not present
    if 'symbol' not in df.columns:
        df['symbol'] = symbol
    
    return df


def load_multiple_stocks_data(symbols):
    """
    Load data for multiple stocks efficiently from database.
    
    Args:
        symbols (list): List of stock symbols
    
    Returns:
        dict: Dictionary mapping symbol to its DataFrame
    """
    return load_multiple_symbols_data(symbols)


def calculate_volatility_cone(df, windows=None):
    """
    Calculate volatility cone data showing HV statistics across time windows.
    Uses pre-calculated HV data from database.
    
    Args:
        df (pd.DataFrame): DataFrame with HV columns
        windows (list): List of window sizes (default: [22, 66, 132, 252])
    
    Returns:
        pd.DataFrame: DataFrame with columns: window, min, max, mean, median, current
    """
    if windows is None:
        # Use the standard windows we have in the database
        windows = [22, 66, 132, 252]
    
    cone_data = {
        'window': [],
        'min': [],
        'max': [],
        'mean': [],
        'median': [],
        'current': []
    }
    
    # Map windows to column names
    window_map = {
        22: 'hv_22',
        66: 'hv_66',
        132: 'hv_132',
        252: 'hv_252'
    }
    
    for window in windows:
        col_name = window_map.get(window)
        if col_name and col_name in df.columns:
            hv = df[col_name] * 100  # Convert to percentage
            
            cone_data['window'].append(window)
            cone_data['min'].append(hv.min())
            cone_data['max'].append(hv.max())
            cone_data['mean'].append(hv.mean())
            cone_data['median'].append(hv.median())
            cone_data['current'].append(hv.iloc[-1] if len(hv) > 0 and not pd.isna(hv.iloc[-1]) else np.nan)
    
    return pd.DataFrame(cone_data)


def get_current_metrics(df):
    """
    Extract current HV metrics and statistics from database data.
    
    Args:
        df (pd.DataFrame): DataFrame with HV metrics from database
    
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
    
    # Get symbol from the dataframe
    symbol = latest_row.get('symbol', df['symbol'].iloc[0] if 'symbol' in df.columns else 'N/A')
    
    metrics = {
        'symbol': symbol,
        'latest_date': latest_row['tradingDate'],
        'current_price': 0.0,  # Price not stored in HV table, set to 0 or fetch separately if needed
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
