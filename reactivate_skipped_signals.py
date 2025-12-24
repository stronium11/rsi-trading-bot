#!/usr/bin/env python3
"""
Reactivate signals that were skipped due to risk limits
Changes their status from 'skipped' back to 'pending' so they execute today
"""

import sys
from pathlib import Path
from datetime import datetime

# Add rsi_trading_bot to path
sys.path.insert(0, str(Path.cwd() / 'rsi_trading_bot'))

from database import get_database


def main():
    """Reactivate skipped signals blocked by risk limits"""

    print("="*70)
    print("REACTIVATING SKIPPED SIGNALS")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")

    db = get_database()

    # Step 1: Find all signals skipped due to risk limits
    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Find skipped signals with risk limit errors in notes
        cursor.execute("""
            SELECT
                id,
                ticker,
                divergence_type,
                timeframe,
                entry_price,
                detected_at,
                notes
            FROM signals
            WHERE status = 'skipped'
            AND (
                notes LIKE '%risk limit%'
                OR notes LIKE '%Max position%'
                OR notes LIKE '%daily trade%'
                OR notes LIKE '%daily loss%'
            )
            ORDER BY detected_at DESC
        """)

        skipped_signals = cursor.fetchall()

    if not skipped_signals:
        print("✅ No skipped signals found due to risk limits")
        print("\nChecking for any pending signals...")

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM signals WHERE status = 'pending'")
            pending_count = cursor.fetchone()[0]

        print(f"   {pending_count} signals already pending execution")
        return

    print(f"Found {len(skipped_signals)} signals that were skipped due to risk limits:\n")

    # Display each skipped signal
    for signal in skipped_signals:
        signal_id, ticker, div_type, timeframe, entry_price, detected_at, notes = signal

        print(f"Signal #{signal_id}:")
        print(f"  Ticker: {ticker}")
        print(f"  Type: {div_type} {timeframe}")
        print(f"  Entry: ${entry_price:.2f}")
        print(f"  Detected: {detected_at}")
        print(f"  Reason skipped: {notes}")
        print()

    # Ask for confirmation
    print("="*70)
    response = input(f"\nReactivate all {len(skipped_signals)} signals for execution today? (yes/no): ").strip().lower()

    if response != 'yes':
        print("\n❌ Cancelled - no signals reactivated")
        return

    # Step 2: Reactivate signals by changing status to 'pending'
    print(f"\nReactivating signals...")

    with db.get_connection() as conn:
        cursor = conn.cursor()

        for signal in skipped_signals:
            signal_id = signal[0]
            ticker = signal[1]

            cursor.execute("""
                UPDATE signals
                SET status = 'pending',
                    notes = 'Reactivated - risk limits removed'
                WHERE id = ?
            """, (signal_id,))

            print(f"  ✅ Signal #{signal_id} ({ticker}) reactivated")

        conn.commit()

    # Step 3: Show summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"✅ Reactivated {len(skipped_signals)} signals")
    print(f"\nThese signals will execute at the next market open (9:30 AM ET)")
    print(f"\nNote: Risk limits have been removed, so all signals will execute")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
