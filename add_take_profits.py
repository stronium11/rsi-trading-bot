#!/usr/bin/env python3
"""
Add Take Profit Orders to Existing Positions
Adds T1 and T2 take profit orders to positions that don't have them
"""

import sys
sys.path.insert(0, 'rsi_trading_bot')

from alpaca_client import get_alpaca_client
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import LimitOrderRequest


def add_take_profits():
    """Add T1 and T2 take profit orders to all open positions"""
    print("="*70)
    print("ADD TAKE PROFIT ORDERS TO EXISTING POSITIONS")
    print("="*70)
    print()

    alpaca = get_alpaca_client()

    # Get all open positions
    print("Fetching positions from Alpaca...")
    positions = alpaca.trading_client.get_all_positions()

    if not positions:
        print("✅ No open positions found")
        return

    print(f"Found {len(positions)} open positions")
    print()

    # Get all existing orders to check what we already have
    print("Fetching existing orders...")
    orders = alpaca.trading_client.get_orders()

    # Group orders by symbol
    orders_by_symbol = {}
    for order in orders:
        if order.symbol not in orders_by_symbol:
            orders_by_symbol[order.symbol] = []
        orders_by_symbol[order.symbol].append(order)

    print()
    print("="*70)

    for pos in positions:
        symbol = pos.symbol
        side = pos.side  # 'long' or 'short'
        qty = float(pos.qty)
        entry_price = float(pos.avg_entry_price)

        print(f"\n{symbol} ({side.upper()}):")
        print(f"  Entry: ${entry_price:.2f}")
        print(f"  Qty: {qty}")

        # Check existing orders for this symbol
        existing_orders = orders_by_symbol.get(symbol, [])
        limit_orders = [o for o in existing_orders if o.order_type == 'limit' and o.status == 'accepted']

        print(f"  Existing limit orders: {len(limit_orders)}")

        if len(limit_orders) >= 2:
            print(f"  ✅ Already has take profit orders, skipping")
            continue

        # Calculate take profit prices
        if side == 'long':
            # LONG: profit when price goes up
            t1_price = round(entry_price * 1.15, 2)  # +15%
            t2_price = round(entry_price * 1.18, 2)  # +18%
            tp_side = OrderSide.SELL
        else:
            # SHORT: profit when price goes down
            t1_price = round(entry_price * 0.85, 2)  # -15%
            t2_price = round(entry_price * 0.82, 2)  # -18%
            tp_side = OrderSide.BUY

        # Calculate quantities
        t1_qty = qty * 0.70  # 70% of position
        t2_qty = qty * 0.15  # 15% of position
        # Remaining 15% runs for T3 (+50%)

        # Determine time-in-force
        is_fractional_t1 = abs(t1_qty) != int(abs(t1_qty))
        is_fractional_t2 = abs(t2_qty) != int(abs(t2_qty))
        tif_t1 = TimeInForce.DAY if is_fractional_t1 else TimeInForce.GTC
        tif_t2 = TimeInForce.DAY if is_fractional_t2 else TimeInForce.GTC

        print(f"  Target T1: ${t1_price:.2f} ({'+15%' if side == 'long' else '-15%'}, {t1_qty:.4f} shares, {tif_t1})")
        print(f"  Target T2: ${t2_price:.2f} ({'+18%' if side == 'long' else '-18%'}, {t2_qty:.4f} shares, {tif_t2})")

        # Ask for confirmation
        response = input(f"  Add take profit orders for {symbol}? (y/n): ").strip().lower()

        if response != 'y':
            print(f"  ⏭️  Skipped {symbol}")
            continue

        try:
            # Place T1 order
            t1_order_data = LimitOrderRequest(
                symbol=symbol,
                qty=abs(t1_qty),
                side=tp_side,
                time_in_force=tif_t1,
                limit_price=t1_price
            )

            t1_order = alpaca.trading_client.submit_order(t1_order_data)
            print(f"  ✅ T1 order placed: {t1_order.id}")

            # Place T2 order
            t2_order_data = LimitOrderRequest(
                symbol=symbol,
                qty=abs(t2_qty),
                side=tp_side,
                time_in_force=tif_t2,
                limit_price=t2_price
            )

            t2_order = alpaca.trading_client.submit_order(t2_order_data)
            print(f"  ✅ T2 order placed: {t2_order.id}")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue

    print()
    print("="*70)
    print("COMPLETE")
    print("="*70)


if __name__ == "__main__":
    try:
        add_take_profits()
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
