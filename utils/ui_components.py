"""
Reusable UI components for HV Dashboard
"""
import streamlit as st
import pandas as pd
import numpy as np


def apply_custom_css():
    """Apply custom CSS for professional dark terminal theme."""
    st.markdown("""
        <style>
        /* Main container styling */
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 100%;
        }
        
        /* High-density metrics styling */
        [data-testid="stMetric"] {
            background-color: #1e293b;
            padding: 10px;
            border-radius: 4px;
            border: 1px solid #334155;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.8rem !important;
        }

        [data-testid="stMetricLabel"] {
        [data-testid="stVerticalBlockBorderWrapper"]:has(h1) {
            padding-bottom: 0 !important;
        }
        
        /* Subheader styling */
        h2 {
            color: #f1f5f9;
            font-weight: 600;
        }
        
        h3 {
            color: #cbd5e1;
            font-weight: 600;
        }
        
        /* Table styling */
        [data-testid="stDataFrame"] {
            font-size: 0.95rem;
        }
        
        /* Tabs styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            font-size: 1.1rem;
            font-weight: 600;
            padding: 0.75rem 1.5rem;
        }
        
        /* Improve spacing */
        .element-container {
            /* margin-bottom: 1rem; */
        }
        
        /* Container borders - same as background color*/
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #334155 !important;
        }
        
        /* Make insights container fill height */
        .insights-fill {
            /* height: 100%; */
            display: flex;
            flex-direction: column;
        }
        </style>
    """, unsafe_allow_html=True)


def render_header(symbol, latest_date, current_price=None):
    """
    Render the main header with stock information.
    
    Args:
        symbol (str): Stock symbol
        latest_date: Latest trading date
        current_price (float, optional): Current stock price (not used with database)
    """
    with st.container(border=True):
        col1, col2 = st.columns([6, 1])
        with col1:
            st.title(f"{symbol} - Historical Volatility Trend")
        
        with col2:
            st.metric("Latest Date", latest_date.strftime("%d/%m/%Y") if hasattr(latest_date, 'strftime') else str(latest_date))

def render_quick_stats_cards(metrics):
    """
    Render key statistics in card layout with deltas vs mean.
    
    Args:
        metrics (dict): Dictionary containing HV metrics
    """
    with st.container(border=True):        
        col1, col2, col3, col4 = st.columns(4)
        
        hv_metrics = metrics['hv_metrics']
        
        periods = ['HV 22 (1M)', 'HV 66 (3M)', 'HV 132 (6M)', 'HV 252 (1Y)']
        labels = ['HV 22 (1 Month)', 'HV 66 (3 Months)', 'HV 132 (6 Months)', 'HV 252 (1 Year)']
        
        for col, period, label in zip([col1, col2, col3, col4], periods, labels):
            with col:
                data = hv_metrics[period]
                current = data['current']
                delta = data.get('delta', np.nan)
                
                st.metric(
                    label,
                    f"{current:.2f}%" if not np.isnan(current) else "N/A",
                    delta=f"{delta:+.2f}% vs avg" if not np.isnan(delta) else None,
                    delta_color="inverse"  # Red when volatility increases
                )


