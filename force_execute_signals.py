#!/usr/bin/env python3
"""
Force Execute Specific Signals - Bypass Duplicate Check
Directly execute signal IDs 22, 23, 24, 25 (today's EA, JNJ, PDD, TER)
"""

import sys
import os
import asyncio
from pathlib import Path

# Add rsi_trading_bot to path
bot_dir = Path(__file__).parent / 'rsi_trading_bot'
sys.path.insert(0, str(bot_dir))

from database import get_database
from order_executor import OrderExecutor

async def force_execute():
    """Force execute specific signals without duplicate checking"""

    db = get_database()
    executor = OrderExecutor()

    # Get the specific signals we want to execute
    signal_ids = [22, 23, 24, 25]  # EA, JNJ, PDD, TER from today

    print("="*70)
    print("FORCE EXECUTING SIGNALS (BYPASSING DUPLICATE CHECK)")
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
        print("❌ No signals found with those IDs")
        return

    print(f"Found {len(signals)} signals to execute:")
    for sig in signals:
        print(f"  • ID {sig['id']}: {sig['ticker']} - {sig['divergence_type']} {sig['timeframe']}")
    print()

    print("🚀 Executing signals NOW (bypassing duplicate check)...")
    print()

    # Execute each signal directly
    for signal in signals:
        print(f"\nExecuting {signal['ticker']} (ID {signal['id']})...")
        try:
            success = await executor.execute_signal(signal)
            if success:
                print(f"✅ {signal['ticker']} executed successfully")
            else:
                print(f"❌ {signal['ticker']} execution failed")
        except Exception as e:
            print(f"❌ Error executing {signal['ticker']}: {e}")

    print()
    print("="*70)
    print("✅ EXECUTION COMPLETE")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(force_execute())
