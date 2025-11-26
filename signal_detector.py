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


def check_sma_touch_history(df: pd.DataFrame, sma_period: int, lookback_days: int = 2) -> bool:
    """
    Check if price touched the SMA in the previous N trading days

    Args:
        df: DataFrame with price and SMA data
        sma_period: SMA period to check (50, 100, 200)
        lookback_days: Number of previous trading days to check (default 2)

    Returns:
        True if price touched SMA in previous days, False otherwise
    """
    if len(df) < lookback_days + 1:
        return False

    sma_col = f'SMA_{sma_period}'

    # Check the previous N trading days (not including today)
    for i in range(1, lookback_days + 1):
        try:
            prev_row = df.iloc[-(i + 1)]
            prev_price = prev_row['Close']
            prev_sma = prev_row[sma_col]

            if pd.isna(prev_price) or pd.isna(prev_sma):
                continue

            # Check if price was near SMA on that day
            if check_price_near_sma(prev_price, prev_sma):
                return True  # Price touched SMA in previous days
        except:
            continue

    return False  # Price did NOT touch SMA in previous days


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

        # Check if price is near this SMA today
        if check_price_near_sma(current_price, sma_value):
            # NEW FILTER: Check if price touched this SMA in previous 1-2 trading days
            if check_sma_touch_history(df, period, lookback_days=2):
                # Skip this signal - price has been riding the SMA
                continue

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
