# Server Deployment Instructions

## Current Status

✅ **Local Fix Complete**: The `order_executor.py` fix has been completed and verified locally
✅ **Committed**: Changes committed to branch `claude/rsi-signal-system-016Ch1qMCkuLd6m8X8ZRb9ap`
✅ **Pushed**: Changes pushed to remote repository

## What Was Fixed

- ❌ Removed broken wait loop calling non-existent `get_order()` method
- ❌ Removed object syntax (`order_status.status`)
- ✅ Added immediate order processing (paper trading fills instantly)
- ✅ Preserved stop loss calculation and placement
- ✅ Preserved position creation
- ✅ Preserved Telegram notifications

## Deploy to Server

### Option 1: Deploy via Git (Recommended)

SSH to your server and run:

```bash
# SSH to server
ssh root@YOUR_SERVER_IP

# Navigate to bot directory
cd /root/trading_bot/rsi_trading_bot  # or wherever your bot is installed

# Create backup
cp order_executor.py order_executor.py.backup.$(date +%Y%m%d_%H%M%S)

# Pull the fix
git fetch origin
git checkout claude/rsi-signal-system-016Ch1qMCkuLd6m8X8ZRb9ap
git pull origin claude/rsi-signal-system-016Ch1qMCkuLd6m8X8ZRb9ap

# Verify the fix
grep -c "for _ in range(10)" order_executor.py
# Should output: 0

grep -c "place_stop_loss_order" order_executor.py
# Should output: 1

# Restart the bot
sudo systemctl restart rsi-trading-bot

# Monitor logs
sudo journalctl -u rsi-trading-bot -f
```

### Option 2: Deploy via File Copy

If git isn't set up on the server:

```bash
# From your LOCAL machine:
scp /home/user/stronium11/rsi_trading_bot/order_executor.py root@YOUR_SERVER_IP:/root/trading_bot/rsi_trading_bot/

# Then SSH to server and restart:
ssh root@YOUR_SERVER_IP
sudo systemctl restart rsi-trading-bot
sudo journalctl -u rsi-trading-bot -f
```

## Verification After Deployment

After restarting the bot, check logs for:

✅ **Clean startup** - No Python errors or exceptions
✅ **Position monitoring** - "Monitoring 1 positions" every 5 minutes
✅ **No subscription errors** - Should use position API, not bar data
✅ **ARE position tracked** - Should show current price and P&L

## What Happens Tomorrow (9:30 AM)

The bot will execute 7 pending signals:
- CAT (Caterpillar)
- CPRT (Copart)
- EA (Electronic Arts)
- GLW (Corning) - 2 signals
- JNJ (Johnson & Johnson)
- LIN (Linde)
- TER (Teradyne)

For each signal, the bot will:
1. ✅ Place market order
2. ✅ Calculate -7% stop loss
3. ✅ Place stop loss order
4. ✅ Create position record
5. ✅ Send Telegram notification
6. ✅ Monitor for profit targets (T1: +15%, T2: +18%, T3: +50%)

## Troubleshooting

If you see errors in logs after restart:

1. **Check backup exists**: `ls -lh /root/trading_bot/rsi_trading_bot/order_executor.py.backup.*`
2. **View recent logs**: `journalctl -u rsi-trading-bot -n 100 --no-pager`
3. **Restore backup if needed**:
   ```bash
   cd /root/trading_bot/rsi_trading_bot
   cp order_executor.py.backup.TIMESTAMP order_executor.py
   sudo systemctl restart rsi-trading-bot
   ```

## Contact

If anything looks wrong in the logs, STOP and report back before market open tomorrow.

---
**Created**: 2025-12-15
**Priority**: CRITICAL - Must deploy before 9:30 AM tomorrow
