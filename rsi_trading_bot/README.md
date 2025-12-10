# RSI Divergence Trading Bot

Automated trading system that detects RSI divergence patterns and executes trades with multi-tier profit targets on Alpaca.

---

## 📊 Signal Detection Logic

The bot scans for **RSI divergence signals** daily at **7:00 AM ET**.

### What is RSI Divergence?

**Bullish Divergence** (Buy Signal):
- Price makes a lower low
- RSI makes a higher low
- Indicates potential upward reversal

**Bearish Divergence** (Short Signal):
- Price makes a higher high
- RSI makes a lower high
- Indicates potential downward reversal

### Detection Process

1. **Daily Scan**: Bot runs at 7:00 AM ET every trading day
2. **Data Source**: Fetches historical price data from Twelve Data API
3. **Timeframes Analyzed**: 1-day, 3-day, and 1-week charts
4. **Universe**: Scans S&P 500 stocks for divergence patterns
5. **Validation**: Confirms divergence meets minimum threshold criteria
6. **Storage**: Valid signals are saved to database with status "pending"

### Signal Requirements

- **RSI Period**: 14
- **Lookback Window**: Analyzes recent price action for peak formations
- **Divergence Confirmation**: Both price and RSI must show opposing trends
- **Quality Filter**: Signals must meet minimum strength criteria

---

## 💰 Trading Logic

### Entry Rules

**When**: Market open (9:30 AM ET) on the next trading day after signal detection

**How**: Market orders executed at open

**Position Size**: $5,000 per trade

**Direction**:
- Bullish divergence → LONG position
- Bearish divergence → SHORT position

**Initial Stop Loss**: -7% from entry price

### Exit Strategy - Multi-Tier Profit Taking

The bot uses a 3-tier exit strategy to maximize profits while protecting gains:

#### **Target 1 (T1): +15% Profit**
- **Action**: Close 70% of position
- **Stop Adjustment**: Move stop to breakeven (entry price)
- **Purpose**: Lock in majority of gains, eliminate risk on remaining position

#### **Target 2 (T2): +18% Profit**
- **Action**: Close 15% of position
- **Stop Adjustment**: Move stop to +5% profit
- **Purpose**: Capture additional gains, protect profits on final portion

#### **Target 3 (T3): +50% Profit OR 120 Days**
- **Action**: Close remaining 15% of position
- **Trigger**: Whichever comes first - 50% profit or 120 calendar days
- **Purpose**: Capture home runs or exit stale positions

### Risk Management

- **Stop Loss**: -7% initial, adjusted after T1 and T2 hits
- **Max Open Positions**: 10 concurrent trades
- **Max Daily Trades**: 5 new positions per day
- **Daily Loss Limit**: $2,000 (trading pauses if hit)
- **Position Monitoring**: Every 5 minutes during market hours

### Example Trade Flow

```
Day 1, 7:00 AM:  Signal detected (AAPL bullish divergence)
Day 2, 9:30 AM:  Enter LONG at $180.00, stop at $167.40 (-7%)
Day 15:          Price hits $207.00 (+15%) → Close 70%, stop to $180.00
Day 22:          Price hits $212.40 (+18%) → Close 15%, stop to $189.00
Day 45:          Price hits $270.00 (+50%) → Close remaining 15%
Result:          Trade complete, all exits executed
```

---

## 🏗️ System Architecture

### Deployment

**Server**: DigitalOcean Droplet (Ubuntu 24.04, $6/month)
- IP: 174.138.50.219
- Location: `/root/trading_bot/rsi_trading_bot/`
- Runs 24/7 as systemd service

### External Services

1. **Alpaca Markets** (Trading)
   - Paper trading account ($200,000 virtual funds)
   - API for order execution and position management
   - Real-time market data
   - Cost: Free for paper trading

2. **Twelve Data** (Market Data)
   - Historical price data for divergence scanning
   - RSI calculations
   - Cost: Free tier (800 API calls/day)

3. **Telegram Bot** (Notifications)
   - Real-time alerts sent to your phone
   - Bot token: Configured in .env
   - Chat ID: Your personal Telegram chat
   - Cost: Free

4. **SQLite Database** (Local Storage)
   - File: `trading_bot.db`
   - Stores signals, orders, positions, trades, performance
   - No external service required

### File Structure

```
/root/trading_bot/
├── venv/                          # Python virtual environment
└── rsi_trading_bot/               # Main application directory
    ├── main.py                    # Main orchestrator (runs all tasks)
    ├── config.py                  # Configuration loader
    ├── database.py                # SQLite database manager
    ├── live_scanner.py            # Signal detection (runs 7 AM daily)
    ├── order_executor.py          # Trade execution (runs 9:30 AM daily)
    ├── position_manager.py        # Position monitoring (every 5 min)
    ├── telegram_bot.py            # Telegram notifications
    ├── alpaca_client.py           # Alpaca API wrapper
    ├── reporting.py               # Report generation
    ├── .env                       # API keys and configuration (SECRET)
    ├── trading_bot.db             # SQLite database
    ├── requirements.txt           # Python dependencies
    ├── README.md                  # This file
    └── REPORTING.md               # Reporting documentation
```

