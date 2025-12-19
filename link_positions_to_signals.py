#!/usr/bin/env python3
"""
Link Orphaned Positions to Signals
Matches positions with signal_id=NULL to their original signals
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add rsi_trading_bot to path
bot_dir = Path(__file__).parent / 'rsi_trading_bot'
sys.path.insert(0, str(bot_dir))

from database import get_database

def link_positions_to_signals():
    """Link orphaned positions to their matching signals"""

    db = get_database()

    print("="*70)
    print("LINKING ORPHANED POSITIONS TO SIGNALS")
    print("="*70)
    print()

    # Get positions with no signal_id
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, ticker, direction, entry_price, opened_at
            FROM positions
            WHERE signal_id IS NULL
        """)
        orphaned_positions = [dict(row) for row in cursor.fetchall()]

    if not orphaned_positions:
        print("✅ No orphaned positions found - all positions are linked to signals")
        return

    print(f"Found {len(orphaned_positions)} orphaned positions:")
    print()

    matches = []

    for pos in orphaned_positions:
        ticker = pos['ticker']
        direction = pos['direction']
        entry_price = pos['entry_price']
        opened_at = pos['opened_at']

        # Infer divergence type from direction
        divergence_type = 'Bullish' if direction == 'LONG' else 'Bearish'

        print(f"Searching for: {ticker} {divergence_type} @ ${entry_price:.2f} (opened {opened_at})")

        # Parse opened_at to datetime
        opened_date = datetime.strptime(opened_at, '%Y-%m-%d %H:%M:%S')

        # Search for matching signals within +/- 7 days and +/- $50 price
        # Wide tolerance because signal detection price != actual fill price
        search_start = (opened_date - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        search_end = (opened_date + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, ticker, divergence_type, timeframe, entry_price, detected_at, status
                FROM signals
                WHERE ticker = ?
                AND divergence_type = ?
                AND ABS(entry_price - ?) <= 50.0
                AND detected_at >= ?
                AND detected_at <= ?
                ORDER BY ABS(entry_price - ?) ASC, ABS(julianday(detected_at) - julianday(?)) ASC
                LIMIT 5
            """, (ticker, divergence_type, entry_price, search_start, search_end, entry_price, opened_at))

            candidates = [dict(row) for row in cursor.fetchall()]

        if not candidates:
            print(f"  ❌ No matching signals found")
            print()
            continue

        # Show candidates
        print(f"  Found {len(candidates)} potential matches:")
        for i, sig in enumerate(candidates, 1):
            price_diff = abs(sig['entry_price'] - entry_price)
            date_diff = abs((datetime.strptime(sig['detected_at'], '%Y-%m-%d %H:%M:%S') - opened_date).days)
            print(f"    {i}. Signal #{sig['id']}: {sig['divergence_type']} {sig['timeframe']} @ ${sig['entry_price']:.2f}")
            print(f"       Detected: {sig['detected_at']} ({sig['status']})")
            print(f"       Price diff: ${price_diff:.2f}, Date diff: {date_diff} days")

        # Use best match (first one, sorted by price similarity then date)
        best_match = candidates[0]

        matches.append({
            'position_id': pos['id'],
            'ticker': ticker,
            'signal_id': best_match['id'],
            'signal_timeframe': best_match['timeframe'],
            'signal_date': best_match['detected_at']
        })

        print(f"  ✅ Best match: Signal #{best_match['id']} ({best_match['timeframe']})")
        print()

    if not matches:
        print("❌ No matches found for any positions")
        return

    # Show summary and ask for confirmation
    print("="*70)
    print(f"SUMMARY: Found {len(matches)} matches")
    print("="*70)
    print()

    for match in matches:
        print(f"{match['ticker']} Position #{match['position_id']} → Signal #{match['signal_id']} ({match['signal_timeframe']})")

    print()
    response = input("Update positions with these signal links? (yes/no): ").strip().lower()

    if response != 'yes':
        print("❌ Update cancelled")
        return

    # Update positions
    print()
    print("Updating positions...")

    with db.get_connection() as conn:
        cursor = conn.cursor()
        for match in matches:
            cursor.execute("""
                UPDATE positions
                SET signal_id = ?
                WHERE id = ?
            """, (match['signal_id'], match['position_id']))
        conn.commit()

    print(f"✅ Updated {len(matches)} positions with signal links")
    print()
    print("="*70)
    print("✅ LINKING COMPLETE")
    print("="*70)
    print()
    print("The trades CSV will now show complete signal information for these positions.")


if __name__ == "__main__":
    link_positions_to_signals()
