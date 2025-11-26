"""
Configuration file for SMA Trading Signal System
"""

# SMA Periods
SMA_PERIODS = [50, 100, 200]

# Timeframes to analyze
TIMEFRAMES = {
    '1d': {'interval': '1d', 'stability_check_days': 14},
    '3d': {'interval': '1d', 'stability_check_days': 25},  # We'll resample daily data
    '1w': {'interval': '1d', 'stability_check_days': 25}   # We'll resample daily data
}

# Signal thresholds
PRICE_PROXIMITY_THRESHOLD = 0.005  # 0.5% - Price must be within this % of SMA
SMA_SEPARATION_THRESHOLD = 0.005   # 0.5% - SMAs must be at least this % apart

# Data fetching
DATA_PERIOD = '1y'  # Fetch 1 year of data to have enough for calculations

# Output
OUTPUT_FILE = 'trading_signals.csv'
SIGNALS_HISTORY_FILE = 'signals_history.json'

# NASDAQ 100 tickers (we'll fetch this programmatically)
NASDAQ_100_URL = 'https://en.wikipedia.org/wiki/Nasdaq-100'
