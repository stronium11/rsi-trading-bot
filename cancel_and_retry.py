#!/usr/bin/env python3
"""
Cancel Existing Orders and Retry
Cancel the wash trade blocking orders, then place new market orders
"""

import sys
import os
from pathlib import Path
import time

# Add rsi_trading_bot to path
bot_dir = Path(__file__).parent / 'rsi_trading_bot'
sys.path.insert(0, str(bot_dir))

from database import get_database
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from config import Config

def main():
    """Cancel existing orders and place new ones"""

    db = get_database()
    is_paper = 'paper' in Config.ALPACA_BASE_URL
    client = TradingClient(Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY, paper=is_paper)

    print("="*70)
    print("CANCEL EXISTING ORDERS AND RETRY")
    print("="*70)
    print()

    # Orders to cancel (from error messages)
    orders_to_cancel = {
        'EA': 'd35d94d3-cfd3-4e45-94da-899c42dde3a3',
        'JNJ': '4e51e723-faa2-451f-a734-313500972433',
        'TER': 'ccd01b68-5c1f-43c6-90c9-cc672ec454f6'
    }

    # Cancel existing orders
    print("Cancelling existing orders...")
    for ticker, order_id in orders_to_cancel.items():
        try:
            client.cancel_order_by_id(order_id)
            print(f"✅ Cancelled {ticker} order {order_id}")
        except Exception as e:
            print(f"⚠️  Could not cancel {ticker} order: {e}")

    print("\nWaiting 2 seconds for cancellations to process...")
    time.sleep(2)
    print()

    # Get signals for EA, JNJ, TER
    signal_ids = [22, 23, 25]  # EA, JNJ, TER (skip PDD - already executed)

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT * FROM signals
            WHERE id IN ({','.join('?' * len(signal_ids))})
        """, signal_ids)
        signals = [dict(row) for row in cursor.fetchall()]

    print(f"Placing new orders for {len(signals)} signals:")
    for sig in signals:
        print(f"  • {sig['ticker']} - {sig['divergence_type']} {sig['timeframe']}")
    print()

    # Execute each signal
    for signal in signals:
        ticker = signal['ticker']
        divergence_type = signal['divergence_type']
        entry_price = signal['entry_price']
        direction = 'LONG' if divergence_type == 'Bullish' else 'SHORT'
        side = OrderSide.BUY if direction == 'LONG' else OrderSide.SELL

        # Calculate shares
        shares = Config.POSITION_SIZE / entry_price
        if direction == 'SHORT':
            shares = int(shares)

        print(f"\n{'='*70}")
        print(f"Placing {direction} market order for {ticker}...")
        print(f"  Shares: {shares:.4f}")
        print(f"{'='*70}")

        try:
            order_data = MarketOrderRequest(
                symbol=ticker,
                qty=shares,
                side=side,
                time_in_force=TimeInForce.DAY
            )

            order = client.submit_order(order_data)

            print(f"✅ Order placed for {ticker}")
            print(f"   Order ID: {order.id}")
            print(f"   Status: {order.status}")

            # Mark signal as executed
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE signals
                    SET status = 'executed', notes = 'Manual market order executed after cancellation'
                    WHERE id = ?
                """, (signal['id'],))

        except Exception as e:
            print(f"❌ Failed to place order for {ticker}: {e}")

            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE signals
                    SET status = 'failed', notes = ?
                    WHERE id = ?
                """, (f'Failed after cancel: {str(e)}', signal['id']))

    print()
    print("="*70)
    print("✅ COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
