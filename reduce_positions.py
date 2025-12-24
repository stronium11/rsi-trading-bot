#!/usr/bin/env python3
"""
Reduce oversized positions by specified dollar amounts

STRATEGY:
1. Cancel existing stop loss orders
2. Place market order to reduce position
3. Place new stop loss for remaining shares
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / 'rsi_trading_bot'))

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, StopOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from config import Config

# Positions to reduce and dollar amounts
REDUCTIONS = {
    'PDD': 10000,   # Reduce by $10,000
    'ARE': 10000,   # Reduce by $10,000
    'MSI': 5000,    # Reduce by $5,000
}

def main():
    """Reduce oversized positions"""

    print("="*70)
    print("REDUCING OVERSIZED POSITIONS")
    print("="*70 + "\n")

    # Initialize Alpaca client
    trading_client = TradingClient(
        api_key=Config.ALPACA_API_KEY,
        secret_key=Config.ALPACA_SECRET_KEY,
        paper=True
    )

    # Get all current positions
    try:
        positions = trading_client.get_all_positions()
    except Exception as e:
        print(f"❌ Error fetching positions: {e}")
        return

    # Create position lookup
    position_map = {p.symbol: p for p in positions}

    success_count = 0
    error_count = 0

    for ticker, reduction_amount in REDUCTIONS.items():
        print(f"\n{'='*70}")
        print(f"Processing: {ticker}")
        print(f"Target reduction: ${reduction_amount:,.2f}")
        print(f"{'='*70}")

        # Check if we have this position
        if ticker not in position_map:
            print(f"❌ No position found for {ticker}")
            error_count += 1
            continue

        position = position_map[ticker]
        current_qty = float(position.qty)
        current_price = float(position.current_price)
        direction = position.side  # 'long' or 'short'

        print(f"\nCurrent Position:")
        print(f"  Direction: {direction.upper()}")
        print(f"  Quantity: {current_qty:.4f} shares")
        print(f"  Current Price: ${current_price:.2f}")
        print(f"  Position Value: ${current_qty * current_price:,.2f}")

        # Calculate shares to reduce
        shares_to_reduce = reduction_amount / current_price

        print(f"\nReduction:")
        print(f"  Shares to reduce: {shares_to_reduce:.4f}")
        print(f"  Dollar value: ${shares_to_reduce * current_price:,.2f}")

        # Calculate remaining shares after reduction
        remaining_shares = current_qty - shares_to_reduce
        print(f"  Remaining shares after: {remaining_shares:.4f}")

        # Determine order side based on position direction
        if direction == 'long':
            # For LONG positions, SELL to reduce
            order_side = OrderSide.SELL
            stop_side = OrderSide.SELL
            # Stop loss 7% below entry
            entry_price = float(position.avg_entry_price)
            stop_price = round(entry_price * 0.93, 2)  # 7% below entry
        else:
            # For SHORT positions, BUY to reduce (cover)
            order_side = OrderSide.BUY
            stop_side = OrderSide.BUY
            # Stop loss 7% above entry
            entry_price = float(position.avg_entry_price)
            stop_price = round(entry_price * 1.07, 2)  # 7% above entry

        try:
            # STEP 1: Cancel existing stop loss orders
            print(f"\n🔍 Checking for existing stop loss orders...")
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus

            # Get open orders for this symbol
            order_filter = GetOrdersRequest(
                status=QueryOrderStatus.OPEN,
                symbols=[ticker]
            )
            existing_orders = trading_client.get_orders(filter=order_filter)

            stop_orders_cancelled = 0
            stop_orders_pending = 0
            for order in existing_orders:
                if order.type == 'stop':
                    # Check if order is already pending cancellation
                    if order.status == 'pending_cancel':
                        print(f"  Stop order {order.id} already pending cancellation...")
                        stop_orders_pending += 1
                    else:
                        print(f"  Cancelling stop order {order.id}...")
                        try:
                            trading_client.cancel_order_by_id(order.id)
                            stop_orders_cancelled += 1
                        except Exception as cancel_error:
                            # Order might already be pending cancel
                            if "pending cancel" in str(cancel_error):
                                print(f"  Order already pending cancellation")
                                stop_orders_pending += 1
                            else:
                                raise

            if stop_orders_cancelled > 0 or stop_orders_pending > 0:
                if stop_orders_cancelled > 0:
                    print(f"✅ Cancelled {stop_orders_cancelled} existing stop loss order(s)")
                if stop_orders_pending > 0:
                    print(f"⏳ {stop_orders_pending} stop loss order(s) already pending cancellation")

                # Wait and poll until orders are actually cancelled
                import time
                print(f"  Polling order status until cancelled (max 30 seconds)...")
                max_wait = 30
                poll_interval = 2
                elapsed = 0
                stop_orders_remaining = stop_orders_cancelled + stop_orders_pending

                while elapsed < max_wait:
                    time.sleep(poll_interval)
                    elapsed += poll_interval

                    # Check if stop orders are gone
                    check_filter = GetOrdersRequest(
                        status=QueryOrderStatus.OPEN,
                        symbols=[ticker]
                    )
                    current_orders = trading_client.get_orders(filter=check_filter)
                    stop_orders_remaining = sum(1 for o in current_orders if o.type == 'stop')

                    if stop_orders_remaining == 0:
                        print(f"  ✅ All stop orders cancelled after {elapsed} seconds")
                        break
                    else:
                        print(f"  ⏳ {stop_orders_remaining} stop order(s) still pending... ({elapsed}s elapsed)")

                if stop_orders_remaining > 0:
                    raise Exception(f"Stop orders still not cancelled after {max_wait} seconds")
            else:
                print(f"  No existing stop orders found")

            # STEP 2: Place market order to reduce position
            print(f"\n➡️  Placing {order_side.value.upper()} market order for {shares_to_reduce:.4f} shares...")

            order = MarketOrderRequest(
                symbol=ticker,
                qty=shares_to_reduce,
                side=order_side,
                time_in_force=TimeInForce.DAY
            )

            response = trading_client.submit_order(order)

            print(f"✅ Reduction order placed successfully!")
            print(f"   Order ID: {response.id}")
            print(f"   Status: {response.status}")

            # STEP 3: Place new stop loss for remaining shares
            print(f"\n➡️  Placing new stop loss for remaining {remaining_shares:.4f} shares...")
            print(f"   Stop price: ${stop_price:.2f} (7% from entry ${entry_price:.2f})")

            # Round remaining shares to whole number for GTC orders
            stop_qty = int(remaining_shares)

            stop_order = StopOrderRequest(
                symbol=ticker,
                qty=stop_qty,
                side=stop_side,
                stop_price=stop_price,
                time_in_force=TimeInForce.GTC
            )

            stop_response = trading_client.submit_order(stop_order)

            print(f"✅ New stop loss placed successfully!")
            print(f"   Order ID: {stop_response.id}")
            print(f"   Stop price: ${stop_price:.2f}")
            print(f"   Quantity: {stop_qty} shares")

            success_count += 1

        except Exception as e:
            print(f"❌ Error: {e}")
            error_count += 1

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total positions to reduce: {len(REDUCTIONS)}")
    print(f"✅ Successfully reduced: {success_count}")
    print(f"❌ Errors: {error_count}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
