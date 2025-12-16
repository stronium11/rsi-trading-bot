#!/usr/bin/env python3
"""
Sync orphaned positions from Alpaca to database
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'rsi_trading_bot'))

from alpaca_client import get_alpaca_client
from database import get_database

def sync_orphaned_positions():
    """Sync positions from Alpaca that aren't in database"""

    alpaca = get_alpaca_client()
    db = get_database()

    print("="*70)
    print("ORPHANED POSITION SYNC")
    print("="*70)
    print()

    # Get positions from Alpaca
    alpaca_positions = alpaca.trading_client.get_all_positions()

    # Get positions from database
    db_positions = db.get_open_positions()
    db_tickers = {pos['ticker'] for pos in db_positions}

    print(f"Alpaca positions: {len(alpaca_positions)}")
    print(f"Database positions: {len(db_positions)}")
    print()

    # Find orphaned positions
    orphaned = []
    for pos in alpaca_positions:
        if pos.symbol not in db_tickers:
            orphaned.append(pos)

    if not orphaned:
        print("✅ No orphaned positions found")
        return

    print(f"Found {len(orphaned)} orphaned positions:")
    print()

    for pos in orphaned:
        ticker = pos.symbol
        qty = float(pos.qty)
        entry = float(pos.avg_entry_price)
        side = pos.side

        print(f"{ticker}:")
        print(f"  Side: {side.upper()}")
        print(f"  Quantity: {qty}")
        print(f"  Entry: ${entry:.2f}")

        # Calculate stop loss
        from config import Config
        stop_pct = Config.STOP_LOSS_PCT / 100

        if side == 'long':
            direction = 'LONG'
            stop_price = round(entry * (1 - stop_pct), 2)
        else:
            direction = 'SHORT'
            stop_price = round(entry * (1 + stop_pct), 2)

        print(f"  Direction: {direction}")
        print(f"  Stop loss: ${stop_price:.2f}")
        print()

        response = input(f"Add {ticker} to database? (yes/no): ").strip().lower()

        if response == 'yes':
            # Create position record (without signal_id since we don't know which signal)
            position_id = db.add_position(
                signal_id=None,  # Unknown signal
                ticker=ticker,
                direction=direction,
                entry_price=entry,
                quantity=abs(qty),
                initial_stop=stop_price
            )

            print(f"  ✅ Added to database (Position ID: {position_id})")
        else:
            print(f"  ⏭️  Skipped {ticker}")

        print()

    print("="*70)
    print("SYNC COMPLETE")
    print("="*70)


if __name__ == "__main__":
    sync_orphaned_positions()
