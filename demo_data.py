"""
Demo data generator for testing the signal system
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_demo_data(ticker: str, trend_type: str = 'bullish') -> pd.DataFrame:
    """
    Generate realistic demo stock data with SMAs that will trigger signals

    Args:
        ticker: Stock ticker symbol
        trend_type: 'bullish' or 'bearish'

    Returns:
        DataFrame with OHLCV data
    """
    # Generate 300 trading days
    days = 300
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    # Base price
    base_price = np.random.uniform(100, 300)

    # Generate price trend
    if trend_type == 'bullish':
        # Upward trend
        trend = np.linspace(0, base_price * 0.3, days)
        noise = np.random.normal(0, base_price * 0.02, days)
    else:
        # Downward trend
        trend = np.linspace(0, -base_price * 0.3, days)
        noise = np.random.normal(0, base_price * 0.02, days)

    close_prices = base_price + trend + noise

    # Generate OHLV from close
    high = close_prices * (1 + np.random.uniform(0, 0.02, days))
    low = close_prices * (1 - np.random.uniform(0, 0.02, days))
    open_prices = close_prices + np.random.uniform(-2, 2, days)
    volume = np.random.randint(1000000, 10000000, days)

    df = pd.DataFrame({
        'Open': open_prices,
        'High': high,
        'Low': low,
        'Close': close_prices,
        'Volume': volume
    }, index=dates)

    return df


def generate_signal_demo_data(ticker: str) -> pd.DataFrame:
    """
    Generate data specifically designed to trigger signals
    Price will touch SMA 50 in the last few days
    """
    days = 300
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    base_price = 150.0

    # Create a bullish trend
    prices = []
    for i in range(days):
        # Gradual uptrend
        trend_component = base_price + (i * 0.15)
        # Add some noise
        noise = np.random.normal(0, 2)
        prices.append(trend_component + noise)

    close_prices = np.array(prices)

    # Calculate what SMA50 will be
    sma_50 = pd.Series(close_prices).rolling(window=50).mean()

    # Make the last price touch the SMA 50 (within 0.5%)
    if not pd.isna(sma_50.iloc[-1]):
        close_prices[-1] = sma_50.iloc[-1] * 1.003  # 0.3% above SMA

    df = pd.DataFrame({
        'Open': close_prices + np.random.uniform(-1, 1, days),
        'High': close_prices * 1.01,
        'Low': close_prices * 0.99,
        'Close': close_prices,
        'Volume': np.random.randint(5000000, 15000000, days)
    }, index=dates)

    return df
