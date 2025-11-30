"""
Configuration for RSI Divergence Detection System
"""

# Timeframes to analyze
TIMEFRAMES = ['1h', '4h', '1d', '3d']

# RSI parameters
RSI_PERIOD = 14

# Divergence detection parameters
DIVERGENCE_ORDER = 5  # Controls local extrema sensitivity
DIVERGENCE_LOOKBACK = 20  # How many bars back to compare

# Data fetching
DATA_PERIOD_HOURLY = '60d'  # 60 days for hourly data
DATA_PERIOD_DAILY = '1y'    # 1 year for daily data

# Output
OUTPUT_FILE = 'rsi_divergence_signals.csv'

# NASDAQ 100 URL
NASDAQ_100_URL = 'https://en.wikipedia.org/wiki/Nasdaq-100'
