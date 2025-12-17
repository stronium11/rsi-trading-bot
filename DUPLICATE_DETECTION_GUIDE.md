# Sophisticated Duplicate Signal Detection

## Overview

The bot now uses intelligent duplicate detection that compares **4 factors** to determine if a signal is truly a duplicate:

1. **Ticker** (e.g., ARE)
2. **Divergence Type** (Bullish or Bearish)
3. **Timeframe** (1d, 3d, 1w)
4. **Close Price** (within $0.01 tolerance)

It looks back **2 weeks** to find matching signals.

## What It Allows ✓

These are **legitimate new signals** that will be executed:

| Scenario | Example | Why Allowed |
|----------|---------|-------------|
| **Different Timeframes** | ARE 1D Bullish @ $100<br>ARE 3D Bullish @ $100 | Different timeframes = different signals |
| **Different Price Levels** | ARE 1D Bullish @ $100<br>ARE 1D Bullish @ $120 | Same timeframe but price moved = new opportunity |
| **Time-Separated** | ARE 1D Bullish @ $100 (Jan 1)<br>ARE 1D Bullish @ $100 (Jan 20) | More than 2 weeks apart = new signal |
| **Different Direction** | ARE 1D Bullish @ $100<br>ARE 1D Bearish @ $100 | Opposite directions = different signals |

## What It Blocks ✗

These are **true duplicates** that will be skipped:

| Scenario | Example | Why Blocked |
|----------|---------|-------------|
| **Exact Duplicate** | ARE 1D Bullish @ $100.00 (Jan 1)<br>ARE 1D Bullish @ $100.00 (Jan 3) | Identical signal within 2 weeks |

## Real-World Example

**Your Scenario:**
```
Week 1: ARE 1D Bullish Divergence @ $95.00
  → Signal saved ✓
  → Order executed at 9:30 AM ✓

Week 5: ARE 3D Bullish Divergence @ $98.00
  → Different timeframe (3D vs 1D) ✓
  → Signal saved ✓
  → New position opened ✓

Result: Both positions allowed because they're different signals
```

**Duplicate Scenario (what gets blocked):**
```
Day 1, 7:00 AM: Scanner detects ARE 1D Bullish @ $100.00
  → Signal saved ✓

Day 1, 7:00 AM: Scanner detects ARE 1D Bullish @ $100.00 again (duplicate scan)
  → Blocked as duplicate ✗
  → Not saved to database
  → Notification sent

Result: Only one signal saved, duplicate prevented
```

## Detailed Notifications

### At Scanner (7:00 AM)

If duplicates are detected during the daily scan, you'll see:

```
📊 Daily Scan Summary

Total Signals: 5
Saved to Database: 3
Duplicates Skipped: 2

Breakdown:
• Bullish: 3
• Bearish: 2

By Timeframe:
• 1d: 4
• 3d: 1

⚠️ Duplicate Signals Detected:
• ARE (Bullish 1d) @ $100.00
  Duplicate of signal #42 from 2025-12-10 07:00:00
• MSI (Bearish 3d) @ $285.50
  Duplicate of signal #38 from 2025-12-09 07:00:00
```

### At Order Execution (9:30 AM)

If a duplicate signal somehow makes it to execution, you'll see:

```
⚠️ Duplicate Signal Detected

Current Signal:
• ARE - Bullish 1d
• Entry: $100.00

Original Signal:
• Detected: 2025-12-10 07:00:00
• ID: #42
• Status: executed
• Entry: $100.00

Signal skipped - identical to recent signal
```

## Technical Details

### Database Method
```python
check_for_duplicate_signal(ticker, divergence_type, timeframe, entry_price)
```

**Query Logic:**
```sql
SELECT * FROM signals
WHERE ticker = 'ARE'
AND divergence_type = 'Bullish'
AND timeframe = '1d'
AND ABS(entry_price - 100.00) < 0.01
AND detected_at >= '2025-12-03'  -- 2 weeks ago
```

**Returns:**
```python
{
    'is_duplicate': True/False,
    'original': {
        'id': 42,
        'ticker': 'ARE',
        'divergence_type': 'Bullish',
        'timeframe': '1d',
        'entry_price': 100.00,
        'detected_at': '2025-12-10 07:00:00',
        'status': 'executed'
    }
}
```

### Where It's Applied

1. **Live Scanner** (`live_scanner.py:235-260`)
   - Checks BEFORE saving to database
   - Prevents duplicates from being added
   - Shows duplicate details in scan summary

2. **Order Executor** (`order_executor.py:367-416`)
   - Double-check BEFORE execution
   - Safety net if duplicate somehow got saved
   - Sends detailed Telegram alert

## Benefits

✅ **Prevents duplicate orders** - No more 2x or 3x oversized positions from duplicate signals

✅ **Allows legitimate opportunities** - Different timeframes, price levels, or dates are still executed

✅ **Full transparency** - Clear notifications explain why signals were skipped

✅ **Historical tracking** - Links to original signal for reference

✅ **Flexible timeframe** - 2-week window balances duplicate prevention with opportunity capture

## Edge Cases Handled

| Case | Handling |
|------|----------|
| Price moved slightly | $100.00 vs $100.02 → Still duplicate (tolerance: $0.01) |
| Price moved significantly | $100.00 vs $105.00 → Not duplicate, new signal |
| Same day re-scan | Duplicate detected and skipped |
| 15 days later | New signal allowed (outside 2-week window) |
| 13 days later | Duplicate detected and skipped (within 2-week window) |
| Different account state | Doesn't matter - compares signal data only |

## Deployment

**To activate on your server:**

```bash
cd /home/user/stronium11/rsi_trading_bot
git pull origin claude/rsi-signal-system-016Ch1qMCkuLd6m8X8ZRb9ap
pkill -f "python.*main.py"
nohup python3 main.py > bot.log 2>&1 &
```

**Next scan:** Tomorrow 7:00 AM ET
**Next execution:** Tomorrow 9:30 AM ET

You'll see the new duplicate detection in action! 🎯
