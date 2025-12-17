#!/usr/bin/env python3
"""
Check Position Sizes - Find oversized positions
"""

import sys
sys.path.insert(0, 'rsi_trading_bot')

from alpaca_client import get_alpaca_client
from config import Config

def check_positions():
    """Check all positions against expected size"""
    print("="*70)
    print("POSITION SIZE CHECK")
    print("="*70)
    print()

    alpaca = get_alpaca_client()
    expected_size = Config.POSITION_SIZE  # $5000

    print(f"Expected position size: ${expected_size:,.2f}")
    print()

    # Get all positions from Alpaca
    positions = alpaca.trading_client.get_all_positions()

    if not positions:
        print("No positions found")
        return

    print(f"Found {len(positions)} positions:")
    print()

    oversized = []

    for pos in positions:
        symbol = pos.symbol
        qty = float(pos.qty)
        entry_price = float(pos.avg_entry_price)
        current_price = float(pos.current_price)
        market_value = abs(float(pos.market_value))
        unrealized_pl = float(pos.unrealized_pl)
        side = pos.side  # 'long' or 'short'

        # Calculate ENTRY VALUE (what we paid when opening)
        entry_value = entry_price * abs(qty)

        # Calculate expected quantity for this position
        expected_qty = expected_size / entry_price

        # Check if ENTRY was oversized (not if it grew profitable)
        is_oversized = entry_value > (expected_size * 1.5)

        entry_ratio = entry_value / expected_size
        current_ratio = market_value / expected_size

        status = "⚠️ OPENED OVERSIZED" if is_oversized else "✅ OK"

        print(f"{symbol} ({side.upper()}):")
        print(f"  Current Qty: {qty:.4f} shares")
        print(f"  Expected Qty: {expected_qty:.4f} shares")
        print(f"  Entry Price: ${entry_price:.2f}")
        print(f"  Current Price: ${current_price:.2f}")
        print(f"  Entry Value: ${entry_value:,.2f} (opened at {entry_ratio:.2f}x)")
        print(f"  Market Value: ${market_value:,.2f} (currently {current_ratio:.2f}x)")
        print(f"  Expected Size: ${expected_size:,.2f}")
        print(f"  P&L: ${unrealized_pl:,.2f}")
        print(f"  Status: {status}")
        if is_oversized:
            print(f"  → Likely duplicate orders - should reduce position")
        elif current_ratio > 1.5:
            print(f"  → Position grew profitable - this is GOOD, don't reduce")
        print()

        if is_oversized:
            oversized.append({
                'symbol': symbol,
                'side': side,
                'qty': qty,
                'expected_qty': expected_qty,
                'excess_qty': qty - expected_qty,
                'entry_price': entry_price,
                'entry_value': entry_value,
                'market_value': market_value,
                'entry_ratio': entry_ratio
            })

    if oversized:
        print("="*70)
        print(f"FOUND {len(oversized)} OVERSIZED POSITIONS:")
        print("="*70)
        print()

        for pos in oversized:
            print(f"{pos['symbol']}:")
            print(f"  Opened at: {pos['entry_ratio']:.2f}x expected size")
            print(f"  Entry value: ${pos['entry_value']:,.2f} (should be $5,000)")
            print(f"  Excess shares: {pos['excess_qty']:.4f}")
            print(f"  Excess value: ${pos['excess_qty'] * pos['entry_price']:,.2f}")
            print(f"  → Likely duplicate orders during opening")
            print()
    else:
        print("="*70)
        print("✅ All positions are within expected size limits")
        print("="*70)

if __name__ == "__main__":
    try:
        check_positions()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
