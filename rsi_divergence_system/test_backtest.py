#!/usr/bin/env python3
"""
Backtest System Test Script
Tests the backtest system with a small subset of data
"""

import os
import pandas as pd
from backtest_scanner import BacktestScanner
from backtest_engine import BacktestEngine
from backtest_reporter import BacktestReporter


def test_backtest_system():
    """
    Test the backtest system with limited data
    """
    print(f"\n{'='*70}")
    print(f"TESTING BACKTEST SYSTEM")
    print(f"{'='*70}\n")

    # Create backtest directories
    os.makedirs('backtest', exist_ok=True)
    os.makedirs('backtest/test_reports', exist_ok=True)

    # Test with just 2 tickers to verify everything works
    test_tickers = ['AAPL', 'MSFT']

    print("Phase 1: Testing historical scanner...")
    print(f"Scanning {len(test_tickers)} test tickers: {', '.join(test_tickers)}\n")

    # Create a test scanner with limited tickers
    scanner = BacktestScanner()
    scanner.tickers = test_tickers  # Override with test tickers

    try:
        signals_df = scanner.scan_all_tickers(output_csv='backtest/test_signals.csv')

        if signals_df.empty or len(signals_df) == 0:
            print("WARNING: No signals found in test data. This is OK for testing.")
            print("Creating dummy signals for testing purposes...\n")

            # Create multiple dummy signal data for realistic testing
            dummy_signals = [
                {
                    'ticker': 'AAPL',
                    'timeframe': '1d',
                    'signal_date': '2024-01-15',
                    'divergence_type': 'Bullish',
                    'signal_close': 185.50,
                    'entry_date': '2024-01-16',
                    'entry_price': 186.00,
                    'first_peak_price': 180.00,
                    'second_peak_price': 175.00,
                    'first_peak_rsi': 28.5,
                    'second_peak_rsi': 32.0
                },
                {
                    'ticker': 'MSFT',
                    'timeframe': '1w',
                    'signal_date': '2024-02-05',
                    'divergence_type': 'Bearish',
                    'signal_close': 405.50,
                    'entry_date': '2024-02-12',
                    'entry_price': 404.00,
                    'first_peak_price': 400.00,
                    'second_peak_price': 408.00,
                    'first_peak_rsi': 82.5,
                    'second_peak_rsi': 78.0
                },
                {
                    'ticker': 'AAPL',
                    'timeframe': '3d',
                    'signal_date': '2024-03-10',
                    'divergence_type': 'Bullish',
                    'signal_close': 170.50,
                    'entry_date': '2024-03-13',
                    'entry_price': 172.00,
                    'first_peak_price': 168.00,
                    'second_peak_price': 165.00,
                    'first_peak_rsi': 24.5,
                    'second_peak_rsi': 26.0
                }
            ]

            signals_df = pd.DataFrame(dummy_signals)
            signals_df.to_csv('backtest/test_signals.csv', index=False)
            print(f"Created {len(dummy_signals)} dummy signals for testing.\n")
        else:
            print(f"✓ Scanner test passed: {len(signals_df)} signals found\n")

    except Exception as e:
        print(f"✗ Scanner test failed: {str(e)}\n")
        return False

    print("Phase 2: Testing trade simulator...")

    try:
        engine = BacktestEngine(signals_csv='backtest/test_signals.csv')
        trades = engine.run_backtest()
        results_df = engine.save_results(output_csv='backtest/test_results.csv')

        print(f"✓ Simulator test passed: {len(trades)} trades simulated\n")

    except Exception as e:
        print(f"✗ Simulator test failed: {str(e)}\n")
        return False

    print("Phase 3: Testing analyzer and reporter...")

    try:
        reporter = BacktestReporter(
            results_csv='backtest/test_results.csv',
            output_dir='backtest/test_reports'
        )
        reports = reporter.generate_all_reports()

        print(f"✓ Reporter test passed: {len(reports)} reports generated\n")

        # Print summary
        print("=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(reports['summary'].to_string(index=False))
        print()

    except Exception as e:
        print(f"✗ Reporter test failed: {str(e)}\n")
        return False

    print(f"\n{'='*70}")
    print(f"ALL TESTS PASSED ✓")
    print(f"{'='*70}\n")

    print("Test output files created:")
    print("  - backtest/test_signals.csv")
    print("  - backtest/test_results.csv")
    print("  - backtest/test_reports/")
    print("\nYou can now run the full backtest with:")
    print("  python run_backtest.py\n")

    return True


if __name__ == "__main__":
    try:
        success = test_backtest_system()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.\n")
        exit(1)
    except Exception as e:
        print(f"\n\nTest failed with error: {str(e)}\n")
        exit(1)
