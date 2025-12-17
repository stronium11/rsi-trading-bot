#!/usr/bin/env python3
"""Check signals in the OLD database (before path fix)"""

import sqlite3

# Old database location (before we fixed the path)
old_db_path = '/root/trading_bot.db'

print(f"Checking old database at: {old_db_path}")
print("="*70)

try:
    conn = sqlite3.connect(old_db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get today's signals
    cursor.execute("""
        SELECT id, ticker, divergence_type, timeframe, detected_at, status, notes
        FROM signals
        WHERE DATE(detected_at) = '2025-12-17'
        ORDER BY detected_at DESC
    """)

    signals = cursor.fetchall()

    if signals:
        print(f"\nFound {len(signals)} signals from today in OLD database:\n")
        for sig in signals:
            print(f"  ID {sig['id']}: {sig['ticker']} {sig['divergence_type']} {sig['timeframe']}")
            print(f"    Detected: {sig['detected_at']}")
            print(f"    Status: {sig['status']}")
            if sig['notes']:
                print(f"    Notes: {sig['notes']}")
            print()
    else:
        print("\n❌ No signals found from today in old database")

    conn.close()

except Exception as e:
    print(f"❌ Error reading old database: {e}")

print("="*70)
print("\nNow checking NEW database at: /root/trading_bot/rsi_trading_bot/trading_bot.db")
print("="*70)

try:
    new_conn = sqlite3.connect('/root/trading_bot/rsi_trading_bot/trading_bot.db')
    new_conn.row_factory = sqlite3.Row
    new_cursor = new_conn.cursor()

    new_cursor.execute("""
        SELECT id, ticker, divergence_type, timeframe, detected_at, status, notes
        FROM signals
        WHERE DATE(detected_at) = '2025-12-17'
        ORDER BY detected_at DESC
    """)

    new_signals = new_cursor.fetchall()

    if new_signals:
        print(f"\nFound {len(new_signals)} signals from today in NEW database:\n")
        for sig in new_signals:
            print(f"  ID {sig['id']}: {sig['ticker']} {sig['divergence_type']} {sig['timeframe']}")
            print(f"    Detected: {sig['detected_at']}")
            print(f"    Status: {sig['status']}")
            if sig['notes']:
                print(f"    Notes: {sig['notes']}")
            print()
    else:
        print("\n❌ No signals found from today in new database")

    new_conn.close()

except Exception as e:
    print(f"❌ Error reading new database: {e}")
