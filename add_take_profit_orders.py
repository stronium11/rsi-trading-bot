#!/usr/bin/env python3
"""
Script to place missing take profit orders for existing positions
Places T1 (+15%, 70%), T2 (+18%, 15%), T3 (+50%, 15%)

STRATEGY:
1. Cancel existing stop loss order for each position
2. Place T1, T2, T3 take profit orders
3. Place new stop loss for remaining shares (15% after T1+T2 exit)
"""

import sys
from pathlib import Path

# Add rsi_trading_bot to path
sys.path.insert(0, str(Path.cwd() / 'rsi_trading_bot'))

from database import get_database
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest, StopOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from config import Config
import os


def main():
    """Place missing take profit orders for all open positions"""

    print("="*70)
    print("ADDING TAKE PROFIT ORDERS FOR EXISTING POSITIONS")
    print("="*70 + "\n")

    # Initialize clients
    db = get_database()
    trading_client = TradingClient(
        api_key=Config.ALPACA_API_KEY,
        secret_key=Config.ALPACA_SECRET_KEY,
        paper=True  # Paper trading
    )

    # Get all open positions from database (the single source of truth)
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                p.id,
                p.ticker,
                p.direction,
                p.entry_price,
                p.quantity,
                p.opened_at
            FROM positions p
            WHERE p.status = 'open'
            ORDER BY p.ticker
        """)

        positions = cursor.fetchall()

    if not positions:
        print("No open positions found in database.")
        print("\n⚠️  If you have positions in Alpaca, run this first:")
        print("    python3 sync_existing_positions.py")
        print("\nThen run this script again.")
        return

    print(f"Found {len(positions)} open positions\n")

    # Profit target configuration
    t1_pct = Config.TARGET1_PCT / 100  # 0.15 (+15%)
    t2_pct = Config.TARGET2_PCT / 100  # 0.18 (+18%)
    t3_pct = Config.TARGET3_PCT / 100  # 0.50 (+50%)

    t1_size = Config.TARGET1_SIZE / 100  # 0.70 (70%)
    t2_size = Config.TARGET2_SIZE / 100  # 0.15 (15%)
    t3_size = Config.TARGET3_SIZE / 100  # 0.15 (15%)

    success_count = 0
    error_count = 0

    for pos in positions:
        pos_id, ticker, direction, entry_price, quantity, opened_at = pos

        print(f"\n{'='*70}")
        print(f"Processing: {ticker}")
        print(f"Direction: {direction}")
        print(f"Entry: ${entry_price:.2f}")
        print(f"Quantity: {quantity:.4f}")
        print(f"Opened: {opened_at}")
        print(f"{'='*70}")

        try:
            # Calculate target prices based on direction
            if direction == 'LONG':
                # LONG: profit when price goes up
                t1_price = round(entry_price * (1 + t1_pct), 2)  # +15%
                t2_price = round(entry_price * (1 + t2_pct), 2)  # +18%
                t3_price = round(entry_price * (1 + t3_pct), 2)  # +50%
                order_side = OrderSide.SELL  # Sell to close long
            else:  # SHORT
                # SHORT: profit when price goes down
                t1_price = round(entry_price * (1 - t1_pct), 2)  # -15%
                t2_price = round(entry_price * (1 - t2_pct), 2)  # -18%
                t3_price = round(entry_price * (1 - t3_pct), 2)  # -50%
                order_side = OrderSide.BUY  # Buy to close short

            # Calculate quantities for each target (use absolute value for SHORT positions)
            abs_qty = abs(quantity)
            t1_qty = abs_qty * t1_size  # 70%
            t2_qty = abs_qty * t2_size  # 15%
            t3_qty = abs_qty * t3_size  # 15%

            # Round to whole shares (GTC orders require whole shares)
            t1_qty = int(t1_qty)
            t2_qty = int(t2_qty)
            t3_qty = int(t3_qty)

            print(f"\nTarget Prices:")
            print(f"  T1: ${t1_price:.2f} ({t1_pct*100:.0f}%) - {t1_size*100:.0f}% position ({t1_qty} shares)")
            print(f"  T2: ${t2_price:.2f} ({t2_pct*100:.0f}%) - {t2_size*100:.0f}% position ({t2_qty} shares)")
            print(f"  T3: ${t3_price:.2f} ({t3_pct*100:.0f}%) - {t3_size*100:.0f}% position ({t3_qty} shares)")

            # STEP 1: Cancel existing stop loss orders for this ticker
            print(f"\n🔍 Checking for existing stop loss orders...")
            existing_orders = trading_client.get_orders(status='open', symbols=[ticker])
            stop_orders_cancelled = 0
            for order in existing_orders:
                if order.type == 'stop':
                    print(f"  Cancelling stop order {order.id}...")
                    trading_client.cancel_order_by_id(order.id)
                    stop_orders_cancelled += 1
            if stop_orders_cancelled > 0:
                print(f"✅ Cancelled {stop_orders_cancelled} existing stop loss order(s)")
            else:
                print(f"  No existing stop orders found")

            # STEP 2: Place T1 take profit order
            print(f"\nPlacing T1 limit order...")
            t1_order = LimitOrderRequest(
                symbol=ticker,
                qty=t1_qty,
                side=order_side,
                limit_price=t1_price,
                time_in_force=TimeInForce.GTC
            )
            t1_response = trading_client.submit_order(t1_order)
            print(f"✅ T1 order placed: {t1_response.id}")

            # Place T2 take profit order
            print(f"Placing T2 limit order...")
            t2_order = LimitOrderRequest(
                symbol=ticker,
                qty=t2_qty,
                side=order_side,
                limit_price=t2_price,
                time_in_force=TimeInForce.GTC
            )
            t2_response = trading_client.submit_order(t2_order)
            print(f"✅ T2 order placed: {t2_response.id}")

            # Place T3 take profit order
            print(f"Placing T3 limit order...")
            t3_order = LimitOrderRequest(
                symbol=ticker,
                qty=t3_qty,
                side=order_side,
                limit_price=t3_price,
                time_in_force=TimeInForce.GTC
            )
            t3_response = trading_client.submit_order(t3_order)
            print(f"✅ T3 order placed: {t3_response.id}")

            # STEP 3: Place new stop loss for remaining shares (15% that will exit at T3)
            print(f"\nPlacing new stop loss for remaining shares...")

            # Calculate stop loss price (7% from entry)
            stop_loss_pct = Config.STOP_LOSS_PCT / 100
            if direction == 'LONG':
                stop_price = round(entry_price * (1 - stop_loss_pct), 2)
                stop_side = OrderSide.SELL
            else:  # SHORT
                stop_price = round(entry_price * (1 + stop_loss_pct), 2)
                stop_side = OrderSide.BUY

            # Stop loss is for the remaining 15% (t3_qty)
            stop_order = StopOrderRequest(
                symbol=ticker,
                qty=t3_qty,
                side=stop_side,
                stop_price=stop_price,
                time_in_force=TimeInForce.GTC
            )
            stop_response = trading_client.submit_order(stop_order)
            print(f"✅ New stop loss placed: ${stop_price:.2f} ({t3_qty} shares)")
            print(f"   Order ID: {stop_response.id}")

            success_count += 1
            print(f"\n✅ All orders placed successfully for {ticker}")
            print(f"   - 3 take profit orders (T1, T2, T3)")
            print(f"   - 1 stop loss order (for remaining 15%)")

        except Exception as e:
            print(f"\n❌ Error placing orders for {ticker}: {str(e)}")
            error_count += 1

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total positions: {len(positions)}")
    print(f"✅ Successfully processed: {success_count}")
    print(f"❌ Errors: {error_count}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
