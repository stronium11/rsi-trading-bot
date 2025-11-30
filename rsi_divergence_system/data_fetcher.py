"""
Data fetching module for RSI divergence system
"""
import yfinance as yf
import pandas as pd
from typing import List
import config


def get_nasdaq100_tickers() -> List[str]:
    """
    Fetch NASDAQ 100 component tickers
    """
    # Hardcoded NASDAQ 100 list
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
        # Try to fetch from Wikipedia
        tables = pd.read_html(config.NASDAQ_100_URL)
        df = tables[4]
        tickers = df['Ticker'].tolist()
        print(f"✓ Fetched {len(tickers)} NASDAQ 100 tickers from Wikipedia")
        return tickers
    except Exception as e:
        print(f"⚠ Could not fetch from Wikipedia: {e}")
        print(f"✓ Using hardcoded NASDAQ 100 list ({len(nasdaq100_tickers)} tickers)")
        return nasdaq100_tickers


def fetch_stock_data(ticker: str, timeframe: str, period: str = config.DATA_PERIOD) -> pd.DataFrame:
    """
    Fetch historical price data for a ticker at specific timeframe

    Args:
        ticker: Stock ticker symbol
        timeframe: '1h', '4h', '1d', '3d'
        period: Period of data to fetch

    Returns:
        DataFrame with OHLCV data
    """
    try:
        stock = yf.Ticker(ticker)

        # Map timeframes to yfinance intervals
        interval_map = {
            '1h': '1h',
            '4h': '1h',  # We'll resample 1h to 4h
            '1d': '1d',
            '3d': '1d'   # We'll resample 1d to 3d
        }

        # Adjust period for hourly data
        if timeframe in ['1h', '4h']:
            period = '60d'  # Max for hourly is ~730 days, use 60 for speed
        else:
            period = '1y'

        interval = interval_map.get(timeframe, '1d')
        df = stock.history(period=period, interval=interval)

        if df.empty:
            return pd.DataFrame()

        # Resample if needed
        if timeframe == '4h':
            df = df.resample('4H').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
        elif timeframe == '3d':
            df = df.resample('3D').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()

        return df

    except Exception as e:
        print(f"Error fetching {ticker} at {timeframe}: {e}")
        return pd.DataFrame()
