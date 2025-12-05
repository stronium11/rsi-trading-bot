#!/usr/bin/env python3
"""
CORRECTED Trade Simulator
Fixes bugs from original advanced_rule_optimizer.py:
- Bug #1: Prevents T1/T2/T3 from firing on same day
- Bug #2: Validates T2 > T1 and T3 > T2
- Bug #3: Clarifies position sizing logic
- Bug #4: Better documentation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class CorrectedTradeSimulator:
    """
    Simulates a single trade with configurable rules (CORRECTED VERSION)
    """

    def __init__(self, signal, price_df, rules):
        """
        Initialize trade simulator

        Parameters:
        - signal: Original signal dictionary
        - price_df: DataFrame with daily OHLC data
        - rules: Dictionary with position management rules
        """
        self.ticker = signal['ticker']
        self.entry_date = pd.to_datetime(signal['entry_date'])
        self.entry_price = signal['entry_price']
        self.direction = signal['direction']
        self.initial_capital = signal['initial_capital']
        self.initial_shares = signal['initial_shares']

        self.price_df = price_df
        self.rules = rules

        # Validate rules
        self._validate_rules()

        # Position tracking
        self.remaining_shares = self.initial_shares
        self.exits = []
        self.days_in_trade = 0
        self.is_closed = False
        self.last_exit_date = None  # FIX: Track last exit to prevent same-day multi-exits

        # Stop loss tracking
        self.stop_price = self.calculate_initial_stop()
        self.highest_profit_pct = 0

    def _validate_rules(self):
        """Validate that rules make logical sense"""
        t1 = self.rules.get('target1_pct', 10)
        t2 = self.rules.get('target2_pct', 20)
        t3 = self.rules.get('target3_pct', 50)

        # FIX: Validate target progression
        if t2 <= t1:
            raise ValueError(f"Target 2 ({t2}%) must be greater than Target 1 ({t1}%)")
        if t3 <= t2:
            raise ValueError(f"Target 3 ({t3}%) must be greater than Target 2 ({t2}%)")

        # Validate position sizing adds up correctly
        t1_size = self.rules.get('target1_size', 50)
        t2_size = self.rules.get('target2_size', 25)

        total_size = t1_size + t2_size
        if total_size > 100:
            raise ValueError(f"T1 size ({t1_size}%) + T2 size ({t2_size}%) = {total_size}% exceeds 100%")

    def calculate_initial_stop(self):
        """Calculate initial stop loss price"""
        stop_pct = self.rules.get('initial_stop_pct', 5) / 100

        if self.direction == 'LONG':
            return self.entry_price * (1 - stop_pct)
        else:  # SHORT
            return self.entry_price * (1 + stop_pct)

    def calculate_profit_pct(self, current_price):
        """Calculate current profit percentage"""
        if self.direction == 'LONG':
            return ((current_price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT
            return ((self.entry_price - current_price) / self.entry_price) * 100

    def update_stop_to_breakeven(self):
        """Move stop to breakeven"""
        self.stop_price = self.entry_price

    def update_stop_to_profit(self, profit_pct):
        """Move stop to specific profit level"""
        if self.direction == 'LONG':
            self.stop_price = self.entry_price * (1 + profit_pct / 100)
        else:  # SHORT
            self.stop_price = self.entry_price * (1 - profit_pct / 100)

    def update_trailing_stop(self, current_price):
        """Update trailing stop if enabled"""
        if not self.rules.get('use_trailing_stop', False):
            return

        trail_pct = self.rules.get('trailing_stop_pct', 10) / 100

        if self.direction == 'LONG':
            new_stop = current_price * (1 - trail_pct)
            if new_stop > self.stop_price:
                self.stop_price = new_stop
        else:  # SHORT
            new_stop = current_price * (1 + trail_pct)
            if new_stop < self.stop_price:
                self.stop_price = new_stop

    def execute_exit(self, date, price, shares, reason):
        """Execute position exit"""
        if shares <= 0 or self.remaining_shares <= 0:
            return

        shares = min(shares, self.remaining_shares)

        if self.direction == 'LONG':
            pnl = (price - self.entry_price) * shares
        else:  # SHORT
            pnl = (self.entry_price - price) * shares

        pnl_pct = self.calculate_profit_pct(price)

        self.exits.append({
            'date': date,
            'price': price,
            'shares': shares,
            'reason': reason,
            'pnl': pnl,
            'pnl_pct': pnl_pct
        })

        self.remaining_shares -= shares
        self.last_exit_date = date  # FIX: Track last exit date

        if self.remaining_shares < 0.0001:
            self.remaining_shares = 0
            self.is_closed = True

    def simulate(self):
        """Run the trade simulation with configured rules"""
        if self.price_df is None or len(self.price_df) == 0:
            # No price data
            self.execute_exit(self.entry_date, self.entry_price, self.remaining_shares, 'No Data')
            return self.get_summary()

        # Get price data starting from entry date
        trade_df = self.price_df[self.price_df.index >= self.entry_date]

        if len(trade_df) == 0:
            self.execute_exit(self.entry_date, self.entry_price, self.remaining_shares, 'No Data')
            return self.get_summary()

        max_hold_days = self.rules.get('max_hold_days', 120)

        # Process each trading day
        for date, row in trade_df.iterrows():
            if self.is_closed:
                break

            self.days_in_trade += 1
            high = row['high']
            low = row['low']
            close = row['close']

            # Track highest profit for trailing stop
            current_profit_pct = self.calculate_profit_pct(close)
            if current_profit_pct > self.highest_profit_pct:
                self.highest_profit_pct = current_profit_pct

            # Check stop loss (use intraday high/low)
            hit_stop = False
            if self.direction == 'LONG':
                if low <= self.stop_price:
                    self.execute_exit(date, self.stop_price, self.remaining_shares, 'Stop Loss')
                    hit_stop = True
            else:  # SHORT
                if high >= self.stop_price:
                    self.execute_exit(date, self.stop_price, self.remaining_shares, 'Stop Loss')
                    hit_stop = True

            if hit_stop or self.is_closed:
                break

            # FIX: Only check targets if no exit happened today
            if self.last_exit_date is not None and self.last_exit_date.date() == date.date():
                # Skip target checks - already exited today
                continue

            # Check profit targets (use intraday high for accuracy)
            profit_pct = self.calculate_profit_pct(high if self.direction == 'LONG' else low)

            # Target 1
            target1_pct = self.rules.get('target1_pct', 10)
            target1_size = self.rules.get('target1_size', 50) / 100

            if profit_pct >= target1_pct and len(self.exits) == 0:
                target_price = self.entry_price * (1 + target1_pct / 100) if self.direction == 'LONG' else self.entry_price * (1 - target1_pct / 100)
                shares_to_close = self.initial_shares * target1_size
                self.execute_exit(date, target_price, shares_to_close, f'Target 1 (+{target1_pct}%)')

                # Move stop to breakeven
                breakeven_trigger = self.rules.get('breakeven_trigger_pct', 5)
                if profit_pct >= breakeven_trigger:
                    self.update_stop_to_breakeven()

                # FIX: Skip further target checks this day
                continue

            # Target 2
            target2_pct = self.rules.get('target2_pct', 20)
            target2_size = self.rules.get('target2_size', 25) / 100

            if profit_pct >= target2_pct and len(self.exits) == 1:
                target_price = self.entry_price * (1 + target2_pct / 100) if self.direction == 'LONG' else self.entry_price * (1 - target2_pct / 100)
                shares_to_close = self.initial_shares * target2_size
                self.execute_exit(date, target_price, shares_to_close, f'Target 2 (+{target2_pct}%)')

                # Move stop to +3%
                self.update_stop_to_profit(3)

                # FIX: Skip T3 check this day
                continue

            # Target 3
            target3_pct = self.rules.get('target3_pct', 50)

            if profit_pct >= target3_pct and len(self.exits) == 2:
                target_price = self.entry_price * (1 + target3_pct / 100) if self.direction == 'LONG' else self.entry_price * (1 - target3_pct / 100)
                self.execute_exit(date, target_price, self.remaining_shares, f'Target 3 (+{target3_pct}%)')

                # Move stop to +10%
                self.update_stop_to_profit(10)

            # Update trailing stop if enabled
            self.update_trailing_stop(close)

            # Check max hold time
            if self.days_in_trade >= max_hold_days and self.remaining_shares > 0:
                self.execute_exit(date, close, self.remaining_shares, f'Max Hold ({max_hold_days} days)')
                break

        # Close any remaining position at end of data
        if self.remaining_shares > 0 and not self.is_closed:
            last_date = trade_df.index[-1]
            last_price = trade_df.iloc[-1]['close']
            self.execute_exit(last_date, last_price, self.remaining_shares, 'Data End')

        return self.get_summary()

    def get_summary(self):
        """Get trade summary"""
        total_pnl = sum([exit['pnl'] for exit in self.exits])
        total_pnl_pct = (total_pnl / self.initial_capital) * 100

        return {
            'ticker': self.ticker,
            'entry_date': self.entry_date,
            'entry_price': self.entry_price,
            'direction': self.direction,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'num_exits': len(self.exits),
            'days_in_trade': self.days_in_trade,
            'exits': self.exits,
            'highest_profit_pct': self.highest_profit_pct
        }


if __name__ == "__main__":
    # Test the validator
    print("Testing CorrectedTradeSimulator validators...\n")

    # Test 1: Valid rules
    try:
        signal = {
            'ticker': 'AAPL',
            'entry_date': '2024-01-01',
            'entry_price': 150.0,
            'direction': 'LONG',
            'initial_capital': 1000,
            'initial_shares': 6.67
        }

        valid_rules = {
            'initial_stop_pct': 5,
            'target1_pct': 10,
            'target1_size': 50,
            'target2_pct': 20,
            'target2_size': 25,
            'target3_pct': 50
        }

        sim = CorrectedTradeSimulator(signal, None, valid_rules)
        print("✅ Test 1 PASSED: Valid rules accepted")
    except Exception as e:
        print(f"❌ Test 1 FAILED: {e}")

    # Test 2: Invalid T2 <= T1
    try:
        invalid_rules = valid_rules.copy()
        invalid_rules['target2_pct'] = 10  # Same as T1
        sim = CorrectedTradeSimulator(signal, None, invalid_rules)
        print("❌ Test 2 FAILED: Should have rejected T2=T1")
    except ValueError as e:
        print(f"✅ Test 2 PASSED: Correctly rejected T2=T1 - {e}")

    # Test 3: Invalid T2 < T1
    try:
        invalid_rules = valid_rules.copy()
        invalid_rules['target2_pct'] = 8  # Less than T1
        sim = CorrectedTradeSimulator(signal, None, invalid_rules)
        print("❌ Test 3 FAILED: Should have rejected T2<T1")
    except ValueError as e:
        print(f"✅ Test 3 PASSED: Correctly rejected T2<T1 - {e}")

    # Test 4: Invalid T3 <= T2
    try:
        invalid_rules = valid_rules.copy()
        invalid_rules['target3_pct'] = 20  # Same as T2
        sim = CorrectedTradeSimulator(signal, None, invalid_rules)
        print("❌ Test 4 FAILED: Should have rejected T3=T2")
    except ValueError as e:
        print(f"✅ Test 4 PASSED: Correctly rejected T3=T2 - {e}")

    # Test 5: Invalid position sizing > 100%
    try:
        invalid_rules = valid_rules.copy()
        invalid_rules['target1_size'] = 70
        invalid_rules['target2_size'] = 40  # 70 + 40 = 110%
        sim = CorrectedTradeSimulator(signal, None, invalid_rules)
        print("❌ Test 5 FAILED: Should have rejected total sizing > 100%")
    except ValueError as e:
        print(f"✅ Test 5 PASSED: Correctly rejected oversizing - {e}")

    print("\n" + "="*70)
    print("VALIDATOR TESTS COMPLETE")
    print("="*70)
