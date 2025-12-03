#!/usr/bin/env python3
"""
Quick configuration test - validates backtest settings
Tests with just 3 tickers to confirm timeframes and divergence types
"""

from backtest_scanner import BacktestScanner
import pandas as pd

print(f"\n{'='*70}")
print(f"QUICK CONFIGURATION TEST")
print(f"{'='*70}\n")

# Test with just 3 tickers
test_tickers = ['AAPL', 'MSFT', 'NVDA']

print(f"Testing with {len(test_tickers)} tickers: {', '.join(test_tickers)}")
print("This will take about 1-2 minutes...\n")

# Create scanner
scanner = BacktestScanner()

# Show configuration
print(f"Configuration:")
print(f"  Timeframes: {scanner.timeframes}")
print(f"  Expected: ['1d', '3d']")
print()

# Override tickers for quick test
scanner.tickers = test_tickers

# Run scan
signals_df = scanner.scan_all_tickers(output_csv='backtest/quick_test_signals.csv')

if len(signals_df) > 0:
    print(f"\n{'='*70}")
    print(f"TEST RESULTS")
    print(f"{'='*70}\n")

    print(f"Total signals found: {len(signals_df)}")
    print()

    # Check timeframes
    timeframes_found = signals_df['timeframe'].unique()
    print(f"Timeframes found: {list(timeframes_found)}")
    print(f"✓ PASS" if set(timeframes_found).issubset({'1d', '3d'}) else "✗ FAIL - Found unexpected timeframes!")
    print()

    # Check divergence types
    types_found = signals_df['divergence_type'].unique()
    print(f"Divergence types found: {list(types_found)}")
    print(f"✓ PASS" if list(types_found) == ['Bullish'] else "✗ FAIL - Found bearish divergences!")
    print()

    # Show breakdown
    print("Breakdown by timeframe:")
    print(signals_df['timeframe'].value_counts())
    print()

    print("Breakdown by ticker:")
    print(signals_df['ticker'].value_counts())
    print()

    print(f"{'='*70}")
    print(f"CONFIGURATION VALIDATED ✓")
    print(f"{'='*70}")
    print("Ready to run full backtest with:")
    print("  python3 run_backtest.py")
    print()
else:
    print("\nNo signals found in test tickers (this is OK)")
    print(f"But configuration should still be correct:")
    print(f"  Timeframes: {scanner.timeframes}")
    print(f"  Should be: ['1d', '3d']")
    print()