### Core Modules

**main.py** - Central coordinator
- Starts all scheduled tasks
- Manages scanner, executor, and position manager
- Handles graceful shutdown

**live_scanner.py** - Signal detection
- Runs daily at 7:00 AM ET
- Scans S&P 500 for divergences
- Saves signals to database
- Sends Telegram notifications

**order_executor.py** - Trade execution
- Runs daily at 9:30 AM ET
- Executes pending signals from database
- Places market orders with stop losses
- Records positions in database

**position_manager.py** - Position monitoring
- Runs every 5 minutes during market hours
- Checks current price against targets
- Executes partial exits at T1, T2, T3
- Adjusts stop losses automatically
- Monitors for stop loss hits

**database.py** - Data persistence
- Manages SQLite database
- Tracks signals, orders, positions, trades
- Provides query methods for reporting

**telegram_bot.py** - Notifications
- Sends alerts for all trading events
- Startup/shutdown notifications
- Signal detections
- Trade executions
- Target hits
- Errors and warnings

**alpaca_client.py** - Brokerage integration
- Wraps Alpaca API
- Places market orders
- Manages positions
- Fetches account data

**reporting.py** - Performance analytics
- Exports signals to CSV
- Exports trades to CSV
- Generates analytics reports

---

## ⚙️ System Commands

The bot runs as a systemd service on your DigitalOcean server.

### Managing the Bot

**Check if bot is running:**
```bash
systemctl status rsi-trading-bot
```

**Start the bot:**
```bash
systemctl start rsi-trading-bot
```

**Stop the bot:**
```bash
systemctl stop rsi-trading-bot
```

**Restart the bot:**
```bash
systemctl restart rsi-trading-bot
```

**Enable auto-start on server reboot:**
```bash
systemctl enable rsi-trading-bot
```

**Disable auto-start:**
```bash
systemctl disable rsi-trading-bot
```

### Viewing Logs

**Watch live logs (real-time):**
```bash
journalctl -u rsi-trading-bot -f
```

**View recent logs (last 50 lines):**
```bash
journalctl -u rsi-trading-bot -n 50
```

**View logs from today:**
```bash
journalctl -u rsi-trading-bot --since today
```

**View logs from specific date:**
```bash
journalctl -u rsi-trading-bot --since "2025-12-10"
```

### Generating Reports

```bash
# Navigate to bot directory
cd ~/trading_bot/rsi_trading_bot

# Activate virtual environment
source /root/trading_bot/venv/bin/activate

# Generate all reports
python reporting.py
```

Reports are saved to: `/root/trading_bot/rsi_trading_bot/reports/`

---

## 📱 Telegram Bot

The bot sends **notifications only** - it does not accept commands.

### Notification Types

✅ **Startup/Shutdown**
- "RSI Trading Bot started successfully"
- "Bot is shutting down..."

🔍 **Signal Detected** (7:00 AM daily)
- "🔔 New Signal Detected!"
- Ticker, divergence type, timeframe
- Entry price target
- Number of signals found

💵 **Trade Executed** (9:30 AM daily)
- "✅ Order Executed"
- Entry price, quantity, direction
- Stop loss level
- Position details

🎯 **Target Hit**
- "🎯 Target 1 Hit!" (+15%)
- "🎯 Target 2 Hit!" (+18%)
- "🎯 Target 3 Hit!" (+50%)
- Exit price, P&L, remaining position

🛡️ **Stop Loss Adjusted**
- "Stop moved to breakeven"
- "Stop moved to +5%"
- Updated stop price

⚠️ **Stop Loss Hit**
- "🛑 Stop Loss Hit"
- Exit price, P&L details

❌ **Errors**
- API failures
- Order rejections
- System issues

### Setting Up Notifications

Your Telegram bot is already configured with:
- **Bot Token**: In `.env` file
- **Chat ID**: Your personal Telegram chat ID

To receive notifications:
1. Find your bot in Telegram (search by username)
2. Start a chat with the bot
3. Bot will send messages automatically when events occur

---

## 📊 Reporting

The bot includes a comprehensive reporting system for tracking performance.

### Report Types

**1. Signals Report**
- All divergence signals detected
- Signal date, ticker, timeframe
- Entry price, status (executed/pending/failed)
- Format: CSV for Excel/Google Sheets

**2. Trades Report**
- All completed positions
- Entry/exit details, P&L, holding period
- TP1/TP2/TP3 hit status and prices
- Average P&L per exit
- Format: CSV with detailed exit breakdown

**3. Analytics Report**
- Overall performance metrics
- **Yearly P&L** breakdown
- Quarterly P&L breakdown
- Monthly statistics
- Performance by timeframe (1d/3d/1w)
- Performance by exit reason
- Format: Multi-section CSV

