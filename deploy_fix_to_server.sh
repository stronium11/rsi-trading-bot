#!/bin/bash
# Deploy order_executor.py fix to the server

echo "=================================================="
echo "DEPLOYING ORDER EXECUTOR FIX"
echo "=================================================="
echo ""

# Navigate to bot directory
cd /root/trading_bot/rsi_trading_bot || exit 1

# Create backup
BACKUP_FILE="order_executor.py.backup.$(date +%Y%m%d_%H%M%S)"
cp order_executor.py "$BACKUP_FILE"
echo "✅ Backup created: $BACKUP_FILE"

# Pull the latest changes from the repo (or manually copy)
echo ""
echo "Replacing order_executor.py with fixed version..."
echo ""

# Copy the fixed file from the local repo
cp /home/user/stronium11/rsi_trading_bot/order_executor.py /root/trading_bot/rsi_trading_bot/order_executor.py

if [ $? -eq 0 ]; then
    echo "✅ File copied successfully"
else
    echo "❌ Failed to copy file"
    exit 1
fi

echo ""
echo "=================================================="
echo "VERIFICATION"
echo "=================================================="
echo ""

# Verify the fix
echo "Checking for broken code..."

# Check for wait loop
if grep -q "for _ in range(10):" order_executor.py; then
    echo "❌ ERROR: Wait loop still exists!"
    echo "Restoring backup..."
    cp "$BACKUP_FILE" order_executor.py
    exit 1
else
    echo "✅ Wait loop removed"
fi

# Check for get_order
if grep -q "self.alpaca.get_order" order_executor.py; then
    echo "❌ ERROR: get_order() call still exists!"
    echo "Restoring backup..."
    cp "$BACKUP_FILE" order_executor.py
    exit 1
else
    echo "✅ No get_order() calls"
fi

# Check for critical code
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
echo "1. Restart the bot:    systemctl restart rsi-trading-bot"
echo "2. Monitor logs:       journalctl -u rsi-trading-bot -f"
echo ""
echo "Backup saved at: $BACKUP_FILE"
