#!/usr/bin/env python3
"""
Stop Loss Verification and Protection Script
- Checks all open positions for stop loss protection
- Adds missing stop losses
- Can be run daily to ensure all positions are protected
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent / 'rsi_trading_bot'))

from alpaca_client import get_alpaca_client
from database import get_database
from config import Config

def add_stop_loss_protection():
    """Add stop losses to positions that are missing them"""

    alpaca = get_alpaca_client()
    db = get_database()

    print("="*70)
    print("STOP LOSS PROTECTION CHECK")
    print("="*70)
    print()

    # Get all open positions from Alpaca
    try:
        positions = alpaca.trading_client.get_all_positions()
    except Exception as e:
        print(f"❌ Error fetching positions: {e}")
        return

    if not positions:
        print("✅ No open positions")
        return

    print(f"Found {len(positions)} open positions")
    print()

    # Get all open orders (to check for existing stop losses)
    try:
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus

        order_request = GetOrdersRequest(status=QueryOrderStatus.OPEN)
        orders = alpaca.trading_client.get_orders(filter=order_request)
        stop_orders = {order.symbol: order for order in orders if order.type == 'stop'}
    except Exception as e:
        print(f"❌ Error fetching orders: {e}")
        return

    # Check each position
    unprotected_count = 0
    protected_count = 0
    added_count = 0

    for pos in positions:
        ticker = pos.symbol
        qty = float(pos.qty)
        entry_price = float(pos.avg_entry_price)
        current_price = float(pos.current_price)
        side = pos.side  # 'long' or 'short'

        print(f"\n{ticker} ({side.upper()}):")
        print(f"  Quantity: {qty}")
        print(f"  Entry: ${entry_price:.2f}")
        print(f"  Current: ${current_price:.2f}")

        # Check if stop loss exists
        if ticker in stop_orders:
            print(f"  ✅ Stop loss exists: {stop_orders[ticker].id}")
            protected_count += 1
            continue

        # No stop loss - need to add one
        print(f"  ⚠️  NO STOP LOSS PROTECTION!")
        unprotected_count += 1

        # Calculate stop loss price
        stop_loss_pct = Config.STOP_LOSS_PCT / 100

        if side == 'long':
            # LONG: stop below entry
            stop_price = round(entry_price * (1 - stop_loss_pct), 2)
            stop_side = 'sell'
        else:
            # SHORT: stop above entry
            stop_price = round(entry_price * (1 + stop_loss_pct), 2)
            stop_side = 'buy'

        print(f"  Calculated stop: ${stop_price:.2f} ({side.upper()} position, {-Config.STOP_LOSS_PCT}%)")

        # Ask for confirmation
        response = input(f"  Add stop loss for {ticker}? (yes/no/skip): ").strip().lower()

        if response == 'skip':
            print(f"  ⏭️  Skipped {ticker}")
            continue

        if response != 'yes':
            print(f"  ❌ Not adding stop for {ticker}")
            continue

        # Try to add stop loss
        try:
            # First, check for and cancel any conflicting orders
            conflicting_orders = [
                o for o in orders
                if o.symbol == ticker and o.side == stop_side
            ]

            if conflicting_orders:
                print(f"  Found {len(conflicting_orders)} conflicting orders, canceling...")
                for order in conflicting_orders:
                    try:
                        alpaca.trading_client.cancel_order_by_id(order.id)
                        print(f"    Canceled order {order.id}")
                    except Exception as e:
                        print(f"    Error canceling {order.id}: {e}")

            # Now place the stop loss
            from alpaca.trading.requests import StopOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce

            order_side = OrderSide.SELL if stop_side == 'sell' else OrderSide.BUY

            stop_request = StopOrderRequest(
                symbol=ticker,
                qty=abs(qty),
                side=order_side,
                stop_price=stop_price,
                time_in_force=TimeInForce.GTC  # Good til canceled
            )

            stop_order = alpaca.trading_client.submit_order(stop_request)

            print(f"  ✅ Stop loss added: Order {stop_order.id}")
            print(f"     Will trigger at ${stop_price:.2f}")
            added_count += 1

        except Exception as e:
            print(f"  ❌ Error adding stop loss: {e}")

    # Summary
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total positions: {len(positions)}")
    print(f"✅ Already protected: {protected_count}")
    print(f"⚠️  Unprotected: {unprotected_count}")
    print(f"➕ Stop losses added: {added_count}")
    print()

    if unprotected_count - added_count > 0:
        print(f"⚠️  WARNING: {unprotected_count - added_count} positions still unprotected!")
    else:
        print("✅ All positions are now protected with stop losses")

    print("="*70)


if __name__ == "__main__":
    print("\n⚠️  This script will add stop loss orders to your Alpaca account")
    print("Stop losses will be placed at -7% from entry price")
    print()

    response = input("Do you want to continue? (yes/no): ").strip().lower()

    if response == 'yes':
        add_stop_loss_protection()
    else:
        print("\n❌ Operation cancelled by user")
