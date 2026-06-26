import requests
import pandas as pd
import time
import os
import datetime

output_folder = "data_output"

def get_all_stock_data(symbols, from_date, to_date, delay=0.1):
    """
    Fetch historical stock data using the public SSI API with pagination.
    Saves raw Parquet files and returns a dictionary of DataFrames.
    """
    if isinstance(symbols, str):
        symbols = [symbols]
        
    results = {}
    url = "https://iboard-api.ssi.com.vn/statistics/company/ssmi/stock-info"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Format dates from DD-MM-YYYY or DD/MM/YYYY to DD/MM/YYYY for the SSI API
    sdate = from_date.replace('-', '/')
    edate = to_date.replace('-', '/')
    
    for symbol in symbols:
        print(f"\n{'='*60}")
        print(f"Fetching data from SSI API for symbol: {symbol}")
        print(f"{'='*60}")
        
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
                response = requests.get(url, params=params, headers=headers, timeout=15)
                if response.status_code != 200:
                    print(f"  [ERROR] HTTP {response.status_code} at page {page}")
                    break
                    
                json_data = response.json()
                if json_data.get('code') != 'SUCCESS' or not json_data.get('data'):
                    break
                    
                page_data = json_data['data']
                if len(page_data) == 0:
                    break
                    
                all_data.extend(page_data)
                
                # Check paging info
                paging = json_data.get('paging', {})
                total = paging.get('total', 0)
                print(f"  Page {page}: fetched {len(page_data)} rows | Total: {len(all_data)}/{total}")
                
                if len(all_data) >= total or len(page_data) < page_size:
                    break
                    
                page += 1
                time.sleep(delay)
                
            except Exception as e:
                print(f"  [ERROR] Connection error at page {page}: {e}")
                time.sleep(1)
                continue
                
        if not all_data:
            print(f"  [WARN] No data returned for {symbol}")
            results[symbol] = None
            continue
            
        # Convert to DataFrame
        df = pd.DataFrame(all_data)
        
        # Convert numeric columns
        for col in ['open', 'high', 'low', 'close']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        if 'volume' in df.columns:
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            
        # Format dates and sort chronologically
        df['tradingDate'] = pd.to_datetime(df['tradingDate'], format='%d/%m/%Y')
        df = df.sort_values('tradingDate').reset_index(drop=True)
        df['tradingDate'] = df['tradingDate'].dt.strftime('%d/%m/%Y')
        
        # Keep only standard columns
        df = df[['tradingDate', 'open', 'high', 'low', 'close', 'volume']]
        
        # Ensure output directory exists
        os.makedirs(output_folder, exist_ok=True)
        
        # Save as compressed Parquet file
        filename = f"{symbol}_{sdate.replace('/', '')}_to_{edate.replace('/', '')}.parquet"
        filepath = os.path.join(output_folder, filename)
        df.to_parquet(filepath, index=False, compression="snappy")
        print(f"  SUCCESS! File saved at: {filepath}")
        
        results[symbol] = df
        
    return results

if __name__ == "__main__":
    symbols = [
        "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG", 
        "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB", 
        "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"
    ]
    import datetime
    from_date = "01/01/2022"
    to_date   = datetime.datetime.now().strftime('%d/%m/%Y')
    
    results = get_all_stock_data(symbols, from_date, to_date, delay=0.1)
    
    # Print sample output for validation
    for symbol, df in results.items():
        if df is not None:
            print(f"\n{symbol}: {len(df)} trading days")
            print("5 most recent days:")
            print(df[['tradingDate', 'open', 'close', 'volume']].tail(5).to_string(index=False))
            break
