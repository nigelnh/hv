import requests
import pandas as pd
import numpy as np
import time
import sys
from datetime import datetime

# Configure output encoding for Windows consoles
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# --- Configurations ---
stock_tickers = ["FPT", "HPG", "MWG", "STB", "TPB", "VHM", "VIC", "VNM", "VPB", "VRE"]
index_symbols = ["VN30", "VNINDEX"]
start_date = "2025-01-01"
end_date = "2025-12-31"

# --- SSI API Fetcher ---
def fetch_price(symbol, start_date, end_date):
    """
    Fetch historical prices from the public SSI API using pagination.
    Converts dates from YYYY-MM-DD to DD/MM/YYYY.
    """
    # Convert dates from YYYY-MM-DD to DD/MM/YYYY
    sdate = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    edate = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    
    url = "https://iboard-api.ssi.com.vn/statistics/company/ssmi/stock-info"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    all_data = []
    page = 1
    page_size = 40
    
    while True:
        params = {
            "symbol": symbol,
            "page": page,
            "pageSize": page_size,
            "fromDate": sdate,
            "toDate": edate
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"[!] HTTP {response.status_code} at page {page} for {symbol}")
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
            time.sleep(0.05)  # polite delay
            
        except Exception as e:
            print(f"[!] Connection error for {symbol} at page {page}: {e}")
            break
            
    if not all_data:
        print(f"[!] No data returned for {symbol}")
        return None
        
    df = pd.DataFrame(all_data)
    
    # Convert date to datetime index
    df["tradingDate"] = pd.to_datetime(df["tradingDate"], format='%d/%m/%Y')
    
    # Convert close price to float
    df["close"] = pd.to_numeric(df["close"], errors='coerce')
    
    # Set display name (e.g. VN30INDEX for VN30)
    is_index = symbol in ["VN30", "VNINDEX"]
    display_name = f"{symbol}INDEX" if is_index else symbol
    
    df = df[["tradingDate", "close"]].rename(columns={"close": display_name})
    return df.set_index("tradingDate")

# --- Main Data Pipeline ---
def main():
    print(f"\n--- UNDERLYING CORRELATION PIPELINE ---")
    print(f"Timeframe: {start_date} to {end_date}")
    
    all_price_df = pd.DataFrame()
    
    # 1. Fetch Stock Data
    print("\nFetching stock price data...")
    for symbol in stock_tickers:
        df = fetch_price(symbol, start_date, end_date)
        if df is not None:
            all_price_df = df if all_price_df.empty else all_price_df.join(df, how="outer")
            print(f"[OK] Fetched data for: {symbol}")
        time.sleep(0.1)
        
    # 2. Fetch Index Data
    print("\nFetching index data...")
    for symbol in index_symbols:
        df = fetch_price(symbol, start_date, end_date)
        if df is not None:
            all_price_df = all_price_df.join(df, how="outer")
            print(f"[OK] Fetched index data for: {symbol}")
        time.sleep(0.1)
        
    if all_price_df.empty:
        print("[ERROR] No data fetched at all. Aborting.")
        return
        
    # --- Calculate log return & correlation ---
    all_price_df = all_price_df.sort_index()
    log_returns = np.log(all_price_df / all_price_df.shift(1)).dropna()
    correlation_matrix = log_returns.corr()
    
    # --- Heatmap Output ---
    print("\n📈 Correlation Matrix (Log Returns):")
    print(correlation_matrix.round(3))
    
    # ====================================================
    # 🔹 Beta (Relative to VN30INDEX)
    # ====================================================
    if "VN30INDEX" in log_returns.columns:
        vn30_returns = log_returns["VN30INDEX"]
        betas = {}
    
        for column in log_returns.columns:
            if column in ["VN30INDEX", "VNINDEXINDEX"]:
                continue
            # Ensure we have aligned data
            valid_idx = log_returns[column].notna() & vn30_returns.notna()
            if valid_idx.sum() > 1:
                cov = np.cov(log_returns[column][valid_idx], vn30_returns[valid_idx])[0, 1]
                var = np.var(vn30_returns[valid_idx])
                beta = cov / var if var != 0 else np.nan
                betas[column] = beta
    
        beta_df = pd.DataFrame.from_dict(betas, orient="index", columns=["Beta vs VN30INDEX"])
        print("\n📊 Beta Coefficients vs VN30INDEX:")
        print(beta_df.sort_values(by="Beta vs VN30INDEX", ascending=False).round(3))
    
    # ====================================================
    # 🔹 Pearson Reliability (Using scipy if available, fallback otherwise)
    # ====================================================
    if "VPB" in log_returns.columns and "VN30INDEX" in log_returns.columns:
        aligned = log_returns[["VPB", "VN30INDEX"]].dropna()
        if len(aligned) > 1:
            try:
                from scipy.stats import pearsonr
                r, p_value = pearsonr(aligned["VPB"], aligned["VN30INDEX"])
                print(f"\n📌 Pearson Reliability (VPB vs VN30INDEX):")
                print(f"   Pearson Correlation: {r:.4f}")
                print(f"   p-value: {p_value:.4e}")
            except ImportError:
                # Fallback to numpy if scipy is not installed yet
                r = np.corrcoef(aligned["VPB"], aligned["VN30INDEX"])[0, 1]
                print(f"\n📌 Pearson Reliability (VPB vs VN30INDEX) [Numpy Fallback]:")
                print(f"   Pearson Correlation: {r:.4f}")
    
    # ====================================================
    # 🔹 Directional Accuracy (DA) relative to VN30INDEX
    # ====================================================
    def calc_directional_accuracy(x, y):
        return (np.sign(x) == np.sign(y)).mean()
    
    if "VN30INDEX" in log_returns.columns:
        directional_accuracy = {}
        for column in log_returns.columns:
            if column in ["VN30INDEX", "VNINDEXINDEX"]:
                continue
            da = calc_directional_accuracy(log_returns[column], vn30_returns)
            directional_accuracy[column] = da
    
        da_df = pd.DataFrame.from_dict(directional_accuracy, orient="index", columns=["Directional Accuracy"])
        print("\n📊 Directional Accuracy (relative to VN30INDEX):")
        print(da_df.sort_values(by="Directional Accuracy", ascending=False).round(3))
        
    print("\n--- PIPELINE COMPLETE ---\n")

if __name__ == "__main__":
    main()