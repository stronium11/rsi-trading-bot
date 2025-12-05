#!/usr/bin/env python3
"""
Advanced Rule Optimizer
Fetches actual price data for each trade and simulates alternative position management rules
Tests different stops, targets, and position sizing with precise results
"""

import pandas as pd
import numpy as np
import ast
from datetime import datetime, timedelta
from data_fetcher import get_data_fetcher
import time
import os


class TradeSimulator:
    """
    Simulates a single trade with configurable rules
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

        # Position tracking
        self.remaining_shares = self.initial_shares
        self.exits = []
        self.days_in_trade = 0
        self.is_closed = False

        # Stop loss tracking
        self.stop_price = self.calculate_initial_stop()
        self.highest_profit_pct = 0

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

            # Target 2
            target2_pct = self.rules.get('target2_pct', 20)
            target2_size = self.rules.get('target2_size', 25) / 100

            if profit_pct >= target2_pct and len(self.exits) == 1:
                target_price = self.entry_price * (1 + target2_pct / 100) if self.direction == 'LONG' else self.entry_price * (1 - target2_pct / 100)
                shares_to_close = self.initial_shares * target2_size
                self.execute_exit(date, target_price, shares_to_close, f'Target 2 (+{target2_pct}%)')

                # Move stop to +3%
                self.update_stop_to_profit(3)

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


class AdvancedRuleOptimizer:
    """
    Tests alternative position management rules using actual price data
    """

    def __init__(self, results_csv='backtest/backtest_results.csv'):
        """Initialize optimizer"""
        self.results_csv = results_csv
        self.df = None
        self.data_fetcher = get_data_fetcher()
        self.baseline_rules = {
            'initial_stop_pct': 5,
            'target1_pct': 10,
            'target1_size': 50,
            'target2_pct': 20,
            'target2_size': 25,
            'target3_pct': 50,
            'breakeven_trigger_pct': 5,
            'max_hold_days': 120,
            'use_trailing_stop': False
        }

    def load_data(self):
        """Load backtest results"""
        print("Loading backtest results...")
        self.df = pd.read_csv(self.results_csv)

        # Parse exits column
        def safe_eval_exits(exits_str):
            safe_dict = {
                'Timestamp': pd.Timestamp,
                'np': np,
                '__builtins__': {}
            }
            try:
                return eval(exits_str, safe_dict)
            except:
                return []

        self.df['exits'] = self.df['exits'].apply(safe_eval_exits)
        self.df['signal_date'] = pd.to_datetime(self.df['signal_date'])
        self.df['entry_date'] = pd.to_datetime(self.df['entry_date'])

        print(f"Loaded {len(self.df)} trades\n")

    def test_rule_set(self, rules, rule_name, sample_size=None):
        """
        Test a specific rule set on all trades

        Parameters:
        - rules: Dictionary of rules
        - rule_name: Name for this scenario
        - sample_size: If set, only test on first N trades (for speed)
        """
        print(f"\nTesting: {rule_name}")
        print(f"Rules: {rules}")
        print("Fetching price data and simulating trades...")

        trades_to_test = self.df.head(sample_size) if sample_size else self.df
        results = []

        for idx, row in trades_to_test.iterrows():
            # Fetch price data for this trade
            start_date = row['entry_date']
            end_date = start_date + timedelta(days=rules.get('max_hold_days', 120) + 30)

            try:
                price_df = self.data_fetcher.fetch_historical_data(
                    row['ticker'],
                    start_date=start_date,
                    end_date=end_date,
                    interval='1day'
                )

                # Simulate trade with new rules
                signal = {
                    'ticker': row['ticker'],
                    'entry_date': row['entry_date'],
                    'entry_price': row['entry_price'],
                    'direction': row['direction'],
                    'initial_capital': row['initial_capital'],
                    'initial_shares': row['initial_shares']
                }

                simulator = TradeSimulator(signal, price_df, rules)
                result = simulator.simulate()
                results.append(result)

            except Exception as e:
                # If we can't fetch data, use original result
                results.append({
                    'ticker': row['ticker'],
                    'total_pnl': row['total_pnl'],
                    'total_pnl_pct': row['total_pnl_pct']
                })

            # Progress indicator
            if (idx + 1) % 20 == 0:
                print(f"  Processed {idx + 1}/{len(trades_to_test)} trades...")

        # Calculate metrics
        results_df = pd.DataFrame(results)
        total_pnl = results_df['total_pnl'].sum()
        total_trades = len(results_df)
        winners = len(results_df[results_df['total_pnl'] > 0])
        win_rate = (winners / total_trades) * 100 if total_trades > 0 else 0

        avg_winner = results_df[results_df['total_pnl'] > 0]['total_pnl'].mean() if winners > 0 else 0
        avg_loser = results_df[results_df['total_pnl'] <= 0]['total_pnl'].mean() if (total_trades - winners) > 0 else 0

        total_wins = results_df[results_df['total_pnl'] > 0]['total_pnl'].sum()
        total_losses = abs(results_df[results_df['total_pnl'] <= 0]['total_pnl'].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        return {
            'name': rule_name,
            'total_pnl': total_pnl,
            'total_trades': total_trades,
            'winners': winners,
            'win_rate': win_rate,
            'avg_winner': avg_winner,
            'avg_loser': avg_loser,
            'profit_factor': profit_factor,
            'avg_pnl_per_trade': total_pnl / total_trades if total_trades > 0 else 0
        }

    def run_optimization_suite(self, sample_size=50):
        """
        Run comprehensive optimization tests

        Parameters:
        - sample_size: Number of trades to test (50 = fast, None = all 434 trades)
        """
        print("="*70)
        print("ADVANCED RULE OPTIMIZATION")
        print(f"Testing on {sample_size if sample_size else 'all'} trades")
        print("="*70)

        scenarios = []

        # Baseline (current rules)
        print("\n[1/9] Baseline - Current Rules")
        scenarios.append(self.test_rule_set(self.baseline_rules, "Baseline (Current Rules)", sample_size))

        # Test 1: Wider stop loss
        print("\n[2/9] Test 1 - Wider Stop (-7%)")
        rules_wider_stop = self.baseline_rules.copy()
        rules_wider_stop['initial_stop_pct'] = 7
        scenarios.append(self.test_rule_set(rules_wider_stop, "Wider Stop (-7%)", sample_size))

        # Test 2: Tighter stop loss
        print("\n[3/9] Test 2 - Tighter Stop (-3%)")
        rules_tighter_stop = self.baseline_rules.copy()
        rules_tighter_stop['initial_stop_pct'] = 3
        scenarios.append(self.test_rule_set(rules_tighter_stop, "Tighter Stop (-3%)", sample_size))

        # Test 3: Lower Target 3
        print("\n[4/9] Test 3 - Lower Target 3 (+35%)")
        rules_lower_t3 = self.baseline_rules.copy()
        rules_lower_t3['target3_pct'] = 35
        scenarios.append(self.test_rule_set(rules_lower_t3, "Lower T3 to +35%", sample_size))

        # Test 4: More aggressive Target 3
        print("\n[5/9] Test 4 - Lower Target 3 (+30%)")
        rules_lower_t3_30 = self.baseline_rules.copy()
        rules_lower_t3_30['target3_pct'] = 30
        scenarios.append(self.test_rule_set(rules_lower_t3_30, "Lower T3 to +30%", sample_size))

        # Test 5: Take more profit at T1
        print("\n[6/9] Test 5 - Take 60% at T1 (instead of 50%)")
        rules_more_t1 = self.baseline_rules.copy()
        rules_more_t1['target1_size'] = 60
        rules_more_t1['target2_size'] = 20
        scenarios.append(self.test_rule_set(rules_more_t1, "Take 60% at T1", sample_size))

        # Test 6: Trailing stop
        print("\n[7/9] Test 6 - Add 10% Trailing Stop")
        rules_trailing = self.baseline_rules.copy()
        rules_trailing['use_trailing_stop'] = True
        rules_trailing['trailing_stop_pct'] = 10
        scenarios.append(self.test_rule_set(rules_trailing, "10% Trailing Stop", sample_size))

        # Test 7: Combination - Wider stop + Lower T3
        print("\n[8/9] Test 7 - Combo: Wider Stop + Lower T3")
        rules_combo1 = self.baseline_rules.copy()
        rules_combo1['initial_stop_pct'] = 7
        rules_combo1['target3_pct'] = 35
        scenarios.append(self.test_rule_set(rules_combo1, "Combo: -7% stop + T3 at 35%", sample_size))

        # Test 8: Best combo
        print("\n[9/9] Test 8 - Best Combo: Wider Stop + Lower T3 + More at T1")
        rules_best = self.baseline_rules.copy()
        rules_best['initial_stop_pct'] = 7
        rules_best['target3_pct'] = 35
        rules_best['target1_size'] = 60
        rules_best['target2_size'] = 20
        scenarios.append(self.test_rule_set(rules_best, "Best Combo", sample_size))

        # Print comparison
        self.print_comparison(scenarios)

        return scenarios

    def print_comparison(self, scenarios):
        """Print scenario comparison"""
        print("\n" + "="*70)
        print("OPTIMIZATION RESULTS")
        print("="*70)

        baseline = scenarios[0]

        for scenario in scenarios:
            is_baseline = scenario['name'] == "Baseline (Current Rules)"

            print(f"\n{scenario['name']}")
            print("-" * 70)

            print(f"Total P&L: ${scenario['total_pnl']:,.2f}", end='')
            if not is_baseline:
                diff = scenario['total_pnl'] - baseline['total_pnl']
                pct_change = (diff / baseline['total_pnl'] * 100) if baseline['total_pnl'] != 0 else 0
                indicator = "✅" if diff > 0 else "❌"
                print(f"  ({diff:+,.2f}, {pct_change:+.1f}%) {indicator}")
            else:
                print(" [BASELINE]")

            print(f"Win Rate: {scenario['win_rate']:.1f}%", end='')
            if not is_baseline:
                diff = scenario['win_rate'] - baseline['win_rate']
                indicator = "✅" if diff > 0 else "❌"
                print(f"  ({diff:+.1f}%) {indicator}")
            else:
                print()

            print(f"Profit Factor: {scenario['profit_factor']:.2f}", end='')
            if not is_baseline:
                diff = scenario['profit_factor'] - baseline['profit_factor']
                indicator = "✅" if diff > 0 else "❌"
                print(f"  ({diff:+.2f}) {indicator}")
            else:
                print()

            print(f"Avg per Trade: ${scenario['avg_pnl_per_trade']:.2f}", end='')
            if not is_baseline:
                diff = scenario['avg_pnl_per_trade'] - baseline['avg_pnl_per_trade']
                indicator = "✅" if diff > 0 else "❌"
                print(f"  ({diff:+.2f}) {indicator}")
            else:
                print()

        # Find best
        print("\n" + "="*70)
        print("WINNER")
        print("="*70)

        best = max([s for s in scenarios if s['name'] != "Baseline (Current Rules)"],
                   key=lambda x: x['total_pnl'])

        print(f"\n🏆 Best Rule Set: {best['name']}")
        print(f"   Total P&L: ${best['total_pnl']:,.2f} (vs ${baseline['total_pnl']:,.2f})")
        improvement = best['total_pnl'] - baseline['total_pnl']
        improvement_pct = (improvement / baseline['total_pnl'] * 100) if baseline['total_pnl'] != 0 else 0
        print(f"   Improvement: +${improvement:,.2f} (+{improvement_pct:.1f}%)")
        print(f"   Win Rate: {best['win_rate']:.1f}% (vs {baseline['win_rate']:.1f}%)")
        print(f"   Profit Factor: {best['profit_factor']:.2f} (vs {baseline['profit_factor']:.2f})")


if __name__ == "__main__":
    import sys

    # Allow user to specify sample size
    sample_size = 50  # Default: test on 50 trades for speed

    if len(sys.argv) > 1:
        if sys.argv[1] == 'all':
            sample_size = None
            print("Testing on ALL 434 trades (this will take 15-20 minutes)")
        else:
            sample_size = int(sys.argv[1])
            print(f"Testing on {sample_size} trades")
    else:
        print(f"Testing on {sample_size} trades (use 'python3 advanced_rule_optimizer.py all' for all trades)")

    print()

    optimizer = AdvancedRuleOptimizer()
    optimizer.load_data()
    optimizer.run_optimization_suite(sample_size=sample_size)
