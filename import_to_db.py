import pandas as pd
import numpy as np
import os
import glob
from collections import defaultdict

def calculate_hv(prices, window):
    """Calculate annualized historical volatility for a given window."""
    if len(prices) < window + 1:
        return pd.Series([np.nan] * len(prices))
    
    # Calculate daily log returns
    log_returns = np.log(prices / prices.shift(1))
    
    # Calculate rolling standard deviation of log returns
    # We multiply by sqrt(252) to annualize
    hv = log_returns.rolling(window=window).std() * np.sqrt(252)
    
    return hv

def process_dataframe(symbol, df):
    """Calculate HV and save directly as a processed Parquet file, bypassing the database."""
    if df is None or df.empty:
        print(f"  [SKIP] No data found for {symbol}")
        return
        
    # Basic validation and copy
    if 'close' not in df.columns or 'tradingDate' not in df.columns:
        print(f"  [ERROR] Missing required columns ('close', 'tradingDate') for {symbol}")
        return
        
    # Create a copy and parse dates
    full_df = df[['tradingDate', 'close']].copy()
    
    # Convert close price to numeric (SSI API returns them as strings)
    full_df['close'] = pd.to_numeric(full_df['close'], errors='coerce')
    
    # Check if tradingDate is already datetime or string
    if not pd.api.types.is_datetime64_any_dtype(full_df['tradingDate']):
        full_df['tradingDate'] = pd.to_datetime(full_df['tradingDate'], dayfirst=True)
    
    # Drop duplicates
    full_df = full_df.drop_duplicates(subset=['tradingDate'])
    full_df = full_df.sort_values('tradingDate').reset_index(drop=True)
    
    # Calculate HV for various windows (stored as decimals, e.g. 0.25 for 25% volatility)
    full_df['hv_22'] = calculate_hv(full_df['close'], 22)
    full_df['hv_66'] = calculate_hv(full_df['close'], 66)
    full_df['hv_132'] = calculate_hv(full_df['close'], 132)
    full_df['hv_252'] = calculate_hv(full_df['close'], 252)
    
    # Drop rows where we couldn't calculate at least the smallest window
    processed_df = full_df.dropna(subset=['hv_22']).copy()
    
    if processed_df.empty:
        print(f"  [WARN] No data left after HV calculation for {symbol} (need at least 23 days)")
        return
    
    # Add symbol column
    processed_df['symbol'] = symbol

    # Save to processed Parquet file
    data_folder = "data_output"
    os.makedirs(data_folder, exist_ok=True)
    filepath = os.path.join(data_folder, f"{symbol}_processed.parquet")
    
    try:
        processed_df.to_parquet(filepath, index=False, compression="snappy")
        print(f"  [OK] Successfully processed and saved {len(processed_df)} rows for {symbol} to {filepath}")
    except Exception as e:
        print(f"  [ERROR] Error saving processed data for {symbol}: {e}")

def process_symbol_data(symbol, files):
    """Consolidate data from multiple files for a symbol and import into database."""
    print(f"Processing symbol: {symbol} ({len(files)} files)")
    
    all_dfs = []
    for filepath in files:
        try:
            df = pd.read_parquet(filepath)  # Read Parquet instead of Excel
            # Basic validation
            if 'close' in df.columns and 'tradingDate' in df.columns:
                all_dfs.append(df[['tradingDate', 'close']])
            else:
                print(f"  [WARN] Skipping file {filepath}: Missing required columns")
        except Exception as e:
            print(f"  [ERROR] Error reading file {filepath}: {e}")
    
    if not all_dfs:
        print(f"  [SKIP] No valid data found for {symbol}")
        return

    # Consolidate
    consolidated_df = pd.concat(all_dfs)
    process_dataframe(symbol, consolidated_df)

def main():
    print("\n--- VOLATILITY PROCESSING START ---")
    
    data_folder = "data_output"
    if not os.path.exists(data_folder):
        print(f"Error: Folder {data_folder} not found.")
        return
        
    # Get all Parquet files, filtering out any already-processed files
    all_files = glob.glob(os.path.join(data_folder, "*.parquet"))
    raw_files = [f for f in all_files if "_processed" not in os.path.basename(f)]
    
    if not raw_files:
        print(f"No raw Parquet files found in {data_folder}/")
        return
        
    # Group files by symbol
    symbol_files = defaultdict(list)
    for filepath in raw_files:
        filename = os.path.basename(filepath)
        if "~$" in filename:
            continue
        symbol = filename.split('_')[0]
        symbol_files[symbol].append(filepath)
    
    print(f"Found {len(symbol_files)} unique symbols to process.")
    for symbol, files in symbol_files.items():
        process_symbol_data(symbol, files)
    
    print("--- VOLATILITY PROCESSING COMPLETE ---\n")

if __name__ == "__main__":
    main()
