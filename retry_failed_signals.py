#!/usr/bin/env python3
"""
Retry Failed Signals - Reset and Execute NOW
Run this to retry today's failed signals before market close
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


async def retry_failed_signals():
    """Reset failed signals and execute them immediately"""

    db = get_database()

    print("="*70)
    print("RETRYING FAILED SIGNALS")
    print("="*70)
    print()

    # Get today's failed signals
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, ticker, divergence_type, timeframe
            FROM signals
            WHERE DATE(detected_at) = DATE('now')
            AND status = 'failed'
        """)
        failed_signals = [dict(row) for row in cursor.fetchall()]

    if not failed_signals:
        print("✅ No failed signals found for today")
        return

    print(f"Found {len(failed_signals)} failed signals:")
    for sig in failed_signals:
        print(f"  • {sig['ticker']} - {sig['divergence_type']} {sig['timeframe']}")
    print()

    # Reset status to 'pending'
    with db.get_connection() as conn:
        cursor = conn.cursor()
        for sig in failed_signals:
            cursor.execute("""
                UPDATE signals
                SET status = 'pending', notes = 'Retrying after initial failure'
                WHERE id = ?
            """, (sig['id'],))
        conn.commit()

    print("✅ Reset signals to 'pending'")
    print()
    print("🚀 Executing signals NOW...")
    print()

    # Execute pending signals immediately
    executor = OrderExecutor()
    await executor.execute_pending_signals()

    print()
    print("="*70)
    print("✅ EXECUTION COMPLETE")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(retry_failed_signals())