def render_hv_chart_plotly(df, symbol, symbols, start_date=None, end_date=None):
    """
    Render interactive HV chart using Plotly.
    
    Args:
        df (pd.DataFrame): DataFrame with HV metrics and tradingDate
        symbol (str): Stock symbol
        symbols (list): List of available stock symbols
        start_date: Start date for filtering
        end_date: End date for filtering
    """
    import plotly.graph_objects as go
    
    with st.container(border=True):
        # Title, comparison toggle, stock selector, and date filters on the same line
        col_mode, col_selector, col_date1, col_date2 = st.columns([4, 1, 1, 1])
        
        with col_mode:
            comparison_mode = st.toggle(
                "Compare",
                value=st.session_state.comparison_mode,
                key="comparison_toggle",
                help="Enable multi-stock comparison"
            )
            if comparison_mode != st.session_state.comparison_mode:
                st.session_state.comparison_mode = comparison_mode
                st.rerun()
        
        with col_selector:
            if st.session_state.comparison_mode:
                # Multi-select mode
                selected_stocks = st.multiselect(
                    "Select Stocks",
                    symbols,
                    default=st.session_state.selected_stocks if st.session_state.selected_stocks else [symbols[0]],
                    key="stock_multiselect",
                    label_visibility="collapsed",
                    max_selections=5
                )
                if selected_stocks and selected_stocks != st.session_state.selected_stocks:
                    st.session_state.selected_stocks = selected_stocks
                    st.rerun()
            else:
                # Single select mode
                selected = st.selectbox(
                    "Select Stock",
                    symbols,
                    index=symbols.index(symbol) if symbol in symbols else 0,
                    key="stock_selector",
                    label_visibility="collapsed"
                )
                # Update session state if selection changed
                if selected != st.session_state.selected_symbol:
                    st.session_state.selected_symbol = selected
                    st.rerun()
        
        # Date filters
        min_date = df['tradingDate'].min().date()
        max_date = df['tradingDate'].max().date()
        
        with col_date1:
            start_date_input = st.date_input(
                "Start Date",
                value=start_date if start_date else min_date,
                min_value=min_date,
                max_value=max_date,
                format="DD/MM/YYYY",
                key="chart_start_date",
                label_visibility="collapsed"
            )
        
        with col_date2:
            end_date_input = st.date_input(
                "End Date",
                value=end_date if end_date else max_date,
                min_value=min_date,
                max_value=max_date,
                format="DD/MM/YYYY",
                key="chart_end_date",
                label_visibility="collapsed"
            )
        
        # Filter data based on date range
        df_filtered = df[
            (df['tradingDate'].dt.date >= start_date_input) & 
            (df['tradingDate'].dt.date <= end_date_input)
        ]
        
        # Use filtered data for chart
        chart_df = df_filtered if not df_filtered.empty else df
        
        # Check if HV data exists
        if chart_df.empty or 'hv_252' not in chart_df.columns:
            st.error(f"No HV data available for {symbol}")
            return
        
        # Color palette matching matplotlib version
        colors = {
            'hv_22': '#ef4444',   # Red
            'hv_66': '#f59e0b',   # Amber
            'hv_132': '#10b981',  # Emerald
            'hv_252': '#8b5cf6'   # Purple
        }
        
        labels = {
            'hv_22': 'HV 22 (1M)',
            'hv_66': 'HV 66 (3M)',
            'hv_132': 'HV 132 (6M)',
            'hv_252': 'HV 252 (1Y)'
        }
        
        # Create figure
        fig = go.Figure()
        
        # Add traces for each HV period
        for col in ['hv_22', 'hv_66', 'hv_132', 'hv_252']:
            if col in chart_df.columns:
                fig.add_trace(go.Scatter(
                    x=chart_df['tradingDate'],
                    y=chart_df[col] * 100,  # Convert to percentage
                    name=labels[col],
                    line=dict(color=colors[col], width=2.5),
                    mode='lines',
                    hovertemplate='<b>%{fullData.name}</b><br>' +
                                  'Date: %{x|%Y-%m-%d}<br>' +
                                  'HV: %{y:.2f}%<extra></extra>'
                ))
        
        # Update layout with dark theme
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='#0f172a',
            plot_bgcolor='#0f172a',
            font=dict(color='#f1f5f9', size=11),
            showlegend=True,
            legend=dict(
                orientation='v',
                yanchor='top',
                y=0.99,
                xanchor='left',
                x=0.01,
                bgcolor='rgba(30, 41, 59, 0.95)',
                bordercolor='#334155',
                borderwidth=1,
                font=dict(size=11)
            ),
            xaxis=dict(
                title=dict(
                    text='Date',
                    font=dict(size=12, color='#f1f5f9')
                ),
                gridcolor='rgba(51, 65, 85, 0.15)',
                gridwidth=0.8,
                showgrid=True,
                zeroline=False,
                color='#f1f5f9'
            ),
            yaxis=dict(
                title=dict(
                    text='Historical Volatility (%)',
                    font=dict(size=12, color='#f1f5f9')
                ),
                gridcolor='rgba(51, 65, 85, 0.15)',
                gridwidth=0.8,
                showgrid=True,
                zeroline=False,
                color='#f1f5f9'
            ),
            hovermode='x unified',
            height=600,
            margin=dict(l=60, r=40, t=20, b=60)
        )
        
        # Display the chart
        st.plotly_chart(fig, use_container_width=True, key=f"hv_chart_{symbol}")

