"""
Fresh Backtest Runner

Clears all cached data and runs complete backtest pipeline from scratch:
1. Clear cache and old results
2. Scan for divergence signals (5 years back from today)
3. Run optimized backtest with enhanced quarterly reporting

Enhanced Quarterly Reporting:
- Capital Deployed: Total position value in quarter
- Quarter Return %: (Quarter P&L / Capital Deployed) * 100
"""

import os
import shutil
from datetime import datetime, timedelta
import subprocess


def clear_cached_data():
    """Clear all cached data and old results"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backtest_dir = os.path.join(script_dir, 'backtest')

    items_to_clear = [
        'price_cache',
        'backtest_results.csv',
        'backtest_signals.csv',
        'optimized_results',
        'filter_tests',
        'reports'
    ]

    print("="*70)
    print("CLEARING CACHED DATA")
    print("="*70)
    print()

    for item in items_to_clear:
        item_path = os.path.join(backtest_dir, item)

        if os.path.isdir(item_path):
            # Remove directory and recreate empty
            try:
                shutil.rmtree(item_path)
                os.makedirs(item_path, exist_ok=True)
                print(f"✓ Cleared directory: {item}")
            except Exception as e:
                print(f"✗ Error clearing {item}: {e}")
        elif os.path.isfile(item_path):
            # Remove file
            try:
                os.remove(item_path)
                print(f"✓ Removed file: {item}")
            except Exception as e:
                print(f"✗ Error removing {item}: {e}")

    print()
    print("Cache cleared successfully!")
    print()


def run_signal_scanner():
    """Run divergence signal scanner for 5 years"""
    print("="*70)
    print("SCANNING FOR DIVERGENCE SIGNALS")
    print("="*70)
    print()

    # Calculate date range: 5 years back from today
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365)

    print(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Lookback: 5 years")
    print()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    scanner_script = os.path.join(script_dir, 'backtest_scanner.py')

    # Run scanner using backtest_scanner.py
    try:
        result = subprocess.run(
            ['python3', scanner_script],
            cwd=script_dir,
            capture_output=True,
            text=True,
            timeout=7200  # 2 hour timeout (scanning takes time)
        )

        print(result.stdout)

        if result.returncode != 0:
            print("Error running signal scanner:")
            print(result.stderr)
            return False

        return True
    except subprocess.TimeoutExpired:
        print("Signal scanner timed out after 2 hours")
        return False
    except Exception as e:
        print(f"Error running signal scanner: {e}")
        return False


def run_optimized_backtest():
    """Run optimized backtest with enhanced reporting"""
    print("="*70)
    print("RUNNING OPTIMIZED BACKTEST")
    print("="*70)
    print()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    backtest_script = os.path.join(script_dir, 'optimized_backtester_enhanced.py')

    # Run backtest
    try:
        result = subprocess.run(
            ['python3', backtest_script],
            cwd=script_dir,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )

        print(result.stdout)

        if result.returncode != 0:
            print("Error running backtest:")
            print(result.stderr)
            return False

        return True
    except subprocess.TimeoutExpired:
        print("Backtest timed out after 1 hour")
        return False
    except Exception as e:
        print(f"Error running backtest: {e}")
        return False


def main():
    """Run complete fresh backtest pipeline"""
    print()
    print("="*70)
    print("FRESH BACKTEST PIPELINE")
    print("="*70)
    print()
    print("This will:")
    print("  1. Clear all cached data and old results")
    print("  2. Scan for divergence signals (5 years back)")
    print("  3. Run optimized backtest with enhanced quarterly reporting")
    print()
    print("="*70)
    print()

    # Step 1: Clear cached data
    clear_cached_data()

    # Step 2: Scan for signals
    print("\nStep 2/3: Scanning for divergence signals...")
    print("-"*70)
    if not run_signal_scanner():
        print("Failed to scan signals. Aborting.")
        return

    # Step 3: Run backtest
    print("\nStep 3/3: Running optimized backtest...")
    print("-"*70)
    if not run_optimized_backtest():
        print("Failed to run backtest. Aborting.")
        return

    print()
    print("="*70)
    print("FRESH BACKTEST COMPLETE")
    print("="*70)
    print()


if __name__ == "__main__":
    main()
