"""
Telegram Bot for Trading Notifications and Commands
"""

import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import Config


class TradingTelegramBot:
    """Telegram bot for trade notifications and control"""

    def __init__(self):
        """Initialize Telegram bot"""
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.app = None
        self.trading_enabled = True

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_msg = """
🤖 *RSI Trading Bot Activated*

I'll notify you about:
• New divergence signals
• Orders placed
• Profit targets hit
• Stop loss adjustments
• Daily performance

*Commands:*
/status - System status
/positions - Current open positions
/pnl - Profit & Loss summary
/signals - Recent signals
/enable - Enable trading
/disable - Disable new trades
/stop - Emergency stop all trading
"""
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        status = "🟢 ACTIVE" if self.trading_enabled else "🔴 DISABLED"
        msg = f"""
📊 *System Status*

Trading: {status}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}

Configuration:
• Position Size: ${Config.POSITION_SIZE:,.0f}
• Max Positions: {Config.MAX_POSITIONS}
• Stop Loss: -{Config.STOP_LOSS_PCT}%
• T1: +{Config.TARGET1_PCT}% (close {Config.TARGET1_SIZE}%)
• T2: +{Config.TARGET2_PCT}% (close {Config.TARGET2_SIZE}%)
• T3: +{Config.TARGET3_PCT}% (close {Config.TARGET3_SIZE}%)
"""
        await update.message.reply_text(msg, parse_mode='Markdown')

    async def enable_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /enable command"""
        self.trading_enabled = True
        await update.message.reply_text("🟢 Trading ENABLED - Will take new signals")

    async def disable_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /disable command"""
        self.trading_enabled = False
        await update.message.reply_text("🟡 Trading DISABLED - No new trades (existing positions still managed)")

    async def emergency_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command - emergency stop"""
        self.trading_enabled = False
        await update.message.reply_text("🔴 EMERGENCY STOP - All trading halted. Existing positions remain open.")

    async def send_message(self, message: str, parse_mode: str = None):
        """Send message to configured chat"""
        if not self.app or not self.chat_id:
            print(f"[Telegram] {message}")
            return

        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
        except Exception as e:
            print(f"Error sending Telegram message: {e}")

    async def send_signal_alert(self, ticker: str, divergence_type: str, timeframe: str, entry_price: float):
        """Send alert for new signal detected"""
        direction = "📈 LONG" if divergence_type == "Bullish" else "📉 SHORT"
        msg = f"""
🎯 *NEW SIGNAL DETECTED*

{direction}
Ticker: {ticker}
Type: {divergence_type} Divergence
Timeframe: {timeframe}
Entry Price: ${entry_price:.2f}
Position: ${Config.POSITION_SIZE:,.0f}

Will execute at market open (9:30 AM ET)
"""
        await self.send_message(msg, parse_mode='Markdown')

    async def send_order_alert(self, ticker: str, direction: str, shares: float, price: float, order_type: str):
        """Send alert for order execution"""
        emoji = "📈" if direction == "LONG" else "📉"
        msg = f"""
{emoji} *ORDER EXECUTED*

{order_type}: {ticker}
Direction: {direction}
Shares: {shares:.4f}
Price: ${price:.2f}
Total: ${shares * price:,.2f}

Stop Loss: ${price * (0.93 if direction == 'LONG' else 1.07):.2f} (-7%)
"""
        await self.send_message(msg, parse_mode='Markdown')

    async def send_profit_target_alert(self, ticker: str, target: str, pct_gain: float, partial_close_pct: float, pnl: float):
        """Send alert for profit target hit"""
        msg = f"""
💰 *PROFIT TARGET HIT*

Ticker: {ticker}
Target: {target}
Gain: +{pct_gain:.1f}%
Closed: {partial_close_pct:.0f}% of position
P&L: ${pnl:,.2f}
"""
        await self.send_message(msg, parse_mode='Markdown')

    async def send_stop_adjustment_alert(self, ticker: str, new_stop: str):
        """Send alert for stop loss adjustment"""
        msg = f"""
🛡️ *STOP LOSS ADJUSTED*

Ticker: {ticker}
New Stop: {new_stop}
Position now risk-free!
"""
        await self.send_message(msg, parse_mode='Markdown')

    async def send_daily_summary(self, trades_today: int, pnl_today: float, open_positions: int):
        """Send daily performance summary"""
        pnl_emoji = "📈" if pnl_today >= 0 else "📉"
        msg = f"""
📊 *DAILY SUMMARY*

Date: {datetime.now().strftime('%Y-%m-%d')}

Trades Today: {trades_today}
P&L Today: {pnl_emoji} ${pnl_today:,.2f}
Open Positions: {open_positions}
"""
        await self.send_message(msg, parse_mode='Markdown')

    async def send_error_alert(self, error_msg: str):
        """Send error alert"""
        msg = f"""
⚠️ *ERROR ALERT*

{error_msg}

Please check the system logs.
"""
        await self.send_message(msg, parse_mode='Markdown')

    def run(self):
        """Start the Telegram bot"""
        if not self.token:
            print("⚠️  Telegram bot token not configured. Notifications disabled.")
            return

        # Create application
        self.app = Application.builder().token(self.token).build()

        # Add command handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(CommandHandler("enable", self.enable_trading))
        self.app.add_handler(CommandHandler("disable", self.disable_trading))
        self.app.add_handler(CommandHandler("stop", self.emergency_stop))

        # Start bot
        print("🤖 Telegram bot started")
        self.app.run_polling()


# Singleton instance
_bot_instance = None

def get_bot():
    """Get singleton bot instance"""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = TradingTelegramBot()
    return _bot_instance
