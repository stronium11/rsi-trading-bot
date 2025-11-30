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


def detect_divergence(df, indicator_values, order=5, lookback=20, min_price_diff_pct=1.0, min_distance=6):
    """
    Detect bullish and bearish divergences between price and a given indicator,
    across longer ranges.

    Parameters:
    - df: DataFrame with 'close' prices.
    - indicator_values: Series with indicator values (e.g., RSI).
    - order: controls local extrema sensitivity.
    - lookback: how many bars back to compare for divergence.
    - min_price_diff_pct: minimum price difference percentage between peaks (default: 1.0%)
    - min_distance: minimum number of candles between peaks (default: 6)

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
    df['divergence_first_peak_date'] = pd.NaT
    df['divergence_first_peak_price'] = np.nan
    df['divergence_first_peak_rsi'] = np.nan
    df['divergence_second_peak_date'] = pd.NaT
    df['divergence_second_peak_price'] = np.nan
    df['divergence_second_peak_rsi'] = np.nan

    # Bearish divergence (price HH, indicator LH)
    for i in price_max_idx:
        for j in price_max_idx:
            if j < i and (i - j) >= min_distance and (i - j) <= lookback:
                price_j = df['close'].iloc[j]
                price_i = df['close'].iloc[i]

                # Calculate price difference percentage
                price_diff_pct = abs((price_i - price_j) / price_j) * 100

                # Check divergence conditions and minimum price difference
                if (df['close'].iloc[i] > df['close'].iloc[j] and
                    df['indicator'].iloc[i] < df['indicator'].iloc[j] and
                    price_diff_pct >= min_price_diff_pct):

                    df.at[df.index[i], 'bearish_divergence'] = True
                    df.at[df.index[i], 'divergence_first_peak_idx'] = j
                    # Convert to timezone-naive datetime
                    first_date = pd.Timestamp(df.index[j])
                    if first_date.tz is not None:
                        first_date = first_date.tz_localize(None)
                    df.at[df.index[i], 'divergence_first_peak_date'] = first_date
                    df.at[df.index[i], 'divergence_first_peak_price'] = df['close'].iloc[j]
                    df.at[df.index[i], 'divergence_first_peak_rsi'] = df['indicator'].iloc[j]
                    # Convert to timezone-naive datetime
                    second_date = pd.Timestamp(df.index[i])
                    if second_date.tz is not None:
                        second_date = second_date.tz_localize(None)
                    df.at[df.index[i], 'divergence_second_peak_date'] = second_date
                    df.at[df.index[i], 'divergence_second_peak_price'] = df['close'].iloc[i]
                    df.at[df.index[i], 'divergence_second_peak_rsi'] = df['indicator'].iloc[i]
                    break  # only need one valid divergence

    # Bullish divergence (price LL, indicator HL)
    for i in price_min_idx:
        for j in price_min_idx:
            if j < i and (i - j) >= min_distance and (i - j) <= lookback:
                price_j = df['close'].iloc[j]
                price_i = df['close'].iloc[i]

                # Calculate price difference percentage
                price_diff_pct = abs((price_i - price_j) / price_j) * 100

                # Check divergence conditions and minimum price difference
                if (df['close'].iloc[i] < df['close'].iloc[j] and
                    df['indicator'].iloc[i] > df['indicator'].iloc[j] and
                    price_diff_pct >= min_price_diff_pct):

                    df.at[df.index[i], 'bullish_divergence'] = True
                    df.at[df.index[i], 'divergence_first_peak_idx'] = j
                    # Convert to timezone-naive datetime
                    first_date = pd.Timestamp(df.index[j])
                    if first_date.tz is not None:
                        first_date = first_date.tz_localize(None)
                    df.at[df.index[i], 'divergence_first_peak_date'] = first_date
                    df.at[df.index[i], 'divergence_first_peak_price'] = df['close'].iloc[j]
                    df.at[df.index[i], 'divergence_first_peak_rsi'] = df['indicator'].iloc[j]
                    # Convert to timezone-naive datetime
                    second_date = pd.Timestamp(df.index[i])
                    if second_date.tz is not None:
                        second_date = second_date.tz_localize(None)
                    df.at[df.index[i], 'divergence_second_peak_date'] = second_date
                    df.at[df.index[i], 'divergence_second_peak_price'] = df['close'].iloc[i]
                    df.at[df.index[i], 'divergence_second_peak_rsi'] = df['indicator'].iloc[i]
                    break

    return df


def extract_divergence_signals(df, ticker, timeframe, max_days_old=30):
    """
    Extract divergence signals from processed DataFrame

    Parameters:
    - df: DataFrame with divergence detection results
    - ticker: Stock ticker symbol
    - timeframe: Timeframe of the data (e.g., '4h', '1d', '1w')
    - max_days_old: Maximum age of signals in trading days (default: 30)

    Returns:
    - List of signal dictionaries
    """
    signals = []

    # Calculate the cutoff date (30 trading days ago)
    # Get the last index date and subtract based on number of bars
    if len(df) == 0:
        return signals

    # Helper function to format peak dates based on timeframe
    def format_peak_date(date, timeframe):
        """Format peak date based on timeframe: 4h includes hour, 1d+ only shows date"""
        if pd.isna(date):
            return None
        if timeframe == '4h':
            # Format as "MM-DD HH:00"
            return date.strftime('%m-%d %H:00')
        else:
            # Format as "MM-DD" for 1d and 1w
            return date.strftime('%m-%d')

    # Use the most recent date in the dataframe as reference
    most_recent_date = df.index[-1]

    # Extract bearish divergences
    bearish = df[df['bearish_divergence'] == True]
    for idx, row in bearish.iterrows():
        # Calculate trading days difference
        idx_position = df.index.get_loc(idx)
        most_recent_position = len(df) - 1
        bars_ago = most_recent_position - idx_position

        # Only include signals from the last 30 trading days
        if bars_ago <= max_days_old:
            signal = {
                'date': idx,  # Keep original timestamp
                'ticker': ticker,
                'timeframe': timeframe,
                'divergence_type': 'Bearish',
                'first_peak_date': format_peak_date(row['divergence_first_peak_date'], timeframe),
                'first_peak_price': round(float(row['divergence_first_peak_price']), 2),
                'first_peak_rsi': round(float(row['divergence_first_peak_rsi']), 2),
                'second_peak_date': format_peak_date(row['divergence_second_peak_date'], timeframe),
                'second_peak_price': round(float(row['divergence_second_peak_price']), 2),
                'second_peak_rsi': round(float(row['divergence_second_peak_rsi']), 2)
            }
            signals.append(signal)

    # Extract bullish divergences
    bullish = df[df['bullish_divergence'] == True]
    for idx, row in bullish.iterrows():
        # Calculate trading days difference
        idx_position = df.index.get_loc(idx)
        most_recent_position = len(df) - 1
        bars_ago = most_recent_position - idx_position

        # Only include signals from the last 30 trading days
        if bars_ago <= max_days_old:
            signal = {
                'date': idx,  # Keep original timestamp
                'ticker': ticker,
                'timeframe': timeframe,
                'divergence_type': 'Bullish',
                'first_peak_date': format_peak_date(row['divergence_first_peak_date'], timeframe),
                'first_peak_price': round(float(row['divergence_first_peak_price']), 2),
                'first_peak_rsi': round(float(row['divergence_first_peak_rsi']), 2),
                'second_peak_date': format_peak_date(row['divergence_second_peak_date'], timeframe),
                'second_peak_price': round(float(row['divergence_second_peak_price']), 2),
                'second_peak_rsi': round(float(row['divergence_second_peak_rsi']), 2)
            }
            signals.append(signal)

    return signals