### Generating Reports

**From DigitalOcean Console:**

```bash
# 1. Open console to your droplet
# 2. Navigate to bot directory
cd ~/trading_bot/rsi_trading_bot

# 3. Activate virtual environment
source /root/trading_bot/venv/bin/activate

# 4. Generate reports
python reporting.py
```

**Output:**
```
✅ Signals exported to: reports/signals_20251210_143052.csv
✅ Trades exported to: reports/trades_20251210_143052.csv
✅ Analytics exported to: reports/analytics_20251210_143052.csv
```

### Accessing Reports

**Option 1: View in console**
```bash
cat reports/signals_*.csv
cat reports/analytics_*.csv
```

**Option 2: Download via SCP (if SSH configured)**
```bash
scp root@174.138.50.219:~/trading_bot/rsi_trading_bot/reports/*.csv ~/Downloads/
```

**Option 3: Copy/paste**
- View file with `cat` command
- Copy output
- Paste into local Excel/Google Sheets

### Report Details

See **REPORTING.md** for complete documentation including:
- Column descriptions for each report
- Example outputs
- How to open in Excel/Google Sheets
- Scheduling automatic report generation

---

## 🚀 Quick Start Guide

### First Time Setup (Already Completed)

1. ✅ Created DigitalOcean droplet
2. ✅ Cloned repository
3. ✅ Configured API keys (.env file)
4. ✅ Installed dependencies
5. ✅ Set up systemd service
6. ✅ Started bot

### Daily Operations

**The bot runs automatically:**
- 7:00 AM ET: Scans for signals
- 9:30 AM ET: Executes pending trades
- Every 5 min: Monitors open positions
- Sends Telegram notifications for all events

**You don't need to do anything** - just monitor Telegram messages.

### Weekly/Monthly Tasks

**Generate performance reports:**
```bash
cd ~/trading_bot/rsi_trading_bot
source /root/trading_bot/venv/bin/activate
python reporting.py
```

**Check bot health:**
```bash
systemctl status rsi-trading-bot
journalctl -u rsi-trading-bot -n 50
```

---

## 🔒 Security Notes

- **.env file** contains sensitive API keys - never commit to git
- **Paper trading** is enabled by default ($200k virtual money)
- To switch to live trading: Update `ALPACA_BASE_URL` in .env to `https://api.alpaca.markets`
- **Database file** (trading_bot.db) contains all trade history - backup regularly

---

## 💡 Troubleshooting

**Bot not running?**
```bash
systemctl status rsi-trading-bot
journalctl -u rsi-trading-bot -n 100
```

**Not receiving Telegram messages?**
- Check bot is running: `systemctl status rsi-trading-bot`
- Verify Telegram chat ID in .env
- Check logs for Telegram errors

**Trades not executing?**
- Check Alpaca API keys in .env
- Verify account has sufficient buying power
- Check logs for API errors
- Verify market is open (9:30 AM - 4:00 PM ET, Mon-Fri)

**No signals detected?**
- Normal - divergences are relatively rare
- Bot scans daily, may go days without signals
- Check logs to confirm scanner ran at 7:00 AM

---

## 📈 Performance Monitoring

**Key Metrics to Track:**

1. **Signal Quality**: How many signals convert to profitable trades
2. **Win Rate**: Percentage of trades that are profitable
3. **Average Win/Loss**: Size of wins vs losses
4. **Target Hit Rate**: How often T1, T2, T3 are reached
5. **Max Drawdown**: Largest peak-to-valley decline

**Review Reports:**
- Weekly: Check trades report for recent performance
- Monthly: Review analytics report for trends
- Quarterly: Assess strategy performance vs backtest

---

## 💵 Cost Breakdown

- **DigitalOcean Server**: $6/month (1 vCPU, 1GB RAM)
- **Alpaca Paper Trading**: Free
- **Twelve Data API**: Free (800 calls/day)
- **Telegram Bot**: Free

**Total Monthly Cost: $6**

---

## ⚠️ Important Disclaimers

- This bot trades with **paper money** by default
- Past performance does not guarantee future results
- Always test thoroughly before using real money
- Monitor the bot regularly, especially in the first weeks
- Set up alerts for daily loss limits being hit
- Review trades weekly to ensure system is working as expected

---

## 📚 Additional Documentation

- **REPORTING.md** - Detailed reporting documentation
- **DEPLOYMENT_STATUS.md** - Deployment history and configuration
- **BUILD_COMPLETE.md** - Original build documentation

---

## 🆘 Support

For issues:
1. Check systemctl status and logs (journalctl)
2. Verify .env configuration
3. Test API connections: `python test_connection.py`
4. Review recent Telegram messages for errors
5. Check Alpaca dashboard for account status

---

**Last Updated**: December 10, 2025
**Version**: 1.0
**Status**: Running in Production (Paper Trading)
