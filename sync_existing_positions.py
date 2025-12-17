#!/usr/bin/env python3
"""
Sync Existing Alpaca Positions to Database

This script imports any open positions from Alpaca into the database
so they can be tracked and appear in the trades.csv report.

Usage: python3 sync_existing_positions.py
"""

import sys
import os
from pathlib import Path

# Add rsi_trading_bot to path
bot_dir = Path(__file__).parent / 'rsi_trading_bot'
sys.path.insert(0, str(bot_dir))

from config import Config
from database import get_database
from alpaca.trading.client import TradingClient
from datetime import datetime


def sync_positions():
    """Sync all open Alpaca positions to the database"""

    # Initialize
    db = get_database()
    is_paper = 'paper' in Config.ALPACA_BASE_URL
    client = TradingClient(Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY, paper=is_paper)

    print("="*70)
    print("SYNCING ALPACA POSITIONS TO DATABASE")
    print("="*70)
    print()

    # Get all open positions from Alpaca
    try:
        positions = client.get_all_positions()
        print(f"Found {len(positions)} open position(s) in Alpaca\n")
    except Exception as e:
        print(f"❌ Error fetching positions from Alpaca: {e}")
        return

    if not positions:
        print("✅ No open positions to sync")
        return

    synced = 0
    skipped = 0

    for pos in positions:
        symbol = pos.symbol
        qty = float(pos.qty)
        entry_price = float(pos.avg_entry_price)
        side = pos.side  # 'long' or 'short'
        direction = side.upper()

        # Check if position already exists in database
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM positions
                WHERE ticker = ? AND status = 'open'
            """, (symbol,))
            existing = cursor.fetchone()

        if existing:
            print(f"⚠️  {symbol} - Already tracked in database (skipping)")
            skipped += 1
            continue

        # Calculate stop loss (7% below entry for LONG, 7% above for SHORT)
        stop_loss_pct = Config.STOP_LOSS_PCT / 100
        if direction == 'LONG':
            stop_loss = entry_price * (1 - stop_loss_pct)
        else:
            stop_loss = entry_price * (1 + stop_loss_pct)

        # Add position to database
        # Note: We don't have signal_id since these weren't opened from detected signals
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO positions (
                    signal_id,
                    ticker,
                    direction,
                    entry_price,
                    quantity,
                    initial_stop,
                    current_stop,
                    remaining_quantity,
                    opened_at,
                    status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                None,  # No signal_id for manually synced positions
                symbol,
                direction,
                entry_price,
                qty,
                stop_loss,
                stop_loss,
                qty,  # Initially all quantity is remaining
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'open'
            ))
            position_id = cursor.lastrowid

        print(f"✅ {symbol} ({direction})")
        print(f"   Qty: {qty:.4f}")
        print(f"   Entry: ${entry_price:.2f}")
        print(f"   Stop Loss: ${stop_loss:.2f}")
        print(f"   Position ID: {position_id}")
        print()

        synced += 1

    print("="*70)
    print(f"✅ SYNC COMPLETE")
    print(f"   Synced: {synced}")
    print(f"   Skipped: {skipped}")
    print("="*70)
    print()

    if synced > 0:
        print("These positions will now appear in trades.csv as ONGOING trades.")
        print("Run: python3 rsi_trading_bot/reporting.py")
        print()


if __name__ == "__main__":
    sync_positions()
