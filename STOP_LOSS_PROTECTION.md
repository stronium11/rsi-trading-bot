# Stop Loss Protection System

## Problem

When executing SHORT positions, Alpaca's paper trading API rejects separate stop loss orders with:
```
"potential wash trade detected. use complex orders"
"opposite side market/stop order exists"
```

This leaves SHORT positions unprotected without stop losses.

## Solution

Two-part approach:
1. **Immediate**: Add stop losses to currently unprotected positions
2. **Ongoing**: Daily automated check to ensure all positions have stop loss protection

---

## Part 1: Add Stop Losses NOW

Run this script to protect your current 6 SHORT positions:

```bash
cd /root/trading_bot
source venv/bin/activate
python3 add_stop_losses.py
```

**What it does:**
- Checks all open positions in Alpaca
- Identifies which ones are missing stop loss orders
- Calculates proper stop price (-7% for LONG, +7% for SHORT)
- Cancels any conflicting orders (to avoid wash trade error)
- Places stop loss orders
- Shows summary of protected vs unprotected positions

**For your current positions:**
- CAT SHORT: Stop at $587.77 * 1.07 = $628.92
- CHRW SHORT: Stop at $157.93 * 1.07 = $169.00
- EA SHORT: Stop at $204.19 * 1.07 = $218.48
- GLW SHORT: Stop at $86.27 * 1.07 = $92.31
- JNJ SHORT: Stop at $209.20 * 1.07 = $223.84
- TER SHORT: Stop at $189.91 * 1.07 = $203.20

You'll be prompted to confirm each one.

---

## Part 2: Daily Automated Check

Set up a cron job to run the stop loss check daily at 10 AM ET (after market open):

```bash
# Edit crontab
crontab -e

# Add this line (runs at 10:00 AM ET / 3:00 PM UTC):
0 15 * * 1-5 cd /root/trading_bot && /root/trading_bot/venv/bin/python3 add_stop_losses.py --auto >> /var/log/stop_loss_check.log 2>&1
```

**Note:** The script currently requires manual confirmation. To make it run automatically in cron, we need to add an `--auto` flag that skips confirmations.

---

## Part 3: Fix Order Execution (Future)

The real fix is to use **bracket orders** in `order_executor.py` instead of separate market + stop orders.

Bracket orders bundle:
- Entry order (market buy/sell)
- Stop loss (automatically attached)
- Take profit (optional)

This way Alpaca won't see them as wash trades.

**Changes needed in `alpaca_client.py`:**

```python
from alpaca.trading.requests import MarketOrderRequest, OrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass

def place_bracket_order(self, symbol, direction, position_size, stop_loss_pct):
    """Place bracket order with built-in stop loss"""

    # Get current price
    current_price = self._get_price(symbol)

    # Calculate shares
    shares = position_size / current_price
    if direction == 'SHORT':
        shares = int(shares)

    # Calculate stop price
    if direction == 'LONG':
        stop_price = current_price * (1 - stop_loss_pct/100)
    else:
        stop_price = current_price * (1 + stop_loss_pct/100)

    # Create bracket order
    side = OrderSide.BUY if direction == 'LONG' else OrderSide.SELL

    bracket_order = MarketOrderRequest(
        symbol=symbol,
        qty=shares,
        side=side,
        time_in_force=TimeInForce.DAY,
        order_class=OrderClass.BRACKET,
        stop_loss={'stop_price': stop_price}
    )

    order = self.trading_client.submit_order(bracket_order)
    return order
```

**Benefits:**
- ✅ No wash trade errors
- ✅ Stop loss guaranteed to be placed
- ✅ Atomic operation (both or neither)
- ✅ Works for both LONG and SHORT

---

## Testing the Fix

After adding `--auto` flag:

```bash
# Test the script manually first
cd /root/trading_bot
source venv/bin/activate
python3 add_stop_losses.py

# Dry run to see what it would do
python3 add_stop_losses.py --dry-run

# Run automatically (no confirmations)
python3 add_stop_losses.py --auto
```

---

## Monitoring

Check the log file to see daily results:

```bash
tail -f /var/log/stop_loss_check.log
```

Expected output:
```
======================================================================
STOP LOSS PROTECTION CHECK
======================================================================

Found 10 open positions

CAT (SHORT):
  ✅ Stop loss exists: abc-123-def

CHRW (SHORT):
  ✅ Stop loss exists: xyz-456-uvw

...

======================================================================
SUMMARY
======================================================================
Total positions: 10
✅ Already protected: 10
⚠️  Unprotected: 0
➕ Stop losses added: 0

✅ All positions are now protected with stop losses
======================================================================
```

---

## Current Status

**Unprotected positions (need immediate attention):**
1. CAT SHORT - No stop loss
2. CHRW SHORT - No stop loss
3. EA SHORT - No stop loss
4. GLW SHORT - No stop loss
5. JNJ SHORT - No stop loss
6. TER SHORT - No stop loss

**Action required:** Run `python3 add_stop_losses.py` NOW to protect these positions.

---

## Next Steps

1. ✅ Run `add_stop_losses.py` now to protect current SHORT positions
2. ⏳ Add `--auto` flag to script for automated runs
3. ⏳ Set up cron job for daily 10 AM checks
4. ⏳ Update `order_executor.py` to use bracket orders
5. ⏳ Test bracket orders with next signal execution

---

**Priority: HIGH** - Unprotected SHORT positions expose you to unlimited risk if prices move against you.
