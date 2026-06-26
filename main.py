import subprocess
import sys
import os
from get_all_stock_data import get_all_stock_data
from import_to_db import process_dataframe

def run_streamlit_ui():
    print(f"\n{'='*70}")
    print("STEP 3: Launching Streamlit UI Dashboard")
    print(f"{'='*70}\n")
    
    try:
        print("Opening Streamlit UI...")
        print("The interface should automatically open in your default browser.")
        print("\nTo stop the UI server, press Ctrl+C in this terminal.\n")
        
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "ui.py"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            check=True
        )
        
    except KeyboardInterrupt:
        print("\n\nStreamlit UI server stopped.")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Error running Streamlit UI!")
        print(f"Exit code: {e.returncode}")
    except Exception as e:
        print(f"\n[ERROR] Unknown error: {e}")

def main():
    # Step 1: Fetch stock data from API
    print(f"\n{'='*70}")
    print("STEP 1: Fetching Raw Stock Prices from KB Buddy API (VN30 Basket)")
    print(f"{'='*70}\n")
    
    symbols = [
        "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG", 
        "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB", 
        "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"
    ]
    import datetime
    from_date = "01/01/2022"
    to_date   = datetime.datetime.now().strftime('%d/%m/%Y')
    
    # Fetch data: It fetches from API, saves raw Parquet files, and returns df dict
    results = get_all_stock_data(symbols, from_date, to_date, delay=0.1)
    
    # Step 2: Compute Volatility & Save processed Parquet
    print(f"\n{'='*70}")
    print("STEP 2: Calculating Historical Volatility & Saving Processed Parquet")
    print(f"{'='*70}\n")
    
    success_count = 0
    for symbol, df in results.items():
        if df is not None and not df.empty:
            try:
                process_dataframe(symbol, df)
                success_count += 1
            except Exception as e:
                print(f"  [ERROR] Error processing symbol {symbol}: {e}")
    print(f"\n--- SUCCESS! Processed and saved {success_count}/{len(symbols)} symbols. ---\n")
    
    # Step 3: Start UI
    run_streamlit_ui()

if __name__ == "__main__":
    main()