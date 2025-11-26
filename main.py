#!/usr/bin/env python3
"""
SMA Trading Signal System - Main Entry Point

Usage:
    python main.py                    # Scan all NASDAQ 100 stocks
    python main.py --test             # Test with a few sample stocks
    python main.py --tickers AAPL MSFT GOOGL  # Scan specific tickers
    python main.py --summary          # Show summary of logged signals
"""
import argparse
from scanner import TradingSignalScanner
from logger import SignalLogger


def main():
    parser = argparse.ArgumentParser(
        description='SMA Trading Signal Detection System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                           # Scan all NASDAQ 100
  python main.py --test                    # Test with sample stocks
  python main.py --tickers AAPL MSFT NVDA  # Scan specific stocks
  python main.py --summary                 # View signal summary
        """
    )

    parser.add_argument(
        '--test',
        action='store_true',
        help='Run test scan with sample tickers (AAPL, MSFT, GOOGL, NVDA, TSLA)'
    )

    parser.add_argument(
        '--tickers',
        nargs='+',
        help='Scan specific ticker symbols'
    )

    parser.add_argument(
        '--summary',
        action='store_true',
        help='Display summary of logged signals and exit'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Show detailed debug information (why signals are filtered)'
    )

    args = parser.parse_args()

    # Show summary and exit
    if args.summary:
        logger = SignalLogger()
        logger.print_summary()
        return

    # Initialize scanner
    scanner = TradingSignalScanner()

    # Run appropriate scan
    if args.test:
        print("\n🔍 Running TEST scan with sample tickers...")
        test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'META', 'AMZN']
        scanner.load_tickers(test_tickers)
        scanner.scan_all(debug=args.debug)
    elif args.tickers:
        print(f"\n🔍 Scanning specific tickers: {', '.join(args.tickers)}")
        scanner.load_tickers(args.tickers)
        scanner.scan_all(debug=args.debug)
    else:
        print("\n🔍 Running FULL scan of NASDAQ 100...")
        scanner.load_tickers()
        scanner.scan_all(debug=args.debug)

    # Show summary after scan
    print("\n📊 Displaying signal summary...")
    logger = SignalLogger()
    logger.print_summary()


if __name__ == '__main__':
    main()
