#!/usr/bin/env python3
"""
Quick test: Run backtest for just one ticker
"""

from backtest_scanner import BacktestScanner
from backtest_engine import BacktestEngine

# Test with just AAPL
test_ticker = 'AAPL'

print(f"Testing backtest with {test_ticker} only...\n")

# Scan for signals
scanner = BacktestScanner()
scanner.tickers = [test_ticker]
signals = scanner.scan_all_tickers(output_csv='backtest/single_ticker_signals.csv')

if len(signals) == 0:
    print(f"No signals found for {test_ticker}")
else:
    print(f"\nFound {len(signals)} signals for {test_ticker}")
    print("\nRunning simulation...")

    # Simulate trades
    engine = BacktestEngine('backtest/single_ticker_signals.csv')
    trades = engine.run_backtest()
    results = engine.save_results('backtest/single_ticker_results.csv')

    print(f"\n✅ SUCCESS! Results saved to backtest/single_ticker_results.csv")
    print(f"\nQuick stats:")
    print(f"  Total P&L: ${results['total_pnl'].sum():.2f}")
    print(f"  Winning trades: {len(results[results['total_pnl'] > 0])}")
    print(f"  Losing trades: {len(results[results['total_pnl'] <= 0])}")
