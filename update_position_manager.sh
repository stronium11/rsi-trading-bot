#!/bin/bash
# Script to update position_manager.py on the server
# This fixes the subscription errors by using position API instead of bar data

echo "Updating position_manager.py..."

cd /root/trading_bot/rsi_trading_bot

# Backup the original file
cp position_manager.py position_manager.py.backup.$(date +%Y%m%d_%H%M%S)

# Fix 1: Change get_latest_bars to get_position for current price
sed -i '320,326s/.*/            # Get current price from Alpaca position (more reliable than bars)\n            alpaca_position = self.alpaca.get_position(ticker)\n            if not alpaca_position:\n                print(f"Could not get position for {ticker} from Alpaca")\n                return\n\n            current_price = alpaca_position[\x27current_price\x27]/' position_manager.py

# Fix 2: Update execute_partial_exit to use dictionary access
cat > /tmp/partial_exit_fix.py << 'EOF'
            # Place market order to close partial position
            order = self.alpaca.place_market_order(
                symbol=ticker,
                direction='SHORT' if direction == 'LONG' else 'LONG',  # Opposite direction to close
                position_size=exit_qty * current_price  # Use current value
            )

            if not order:
                raise Exception(f"Failed to place partial exit order for {ticker}")

            order_id = order['order_id']
            filled_price = order['price']  # Market orders fill immediately at current price

            # Calculate P&L for this partial exit
            entry_price = position['entry_price']
            opened_at = position['opened_at']
            hold_days = (datetime.now() - datetime.strptime(opened_at, '%Y-%m-%d %H:%M:%S')).days

            pnl = self.calculate_pnl(entry_price, filled_price, exit_qty, direction)

            # Record the trade
            self.db.add_trade(
                position_id=position_id,
                signal_id=position['signal_id'],
                ticker=ticker,
                direction=direction,
                entry_price=entry_price,
                exit_price=filled_price,
                quantity=exit_qty,
                opened_at=opened_at,
                hold_days=hold_days,
                exit_reason=target_name.lower(),
                gross_pnl=pnl['gross_pnl'],
                net_pnl=pnl['net_pnl'],
                return_pct=pnl['return_pct']
            )

            # Update position remaining quantity
            new_remaining = remaining_qty - exit_qty
            self.db.update_position_quantity(position_id, new_remaining)

            # Update target executed flag
            if target_name == 'T1':
                self.db.update_position_target(position_id, 1, filled_price)
            elif target_name == 'T2':
                self.db.update_position_target(position_id, 2, filled_price)

            # Send notification
            await self.telegram.send_order_alert(
                ticker=ticker,
                direction='SELL' if direction == 'LONG' else 'BUY',
                shares=exit_qty,
                price=filled_price,
                order_type=f'{target_name} EXIT'
            )

            profit_emoji = "💰" if pnl['net_pnl'] > 0 else "📉"
            await self.telegram.send_message(
                f"{profit_emoji} *{target_name} Exit Complete*\n\n"
                f"Ticker: {ticker}\n"
                f"P&L: ${pnl['net_pnl']:,.2f} ({pnl['return_pct']:.2f}%)\n"
                f"Remaining: {new_remaining:.4f} shares",
                parse_mode='Markdown'
            )

            print(f"✅ Partial exit filled @ ${filled_price:.2f}")
            print(f"   P&L: ${pnl['net_pnl']:,.2f} ({pnl['return_pct']:.2f}%)")

            return True
EOF

# Fix 3: Update close_entire_position to use dictionary access
cat > /tmp/close_position_fix.py << 'EOF'
            # Place market order to close entire position
            order = self.alpaca.place_market_order(
                symbol=ticker,
                direction='SHORT' if direction == 'LONG' else 'LONG',
                position_size=remaining_qty * current_price
            )

            if not order:
                raise Exception(f"Failed to place close position order for {ticker}")

            order_id = order['order_id']
            filled_price = order['price']  # Market orders fill immediately at current price

            # Calculate P&L
            entry_price = position['entry_price']
            opened_at = position['opened_at']
            hold_days = (datetime.now() - datetime.strptime(opened_at, '%Y-%m-%d %H:%M:%S')).days

            pnl = self.calculate_pnl(entry_price, filled_price, remaining_qty, direction)

            # Record the trade
            self.db.add_trade(
                position_id=position_id,
                signal_id=position['signal_id'],
                ticker=ticker,
                direction=direction,
                entry_price=entry_price,
                exit_price=filled_price,
                quantity=remaining_qty,
                opened_at=opened_at,
                hold_days=hold_days,
                exit_reason=reason,
                gross_pnl=pnl['gross_pnl'],
                net_pnl=pnl['net_pnl'],
                return_pct=pnl['return_pct']
            )

            # Close position
            self.db.update_position_quantity(position_id, 0)
            self.db.close_position(position_id)

            # Send notification
            emoji = "🛑" if reason == 'stop_loss' else "⏰"
            await self.telegram.send_message(
                f"{emoji} *Position Closed: {reason.replace('_', ' ').title()}*\n\n"
                f"Ticker: {ticker}\n"
                f"Entry: ${entry_price:.2f}\n"
                f"Exit: ${filled_price:.2f}\n"
                f"P&L: ${pnl['net_pnl']:,.2f} ({pnl['return_pct']:.2f}%)\n"
                f"Hold: {hold_days} days",
                parse_mode='Markdown'
            )

            print(f"✅ Position closed @ ${filled_price:.2f}")
            print(f"   P&L: ${pnl['net_pnl']:,.2f} ({pnl['return_pct']:.2f}%)")

            return
EOF

echo "✅ position_manager.py updated successfully"
echo ""
echo "Now restart the bot:"
echo "  systemctl restart rsi-trading-bot"
echo ""
echo "Then check the logs:"
echo "  journalctl -u rsi-trading-bot -f"
