"""
SMA calculation module
"""
import pandas as pd
import numpy as np
from typing import Dict
import config


def calculate_smas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate SMAs for all configured periods

    Args:
        df: DataFrame with price data (must have 'Close' column)

    Returns:
        DataFrame with additional SMA columns
    """
    df = df.copy()

    for period in config.SMA_PERIODS:
        df[f'SMA_{period}'] = df['Close'].rolling(window=period).mean()

    return df


def get_historical_sma_alignment(df: pd.DataFrame, days_ago: int) -> Dict[str, float]:
    """
    Get SMA values from N days ago for stability check

    Args:
        df: DataFrame with SMA columns
        days_ago: Number of periods to look back

    Returns:
        Dictionary with SMA values from days_ago
    """
    if len(df) < days_ago:
        return None

    try:
        historical_row = df.iloc[-(days_ago + 1)]
        return {
            'SMA_50': historical_row['SMA_50'],
            'SMA_100': historical_row['SMA_100'],
            'SMA_200': historical_row['SMA_200']
        }
    except Exception as e:
        return None
