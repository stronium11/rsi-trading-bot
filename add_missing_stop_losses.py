#!/usr/bin/env python3
"""
Add Missing Stop Losses
Places stop loss orders for positions that don't have them
"""

import sys
import os
from pathlib import Path

# Add rsi_trading_bot to path
bot_dir = Path(__file__).parent / 'rsi_trading_bot'
sys.path.insert(0, str(bot_dir))

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import StopOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from config import Config

def add_missing_stop_losses():
    """Add stop losses for positions that don't have them"""

    is_paper = 'paper' in Config.ALPACA_BASE_URL
    client = TradingClient(Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY, paper=is_paper)

    print("="*70)
    print("ADDING MISSING STOP LOSSES")
    print("="*70)
    print()

    # Get all positions
    positions = client.get_all_positions()
    print(f"Total positions: {len(positions)}")

    # Get all stop orders
    orders = client.get_orders()
    stop_orders = {order.symbol: order for order in orders if order.order_type.name == 'STOP'}
    print(f"Total stop loss orders: {len(stop_orders)}")
    print()

    # Find positions without stop losses
    missing_stops = []
    for pos in positions:
        if pos.symbol not in stop_orders:
            missing_stops.append(pos)

    if not missing_stops:
        print("✅ All positions have stop losses!")
        return

    print(f"⚠️  Found {len(missing_stops)} positions missing stop losses:")
    print()

    for pos in missing_stops:
        symbol = pos.symbol
        side = pos.side
        qty = float(pos.qty)
        entry_price = float(pos.avg_entry_price)
        direction = 'LONG' if side.name == 'LONG' else 'SHORT'

        print(f"{symbol} ({direction}):")
        print(f"  Position: {qty:.4f} shares @ ${entry_price:.2f}")

        # Calculate stop loss (7% below entry for LONG, 7% above for SHORT)
        stop_loss_pct = Config.STOP_LOSS_PCT / 100
        if direction == 'LONG':
            stop_price = round(entry_price * (1 - stop_loss_pct), 2)
            stop_side = OrderSide.SELL
        else:
            stop_price = round(entry_price * (1 + stop_loss_pct), 2)
            stop_side = OrderSide.BUY

        # Round quantity for GTC orders (Alpaca requirement)
        stop_qty = int(qty)

        print(f"  Stop Loss: {stop_side.name} {stop_qty} shares @ ${stop_price:.2f}")
        print()

    # Ask for confirmation
    response = input(f"Place stop losses for these {len(missing_stops)} positions? (yes/no): ").strip().lower()

    if response != 'yes':
        print("❌ Cancelled")
        return

    print()
    print("Placing stop loss orders...")
    print()

    # Place stop losses
    success_count = 0
    for pos in missing_stops:
        symbol = pos.symbol
        side = pos.side
        qty = float(pos.qty)
        entry_price = float(pos.avg_entry_price)
        direction = 'LONG' if side.name == 'LONG' else 'SHORT'

        # Calculate stop loss
        stop_loss_pct = Config.STOP_LOSS_PCT / 100
        if direction == 'LONG':
            stop_price = round(entry_price * (1 - stop_loss_pct), 2)
            stop_side = OrderSide.SELL
        else:
            stop_price = round(entry_price * (1 + stop_loss_pct), 2)
            stop_side = OrderSide.BUY

        # Round quantity
        stop_qty = int(qty)

        try:
            stop_order = StopOrderRequest(
                symbol=symbol,
                qty=stop_qty,
                side=stop_side,
                stop_price=stop_price,
                time_in_force=TimeInForce.GTC
            )

            order = client.submit_order(stop_order)

            print(f"✅ {symbol}: Stop loss placed")
            print(f"   Order ID: {order.id}")
            print(f"   {stop_side.name} {stop_qty} shares @ ${stop_price:.2f}")
            success_count += 1

        except Exception as e:
            print(f"❌ {symbol}: Failed to place stop loss")
            print(f"   Error: {e}")

        print()

    print("="*70)
    print(f"✅ COMPLETE: Placed {success_count}/{len(missing_stops)} stop losses")
    print("="*70)


if __name__ == "__main__":
    add_missing_stop_losses()
