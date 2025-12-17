#!/usr/bin/env python3
"""Check what signals are in the database"""

import sys
from pathlib import Path

bot_dir = Path(__file__).parent / 'rsi_trading_bot'
sys.path.insert(0, str(bot_dir))

from database import get_database

db = get_database()

with db.get_connection() as conn:
    cursor = conn.cursor()

    # Get all signals
    cursor.execute("SELECT id, ticker, divergence_type, timeframe, detected_at, status FROM signals ORDER BY detected_at DESC LIMIT 10")
    signals = cursor.fetchall()

    print(f"Total signals in database: {len(signals)}")
    print("\nRecent signals:")
    for sig in signals:
        print(f"  ID {sig[0]}: {sig[1]} {sig[2]} {sig[3]} - Detected: {sig[4]} - Status: {sig[5]}")
