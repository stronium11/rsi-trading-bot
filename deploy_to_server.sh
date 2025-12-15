#!/bin/bash
# Deploy order_executor.py fix to the actual server
# Run this script ON THE SERVER (root@ubuntu-s-1vcpu-1gb-nyc3-01)

echo "=================================================="
echo "DEPLOYING ORDER EXECUTOR FIX TO SERVER"
echo "=================================================="
echo ""

# Find the trading bot directory
if [ -d "/root/trading_bot/rsi_trading_bot" ]; then
    BOT_DIR="/root/trading_bot/rsi_trading_bot"
elif [ -d "/home/user/stronium11/rsi_trading_bot" ]; then
    BOT_DIR="/home/user/stronium11/rsi_trading_bot"
else
    echo "❌ Could not find trading bot directory!"
    echo "Please update BOT_DIR in this script"
    exit 1
fi

echo "Bot directory: $BOT_DIR"
cd "$BOT_DIR" || exit 1

# Create backup
BACKUP_FILE="order_executor.py.backup.$(date +%Y%m%d_%H%M%S)"
cp order_executor.py "$BACKUP_FILE"
echo "✅ Backup created: $BACKUP_FILE"
echo ""

# Check if we have git and can pull
if [ -d .git ]; then
    echo "Git repository detected. Pulling latest changes..."
    git fetch origin
    git checkout claude/rsi-signal-system-016Ch1qMCkuLd6m8X8ZRb9ap
    git pull origin claude/rsi-signal-system-016Ch1qMCkuLd6m8X8ZRb9ap
    echo "✅ Pulled latest changes from git"
else
    echo "⚠️  No git repository. You'll need to manually copy the file."
    echo "Use: scp /home/user/stronium11/rsi_trading_bot/order_executor.py root@YOUR_SERVER:$BOT_DIR/"
    exit 1
fi

echo ""
echo "=================================================="
echo "VERIFICATION"
echo "=================================================="
echo ""

# Verify the fix
echo "Checking for issues..."

if grep -q "for _ in range(10):" order_executor.py; then
    echo "❌ ERROR: Wait loop still exists!"
    echo "Restoring backup..."
    cp "$BACKUP_FILE" order_executor.py
    exit 1
else
    echo "✅ Wait loop removed"
fi

if grep -q "self.alpaca.get_order" order_executor.py; then
    echo "❌ ERROR: get_order() call still exists!"
    echo "Restoring backup..."
    cp "$BACKUP_FILE" order_executor.py
    exit 1
else
    echo "✅ No get_order() calls"
fi

if grep -q "place_stop_loss_order" order_executor.py; then
    echo "✅ Stop loss code present"
else
    echo "❌ ERROR: Missing stop loss code!"
    echo "Restoring backup..."
    cp "$BACKUP_FILE" order_executor.py
    exit 1
fi

if grep -q "add_position" order_executor.py; then
    echo "✅ Position creation code present"
else
    echo "❌ ERROR: Missing position creation!"
    echo "Restoring backup..."
    cp "$BACKUP_FILE" order_executor.py
    exit 1
fi

echo ""
echo "=================================================="
echo "✅ DEPLOYMENT SUCCESSFUL"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Restart bot:    sudo systemctl restart rsi-trading-bot"
echo "2. Monitor logs:   sudo journalctl -u rsi-trading-bot -f"
echo ""
echo "What to look for in logs:"
echo "- Clean startup with no errors"
echo "- Position monitoring without subscription errors"
echo "- 'Monitoring 1 positions' every 5 minutes"
echo ""
echo "Backup saved: $BACKUP_FILE"
