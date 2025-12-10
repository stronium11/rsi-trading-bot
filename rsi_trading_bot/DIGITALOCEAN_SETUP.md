# DigitalOcean Deployment Guide

Complete guide for deploying the RSI Trading Bot on DigitalOcean.

---

## Prerequisites

- DigitalOcean account
- Alpaca API keys (paper or live)
- Telegram bot token and chat ID
- Basic SSH knowledge

---

## Step 1: Create Droplet

1. **Log into DigitalOcean**
   - Go to https://cloud.digitalocean.com/

2. **Create New Droplet**
   - Click "Create" → "Droplets"

3. **Choose Image**
   - Distribution: **Ubuntu 22.04 (LTS) x64**

4. **Choose Plan**
   - Droplet Type: **Basic**
   - CPU Options: **Regular**
   - Size: **$6/mo** (1 GB RAM, 1 vCPU, 25 GB SSD)
     - This is sufficient for the bot

5. **Choose Datacenter Region**
   - Recommend: **New York** (closest to US market)

6. **Authentication**
   - **Option A (Recommended):** SSH Key
     - Add your SSH public key
   - **Option B:** Password
     - Use a strong password

7. **Finalize**
   - Hostname: `rsi-trading-bot`
   - Click **Create Droplet**

8. **Wait for Droplet Creation**
   - Takes 1-2 minutes
   - Note the IP address when ready

---

## Step 2: Connect to Droplet

### Using SSH Key (Recommended)

```bash
ssh root@YOUR_DROPLET_IP
```

### Using Password

```bash
ssh root@YOUR_DROPLET_IP
# Enter password when prompted
```

---

## Step 3: Run Deployment Script

1. **Download the deployment script**

```bash
# Create directory
mkdir -p ~/trading_bot && cd ~/trading_bot

# Download your repository (replace with your actual repo URL)
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git .
```

2. **Make script executable**

```bash
chmod +x rsi_trading_bot/deploy_digitalocean.sh
```

3. **Run deployment script**

```bash
cd rsi_trading_bot
./deploy_digitalocean.sh
```

The script will:
- Update system packages
- Install Python 3.11
- Create virtual environment
- Install dependencies
- Set up systemd service
- Configure auto-start on reboot

---

## Step 4: Configure Environment Variables

1. **Edit .env file**

```bash
nano ~/trading_bot/rsi_trading_bot/.env
```

2. **Update with your actual values:**

```bash
# Alpaca API Configuration
ALPACA_API_KEY=YOUR_ACTUAL_KEY_HERE
ALPACA_SECRET_KEY=YOUR_ACTUAL_SECRET_HERE
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # Change to api.alpaca.markets for live

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
TELEGRAM_CHAT_ID=YOUR_CHAT_ID_HERE

# Trading Configuration (adjust as needed)
POSITION_SIZE=5000
MAX_POSITIONS=10
MAX_DAILY_TRADES=5
DAILY_LOSS_LIMIT=2000

# Risk Management (from your backtested strategy)
STOP_LOSS_PCT=7
TARGET1_PCT=15
TARGET1_SIZE=70
TARGET2_PCT=18
TARGET2_SIZE=15
TARGET3_PCT=50
TARGET3_SIZE=15
MAX_HOLD_DAYS=120
```

3. **Save and exit:**
   - Press `Ctrl + X`
   - Press `Y` to confirm
   - Press `Enter`

---

## Step 5: Test the Bot

Before starting the bot as a service, test it manually:

```bash
# Activate virtual environment
cd ~/trading_bot
source venv/bin/activate

# Test connections
cd rsi_trading_bot
python test_connection.py
```

**Expected output:**
```
✓ Configuration loaded successfully
✓ Alpaca account connected
✓ Telegram bot connected
✓ All tests passed
```

If tests fail:
- Check .env file for typos
- Verify API keys are correct
- Ensure Telegram chat ID is correct

---

## Step 6: Start the Bot

### Start as a Service

```bash
# Start the bot
sudo systemctl start trading-bot

# Check status
sudo systemctl status trading-bot

# Should show: "active (running)"
```

### View Live Logs

```bash
# Follow logs in real-time
sudo journalctl -u trading-bot -f

# Press Ctrl+C to exit
```

### Check Telegram

You should receive a startup message on Telegram:
```
🤖 RSI Trading Bot Started

📊 Current Status:
• Open Positions: 0
• Total Signals: 0
...

✅ Bot is now running...
```

---

## Step 7: Bot Management

### Stop the Bot

```bash
sudo systemctl stop trading-bot
```

### Restart the Bot

```bash
sudo systemctl restart trading-bot
```

### Disable Auto-Start

```bash
sudo systemctl disable trading-bot
```

### View Recent Logs

```bash
# Last 100 lines
sudo journalctl -u trading-bot -n 100

# Last hour
sudo journalctl -u trading-bot --since "1 hour ago"

# Today's logs
sudo journalctl -u trading-bot --since today
```

