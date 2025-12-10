"""
Configuration Management
Loads settings from .env file securely
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)


class Config:
    """Configuration class for trading bot"""

    # Alpaca API Configuration
    ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
    ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')
    ALPACA_BASE_URL = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

    # Trading Parameters
    POSITION_SIZE = float(os.getenv('POSITION_SIZE', 5000))
    MAX_POSITIONS = int(os.getenv('MAX_POSITIONS', 10))
    MAX_DAILY_TRADES = int(os.getenv('MAX_DAILY_TRADES', 5))
    DAILY_LOSS_LIMIT = float(os.getenv('DAILY_LOSS_LIMIT', 2000))

    # Risk Management Rules
    STOP_LOSS_PCT = float(os.getenv('STOP_LOSS_PCT', 7))
    TARGET1_PCT = float(os.getenv('TARGET1_PCT', 15))
    TARGET1_SIZE = float(os.getenv('TARGET1_SIZE', 70))
    TARGET2_PCT = float(os.getenv('TARGET2_PCT', 18))
    TARGET2_SIZE = float(os.getenv('TARGET2_SIZE', 15))
    TARGET3_PCT = float(os.getenv('TARGET3_PCT', 50))
    TARGET3_SIZE = float(os.getenv('TARGET3_SIZE', 15))
    MAX_HOLD_DAYS = int(os.getenv('MAX_HOLD_DAYS', 120))

    # Market Hours (ET)
    MARKET_OPEN = "09:30"
    MARKET_CLOSE = "16:00"
    SCANNER_TIME = "07:00"  # Run scanner before market open

    # Database
    DB_PATH = Path(__file__).parent / 'trading.db'

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = Path(__file__).parent / 'logs' / 'trading_bot.log'

    @classmethod
    def validate(cls):
        """Validate that all required config is set"""
        required = [
            'ALPACA_API_KEY',
            'ALPACA_SECRET_KEY',
            'TELEGRAM_BOT_TOKEN',
        ]

        missing = []
        for key in required:
            if not getattr(cls, key):
                missing.append(key)

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        return True


# Validate on import
try:
    Config.validate()
    print("✓ Configuration loaded successfully")
except ValueError as e:
    print(f"⚠️  Configuration incomplete: {e}")
    print("Please copy .env.example to .env and fill in your API keys")
