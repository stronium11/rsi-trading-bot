"""
Market Scanner Module
Scans market data for RSI divergences across multiple tickers and timeframes
"""

import pandas as pd
from datetime import datetime, timedelta
import time
from rsi_divergence_detector import calculate_rsi, detect_divergence, extract_divergence_signals
from signal_logger import SignalLogger
from nasdaq100_tickers import get_nasdaq100_tickers
from sp500_tickers import get_sp500_tickers
from data_fetcher import get_data_fetcher


class MarketScanner:
    """
    Scans market data for RSI divergences
    """

    def __init__(self, logger=None):
        """
        Initialize the market scanner

        Parameters:
        - logger: SignalLogger instance (optional)
        """
        self.logger = logger or SignalLogger()
        self.timeframes = ['4h', '1d', '1w']

        # Combine Nasdaq 100 and S&P 500 tickers, remove duplicates
        nasdaq_tickers = get_nasdaq100_tickers()
        sp500_tickers = get_sp500_tickers()
        combined = list(set(nasdaq_tickers + sp500_tickers))
        self.tickers = sorted(combined)  # Sort alphabetically for consistent order

        # Initialize Finnhub data fetcher
        self.data_fetcher = get_data_fetcher()

    def fetch_data(self, ticker, timeframe, period='3mo'):
        """
        Fetch market data for a ticker and timeframe using Finnhub

        NOTE: Finnhub free tier only supports daily data (no intraday/hourly).
        4h timeframe is not supported with Finnhub free tier.

        Parameters:
        - ticker: Stock ticker symbol
        - timeframe: Timeframe interval (1d or 1w supported)
        - period: Data period to fetch

        Returns:
        - DataFrame with market data or None if error
        """
        try:
            # Finnhub free tier limitation: no intraday data (4h not supported)
            if timeframe == '4h':
                print(f"Warning: 4h timeframe not supported with Finnhub free tier. Skipping {ticker}.")
                return None

            # Adjust period based on timeframe
            if timeframe == '1d':
                period = '6mo'  # 6 months for daily
            elif timeframe == '1w':
                period = '2y'   # 2 years for weekly
            else:
                period = '6mo'  # Default

            # Fetch data using Finnhub
            df = self.data_fetcher.fetch_historical_data(ticker, period=period)

            if df is None or len(df) == 0:
                return None

            # Resample for weekly timeframe if needed
            if timeframe == '1w':
                df = self.data_fetcher.resample_to_weekly(df)

            return df

        except Exception as e:
            print(f"Error fetching data for {ticker} ({timeframe}): {str(e)}")
            return None

    def scan_ticker(self, ticker, timeframe):
        """
        Scan a single ticker for RSI divergences

        Parameters:
        - ticker: Stock ticker symbol
        - timeframe: Timeframe to scan

        Returns:
        - List of signals detected
        """
        try:
            # Fetch data
            df = self.fetch_data(ticker, timeframe)

            if df is None or len(df) < 50:
                return []

            # Calculate RSI
            rsi_values = calculate_rsi(df)

            # Detect divergences
            df_with_divergence = detect_divergence(df, rsi_values)

            # Extract signals
            signals = extract_divergence_signals(df_with_divergence, ticker, timeframe)

            return signals

        except Exception as e:
            print(f"Error scanning {ticker} ({timeframe}): {str(e)}")
            return []

    def scan_all_tickers(self, timeframes=None):
        """
        Scan all tickers across specified timeframes

        Parameters:
        - timeframes: List of timeframes to scan (default: all configured timeframes)

        Returns:
        - Dictionary with scan statistics
        """
        if timeframes is None:
            timeframes = self.timeframes

        all_signals = []
        scan_stats = {
            'total_tickers': len(self.tickers),
            'total_timeframes': len(timeframes),
            'signals_found': 0,
            'tickers_scanned': 0,
            'errors': 0,
            'start_time': datetime.now()
        }

        print(f"\n{'='*60}")
        print(f"RSI DIVERGENCE SCANNER")
        print(f"{'='*60}")
        print(f"Scanning Nasdaq 100 + S&P 500 stocks")
        print(f"Total unique tickers: {len(self.tickers)}")
        print(f"Timeframes: {', '.join(timeframes)}")
        print(f"Started at: {scan_stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        # Scan each ticker across all timeframes
        for idx, ticker in enumerate(self.tickers, 1):
            try:
                ticker_signals = []

                for timeframe in timeframes:
                    signals = self.scan_ticker(ticker, timeframe)
                    ticker_signals.extend(signals)

                    # Rate limiting to avoid overwhelming API
                    time.sleep(0.5)

                if ticker_signals:
                    all_signals.extend(ticker_signals)
                    print(f"[{idx}/{len(self.tickers)}] {ticker}: Found {len(ticker_signals)} signals")
                else:
                    print(f"[{idx}/{len(self.tickers)}] {ticker}: No signals")

                scan_stats['tickers_scanned'] += 1

            except Exception as e:
                print(f"[{idx}/{len(self.tickers)}] {ticker}: Error - {str(e)}")
                scan_stats['errors'] += 1

        # Log all signals
        if all_signals:
            self.logger.log_signals(all_signals)
            scan_stats['signals_found'] = len(all_signals)

        scan_stats['end_time'] = datetime.now()
        scan_stats['duration'] = scan_stats['end_time'] - scan_stats['start_time']

        # Print summary
        print(f"\n{'='*60}")
        print(f"SCAN COMPLETE")
        print(f"{'='*60}")
        print(f"Tickers scanned: {scan_stats['tickers_scanned']}/{scan_stats['total_tickers']}")
        print(f"Signals found: {scan_stats['signals_found']}")
        print(f"Errors: {scan_stats['errors']}")
        print(f"Duration: {scan_stats['duration']}")
        print(f"{'='*60}\n")

        return scan_stats

    def scan_single_ticker(self, ticker, timeframes=None):
        """
        Scan a single ticker across specified timeframes

        Parameters:
        - ticker: Stock ticker symbol
        - timeframes: List of timeframes to scan (default: all configured timeframes)

        Returns:
        - List of signals found
        """
        if timeframes is None:
            timeframes = self.timeframes

        all_signals = []

        print(f"\n{'='*60}")
        print(f"Scanning {ticker} across {len(timeframes)} timeframes")
        print(f"Timeframes: {', '.join(timeframes)}")
        print(f"{'='*60}\n")

        for timeframe in timeframes:
            signals = self.scan_ticker(ticker, timeframe)

            if signals:
                all_signals.extend(signals)
                print(f"{ticker} ({timeframe}): Found {len(signals)} signals")
            else:
                print(f"{ticker} ({timeframe}): No signals")

            time.sleep(0.5)

        # Log signals
        if all_signals:
            self.logger.log_signals(all_signals)

        print(f"\n{'='*60}")
        print(f"Total signals found for {ticker}: {len(all_signals)}")
        print(f"{'='*60}\n")

        return all_signals
