#!/usr/bin/env python3
"""
Execute pending signals immediately (if market is open)
This script can be uploaded to your DigitalOcean server to execute the 6 pending signals today
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add rsi_trading_bot to path
sys.path.insert(0, str(Path.cwd() / 'rsi_trading_bot'))

from database import get_database
from order_executor import get_order_executor


async def main():
    """Execute all pending signals immediately"""

    print("="*70)
    print("EXECUTE PENDING SIGNALS")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}")
    print("="*70 + "\n")

    db = get_database()

    # Get all pending signals
    pending_signals = db.get_pending_signals()

    if not pending_signals:
        print("✅ No pending signals found")
        return

    print(f"Found {len(pending_signals)} pending signals:\n")

    # Display each pending signal
    for signal in pending_signals:
        print(f"• {signal['ticker']} - {signal['divergence_type']} {signal['timeframe']}")
        print(f"  Entry: ${signal.get('entry_price', 0):.2f}")
        print(f"  Detected: {signal.get('detected_at', 'N/A')}")
        print()

    # Execute signals
    print("="*70)
    print("Executing signals...")
    print("="*70 + "\n")

    executor = get_order_executor()
    stats = await executor.execute_pending_signals()

    # Summary
    print(f"\n{'='*70}")
    print("EXECUTION SUMMARY")
    print(f"{'='*70}")
    print(f"Total Pending: {stats['total_pending']}")
    print(f"✅ Executed: {stats['executed']}")
    print(f"❌ Failed: {stats['failed']}")
    print(f"⏭️ Skipped: {stats['skipped']}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
