"""
Main scanner for RSI divergence detection
"""
from typing import List
import config
from data_fetcher import get_nasdaq100_tickers, fetch_stock_data
from rsi_divergence_detector import detect_divergence
from logger import DivergenceLogger


class RSIDivergenceScanner:
    """Scans stocks for RSI divergences"""

    def __init__(self):
        self.logger = DivergenceLogger()
        self.tickers = []
        self.total_divergences = 0

    def load_tickers(self, custom_tickers: List[str] = None):
        """Load ticker symbols to scan"""
        if custom_tickers:
            self.tickers = custom_tickers
            print(f"Using custom ticker list: {len(self.tickers)} tickers")
        else:
            self.tickers = get_nasdaq100_tickers()

    def scan_ticker(self, ticker: str, timeframe: str):
        """
        Scan a single ticker for divergences on one timeframe

        Args:
            ticker: Stock ticker
            timeframe: Timeframe to analyze
        """
        # Fetch data
        df = fetch_stock_data(ticker, timeframe)

        if df.empty:
            return

        # Detect divergences
        divergences = detect_divergence(df)

        if divergences:
            # Log to CSV
            self.logger.log_signals(ticker, timeframe, divergences)
            self.total_divergences += len(divergences)

    def scan_all(self):
        """Scan all tickers across all timeframes"""
        print(f"\n{'='*60}")
        print(f"Starting RSI Divergence Scan")
        print(f"Tickers: {len(self.tickers)}")
        print(f"Timeframes: {', '.join(config.TIMEFRAMES)}")
        print(f"{'='*60}\n")

        self.total_divergences = 0
        processed = 0
        errors = 0

        for ticker in self.tickers:
            try:
                print(f"Scanning {ticker}...", end=' ', flush=True)
                ticker_divergences = 0

                for timeframe in config.TIMEFRAMES:
                    self.scan_ticker(ticker, timeframe)

                print(f"✓")
                processed += 1

            except Exception as e:
                print(f"✗ Error: {e}")
                errors += 1

        # Summary
        print(f"\n{'='*60}")
        print(f"SCAN COMPLETE")
        print(f"{'='*60}")
        print(f"Tickers processed: {processed}")
        print(f"Errors: {errors}")
        print(f"Total divergences found: {self.total_divergences}")
        print(f"{'='*60}\n")

    def quick_scan(self, tickers: List[str]):
        """Quick scan of specific tickers"""
        self.load_tickers(tickers)
        self.scan_all()
