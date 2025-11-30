"""
RSI Divergence Detection Module
Based on provided divergence detection code
"""
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from scipy.signal import argrelextrema
import config


def calculate_rsi(df, rsi_period=config.RSI_PERIOD):
    """
    Calculate RSI indicator

    Args:
        df: DataFrame with 'Close' column
        rsi_period: RSI period (default: 14)

    Returns:
        Series with RSI values
    """
    rsi = RSIIndicator(df['Close'], window=rsi_period)
    return rsi.rsi()


def detect_divergence(df, order=config.DIVERGENCE_ORDER, lookback=config.DIVERGENCE_LOOKBACK):
    """
    Detect bullish and bearish divergences between price and RSI.

    Parameters:
    - df: DataFrame with 'Close' prices.
    - order: controls local extrema sensitivity.
    - lookback: how many bars back to compare for divergence.

    Returns:
    - List of divergence signals with details
    """
    if len(df) < lookback + order:
        return []

    df = df.copy()

    # Calculate RSI
    df['RSI'] = calculate_rsi(df)

    # Drop NaN values from RSI calculation
    df = df.dropna()

    if len(df) < lookback + order:
        return []

    # Identify local extrema
    price_max_idx = argrelextrema(df['Close'].values, np.greater_equal, order=order)[0]
    price_min_idx = argrelextrema(df['Close'].values, np.less_equal, order=order)[0]

    signals = []

    # Bearish divergence (price HH, RSI LH)
    for i in price_max_idx:
        for j in price_max_idx:
            if j < i and (i - j) <= lookback:
                price_i = df['Close'].iloc[i]
                price_j = df['Close'].iloc[j]
                rsi_i = df['RSI'].iloc[i]
                rsi_j = df['RSI'].iloc[j]

                # Price Higher High, RSI Lower High
                if price_i > price_j and rsi_i < rsi_j:
                    signal = {
                        'date': df.index[i],
                        'type': 'bearish',
                        'first_peak_price': price_j,
                        'second_peak_price': price_i,
                        'first_peak_rsi': rsi_j,
                        'second_peak_rsi': rsi_i,
                        'first_peak_date': df.index[j],
                        'bars_between': i - j
                    }
                    signals.append(signal)
                    break  # Only one divergence per peak

    # Bullish divergence (price LL, RSI HL)
    for i in price_min_idx:
        for j in price_min_idx:
            if j < i and (i - j) <= lookback:
                price_i = df['Close'].iloc[i]
                price_j = df['Close'].iloc[j]
                rsi_i = df['RSI'].iloc[i]
                rsi_j = df['RSI'].iloc[j]

                # Price Lower Low, RSI Higher Low
                if price_i < price_j and rsi_i > rsi_j:
                    signal = {
                        'date': df.index[i],
                        'type': 'bullish',
                        'first_peak_price': price_j,
                        'second_peak_price': price_i,
                        'first_peak_rsi': rsi_j,
                        'second_peak_rsi': rsi_i,
                        'first_peak_date': df.index[j],
                        'bars_between': i - j
                    }
                    signals.append(signal)
                    break  # Only one divergence per trough

    return signals
