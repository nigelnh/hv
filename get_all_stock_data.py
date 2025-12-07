import requests
import pandas as pd
import time
import os

output_folder = "data_output"

def get_all_stock_data(symbols, from_date, to_date, delay=0.5):
    if isinstance(symbols, str):
        symbols = [symbols]
    
    results = {}
    
    for symbol in symbols:
        print(f"\n{'='*60}")
        print(f"Đang lấy dữ liệu cho mã: {symbol}")
        print(f"{'='*60}")
        
        url = "https://iboard-api.ssi.com.vn/statistics/company/ssmi/stock-info"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        all_data = []
        page = 1
        while True:
            params = {
                "symbol": symbol,
                "page": page,
                "pageSize": 40,
                "fromDate": from_date,
                "toDate": to_date
            }
            
            try:
                response = requests.get(url, params=params, headers=headers, timeout=10)
                if response.status_code != 200:
                    print(f"Lỗi {response.status_code} tại page {page}")
                    break
                    
                json_data = response.json()
                
                if json_data.get('code') != 'SUCCESS' or not json_data.get('data'):
                    print("Hết dữ liệu hoặc API lỗi:", json_data.get('message'))
                    break
                    
                page_data = json_data['data']
                if len(page_data) == 0:
                    print(f"Đã hết dữ liệu tại page {page}")
                    break
                    
                all_data.extend(page_data)
                total = json_data['paging']['total']
                print(f"Page {page}: lấy được {len(page_data)} dòng | Tổng cộng hiện tại: {len(all_data)} / ~{total}")
                
                if len(all_data) >= total:
                    print("Đã lấy đủ toàn bộ dữ liệu!")
                    break
                    
                page += 1
                time.sleep(delay)
                
            except Exception as e:
                print("Lỗi kết nối:", e)
                time.sleep(2)
                continue
        
        if not all_data:
            print(f"Không lấy được dữ liệu nào cho mã {symbol}!")
            results[symbol] = None
            continue
        
        df = pd.DataFrame(all_data)
        
        df['tradingDate'] = pd.to_datetime(df['tradingDate'], format='%d/%m/%Y')
        df = df.sort_values('tradingDate').reset_index(drop=True)
        df['tradingDate'] = df['tradingDate'].dt.strftime('%d/%m/%Y')
        
        # filename = f"{symbol}_{from_date.replace('/', '')}_to_{to_date.replace('/', '')}.xlsx"
        # df.to_excel(filename, index=False)
        # print(f"\nHOÀN TẤT! Đã lưu {len(df)} ngày giao dịch vào file: {filename}")
        filename = f"{symbol}_{from_date.replace('/', '')}_to_{to_date.replace('/', '')}.xlsx"
        filepath = os.path.join(output_folder, filename)
        df.to_excel(filepath, index=False)
        print(f"\nHOÀN TẤT! File được lưu tại: {filepath}")
        
        results[symbol] = df
    
    return results


if __name__ == "__main__":
    symbols = ["ACB", "DGC", "FPT", "HDB", "HPG", "LPB", "MBB", "MSN", "MWG", "SHB", "SSB", "SSI", "STB", "TCB", "TPB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"]
    from_date = "01/11/2024"
    to_date   = "03/12/2025"
    
    results = get_all_stock_data(symbols, from_date, to_date, delay=0.3)

    for symbol, df in results.items():
        if df is not None:
            print(f"\n{symbol}: {len(df)} ngày giao dịch")
            print("5 ngày gần nhất:")
            print(df[['tradingDate', 'open', 'close', 'volume', 'perPriceChange']].tail(5).to_string(index=False))
        else:
            print(f"\n{symbol}: Không có dữ liệu")
