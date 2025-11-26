"""
Main scanner module - orchestrates the entire signal detection process
"""
import pandas as pd
from typing import List, Dict
import config
from data_fetcher import get_nasdaq100_tickers, fetch_stock_data, resample_to_timeframe
from sma_calculator import calculate_smas
from trend_validator import validate_trend
from signal_detector import detect_signals
from deduplicator import SignalDeduplicator
from logger import SignalLogger


class TradingSignalScanner:
    """Main scanner class that coordinates all components"""

    def __init__(self):
        self.deduplicator = SignalDeduplicator()
        self.logger = SignalLogger()
        self.tickers = []
        self.all_signals = []

    def load_tickers(self, custom_tickers: List[str] = None):
        """
        Load ticker symbols to scan

        Args:
            custom_tickers: Optional list of custom tickers (for testing)
        """
        if custom_tickers:
            self.tickers = custom_tickers
            print(f"Using custom ticker list: {len(self.tickers)} tickers")
        else:
            self.tickers = get_nasdaq100_tickers()
            print(f"Loaded NASDAQ 100 tickers: {len(self.tickers)} tickers")

    def scan_ticker(self, ticker: str) -> List[Dict]:
        """
        Scan a single ticker for signals across all timeframes

        Args:
            ticker: Stock ticker symbol

        Returns:
            List of signals found
        """
        signals = []

        # Fetch daily data
        df = fetch_stock_data(ticker)
        if df.empty:
            return signals

        # Process each timeframe
        for timeframe, settings in config.TIMEFRAMES.items():
            # Resample data to timeframe
            df_timeframe = resample_to_timeframe(df.copy(), timeframe)

            if df_timeframe.empty:
                continue

            # Calculate SMAs
            df_timeframe = calculate_smas(df_timeframe)

            # Validate trend (includes separation and stability checks)
            trend = validate_trend(df_timeframe, settings['stability_check_days'])

            if trend is None:
                continue  # No valid trend, skip this timeframe

            # Detect signals
            timeframe_signals = detect_signals(df_timeframe, ticker, timeframe, trend)
            signals.extend(timeframe_signals)

        return signals

    def scan_all(self):
        """Scan all tickers and log signals"""
        print(f"\n{'='*60}")
        print(f"Starting scan of {len(self.tickers)} tickers...")
        print(f"{'='*60}\n")

        self.all_signals = []
        processed = 0
        errors = 0

        for ticker in self.tickers:
            try:
                print(f"Scanning {ticker}... ", end='', flush=True)
                signals = self.scan_ticker(ticker)

                if signals:
                    # Filter duplicates
                    unique_signals = self.deduplicator.filter_duplicates(signals)

                    if unique_signals:
                        self.all_signals.extend(unique_signals)
                        print(f"✓ Found {len(unique_signals)} new signal(s)")
                    else:
                        print("✓ (signals filtered as duplicates)")
                else:
                    print("✓ (no signals)")

                processed += 1

            except Exception as e:
                print(f"✗ Error: {e}")
                errors += 1

        # Log all signals
        if self.all_signals:
            self.logger.log_signals(self.all_signals)

        # Print summary
        print(f"\n{'='*60}")
        print(f"SCAN COMPLETE")
        print(f"{'='*60}")
        print(f"Tickers processed: {processed}")
        print(f"Errors: {errors}")
        print(f"Total new signals found: {len(self.all_signals)}")
        print(f"{'='*60}\n")

        if self.all_signals:
            self._print_signals()

    def _print_signals(self):
        """Print signals in a readable format"""
        print("\nNEW SIGNALS DETECTED:\n")
        for signal in self.all_signals:
            print(f"{signal['date']} | {signal['ticker']:6} | "
                  f"SMA-{signal['sma_period']:3} | {signal['timeframe']:3} | "
                  f"{signal['trend']:8} | Price: ${signal['price']:8.2f} | "
                  f"SMA: ${signal['sma_value']:8.2f} | "
                  f"Distance: {signal['distance_pct']:.3f}%")

    def quick_scan(self, tickers: List[str]):
        """
        Quick scan of specific tickers (for testing)

        Args:
            tickers: List of ticker symbols
        """
        self.load_tickers(tickers)
        self.scan_all()
