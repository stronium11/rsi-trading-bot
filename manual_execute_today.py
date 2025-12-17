#!/usr/bin/env python3
"""
Manual Execute Today's Signals - Direct Alpaca Orders
Bypass all checks and directly place bracket orders for EA, JNJ, PDD, TER
"""

import sys
import os
from pathlib import Path

# Add rsi_trading_bot to path
bot_dir = Path(__file__).parent / 'rsi_trading_bot'
sys.path.insert(0, str(bot_dir))

from database import get_database
from alpaca_client import get_alpaca_client
from config import Config

def main():
    """Manually execute today's failed signals"""

    db = get_database()
    alpaca = get_alpaca_client()

    # Get the specific signals
    signal_ids = [22, 23, 24, 25]  # EA, JNJ, PDD, TER

    print("="*70)
    print("MANUAL EXECUTION - DIRECT ALPACA ORDERS")
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
    account = alpaca.get_account()
    if not account:
        print("❌ Cannot get account info")
        return

    print(f"Account buying power: ${account['buying_power']}")
    print()

    # Execute each signal
    for signal in signals:
        ticker = signal['ticker']
        divergence_type = signal['divergence_type']
        direction = 'LONG' if divergence_type == 'Bullish' else 'SHORT'

        print(f"\n{'='*70}")
        print(f"Placing {direction} order for {ticker}...")
        print(f"{'='*70}")

        # Place bracket order with stop loss
        order = alpaca.place_bracket_order_with_stop(
            symbol=ticker,
            direction=direction,
            position_size=Config.POSITION_SIZE,
            stop_loss_pct=Config.STOP_LOSS_PCT
        )

        if order:
            print(f"✅ Order placed for {ticker}")
            print(f"   Order ID: {order['order_id']}")
            print(f"   Quantity: {order['qty']:.4f}")
            print(f"   Entry: ${order['price']:.2f}")
            print(f"   Stop: ${order['stop_price']:.2f}")

            # Mark signal as executed
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE signals
                    SET status = 'executed', notes = 'Manually executed via force script'
                    WHERE id = ?
                """, (signal['id'],))
        else:
            print(f"❌ Failed to place order for {ticker}")

            # Mark signal as failed
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE signals
                    SET status = 'failed', notes = 'Manual execution failed'
                    WHERE id = ?
                """, (signal['id'],))

    print()
    print("="*70)
    print("✅ MANUAL EXECUTION COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
