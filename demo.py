#!/usr/bin/env python3
"""
Demo script to test the signal system with generated data
"""
from scanner import TradingSignalScanner
from logger import SignalLogger
import data_fetcher
from demo_data import generate_signal_demo_data


# Monkey patch the fetch function to use demo data
original_fetch = data_fetcher.fetch_stock_data

def demo_fetch_stock_data(ticker: str, period: str = None):
    """Use demo data instead of real data"""
    print(f"[DEMO MODE] Generating demo data for {ticker}")
    return generate_signal_demo_data(ticker)

data_fetcher.fetch_stock_data = demo_fetch_stock_data


def main():
    print("\n" + "="*60)
    print("DEMO MODE - Using Generated Data")
    print("="*60 + "\n")

    scanner = TradingSignalScanner()

    # Test with a few demo tickers
    demo_tickers = ['DEMO_AAPL', 'DEMO_MSFT', 'DEMO_GOOGL', 'DEMO_NVDA']

    scanner.quick_scan(demo_tickers)

    # Show summary
    logger = SignalLogger()
    logger.print_summary()


if __name__ == '__main__':
    main()