def render_volatility_cone(df, symbol):
    """
    Render Plotly volatility cone chart showing HV term structure.
    
    Args:
        df (pd.DataFrame): DataFrame with log_return column
        symbol (str): Stock symbol
    """
    import plotly.graph_objects as go
    from utils.data_loader import calculate_volatility_cone
    
    with st.container(border=True):
        st.subheader("Volatility Cone")
        
        # Calculate cone data
        cone = calculate_volatility_cone(df)
        
        if cone.empty:
            st.warning("No data available for volatility cone")
            return
        
        # Create Plotly figure
        fig = go.Figure()
        
        # Max line (top of cone)
        fig.add_trace(go.Scatter(
            x=cone['window'],
            y=cone['max'],
            name='Historical Max',
            line=dict(color='rgba(239, 68, 68, 0.5)', width=1.5),
            fill=None,
            mode='lines',
            hovertemplate='Window: %{x} days<br>Max: %{y:.2f}%<extra></extra>'
        ))
        
        # Min line (bottom of cone) - fill between max and min
        fig.add_trace(go.Scatter(
            x=cone['window'],
            y=cone['min'],
            name='Historical Min',
            line=dict(color='rgba(16, 185, 129, 0.5)', width=1.5),
            fill='tonexty',  # Fill to previous trace (max)
            fillcolor='rgba(100, 116, 139, 0.15)',
            mode='lines',
            hovertemplate='Window: %{x} days<br>Min: %{y:.2f}%<extra></extra>'
        ))
        
        # Mean line
        fig.add_trace(go.Scatter(
            x=cone['window'],
            y=cone['mean'],
            name='Historical Mean',
            line=dict(color='#60a5fa', width=2.5, dash='dash'),
            mode='lines',
            hovertemplate='Window: %{x} days<br>Mean: %{y:.2f}%<extra></extra>'
        ))
        
        # Current HV markers
        fig.add_trace(go.Scatter(
            x=cone['window'],
            y=cone['current'],
            name='Current HV',
            mode='markers+lines',
            marker=dict(size=12, color='#fbbf24', symbol='diamond', line=dict(width=2, color='#0f172a')),
            line=dict(color='#fbbf24', width=2.5),
            hovertemplate='Window: %{x} days<br>Current: %{y:.2f}%<extra></extra>'
        ))
        
        # Update layout with dark theme
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='#0f172a',
            plot_bgcolor='#0f172a',
            font=dict(color='#f1f5f9', size=11),
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1,
                bgcolor='rgba(30, 41, 59, 0.8)',
                bordercolor='#334155',
                borderwidth=1
            ),
            xaxis=dict(
                title=dict(
                    text='Time Window (Days)',
                    font=dict(size=12, color='#f1f5f9')
                ),
                gridcolor='rgba(51, 65, 85, 0.15)',
                gridwidth=0.8,
                showgrid=True,
                zeroline=False,
                color='#f1f5f9',
                tickmode='array',
                tickvals=cone['window'].tolist()
            ),
            yaxis=dict(
                title=dict(
                    text='Historical Volatility (%)',
                    font=dict(size=12, color='#f1f5f9')
                ),
                gridcolor='rgba(51, 65, 85, 0.15)',
                gridwidth=0.8,
                showgrid=True,
                zeroline=False,
                color='#f1f5f9'
            ),
            hovermode='x unified',
            height=500,
            margin=dict(l=60, r=40, t=60, b=60)
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"vol_cone_{symbol}")


