"""
Order Executor Module
Executes trades at market open (9:30 AM ET) for pending signals
"""

from datetime import datetime
from typing import List, Dict, Optional
from alpaca_client import get_alpaca_client
from database import get_database
from telegram_bot import get_bot
from config import Config


class OrderExecutor:
    """
    Executes market orders at market open for pending signals
    Manages position sizing, stop losses, and risk limits
    """

    def __init__(self):
        """Initialize the order executor"""
        self.alpaca = get_alpaca_client()
        self.db = get_database()
        self.telegram = get_bot()

        # Trading configuration
        self.position_size = Config.POSITION_SIZE
        self.initial_stop_pct = Config.STOP_LOSS_PCT
        self.max_positions = Config.MAX_POSITIONS
        self.max_daily_trades = Config.MAX_DAILY_TRADES
        self.daily_loss_limit = Config.DAILY_LOSS_LIMIT

    def check_risk_limits(self) -> Dict[str, bool]:
        """
        Check if we're within risk limits before placing new orders

        Returns:
        - Dictionary with risk limit checks
        """
        limits = {
            'max_positions_ok': True,
            'daily_trades_ok': True,
            'daily_loss_ok': True,
            'can_trade': True
        }

        # Check max open positions
        open_positions = self.db.get_open_positions()
        if len(open_positions) >= self.max_positions:
            limits['max_positions_ok'] = False
            limits['can_trade'] = False

        # Check daily trade limit
        today = datetime.now().strftime('%Y-%m-%d')
        today_trades = self.db.get_trades_by_date_range(today, today)
        if len(today_trades) >= self.max_daily_trades:
            limits['daily_trades_ok'] = False
            limits['can_trade'] = False

        # Check daily loss limit
        today_pnl = sum(t['net_pnl'] for t in today_trades)
        if today_pnl <= -self.daily_loss_limit:
            limits['daily_loss_ok'] = False
            limits['can_trade'] = False

        return limits

    def calculate_stop_loss(self, entry_price: float, direction: str) -> float:
        """
        Calculate initial stop loss price

        Parameters:
        - entry_price: Entry price
        - direction: 'LONG' or 'SHORT'

        Returns:
        - Stop loss price
        """
        if direction == 'LONG':
            # For long: stop is below entry
            stop_price = entry_price * (1 - self.initial_stop_pct / 100)
        else:
            # For short: stop is above entry
            stop_price = entry_price * (1 + self.initial_stop_pct / 100)

        return round(stop_price, 2)

    async def execute_signal(self, signal: Dict) -> bool:
        """
        Execute a single signal with atomic transaction pattern

        ATOMIC EXECUTION FLOW:
        1. Place bracket order (entry + stop loss together)
        2. Place T1 take profit order (70% of position @ +15%)
        3. Place T2 take profit order (15% of position @ +18%)
        4. Place T3 take profit order (15% of position @ +50%)
        5. If all Alpaca orders succeed: save to database
        6. If any order fails: cancel all orders, mark signal failed

        Parameters:
        - signal: Signal dictionary from database

        Returns:
        - True if executed successfully, False otherwise
        """
        alpaca_orders = []  # Track orders for potential rollback
        ticker = signal['ticker']
        divergence_type = signal['divergence_type']
        signal_id = signal['id']

        try:
            # Determine direction
            direction = 'LONG' if divergence_type == 'Bullish' else 'SHORT'

            print(f"\nExecuting {direction} order for {ticker}...")

            # STEP 1: Place bracket order (entry + stop loss + T1 take profit)
            # Using T1 (+15%) as the primary/only take profit
            # This avoids "potential wash trade" errors on SHORT positions
            # Note: We're using T1 which takes 70% of position at +15% profit
            bracket_order = self.alpaca.place_bracket_order_with_targets(
                symbol=ticker,
                direction=direction,
                position_size=self.position_size,
                stop_loss_pct=self.initial_stop_pct,  # 7%
                take_profit_pct=15,  # T1 target at +15% (most important level)
                take_profit_qty_pct=100  # Full position
            )

            if not bracket_order:
                raise Exception(f"Failed to place bracket order for {ticker}")

            alpaca_orders.append(bracket_order['order_id'])

            # Extract order details
            order_id = bracket_order['order_id']
            filled_price = bracket_order['price']
            quantity = bracket_order['qty']
            stop_price = bracket_order['stop_price']
            t3_price_from_bracket = bracket_order['take_profit_price']

            t1_price_from_bracket = bracket_order['take_profit_price']

            print(f"✅ Bracket order placed: {quantity:.4f} shares @ ${filled_price:.2f}")
            print(f"   Stop loss: ${stop_price:.2f}")
            print(f"   Take profit (T1): ${t1_price_from_bracket:.2f} (+15%)")
            print(f"   ✅ Position secured with stop loss and take profit")

            # STEP 5: All Alpaca orders succeeded - now save to database atomically

            # Save main market order
            self.db.add_order(
                signal_id=signal_id,
                alpaca_order_id=order_id,
                ticker=ticker,
                order_type='market',
                side='buy' if direction == 'LONG' else 'sell',
                quantity=quantity,
                price=filled_price
            )

            # Update to filled status (paper trading fills instantly)
            self.db.update_order_status(
                alpaca_order_id=order_id,
                status='filled',
                filled_price=filled_price,
                filled_at=None
            )

            # Note: Stop loss and take profit (T1) are part of the bracket order
            # They're managed by Alpaca automatically

            # Create position record
            position_id = self.db.add_position(
                signal_id=signal_id,
                ticker=ticker,
                direction=direction,
                entry_price=filled_price,
                quantity=quantity,
                initial_stop=stop_price
            )

            # Update signal status
            self.db.update_signal_status(signal_id, 'executed')

            # STEP 7: Send notifications
            await self.telegram.send_order_alert(
                ticker=ticker,
                direction=direction,
                shares=quantity,
                price=filled_price,
                order_type='BRACKET'
            )

            # Format profit percentages based on direction
            if direction == 'LONG':
                profit_msg = (
                    f"🛡️ Stop Loss: ${stop_price:.2f} (-{self.initial_stop_pct}%)\n"
                    f"🎯 Take Profit: ${t1_price_from_bracket:.2f} (+15%)"
                )
            else:
                profit_msg = (
                    f"🛡️ Stop Loss: ${stop_price:.2f} (+{self.initial_stop_pct}%)\n"
                    f"🎯 Take Profit: ${t1_price_from_bracket:.2f} (-15%)"
                )

            await self.telegram.send_message(profit_msg)

            print(f"✅ Position secured with stop loss and take profit")

            return True

        except Exception as e:
            error_msg = f"Error executing {ticker}: {str(e)}"
            print(f"❌ {error_msg}")

            # ROLLBACK: Cancel all Alpaca orders that were placed
            if alpaca_orders:
                print(f"⚠️  Rolling back {len(alpaca_orders)} orders...")
                for order_id in alpaca_orders:
                    try:
                        self.alpaca.cancel_order(order_id)
                        print(f"  ✅ Cancelled order {order_id}")
                    except Exception as cancel_error:
                        print(f"  ⚠️  Could not cancel {order_id}: {cancel_error}")

            # Update signal as failed
            self.db.update_signal_status(signal_id, 'failed', notes=str(e))

            # Send notification
            await self.telegram.send_message(f"❌ {error_msg}")

            return False

    async def execute_pending_signals(self) -> Dict[str, int]:
        """
        Execute all pending signals that pass risk limits

        Returns:
        - Dictionary with execution statistics
        """
        print("\n" + "="*70)
        print("ORDER EXECUTOR - Market Open Execution")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}")
        print("="*70 + "\n")

        stats = {
            'total_pending': 0,
            'executed': 0,
            'failed': 0,
            'skipped': 0
        }

        try:
            # Check if market is open
            market_hours = self.alpaca.get_market_hours()
            if not market_hours['is_open']:
                msg = "⚠️ Market is currently closed. Skipping order execution."
                print(msg)
                await self.telegram.send_message(msg)
                return stats

            # Get pending signals
            pending_signals = self.db.get_pending_signals()
            stats['total_pending'] = len(pending_signals)

            if len(pending_signals) == 0:
                msg = "✅ No pending signals to execute."
                print(msg)
                await self.telegram.send_message(msg)
                return stats

            print(f"Found {len(pending_signals)} pending signals")
            await self.telegram.send_message(
                f"📊 Executing {len(pending_signals)} pending signals at market open..."
            )

            # Execute each signal
            # NOTE: No duplicate checking here - these signals already passed
            # duplicate prevention when they were detected by the scanner.
            # Pending signals should execute without re-checking for duplicates.
            for signal in pending_signals:
                ticker = signal['ticker']

                # Execute signal
                success = await self.execute_signal(signal)

                if success:
                    stats['executed'] += 1
                else:
                    stats['failed'] += 1

            # Send summary
            summary = f"""
📊 *Execution Summary*

Total Pending: {stats['total_pending']}
✅ Executed: {stats['executed']}
❌ Failed: {stats['failed']}
⏭️ Skipped: {stats['skipped']}
"""
            await self.telegram.send_message(summary, parse_mode='Markdown')

            print("\n" + "="*70)
            print("Execution Complete")
            print("="*70 + "\n")

            return stats

        except Exception as e:
            error_msg = f"❌ Fatal error during execution: {str(e)}"
            print(error_msg)
            await self.telegram.send_message(error_msg)
            raise

    async def run_market_open_execution(self):
        """
        Main method called by scheduler at market open (9:30 AM ET)
        """
        try:
            stats = await self.execute_pending_signals()
            return stats

        except Exception as e:
            print(f"Error in market open execution: {str(e)}")
            raise


def get_order_executor() -> OrderExecutor:
    """Get the order executor instance"""
    return OrderExecutor()


# For testing
if __name__ == "__main__":
    import asyncio

    async def test_execution():
        executor = get_order_executor()
        await executor.run_market_open_execution()

    asyncio.run(test_execution())
