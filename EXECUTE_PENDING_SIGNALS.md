# Execute Pending Signals on DigitalOcean Server

Your 6 pending signals are waiting on your DigitalOcean server. Here's how to execute them TODAY.

---

## Quick Instructions

### Step 1: SSH into Your Server

```bash
ssh root@174.138.50.219
```

### Step 2: Navigate to Trading Bot Directory

```bash
cd ~/trading_bot/rsi_trading_bot
```

### Step 3: Check Pending Signals

```bash
source ../venv/bin/activate
python3 -c "
from database import get_database
db = get_database()
pending = db.get_pending_signals()
print(f'Pending signals: {len(pending)}')
for s in pending:
    print(f\"  {s['ticker']} - {s['divergence_type']} {s['timeframe']}\")
"
```

### Step 4: Execute Pending Signals

**Option A: Execute Immediately (if market is open)**

```bash
python3 -c "
import asyncio
from order_executor import get_order_executor

async def run():
    executor = get_order_executor()
    stats = await executor.execute_pending_signals()
    print(f'Executed: {stats[\"executed\"]}, Failed: {stats[\"failed\"]}')

asyncio.run(run())
"
```

**Option B: Verify Signals Will Execute at Market Open**

The pending signals will execute automatically at 9:30 AM ET when the market opens. The bot checks for pending signals every minute during market hours.

To verify the bot is running:

```bash
# Check bot status
ps aux | grep main.py

# Check recent logs
tail -100 bot.log
```

---

## Alternative: Upload and Run Script

If you prefer, I've created a script for you. Upload it to your server:

### On Your Local Machine:

```bash
# Copy script to server
scp execute_pending_signals.py root@174.138.50.219:~/trading_bot/
```

### On Your Server:

```bash
cd ~/trading_bot
python3 execute_pending_signals.py
```

---

## What Are the 6 Pending Signals?

Based on your screenshot:

1. **FOXA** - Bearish 1d @ $73.71
2. **FOX** - Bearish 1d @ $64.55
3. **FOXA** - Bearish 1d @ $73.62
4. **CHRW** - Bearish 1w @ $166.46
5. **MSI** - Bullish 3d @ $363.83
6. **EA** - Bearish 3d @ $204.20

---

## Important Notes

### Market Hours
- **Today (Dec 24):** Market may have early close (1:00 PM ET) for Christmas Eve
- **Tomorrow (Dec 25):** Market CLOSED for Christmas
- **Next trading day:** Friday, Dec 27

### Risk Limits Removed
The bot no longer has:
- Max positions limit (was 10)
- Daily trade limit (was 5)
- Daily loss limit (was $2000)

All 6 signals should execute without issues.

### T3 Take Profit Orders
The bot now places ALL three take profit orders:
- T1: +15% (70% of position)
- T2: +18% (15% of position)
- T3: +50% (15% of position)

---

## Troubleshooting

### If signals don't execute:

1. **Check bot is running:**
```bash
ps aux | grep main.py
```

2. **Check database status:**
```bash
python3 -c "
from database import get_database
db = get_database()
pending = db.get_pending_signals()
print('Pending:', len(pending))
for s in pending:
    print(f\"  {s['ticker']}: {s['status']}\")
"
```

3. **Manually execute:**
```bash
python3 -c "
import asyncio
from order_executor import get_order_executor
asyncio.run(get_order_executor().execute_pending_signals())
"
```

---

## Need Help?

If you encounter any issues, let me know and I can help troubleshoot.
