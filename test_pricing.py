#!/usr/bin/env python3
"""
Test pricing functionality - Debug why "Could not get current price" happens
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent / 'rsi_trading_bot'))

from alpaca_client import get_alpaca_client
from database import get_database

def test_pricing():
    """Test getting prices for pending signals"""

    alpaca = get_alpaca_client()
    db = get_database()

    print("="*70)
    print("PRICING TEST - Diagnosing Price Fetch Issues")
    print("="*70)
    print()

    # Get pending signals
    pending = db.get_pending_signals()

    if not pending:
        print("No pending signals. Testing with GLW, CAT, JNJ instead...")
        test_symbols = ['GLW', 'CAT', 'JNJ']
    else:
        test_symbols = [s['ticker'] for s in pending]

    print(f"Testing pricing for: {', '.join(test_symbols)}")
    print()

    # Test 1: Check market status
    print("="*70)
    print("TEST 1: Market Status")
    print("="*70)
    try:
        market_hours = alpaca.get_market_hours()
        if market_hours:
            print(f"Market Open: {market_hours['is_open']}")
            print(f"Next Open: {market_hours['next_open']}")
            print(f"Next Close: {market_hours['next_close']}")
        else:
            print("❌ Could not get market hours")
    except Exception as e:
        print(f"❌ Error checking market: {e}")

    print()

    # Test 2: Try to get bars
    print("="*70)
    print("TEST 2: Get Latest Bars (1Min)")
    print("="*70)
    try:
        bars = alpaca.get_latest_bars(test_symbols, timeframe='1Min')
        if bars:
            for symbol, data in bars.items():
                print(f"✅ {symbol}: ${data['close']:.2f}")
        else:
            print("❌ No bars returned")
    except Exception as e:
        print(f"❌ Error: {e}")

    print()

    # Test 3: Try to get quotes
    print("="*70)
    print("TEST 3: Get Latest Quotes")
    print("="*70)
    try:
        quotes = alpaca.get_latest_quote(test_symbols)
        if quotes:
            for symbol, data in quotes.items():
                print(f"✅ {symbol}: ${data['close']:.2f}")
        else:
            print("❌ No quotes returned")
    except Exception as e:
        print(f"❌ Error: {e}")

    print()

    # Test 4: Try each symbol individually
    print("="*70)
    print("TEST 4: Individual Symbol Tests")
    print("="*70)
    for symbol in test_symbols:
        print(f"\nTesting {symbol}:")

        # Try bars
        try:
            bars = alpaca.get_latest_bars([symbol])
            if bars and symbol in bars:
                print(f"  ✅ Bars: ${bars[symbol]['close']:.2f}")
            else:
                print(f"  ❌ Bars: None")
        except Exception as e:
            print(f"  ❌ Bars error: {e}")

        # Try quotes
        try:
            quotes = alpaca.get_latest_quote([symbol])
            if quotes and symbol in quotes:
                print(f"  ✅ Quotes: ${quotes[symbol]['close']:.2f}")
            else:
                print(f"  ❌ Quotes: None")
        except Exception as e:
            print(f"  ❌ Quotes error: {e}")

    print()

    # Test 5: Test place_market_order logic (without actually placing order)
    print("="*70)
    print("TEST 5: Simulate place_market_order Logic")
    print("="*70)

    for symbol in test_symbols[:1]:  # Test just first symbol
        print(f"\nSimulating order for {symbol}:")

        try:
            # This is what place_market_order does
            bars = alpaca.get_latest_bars([symbol])

            if not bars or symbol not in bars:
                print(f"  ❌ Cannot get price - bars check failed")
                print(f"     bars = {bars}")
            else:
                current_price = bars[symbol]['close']
                print(f"  ✅ Got price: ${current_price:.2f}")

                # Calculate shares
                position_size = 5000
                shares = position_size / current_price
                print(f"  Would buy {shares:.4f} shares")

        except Exception as e:
            print(f"  ❌ Error: {e}")

    print()
    print("="*70)
    print("PRICING TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    test_pricing()
