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
        tables = pd.read_html(config.NASDAQ_100_URL)
        df = tables[4]
        tickers = df['Ticker'].tolist()
        print(f"✓ Fetched {len(tickers)} NASDAQ 100 tickers from Wikipedia")
        return tickers
    except Exception as e:
        print(f"⚠ Could not fetch from Wikipedia: {e}")
        print(f"✓ Using hardcoded NASDAQ 100 list ({len(nasdaq100_tickers)} tickers)")
        return nasdaq100_tickers


def fetch_stock_data(ticker: str, timeframe: str) -> pd.DataFrame:
    """
    Fetch historical price data for a ticker at specific timeframe

    Args:
        ticker: Stock ticker symbol
        timeframe: '1h', '4h', '1d', '3d'

    Returns:
        DataFrame with OHLCV data
    """
    try:
        stock = yf.Ticker(ticker)

        # Map timeframes
        if timeframe in ['1h', '4h']:
            interval = '1h'
            period = config.DATA_PERIOD_HOURLY
        else:
            interval = '1d'
            period = config.DATA_PERIOD_DAILY

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
        return pd.DataFrame()
