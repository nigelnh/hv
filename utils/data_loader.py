import pandas as pd
import numpy as np
import streamlit as st
import os
import glob
import datetime

DATA_FOLDER = "data_output"

def sync_latest_data():
    """
    Check if the latest data in the local Parquet files is older than the latest trading day (T-1).
    If older, automatically fetch the entire range from 01/01/2022 to today and recalculate HVs.
    This takes ~3-4 seconds total and runs seamlessly on startup.
    """
    from get_all_stock_data import get_all_stock_data
    from import_to_db import process_dataframe
    
    symbols = [
        "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG", 
        "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB", 
        "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"
    ]
    
    # Check latest date in ACB_processed.parquet
    test_filepath = os.path.join(DATA_FOLDER, "ACB_processed.parquet")
    if not os.path.exists(test_filepath):
        print("[SYNC] No processed data found. Initializing full pipeline...")
        return
        
    try:
        df_test = pd.read_parquet(test_filepath)
        if df_test.empty or 'tradingDate' not in df_test.columns:
            return
        df_test['tradingDate'] = pd.to_datetime(df_test['tradingDate'], dayfirst=True)
        latest_local_date = df_test['tradingDate'].max().date()
    except Exception as e:
        print(f"[SYNC] Error checking local file: {e}")
        return
        
    now = datetime.datetime.now()
    today = now.date()
    
    # Target date logic:
    # If weekend, target is last Friday.
    # If weekday: before 16:00, target is yesterday. After 16:00, target is today.
    if today.weekday() >= 5: # Saturday or Sunday
        days_to_subtract = 1 if today.weekday() == 5 else 2
        target_date = today - datetime.timedelta(days=days_to_subtract)
    else:
        if now.hour < 16:
            yesterday = today - datetime.timedelta(days=1)
            if yesterday.weekday() == 6:
                target_date = yesterday - datetime.timedelta(days=2)
            elif yesterday.weekday() == 5:
                target_date = yesterday - datetime.timedelta(days=1)
            else:
                target_date = yesterday
        else:
            target_date = today
            
    # Check if sync is needed
    if latest_local_date >= target_date:
        print(f"[SYNC] Data is up-to-date (Local: {latest_local_date}, Target: {target_date})")
        return
        
    print(f"[SYNC] Data is stale. Syncing from 01/01/2022 to {today.strftime('%d/%m/%Y')}...")
    
    # We use a streamlit spinner to notify the user
    try:
        with st.spinner("🔄 Syncing latest market data from SSI API..."):
            # Fetch from SSI (paginated fetch, using polite 0.05s delay to be safe and fast)
            results = get_all_stock_data(symbols, "01/01/2022", today.strftime('%d/%m/%Y'), delay=0.05)
            
            # Recalculate volatilities
            success_count = 0
            for symbol, df in results.items():
                if df is not None and not df.empty:
                    try:
                        process_dataframe(symbol, df)
                        success_count += 1
                    except Exception as e:
                        print(f"  [ERROR] Error processing {symbol}: {e}")
            print(f"[SYNC] Successfully synced and processed {success_count}/{len(symbols)} symbols.")
            
            # Clear streamlit cache to reload the new data!
            st.cache_data.clear()
    except Exception as e:
        print(f"[SYNC] Auto-sync failed: {e}")


DATA_FOLDER = "data_output"


@st.cache_data(ttl=600)
def load_available_symbols():
    """
    Get list of available stock symbols from local processed Parquet files.
    
    Returns:
        list: Sorted list of symbols
    """
    if not os.path.exists(DATA_FOLDER):
        return []
    
    # Processed files are named like '{symbol}_processed.parquet'
    pattern = os.path.join(DATA_FOLDER, "*_processed.parquet")
    files = glob.glob(pattern)
    
    symbols = []
    for filepath in files:
        filename = os.path.basename(filepath)
        symbol = filename.split('_')[0]
        symbols.append(symbol)
        
    return sorted(symbols)


@st.cache_data(ttl=600)
def load_stock_data(symbol):
    """
    Load historical volatility data from local processed Parquet file.
    
    Args:
        symbol (str): Stock symbol (e.g., 'ACB', 'VNM')
    
    Returns:
        pd.DataFrame: DataFrame with HV data
    """
    filepath = os.path.join(DATA_FOLDER, f"{symbol}_processed.parquet")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No processed data found for symbol {symbol}")
        
    df = pd.read_parquet(filepath)
    
    # Ensure tradingDate is datetime
    if 'tradingDate' in df.columns:
        df['tradingDate'] = pd.to_datetime(df['tradingDate'], dayfirst=True)
        
    # Ensure symbol column is present
    if 'symbol' not in df.columns:
        df['symbol'] = symbol
        
    return df


