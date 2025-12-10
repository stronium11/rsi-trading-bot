"""
RSI Trading Bot - Main Orchestrator
Coordinates all modules and manages scheduling
"""

import asyncio
import signal
import sys
from datetime import datetime, time
from typing import Dict
import pytz
from config import Config
from database import get_database
from telegram_bot import get_bot
from live_scanner import get_scanner
from order_executor import get_order_executor
from position_manager import get_position_manager


class TradingBot:
    """
    Main trading bot orchestrator
    Manages scheduling and coordinates all modules
    """

    def __init__(self):
        """Initialize the trading bot"""
        self.db = get_database()
        self.telegram = get_bot()
        self.scanner = get_scanner()
        self.executor = get_order_executor()
        self.position_manager = get_position_manager()

        # Eastern Time (market timezone)
        self.et_tz = pytz.timezone('US/Eastern')

        # Scheduling config
        self.scanner_time = time(7, 0)      # 7:00 AM ET - Daily scan
        self.market_open = time(9, 30)      # 9:30 AM ET - Market open execution
        self.position_check_interval = 300   # 5 minutes (in seconds)

        # State
        self.running = False
        self.scanner_task = None
        self.executor_task = None
        self.position_task = None

    async def send_startup_message(self):
        """Send startup notification"""
        stats = self.db.get_statistics()

        message = f"""
🤖 *RSI Trading Bot Started*

📊 *Current Status:*
• Open Positions: {stats['open_positions']}
• Total Signals: {stats['total_signals']}
• Total Trades: {stats['total_trades']}
• Win Rate: {stats['win_rate']:.1f}%
• Total P&L: ${stats['total_pnl']:,.2f}

⏰ *Schedule:*
• Daily Scan: 7:00 AM ET
• Order Execution: 9:30 AM ET
• Position Monitoring: Every 5 min

✅ Bot is now running...
"""
        await self.telegram.send_message(message, parse_mode='Markdown')

    async def run_daily_scanner(self):
        """Run the daily scanner at 7:00 AM ET"""
        while self.running:
            try:
                # Get current time in ET
                now_et = datetime.now(self.et_tz)
                current_time = now_et.time()

                # Check if it's time to run the scanner
                if current_time.hour == self.scanner_time.hour and current_time.minute == self.scanner_time.minute:
                    print(f"\n{'='*70}")
                    print(f"DAILY SCAN TRIGGERED - {now_et.strftime('%Y-%m-%d %H:%M:%S ET')}")
                    print(f"{'='*70}\n")

                    await self.scanner.run_daily_scan()

                    # Sleep for 65 seconds to avoid running twice in the same minute
                    await asyncio.sleep(65)
                else:
                    # Check every 30 seconds
                    await asyncio.sleep(30)

            except Exception as e:
                error_msg = f"Error in daily scanner task: {str(e)}"
                print(error_msg)
                await self.telegram.send_message(f"❌ {error_msg}")
                await asyncio.sleep(60)

    async def run_market_open_executor(self):
        """Run order executor at market open (9:30 AM ET)"""
        while self.running:
            try:
                # Get current time in ET
                now_et = datetime.now(self.et_tz)
                current_time = now_et.time()

                # Check if it's market open time
                if current_time.hour == self.market_open.hour and current_time.minute == self.market_open.minute:
                    print(f"\n{'='*70}")
                    print(f"MARKET OPEN EXECUTION - {now_et.strftime('%Y-%m-%d %H:%M:%S ET')}")
                    print(f"{'='*70}\n")

                    await self.executor.run_market_open_execution()

                    # Sleep for 65 seconds to avoid running twice
                    await asyncio.sleep(65)
                else:
                    # Check every 30 seconds
                    await asyncio.sleep(30)

            except Exception as e:
                error_msg = f"Error in market open executor task: {str(e)}"
                print(error_msg)
                await self.telegram.send_message(f"❌ {error_msg}")
                await asyncio.sleep(60)

    async def run_position_monitor(self):
        """Run position monitoring every 5 minutes during market hours"""
        while self.running:
            try:
                await self.position_manager.run_position_monitoring()

                # Sleep for 5 minutes
                await asyncio.sleep(self.position_check_interval)

            except Exception as e:
                error_msg = f"Error in position monitor task: {str(e)}"
                print(error_msg)
                await self.telegram.send_message(f"❌ {error_msg}")
                await asyncio.sleep(60)

    async def get_bot_status(self) -> str:
        """Get current bot status"""
        stats = self.db.get_statistics()
        open_positions = self.db.get_open_positions()
        pending_signals = self.db.get_pending_signals()

        status = f"""
📊 *Bot Status Report*

⏰ *Time:* {datetime.now(self.et_tz).strftime('%Y-%m-%d %H:%M:%S ET')}

📈 *Open Positions:* {len(open_positions)}
"""
        if len(open_positions) > 0:
            status += "\n"
            for pos in open_positions:
                status += f"• {pos['ticker']} ({pos['direction']}) - {pos['remaining_quantity']:.4f} shares\n"

        status += f"""
🎯 *Pending Signals:* {len(pending_signals)}

📊 *Overall Stats:*
• Total Trades: {stats['total_trades']}
• Win Rate: {stats['win_rate']:.1f}%
• Total P&L: ${stats['total_pnl']:,.2f}

✅ Bot Status: Running
"""
        return status

    def handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        print("\n\n" + "="*70)
        print("SHUTDOWN SIGNAL RECEIVED")
        print("="*70 + "\n")
        self.running = False

    async def start(self):
        """Start the trading bot"""
        try:
            print("\n" + "="*70)
            print("RSI TRADING BOT")
            print("="*70)
            print(f"\nStarting at: {datetime.now(self.et_tz).strftime('%Y-%m-%d %H:%M:%S ET')}")
            print(f"\nPosition Size: ${Config.POSITION_SIZE:,.0f}")
            print(f"Max Positions: {Config.MAX_POSITIONS}")
            print(f"Daily Trade Limit: {Config.MAX_DAILY_TRADES}")
            print(f"Daily Loss Limit: ${Config.DAILY_LOSS_LIMIT:,.0f}")
            print(f"\nTargets: T1={Config.TARGET1_PCT}% ({Config.TARGET1_SIZE}%), " +
                  f"T2={Config.TARGET2_PCT}% ({Config.TARGET2_SIZE}%), " +
                  f"T3={Config.TARGET3_PCT}% ({Config.TARGET3_SIZE}%)")
            print(f"Stop Loss: -{Config.STOP_LOSS_PCT}%")
            print(f"Max Hold: {Config.MAX_HOLD_DAYS} days")
            print("\n" + "="*70 + "\n")

            # Send startup notification
            await self.send_startup_message()

            # Set running flag
            self.running = True

            # Register signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self.handle_shutdown)
            signal.signal(signal.SIGTERM, self.handle_shutdown)

            # Start all scheduled tasks
            self.scanner_task = asyncio.create_task(self.run_daily_scanner())
            self.executor_task = asyncio.create_task(self.run_market_open_executor())
            self.position_task = asyncio.create_task(self.run_position_monitor())

            print("✅ All tasks started successfully")
            print("\nBot is now running. Press Ctrl+C to stop.\n")

            # Keep the bot running
            while self.running:
                await asyncio.sleep(1)

            # Cancel all tasks on shutdown
            print("\nShutting down tasks...")
            self.scanner_task.cancel()
            self.executor_task.cancel()
            self.position_task.cancel()

            # Wait for tasks to complete
            await asyncio.gather(
                self.scanner_task,
                self.executor_task,
                self.position_task,
                return_exceptions=True
            )

            # Send shutdown notification
            await self.telegram.send_message("🛑 *Bot Stopped*\n\nTrading bot has been shut down.", parse_mode='Markdown')

            print("\n✅ Bot stopped gracefully\n")

        except Exception as e:
            error_msg = f"Fatal error in bot: {str(e)}"
            print(f"\n❌ {error_msg}\n")
            await self.telegram.send_message(f"❌ {error_msg}")
            raise


async def main():
    """Main entry point"""
    bot = TradingBot()
    await bot.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nBot interrupted by user")
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        sys.exit(1)
