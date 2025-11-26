"""
Signal detection module - detects when price touches or comes close to SMAs
"""
import pandas as pd
from typing import List, Dict, Optional
import config


def check_price_near_sma(price: float, sma: float, threshold: float = config.PRICE_PROXIMITY_THRESHOLD) -> bool:
    """
    Check if price is within threshold % of SMA

    Args:
        price: Current price
        sma: SMA value
        threshold: Proximity threshold (default 0.5% = 0.005)

    Returns:
        True if price is within threshold of SMA
    """
    if pd.isna(sma) or pd.isna(price):
        return False

    lower_bound = sma * (1 - threshold)
    upper_bound = sma * (1 + threshold)

    return lower_bound <= price <= upper_bound


def detect_signals(df: pd.DataFrame, ticker: str, timeframe: str, trend: str) -> List[Dict]:
    """
    Detect all signals for the latest data point

    Args:
        df: DataFrame with price and SMA data
        ticker: Stock ticker symbol
        timeframe: Timeframe being analyzed ('1d', '3d', '1w')
        trend: Trend type ('bullish' or 'bearish')

    Returns:
        List of signal dictionaries
    """
    if len(df) == 0:
        return []

    signals = []
    latest_row = df.iloc[-1]
    current_price = latest_row['Close']
    current_date = latest_row.name  # Index should be datetime

    # Check each SMA period
    for period in config.SMA_PERIODS:
        sma_col = f'SMA_{period}'
        sma_value = latest_row[sma_col]

        if pd.isna(sma_value):
            continue

        # Check if price is near this SMA
        if check_price_near_sma(current_price, sma_value):
            signal = {
                'date': current_date.strftime('%Y-%m-%d') if hasattr(current_date, 'strftime') else str(current_date),
                'ticker': ticker,
                'sma_period': period,
                'timeframe': timeframe,
                'trend': trend,
                'price': round(current_price, 2),
                'sma_value': round(sma_value, 2),
                'distance_pct': round(abs(current_price - sma_value) / sma_value * 100, 3)
            }
            signals.append(signal)

    return signals
