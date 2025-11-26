"""
Data fetching module for market data and NASDAQ 100 tickers
"""
import yfinance as yf
import pandas as pd
from typing import List, Dict
import config
import os

# Demo mode flag
DEMO_MODE = os.environ.get('DEMO_MODE', 'false').lower() == 'true'


def get_nasdaq100_tickers() -> List[str]:
    """
    Fetch NASDAQ 100 component tickers from Wikipedia
    Returns list of ticker symbols
    """
    try:
        # Read NASDAQ 100 from Wikipedia
        tables = pd.read_html(config.NASDAQ_100_URL)
        df = tables[4]  # The ticker table is usually the 4th table
        tickers = df['Ticker'].tolist()
        print(f"Fetched {len(tickers)} NASDAQ 100 tickers")
        return tickers
    except Exception as e:
        print(f"Error fetching NASDAQ 100 tickers: {e}")
        # Fallback to a small sample for testing
        return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']


def fetch_stock_data(ticker: str, period: str = config.DATA_PERIOD) -> pd.DataFrame:
    """
    Fetch historical price data for a ticker

    Args:
        ticker: Stock ticker symbol
        period: Period of data to fetch (default: from config)

    Returns:
        DataFrame with OHLCV data
    """
    # Use demo data if in demo mode
    if DEMO_MODE:
        try:
            from demo_data import generate_signal_demo_data
            print(f"[DEMO] Generating data for {ticker}")
            return generate_signal_demo_data(ticker)
        except Exception as e:
            print(f"Error generating demo data for {ticker}: {e}")
            return pd.DataFrame()

    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval='1d')

        if df.empty:
            print(f"No data found for {ticker}")
            return pd.DataFrame()

        return df
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()


def resample_to_timeframe(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    Resample daily data to different timeframes

    Args:
        df: DataFrame with daily OHLCV data
        timeframe: '1d', '3d', or '1w'

    Returns:
        Resampled DataFrame
    """
    if timeframe == '1d':
        return df
    elif timeframe == '3d':
        # Resample to 3-day periods
        resampled = df.resample('3D').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        return resampled
    elif timeframe == '1w':
        # Resample to weekly periods
        resampled = df.resample('W').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        return resampled
    else:
        return df
