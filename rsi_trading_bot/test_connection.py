"""
Test Script to Verify Alpaca and Telegram Connections
Run this after setting up your .env file
"""

import sys
import asyncio
from config import Config
from alpaca_client import get_alpaca_client
from telegram_bot import get_bot


def test_alpaca():
    """Test Alpaca API connection"""
    print("\n" + "="*70)
    print("TESTING ALPACA CONNECTION")
    print("="*70)

    try:
        client = get_alpaca_client()

        # Test 1: Get account info
        print("\n1. Getting account information...")
        account = client.get_account()

        if account:
            print(f"   ✓ Account Status: {account['status']}")
            print(f"   ✓ Buying Power: ${account['buying_power']:,.2f}")
            print(f"   ✓ Portfolio Value: ${account['portfolio_value']:,.2f}")
            print(f"   ✓ Cash: ${account['cash']:,.2f}")
        else:
            print("   ✗ Failed to get account info")
            return False

        # Test 2: Get positions
        print("\n2. Getting current positions...")
        positions = client.get_positions()
        print(f"   ✓ Open Positions: {len(positions)}")

        if positions:
            for pos in positions:
                print(f"     - {pos['symbol']}: {pos['qty']} shares @ ${pos['avg_entry_price']:.2f}")

        # Test 3: Check market status
        print("\n3. Checking market status...")
        market_hours = client.get_market_hours()

        if market_hours:
            status = "OPEN" if market_hours['is_open'] else "CLOSED"
            print(f"   ✓ Market Status: {status}")
            print(f"   ✓ Next Open: {market_hours['next_open']}")
            print(f"   ✓ Next Close: {market_hours['next_close']}")
        else:
            print("   ✗ Failed to get market status")
            return False

        # Test 4: Get sample price data
        print("\n4. Testing market data access...")
        symbols = ['AAPL', 'MSFT']
        bars = client.get_latest_bars(symbols, timeframe='1Day')

        if bars:
            print(f"   ✓ Successfully retrieved price data")
            for symbol, data in bars.items():
                print(f"     - {symbol}: ${data['close']:.2f}")
        else:
            print("   ✗ Failed to get price data")
            return False

        print("\n✅ ALPACA CONNECTION SUCCESSFUL")
        return True

    except Exception as e:
        print(f"\n❌ ALPACA CONNECTION FAILED: {e}")
        return False


async def test_telegram():
    """Test Telegram bot connection"""
    print("\n" + "="*70)
    print("TESTING TELEGRAM CONNECTION")
    print("="*70)

    if not Config.TELEGRAM_CHAT_ID or Config.TELEGRAM_CHAT_ID == 'your_chat_id_here':
        print("\n⚠️  TELEGRAM CHAT ID NOT SET")
        print("   Please:")
        print("   1. Send a message to @Archie_TradingBot on Telegram")
        print("   2. Visit: https://api.telegram.org/bot8566250092:AAH3__b0H9D5ydLv9Sy8eIYmVS26JoCUnZI/getUpdates")
        print("   3. Find 'chat':{'id':YOUR_NUMBER}")
        print("   4. Update TELEGRAM_CHAT_ID in .env")
        return False

    try:
        bot = get_bot()

        print(f"\n1. Sending test message to Chat ID: {Config.TELEGRAM_CHAT_ID}...")

        # Send test message
        await bot.send_message("🤖 Test message from RSI Trading Bot!\n\nConnection successful! ✅")

        print("   ✓ Test message sent")
        print("\n✅ TELEGRAM CONNECTION SUCCESSFUL")
        print("   Check your Telegram app for the test message!")
        return True

    except Exception as e:
        print(f"\n❌ TELEGRAM CONNECTION FAILED: {e}")
        print("   Make sure:")
        print("   1. You sent a message to @Archie_TradingBot first")
        print("   2. TELEGRAM_CHAT_ID is correct in .env")
        return False


def main():
    """Run all connection tests"""
    print("\n" + "="*70)
    print("RSI TRADING BOT - CONNECTION TEST")
    print("="*70)
    print(f"\nUsing Configuration:")
    print(f"  Alpaca: {Config.ALPACA_BASE_URL}")
    print(f"  Position Size: ${Config.POSITION_SIZE:,.0f}")
    print(f"  Max Positions: {Config.MAX_POSITIONS}")

    # Test Alpaca
    alpaca_ok = test_alpaca()

    # Test Telegram
    telegram_ok = asyncio.run(test_telegram())

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"  Alpaca API: {'✅ PASS' if alpaca_ok else '❌ FAIL'}")
    print(f"  Telegram Bot: {'✅ PASS' if telegram_ok else '⚠️  INCOMPLETE'}")

    if alpaca_ok and telegram_ok:
        print("\n🎉 ALL TESTS PASSED!")
        print("   Your trading bot is ready to run.")
        print("\n   Next steps:")
        print("   1. Review configuration in .env")
        print("   2. Run: python main.py")
    elif alpaca_ok:
        print("\n⚠️  Alpaca works but Telegram needs setup")
        print("   Update TELEGRAM_CHAT_ID in .env and test again")
    else:
        print("\n❌ TESTS FAILED")
        print("   Please check your .env configuration")

    print("="*70 + "\n")


if __name__ == "__main__":
    main()
