"""
Trend validation module - checks if SMAs show a clear trend
"""
import pandas as pd
from typing import Optional, Dict
import config


def check_sma_separation_and_trend(sma_50: float, sma_100: float, sma_200: float) -> Optional[str]:
    """
    Check if SMAs are properly separated and aligned for a trend

    Args:
        sma_50: 50-period SMA value
        sma_100: 100-period SMA value
        sma_200: 200-period SMA value

    Returns:
        'bullish', 'bearish', or None if no clear trend
    """
    threshold = config.SMA_SEPARATION_THRESHOLD

    # Check for bullish trend
    # SMA 50 >= SMA 100 * 1.005 AND SMA 100 >= SMA 200 * 1.005
    if (sma_50 >= sma_100 * (1 + threshold) and
        sma_100 >= sma_200 * (1 + threshold)):
        return 'bullish'

    # Check for bearish trend
    # SMA 50 <= SMA 100 * 0.995 AND SMA 100 <= SMA 200 * 0.995
    if (sma_50 <= sma_100 * (1 - threshold) and
        sma_100 <= sma_200 * (1 - threshold)):
        return 'bearish'

    # No clear trend
    return None


def check_trend_stability(current_smas: Dict[str, float],
                         historical_smas: Dict[str, float]) -> bool:
    """
    Check if the trend alignment was the same N periods ago

    Args:
        current_smas: Current SMA values {'SMA_50': x, 'SMA_100': y, 'SMA_200': z}
        historical_smas: Historical SMA values from N periods ago

    Returns:
        True if trend is stable (same alignment), False otherwise
    """
    if historical_smas is None:
        return False

    current_trend = check_sma_separation_and_trend(
        current_smas['SMA_50'],
        current_smas['SMA_100'],
        current_smas['SMA_200']
    )

    historical_trend = check_sma_separation_and_trend(
        historical_smas['SMA_50'],
        historical_smas['SMA_100'],
        historical_smas['SMA_200']
    )

    # Trend is stable if both periods show the same trend type
    return current_trend == historical_trend and current_trend is not None


def validate_trend(df: pd.DataFrame, stability_check_days: int) -> Optional[str]:
    """
    Complete trend validation: separation + stability

    Args:
        df: DataFrame with SMA columns
        stability_check_days: Number of days to check for stability

    Returns:
        'bullish', 'bearish', or None if no valid trend
    """
    if len(df) < max(config.SMA_PERIODS) + stability_check_days:
        return None

    # Get current SMAs
    latest_row = df.iloc[-1]
    current_smas = {
        'SMA_50': latest_row['SMA_50'],
        'SMA_100': latest_row['SMA_100'],
        'SMA_200': latest_row['SMA_200']
    }

    # Check if any SMA is NaN
    if any(pd.isna(val) for val in current_smas.values()):
        return None

    # Get historical SMAs for stability check
    from sma_calculator import get_historical_sma_alignment
    historical_smas = get_historical_sma_alignment(df, stability_check_days)

    if historical_smas is None:
        return None

    # Check if any historical SMA is NaN
    if any(pd.isna(val) for val in historical_smas.values()):
        return None

    # Check current trend
    current_trend = check_sma_separation_and_trend(
        current_smas['SMA_50'],
        current_smas['SMA_100'],
        current_smas['SMA_200']
    )

    if current_trend is None:
        return None

    # Check stability
    is_stable = check_trend_stability(current_smas, historical_smas)

    if is_stable:
        return current_trend
    else:
        return None
