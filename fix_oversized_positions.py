#!/usr/bin/env python3
"""
Fix Oversized Positions
Reduces positions that are larger than expected back to target size
"""

import sys
sys.path.insert(0, 'rsi_trading_bot')

from alpaca_client import get_alpaca_client
from config import Config
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest


def fix_oversized_positions():
    """Identify and fix oversized positions"""
    print("="*70)
    print("FIX OVERSIZED POSITIONS")
    print("="*70)
    print()

    alpaca = get_alpaca_client()
    target_size = Config.POSITION_SIZE  # $5000

    print(f"Target position size: ${target_size:,.2f}")
    print(f"Tolerance: 1.5x (${target_size * 1.5:,.2f})")
    print()

    # Get all positions from Alpaca
    positions = alpaca.trading_client.get_all_positions()

    if not positions:
        print("No positions found")
        return

    print(f"Checking {len(positions)} positions...")
    print()

    oversized = []

    for pos in positions:
        symbol = pos.symbol
        qty = float(pos.qty)
        entry_price = float(pos.avg_entry_price)
        current_price = float(pos.current_price)
        market_value = abs(float(pos.market_value))
        side = pos.side  # 'long' or 'short'

        # Check if oversized (more than 1.5x target)
        if market_value > (target_size * 1.5):
            # Calculate target quantity
            target_qty = target_size / current_price
            excess_qty = abs(qty) - target_qty

            size_ratio = market_value / target_size

            oversized.append({
                'symbol': symbol,
                'side': side,
                'current_qty': abs(qty),
                'target_qty': target_qty,
                'excess_qty': excess_qty,
                'current_price': current_price,
                'market_value': market_value,
                'size_ratio': size_ratio
            })

            print(f"⚠️  {symbol} ({side.upper()}) - {size_ratio:.2f}x oversized")
            print(f"   Current: {abs(qty):.4f} shares (${market_value:,.2f})")
            print(f"   Target: {target_qty:.4f} shares (${target_size:,.2f})")
            print(f"   Excess: {excess_qty:.4f} shares (${excess_qty * current_price:,.2f})")
            print()

    if not oversized:
        print("✅ No oversized positions found")
        return

    print("="*70)
    print(f"FOUND {len(oversized)} OVERSIZED POSITION(S)")
    print("="*70)
    print()

    # Ask for confirmation
    print("This script will close EXCESS shares to bring positions back to target size.")
    print()
    response = input("Do you want to proceed? (yes/no): ").strip().lower()

    if response != 'yes':
        print("\nAborted. No changes made.")
        return

    print()
    print("="*70)
    print("EXECUTING ORDERS TO REDUCE POSITIONS")
    print("="*70)
    print()

    for pos in oversized:
        symbol = pos['symbol']
        excess_qty = pos['excess_qty']
        side = pos['side']

        # Determine order side (opposite of position side)
        if side == 'long':
            order_side = OrderSide.SELL  # Sell to reduce LONG
        else:
            order_side = OrderSide.BUY   # Buy to reduce SHORT

        print(f"Reducing {symbol} position by {excess_qty:.4f} shares...")

        try:
            # Create market order to close excess
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=excess_qty,
                side=order_side,
                time_in_force=TimeInForce.DAY
            )

            order = alpaca.trading_client.submit_order(order_data)

            print(f"✅ Order placed: {order.id}")
            print(f"   {order_side.value.upper()} {excess_qty:.4f} shares of {symbol}")
            print()

        except Exception as e:
            print(f"❌ Error placing order for {symbol}: {e}")
            print()
            continue

    print("="*70)
    print("COMPLETE")
    print("="*70)
    print()
    print("Please verify positions in Alpaca dashboard.")
    print("Note: You may need to manually adjust database records if they're out of sync.")


if __name__ == "__main__":
    try:
        fix_oversized_positions()
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
