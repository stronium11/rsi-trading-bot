"""
Position Manager Module
Monitors open positions and manages profit targets and stop losses
Runs every 5 minutes during market hours
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from alpaca_client import get_alpaca_client
from database import get_database
from telegram_bot import get_bot
from config import Config


class PositionManager:
    """
    Manages open positions:
    - Monitors profit targets (T1: +15%, T2: +18%, T3: +50%)
    - Executes partial exits (70%, 15%, 15%)
    - Adjusts stop losses (breakeven after T1, +5% after T2)
    - Tracks maximum hold period (120 days)
    """

    def __init__(self):
        """Initialize the position manager"""
        self.alpaca = get_alpaca_client()
        self.db = get_database()
        self.telegram = get_bot()

        # Trading configuration
        self.target1_pct = Config.TARGET1_PCT
        self.target1_size = Config.TARGET1_SIZE
        self.target2_pct = Config.TARGET2_PCT
        self.target2_size = Config.TARGET2_SIZE
        self.target3_pct = Config.TARGET3_PCT
        self.target3_size = Config.TARGET3_SIZE
        self.breakeven_trigger_pct = Config.BREAKEVEN_TRIGGER_PCT
        self.max_hold_days = Config.MAX_HOLD_DAYS

    def calculate_pnl(self, entry_price: float, current_price: float,
                      quantity: float, direction: str) -> Dict[str, float]:
        """
        Calculate P&L for a position

        Parameters:
        - entry_price: Entry price
        - current_price: Current price
        - quantity: Position size
        - direction: 'LONG' or 'SHORT'

        Returns:
        - Dictionary with P&L metrics
        """
        if direction == 'LONG':
            price_change = current_price - entry_price
        else:  # SHORT
            price_change = entry_price - current_price

        gross_pnl = price_change * quantity
        return_pct = (price_change / entry_price) * 100

        return {
            'gross_pnl': gross_pnl,
            'net_pnl': gross_pnl,  # No commissions with Alpaca
            'return_pct': return_pct
        }

    def check_target_hit(self, entry_price: float, current_price: float,
                         target_pct: float, direction: str) -> bool:
        """
        Check if a profit target has been hit

        Parameters:
        - entry_price: Entry price
        - current_price: Current market price
        - target_pct: Target profit percentage
        - direction: 'LONG' or 'SHORT'

        Returns:
        - True if target hit, False otherwise
        """
        if direction == 'LONG':
            target_price = entry_price * (1 + target_pct / 100)
            return current_price >= target_price
        else:  # SHORT
            target_price = entry_price * (1 - target_pct / 100)
            return current_price <= target_price

    def calculate_new_stop(self, entry_price: float, trigger_type: str,
                           direction: str) -> float:
        """
        Calculate new stop loss after target hit

        Parameters:
        - entry_price: Original entry price
        - trigger_type: 'breakeven' or 'plus5'
        - direction: 'LONG' or 'SHORT'

        Returns:
        - New stop price
        """
        if trigger_type == 'breakeven':
            return entry_price

        elif trigger_type == 'plus5':
            if direction == 'LONG':
                return entry_price * (1 + 5 / 100)
            else:  # SHORT
                return entry_price * (1 - 5 / 100)

        return entry_price

    async def execute_partial_exit(self, position: Dict, exit_pct: float,
                                   target_name: str, current_price: float) -> bool:
        """
        Execute a partial exit of a position

        Parameters:
        - position: Position dictionary from database
        - exit_pct: Percentage of position to close (e.g., 70 for 70%)
        - target_name: Name of target ('T1', 'T2', 'T3')
        - current_price: Current market price

        Returns:
        - True if exit successful, False otherwise
        """
        try:
            ticker = position['ticker']
            direction = position['direction']
            remaining_qty = position['remaining_quantity']
            position_id = position['id']

            # Calculate quantity to exit
            exit_qty = remaining_qty * (exit_pct / 100)

            print(f"\n{target_name} hit for {ticker}: Exiting {exit_pct}% ({exit_qty:.4f} shares)")

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

        except Exception as e:
            error_msg = f"Error executing partial exit for {ticker}: {str(e)}"
            print(f"❌ {error_msg}")
            await self.telegram.send_message(f"❌ {error_msg}")
            return False

    async def close_entire_position(self, position: Dict, reason: str, current_price: float):
        """
        Close entire position (for stop loss or max hold period)

        Parameters:
        - position: Position dictionary from database
        - reason: Exit reason ('stop_loss' or 'max_hold')
        - current_price: Current market price
        """
        try:
            ticker = position['ticker']
            direction = position['direction']
            remaining_qty = position['remaining_quantity']
            position_id = position['id']

            print(f"\n{reason.upper()}: Closing entire position for {ticker}")

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

        except Exception as e:
            error_msg = f"Error closing position for {ticker}: {str(e)}"
            print(f"❌ {error_msg}")
            await self.telegram.send_message(f"❌ {error_msg}")

    async def manage_position(self, position: Dict):
        """
        Manage a single open position

        Parameters:
        - position: Position dictionary from database
        """
        try:
            ticker = position['ticker']
            direction = position['direction']
            entry_price = position['entry_price']
            remaining_qty = position['remaining_quantity']
            t1_executed = position['t1_executed']
            t2_executed = position['t2_executed']
            opened_at = position['opened_at']

            # Get current price from Alpaca position (more reliable than bars)
            alpaca_position = self.alpaca.get_position(ticker)
            if not alpaca_position:
                print(f"Could not get position for {ticker} from Alpaca")
                return

            current_price = alpaca_position['current_price']

            # Check max hold period
            days_held = (datetime.now() - datetime.strptime(opened_at, '%Y-%m-%d %H:%M:%S')).days
            if days_held >= self.max_hold_days:
                print(f"{ticker}: Max hold period ({self.max_hold_days} days) reached")
                await self.close_entire_position(position, 'max_hold', current_price)
                return

            # Check Target 3 (+50%)
            if self.check_target_hit(entry_price, current_price, self.target3_pct, direction):
                print(f"{ticker}: T3 (+{self.target3_pct}%) hit!")
                await self.execute_partial_exit(position, self.target3_size, 'T3', current_price)

                # If this was the last 15%, close the position
                if remaining_qty * (self.target3_size / 100) >= remaining_qty * 0.9:
                    self.db.close_position(position['id'])
                return

            # Check Target 2 (+18%)
            if not t2_executed and self.check_target_hit(entry_price, current_price, self.target2_pct, direction):
                print(f"{ticker}: T2 (+{self.target2_pct}%) hit!")
                success = await self.execute_partial_exit(position, self.target2_size, 'T2', current_price)

                if success:
                    # Adjust stop to +5%
                    new_stop = self.calculate_new_stop(entry_price, 'plus5', direction)
                    self.db.update_position_stop(position['id'], new_stop)
                    print(f"   Stop adjusted to +5%: ${new_stop:.2f}")
                    await self.telegram.send_message(
                        f"🛡️ Stop loss adjusted to +5%: ${new_stop:.2f}"
                    )
                return

            # Check Target 1 (+15%)
            if not t1_executed and self.check_target_hit(entry_price, current_price, self.target1_pct, direction):
                print(f"{ticker}: T1 (+{self.target1_pct}%) hit!")
                success = await self.execute_partial_exit(position, self.target1_size, 'T1', current_price)

                if success:
                    # Move stop to breakeven
                    new_stop = entry_price
                    self.db.update_position_stop(position['id'], new_stop)
                    print(f"   Stop moved to breakeven: ${new_stop:.2f}")
                    await self.telegram.send_message(
                        f"🛡️ Stop loss moved to breakeven: ${new_stop:.2f}"
                    )
                return

        except Exception as e:
            print(f"Error managing position for {position['ticker']}: {str(e)}")

    async def monitor_positions(self):
        """
        Monitor all open positions
        Called every 5 minutes during market hours
        """
        try:
            # Check if market is open
            market_hours = self.alpaca.get_market_hours()
            if not market_hours or not market_hours['is_open']:
                return

            # Get all open positions
            positions = self.db.get_open_positions()

            if len(positions) == 0:
                return

            print(f"\n{'='*70}")
            print(f"POSITION MANAGER - Monitoring {len(positions)} positions")
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}")
            print(f"{'='*70}")

            # Manage each position
            for position in positions:
                await self.manage_position(position)

        except Exception as e:
            error_msg = f"Error monitoring positions: {str(e)}"
            print(f"❌ {error_msg}")
            await self.telegram.send_message(f"❌ {error_msg}")

    async def run_position_monitoring(self):
        """
        Main method called by scheduler every 5 minutes
        """
        try:
            await self.monitor_positions()
        except Exception as e:
            print(f"Error in position monitoring: {str(e)}")
            raise


def get_position_manager() -> PositionManager:
    """Get the position manager instance"""
    return PositionManager()


# For testing
if __name__ == "__main__":
    import asyncio

    async def test_monitoring():
        manager = get_position_manager()
        await manager.run_position_monitoring()

    asyncio.run(test_monitoring())
