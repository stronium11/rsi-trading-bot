#!/bin/bash
# Quick deployment script - Run this ON YOUR SERVER via SSH
# Usage: ssh root@YOUR_SERVER_IP 'bash -s' < DEPLOY_NOW.sh

set -e  # Exit on any error

echo "=========================================="
echo "🚀 DEPLOYING ORDER EXECUTOR FIX"
echo "=========================================="
echo ""

# Navigate to bot directory
cd /root/trading_bot/rsi_trading_bot || {
    echo "❌ Error: Bot directory not found at /root/trading_bot/rsi_trading_bot"
    exit 1
}

echo "📂 Working directory: $(pwd)"
echo ""

# Create backup
BACKUP_FILE="order_executor.py.backup.$(date +%Y%m%d_%H%M%S)"
cp order_executor.py "$BACKUP_FILE"
echo "✅ Backup created: $BACKUP_FILE"
echo ""

# Pull the fix from git
echo "📥 Pulling latest changes from git..."
git fetch origin claude/rsi-signal-system-016Ch1qMCkuLd6m8X8ZRb9ap
git checkout claude/rsi-signal-system-016Ch1qMCkuLd6m8X8ZRb9ap
git pull origin claude/rsi-signal-system-016Ch1qMCkuLd6m8X8ZRb9ap

if [ $? -ne 0 ]; then
    echo "❌ Git pull failed!"
    exit 1
fi

echo "✅ Git pull successful"
echo ""

# Verify the fix
echo "🔍 Verifying fix..."
echo ""

# Check for broken wait loop
if grep -q "for _ in range(10):" order_executor.py; then
    echo "❌ ERROR: Broken wait loop still exists!"
    echo "   Restoring backup..."
    cp "$BACKUP_FILE" order_executor.py
    exit 1
fi
echo "✅ No wait loop (good)"

# Check for broken get_order call
if grep -q "self.alpaca.get_order(" order_executor.py; then
    echo "❌ ERROR: Broken get_order() call still exists!"
    echo "   Restoring backup..."
    cp "$BACKUP_FILE" order_executor.py
    exit 1
fi
echo "✅ No get_order() calls (good)"

# Check for stop loss code
if ! grep -q "place_stop_loss_order" order_executor.py; then
    echo "❌ ERROR: Missing stop loss code!"
    echo "   Restoring backup..."
    cp "$BACKUP_FILE" order_executor.py
    exit 1
fi
echo "✅ Stop loss code present"

# Check for position creation
if ! grep -q "add_position" order_executor.py; then
    echo "❌ ERROR: Missing position creation code!"
    echo "   Restoring backup..."
    cp "$BACKUP_FILE" order_executor.py
    exit 1
fi
echo "✅ Position creation code present"

echo ""
echo "=========================================="
echo "✅ VERIFICATION PASSED"
echo "=========================================="
echo ""

# Restart the bot
echo "🔄 Restarting trading bot..."
systemctl restart rsi-trading-bot

if [ $? -ne 0 ]; then
    echo "❌ Failed to restart bot!"
    exit 1
fi

echo "✅ Bot restarted successfully"
echo ""

# Wait a moment for startup
sleep 2

# Show recent logs
echo "=========================================="
echo "📋 RECENT LOGS (last 20 lines):"
echo "=========================================="
journalctl -u rsi-trading-bot -n 20 --no-pager

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Monitor logs: journalctl -u rsi-trading-bot -f"
echo "2. Check for clean startup (no errors)"
echo "3. Verify position monitoring works"
echo ""
echo "Backup saved: $BACKUP_FILE"
echo ""
