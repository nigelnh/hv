import streamlit as st
from datetime import datetime
from utils.data_loader import sync_latest_data, load_available_symbols, load_stock_data, get_current_metrics
from utils.ui_components import (
    apply_custom_css,
    render_header,
    render_hv_chart_plotly,
    render_volatility_cone,
    render_hv_distribution,
    render_risk_metrics_card,
    render_peer_correlation_card,
    render_multi_stock_comparison
)

# Page configuration
st.set_page_config(
    layout="wide",
    initial_sidebar_state="collapsed",
    page_title="HV Pro Terminal"
)

# Run T-1 Automatic Data Sync on Startup!
# This checks if local Parquet files are stale, and if so, runs a quick 3s background pull from KB Buddy.
sync_latest_data()

# Apply custom styling
apply_custom_css()

# Load available symbols
symbols = load_available_symbols()

if not symbols:
    st.error("""
    ❌ No processed stock data found in the `data_output` folder!
    Please run the full pipeline to fetch raw stock price data and calculate historical volatilities.
    """)
    st.stop()

# Session states
if 'selected_symbol' not in st.session_state:
    st.session_state.selected_symbol = symbols[0]

if 'selected_stocks' not in st.session_state:
    st.session_state.selected_stocks = ["FPT", "HPG", "VPB"] # default comparison basket

# Master Tabs (Overview with Green Badge)
tab_overview, tab_comparison = st.tabs([
    "Overview 🟢", 
    "Peer Correlation 📊"
])

with tab_overview:
    current_symbol = st.session_state.selected_symbol
    try:
        df = load_stock_data(current_symbol)
        metrics = get_current_metrics(df)
        
        # Render Premium Header (Symbol, session info, and live ticking clock)
        render_header(
            metrics['symbol'],
            metrics['latest_date'],
            metrics['current_price']
        )
        
        # -----------------------------------------------------------------
        # BENTO GRID LAYOUT
        # -----------------------------------------------------------------
        
        # Bento Row 1: Timeline (8/12) & Volatility Cone (4/12)
        row1_col1, row1_col2 = st.columns([8, 4])
        
        with row1_col1:
            # Cell A: Timeline Chart & selector controls
            # Captures the filtered dataframe from date controls inside the card
            df_filtered = render_hv_chart_plotly(df, current_symbol, symbols)
            
        with row1_col2:
            # Cell B: Term Structure Volatility Cone
            render_volatility_cone(df, current_symbol)
            
        st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)
        
        # Bento Row 2: Distribution (4/12), Risk Metrics (4/12), Peer Correlation (4/12)
        row2_col1, row2_col2, row2_col3 = st.columns([4, 4, 4])
        
        with row2_col1:
            # Cell C: Volatility Distribution Density
            render_hv_distribution(df, current_symbol)
            
        with row2_col2:
            # Cell D: High-Density Risk KPI Stats
            render_risk_metrics_card(df, metrics)
            
        with row2_col3:
            # Cell E: Peer Correlation, Beta & Directional Accuracy vs VN30
            render_peer_correlation_card(current_symbol, df)
            
    except FileNotFoundError as e:
        st.error(f"❌ {str(e)}")
    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")
        st.exception(e)

with tab_comparison:
    st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
    # Render comparative overlay, full 30-stock heatmap, and stats matrix
    render_multi_stock_comparison(st.session_state.selected_stocks, symbols)
