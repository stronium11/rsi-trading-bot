#!/usr/bin/env python3
"""
RSI Divergence Detection System

Usage:
    python main.py                    # Scan all NASDAQ 100
    python main.py --test             # Test with sample stocks
    python main.py --tickers AAPL MSFT  # Scan specific tickers
    python main.py --summary          # View summary
"""
import argparse
from scanner import RSIDivergenceScanner
from logger import DivergenceLogger


def main():
    parser = argparse.ArgumentParser(description='RSI Divergence Detection System')

    parser.add_argument('--test', action='store_true', help='Test with sample tickers')
    parser.add_argument('--tickers', nargs='+', help='Scan specific tickers')
    parser.add_argument('--summary', action='store_true', help='Show summary')

    args = parser.parse_args()

    if args.summary:
        logger = DivergenceLogger()
        logger.get_summary()
        return

    scanner = RSIDivergenceScanner()

    if args.test:
        print("\n🔍 TEST SCAN")
        scanner.load_tickers(['AAPL', 'MSFT', 'NVDA', 'TSLA', 'META'])
        scanner.scan_all()
    elif args.tickers:
        print(f"\n🔍 Scanning: {', '.join(args.tickers)}")
        scanner.load_tickers(args.tickers)
        scanner.scan_all()
    else:
        print("\n🔍 FULL NASDAQ 100 SCAN")
        scanner.load_tickers()
        scanner.scan_all()

    logger = DivergenceLogger()
    logger.get_summary()


if __name__ == '__main__':
    main()
