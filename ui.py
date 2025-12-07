import streamlit as st
import os
import glob

chart_folder = "draw_output"
chart_pattern = os.path.join(chart_folder, "historical_volatility_chart_*.png")
chart_files = glob.glob(chart_pattern)

symbols = []
chart_dict = {}
for filepath in chart_files:
    filename = os.path.basename(filepath)
    symbol = filename.replace("historical_volatility_chart_", "").replace(".png", "")
    symbols.append(symbol)
    chart_dict[symbol] = filepath
    
symbols.sort()
    
selected_symbol = st.sidebar.selectbox(
    "Choose a stock symbol:",
    symbols,
    index=0
)
    
if selected_symbol in chart_dict:
    st.subheader(f"Historical Volatility - {selected_symbol}")
    st.image(chart_dict[selected_symbol], use_container_width=False)
else:
    st.error(f"Chart not found for {selected_symbol}")
