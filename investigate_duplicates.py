#!/usr/bin/env python3
"""
Investigate duplicate positions for ARE and MSI
"""
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent / 'rsi_trading_bot'))

from database import get_database

def investigate():
    """Investigate duplicate positions"""
    db = get_database()

    print("="*70)
    print("DUPLICATE POSITION INVESTIGATION")
    print("="*70)
    print()

    # Check ARE
    print("ARE (Expected: 1 signal, 1 position)")
    print("-" * 70)

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Get ARE signals
        cursor.execute("""
            SELECT id, ticker, divergence_type, entry_price, status, detected_at
            FROM signals
            WHERE ticker = 'ARE'
            ORDER BY detected_at
        """)
        are_signals = cursor.fetchall()

        print(f"ARE Signals: {len(are_signals)}")
        for signal in are_signals:
            print(f"  ID {signal[0]}: {signal[2]} @ ${signal[3]:.2f} - Status: {signal[4]} - Detected: {signal[5]}")

        print()

        # Get ARE positions
        cursor.execute("""
            SELECT id, signal_id, ticker, direction, entry_price, quantity, status, created_at
            FROM positions
            WHERE ticker = 'ARE'
            ORDER BY created_at
        """)
        are_positions = cursor.fetchall()

        print(f"ARE Positions: {len(are_positions)}")
        for pos in are_positions:
            print(f"  ID {pos[0]}: Signal {pos[1]} - {pos[3]} - {pos[5]:.4f} shares @ ${pos[4]:.2f} - Status: {pos[6]} - Created: {pos[7]}")

        print()
        print("="*70)
        print()

        # Check MSI
        print("MSI (Expected: 1 signal, 1 position)")
        print("-" * 70)

        # Get MSI signals
        cursor.execute("""
            SELECT id, ticker, divergence_type, entry_price, status, detected_at
            FROM signals
            WHERE ticker = 'MSI'
            ORDER BY detected_at
        """)
        msi_signals = cursor.fetchall()

        print(f"MSI Signals: {len(msi_signals)}")
        for signal in msi_signals:
            print(f"  ID {signal[0]}: {signal[2]} @ ${signal[3]:.2f} - Status: {signal[4]} - Detected: {signal[5]}")

        print()

        # Get MSI positions
        cursor.execute("""
            SELECT id, signal_id, ticker, direction, entry_price, quantity, status, created_at
            FROM positions
            WHERE ticker = 'MSI'
            ORDER BY created_at
        """)
        msi_positions = cursor.fetchall()

        print(f"MSI Positions: {len(msi_positions)}")
        for pos in msi_positions:
            print(f"  ID {pos[0]}: Signal {pos[1]} - {pos[3]} - {pos[5]:.4f} shares @ ${pos[4]:.2f} - Status: {pos[6]} - Created: {pos[7]}")

        print()
        print("="*70)
        print()

        # Summary
        print("SUMMARY:")
        print(f"ARE: {len(are_signals)} signals, {len(are_positions)} positions")
        print(f"MSI: {len(msi_signals)} signals, {len(msi_positions)} positions")
        print()

        if len(are_signals) > 1:
            print(f"⚠️  ARE has {len(are_signals)} duplicate signals!")

        if len(msi_signals) > 1:
            print(f"⚠️  MSI has {len(msi_signals)} duplicate signals!")

        print()
        print("="*70)

if __name__ == "__main__":
    investigate()
