#!/usr/bin/env python3
"""
Investigate Existing Orders and Positions
Check what orders and positions exist before cancelling anything
"""

import sys
import os
from pathlib import Path

# Add rsi_trading_bot to path
bot_dir = Path(__file__).parent / 'rsi_trading_bot'
sys.path.insert(0, str(bot_dir))

from alpaca.trading.client import TradingClient
from config import Config

def main():
    """Investigate existing orders and positions"""

    is_paper = 'paper' in Config.ALPACA_BASE_URL
    client = TradingClient(Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY, paper=is_paper)

    print("="*70)
    print("INVESTIGATING EXISTING ORDERS AND POSITIONS")
    print("="*70)
    print()

    # Get all open positions
    print("OPEN POSITIONS:")
    print("-"*70)
    try:
        positions = client.get_all_positions()
        if positions:
            for pos in positions:
                print(f"\n{pos.symbol}:")
                print(f"  Side: {pos.side}")
                print(f"  Qty: {pos.qty}")
                print(f"  Entry Price: ${float(pos.avg_entry_price):.2f}")
                print(f"  Current Price: ${float(pos.current_price):.2f}")
                print(f"  P&L: ${float(pos.unrealized_pl):.2f} ({float(pos.unrealized_plpc)*100:.2f}%)")
        else:
            print("  No open positions")
    except Exception as e:
        print(f"  Error getting positions: {e}")

    print("\n" + "="*70)
    print("ALL OPEN ORDERS:")
    print("-"*70)

    # Get all open orders
    try:
        orders = client.get_orders()

        if orders:
            for order in orders:
                print(f"\n{order.symbol}:")
                print(f"  Order ID: {order.id}")
                print(f"  Type: {order.order_type}")
                print(f"  Side: {order.side}")
                print(f"  Qty: {order.qty}")
                print(f"  Status: {order.status}")
                print(f"  Time in Force: {order.time_in_force}")

                # Check if it's a stop loss
                if hasattr(order, 'stop_price') and order.stop_price:
                    print(f"  Stop Price: ${float(order.stop_price):.2f}")

                # Check if it's a limit order
                if hasattr(order, 'limit_price') and order.limit_price:
                    print(f"  Limit Price: ${float(order.limit_price):.2f}")

                # Check order class (bracket, oco, etc)
                if hasattr(order, 'order_class'):
                    print(f"  Order Class: {order.order_class}")

                # Check if it's part of a leg
                if hasattr(order, 'legs') and order.legs:
                    print(f"  Legs: {len(order.legs)}")
                    for i, leg in enumerate(order.legs):
                        print(f"    Leg {i+1}: {leg}")

                print(f"  Created: {order.created_at}")
        else:
            print("  No open orders")

    except Exception as e:
        print(f"  Error getting orders: {e}")

    print("\n" + "="*70)
    print("SPECIFIC ORDER IDS FROM ERROR MESSAGES:")
    print("-"*70)

    # Check the specific order IDs that were blocking
    blocking_orders = {
        'EA': 'd35d94d3-cfd3-4e45-94da-899c42dde3a3',
        'JNJ': '4e51e723-faa2-451f-a734-313500972433',
        'TER': 'ccd01b68-5c1f-43c6-90c9-cc672ec454f6'
    }

    for ticker, order_id in blocking_orders.items():
        print(f"\n{ticker} - Order ID: {order_id}")
        try:
            order = client.get_order_by_id(order_id)
            print(f"  Symbol: {order.symbol}")
            print(f"  Type: {order.order_type}")
            print(f"  Side: {order.side}")
            print(f"  Qty: {order.qty}")
            print(f"  Status: {order.status}")

            if hasattr(order, 'stop_price') and order.stop_price:
                print(f"  Stop Price: ${float(order.stop_price):.2f}")

            if hasattr(order, 'limit_price') and order.limit_price:
                print(f"  Limit Price: ${float(order.limit_price):.2f}")

            if hasattr(order, 'order_class'):
                print(f"  Order Class: {order.order_class}")

            print(f"  Created: {order.created_at}")

            # CRITICAL: Check if this order is protecting a position
            print(f"\n  🔍 ANALYSIS:")
            try:
                position = client.get_open_position(ticker)
                print(f"  ⚠️  WARNING: Open position exists for {ticker}!")
                print(f"     Position side: {position.side}")
                print(f"     Position qty: {position.qty}")
                print(f"     This order might be a STOP LOSS protecting the position!")
            except:
                print(f"  ✅ No open position for {ticker}")
                print(f"     This order is likely orphaned from failed execution")

        except Exception as e:
            print(f"  Error getting order details: {e}")

    print("\n" + "="*70)


if __name__ == "__main__":
    main()
