"""
HV Dashboard - Main Application
Professional Streamlit UI for Historical Volatility Analysis
"""
import streamlit as st
from datetime import datetime, timedelta
from utils.data_loader import load_available_symbols, load_stock_data, get_current_metrics
from utils.ui_components import (
    apply_custom_css,
    render_header,
    render_hv_chart_plotly,
    render_quick_stats_cards,
    render_volatility_cone,
    render_hv_distribution,
    render_multi_stock_comparison
)

# Page configuration
st.set_page_config(
    layout="wide",
    initial_sidebar_state="collapsed",
    page_title="HV Pro Terminal"
)

# Apply custom styling
apply_custom_css()

# Load available symbols
symbols = load_available_symbols()

if not symbols:
    st.error("❌ No data files found in data_output folder. Please run the data generation scripts first.")
    st.stop()

# Stock selector (will be rendered inline with chart title)
if 'selected_symbol' not in st.session_state:
    st.session_state.selected_symbol = symbols[0]

# Multi-stock comparison mode
if 'selected_stocks' not in st.session_state:
    st.session_state.selected_stocks = [symbols[0]]

if 'comparison_mode' not in st.session_state:
    st.session_state.comparison_mode = False

selected_tab = "Historical Volatility"  # Default tab

# Load data based on mode
try:
    if st.session_state.comparison_mode and len(st.session_state.selected_stocks) > 1:
        # Multi-stock comparison mode
        from utils.ui_components import render_multi_stock_comparison
        render_multi_stock_comparison(st.session_state.selected_stocks, symbols)
    else:
        # Single stock mode
        current_symbol = st.session_state.selected_stocks[0] if st.session_state.comparison_mode else st.session_state.selected_symbol
        df = load_stock_data(current_symbol)
        metrics = get_current_metrics(df)
        
        # Header Section
        render_header(
            metrics['symbol'],
            metrics['latest_date'],
            metrics['current_price']
        )
        
        # ---------------------------------------------------------
        # MAIN GRID LAYOUT
        # ---------------------------------------------------------
        
        # Row 1: Main Chart with integrated controls
        render_hv_chart_plotly(df, current_symbol, symbols)

        col_r1_c1, col_r1_c2 = st.columns([1, 1])

        with col_r1_c1:
            # Quick Stats and Distribution
            render_quick_stats_cards(metrics)
            render_hv_distribution(df, current_symbol)

        with col_r1_c2:
            # Volatility Cone
            render_volatility_cone(df, current_symbol)
            
except FileNotFoundError as e:
    st.error(f"❌ {str(e)}")
except Exception as e:
    st.error(f"❌ Error loading data: {str(e)}")
    st.exception(e)


