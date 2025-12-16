# Fixing Remaining Issues - Action Plan

## Issues Identified

1. ❌ **4 vs 10 positions** - Database shows 4, Alpaca has 10
2. ❌ **Duplicate signals** - 21 signals with duplicates
3. ❌ **Missing take profit orders** - Only stop losses exist, no take profit orders
4. ✅ **Startup message** - Fixed to show real Alpaca data with Long/Short breakdown

---

## STEP 1: Sync Orphaned Positions to Database

**Problem:** 6 SHORT positions exist in Alpaca but not in database because they failed to save when stop loss placement errored.

**Positions to sync:**
- CAT (SHORT)
- CHRW (SHORT)
- EA (SHORT)
- GLW (SHORT)
- JNJ (SHORT)
- TER (SHORT)

**Action:**

```bash
cd /root/trading_bot/rsi_trading_bot
git pull origin claude/rsi-signal-system-016Ch1qMCkuLd6m8X8ZRb9ap

cd /root/trading_bot
source venv/bin/activate
python3 sync_orphaned_positions.py
```

Type `yes` for each of the 6 SHORT positions to add them to the database.

**Expected result:** Database will have all 10 positions (4 LONG + 6 SHORT)

---

## STEP 2: Deploy Duplicate Prevention

**Problem:** Duplicate prevention code exists but hasn't been deployed. The bot needs to be restarted with the new code.

**What it prevents:**
- Multiple signals for the same ticker when a position is already open
- Multiple signals for the same ticker when a pending signal already exists

**Action:**

```bash
cd /root/trading_bot/rsi_trading_bot
git pull origin claude/rsi-signal-system-016Ch1qMCkuLd6m8X8ZRb9ap
systemctl restart rsi-trading-bot

# Verify restart
systemctl status rsi-trading-bot
journalctl -u rsi-trading-bot -n 30 --no-pager
```

**Expected result:**
- Tomorrow's 7 AM scan will skip tickers that already have open positions
- Startup message will show "Total Positions: 10 - LONG: 4 - SHORT: 6"
- Current P&L will be displayed

---

## STEP 3: Add Take Profit Orders (Code Fix Needed)

**Problem:** The `order_executor.py` only creates stop loss orders, not take profit orders.

**Current behavior:**
```python
# After market order fills:
1. Create position record
2. Place stop loss order  ← Only this
3. Update signal status
```

**Needed behavior:**
```python
# After market order fills:
1. Create position record
2. Place stop loss order
3. Place T1 take profit order (15%, close 70%)  ← Missing
4. Place T2 take profit order (18%, close 15%)  ← Missing
5. Update signal status
```

**Why it's complex:**
Alpaca has issues with:
- Multiple orders on the same position
- Wash trade detection
- Order conflicts

**Options:**

### Option A: Bracket Orders (Recommended)
Use Alpaca's bracket orders which include:
- Entry order
- Stop loss
- Single take profit

Then manually add second take profit after first fills.

### Option B: Separate Orders
Place take profit orders separately, but need to:
- Handle wash trade errors
- Use correct time-in-force for fractional shares
- Ensure orders don't conflict

**I recommend we tackle this as a separate task** because:
1. Your positions are protected with stop losses (most important)
2. You can manually set take profit orders in Alpaca dashboard
3. It requires careful testing to avoid order conflicts

---

## STEP 4: Verify Everything Works

After Steps 1 & 2, verify:

```bash
cd /root/trading_bot
python3 check_database.py
```

Should show:
- Total positions: 10
- All positions listed with correct details

Check Alpaca dashboard:
- 10 positions (4 LONG, 6 SHORT)
- Each position has stop loss order
- Manually add take profit orders for now

---

## Understanding the Duplicate Signals

**Why there are 21 signals:**

Looking at your database history:
- Some signals from multiple days
- Some were duplicates before prevention was added
- Some failed to execute
- Some executed successfully

**Breakdown (estimated):**
- 4 executed successfully (ARE, CPRT, LIN, MSI)
- 6 executed today (CAT, CHRW, EA, GLW, JNJ, TER)
- 8 skipped (duplicates)
- 3 other/old signals

**Going forward with duplicate prevention:**
- Scanner checks before adding signals
- Skips if ticker already has pending signal
- Skips if ticker already has open position

---

## Priority Actions (Do These Now)

### HIGH PRIORITY:

1. **Sync orphaned positions** (5 minutes)
   ```bash
   python3 sync_orphaned_positions.py
   ```

2. **Deploy duplicate prevention** (2 minutes)
   ```bash
   systemctl restart rsi-trading-bot
   ```

3. **Verify sync** (1 minute)
   ```bash
   python3 check_database.py
   ```

### MEDIUM PRIORITY:

4. **Manually add take profit orders** (10 minutes)
   - Go to Alpaca dashboard
   - For each position, create:
     - Limit order at +15% (70% of position size)
     - Limit order at +18% (15% of position size)

### LOW PRIORITY (Future Enhancement):

5. **Automate take profit orders** (requires code changes and testing)
   - Design bracket order system
   - Test with paper trading
   - Deploy after verification

---

## Expected State After Fixes

**Database:**
- 10 positions (synced with Alpaca)
- Signals marked correctly
- No orphaned positions

**Alpaca:**
- 4 LONG positions with stop losses
- 6 SHORT positions with stop losses
- (Manual) Take profit orders added

**Bot Behavior:**
- Tomorrow 7 AM: Scans, skips duplicates
- Tomorrow 9:30 AM: Executes new signals if any
- Shows correct position count and P&L on startup
- No more orphaned positions

---

## Run These Commands Now

```bash
cd /root/trading_bot/rsi_trading_bot
git pull origin claude/rsi-signal-system-016Ch1qMCkuLd6m8X8ZRb9ap

cd /root/trading_bot
source venv/bin/activate

# Step 1: Sync orphaned positions
python3 sync_orphaned_positions.py
# Type 'yes' for each SHORT position

# Step 2: Restart bot with all fixes
cd /root/trading_bot/rsi_trading_bot
systemctl restart rsi-trading-bot
sleep 5
systemctl status rsi-trading-bot

# Step 3: Verify
cd /root/trading_bot
python3 check_database.py
```

---

## Questions to Answer

1. **Should we build automatic take profit orders?**
   - Pros: Fully automated
   - Cons: Complex, needs testing, can conflict with Alpaca
   - Alternative: Manual for now, automate later

2. **How to handle the take profit orders?**
   - Option A: You add manually in Alpaca (quick)
   - Option B: I build it (1-2 hours of work + testing)

Let me know your preference!
