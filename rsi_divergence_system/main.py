#!/usr/bin/env python3
"""
RSI Divergence Signal System - Main Entry Point
Scans Nasdaq 100 stocks for RSI divergences across multiple timeframes
"""

import argparse
import sys
from market_scanner import MarketScanner
from signal_logger import SignalLogger


def main():
    """
    Main function to run the RSI divergence scanner
    """
    parser = argparse.ArgumentParser(
        description='RSI Divergence Detection System for Nasdaq 100',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan all Nasdaq 100 tickers across all timeframes (4h, 1d, 1w)
  python main.py

  # Scan a single ticker
  python main.py --ticker AAPL

  # Scan specific timeframes only
  python main.py --timeframes 4h 1d

  # Scan a single ticker with specific timeframes
  python main.py --ticker TSLA --timeframes 1d 1w

  # View recent signals
  python main.py --view-signals 20
        """
    )

    parser.add_argument(
        '--ticker',
        type=str,
        help='Scan a specific ticker symbol (e.g., AAPL)'
    )

    parser.add_argument(
        '--timeframes',
        type=str,
        nargs='+',
        choices=['4h', '1d', '1w'],
        help='Specific timeframes to scan (default: 4h, 1d, 1w)'
    )

    parser.add_argument(
        '--view-signals',
        type=int,
        metavar='N',
        help='View the N most recent signals and exit'
    )

    parser.add_argument(
        '--csv-path',
        type=str,
        default='logs/rsi_divergence_signals.csv',
        help='Path to CSV file for logging signals (default: logs/rsi_divergence_signals.csv)'
    )

    args = parser.parse_args()

    # Initialize logger
    logger = SignalLogger(csv_path=args.csv_path)

    # View signals mode
    if args.view_signals:
        print(f"\n{'='*60}")
        print(f"RECENT RSI DIVERGENCE SIGNALS (Last {args.view_signals})")
        print(f"{'='*60}\n")

        recent_signals = logger.get_recent_signals(n=args.view_signals)

        if recent_signals.empty:
            print("No signals found in the log file.")
        else:
            print(recent_signals.to_string(index=False))

        print(f"\nTotal signals in database: {logger.get_signal_count()}")
        print(f"CSV file location: {args.csv_path}\n")
        return

    # Initialize scanner
    scanner = MarketScanner(logger=logger)

    # Scan mode
    if args.ticker:
        # Scan single ticker
        signals = scanner.scan_single_ticker(
            ticker=args.ticker.upper(),
            timeframes=args.timeframes
        )

        if signals:
            print(f"\nSignals have been logged to: {args.csv_path}")
        else:
            print(f"\nNo signals detected for {args.ticker.upper()}")

    else:
        # Scan all tickers
        print("\nStarting full market scan of Nasdaq 100 stocks...")
        print("This may take several minutes due to API rate limiting.\n")

        stats = scanner.scan_all_tickers(timeframes=args.timeframes)

        if stats['signals_found'] > 0:
            print(f"\nSignals have been logged to: {args.csv_path}")
            print(f"\nTo view recent signals, run:")
            print(f"  python main.py --view-signals 20")
        else:
            print(f"\nNo signals detected in this scan.")

        print(f"\nTotal signals in database: {logger.get_signal_count()}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user. Exiting gracefully...\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {str(e)}\n")
        sys.exit(1)
