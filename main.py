import subprocess
import sys
import os

def run_script(script_name, description):
    print(f"\n{'='*70}")
    print(f"{description}")
    print(f"{'='*70}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            check=True,
            capture_output=False
        )
        
        print(f"\n{description} - HOÀN TẤT!\n")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Lỗi khi chạy {script_name}!")
        print(f"Exit code: {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"\n❌ Không tìm thấy file: {script_name}")
        return False
    except Exception as e:
        print(f"\n❌ Lỗi không xác định: {e}")
        return False

def run_streamlit_ui():
    print(f"\n{'='*70}")
    print("BƯỚC 3: Khởi động giao diện Streamlit UI")
    print(f"{'='*70}\n")
    
    try:
        print("Đang mở Streamlit UI...")
        print("Giao diện sẽ tự động mở trong trình duyệt của bạn")
        print("\nĐể dừng UI, nhấn Ctrl+C trong terminal\n")
        
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "ui.py"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            check=True
        )
        
    except KeyboardInterrupt:
        print("\n\n Đã đóng Streamlit UI")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Lỗi khi chạy Streamlit UI!")
        print(f"Exit code: {e.returncode}")
    except Exception as e:
        print(f"\n❌ Lỗi không xác định: {e}")

def main():
    print("\n" + "="*70)
    print("CHƯƠNG TRÌNH TỰ ĐỘNG HÓA: LẤY DỮ LIỆU & VẼ BIỂU ĐỒ HV")
    print("="*70)
    
    success = run_script(
        "get_all_stock_data.py",
        "BƯỚC 1: Lấy dữ liệu chứng khoán từ API"
    )
    
    if not success:
        print("\n⚠️  Dừng chương trình do lỗi ở bước 1")
        sys.exit(1)
    
    success = run_script(
        "calc_and_draw.py",
        "BƯỚC 2: Tính toán và vẽ biểu đồ Historical Volatility"
    )
    
    if not success:
        print("\n⚠️  Dừng chương trình do lỗi ở bước 2")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("HOÀN TẤT CÁC BƯỚC XỬ LÝ DỮ LIỆU!")
    print("="*70)
    print("Dữ liệu được lưu tại: data_output/")
    print("Biểu đồ được lưu tại: draw_output/")
    print("="*70 + "\n")
    
    run_streamlit_ui()

if __name__ == "__main__":
    main()