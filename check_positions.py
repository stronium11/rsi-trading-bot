#!/usr/bin/env python3
"""Quick script to check current Alpaca positions"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / 'rsi_trading_bot'))

from alpaca_client import get_alpaca_client

alpaca = get_alpaca_client()
positions = alpaca.get_positions()

print(f"\nOpen positions: {len(positions)}\n")

if positions:
    for p in positions:
        print(f"  {p['symbol']:6s}: {float(p['qty']):>10.4f} shares @ ${float(p['avg_entry_price']):>8.2f}")
else:
    print("  No open positions found")
