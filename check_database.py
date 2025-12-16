#!/usr/bin/env python3
"""
Check database location and contents
"""
import sqlite3
import sys
from pathlib import Path

def check_database():
    """Check database file and contents"""

    print("="*70)
    print("DATABASE DIAGNOSTIC")
    print("="*70)
    print()

    # Database is in the rsi_trading_bot directory
    db_path = Path(__file__).parent / 'rsi_trading_bot' / 'trading_bot.db'
    print(f"Database path: {db_path}")
    print()

    # Check if file exists
    if Path(db_path).exists():
        size = Path(db_path).stat().st_size
        print(f"✅ Database file exists")
        print(f"   Size: {size:,} bytes")
    else:
        print(f"❌ Database file does not exist!")
        return

    print()

    # Connect and check tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check signals table
    print("="*70)
    print("SIGNALS TABLE")
    print("="*70)

    cursor.execute("SELECT COUNT(*) FROM signals")
    count = cursor.fetchone()[0]
    print(f"Total signals: {count}")

    if count > 0:
        cursor.execute("""
            SELECT status, COUNT(*)
            FROM signals
            GROUP BY status
        """)
        for status, cnt in cursor.fetchall():
            print(f"  {status}: {cnt}")

        print()
        print("Last 10 signals:")
        cursor.execute("""
            SELECT id, ticker, divergence_type, entry_price, status, detected_at
            FROM signals
            ORDER BY detected_at DESC
            LIMIT 10
        """)
        for row in cursor.fetchall():
            print(f"  ID {row[0]}: {row[1]} - {row[2]} @ ${row[3]:.2f} - {row[4]} - {row[5]}")

    print()
    print("="*70)
    print("POSITIONS TABLE")
    print("="*70)

    cursor.execute("SELECT COUNT(*) FROM positions")
    count = cursor.fetchone()[0]
    print(f"Total positions: {count}")

    if count > 0:
        cursor.execute("""
            SELECT status, COUNT(*)
            FROM positions
            GROUP BY status
        """)
        for status, cnt in cursor.fetchall():
            print(f"  {status}: {cnt}")

        print()
        print("All positions:")
        cursor.execute("""
            SELECT id, ticker, direction, entry_price, quantity, status, opened_at
            FROM positions
            ORDER BY opened_at DESC
        """)
        for row in cursor.fetchall():
            print(f"  ID {row[0]}: {row[1]} - {row[2]} - {row[4]:.4f} shares @ ${row[3]:.2f} - {row[5]} - {row[6]}")

    print()
    print("="*70)
    print("ORDERS TABLE")
    print("="*70)

    cursor.execute("SELECT COUNT(*) FROM orders")
    count = cursor.fetchone()[0]
    print(f"Total orders: {count}")

    if count > 0:
        cursor.execute("""
            SELECT status, COUNT(*)
            FROM orders
            GROUP BY status
        """)
        for status, cnt in cursor.fetchall():
            print(f"  {status}: {cnt}")

    # Ask if user wants to reset failed signals
    print()
    print("="*70)
    print("RESET FAILED SIGNALS")
    print("="*70)

    cursor.execute("""
        SELECT id, ticker, divergence_type, entry_price
        FROM signals
        WHERE status = 'failed'
        ORDER BY detected_at DESC
    """)

    failed = cursor.fetchall()

    if failed:
        print(f"\nFound {len(failed)} failed signals:")
        for sig in failed:
            print(f"  ID {sig[0]}: {sig[1]} - {sig[2]} @ ${sig[3]:.2f}")

        print()
        response = input("Reset these signals to PENDING for testing? (yes/no): ").strip().lower()

        if response == 'yes':
            cursor.execute("""
                UPDATE signals
                SET status = 'pending'
                WHERE status = 'failed'
            """)
            conn.commit()
            print(f"\n✅ Reset {len(failed)} signals to PENDING")
            print("\nYou can now run: python3 execute_signals_now.py")
        else:
            print("\n❌ No signals reset")
    else:
        print("\nNo failed signals to reset")

    conn.close()

    print()
    print("="*70)


if __name__ == "__main__":
    check_database()
