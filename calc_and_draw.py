import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# Đọc file output
symbols = ['ACB', 'DGC', 'FPT', 'HDB', 'HPG', 'LPB', 'MBB', 'MSN', 'MWG', 'SHB', 'SSB', 'SSI', 'STB', 'TCB', 'TPB', 'VHM', 'VIB', 'VIC', 'VJC', 'VNM', 'VPB', 'VRE']

for symbol in symbols:
    file_path = f'data_output/{symbol}_01112024_to_03122025.xlsx'
    df = pd.read_excel(file_path)

    # Chuyển 'tradingDate' sang datetime
    df['tradingDate'] = pd.to_datetime(df['tradingDate'], dayfirst=True)

    # Sắp xếp theo date tăng dần
    df = df.sort_values('tradingDate').reset_index(drop=True)

    # Tính log returns từ close price
    df['log_return'] = np.log(df['closePriceAdjusted'] / df['closePriceAdjusted'].shift(1))

    # Định nghĩa các window cho historical volatility
    windows = {
        'hv_22': 22,   # ~1 tháng trading
        'hv_66': 66,   # ~3 tháng trading
        'hv_132': 132, # ~6 tháng trading
        'hv_252': 252  # ~1 năm trading
    }

    # Tính historical volatility cho mỗi window (annualized)
    # HV = std(log_returns) * sqrt(252) để annualize
    for col_name, window in windows.items():
        df[col_name] = df['log_return'].rolling(window=window).std() * np.sqrt(252)

    # Tạo figure và axis
    plt.figure(figsize=(12, 6))

    # Vẽ từng đường HV
    colors = ['red', 'green', 'orange', 'purple']
    labels = ['HV 22', 'HV 66', 'HV 132', 'HV 252']

    for i, (col_name, window) in enumerate(windows.items()):
        plt.plot(df['tradingDate'], df[col_name] * 100, 
                 color=colors[i], label=labels[i], linewidth=1.5)

    # Thiết lập tiêu đề và nhãn
    symbol = df['symbol'].iloc[0] if 'symbol' in df.columns else 'Stock'
    plt.title(f'Historical Volatility - {symbol}', fontsize=14, fontweight='bold')
    plt.xlabel('Date')
    plt.ylabel('Historical Volatility (%)')
    plt.grid(True, alpha=0.3)
    plt.legend(loc='upper left')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Lưu biểu đồ
    draw_folder = "draw_output"
    filepath = os.path.join(draw_folder, f'historical_volatility_chart_{symbol}.png')
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"Biểu đồ đã được lưu thành 'draw_output/historical_volatility_chart_{symbol}.png'")

    # # Hiển thị biểu đồ
    # plt.show()

