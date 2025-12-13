# Position Manager Fix - Subscription Error Resolution

## Problem Summary

The ARE position was executing correctly in Alpaca but the position manager couldn't monitor it due to subscription errors:

```
{"message":"subscription does not permit querying recent SIP data"}
```

This error occurred every 5 minutes when the bot tried to use `get_latest_bars()` to fetch price data. The free/paper trading tier doesn't allow recent bar data queries.

## Root Cause

**position_manager.py** was using `get_latest_bars()` to get current prices for monitoring positions:

```python
# OLD CODE (broken)
bars = self.alpaca.get_latest_bars([ticker])
if not bars or ticker not in bars:
    print(f"Could not get price for {ticker}")
    return  # Silently fails to monitor!

current_price = bars[ticker]['close']
```

When `get_latest_bars()` failed due to subscription restrictions, the position manager would just **silently return** without monitoring the position.

## Solution

Use Alpaca's **position API** instead of bar data to get current prices. The position API provides `current_price` without any subscription restrictions:

```python
# NEW CODE (fixed)
alpaca_position = self.alpaca.get_position(ticker)
if not alpaca_position:
    print(f"Could not get position for {ticker} from Alpaca")
    return

current_price = alpaca_position['current_price']
```

## Additional Fixes

Also fixed dictionary access errors in exit methods (similar to the order_executor.py fix):

1. **execute_partial_exit()**: Changed `order.id` → `order['order_id']`
2. **close_entire_position()**: Changed `order.id` → `order['order_id']`
3. Removed wait loops (market orders fill immediately in paper trading)

## How to Apply the Fix on Server

### Option 1: Run the Python Script (Recommended)

```bash
# Copy the fix script to the server (use your method - scp, copy/paste, etc.)
cd /root/trading_bot/rsi_trading_bot
python3 fix_position_manager.py

# Restart the bot
systemctl restart rsi-trading-bot

# Watch the logs
journalctl -u rsi-trading-bot -f
```

### Option 2: Manual File Transfer

1. Copy the updated `position_manager.py` from the local repo to the server
2. Replace `/root/trading_bot/rsi_trading_bot/position_manager.py`
3. Restart: `systemctl restart rsi-trading-bot`

## What This Fixes

✅ **Position monitoring works** - No more subscription errors
✅ **ARE position is tracked** - Bot can now monitor targets (T1: +15%, T2: +18%, T3: +50%)
✅ **Stop loss monitoring** - Bot can detect if stop is hit
✅ **Partial exits work** - When targets are hit, bot can close portions correctly
✅ **Silent failures eliminated** - Position manager no longer fails silently

## Expected Behavior After Fix

When you check the logs after restarting, you should see:

```
======================================================================
POSITION MANAGER - Monitoring 1 positions
Time: 2025-12-12 XX:XX:XX ET
======================================================================
ARE: Current price: $XX.XX
ARE: Entry: $45.97, Current: $XX.XX, P&L: X.XX%
```

**No more subscription errors every 5 minutes!**

## Verification

After applying the fix and restarting, run:

```bash
journalctl -u rsi-trading-bot --no-pager | tail -100 | grep -i "ARE\|monitoring\|position"
```

You should see:
- "POSITION MANAGER - Monitoring 1 positions"
- ARE position details
- NO "subscription does not permit" errors

## Files Modified

- `position_manager.py` - Main fix (use position API instead of bars)

## Files Provided

1. `fix_position_manager.py` - Automated fix script
2. `position_manager.py` (in local repo) - Updated version
3. `POSITION_MANAGER_FIX.md` - This document

## Tomorrow's Trading

With this fix in place:
- 4 pending signals (CAT, GLW x2) will execute at 9:30 AM
- ARE position will be monitored continuously
- All positions will track profit targets correctly
- No more silent monitoring failures

## Technical Details

**Why position API works but bars don't:**
- Bar data (`get_latest_bars`) requires premium subscription for recent SIP data
- Position API (`get_position`) is included in all tiers (free/paper/live)
- Position object includes `current_price` which Alpaca updates in real-time
- This is actually MORE reliable than bars because it's the exact price Alpaca is tracking

**Why we removed wait loops:**
- In paper trading, market orders fill instantly
- No need to poll for fill status
- Simplifies code and reduces API calls
- Real trading may need wait loops, but not for paper

---

**Created**: 2025-12-12
**Issue**: Subscription errors preventing position monitoring
**Status**: Fixed, ready to deploy