def render_hv_distribution(df, symbol):
    """
    Render HV distribution chart (Histogram/Box plot).
    """
    import plotly.graph_objects as go
    
    with st.container(border=True):
        st.subheader("HV Distribution")
        
        if df.empty:
            st.warning("No data available")
            return

        # Get current HV values
        current_hv = {
            'hv_22': df['hv_22'].iloc[-1] * 100 if not pd.isna(df['hv_22'].iloc[-1]) else 0,
            'hv_66': df['hv_66'].iloc[-1] * 100 if not pd.isna(df['hv_66'].iloc[-1]) else 0,
            'hv_132': df['hv_132'].iloc[-1] * 100 if not pd.isna(df['hv_132'].iloc[-1]) else 0,
            'hv_252': df['hv_252'].iloc[-1] * 100 if not pd.isna(df['hv_252'].iloc[-1]) else 0
        }
        
        fig = go.Figure()
        
        # Colors for different periods
        colors = {'hv_22': '#ef4444', 'hv_66': '#f59e0b', 'hv_132': '#10b981', 'hv_252': '#8b5cf6'}
        labels = {'hv_22': 'HV 22', 'hv_66': 'HV 66', 'hv_132': 'HV 132', 'hv_252': 'HV 252'}
        
        # Add box plots for each period
        for col in ['hv_252', 'hv_132', 'hv_66', 'hv_22']: # Reverse order for display
            if col in df.columns:
                # Box plot for distribution
                fig.add_trace(go.Box(
                    x=df[col] * 100,
                    name=labels[col],
                    marker_color=colors[col],
                    boxpoints=False, # Don't show all points
                    orientation='h',
                    line_width=1.5,
                    fillcolor='rgba(0,0,0,0)', # Transparent fill
                ))
                
                # Add marker for current value
                fig.add_trace(go.Scatter(
                    x=[current_hv[col]],
                    y=[labels[col]],
                    mode='markers',
                    marker=dict(size=10, color='#ffffff', symbol='line-ns-open', line=dict(width=3, color='#ffffff')),
                    name=f'Current {labels[col]}',
                    showlegend=False,
                    hovertemplate=f'Current: %{{x:.2f}}%<extra></extra>'
                ))

        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='#0f172a',
            plot_bgcolor='#0f172a',
            font=dict(color='#f1f5f9', size=10),
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
            xaxis=dict(
                title='Volatility (%)',
                gridcolor='rgba(51, 65, 85, 0.15)',
                zeroline=False
            ),
            yaxis=dict(
                gridcolor='rgba(51, 65, 85, 0.15)',
                zeroline=False
            ),
            hovermode='y unified'
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"dist_{symbol}")


