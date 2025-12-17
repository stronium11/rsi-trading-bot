#!/usr/bin/env python3
"""
Simple Market Orders - No Price Lookup Required
Place simple market orders using position size divided by signal entry price
"""

import sys
import os
from pathlib import Path

# Add rsi_trading_bot to path
bot_dir = Path(__file__).parent / 'rsi_trading_bot'
sys.path.insert(0, str(bot_dir))

from database import get_database
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from config import Config

def main():
    """Place simple market orders for today's signals"""

    db = get_database()

    is_paper = 'paper' in Config.ALPACA_BASE_URL
    client = TradingClient(Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY, paper=is_paper)

    # Get the specific signals
    signal_ids = [22, 23, 24, 25]  # EA, JNJ, PDD, TER

    print("="*70)
    print("SIMPLE MARKET ORDERS - NO PRICE LOOKUP")
    print("="*70)
    print()

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT * FROM signals
            WHERE id IN ({','.join('?' * len(signal_ids))})
        """, signal_ids)
        signals = [dict(row) for row in cursor.fetchall()]

    if not signals:
        print("❌ No signals found")
        return

    print(f"Found {len(signals)} signals:")
    for sig in signals:
        print(f"  • {sig['ticker']} - {sig['divergence_type']} {sig['timeframe']} @ ${sig['entry_price']:.2f}")
    print()

    # Get account info
    account = client.get_account()
    print(f"Account buying power: ${float(account.buying_power):.2f}")
    print()

    # Execute each signal
    for signal in signals:
        ticker = signal['ticker']
        divergence_type = signal['divergence_type']
        entry_price = signal['entry_price']
        direction = 'LONG' if divergence_type == 'Bullish' else 'SHORT'
        side = OrderSide.BUY if direction == 'LONG' else OrderSide.SELL

        # Calculate shares using signal entry price
        shares = Config.POSITION_SIZE / entry_price

        # Round to whole shares for SHORT orders (Alpaca requirement)
        if direction == 'SHORT':
            shares = int(shares)

        print(f"\n{'='*70}")
        print(f"Placing {direction} market order for {ticker}...")
        print(f"  Entry price (from signal): ${entry_price:.2f}")
        print(f"  Shares: {shares:.4f}")
        print(f"{'='*70}")

        try:
            # Create simple market order
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
            print(f"   Quantity: {shares:.4f}")

            # Mark signal as executed
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE signals
                    SET status = 'executed', notes = 'Manual market order executed'
                    WHERE id = ?
                """, (signal['id'],))

        except Exception as e:
            print(f"❌ Failed to place order for {ticker}: {e}")

            # Mark signal as failed
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE signals
                    SET status = 'failed', notes = ?
                    WHERE id = ?
                """, (f'Manual execution failed: {str(e)}', signal['id']))

    print()
    print("="*70)
    print("✅ EXECUTION COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
