# RSI Divergence Trading Bot

Automated trading system for RSI divergence signals with Alpaca paper trading.

## Features

- 📊 **Automated Signal Detection**: Daily scanning for RSI divergences
- 🤖 **Alpaca Integration**: Paper and live trading support
- 📱 **Telegram Notifications**: Real-time alerts on your phone
- 💰 **Multi-Leg Profit Taking**: T1 (+15%), T2 (+18%), T3 (+50%)
- 🛡️ **Risk Management**: Stop losses, position sizing, daily limits
- 📈 **Position Management**: Automatic stop adjustments

## Setup Instructions

### 1. Get Alpaca API Keys

1. Go to https://alpaca.markets/
2. Sign up and verify your account
3. Navigate to **Paper Trading** section
4. Click **Generate API Keys** or **View Keys**
5. Copy both:
   - API Key ID (starts with PK...)
   - Secret Key

### 2. Get Your Telegram Chat ID

After creating your bot (@BotFather gave you the token), you need your chat ID:

1. Send a message to your bot (anything)
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for `"chat":{"id":123456789...}`
4. Copy that ID number

### 3. Configure Environment

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your credentials:
   ```bash
   nano .env
   ```

3. Fill in:
   ```
   ALPACA_API_KEY=your_alpaca_key_here
   ALPACA_SECRET_KEY=your_alpaca_secret_here
   TELEGRAM_BOT_TOKEN=8566250092:AAH3__b0H9D5ydLv9Sy8eIYmVS26JoCUnZI
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```

### 4. Install Dependencies

```bash
cd rsi_trading_bot
pip install -r requirements.txt
```

### 5. Test Configuration

```bash
python config.py
```

You should see: `✓ Configuration loaded successfully`

### 6. Test Telegram Bot

```bash
python telegram_bot.py
```

Send `/start` to your bot on Telegram. You should get a welcome message.

## Trading Rules

### Entry
- Enter at market OPEN (9:30 AM ET) on next trading day after signal
- Position size: $5,000 per trade
- Initial stop loss: -7%

### Exit Targets
- **T1**: +15% profit → Close 70%, move stop to breakeven
- **T2**: +18% profit → Close 15%, move stop to +5%
- **T3**: +50% profit OR 120 days → Close remaining 15%

### Risk Management
- Max open positions: 10
- Max daily trades: 5
- Daily loss limit: $2,000

## Commands

Once running, use these Telegram commands:

- `/start` - Get welcome message and command list
- `/status` - Check system status and configuration
- `/positions` - View current open positions
- `/pnl` - See profit/loss summary
- `/signals` - Recent divergence signals
- `/enable` - Enable trading (takes new signals)
- `/disable` - Disable new trades (manages existing positions)
- `/stop` - Emergency stop (halts all trading)

## Running the Bot

### Manual Test (Development)
```bash
python main.py
```

### Production (Server)
```bash
# Keep running in background
nohup python main.py > bot.log 2>&1 &
```

### With Auto-Restart (Systemd)
Create `/etc/systemd/system/trading-bot.service`:
```ini
[Unit]
Description=RSI Trading Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/rsi_trading_bot
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
sudo systemctl status trading-bot
```

## File Structure

```
rsi_trading_bot/
├── config.py              # Configuration management
├── telegram_bot.py        # Telegram notifications
├── alpaca_client.py       # Alpaca API wrapper
├── live_scanner.py        # Daily divergence scanner
├── order_executor.py      # Order placement
├── position_manager.py    # Position monitoring
├── database.py            # Trade logging
├── main.py                # Main orchestrator
├── requirements.txt       # Dependencies
├── .env                   # Your credentials (DO NOT COMMIT)
└── README.md              # This file
```

## Safety Features

1. **Paper Trading First**: Start with paper money
2. **Emergency Stop**: `/stop` command halts trading
3. **Daily Loss Limit**: Stops after $2,000 daily loss
4. **Max Positions**: Limits open positions to 10
5. **Sanity Checks**: Validates orders before execution

## Monitoring

The bot sends Telegram notifications for:
- ✅ New signals detected
- 💰 Orders executed
- 📈 Profit targets hit
- 🛡️ Stop losses adjusted
- ⚠️ Errors and warnings
- 📊 Daily performance summary

## Next Steps

1. Complete `.env` configuration
2. Test with paper trading for 2-4 weeks
3. Monitor performance vs backtest expectations
4. Once confident, switch to live trading (update `ALPACA_BASE_URL` in `.env`)

## Support

For issues or questions:
- Check logs: `tail -f bot.log`
- Test individual modules
- Review Alpaca dashboard
- Check Telegram bot is responding

## Cost Breakdown

- DigitalOcean Server: $6/month
- Alpaca Paper Trading: Free
- Alpaca Live Trading Data: $9/month (when going live)
- **Total: $6-15/month**

---

**⚠️ Important:** Always start with paper trading. Never risk real money until you've validated the system works as expected.
