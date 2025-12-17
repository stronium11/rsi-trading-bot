#!/bin/bash
echo "Looking for all .db files..."
find ~/trading_bot -name "*.db" -type f 2>/dev/null
find ~ -name "trading_bot.db" -type f 2>/dev/null
echo ""
echo "Checking database locations in code..."
grep -r "db_path\|\.db" ~/trading_bot/rsi_trading_bot/database.py | head -5
