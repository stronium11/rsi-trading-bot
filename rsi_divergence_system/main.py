#!/usr/bin/env python3
"""
RSI Divergence Detection System - Main Entry Point

Usage:
    python main.py                           # Scan all NASDAQ 100
    python main.py --test                    # Test with sample stocks
    python main.py --tickers AAPL MSFT NVDA  # Scan specific tickers
    python main.py --summary                 # View summary
"""
import argparse
from scanner import RSIDivergenceScanner
from logger import DivergenceLogger


def main():
    parser = argparse.ArgumentParser(
        description='RSI Divergence Detection System',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--test',
        action='store_true',
        help='Test with sample tickers'
    )

    parser.add_argument(
        '--tickers',
        nargs='+',
        help='Scan specific ticker symbols'
    )

    parser.add_argument(
        '--summary',
        action='store_true',
        help='Display summary and exit'
    )

    args = parser.parse_args()

    # Show summary
    if args.summary:
        logger = DivergenceLogger()
        logger.get_summary()
        return

    # Initialize scanner
    scanner = RSIDivergenceScanner()

    # Run scan
    if args.test:
        print("\n🔍 Running TEST scan...")
        test_tickers = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'META']
        scanner.quick_scan(test_tickers)
    elif args.tickers:
        print(f"\n🔍 Scanning: {', '.join(args.tickers)}")
        scanner.quick_scan(args.tickers)
    else:
        print("\n🔍 Scanning all NASDAQ 100...")
        scanner.load_tickers()
        scanner.scan_all()

    # Show summary
    print("\n📊 Summary:")
    logger = DivergenceLogger()
    logger.get_summary()


if __name__ == '__main__':
    main()
