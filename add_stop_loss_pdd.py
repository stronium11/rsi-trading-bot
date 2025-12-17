#!/usr/bin/env python3
"""
Add Stop Loss for PDD Position
Place protective stop loss for the PDD LONG position opened today
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

def main():
    """Add stop loss for PDD"""

    is_paper = 'paper' in Config.ALPACA_BASE_URL
    client = TradingClient(Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY, paper=is_paper)

    print("="*70)
    print("ADDING STOP LOSS FOR PDD")
    print("="*70)
    print()

    # Get PDD position
    try:
        position = client.get_open_position('PDD')

        qty = float(position.qty)
        entry_price = float(position.avg_entry_price)
        side = position.side

        print(f"PDD Position:")
        print(f"  Side: {side}")
        print(f"  Qty: {qty:.4f}")
        print(f"  Entry: ${entry_price:.2f}")
        print()

        # Calculate stop loss (7% below entry for LONG)
        stop_loss_pct = Config.STOP_LOSS_PCT / 100
        stop_price = entry_price * (1 - stop_loss_pct)

        print(f"Placing stop loss:")
        print(f"  Stop Price: ${stop_price:.2f}")
        print(f"  Type: SELL {qty:.4f} shares at stop")
        print()

        # Place stop loss order
        stop_order = StopOrderRequest(
            symbol='PDD',
            qty=qty,
            side=OrderSide.SELL,
            stop_price=stop_price,
            time_in_force=TimeInForce.GTC
        )

        order = client.submit_order(stop_order)

        print(f"✅ Stop loss placed!")
        print(f"   Order ID: {order.id}")
        print(f"   Status: {order.status}")
        print(f"   Stop Price: ${float(order.stop_price):.2f}")

    except Exception as e:
        print(f"❌ Error: {e}")

    print()
    print("="*70)


if __name__ == "__main__":
    main()
