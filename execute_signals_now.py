#!/usr/bin/env python3
"""
Manual Order Execution - Execute pending signals on demand
This allows testing order execution without waiting for 9:30 AM
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent / 'rsi_trading_bot'))

from database import get_database
from order_executor import get_order_executor
from telegram_bot import get_bot

async def execute_now():
    """Execute pending signals immediately"""

    db = get_database()
    executor = get_order_executor()
    telegram = get_bot()

    print("="*70)
    print("MANUAL ORDER EXECUTION")
    print("="*70)
    print()

    # Get pending signals
    pending = db.get_pending_signals()

    if not pending:
        print("❌ No pending signals to execute")
        return

    print(f"Found {len(pending)} pending signals:")
    print()

    for i, signal in enumerate(pending, 1):
        print(f"{i}. {signal['ticker']} - {signal['divergence_type']} @ ${signal['entry_price']:.2f}")

    print()
    print("="*70)
    print()

    # Ask which signals to execute
    response = input("Execute ALL signals? (yes/no) or enter signal numbers (e.g., 1,3,5): ").strip().lower()

    if response == 'yes':
        signals_to_execute = pending
    elif response == 'no':
        print("❌ Execution cancelled")
        return
    else:
        # Parse signal numbers
        try:
            indices = [int(x.strip()) - 1 for x in response.split(',')]
            signals_to_execute = [pending[i] for i in indices if 0 <= i < len(pending)]

            if not signals_to_execute:
                print("❌ Invalid signal numbers")
                return

        except ValueError:
            print("❌ Invalid input")
            return

    print()
    print(f"Executing {len(signals_to_execute)} signals...")
    print()

    # Execute each signal
    success_count = 0
    fail_count = 0

    for signal in signals_to_execute:
        ticker = signal['ticker']
        print(f"\n{'='*70}")
        print(f"Executing {ticker}...")
        print(f"{'='*70}\n")

        try:
            result = await executor.execute_signal(signal)

            if result:
                success_count += 1
                print(f"✅ {ticker} executed successfully")
            else:
                fail_count += 1
                print(f"❌ {ticker} execution failed")

        except Exception as e:
            fail_count += 1
            print(f"❌ {ticker} execution error: {str(e)}")

    print()
    print("="*70)
    print("EXECUTION SUMMARY")
    print("="*70)
    print(f"Total: {len(signals_to_execute)}")
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print("="*70)


if __name__ == "__main__":
    print("\n⚠️  WARNING: This will place REAL orders in your Alpaca account!")
    print("Make sure the market is open and you understand what will happen.\n")

    response = input("Do you want to continue? (yes/no): ").strip().lower()

    if response == 'yes':
        asyncio.run(execute_now())
    else:
        print("\n❌ Operation cancelled by user")
