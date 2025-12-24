#!/usr/bin/env python3
"""
Reduce oversized positions by specified dollar amounts
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / 'rsi_trading_bot'))

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
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

        # Determine order side based on position direction
        if direction == 'long':
            # For LONG positions, SELL to reduce
            order_side = OrderSide.SELL
        else:
            # For SHORT positions, BUY to reduce (cover)
            order_side = OrderSide.BUY

        # Confirm before placing order
        print(f"\n➡️  Placing {order_side.value.upper()} market order for {shares_to_reduce:.4f} shares...")

        try:
            # Place market order to reduce position
            order = MarketOrderRequest(
                symbol=ticker,
                qty=shares_to_reduce,
                side=order_side,
                time_in_force=TimeInForce.DAY
            )

            response = trading_client.submit_order(order)

            print(f"✅ Order placed successfully!")
            print(f"   Order ID: {response.id}")
            print(f"   Status: {response.status}")

            success_count += 1

        except Exception as e:
            print(f"❌ Error placing order: {e}")
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
