#!/bin/bash

# RSI Trading Bot - DigitalOcean Deployment Script
# This script sets up the trading bot on a fresh Ubuntu 22.04 droplet

set -e  # Exit on any error

echo "=============================================="
echo "RSI Trading Bot - DigitalOcean Deployment"
echo "=============================================="
echo ""

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3.11+ and pip
echo "🐍 Installing Python 3.11..."
sudo apt-get install -y python3.11 python3.11-venv python3-pip git

# Install system dependencies
echo "📚 Installing system dependencies..."
sudo apt-get install -y build-essential libssl-dev libffi-dev python3-dev

# Create bot directory
echo "📁 Creating bot directory..."
mkdir -p ~/trading_bot
cd ~/trading_bot

# Clone repository (you'll need to provide your repo URL)
echo "📥 Repository cloning..."
echo "NOTE: Please manually clone your repository:"
echo "  git clone <your-repo-url> ."
echo ""
echo "Press ENTER when done..."
read

# Create virtual environment
echo "🔧 Creating Python virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd rsi_trading_bot
pip install --upgrade pip
pip install -r requirements.txt

# Copy .env.example to .env
echo "⚙️  Setting up environment configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "✅ Created .env file"
    echo "❗ IMPORTANT: Edit .env file with your actual credentials:"
    echo "   nano .env"
    echo ""
else
    echo "✅ .env file already exists"
fi

# Create systemd service for auto-start
echo "🔧 Creating systemd service..."
sudo tee /etc/systemd/system/trading-bot.service > /dev/null <<EOF
[Unit]
Description=RSI Trading Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/trading_bot/rsi_trading_bot
Environment="PATH=$HOME/trading_bot/venv/bin"
ExecStart=$HOME/trading_bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# Enable service to start on boot
echo "✅ Enabling bot to start on boot..."
sudo systemctl enable trading-bot.service

echo ""
echo "=============================================="
echo "✅ Deployment Complete!"
echo "=============================================="
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Edit your .env file with real credentials:"
echo "   nano ~/trading_bot/rsi_trading_bot/.env"
echo ""
echo "2. Test the bot manually first:"
echo "   cd ~/trading_bot/rsi_trading_bot"
echo "   source ../venv/bin/activate"
echo "   python test_connection.py"
echo ""
echo "3. Start the bot service:"
echo "   sudo systemctl start trading-bot"
echo ""
echo "4. Check bot status:"
echo "   sudo systemctl status trading-bot"
echo ""
echo "5. View bot logs:"
echo "   sudo journalctl -u trading-bot -f"
echo ""
echo "6. Stop the bot:"
echo "   sudo systemctl stop trading-bot"
echo ""
echo "=============================================="
