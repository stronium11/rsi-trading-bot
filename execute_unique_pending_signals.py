#!/usr/bin/env python3
"""
Execute unique pending signals and clean up duplicates

This script:
1. Identifies duplicate pending signals
2. Keeps the oldest signal of each duplicate set
3. Marks newer duplicates as skipped
4. Executes the unique pending signals
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add rsi_trading_bot to path
sys.path.insert(0, str(Path.cwd() / 'rsi_trading_bot'))

from database import get_database
from order_executor import get_order_executor


async def main():
    """Clean up duplicates and execute unique pending signals"""

    print("="*70)
    print("CLEAN UP DUPLICATES AND EXECUTE UNIQUE SIGNALS")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}")
    print("="*70 + "\n")

    db = get_database()

    # Get all pending signals
    pending_signals = db.get_pending_signals()

    if not pending_signals:
        print("✅ No pending signals found")
        return

    print(f"Found {len(pending_signals)} pending signals\n")

    # Group signals by (ticker, divergence_type, timeframe, entry_price)
    signal_groups = defaultdict(list)

    for signal in pending_signals:
        key = (
            signal['ticker'],
            signal['divergence_type'],
            signal['timeframe'],
            round(signal.get('entry_price', 0), 2)
        )
        signal_groups[key].append(signal)

    # Identify duplicates and signals to keep
    signals_to_keep = []
    signals_to_skip = []

    for key, signals in signal_groups.items():
        ticker, div_type, timeframe, entry_price = key

        if len(signals) > 1:
            # Sort by detected_at to find oldest
            signals_sorted = sorted(signals, key=lambda s: s.get('detected_at', ''))
            oldest = signals_sorted[0]
            duplicates = signals_sorted[1:]

            print(f"Duplicate group: {ticker} {div_type} {timeframe} @ ${entry_price:.2f}")
            print(f"  Keeping: ID {oldest['id']} (detected {oldest.get('detected_at', 'N/A')})")
            print(f"  Skipping {len(duplicates)} duplicate(s):")
            for dup in duplicates:
                print(f"    ID {dup['id']} (detected {dup.get('detected_at', 'N/A')})")
            print()

            signals_to_keep.append(oldest)
            signals_to_skip.extend(duplicates)
        else:
            # No duplicates, keep the signal
            signals_to_keep.append(signals[0])

    # Mark duplicates as skipped in database
    print(f"{'='*70}")
    print(f"Marking {len(signals_to_skip)} duplicate signals as skipped...")
    print(f"{'='*70}\n")

    with db.get_connection() as conn:
        cursor = conn.cursor()
        for signal in signals_to_skip:
            cursor.execute("""
                UPDATE signals
                SET status = 'skipped',
                    notes = 'Duplicate signal - keeping oldest version'
                WHERE id = ?
            """, (signal['id'],))
        conn.commit()

    print(f"✅ Marked {len(signals_to_skip)} duplicates as skipped")
    print(f"\n{'='*70}")
    print(f"Executing {len(signals_to_keep)} unique signals...")
    print(f"{'='*70}\n")

    # Display signals to execute
    for signal in signals_to_keep:
        print(f"• {signal['ticker']} - {signal['divergence_type']} {signal['timeframe']}")
        print(f"  ID: {signal['id']}")
        print(f"  Entry: ${signal.get('entry_price', 0):.2f}")
        print(f"  Detected: {signal.get('detected_at', 'N/A')}")
        print()

    # Execute unique signals
    executor = get_order_executor()

    executed = 0
    failed = 0

    for signal in signals_to_keep:
        ticker = signal['ticker']
        print(f"\n{'='*70}")
        print(f"Executing: {ticker} - {signal['divergence_type']} {signal['timeframe']}")
        print(f"{'='*70}")

        success = await executor.execute_signal(signal)

        if success:
            executed += 1
        else:
            failed += 1

    # Summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"Total pending signals found: {len(pending_signals)}")
    print(f"Duplicate signals skipped: {len(signals_to_skip)}")
    print(f"Unique signals to execute: {len(signals_to_keep)}")
    print(f"✅ Successfully executed: {executed}")
    print(f"❌ Failed: {failed}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