def render_multi_stock_comparison(selected_stocks, all_symbols):
    """
    Render multi-stock comparison view with overlay charts and correlation analysis.
    
    Args:
        selected_stocks (list): List of selected stock symbols
        all_symbols (list): All available stock symbols
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from utils.data_loader import load_multiple_stocks_data, get_current_metrics
    
    if not selected_stocks or len(selected_stocks) < 2:
        st.warning("⚠️ Please select at least 2 stocks for comparison")
        return
    
    # Load data for all selected stocks efficiently (single DB query)
    stocks_data = load_multiple_stocks_data(selected_stocks)
    stocks_metrics = {}
    
    # Calculate metrics for each stock
    for symbol, df in stocks_data.items():
        stocks_metrics[symbol] = get_current_metrics(df)
    
    if len(stocks_data) < 2:
        st.error("❌ Could not load enough stocks for comparison")
        return
    
    # Main comparison chart with controls
    with st.container(border=True):
        # mode toggle, stock selector, and date filters
        col_mode, col_selector, col_date1, col_date2 = st.columns([1, 1, 1, 1])

        with col_mode:
            if st.toggle("Compare", value=True, key="comparison_toggle_chart", help="Disable to return to single stock"):
                pass
            else:
                st.session_state.comparison_mode = False
                st.rerun()
        
        with col_selector:
            updated_stocks = st.multiselect(
                "Select Stocks",
                all_symbols,
                default=selected_stocks,
                key="stock_multiselect_chart",
                label_visibility="collapsed",
                max_selections=5
            )
            if updated_stocks and updated_stocks != st.session_state.selected_stocks:
                st.session_state.selected_stocks = updated_stocks
                st.rerun()
        
        # Date filters
        all_dates = pd.concat([df['tradingDate'] for df in stocks_data.values()])
        min_date = all_dates.min().date()
        max_date = all_dates.max().date()
        
        with col_date1:
            start_date = st.date_input(
                "Start Date",
                value=min_date,
                min_value=min_date,
                max_value=max_date,
                format="DD/MM/YYYY",
                key="multi_start_date",
                label_visibility="collapsed"
            )
        
        with col_date2:
            end_date = st.date_input(
                "End Date",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
                format="DD/MM/YYYY",
                key="multi_end_date",
                label_visibility="collapsed"
            )
        
        # HV Period selector
        hv_period = st.radio(
            "",
            ["HV 22", "HV 66", "HV 132", "HV 252"],
            index=3,
            horizontal=True,
            key="hv_period_selector"
        )
        
        period_map = {
            "HV 22": "hv_22",
            "HV 66": "hv_66",
            "HV 132": "hv_132",
            "HV 252": "hv_252"
        }
        selected_hv_col = period_map[hv_period]
        
        # Create overlay chart
        fig = go.Figure()
        
        # Color palette for different stocks
        stock_colors = ['#ef4444', '#f59e0b', '#10b981', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316']
        
        for idx, (symbol, df) in enumerate(stocks_data.items()):
            # Filter by date range
            df_filtered = df[
                (df['tradingDate'].dt.date >= start_date) & 
                (df['tradingDate'].dt.date <= end_date)
            ]
            
            if selected_hv_col in df_filtered.columns:
                color = stock_colors[idx % len(stock_colors)]
                fig.add_trace(go.Scatter(
                    x=df_filtered['tradingDate'],
                    y=df_filtered[selected_hv_col] * 100,
                    name=symbol,
                    line=dict(color=color, width=2.5),
                    mode='lines',
                    hovertemplate=f'<b>{symbol}</b><br>' +
                                  'Date: %{x|%Y-%m-%d}<br>' +
                                  hv_period + ': %{y:.2f}%<extra></extra>'
                ))
        
        # Update layout
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='#0f172a',
            plot_bgcolor='#0f172a',
            font=dict(color='#f1f5f9', size=11),
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1,
                bgcolor='rgba(30, 41, 59, 0.95)',
                bordercolor='#334155',
                borderwidth=1
            ),
            xaxis=dict(
                title='Date',
                gridcolor='rgba(51, 65, 85, 0.15)',
                showgrid=True,
                color='#f1f5f9'
            ),
            yaxis=dict(
                title=f'{hv_period} (%)',
                gridcolor='rgba(51, 65, 85, 0.15)',
                showgrid=True,
                color='#f1f5f9'
            ),
            hovermode='x unified',
            height=500,
            margin=dict(l=60, r=40, t=60, b=60)
        )
        
        st.plotly_chart(fig, use_container_width=True, key="multi_stock_hv_chart")
    
    # Comparison metrics and correlation analysis
    col_metrics, col_corr = st.columns([1, 1])
    
    with col_metrics:
        render_comparison_metrics(stocks_metrics, selected_hv_col)
    
    with col_corr:
        render_correlation_matrix(stocks_data, selected_hv_col)


def render_comparison_metrics(stocks_metrics, hv_col):
    """
    Render comparison metrics table for multiple stocks.
    
    Args:
        stocks_metrics (dict): Dictionary of stock symbols to their metrics
        hv_col (str): HV column to display (e.g., 'hv_252')
    """
    with st.container(border=True):
        st.subheader("Comparison Metrics")
        
        # Map column names to display names
        period_names = {
            'hv_22': 'HV 22 (1M)',
            'hv_66': 'HV 66 (3M)',
            'hv_132': 'HV 132 (6M)',
            'hv_252': 'HV 252 (1Y)'
        }
        
        # Create comparison table
        comparison_data = []
        for symbol, metrics in stocks_metrics.items():
            hv_key = period_names.get(hv_col, hv_col)
            hv_data = metrics['hv_metrics'].get(hv_key, {})
            
            comparison_data.append({
                'Symbol': symbol,
                'Current Price': f"{metrics['current_price']:,.2f}",
                'Current HV (%)': f"{hv_data.get('current', 0):.2f}",
                'Avg HV (%)': f"{hv_data.get('mean', 0):.2f}",
                'Min HV (%)': f"{hv_data.get('min', 0):.2f}",
                'Max HV (%)': f"{hv_data.get('max', 0):.2f}",
            })
        
        df_comparison = pd.DataFrame(comparison_data)
        
        st.dataframe(
            df_comparison,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Symbol": st.column_config.TextColumn("Stock", width="small"),
                "Current Price": st.column_config.TextColumn("Price", width="small"),
                "Current HV (%)": st.column_config.TextColumn("Current", width="small"),
                "Avg HV (%)": st.column_config.TextColumn("Average", width="small"),
                "Min HV (%)": st.column_config.TextColumn("Min", width="small"),
                "Max HV (%)": st.column_config.TextColumn("Max", width="small"),
            }
        )


def render_correlation_matrix(stocks_data, hv_col):
    """
    Render correlation matrix heatmap for selected stocks.
    
    Args:
        stocks_data (dict): Dictionary of stock symbols to their dataframes
        hv_col (str): HV column to analyze (e.g., 'hv_252')
    """
    import plotly.graph_objects as go
    
    with st.container(border=True):
        st.subheader("HV Correlation Matrix")
        
        # Prepare data for correlation
        hv_series = {}
        for symbol, df in stocks_data.items():
            if hv_col in df.columns:
                hv_series[symbol] = df.set_index('tradingDate')[hv_col]
        
        if len(hv_series) < 2:
            st.warning("Not enough data for correlation analysis")
            return
        
        # Create correlation dataframe
        hv_df = pd.DataFrame(hv_series)
        
        # Calculate correlation matrix
        corr_matrix = hv_df.corr()
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.index,
            colorscale='RdYlGn',
            zmid=0,
            text=corr_matrix.values,
            texttemplate='%{text:.2f}',
            textfont={"size": 12},
            colorbar=dict(
                title="Correlation",
                title_side="right",
                tickmode="linear",
                tick0=-1,
                dtick=0.5
            ),
            hovertemplate='%{y} vs %{x}<br>Correlation: %{z:.3f}<extra></extra>'
        ))
        
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='#0f172a',
            plot_bgcolor='#0f172a',
            font=dict(color='#f1f5f9', size=11),
            height=400,
            margin=dict(l=60, r=60, t=20, b=60),
            xaxis=dict(side='bottom'),
            yaxis=dict(side='left')
        )
        
        st.plotly_chart(fig, use_container_width=True, key="correlation_heatmap")
        
        # # Add insights
        # st.markdown("Correlation Insights:")
        
        # # Find strongest correlations
        # corr_pairs = []
        # for i in range(len(corr_matrix.columns)):
        #     for j in range(i+1, len(corr_matrix.columns)):
        #         corr_pairs.append({
        #             'pair': f"{corr_matrix.columns[i]} - {corr_matrix.columns[j]}",
        #             'correlation': corr_matrix.iloc[i, j]
        #         })
        
        # if corr_pairs:
        #     corr_pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)
            
        #     # Show top 3 correlations
        #     for i, pair in enumerate(corr_pairs[:3]):
        #         corr_val = pair['correlation']
        #         if corr_val > 0.7:
        #             st.success(f"{pair['pair']}: Strong positive correlation ({corr_val:.2f}) - move together")
        #         elif corr_val < -0.5:
        #             st.error(f"{pair['pair']}: Negative correlation ({corr_val:.2f}) - move opposite")
        #         else:
        #             st.info(f"{pair['pair']}: Moderate correlation ({corr_val:.2f})")
