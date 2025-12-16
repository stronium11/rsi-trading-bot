#!/usr/bin/env python3
"""
Fix oversized ARE and MSI positions by selling excess shares to get back to target $5,000 position size
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent / 'rsi_trading_bot'))

from alpaca_client import get_alpaca_client
from database import get_database
from config import Config

def fix_oversized_positions():
    """Reduce ARE and MSI positions to target size"""

    alpaca = get_alpaca_client()
    db = get_database()

    target_position_size = Config.POSITION_SIZE  # $5,000

    print("="*70)
    print("FIXING OVERSIZED POSITIONS")
    print("="*70)
    print(f"Target position size: ${target_position_size:,.2f}")
    print()

    # Get all positions from Alpaca
    try:
        positions = alpaca.api.list_positions()
    except Exception as e:
        print(f"❌ Error fetching positions: {e}")
        return

    # Find ARE and MSI positions
    are_position = None
    msi_position = None

    for pos in positions:
        if pos.symbol == 'ARE':
            are_position = pos
        elif pos.symbol == 'MSI':
            msi_position = pos

    # Process ARE
    if are_position:
        process_position(alpaca, db, are_position, target_position_size, 'ARE')
    else:
        print("⚠️  ARE position not found in Alpaca")

    print()

    # Process MSI
    if msi_position:
        process_position(alpaca, db, msi_position, target_position_size, 'MSI')
    else:
        print("⚠️  MSI position not found in Alpaca")

    print()
    print("="*70)
    print("POSITION REDUCTION COMPLETE")
    print("="*70)


def process_position(alpaca, db, position, target_size, ticker):
    """Process a single position to reduce to target size"""

    print(f"{ticker} Position Analysis")
    print("-" * 70)

    # Get position details
    current_qty = float(position.qty)
    current_price = float(position.current_price)
    cost_basis = float(position.cost_basis)
    market_value = float(position.market_value)
    side = position.side  # 'long' or 'short'

    print(f"Current quantity: {current_qty} shares")
    print(f"Current price: ${current_price:.2f}")
    print(f"Cost basis: ${cost_basis:,.2f}")
    print(f"Market value: ${market_value:,.2f}")
    print(f"Side: {side.upper()}")
    print()

    # Calculate target quantity
    target_qty = target_size / current_price

    # Calculate shares to sell
    excess_qty = current_qty - target_qty

    if excess_qty <= 0:
        print(f"✅ {ticker} position is already at or below target size. No action needed.")
        return

    print(f"Target quantity: {target_qty:.4f} shares (${target_size:,.2f} value)")
    print(f"Excess quantity: {excess_qty:.4f} shares")
    print()

    # Confirm action
    reduction_value = excess_qty * current_price
    print(f"ACTION REQUIRED:")
    print(f"Sell {excess_qty:.4f} shares of {ticker} @ ${current_price:.2f}")
    print(f"This will reduce position value by ~${reduction_value:,.2f}")
    print(f"Final position value: ~${target_size:,.2f}")
    print()

    # Ask for confirmation
    response = input(f"Execute this trade? (yes/no): ").strip().lower()

    if response != 'yes':
        print(f"❌ Skipping {ticker} position reduction")
        return

    # Place the order
    print(f"\n🔄 Placing order to sell {excess_qty:.4f} shares of {ticker}...")

    try:
        # Place market order to sell
        if side == 'long':
            # For long positions, sell shares
            order = alpaca.api.submit_order(
                symbol=ticker,
                qty=excess_qty,
                side='sell',
                type='market',
                time_in_force='day'
            )
        else:
            # For short positions, buy to cover
            order = alpaca.api.submit_order(
                symbol=ticker,
                qty=excess_qty,
                side='buy',
                type='market',
                time_in_force='day'
            )

        print(f"✅ Order placed successfully!")
        print(f"   Order ID: {order.id}")
        print(f"   Status: {order.status}")
        print()

        # Update database to mark excess signals as 'closed'
        # This prevents them from being tracked
        update_database_for_reduction(db, ticker, target_qty)

    except Exception as e:
        print(f"❌ Error placing order: {e}")
        return


def update_database_for_reduction(db, ticker, target_qty):
    """Update database to reflect position reduction"""

    print(f"📝 Updating database for {ticker}...")

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Get all open positions for this ticker
        cursor.execute("""
            SELECT id, quantity, entry_price
            FROM positions
            WHERE ticker = ? AND status = 'open'
            ORDER BY created_at
        """, (ticker,))

        positions = cursor.fetchall()

        if not positions:
            print(f"⚠️  No open positions found in database for {ticker}")
            return

        print(f"Found {len(positions)} database positions for {ticker}")

        # We want to keep only the first position and mark others as reduced
        if len(positions) > 1:
            # Mark duplicate positions as closed
            for i, pos in enumerate(positions[1:], start=2):
                pos_id = pos[0]
                cursor.execute("""
                    UPDATE positions
                    SET status = 'closed',
                        notes = COALESCE(notes, '') || ' [Closed due to duplicate position - manual reduction]'
                    WHERE id = ?
                """, (pos_id,))
                print(f"  Marked position {pos_id} as closed (duplicate #{i})")

            conn.commit()
            print(f"✅ Database updated - kept first position, closed {len(positions)-1} duplicates")
        else:
            # Update the quantity of the remaining position
            pos_id = positions[0][0]
            cursor.execute("""
                UPDATE positions
                SET quantity = ?,
                    notes = COALESCE(notes, '') || ' [Quantity reduced from duplicate entries]'
                WHERE id = ?
            """, (target_qty, pos_id))
            conn.commit()
            print(f"✅ Updated position {pos_id} quantity to {target_qty:.4f}")


if __name__ == "__main__":
    print("\n⚠️  WARNING: This script will place REAL market orders!")
    print("Make sure you understand what this will do before proceeding.\n")

    response = input("Do you want to continue? (yes/no): ").strip().lower()

    if response == 'yes':
        fix_oversized_positions()
    else:
        print("\n❌ Operation cancelled by user")
