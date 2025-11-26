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

    def __init__(self, target_date: str = None):
        self.deduplicator = SignalDeduplicator()
        self.logger = SignalLogger()
        self.tickers = []
        self.all_signals = []
        self.target_date = target_date  # Format: 'YYYY-MM-DD'

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

    def scan_ticker(self, ticker: str, debug: bool = False) -> List[Dict]:
        """
        Scan a single ticker for signals across all timeframes

        Args:
            ticker: Stock ticker symbol
            debug: If True, print detailed debug information

        Returns:
            List of signals found
        """
        signals = []

        # Fetch daily data
        df = fetch_stock_data(ticker)
        if df.empty:
            return signals

        # Filter data up to target date if specified
        if self.target_date:
            import pandas as pd
            target_dt = pd.to_datetime(self.target_date)
            # Handle timezone-aware datetime index
            if df.index.tz is not None:
                target_dt = target_dt.tz_localize(df.index.tz)
            df = df[df.index <= target_dt]
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

            if debug and trend is None:
                # Show why no trend was detected
                if len(df_timeframe) > 0:
                    latest = df_timeframe.iloc[-1]
                    print(f"  [{timeframe}] No valid trend - SMA50: {latest.get('SMA_50', 'N/A'):.2f}, SMA100: {latest.get('SMA_100', 'N/A'):.2f}, SMA200: {latest.get('SMA_200', 'N/A'):.2f}")

            if trend is None:
                continue  # No valid trend, skip this timeframe

            # Detect signals
            timeframe_signals = detect_signals(df_timeframe, ticker, timeframe, trend)

            if debug:
                if timeframe_signals:
                    print(f"  [{timeframe}] {trend} trend - Found {len(timeframe_signals)} signal(s)")
                else:
                    latest = df_timeframe.iloc[-1]
                    print(f"  [{timeframe}] {trend} trend - No signals (Price: ${latest['Close']:.2f})")

            signals.extend(timeframe_signals)

        return signals

    def scan_all(self, debug: bool = False):
        """Scan all tickers and log signals

        Args:
            debug: If True, print detailed debug information for each ticker
        """
        print(f"\n{'='*60}")
        if self.target_date:
            print(f"Starting scan of {len(self.tickers)} tickers for date: {self.target_date}")
        else:
            print(f"Starting scan of {len(self.tickers)} tickers...")
        if debug:
            print("DEBUG MODE: Showing detailed filtering info")
        print(f"{'='*60}\n")

        self.all_signals = []
        processed = 0
        errors = 0

        for ticker in self.tickers:
            try:
                if debug:
                    print(f"\nScanning {ticker}:")
                else:
                    print(f"Scanning {ticker}... ", end='', flush=True)

                signals = self.scan_ticker(ticker, debug=debug)

                if signals:
                    # Filter duplicates
                    unique_signals = self.deduplicator.filter_duplicates(signals)

                    if unique_signals:
                        self.all_signals.extend(unique_signals)
                        if not debug:
                            print(f"✓ Found {len(unique_signals)} new signal(s)")
                    else:
                        if debug:
                            print(f"  → Signals filtered as duplicates")
                        else:
                            print("✓ (signals filtered as duplicates)")
                else:
                    if not debug:
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

    def quick_scan(self, tickers: List[str], debug: bool = False):
        """
        Quick scan of specific tickers (for testing)

        Args:
            tickers: List of ticker symbols
            debug: If True, print detailed debug information
        """
        self.load_tickers(tickers)
        self.scan_all(debug=debug)
