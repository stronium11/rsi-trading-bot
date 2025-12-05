#!/usr/bin/env python3
"""
Entry Price Optimizer
Tests different entry timing strategies to find optimal entry points
Uses optimized exit rules from iterative optimizer
"""

import pandas as pd
import numpy as np
import ast
import os
from datetime import datetime, timedelta
from iterative_optimizer import PriceDataCache
from corrected_trade_simulator import CorrectedTradeSimulator
import time


class EntryPriceOptimizer:
    """
    Tests different entry price strategies on actual backtest signals
    """

    def __init__(self, signals_csv=None):
        """Initialize optimizer"""
        # Default to path relative to this script's location
        script_dir = os.path.dirname(os.path.abspath(__file__))

        if signals_csv is None:
            signals_csv = os.path.join(script_dir, 'backtest', 'backtest_signals.csv')

        self.signals_csv = signals_csv
        self.signals_df = None

        # Initialize cache with correct path
        cache_dir = os.path.join(script_dir, 'backtest', 'price_cache')
        self.cache = PriceDataCache(cache_dir=cache_dir)

        # Optimized exit rules from iterative optimizer
        self.optimal_exit_rules = {
            'initial_stop_pct': 7,
            'target1_pct': 15,
            'target1_size': 70,
            'target2_pct': 18,
            'target2_size': 15,
            'target3_pct': 50,
            'breakeven_trigger_pct': 5,
            'max_hold_days': 120,
            'use_trailing_stop': False
        }

    def load_signals(self):
        """Load backtest signals"""
        print("Loading backtest signals...")
        self.signals_df = pd.read_csv(self.signals_csv)

        # Parse dates
        self.signals_df['signal_date'] = pd.to_datetime(self.signals_df['signal_date'])
        self.signals_df['entry_date'] = pd.to_datetime(self.signals_df['entry_date'])

        print(f"Loaded {len(self.signals_df)} signals\n")

    def ensure_signal_day_in_data(self, ticker, signal_date, price_df):
        """
        Ensure signal day is in price data by fetching if needed

        Returns updated price_df with signal day included
        """
        if price_df is None:
            return None

        # Check if signal_date is already in the data
        if signal_date in price_df.index:
            return price_df

        # Need to fetch signal day data
        from data_fetcher import get_data_fetcher
        fetcher = get_data_fetcher()

        try:
            # Fetch a small range around signal date to get that day
            start = signal_date - timedelta(days=5)
            end = signal_date + timedelta(days=5)

            signal_df = fetcher.fetch_historical_data(
                ticker,
                start_date=start,
                end_date=end,
                interval='1day'
            )

            if signal_df is not None and signal_date in signal_df.index:
                # Get just the signal day
                signal_day = signal_df.loc[[signal_date]]
                # Prepend to existing data
                price_df = pd.concat([signal_day, price_df])
                # Remove duplicates and sort
                price_df = price_df[~price_df.index.duplicated(keep='first')]
                price_df = price_df.sort_index()

        except Exception as e:
            print(f"    Warning: Could not fetch signal day for {ticker}: {e}")

        return price_df

    def get_entry_price_methods(self, signal, price_df):
        """
        Calculate different entry prices for a given signal

        Returns dict of entry method name -> entry price
        """
        signal_date = pd.to_datetime(signal['signal_date'])
        entry_date = pd.to_datetime(signal['entry_date'])  # Next day after signal
        divergence_type = signal['divergence_type']

        # Derive direction from divergence_type
        direction = 'LONG' if divergence_type == 'Bullish' else 'SHORT'

        # Get signal day data
        signal_day = price_df[price_df.index == signal_date]
        if len(signal_day) == 0:
            return None

        signal_close = signal_day.iloc[0]['close']
        signal_high = signal_day.iloc[0]['high']
        signal_low = signal_day.iloc[0]['low']

        # Get entry day data (next day)
        entry_day = price_df[price_df.index == entry_date]
        if len(entry_day) == 0:
            return None

        entry_open = entry_day.iloc[0]['open']
        entry_close = entry_day.iloc[0]['close']
        entry_high = entry_day.iloc[0]['high']
        entry_low = entry_day.iloc[0]['low']

        # Get next 3 days for pullback strategy
        next_3_days = price_df[price_df.index > signal_date].head(3)

        entry_methods = {}

        # Method 1: Current (entry day close - baseline)
        entry_methods['Current (Entry Close)'] = entry_close

        # Method 2: Entry day open
        entry_methods['Entry Day Open'] = entry_open

        # Method 3: Limit order at 0.5% discount
        if direction == 'LONG':
            limit_price = signal_close * 0.995
            # Check if limit would have been filled next day (price touched it)
            if entry_low <= limit_price:
                entry_methods['Limit -0.5%'] = limit_price
            else:
                # Not filled, enter at close on day 2
                entry_methods['Limit -0.5%'] = entry_close
        else:  # SHORT
            limit_price = signal_close * 1.005
            if entry_high >= limit_price:
                entry_methods['Limit -0.5%'] = limit_price
            else:
                entry_methods['Limit -0.5%'] = entry_close

        # Method 4: Limit order at 1.0% discount
        if direction == 'LONG':
            limit_price = signal_close * 0.99
            if entry_low <= limit_price:
                entry_methods['Limit -1.0%'] = limit_price
            else:
                entry_methods['Limit -1.0%'] = entry_close
        else:  # SHORT
            limit_price = signal_close * 1.01
            if entry_high >= limit_price:
                entry_methods['Limit -1.0%'] = limit_price
            else:
                entry_methods['Limit -1.0%'] = entry_close

        # Method 5: Limit order at 1.5% discount
        if direction == 'LONG':
            limit_price = signal_close * 0.985
            if entry_low <= limit_price:
                entry_methods['Limit -1.5%'] = limit_price
            else:
                entry_methods['Limit -1.5%'] = entry_close
        else:  # SHORT
            limit_price = signal_close * 1.015
            if entry_high >= limit_price:
                entry_methods['Limit -1.5%'] = limit_price
            else:
                entry_methods['Limit -1.5%'] = entry_close

        # Method 6: Signal day low/high
        if direction == 'LONG':
            entry_methods['Signal Day Low'] = signal_low
        else:  # SHORT
            entry_methods['Signal Day High'] = signal_high

        # Method 7: Best price in next 3 days
        if len(next_3_days) > 0:
            if direction == 'LONG':
                best_price = next_3_days['low'].min()
                entry_methods['Best in 3 Days'] = best_price
            else:  # SHORT
                best_price = next_3_days['high'].max()
                entry_methods['Best in 3 Days'] = best_price

        return entry_methods

    def test_entry_strategy(self, strategy_name):
        """
        Test a specific entry strategy on all signals

        Returns performance metrics
        """
        results = []
        skipped_no_cache = 0
        skipped_no_methods = 0
        debug_first = True  # Debug first failure

        for idx, row in self.signals_df.iterrows():
            # Load cached price data (cached by entry_date)
            price_df = self.cache.load(row['ticker'], row['entry_date'])

            if price_df is None:
                # Skip if no price data
                skipped_no_cache += 1
                continue

            # Ensure signal day is in the data (may need to fetch)
            price_df = self.ensure_signal_day_in_data(row['ticker'], row['signal_date'], price_df)

            if price_df is None:
                skipped_no_cache += 1
                continue

            # Get all entry methods for this signal
            entry_methods = self.get_entry_price_methods(row, price_df)

            if entry_methods is None or strategy_name not in entry_methods:
                skipped_no_methods += 1
                # Debug first failure
                if debug_first:
                    print(f"\n  DEBUG FIRST FAILURE:")
                    print(f"    Ticker: {row['ticker']}")
                    print(f"    Signal Date: {row['signal_date']} (type: {type(row['signal_date'])})")
                    print(f"    Entry Date: {row['entry_date']}")
                    print(f"    Price DF date range: {price_df.index.min()} to {price_df.index.max()}")
                    print(f"    Price DF index type: {type(price_df.index)}")
                    print(f"    Entry methods returned: {entry_methods}")
                    debug_first = False
                continue

            # Use the specific entry price for this strategy
            entry_price = entry_methods[strategy_name]

            # Calculate position sizing based on entry price
            initial_capital = min(1000, entry_price)
            initial_shares = initial_capital / entry_price

            # Derive direction from divergence_type
            direction = 'LONG' if row['divergence_type'] == 'Bullish' else 'SHORT'

            # Create signal with this entry method
            signal = {
                'ticker': row['ticker'],
                'entry_date': row['entry_date'],
                'entry_price': entry_price,
                'direction': direction,
                'initial_capital': initial_capital,
                'initial_shares': initial_shares
            }

            # Simulate trade with optimized exit rules
            simulator = CorrectedTradeSimulator(signal, price_df, self.optimal_exit_rules)
            result = simulator.simulate()

            # Add metadata
            result['timeframe'] = row['timeframe']
            result['divergence_type'] = row['divergence_type']

            results.append(result)

        # Debug output
        print(f"  Debug: Processed {len(self.signals_df)} total signals")
        print(f"  Debug: Skipped {skipped_no_cache} signals (no price cache)")
        print(f"  Debug: Skipped {skipped_no_methods} signals (no entry methods)")
        print(f"  Debug: Successfully collected {len(results)} trade results")

        # Check for empty results
        if len(results) == 0:
            print(f"  ERROR: No results collected for strategy '{strategy_name}'")
            print(f"  Possible causes:")
            print(f"    - Price cache not found (check cache path)")
            print(f"    - Entry methods returning None for all signals")
            print(f"    - Strategy name mismatch in entry_methods dict")
            return {
                'strategy': strategy_name,
                'total_pnl': 0,
                'total_trades': 0,
                'winners': 0,
                'win_rate': 0,
                'avg_winner': 0,
                'avg_loser': 0,
                'profit_factor': 0,
                'avg_pnl_per_trade': 0
            }

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
            'strategy': strategy_name,
            'total_pnl': total_pnl,
            'total_trades': total_trades,
            'winners': winners,
            'win_rate': win_rate,
            'avg_winner': avg_winner,
            'avg_loser': avg_loser,
            'profit_factor': profit_factor,
            'avg_pnl_per_trade': total_pnl / total_trades if total_trades > 0 else 0
        }

    def run_all_entry_tests(self):
        """
        Test all entry strategies
        """
        print("="*70)
        print("ENTRY PRICE OPTIMIZATION")
        print("="*70)
        print("\nUsing OPTIMIZED exit rules:")
        print(f"  Stop: -7%")
        print(f"  T1: +15% (close 70%)")
        print(f"  T2: +18% (close 15%)")
        print(f"  T3: +50% (close 15%)")
        print(f"  Max hold: 120 days")
        print()

        strategies = [
            'Current (Entry Close)',
            'Entry Day Open',
            'Limit -0.5%',
            'Limit -1.0%',
            'Limit -1.5%',
            'Signal Day Low',
            'Best in 3 Days'
        ]

        results = []

        for i, strategy in enumerate(strategies, 1):
            print(f"\n[{i}/{len(strategies)}] Testing: {strategy}")
            print(f"{'='*70}")

            start = time.time()
            result = self.test_entry_strategy(strategy)
            elapsed = time.time() - start

            results.append(result)

            print(f"  Total P&L: ${result['total_pnl']:,.2f}")
            print(f"  Win Rate: {result['win_rate']:.1f}%")
            print(f"  Profit Factor: {result['profit_factor']:.2f}")
            print(f"  Avg per Trade: ${result['avg_pnl_per_trade']:.2f}")
            print(f"  Completed in {elapsed:.1f}s")

        # Print comparison
        self.print_comparison(results)

        return results

    def print_comparison(self, results):
        """Print detailed comparison"""
        print("\n" + "="*70)
        print("ENTRY STRATEGY COMPARISON")
        print("="*70)

        baseline = results[0]  # Current entry method

        for result in results:
            is_baseline = result['strategy'] == 'Current (Entry Close)'

            print(f"\n{result['strategy']}")
            print("-" * 70)

            print(f"Total P&L: ${result['total_pnl']:,.2f}", end='')
            if not is_baseline:
                diff = result['total_pnl'] - baseline['total_pnl']
                pct_change = (diff / baseline['total_pnl'] * 100) if baseline['total_pnl'] != 0 else 0
                indicator = "✅" if diff > 0 else "❌"
                print(f"  ({diff:+,.2f}, {pct_change:+.1f}%) {indicator}")
            else:
                print(" [BASELINE]")

            print(f"Win Rate: {result['win_rate']:.1f}%", end='')
            if not is_baseline:
                diff = result['win_rate'] - baseline['win_rate']
                indicator = "✅" if diff > 0 else "❌"
                print(f"  ({diff:+.1f}%) {indicator}")
            else:
                print()

            print(f"Profit Factor: {result['profit_factor']:.2f}", end='')
            if not is_baseline:
                diff = result['profit_factor'] - baseline['profit_factor']
                indicator = "✅" if diff > 0 else "❌"
                print(f"  ({diff:+.2f}) {indicator}")
            else:
                print()

            print(f"Avg per Trade: ${result['avg_pnl_per_trade']:.2f}", end='')
            if not is_baseline:
                diff = result['avg_pnl_per_trade'] - baseline['avg_pnl_per_trade']
                indicator = "✅" if diff > 0 else "❌"
                print(f"  ({diff:+.2f}) {indicator}")
            else:
                print()

        # Find best
        print("\n" + "="*70)
        print("WINNER")
        print("="*70)

        best = max([r for r in results if r['strategy'] != 'Current (Entry Close)'],
                   key=lambda x: x['total_pnl'])

        print(f"\n🏆 BEST ENTRY STRATEGY: {best['strategy']}")
        print(f"   Total P&L: ${best['total_pnl']:,.2f} (vs ${baseline['total_pnl']:,.2f})")

        improvement = best['total_pnl'] - baseline['total_pnl']
        improvement_pct = (improvement / baseline['total_pnl'] * 100) if baseline['total_pnl'] != 0 else 0

        print(f"   Improvement: +${improvement:,.2f} (+{improvement_pct:.1f}%)")
        print(f"   Win Rate: {best['win_rate']:.1f}% (vs {baseline['win_rate']:.1f}%)")
        print(f"   Profit Factor: {best['profit_factor']:.2f} (vs {baseline['profit_factor']:.2f})")

        print(f"\n💡 COMBINED OPTIMIZATION:")
        print(f"   Optimized exits alone: +19.9% improvement")
        print(f"   Optimized entry: +{improvement_pct:.1f}% additional")
        print(f"   Total potential: ~{19.9 + improvement_pct:.1f}% improvement")


if __name__ == "__main__":
    optimizer = EntryPriceOptimizer()
    optimizer.load_signals()
    optimizer.run_all_entry_tests()
