#!/usr/bin/env python3
"""
Check signal status and optionally reset failed signals to pending
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent / 'rsi_trading_bot'))

from database import get_database

def check_signals():
    """Check all signals and their status"""

    db = get_database()

    print("="*70)
    print("SIGNAL STATUS CHECK")
    print("="*70)
    print()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Get all signals
        cursor.execute("""
            SELECT id, ticker, divergence_type, entry_price, status, detected_at
            FROM signals
            ORDER BY detected_at DESC
            LIMIT 20
        """)

        signals = cursor.fetchall()

        if not signals:
            print("No signals found in database")
            return

        # Group by status
        by_status = {}
        for signal in signals:
            status = signal[4]
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(signal)

        # Show summary
        print("Signal Summary:")
        for status, sigs in by_status.items():
            print(f"  {status.upper()}: {len(sigs)} signals")

        print()
        print("="*70)
        print("DETAILED SIGNAL LIST")
        print("="*70)
        print()

        for signal in signals:
            sig_id, ticker, div_type, price, status, detected = signal
            print(f"ID {sig_id}: {ticker} - {div_type} @ ${price:.2f} - Status: {status.upper()}")
            print(f"        Detected: {detected}")
            print()

        # Ask if user wants to reset failed signals
        print("="*70)
        print()

        failed_signals = [s for s in signals if s[4] in ('failed', 'skipped')]

        if not failed_signals:
            print("No failed or skipped signals to reset")
            return

        print(f"Found {len(failed_signals)} failed/skipped signals:")
        for signal in failed_signals:
            print(f"  - {signal[1]} ({signal[2]})")

        print()
        response = input("Reset these signals to PENDING status? (yes/no): ").strip().lower()

        if response == 'yes':
            # Reset to pending
            for signal in failed_signals:
                sig_id = signal[0]
                cursor.execute("""
                    UPDATE signals
                    SET status = 'pending'
                    WHERE id = ?
                """, (sig_id,))

            conn.commit()
            print(f"\n✅ Reset {len(failed_signals)} signals to PENDING status")
            print("\nYou can now run: python3 execute_signals_now.py")
        else:
            print("\n❌ No signals reset")


if __name__ == "__main__":
    check_signals()
