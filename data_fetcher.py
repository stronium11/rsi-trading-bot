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
    Fetch NASDAQ 100 component tickers from Wikipedia or use hardcoded list
    Returns list of ticker symbols
    """
    # Hardcoded NASDAQ 100 list (updated as of Nov 2024)
    nasdaq100_tickers = [
        'AAPL', 'ABNB', 'ADBE', 'ADI', 'ADP', 'ADSK', 'AEP', 'AMAT', 'AMD', 'AMGN',
        'AMZN', 'ANSS', 'ASML', 'AVGO', 'AZN', 'BIIB', 'BKNG', 'BKR', 'CDNS', 'CEG',
        'CHTR', 'CMCSA', 'COST', 'CPRT', 'CRWD', 'CSCO', 'CSGP', 'CSX', 'CTAS', 'CTSH',
        'DDOG', 'DXCM', 'EA', 'EXC', 'FANG', 'FAST', 'FTNT', 'GEHC', 'GFS', 'GILD',
        'GOOGL', 'GOOG', 'HON', 'IDXX', 'ILMN', 'INTC', 'INTU', 'ISRG', 'KDP', 'KHC',
        'KLAC', 'LIN', 'LRCX', 'LULU', 'MAR', 'MCHP', 'MDB', 'MDLZ', 'MELI', 'META',
        'MNST', 'MRNA', 'MRVL', 'MSFT', 'MU', 'NFLX', 'NVDA', 'NXPI', 'ODFL', 'ON',
        'ORLY', 'PANW', 'PAYX', 'PCAR', 'PDD', 'PEP', 'PYPL', 'QCOM', 'REGN', 'ROP',
        'ROST', 'SBUX', 'SMCI', 'SNPS', 'TEAM', 'TMUS', 'TSLA', 'TTD', 'TTWO', 'TXN',
        'VRSK', 'VRTX', 'WBD', 'WDAY', 'XEL', 'ZS'
    ]

    try:
        # Try to fetch from Wikipedia first
        tables = pd.read_html(config.NASDAQ_100_URL)
        df = tables[4]  # The ticker table is usually the 4th table
        tickers = df['Ticker'].tolist()
        print(f"✓ Fetched {len(tickers)} NASDAQ 100 tickers from Wikipedia")
        return tickers
    except Exception as e:
        print(f"⚠ Could not fetch from Wikipedia: {e}")
        print(f"✓ Using hardcoded NASDAQ 100 list ({len(nasdaq100_tickers)} tickers)")
        return nasdaq100_tickers


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
