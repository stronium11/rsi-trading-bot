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
        """Load ticker symbols"""
        if custom_tickers:
            self.tickers = custom_tickers
            print(f"Using custom list: {len(self.tickers)} tickers")
        else:
            self.tickers = get_nasdaq100_tickers()

    def scan_ticker(self, ticker: str, timeframe: str):
        """Scan a single ticker for divergences"""
        df = fetch_stock_data(ticker, timeframe)

        if df.empty:
            return 0

        divergences = detect_divergence(df)

        if divergences:
            self.logger.log_signals(ticker, timeframe, divergences)
            return len(divergences)

        return 0

    def scan_all(self):
        """Scan all tickers across all timeframes"""
        print(f"\n{'='*60}")
        print(f"RSI Divergence Scan")
        print(f"Tickers: {len(self.tickers)} | Timeframes: {', '.join(config.TIMEFRAMES)}")
        print(f"{'='*60}\n")

        self.total_divergences = 0
        processed = 0

        for ticker in self.tickers:
            try:
                print(f"Scanning {ticker}... ", end='', flush=True)
                count = 0

                for timeframe in config.TIMEFRAMES:
                    count += self.scan_ticker(ticker, timeframe)

                if count > 0:
                    print(f"✓ Found {count} divergence(s)")
                else:
                    print(f"✓")

                self.total_divergences += count
                processed += 1

            except Exception as e:
                print(f"✗ Error: {e}")

        print(f"\n{'='*60}")
        print(f"COMPLETE - Processed: {processed} | Total Divergences: {self.total_divergences}")
        print(f"{'='*60}\n")
