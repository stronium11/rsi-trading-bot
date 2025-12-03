#!/usr/bin/env python3
"""
Complete Backtest System Runner
Runs the entire backtesting pipeline from data collection to reporting
"""

import argparse
import sys
from datetime import datetime
from backtest_scanner import BacktestScanner
from backtest_engine import BacktestEngine
from backtest_reporter import BacktestReporter


def run_complete_backtest(skip_scan=False, skip_sim=False):
    """
    Run the complete backtest pipeline

    Parameters:
    - skip_scan: Skip the data scanning phase (use existing signals)
    - skip_sim: Skip the simulation phase (use existing results)
    """
    print(f"\n{'#'*70}")
    print(f"# RSI DIVERGENCE BACKTEST SYSTEM")
    print(f"# 5-Year Historical Analysis")
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*70}\n")

    # Phase 1: Scan Historical Data
    if not skip_scan:
        print(f"\n{'='*70}")
        print(f"PHASE 1: SCANNING HISTORICAL DATA (5 YEARS)")
        print(f"{'='*70}\n")

        scanner = BacktestScanner()
        signals_df = scanner.scan_all_tickers()

        if signals_df.empty:
            print("No signals found in historical data. Exiting.")
            return

        print(f"\nPhase 1 Complete: {len(signals_df)} signals detected\n")
    else:
        print("\nSkipping Phase 1 (using existing signals)...\n")

    # Phase 2: Simulate Trades
    if not skip_sim:
        print(f"\n{'='*70}")
        print(f"PHASE 2: SIMULATING TRADES")
        print(f"{'='*70}\n")

        engine = BacktestEngine()
        trades = engine.run_backtest()
        results_df = engine.save_results()

        print(f"\nPhase 2 Complete: {len(trades)} trades simulated\n")
    else:
        print("\nSkipping Phase 2 (using existing results)...\n")

    # Phase 3 & 4: Analyze and Report
    print(f"\n{'='*70}")
    print(f"PHASE 3 & 4: ANALYZING PERFORMANCE & GENERATING REPORTS")
    print(f"{'='*70}\n")

    reporter = BacktestReporter()
    reporter.print_full_report()

    print(f"\n{'#'*70}")
    print(f"# BACKTEST SYSTEM COMPLETE")
    print(f"# Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*70}\n")

    print("Output Files:")
    print("  - backtest/backtest_signals.csv       (Historical signals)")
    print("  - backtest/backtest_results.csv       (Trade simulation results)")
    print("  - backtest/reports/summary_report.csv (Overall summary)")
    print("  - backtest/reports/timeframe_report.csv (By timeframe)")
    print("  - backtest/reports/type_report.csv    (By divergence type)")
    print("  - backtest/reports/quarterly_report.csv (Quarterly performance)")
    print("  - backtest/reports/trade_details_report.csv (All trades)")
    print("  - backtest/reports/equity_curve.csv   (Cumulative P&L)\n")


def main():
    """Main entry point with CLI arguments"""
    parser = argparse.ArgumentParser(
        description='RSI Divergence Backtest System - 5 Year Historical Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run complete backtest (scan + simulate + analyze)
  python run_backtest.py

  # Skip scanning phase (use existing signals)
  python run_backtest.py --skip-scan

  # Skip both scan and simulation (only analyze existing results)
  python run_backtest.py --skip-scan --skip-sim

  # Run only specific phases:
  python run_backtest.py --scan-only     # Only scan for signals
  python run_backtest.py --sim-only      # Only simulate trades
  python run_backtest.py --report-only   # Only generate reports
        """
    )

    parser.add_argument(
        '--skip-scan',
        action='store_true',
        help='Skip historical data scanning (use existing signals)'
    )

    parser.add_argument(
        '--skip-sim',
        action='store_true',
        help='Skip trade simulation (use existing results)'
    )

    parser.add_argument(
        '--scan-only',
        action='store_true',
        help='Only run Phase 1: Historical data scanning'
    )

    parser.add_argument(
        '--sim-only',
        action='store_true',
        help='Only run Phase 2: Trade simulation'
    )

    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Only run Phase 3 & 4: Analysis and reporting'
    )

    args = parser.parse_args()

    try:
        # Handle phase-specific execution
        if args.scan_only:
            print(f"\n{'='*70}")
            print(f"RUNNING PHASE 1 ONLY: HISTORICAL DATA SCANNING")
            print(f"{'='*70}\n")
            scanner = BacktestScanner()
            signals_df = scanner.scan_all_tickers()
            print(f"\nPhase 1 Complete: {len(signals_df)} signals detected\n")

        elif args.sim_only:
            print(f"\n{'='*70}")
            print(f"RUNNING PHASE 2 ONLY: TRADE SIMULATION")
            print(f"{'='*70}\n")
            engine = BacktestEngine()
            trades = engine.run_backtest()
            results_df = engine.save_results()
            print(f"\nPhase 2 Complete: {len(trades)} trades simulated\n")

        elif args.report_only:
            print(f"\n{'='*70}")
            print(f"RUNNING PHASE 3 & 4 ONLY: ANALYSIS & REPORTING")
            print(f"{'='*70}\n")
            reporter = BacktestReporter()
            reporter.print_full_report()

        else:
            # Run complete backtest
            run_complete_backtest(
                skip_scan=args.skip_scan,
                skip_sim=args.skip_sim
            )

    except KeyboardInterrupt:
        print("\n\nBacktest interrupted by user. Exiting gracefully...\n")
        sys.exit(0)
    except FileNotFoundError as e:
        print(f"\n\nError: Required file not found - {str(e)}")
        print("Make sure you have run the previous phases before skipping them.\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