@st.cache_data(ttl=600)
def load_multiple_stocks_data(symbols):
    """
    Load data for multiple stocks efficiently from local processed Parquet files.
    
    Args:
        symbols (list): List of stock symbols
    
    Returns:
        dict: Dictionary mapping symbol to its DataFrame
    """
    results = {}
    for symbol in symbols:
        try:
            results[symbol] = load_stock_data(symbol)
        except Exception as e:
            print(f"Error loading {symbol}: {e}")
    return results


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
            hv = df[col_name] * 100
            
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


@st.cache_data(ttl=3600)
def load_vn30_index_data():
    """
    Fetch or load VN30 Index data from the public SSI API using pagination.
    """
    import requests
    import datetime
    import time
    
    today = datetime.datetime.now().strftime('%d/%m/%Y')
    url = "https://iboard-api.ssi.com.vn/statistics/company/ssmi/stock-info"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    all_data = []
    page = 1
    page_size = 40
    
    while True:
        params = {
            "symbol": "VN30",
            "page": page,
            "pageSize": page_size,
            "fromDate": "01/01/2022",
            "toDate": today
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code != 200:
                break
                
            json_data = response.json()
            if json_data.get('code') != 'SUCCESS' or not json_data.get('data'):
                break
                
            page_data = json_data['data']
            if len(page_data) == 0:
                break
                
            all_data.extend(page_data)
            
            paging = json_data.get('paging', {})
            total = paging.get('total', 0)
            
            if len(all_data) >= total or len(page_data) < page_size:
                break
                
            page += 1
            time.sleep(0.02)  # short polite delay
            
        except Exception as e:
            print(f"Error loading VN30 index page {page}: {e}")
            break
            
    if not all_data:
        return None
        
    df = pd.DataFrame(all_data)
    df['tradingDate'] = pd.to_datetime(df['tradingDate'], format='%d/%m/%Y')
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    return df[['tradingDate', 'close']].sort_values('tradingDate').reset_index(drop=True)


def calculate_stock_beta_and_da(stock_df):
    """
    Calculate stock's Beta and Directional Accuracy (DA) relative to VN30 Index.
    """
    vn30_df = load_vn30_index_data()
    if vn30_df is None or stock_df.empty:
        return 1.0, 0.5  # default fallbacks
        
    # Align both datasets on date
    stock_df = stock_df.copy()
    # Ensure tradingDate is datetime64[ns]
    stock_df['tradingDate'] = pd.to_datetime(stock_df['tradingDate'])
    vn30_df['tradingDate'] = pd.to_datetime(vn30_df['tradingDate'])
    
    # If the stock_df doesn't have a close price column, we try to load it from raw data, 
    # but actually the raw Parquet file has the close price! Let's check: 
    # Yes, get_all_stock_data saves raw files with close price, but import_to_db might drop it?
    # Wait! import_to_db saves:
    # df = df[['tradingDate', 'close', 'log_return', 'hv_22', 'hv_66', 'hv_132', 'hv_252']]
    # Yes! It keeps the 'close' price column! This is absolutely perfect!
    
    merged = pd.merge(
        stock_df[['tradingDate', 'close']], 
        vn30_df[['tradingDate', 'close']], 
        on='tradingDate', 
        suffixes=('_stock', '_vn30')
    ).sort_values('tradingDate')
    
    if len(merged) < 5:
        return 1.0, 0.5
        
    # Compute returns
    merged['ret_stock'] = np.log(merged['close_stock'] / merged['close_stock'].shift(1))
    merged['ret_vn30'] = np.log(merged['close_vn30'] / merged['close_vn30'].shift(1))
    merged = merged.dropna()
    
    if len(merged) < 5:
        return 1.0, 0.5
        
    # Beta
    cov = np.cov(merged['ret_stock'], merged['ret_vn30'])[0, 1]
    var = np.var(merged['ret_vn30'])
    beta = cov / var if var != 0 else 1.0
    
    # Directional Accuracy (DA)
    da = (np.sign(merged['ret_stock']) == np.sign(merged['ret_vn30'])).mean()
    
    return beta, da

