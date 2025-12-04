"""
Data Fetcher Module
Handles fetching historical stock data using Twelve Data API
"""

import os
import pandas as pd
import requests
from datetime import datetime, timedelta
import time


class TwelveDataFetcher:
    """
    Fetches stock data using Twelve Data API
    """

    def __init__(self):
        """Initialize Twelve Data client with API key from environment"""
        api_key = os.getenv('TWELVEDATA_API_KEY')

        if not api_key:
            raise ValueError(
                "TWELVEDATA_API_KEY environment variable not set. "
                "Set it with: export TWELVEDATA_API_KEY='your_key'"
            )

        self.api_key = api_key
        self.base_url = "https://api.twelvedata.com"

        # Rate limiting: Upgraded plan allows 55 calls/minute
        # 60 seconds / 55 calls = 1.09 seconds per call
        self.rate_limit_delay = 1.1  # 1.1 seconds = ~55 calls/minute

    def fetch_historical_data(self, ticker, start_date=None, end_date=None, period='5y', interval='1day'):
        """
        Fetch historical data for a ticker

        Parameters:
        - ticker: Stock ticker symbol
        - start_date: Start date (datetime or string 'YYYY-MM-DD'). If None, calculated from period
        - end_date: End date (datetime or string 'YYYY-MM-DD'). If None, uses today
        - period: Period string like '5y', '1y', '6mo' (used if start_date is None)
        - interval: Data interval (1min, 5min, 15min, 30min, 45min, 1h, 2h, 4h, 1day, 1week, 1month)

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
                elif period == '3mo':
                    start_date = datetime.now() - timedelta(days=90)
                elif period == '2y':
                    start_date = datetime.now() - timedelta(days=2*365)
                else:
                    start_date = datetime.now() - timedelta(days=5*365)  # Default to 5 years
            elif isinstance(start_date, str):
                start_date = pd.to_datetime(start_date)

            # Set end_date to today if not provided
            if end_date is None:
                end_date = datetime.now()
            elif isinstance(end_date, str):
                end_date = pd.to_datetime(end_date)

            # Format dates for API
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')

            # Build API request
            # Note: Twelve Data uses 'outputsize=5000' to get max data points
            params = {
                'symbol': ticker,
                'interval': interval,
                'apikey': self.api_key,
                'start_date': start_date_str,
                'end_date': end_date_str,
                'outputsize': 5000,  # Maximum data points
                'format': 'JSON'
            }

            # Make API request
            response = requests.get(f"{self.base_url}/time_series", params=params)

            # Rate limiting
            time.sleep(self.rate_limit_delay)

            # Check for errors
            if response.status_code != 200:
                print(f"API error for {ticker}: {response.status_code}")
                return None

            data = response.json()

            # Check for API errors in response
            if 'status' in data and data['status'] == 'error':
                print(f"API error for {ticker}: {data.get('message', 'Unknown error')}")
                return None

            # Check if data exists
            if 'values' not in data or not data['values']:
                return None

            # Convert to DataFrame
            df = pd.DataFrame(data['values'])

            # Rename columns to match our standard
            df = df.rename(columns={
                'datetime': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })

            # Convert data types
            df['open'] = pd.to_numeric(df['open'], errors='coerce')
            df['high'] = pd.to_numeric(df['high'], errors='coerce')
            df['low'] = pd.to_numeric(df['low'], errors='coerce')
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

            # Set datetime index
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            df = df.sort_index()  # Twelve Data returns newest first, we want oldest first

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
    - TwelveDataFetcher instance
    """
    return TwelveDataFetcher()


if __name__ == "__main__":
    # Test the data fetcher
    print("Testing Twelve Data Fetcher...")

    try:
        fetcher = get_data_fetcher()
        print("✓ API key found and client initialized")

        # Test fetching data
        print("\nFetching AAPL data (last 1 year, daily)...")
        df = fetcher.fetch_historical_data('AAPL', period='1y', interval='1day')

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

            # Test intraday (4h)
            print("\nFetching AAPL data (4-hour, last 60 days)...")
            df_4h = fetcher.fetch_historical_data('AAPL', period='3mo', interval='4h')
            if df_4h is not None:
                print(f"✓ Successfully fetched {len(df_4h)} 4-hour candles")
            else:
                print("✗ Failed to fetch 4h data")

        else:
            print("✗ Failed to fetch data")

    except ValueError as e:
        print(f"✗ Error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
