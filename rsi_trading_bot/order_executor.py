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
        4. If all Alpaca orders succeed: save to database
        5. If any order fails: cancel all orders, mark signal failed

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

            # STEP 1: Place bracket order (entry + stop loss together)
            # This prevents wash trade errors on SHORT positions
            bracket_order = self.alpaca.place_bracket_order_with_stop(
                symbol=ticker,
                direction=direction,
                position_size=self.position_size,
                stop_loss_pct=self.initial_stop_pct
            )

            if not bracket_order:
                raise Exception(f"Failed to place bracket order for {ticker}")

            alpaca_orders.append(bracket_order['order_id'])

            # Extract order details
            order_id = bracket_order['order_id']
            filled_price = bracket_order['price']
            quantity = bracket_order['qty']
            stop_price = bracket_order['stop_price']

            print(f"✅ Bracket order placed: {quantity:.4f} shares @ ${filled_price:.2f}")
            print(f"   Stop loss: ${stop_price:.2f}")

            # STEP 2: Calculate take profit targets
            if direction == 'LONG':
                # LONG: profit when price goes up
                t1_price = round(filled_price * 1.15, 2)  # +15%
                t2_price = round(filled_price * 1.18, 2)  # +18%
            else:
                # SHORT: profit when price goes down
                t1_price = round(filled_price * 0.85, 2)  # -15%
                t2_price = round(filled_price * 0.82, 2)  # -18%

            # Calculate quantities for take profit orders
            t1_qty = quantity * 0.70  # 70% of position
            t2_qty = quantity * 0.15  # 15% of position
            # Remaining 15% runs for T3 (+50%) - no order needed

            # STEP 3: Place T1 take profit order
            t1_order = self.alpaca.place_take_profit_order(
                symbol=ticker,
                direction=direction,
                target_price=t1_price,
                qty=t1_qty
            )

            if not t1_order:
                raise Exception(f"Failed to place T1 take profit for {ticker}")

            alpaca_orders.append(t1_order['order_id'])
            print(f"✅ T1 take profit: ${t1_price:.2f} (70% of position)")

            # STEP 4: Place T2 take profit order
            t2_order = self.alpaca.place_take_profit_order(
                symbol=ticker,
                direction=direction,
                target_price=t2_price,
                qty=t2_qty
            )

            if not t2_order:
                raise Exception(f"Failed to place T2 take profit for {ticker}")

            alpaca_orders.append(t2_order['order_id'])
            print(f"✅ T2 take profit: ${t2_price:.2f} (15% of position)")

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

            # Save T1 take profit order
            self.db.add_order(
                signal_id=signal_id,
                alpaca_order_id=t1_order['order_id'],
                ticker=ticker,
                order_type='limit',
                side='sell' if direction == 'LONG' else 'buy',
                quantity=t1_qty,
                price=t1_price
            )

            # Save T2 take profit order
            self.db.add_order(
                signal_id=signal_id,
                alpaca_order_id=t2_order['order_id'],
                ticker=ticker,
                order_type='limit',
                side='sell' if direction == 'LONG' else 'buy',
                quantity=t2_qty,
                price=t2_price
            )

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

            # STEP 6: Send notifications
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
                    f"🛡️ Stop: ${stop_price:.2f} (-{self.initial_stop_pct}%)\n"
                    f"🎯 T1: ${t1_price:.2f} (+15%, 70%)\n"
                    f"🎯 T2: ${t2_price:.2f} (+18%, 15%)\n"
                    f"🚀 T3: Running (15% for +50%)"
                )
            else:
                profit_msg = (
                    f"🛡️ Stop: ${stop_price:.2f} (+{self.initial_stop_pct}%)\n"
                    f"🎯 T1: ${t1_price:.2f} (-15%, 70%)\n"
                    f"🎯 T2: ${t2_price:.2f} (-18%, 15%)\n"
                    f"🚀 T3: Running (15% for -50%)"
                )

            await self.telegram.send_message(profit_msg)

            print(f"✅ Position fully configured with stop loss and take profit orders")
            print(f"   Remaining 15% will run for T3 target (+50%)")

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

            # Check risk limits
            limits = self.check_risk_limits()
            if not limits['can_trade']:
                reasons = []
                if not limits['max_positions_ok']:
                    reasons.append(f"Max positions ({self.max_positions}) reached")
                if not limits['daily_trades_ok']:
                    reasons.append(f"Daily trade limit ({self.max_daily_trades}) reached")
                if not limits['daily_loss_ok']:
                    reasons.append(f"Daily loss limit (${self.daily_loss_limit}) hit")

                msg = f"⚠️ Risk limits exceeded:\n" + "\n".join(f"• {r}" for r in reasons)
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
            for signal in pending_signals:
                # Check if we can still trade
                limits = self.check_risk_limits()
                if not limits['can_trade']:
                    print(f"\nRisk limits reached. Skipping remaining signals.")
                    self.db.update_signal_status(
                        signal['id'],
                        'skipped',
                        notes='Risk limits reached'
                    )
                    stats['skipped'] += 1
                    continue

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
