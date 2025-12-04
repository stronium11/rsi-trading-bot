"""
Data Fetcher Module
Handles fetching historical stock data using Finnhub API
"""

import os
import pandas as pd
import finnhub
from datetime import datetime, timedelta
import time


class FinnhubDataFetcher:
    """
    Fetches stock data using Finnhub API
    """

    def __init__(self):
        """Initialize Finnhub client with API key from environment"""
        api_key = os.getenv('FINNHUB_API_KEY')

        if not api_key:
            raise ValueError(
                "FINNHUB_API_KEY environment variable not set. "
                "Set it with: export FINNHUB_API_KEY='your_key'"
            )

        self.client = finnhub.Client(api_key=api_key)
        self.rate_limit_delay = 1.0  # 1 second between calls (60/min limit)

    def fetch_historical_data(self, ticker, start_date=None, end_date=None, period='5y'):
        """
        Fetch historical daily data for a ticker

        Parameters:
        - ticker: Stock ticker symbol
        - start_date: Start date (datetime or string 'YYYY-MM-DD'). If None, calculated from period
        - end_date: End date (datetime or string 'YYYY-MM-DD'). If None, uses today
        - period: Period string like '5y', '1y', '6mo' (used if start_date is None)

        Returns:
        - DataFrame with columns: open, high, low, close, volume, and datetime index
        """
        try:
            # Convert period to start_date if not provided
            if start_date is None:
                if period == '5y':
                    start_date = datetime.now() - timedelta(days=5*365)
                elif period == '1y':
                    start_date = datetime.now() - timedelta(days=365)
                elif period == '6mo':
                    start_date = datetime.now() - timedelta(days=180)
                else:
                    start_date = datetime.now() - timedelta(days=5*365)  # Default to 5 years
            elif isinstance(start_date, str):
                start_date = pd.to_datetime(start_date)

            # Set end_date to today if not provided
            if end_date is None:
                end_date = datetime.now()
            elif isinstance(end_date, str):
                end_date = pd.to_datetime(end_date)

            # Convert to Unix timestamps
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())

            # Fetch data from Finnhub
            result = self.client.stock_candles(
                ticker,
                'D',  # Daily resolution
                start_timestamp,
                end_timestamp
            )

            # Rate limiting
            time.sleep(self.rate_limit_delay)

            # Check if data is valid
            if result['s'] != 'ok':
                return None

            # Convert to DataFrame
            df = pd.DataFrame({
                'open': result['o'],
                'high': result['h'],
                'low': result['l'],
                'close': result['c'],
                'volume': result['v']
            })

            # Convert timestamps to datetime index
            df.index = pd.to_datetime(result['t'], unit='s')
            df.index.name = 'date'

            # Remove timezone info for consistency
            df.index = df.index.tz_localize(None)

            return df

        except Exception as e:
            print(f"Error fetching data for {ticker}: {str(e)}")
            return None

    def resample_to_3d(self, df):
        """
        Resample daily data to 3-day timeframe

        Parameters:
        - df: DataFrame with daily data

        Returns:
        - DataFrame resampled to 3-day intervals
        """
        if df is None or len(df) == 0:
            return None

        df_resampled = df.resample('3D').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        return df_resampled

    def resample_to_weekly(self, df):
        """
        Resample daily data to weekly timeframe

        Parameters:
        - df: DataFrame with daily data

        Returns:
        - DataFrame resampled to weekly intervals
        """
        if df is None or len(df) == 0:
            return None

        df_resampled = df.resample('W').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        return df_resampled


def get_data_fetcher():
    """
    Factory function to get data fetcher instance

    Returns:
    - FinnhubDataFetcher instance
    """
    return FinnhubDataFetcher()


if __name__ == "__main__":
    # Test the data fetcher
    print("Testing Finnhub Data Fetcher...")

    try:
        fetcher = get_data_fetcher()
        print("✓ API key found and client initialized")

        # Test fetching data
        print("\nFetching AAPL data (last 1 year)...")
        df = fetcher.fetch_historical_data('AAPL', period='1y')

        if df is not None:
            print(f"✓ Successfully fetched {len(df)} days of data")
            print(f"\nFirst few rows:")
            print(df.head())
            print(f"\nLast few rows:")
            print(df.tail())

            # Test resampling
            print("\nTesting 3-day resampling...")
            df_3d = fetcher.resample_to_3d(df)
            print(f"✓ Resampled to {len(df_3d)} 3-day candles")

        else:
            print("✗ Failed to fetch data")

    except ValueError as e:
        print(f"✗ Error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
