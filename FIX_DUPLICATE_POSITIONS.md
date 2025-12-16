# Fix Duplicate Positions - ARE & MSI

## Problem Summary

**ARE Position:** Cost basis $15,397 (should be ~$5,000) - **3 duplicate entries**
**MSI Position:** Value $10,006 (should be ~$5,000) - **2 duplicate entries**

**Root Cause:** The duplicate prevention method was never implemented, allowing the scanner to create multiple signals for the same ticker.

## What Was Fixed

### 1. Added Duplicate Prevention (database.py)
- New method: `has_active_signal_or_position(ticker)`
- Checks for pending signals AND open positions
- Returns True if ticker should be skipped

### 2. Updated Scanner (live_scanner.py)
- Calls duplicate check before saving each signal
- Skips and logs duplicates
- Shows count of skipped signals

### 3. Investigation Script (investigate_duplicates.py)
- Shows all signals and positions for ARE and MSI
- Helps understand the duplicate situation

### 4. Position Reduction Script (fix_oversized_positions.py)
- Calculates excess shares automatically
- Places market orders to reduce positions to $5,000
- Updates database to mark duplicates as closed
- **Interactive with confirmations before trading**

---

## STEP 1: Investigate Current State (Optional)

Run on the **server** via DO console:

```bash
cd /root/trading_bot
source venv/bin/activate
cd /root/trading_bot

# Pull the latest code
cd /root/trading_bot/rsi_trading_bot
git pull origin claude/rsi-signal-system-016Ch1qMCkuLd6m8X8ZRb9ap

# Go to parent directory where scripts are
cd /root/trading_bot

# Run investigation script
python3 investigate_duplicates.py
```

This will show you:
- How many ARE signals exist in database
- How many MSI signals exist in database
- How many positions for each
- When they were created

---

## STEP 2: Fix Oversized Positions

**⚠️ WARNING: This step places REAL market orders!**

Run on the **server** via DO console:

```bash
cd /root/trading_bot
source venv/bin/activate

# Run the position reduction script
python3 fix_oversized_positions.py
```

### What the Script Does:

1. **Fetches current positions from Alpaca**
   - Gets ARE and MSI positions
   - Shows current quantity, price, and value

2. **Calculates reduction needed**
   - Target: $5,000 per position
   - Calculates excess shares to sell

3. **Shows you the plan**
   ```
   ARE Position Analysis
   Current quantity: X shares
   Current price: $Y
   Market value: $15,397

   Target quantity: Z shares ($5,000 value)
   Excess quantity: A shares

   ACTION: Sell A shares @ $Y
   This will reduce position value by ~$10,397
   Final position value: ~$5,000
   ```

4. **Asks for confirmation** (twice!)
   - First: "Do you want to continue?"
   - Then for each position: "Execute this trade?"

5. **Places market orders**
   - Sells excess shares
   - Updates database

### Expected Results:

**ARE:**
- Current: ~$15,397 (likely ~115-120 shares)
- Will sell: ~75-80 shares (2/3 of position)
- Final: ~$5,000 (~37-40 shares)

**MSI:**
- Current: ~$10,006 (likely ~22-23 shares)
- Will sell: ~11 shares (1/2 of position)
- Final: ~$5,000 (~11 shares)

---

## STEP 3: Deploy Duplicate Prevention

After fixing positions, deploy the code to prevent future duplicates:

```bash
cd /root/trading_bot/rsi_trading_bot

# Already pulled in Step 1, but if not:
git pull origin claude/rsi-signal-system-016Ch1qMCkuLd6m8X8ZRb9ap

# Restart the bot
systemctl restart rsi-trading-bot

# Verify it started
systemctl status rsi-trading-bot

# Check logs for clean startup
journalctl -u rsi-trading-bot -n 30 --no-pager
```

### Verify Duplicate Prevention is Active:

Tomorrow morning (or next scan), check logs for:
```
⚠️  Skipped X duplicate signals
```

This confirms the duplicate prevention is working.

---

## STEP 4: Verify Positions

After running the fix script, verify in Alpaca:

1. **Check ARE position**
   - Should be ~$5,000 market value
   - Should have ~37-40 shares

2. **Check MSI position**
   - Should be ~$5,000 market value
   - Should have ~11 shares

3. **Check database**
   ```bash
   cd /root/trading_bot
   python3 investigate_duplicates.py
   ```
   - Should show duplicate positions marked as "closed"
   - One position should remain "open" with correct quantity

---

## FAQ

### Q: Will this affect my profit tracking?
**A:** The script marks duplicate positions as "closed" in the database but doesn't record them as trades with P&L. They're essentially removed from tracking. The remaining position will be tracked normally.

### Q: What if the market is closed?
**A:** Market orders will be queued and execute when market opens at 9:30 AM ET. The script will place the orders successfully but they'll fill at opening prices.

### Q: Can I run this during market hours?
**A:** Yes, that's actually best. Orders will fill immediately at current market prices.

### Q: What if I accidentally run it twice?
**A:** The script checks current Alpaca positions each time. If you already reduced a position, it will see the correct size and say "No action needed."

### Q: What about stop loss orders?
**A:** The existing stop loss orders will remain active for the full position. You may want to manually check and adjust them after reduction.

---

## Safety Features

1. ✅ **Two confirmation prompts** - Must type "yes" twice
2. ✅ **Shows exact trade details** before execution
3. ✅ **Only processes ARE and MSI** - Won't touch other positions
4. ✅ **Checks if reduction needed** - Skips if already correct size
5. ✅ **Updates database properly** - Marks duplicates as closed

---

## Next Steps After Fix

1. ✅ Monitor tomorrow's 7:00 AM scan for duplicate prevention
2. ✅ Verify no duplicate signals are created
3. ✅ Check that existing open positions block new signals
4. ✅ Ensure future scans only create 1 signal per ticker

---

## Summary

**Files Changed:**
- `rsi_trading_bot/database.py` - Added `has_active_signal_or_position()`
- `rsi_trading_bot/live_scanner.py` - Added duplicate checking
- `investigate_duplicates.py` - Investigation tool
- `fix_oversized_positions.py` - Position reduction tool

**What Happens:**
1. Investigation shows the duplicate signals
2. Reduction script sells excess shares to get back to $5,000 per position
3. Database updated to mark duplicates as closed
4. Future scans prevented from creating duplicates

**Ready to execute when you are!**
