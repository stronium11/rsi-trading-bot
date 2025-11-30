"""
RSI Divergence Detection Module
Detects bullish and bearish divergences between price and RSI indicator
"""

import pandas as pd
import numpy as np
from scipy.signal import argrelextrema


def calculate_rsi(df, rsi_period=14):
    """
    Calculate RSI indicator for given price data using custom implementation

    Parameters:
    - df: DataFrame with 'close' prices
    - rsi_period: RSI calculation period (default: 14)

    Returns:
    - Series with RSI values
    """
    close = df['close'].copy()

    # Calculate price changes
    delta = close.diff()

    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Calculate average gain and average loss using EMA
    avg_gain = gain.ewm(com=rsi_period - 1, min_periods=rsi_period).mean()
    avg_loss = loss.ewm(com=rsi_period - 1, min_periods=rsi_period).mean()

    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def detect_divergence(df, indicator_values, order=5, lookback=20):
    """
    Detect bullish and bearish divergences between price and a given indicator,
    across longer ranges.

    Parameters:
    - df: DataFrame with 'close' prices.
    - indicator_values: Series with indicator values (e.g., RSI).
    - order: controls local extrema sensitivity.
    - lookback: how many bars back to compare for divergence.

    Returns:
    - df with divergence columns and divergence details
    """
    df = df.copy()
    df['indicator'] = indicator_values

    # Identify local extrema
    price_max_idx = argrelextrema(df['close'].values, np.greater_equal, order=order)[0]
    price_min_idx = argrelextrema(df['close'].values, np.less_equal, order=order)[0]
    ind_max_idx = argrelextrema(df['indicator'].values, np.greater_equal, order=order)[0]
    ind_min_idx = argrelextrema(df['indicator'].values, np.less_equal, order=order)[0]

    df['bullish_divergence'] = False
    df['bearish_divergence'] = False
    df['divergence_first_peak_idx'] = np.nan
    df['divergence_first_peak_price'] = np.nan
    df['divergence_first_peak_rsi'] = np.nan
    df['divergence_second_peak_price'] = np.nan
    df['divergence_second_peak_rsi'] = np.nan

    # Bearish divergence (price HH, indicator LH)
    for i in price_max_idx:
        for j in price_max_idx:
            if j < i and (i - j) <= lookback:
                if df['close'].iloc[i] > df['close'].iloc[j] and df['indicator'].iloc[i] < df['indicator'].iloc[j]:
                    df.at[df.index[i], 'bearish_divergence'] = True
                    df.at[df.index[i], 'divergence_first_peak_idx'] = j
                    df.at[df.index[i], 'divergence_first_peak_price'] = df['close'].iloc[j]
                    df.at[df.index[i], 'divergence_first_peak_rsi'] = df['indicator'].iloc[j]
                    df.at[df.index[i], 'divergence_second_peak_price'] = df['close'].iloc[i]
                    df.at[df.index[i], 'divergence_second_peak_rsi'] = df['indicator'].iloc[i]
                    break  # only need one valid divergence

    # Bullish divergence (price LL, indicator HL)
    for i in price_min_idx:
        for j in price_min_idx:
            if j < i and (i - j) <= lookback:
                if df['close'].iloc[i] < df['close'].iloc[j] and df['indicator'].iloc[i] > df['indicator'].iloc[j]:
                    df.at[df.index[i], 'bullish_divergence'] = True
                    df.at[df.index[i], 'divergence_first_peak_idx'] = j
                    df.at[df.index[i], 'divergence_first_peak_price'] = df['close'].iloc[j]
                    df.at[df.index[i], 'divergence_first_peak_rsi'] = df['indicator'].iloc[j]
                    df.at[df.index[i], 'divergence_second_peak_price'] = df['close'].iloc[i]
                    df.at[df.index[i], 'divergence_second_peak_rsi'] = df['indicator'].iloc[i]
                    break

    return df


def extract_divergence_signals(df, ticker, timeframe):
    """
    Extract divergence signals from processed DataFrame

    Parameters:
    - df: DataFrame with divergence detection results
    - ticker: Stock ticker symbol
    - timeframe: Timeframe of the data (e.g., '1h', '4h', '1d', '3d')

    Returns:
    - List of signal dictionaries
    """
    signals = []

    # Extract bearish divergences
    bearish = df[df['bearish_divergence'] == True]
    for idx, row in bearish.iterrows():
        signal = {
            'date': idx,
            'ticker': ticker,
            'timeframe': timeframe,
            'divergence_type': 'Bearish',
            'first_peak_price': row['divergence_first_peak_price'],
            'second_peak_price': row['divergence_second_peak_price'],
            'first_peak_rsi': row['divergence_first_peak_rsi'],
            'second_peak_rsi': row['divergence_second_peak_rsi']
        }
        signals.append(signal)

    # Extract bullish divergences
    bullish = df[df['bullish_divergence'] == True]
    for idx, row in bullish.iterrows():
        signal = {
            'date': idx,
            'ticker': ticker,
            'timeframe': timeframe,
            'divergence_type': 'Bullish',
            'first_peak_price': row['divergence_first_peak_price'],
            'second_peak_price': row['divergence_second_peak_price'],
            'first_peak_rsi': row['divergence_first_peak_rsi'],
            'second_peak_rsi': row['divergence_second_peak_rsi']
        }
        signals.append(signal)

    return signals
