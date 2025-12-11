"""
Database connector for Historical Volatility Dashboard
Handles connection to PostgreSQL database
"""
import psycopg2
import pandas as pd
from psycopg2 import pool
import streamlit as st

# Try to import db_config, provide helpful error if not found
try:
    from db_config import DB_CONFIG
except ImportError:
    st.error("""
    ❌ Database configuration not found!
    
    Please create a `db_config.py` file in the project root with your database credentials.
    You can copy `db_config.example.py` as a template.
    """)
    st.stop()


class DatabaseConnector:
    """Handles database connections and queries"""
    
    _connection_pool = None
    
    @classmethod
    def get_connection_pool(cls):
        """Get or create connection pool"""
        if cls._connection_pool is None:
            try:
                cls._connection_pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    host=DB_CONFIG['host'],
                    port=DB_CONFIG['port'],
                    database=DB_CONFIG['database'],
                    user=DB_CONFIG['user'],
                    password=DB_CONFIG['password']
                )
            except Exception as e:
                st.error(f"❌ Failed to connect to database: {str(e)}")
                st.stop()
        return cls._connection_pool
    
    @classmethod
    def get_connection(cls):
        """Get a connection from the pool"""
        pool = cls.get_connection_pool()
        return pool.getconn()
    
    @classmethod
    def return_connection(cls, conn):
        """Return a connection to the pool"""
        pool = cls.get_connection_pool()
        pool.putconn(conn)
    
    @classmethod
    def execute_query(cls, query, params=None):
        """
        Execute a query and return results as pandas DataFrame.
        
        Args:
            query (str): SQL query to execute
            params (tuple): Query parameters for safe parameterized queries
        
        Returns:
            pd.DataFrame: Query results
        """
        conn = None
        try:
            conn = cls.get_connection()
            df = pd.read_sql_query(query, conn, params=params)
            return df
        except Exception as e:
            st.error(f"❌ Database query error: {str(e)}")
            return pd.DataFrame()
        finally:
            if conn:
                cls.return_connection(conn)


def get_available_symbols():
    """
    Get list of unique symbols from the database.
    
    Returns:
        list: Sorted list of stock symbols
    """
    query = """
    SELECT DISTINCT symbol 
    FROM historical_volatility 
    ORDER BY symbol
    """
    
    df = DatabaseConnector.execute_query(query)
    return df['symbol'].tolist() if not df.empty else []


def load_symbol_data(symbol):
    """
    Load all historical volatility data for a specific symbol.
    Uses efficient WHERE clause to avoid loading entire table.
    
    Args:
        symbol (str): Stock symbol
    
    Returns:
        pd.DataFrame: Historical volatility data for the symbol
    """
    query = """
    SELECT 
        id,
        symbol,
        trading_date as "tradingDate",
        hv_22,
        hv_66,
        hv_132,
        hv_252
    FROM historical_volatility
    WHERE symbol = %s
    ORDER BY trading_date ASC
    """
    
    df = DatabaseConnector.execute_query(query, params=(symbol,))
    
    if not df.empty:
        # Convert trading_date to datetime
        df['tradingDate'] = pd.to_datetime(df['tradingDate'])
        
        # Convert HV values from percentage to decimal (0-1 range)
        # Assuming database stores as percentages (e.g., 25.5 for 25.5%)
        for col in ['hv_22', 'hv_66', 'hv_132', 'hv_252']:
            if col in df.columns:
                df[col] = df[col] / 100.0
    
    return df


def load_multiple_symbols_data(symbols):
    """
    Load historical volatility data for multiple symbols efficiently.
    Uses IN clause to fetch all symbols in one query.
    
    Args:
        symbols (list): List of stock symbols
    
    Returns:
        dict: Dictionary mapping symbol to its DataFrame
    """
    if not symbols:
        return {}
    
    # Create parameterized query with IN clause
    placeholders = ','.join(['%s'] * len(symbols))
    query = f"""
    SELECT 
        id,
        symbol,
        trading_date as "tradingDate",
        hv_22,
        hv_66,
        hv_132,
        hv_252
    FROM historical_volatility
    WHERE symbol IN ({placeholders})
    ORDER BY symbol, trading_date ASC
    """
    
    df = DatabaseConnector.execute_query(query, params=tuple(symbols))
    
    if df.empty:
        return {}
    
    # Convert trading_date to datetime
    df['tradingDate'] = pd.to_datetime(df['tradingDate'])
    
    # Convert HV values from percentage to decimal (0-1 range)
    for col in ['hv_22', 'hv_66', 'hv_132', 'hv_252']:
        if col in df.columns:
            df[col] = df[col] / 100.0
    
    # Split into dictionary by symbol
    result = {}
    for symbol in symbols:
        symbol_df = df[df['symbol'] == symbol].copy()
        result[symbol] = symbol_df
    
    return result


def get_latest_data_date(symbol=None):
    """
    Get the latest trading date in the database.
    
    Args:
        symbol (str, optional): If provided, get latest date for specific symbol
    
    Returns:
        datetime: Latest trading date
    """
    if symbol:
        query = """
        SELECT MAX(trading_date) as latest_date
        FROM historical_volatility
        WHERE symbol = %s
        """
        df = DatabaseConnector.execute_query(query, params=(symbol,))
    else:
        query = """
        SELECT MAX(trading_date) as latest_date
        FROM historical_volatility
        """
        df = DatabaseConnector.execute_query(query)
    
    if not df.empty and df['latest_date'].iloc[0]:
        return pd.to_datetime(df['latest_date'].iloc[0])
    return None


def get_data_date_range(symbol=None):
    """
    Get the date range of available data.
    
    Args:
        symbol (str, optional): If provided, get range for specific symbol
    
    Returns:
        tuple: (min_date, max_date)
    """
    if symbol:
        query = """
        SELECT 
            MIN(trading_date) as min_date,
            MAX(trading_date) as max_date
        FROM historical_volatility
        WHERE symbol = %s
        """
        df = DatabaseConnector.execute_query(query, params=(symbol,))
    else:
        query = """
        SELECT 
            MIN(trading_date) as min_date,
            MAX(trading_date) as max_date
        FROM historical_volatility
        """
        df = DatabaseConnector.execute_query(query)
    
    if not df.empty:
        min_date = pd.to_datetime(df['min_date'].iloc[0]) if df['min_date'].iloc[0] else None
        max_date = pd.to_datetime(df['max_date'].iloc[0]) if df['max_date'].iloc[0] else None
        return min_date, max_date
    
    return None, None

