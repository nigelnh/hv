import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Đọc file output
file_path = 'historical_volatility.xlsx'  # Thay bằng 'historical_volatility_with_spread.xlsx' nếu cần
df = pd.read_excel(file_path)

# Chuyển 'date' sang datetime nếu chưa
df['date'] = pd.to_datetime(df['date'])

# Sắp xếp theo date tăng dần (chronological order) để vẽ biểu đồ đúng thứ tự
df = df.sort_values('date')

# Các cột volatility cần plot (thêm/bớt tùy file của bạn)
vol_columns = ['hv_22', 'hv_66', 'hv_132', 'hv_252']  # Nếu có hv_126, thêm vào: ['hv_22', 'hv_66', 'hv_126', 'hv_132', 'hv_252']

# Tạo figure và axis
plt.figure(figsize=(12, 6))  # Kích thước biểu đồ

# Vẽ từng đường
colors = ['red', 'green', 'orange', 'purple']  # Màu tương tự hình: đỏ cho hv_22, xanh cho hv_66, vàng cho hv_132, tím cho hv_252
labels = ['HV 22', 'HV 66', 'HV 132', 'HV 252']  # Label cho legend

for i, col in enumerate(vol_columns):
    if col in df.columns:
        plt.plot(df['date'], df[col] * 100, color=colors[i % len(colors)], label=labels[i], linewidth=1.5)  # *100 để hiển thị dạng %

# Thiết lập tiêu đề và nhãn
plt.title('Historical Volatility - HPG', fontsize=14, fontweight='bold')
plt.xlabel('Date')
plt.ylabel('Historical Volatility (%)')
plt.grid(True, alpha=0.3)  # Lưới mờ
plt.legend(loc='upper left')  # Legend ở góc trên trái

# Xoay nhãn x-axis để dễ đọc
plt.xticks(rotation=45)

# Hiển thị biểu đồ
plt.tight_layout()  # Tự động điều chỉnh layout
plt.show()

# Lưu biểu đồ thành file PNG (tùy chọn)
plt.savefig('historical_volatility_chart.png', dpi=300, bbox_inches='tight')
print("Biểu đồ đã được vẽ và lưu thành 'historical_volatility_chart.png'")