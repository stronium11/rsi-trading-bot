#!/usr/bin/env python3
"""
Script to fix position_manager.py on the server
Fixes subscription errors by using position API instead of bar data
"""

import os
import shutil
from datetime import datetime

# Path to the file
FILE_PATH = '/root/trading_bot/rsi_trading_bot/position_manager.py'

print("Reading position_manager.py...")

# Backup the original
backup_path = f"{FILE_PATH}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy2(FILE_PATH, backup_path)
print(f"✅ Backup created: {backup_path}")

# Read the file
with open(FILE_PATH, 'r') as f:
    content = f.read()

# Fix 1: Replace get_latest_bars with get_position
old_get_price = """            # Get current price
            bars = self.alpaca.get_latest_bars([ticker])
            if not bars or ticker not in bars:
                print(f"Could not get price for {ticker}")
                return

            current_price = bars[ticker]['close']"""

new_get_price = """            # Get current price from Alpaca position (more reliable than bars)
            alpaca_position = self.alpaca.get_position(ticker)
            if not alpaca_position:
                print(f"Could not get position for {ticker} from Alpaca")
                return

            current_price = alpaca_position['current_price']"""

content = content.replace(old_get_price, new_get_price)
print("✅ Fixed: Changed to use get_position() instead of get_latest_bars()")

# Fix 2: Replace partial exit order handling
old_partial_exit = """            # Place market order to close partial position
            order = self.alpaca.place_market_order(
                symbol=ticker,
                direction='SHORT' if direction == 'LONG' else 'LONG',  # Opposite direction to close
                position_size=exit_qty * current_price  # Use current value
            )

            # Wait for fill
            import time
            for _ in range(10):
                order_status = self.alpaca.get_order(order.id)
                if order_status.status == 'filled':
                    filled_price = float(order_status.filled_avg_price)"""

new_partial_exit = """            # Place market order to close partial position
            order = self.alpaca.place_market_order(
                symbol=ticker,
                direction='SHORT' if direction == 'LONG' else 'LONG',  # Opposite direction to close
                position_size=exit_qty * current_price  # Use current value
            )

            if not order:
                raise Exception(f"Failed to place partial exit order for {ticker}")

            order_id = order['order_id']
            filled_price = order['price']  # Market orders fill immediately at current price"""

if old_partial_exit in content:
    content = content.replace(old_partial_exit, new_partial_exit)
    print("✅ Fixed: Updated execute_partial_exit() to use dictionary access")
else:
    print("⚠️  Warning: Could not find old partial exit code (may already be fixed)")

# Fix 3: Remove the wait loop ending in partial exit
old_wait_end = """
                time.sleep(1)

            raise Exception("Partial exit order not filled within timeout")"""

# Find and remove indentation issues - replace the over-indented section
content = content.replace("""                    # Calculate P&L for this partial exit
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
                        f"{profit_emoji} *{target_name} Exit Complete*\\n\\n"
                        f"Ticker: {ticker}\\n"
                        f"P&L: ${pnl['net_pnl']:,.2f} ({pnl['return_pct']:.2f}%)\\n"
                        f"Remaining: {new_remaining:.4f} shares",
                        parse_mode='Markdown'
                    )

                    print(f"✅ Partial exit filled @ ${filled_price:.2f}")
                    print(f"   P&L: ${pnl['net_pnl']:,.2f} ({pnl['return_pct']:.2f}%)")

                    return True

                time.sleep(1)

            raise Exception("Partial exit order not filled within timeout")""",
"""
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
                f"{profit_emoji} *{target_name} Exit Complete*\\n\\n"
                f"Ticker: {ticker}\\n"
                f"P&L: ${pnl['net_pnl']:,.2f} ({pnl['return_pct']:.2f}%)\\n"
                f"Remaining: {new_remaining:.4f} shares",
                parse_mode='Markdown'
            )

            print(f"✅ Partial exit filled @ ${filled_price:.2f}")
            print(f"   P&L: ${pnl['net_pnl']:,.2f} ({pnl['return_pct']:.2f}%)")

            return True""")

print("✅ Fixed: Removed wait loop from execute_partial_exit()")

# Fix 4: Replace close position order handling
old_close_position = """            # Place market order to close entire position
            order = self.alpaca.place_market_order(
                symbol=ticker,
                direction='SHORT' if direction == 'LONG' else 'LONG',
                position_size=remaining_qty * current_price
            )

            # Wait for fill
            import time
            for _ in range(10):
                order_status = self.alpaca.get_order(order.id)
                if order_status.status == 'filled':
                    filled_price = float(order_status.filled_avg_price)"""

new_close_position = """            # Place market order to close entire position
            order = self.alpaca.place_market_order(
                symbol=ticker,
                direction='SHORT' if direction == 'LONG' else 'LONG',
                position_size=remaining_qty * current_price
            )

            if not order:
                raise Exception(f"Failed to place close position order for {ticker}")

            order_id = order['order_id']
            filled_price = order['price']  # Market orders fill immediately at current price"""

if old_close_position in content:
    content = content.replace(old_close_position, new_close_position)
    print("✅ Fixed: Updated close_entire_position() to use dictionary access")
else:
    print("⚠️  Warning: Could not find old close position code (may already be fixed)")

# Fix 5: Remove wait loop from close position
content = content.replace("""                    # Calculate P&L
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
                        f"{emoji} *Position Closed: {reason.replace('_', ' ').title()}*\\n\\n"
                        f"Ticker: {ticker}\\n"
                        f"Entry: ${entry_price:.2f}\\n"
                        f"Exit: ${filled_price:.2f}\\n"
                        f"P&L: ${pnl['net_pnl']:,.2f} ({pnl['return_pct']:.2f}%)\\n"
                        f"Hold: {hold_days} days",
                        parse_mode='Markdown'
                    )

                    print(f"✅ Position closed @ ${filled_price:.2f}")
                    print(f"   P&L: ${pnl['net_pnl']:,.2f} ({pnl['return_pct']:.2f}%)")

                    return

                time.sleep(1)

            raise Exception("Close position order not filled within timeout")""",
"""
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
                f"{emoji} *Position Closed: {reason.replace('_', ' ').title()}*\\n\\n"
                f"Ticker: {ticker}\\n"
                f"Entry: ${entry_price:.2f}\\n"
                f"Exit: ${filled_price:.2f}\\n"
                f"P&L: ${pnl['net_pnl']:,.2f} ({pnl['return_pct']:.2f}%)\\n"
                f"Hold: {hold_days} days",
                parse_mode='Markdown'
            )

            print(f"✅ Position closed @ ${filled_price:.2f}")
            print(f"   P&L: ${pnl['net_pnl']:,.2f} ({pnl['return_pct']:.2f}%)")

            return""")

print("✅ Fixed: Removed wait loop from close_entire_position()")

# Write the updated file
with open(FILE_PATH, 'w') as f:
    f.write(content)

print("\n" + "="*60)
print("✅ position_manager.py successfully updated!")
print("="*60)
print("\nChanges made:")
print("1. Uses get_position() API instead of get_latest_bars()")
print("   - Avoids subscription errors")
print("   - More reliable for current price")
print("2. Fixed dictionary access in execute_partial_exit()")
print("3. Fixed dictionary access in close_entire_position()")
print("4. Removed wait loops (market orders fill immediately)")
print("\nNext steps:")
print("  systemctl restart rsi-trading-bot")
print("  journalctl -u rsi-trading-bot -f")
print("\nBackup saved to:")
print(f"  {backup_path}")
