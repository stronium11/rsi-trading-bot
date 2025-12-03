"""
Backtest Historical Data Scanner
Scans 5 years of historical data for RSI divergences
Used for backtesting trading strategies
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time
from rsi_divergence_detector import calculate_rsi, detect_divergence
from nasdaq100_tickers import get_nasdaq100_tickers
from sp500_tickers import get_sp500_tickers


class BacktestScanner:
    """
    Scans historical data for backtesting purposes
    """

    def __init__(self):
        """
        Initialize the backtest scanner
        """
        self.timeframes = ['1d', '3d', '1w']  # Only daily and weekly for backtesting

        # Combine Nasdaq 100 and S&P 500 tickers, remove duplicates
        nasdaq_tickers = get_nasdaq100_tickers()
        sp500_tickers = get_sp500_tickers()
        combined = list(set(nasdaq_tickers + sp500_tickers))
        self.tickers = sorted(combined)

    def fetch_historical_data(self, ticker, timeframe):
        """
        Fetch 5 years of historical data

        Parameters:
        - ticker: Stock ticker symbol
        - timeframe: Timeframe interval (1d, 3d, 1w)

        Returns:
        - DataFrame with historical data or None if error
        """
        try:
            # Map timeframes to yfinance intervals
            interval_map = {
                '1d': '1d',
                '3d': '1d',  # Will resample daily to 3d
                '1w': '1wk'
            }

            interval = interval_map.get(timeframe, '1d')

            # Fetch 5 years of data
            period = '5y'

            df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)

            if df.empty:
                return None

            # Handle MultiIndex columns (newer yfinance versions)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Rename columns to lowercase
            df.columns = [col.lower() for col in df.columns]

            # Resample for 3d timeframe
            if timeframe == '3d' and interval == '1d':
                df = df.resample('3D').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()

            return df

        except Exception as e:
            print(f"Error fetching data for {ticker} ({timeframe}): {str(e)}")
            return None

    def get_next_trading_day_close(self, df, signal_date):
        """
        Get the close price of the next trading day after signal

        Parameters:
        - df: DataFrame with price data
        - signal_date: Date when signal was detected

        Returns:
        - Tuple of (entry_date, entry_price) or (None, None) if not found
        """
        try:
            # Find all dates after signal_date
            future_dates = df.index[df.index > signal_date]

            if len(future_dates) == 0:
                return None, None

            # Get the next trading day (first date after signal)
            entry_date = future_dates[0]
            entry_price = df.loc[entry_date, 'close']

            return entry_date, float(entry_price)

        except Exception as e:
            return None, None

    def extract_all_divergences(self, df, ticker, timeframe):
        """
        Extract ALL divergences from the dataframe (no time filter)

        Parameters:
        - df: DataFrame with divergence detection results
        - ticker: Stock ticker symbol
        - timeframe: Timeframe of the data

        Returns:
        - List of signal dictionaries with entry prices
        """
        signals = []

        if len(df) == 0:
            return signals

        # Extract bearish divergences
        bearish = df[df['bearish_divergence'] == True]
        for idx, row in bearish.iterrows():
            # Get next day's entry price
            entry_date, entry_price = self.get_next_trading_day_close(df, idx)

            if entry_date is None:
                continue  # Skip if no next trading day available

            signal = {
                'ticker': ticker,
                'timeframe': timeframe,
                'signal_date': idx,
                'divergence_type': 'Bearish',
                'signal_close': float(df.loc[idx, 'close']),
                'entry_date': entry_date,
                'entry_price': entry_price,
                'first_peak_price': float(row['divergence_first_peak_price']),
                'second_peak_price': float(row['divergence_second_peak_price']),
                'first_peak_rsi': float(row['divergence_first_peak_rsi']),
                'second_peak_rsi': float(row['divergence_second_peak_rsi'])
            }
            signals.append(signal)

        # Extract bullish divergences
        bullish = df[df['bullish_divergence'] == True]
        for idx, row in bullish.iterrows():
            # Get next day's entry price
            entry_date, entry_price = self.get_next_trading_day_close(df, idx)

            if entry_date is None:
                continue  # Skip if no next trading day available

            signal = {
                'ticker': ticker,
                'timeframe': timeframe,
                'signal_date': idx,
                'divergence_type': 'Bullish',
                'signal_close': float(df.loc[idx, 'close']),
                'entry_date': entry_date,
                'entry_price': entry_price,
                'first_peak_price': float(row['divergence_first_peak_price']),
                'second_peak_price': float(row['divergence_second_peak_price']),
                'first_peak_rsi': float(row['divergence_first_peak_rsi']),
                'second_peak_rsi': float(row['divergence_second_peak_rsi'])
            }
            signals.append(signal)

        return signals

    def scan_ticker(self, ticker, timeframe):
        """
        Scan a single ticker for historical divergences

        Parameters:
        - ticker: Stock ticker symbol
        - timeframe: Timeframe to scan

        Returns:
        - List of signals with entry prices
        """
        try:
            # Fetch historical data
            df = self.fetch_historical_data(ticker, timeframe)

            if df is None or len(df) < 50:
                return []

            # Calculate RSI
            rsi_values = calculate_rsi(df)

            # Detect divergences
            df_with_divergence = detect_divergence(df, rsi_values)

            # Extract all divergences (no time limit)
            signals = self.extract_all_divergences(df_with_divergence, ticker, timeframe)

            return signals

        except Exception as e:
            print(f"Error scanning {ticker} ({timeframe}): {str(e)}")
            return []

    def scan_all_tickers(self, output_csv='backtest/backtest_signals.csv'):
        """
        Scan all tickers for 5 years of historical divergences

        Parameters:
        - output_csv: Path to save signals CSV

        Returns:
        - DataFrame with all signals
        """
        all_signals = []

        print(f"\n{'='*70}")
        print(f"BACKTEST HISTORICAL SCANNER - 5 YEAR ANALYSIS")
        print(f"{'='*70}")
        print(f"Scanning Nasdaq 100 + S&P 500 stocks")
        print(f"Total unique tickers: {len(self.tickers)}")
        print(f"Timeframes: {', '.join(self.timeframes)}")
        print(f"Period: 5 years of historical data")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")

        start_time = datetime.now()

        # Scan each ticker
        for idx, ticker in enumerate(self.tickers, 1):
            try:
                ticker_signals = []

                for timeframe in self.timeframes:
                    signals = self.scan_ticker(ticker, timeframe)
                    ticker_signals.extend(signals)

                    # Rate limiting
                    time.sleep(0.5)

                if ticker_signals:
                    all_signals.extend(ticker_signals)
                    print(f"[{idx}/{len(self.tickers)}] {ticker}: Found {len(ticker_signals)} signals")
                else:
                    print(f"[{idx}/{len(self.tickers)}] {ticker}: No signals")

            except Exception as e:
                print(f"[{idx}/{len(self.tickers)}] {ticker}: Error - {str(e)}")

        # Convert to DataFrame
        if all_signals:
            df_signals = pd.DataFrame(all_signals)

            # Create backtest directory if it doesn't exist
            import os
            os.makedirs('backtest', exist_ok=True)

            # Save to CSV
            df_signals.to_csv(output_csv, index=False)

            print(f"\n{'='*70}")
            print(f"SCAN COMPLETE")
            print(f"{'='*70}")
            print(f"Total signals found: {len(all_signals)}")
            print(f"Signals saved to: {output_csv}")
            print(f"Duration: {datetime.now() - start_time}")
            print(f"{'='*70}\n")

            return df_signals
        else:
            print(f"\n{'='*70}")
            print(f"No signals found")
            print(f"{'='*70}\n")
            return pd.DataFrame()


if __name__ == "__main__":
    scanner = BacktestScanner()
    signals_df = scanner.scan_all_tickers()

    if not signals_df.empty:
        print(f"\nSignals Summary:")
        print(f"Bullish signals: {len(signals_df[signals_df['divergence_type'] == 'Bullish'])}")
        print(f"Bearish signals: {len(signals_df[signals_df['divergence_type'] == 'Bearish'])}")
        print(f"\nBy Timeframe:")
        print(signals_df.groupby('timeframe').size())