---

## Step 8: Monitoring

### System Resources

```bash
# Check CPU and memory usage
htop

# Or use top
top
```

### Disk Space

```bash
# Check available disk space
df -h

# Check database size
ls -lh ~/trading_bot/rsi_trading_bot/trading_bot.db
```

### Database Stats

```bash
cd ~/trading_bot/rsi_trading_bot
source ../venv/bin/activate

# Open Python
python3

# Run queries
>>> from database import get_database
>>> db = get_database()
>>> stats = db.get_statistics()
>>> print(stats)
>>> exit()
```

---

## Troubleshooting

### Bot Not Starting

1. **Check logs:**
```bash
sudo journalctl -u trading-bot -n 50
```

2. **Check .env file:**
```bash
cat ~/trading_bot/rsi_trading_bot/.env
```

3. **Test manually:**
```bash
cd ~/trading_bot/rsi_trading_bot
source ../venv/bin/activate
python main.py
```

### Connection Errors

1. **Test Alpaca connection:**
```bash
python test_connection.py
```

2. **Check API keys:**
   - Ensure keys are valid
   - Check if paper trading URL matches account type

3. **Check firewall:**
```bash
# Allow outbound HTTPS
sudo ufw allow out 443/tcp
```

### High CPU Usage

```bash
# Check if bot is in a loop
sudo journalctl -u trading-bot -f

# Restart if needed
sudo systemctl restart trading-bot
```

### Database Issues

```bash
# Backup database
cp ~/trading_bot/rsi_trading_bot/trading_bot.db ~/trading_bot.db.backup

# Check database integrity
cd ~/trading_bot/rsi_trading_bot
sqlite3 trading_bot.db "PRAGMA integrity_check;"
```

---

## Updating the Bot

### Pull Latest Changes

```bash
# Stop the bot
sudo systemctl stop trading-bot

# Pull updates
cd ~/trading_bot
git pull origin main

# Update dependencies
source venv/bin/activate
cd rsi_trading_bot
pip install -r requirements.txt --upgrade

# Restart bot
sudo systemctl start trading-bot
```

---

## Security Best Practices

### 1. Set Up Firewall

```bash
# Enable UFW firewall
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow outbound traffic
sudo ufw default allow outgoing

# Block incoming (bot doesn't need it)
sudo ufw default deny incoming
```

### 2. Disable Root Login

```bash
# Create a non-root user
adduser trader
usermod -aG sudo trader

# Copy SSH keys
mkdir -p /home/trader/.ssh
cp ~/.ssh/authorized_keys /home/trader/.ssh/
chown -R trader:trader /home/trader/.ssh
chmod 700 /home/trader/.ssh
chmod 600 /home/trader/.ssh/authorized_keys

# Disable root login
nano /etc/ssh/sshd_config
# Change: PermitRootLogin no

# Restart SSH
sudo systemctl restart sshd

# Test new user login before logging out!
```

### 3. Keep System Updated

```bash
# Set up automatic security updates
sudo apt-get install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### 4. Backup Strategy

```bash
# Create backup script
cat > ~/backup_bot.sh <<'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf ~/backups/trading_bot_$DATE.tar.gz \
    ~/trading_bot/rsi_trading_bot/trading_bot.db \
    ~/trading_bot/rsi_trading_bot/.env
# Keep only last 30 days
find ~/backups -name "trading_bot_*.tar.gz" -mtime +30 -delete
EOF

chmod +x ~/backup_bot.sh

# Run daily via cron
crontab -e
# Add: 0 2 * * * ~/backup_bot.sh
```

---

## Cost Breakdown

| Service | Cost |
|---------|------|
| DigitalOcean Droplet ($6/month) | $6.00 |
| Alpaca Paper Trading | Free |
| Telegram Bot | Free |
| **Total** | **$6/month** |

When switching to live trading:
- Alpaca Live Data Feed: +$9/month
- **Total Live:** **$15/month**

---

## Next Steps After Deployment

1. **Paper Trading Period (2-4 weeks)**
   - Monitor all trades
   - Verify strategy execution
   - Check for any bugs
   - Compare results to backtest

2. **Performance Tracking**
   - Daily P&L review via Telegram
   - Weekly performance analysis
   - Monthly backtest comparison

3. **Go Live Checklist**
   - [ ] Paper trading successful for 2+ weeks
   - [ ] No critical bugs found
   - [ ] Results match backtest expectations
   - [ ] All risk limits working correctly
   - [ ] Update .env to use live API
   - [ ] Fund Alpaca account
   - [ ] Subscribe to Alpaca live data
   - [ ] Restart bot with live config

---

## Support

If you encounter issues:

1. Check logs: `sudo journalctl -u trading-bot -f`
2. Review Telegram messages
3. Test connections: `python test_connection.py`
4. Check database stats
5. Review deployment guide sections above

---

**Last Updated:** December 10, 2025
**Bot Version:** v1.0.0
