#!/usr/bin/env python3
"""
Clean Up Duplicate Signals
Removes duplicate signals from database, keeping only the oldest occurrence
"""

import sys
import os
from pathlib import Path

# Add rsi_trading_bot to path
bot_dir = Path(__file__).parent / 'rsi_trading_bot'
sys.path.insert(0, str(bot_dir))

from database import get_database

def cleanup_duplicates():
    """Remove duplicate signals, keeping the oldest one"""

    db = get_database()

    print("="*70)
    print("CLEANING UP DUPLICATE SIGNALS")
    print("="*70)
    print()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Find all signals
        cursor.execute("""
            SELECT id, ticker, divergence_type, timeframe, entry_price, detected_at, status
            FROM signals
            ORDER BY detected_at ASC
        """)
        all_signals = [dict(row) for row in cursor.fetchall()]

    print(f"Total signals in database: {len(all_signals)}")
    print()

    # Track which signals to keep (oldest of each unique combination)
    seen = {}
    to_delete = []

    for signal in all_signals:
        ticker = signal['ticker']
        div_type = signal['divergence_type']
        timeframe = signal['timeframe']
        price = signal['entry_price']
        signal_id = signal['id']
        detected_at = signal['detected_at']
        status = signal['status']

        # Create a key for this signal (ticker + type + timeframe + price rounded to nearest dollar)
        # This groups signals that are essentially the same
        key = (ticker, div_type, timeframe, round(price))

        if key not in seen:
            # First occurrence - keep it
            seen[key] = {
                'id': signal_id,
                'detected_at': detected_at,
                'price': price,
                'status': status
            }
        else:
            # Duplicate found - mark for deletion
            original = seen[key]
            to_delete.append({
                'id': signal_id,
                'ticker': ticker,
                'div_type': div_type,
                'timeframe': timeframe,
                'price': price,
                'detected_at': detected_at,
                'status': status,
                'original_id': original['id'],
                'original_date': original['detected_at']
            })

    if not to_delete:
        print("✅ No duplicates found! Database is clean.")
        return

    print(f"Found {len(to_delete)} duplicate signals to remove:")
    print()

    # Group by ticker for display
    by_ticker = {}
    for dup in to_delete:
        ticker = dup['ticker']
        if ticker not in by_ticker:
            by_ticker[ticker] = []
        by_ticker[ticker].append(dup)

    for ticker, dups in sorted(by_ticker.items()):
        print(f"{ticker}:")
        for dup in dups:
            print(f"  ID {dup['id']}: {dup['div_type']} {dup['timeframe']} @ ${dup['price']:.2f}")
            print(f"    Detected: {dup['detected_at']} ({dup['status']})")
            print(f"    Duplicate of ID {dup['original_id']} from {dup['original_date']}")
        print()

    # Ask for confirmation
    response = input("Delete these duplicate signals? (yes/no): ").strip().lower()

    if response != 'yes':
        print("❌ Cleanup cancelled")
        return

    # Delete duplicates
    print()
    print("Deleting duplicates...")

    with db.get_connection() as conn:
        cursor = conn.cursor()
        for dup in to_delete:
            cursor.execute("DELETE FROM signals WHERE id = ?", (dup['id'],))
        conn.commit()

    print(f"✅ Deleted {len(to_delete)} duplicate signals")
    print(f"✅ Kept {len(seen)} unique signals")
    print()
    print("="*70)
    print("CLEANUP COMPLETE")
    print("="*70)


if __name__ == "__main__":
    cleanup_duplicates()
