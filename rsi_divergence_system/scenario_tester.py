#!/usr/bin/env python3
"""
Advanced Scenario Tester
Tests alternative position management rules on actual backtest data
"""

import pandas as pd
import numpy as np
import ast
from datetime import datetime, timedelta


class ScenarioTester:
    """
    Tests different position management scenarios on historical trades
    """

    def __init__(self, results_csv='backtest/backtest_results.csv'):
        """Initialize with backtest results"""
        self.results_csv = results_csv
        self.df = None
        self.baseline_metrics = {}
        self.scenarios = []

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
            except Exception as e:
                return []

        self.df['exits'] = self.df['exits'].apply(safe_eval_exits)
        self.df['signal_date'] = pd.to_datetime(self.df['signal_date'])
        self.df['entry_date'] = pd.to_datetime(self.df['entry_date'])

        print(f"Loaded {len(self.df)} trades\n")

    def calculate_baseline(self):
        """Calculate current system performance"""
        total_pnl = self.df['total_pnl'].sum()
        total_trades = len(self.df)
        winners = len(self.df[self.df['total_pnl'] > 0])
        losers = len(self.df[self.df['total_pnl'] <= 0])
        win_rate = (winners / total_trades) * 100

        avg_winner = self.df[self.df['total_pnl'] > 0]['total_pnl'].mean()
        avg_loser = self.df[self.df['total_pnl'] <= 0]['total_pnl'].mean()

        total_wins = self.df[self.df['total_pnl'] > 0]['total_pnl'].sum()
        total_losses = abs(self.df[self.df['total_pnl'] <= 0]['total_pnl'].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        self.baseline_metrics = {
            'name': 'Current System',
            'total_pnl': total_pnl,
            'total_trades': total_trades,
            'winners': winners,
            'losers': losers,
            'win_rate': win_rate,
            'avg_winner': avg_winner,
            'avg_loser': avg_loser,
            'profit_factor': profit_factor,
            'avg_pnl_per_trade': total_pnl / total_trades
        }

        return self.baseline_metrics

    def scenario_filter_best_setups(self):
        """Scenario: Only trade best performing setups"""
        # Based on analysis: 1d Bullish (43.6% WR) and 3d Bearish (42.3% WR)
        filtered = self.df[
            ((self.df['timeframe'] == '1d') & (self.df['divergence_type'] == 'Bullish')) |
            ((self.df['timeframe'] == '3d') & (self.df['divergence_type'] == 'Bearish'))
        ]

        total_pnl = filtered['total_pnl'].sum()
        total_trades = len(filtered)
        winners = len(filtered[filtered['total_pnl'] > 0])
        win_rate = (winners / total_trades) * 100 if total_trades > 0 else 0

        avg_winner = filtered[filtered['total_pnl'] > 0]['total_pnl'].mean()
        avg_loser = filtered[filtered['total_pnl'] <= 0]['total_pnl'].mean()

        total_wins = filtered[filtered['total_pnl'] > 0]['total_pnl'].sum()
        total_losses = abs(filtered[filtered['total_pnl'] <= 0]['total_pnl'].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        return {
            'name': 'Only Best Setups (1d Bullish + 3d Bearish)',
            'total_pnl': total_pnl,
            'total_trades': total_trades,
            'winners': winners,
            'losers': total_trades - winners,
            'win_rate': win_rate,
            'avg_winner': avg_winner,
            'avg_loser': avg_loser,
            'profit_factor': profit_factor,
            'avg_pnl_per_trade': total_pnl / total_trades if total_trades > 0 else 0,
            'trades_filtered_out': len(self.df) - total_trades
        }

    def scenario_cap_hold_time(self, max_days=60):
        """Scenario: Cap maximum hold time"""
        # Simulate what would happen if we closed all positions at max_days
        # Note: This is an approximation since we don't have intraday price data

        modified_pnl = 0
        trades_affected = 0

        for idx, row in self.df.iterrows():
            if row['days_in_trade'] <= max_days:
                # Trade finished within limit, use actual P&L
                modified_pnl += row['total_pnl']
            else:
                # Trade would have been closed at max_days
                # Estimate P&L based on exits that occurred before max_days
                trades_affected += 1

                pnl_so_far = 0
                for exit in row['exits']:
                    # We don't have exact dates, so we estimate
                    # Assume exits are evenly distributed over the trade duration
                    pnl_so_far += exit.get('pnl', 0)

                # For trades that went long, assume we'd capture partial profit
                # This is a rough estimate
                estimated_pnl = pnl_so_far * (max_days / row['days_in_trade'])
                modified_pnl += estimated_pnl

        # Recalculate metrics
        # Note: Win rate estimate is rough since we're estimating P&L
        estimated_winners = int(self.baseline_metrics['winners'] * 0.5)  # Conservative estimate
        total_trades = len(self.df)

        return {
            'name': f'Cap Hold Time at {max_days} Days',
            'total_pnl': modified_pnl,
            'total_trades': total_trades,
            'winners': estimated_winners,
            'losers': total_trades - estimated_winners,
            'win_rate': (estimated_winners / total_trades) * 100,
            'avg_winner': 0,  # Can't accurately estimate without full data
            'avg_loser': 0,
            'profit_factor': 0,
            'avg_pnl_per_trade': modified_pnl / total_trades,
            'trades_affected': trades_affected,
            'note': 'Estimated based on partial data - actual results may vary'
        }

    def scenario_exclude_weak_setups(self):
        """Scenario: Exclude worst performing setups"""
        # Exclude 1d Bearish (33.5% WR) and 3d Bullish (30.4% WR)
        filtered = self.df[
            ~(((self.df['timeframe'] == '1d') & (self.df['divergence_type'] == 'Bearish')) |
              ((self.df['timeframe'] == '3d') & (self.df['divergence_type'] == 'Bullish')))
        ]

        total_pnl = filtered['total_pnl'].sum()
        total_trades = len(filtered)
        winners = len(filtered[filtered['total_pnl'] > 0])
        win_rate = (winners / total_trades) * 100 if total_trades > 0 else 0

        avg_winner = filtered[filtered['total_pnl'] > 0]['total_pnl'].mean()
        avg_loser = filtered[filtered['total_pnl'] <= 0]['total_pnl'].mean()

        total_wins = filtered[filtered['total_pnl'] > 0]['total_pnl'].sum()
        total_losses = abs(filtered[filtered['total_pnl'] <= 0]['total_pnl'].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        return {
            'name': 'Exclude Weak Setups (1d Bearish + 3d Bullish)',
            'total_pnl': total_pnl,
            'total_trades': total_trades,
            'winners': winners,
            'losers': total_trades - winners,
            'win_rate': win_rate,
            'avg_winner': avg_winner,
            'avg_loser': avg_loser,
            'profit_factor': profit_factor,
            'avg_pnl_per_trade': total_pnl / total_trades if total_trades > 0 else 0,
            'trades_filtered_out': len(self.df) - total_trades
        }

    def scenario_only_timeframe(self, timeframe):
        """Scenario: Only trade specific timeframe"""
        filtered = self.df[self.df['timeframe'] == timeframe]

        total_pnl = filtered['total_pnl'].sum()
        total_trades = len(filtered)
        winners = len(filtered[filtered['total_pnl'] > 0])
        win_rate = (winners / total_trades) * 100 if total_trades > 0 else 0

        avg_winner = filtered[filtered['total_pnl'] > 0]['total_pnl'].mean() if winners > 0 else 0
        avg_loser = filtered[filtered['total_pnl'] <= 0]['total_pnl'].mean() if (total_trades - winners) > 0 else 0

        total_wins = filtered[filtered['total_pnl'] > 0]['total_pnl'].sum()
        total_losses = abs(filtered[filtered['total_pnl'] <= 0]['total_pnl'].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        return {
            'name': f'Only {timeframe} Timeframe',
            'total_pnl': total_pnl,
            'total_trades': total_trades,
            'winners': winners,
            'losers': total_trades - winners,
            'win_rate': win_rate,
            'avg_winner': avg_winner,
            'avg_loser': avg_loser,
            'profit_factor': profit_factor,
            'avg_pnl_per_trade': total_pnl / total_trades if total_trades > 0 else 0
        }

    def scenario_only_divergence_type(self, div_type):
        """Scenario: Only trade specific divergence type"""
        filtered = self.df[self.df['divergence_type'] == div_type]

        total_pnl = filtered['total_pnl'].sum()
        total_trades = len(filtered)
        winners = len(filtered[filtered['total_pnl'] > 0])
        win_rate = (winners / total_trades) * 100 if total_trades > 0 else 0

        avg_winner = filtered[filtered['total_pnl'] > 0]['total_pnl'].mean() if winners > 0 else 0
        avg_loser = filtered[filtered['total_pnl'] <= 0]['total_pnl'].mean() if (total_trades - winners) > 0 else 0

        total_wins = filtered[filtered['total_pnl'] > 0]['total_pnl'].sum()
        total_losses = abs(filtered[filtered['total_pnl'] <= 0]['total_pnl'].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        return {
            'name': f'Only {div_type} Divergences',
            'total_pnl': total_pnl,
            'total_trades': total_trades,
            'winners': winners,
            'losers': total_trades - winners,
            'win_rate': win_rate,
            'avg_winner': avg_winner,
            'avg_loser': avg_loser,
            'profit_factor': profit_factor,
            'avg_pnl_per_trade': total_pnl / total_trades if total_trades > 0 else 0
        }

    def run_all_scenarios(self):
        """Run all scenario tests"""
        print("="*70)
        print("SCENARIO TESTING")
        print("="*70)
        print()

        # Calculate baseline
        baseline = self.calculate_baseline()
        self.scenarios.append(baseline)

        # Run scenarios
        print("Running scenario tests...\n")

        self.scenarios.append(self.scenario_filter_best_setups())
        self.scenarios.append(self.scenario_exclude_weak_setups())
        self.scenarios.append(self.scenario_cap_hold_time(60))
        self.scenarios.append(self.scenario_cap_hold_time(90))
        self.scenarios.append(self.scenario_only_timeframe('1d'))
        self.scenarios.append(self.scenario_only_timeframe('3d'))
        self.scenarios.append(self.scenario_only_timeframe('1w'))
        self.scenarios.append(self.scenario_only_divergence_type('Bullish'))
        self.scenarios.append(self.scenario_only_divergence_type('Bearish'))

        # Print comparison
        self.print_comparison()

    def print_comparison(self):
        """Print side-by-side comparison"""
        print("="*70)
        print("SCENARIO COMPARISON RESULTS")
        print("="*70)
        print()

        baseline = self.scenarios[0]

        for scenario in self.scenarios:
            is_baseline = scenario['name'] == 'Current System'

            print(f"\n{'='*70}")
            print(f"{scenario['name']}")
            print(f"{'='*70}")

            print(f"Total P&L: ${scenario['total_pnl']:,.2f}", end='')
            if not is_baseline:
                diff = scenario['total_pnl'] - baseline['total_pnl']
                pct_change = (diff / baseline['total_pnl'] * 100) if baseline['total_pnl'] != 0 else 0
                indicator = "✅" if diff > 0 else "❌"
                print(f"  ({diff:+,.2f}, {pct_change:+.1f}%) {indicator}")
            else:
                print(" [BASELINE]")

            print(f"Total Trades: {scenario['total_trades']}", end='')
            if not is_baseline and 'trades_filtered_out' in scenario:
                print(f"  (filtered out: {scenario['trades_filtered_out']})")
            else:
                print()

            print(f"Winners: {scenario['winners']} | Losers: {scenario['losers']}")
            print(f"Win Rate: {scenario['win_rate']:.1f}%", end='')
            if not is_baseline:
                diff = scenario['win_rate'] - baseline['win_rate']
                indicator = "✅" if diff > 0 else "❌"
                print(f"  ({diff:+.1f}%) {indicator}")
            else:
                print()

            if scenario['avg_winner'] > 0:
                print(f"Avg Winner: ${scenario['avg_winner']:,.2f}")
                print(f"Avg Loser: ${scenario['avg_loser']:,.2f}")

            print(f"Profit Factor: {scenario['profit_factor']:.2f}", end='')
            if not is_baseline and scenario['profit_factor'] > 0:
                diff = scenario['profit_factor'] - baseline['profit_factor']
                indicator = "✅" if diff > 0 else "❌"
                print(f"  ({diff:+.2f}) {indicator}")
            else:
                print()

            print(f"Avg P&L per Trade: ${scenario['avg_pnl_per_trade']:,.2f}", end='')
            if not is_baseline:
                diff = scenario['avg_pnl_per_trade'] - baseline['avg_pnl_per_trade']
                indicator = "✅" if diff > 0 else "❌"
                print(f"  ({diff:+,.2f}) {indicator}")
            else:
                print()

            if 'note' in scenario:
                print(f"\nNote: {scenario['note']}")

            if 'trades_affected' in scenario:
                print(f"Trades Affected: {scenario['trades_affected']}")

        # Summary
        print(f"\n{'='*70}")
        print("SUMMARY RECOMMENDATIONS")
        print(f"{'='*70}\n")

        # Find best scenarios
        best_total_pnl = max([s for s in self.scenarios if s['name'] != 'Current System'],
                            key=lambda x: x['total_pnl'])
        best_win_rate = max([s for s in self.scenarios if s['name'] != 'Current System'],
                           key=lambda x: x['win_rate'])
        best_per_trade = max([s for s in self.scenarios if s['name'] != 'Current System' and s['total_trades'] > 0],
                            key=lambda x: x['avg_pnl_per_trade'])

        print(f"🏆 Best Total P&L: {best_total_pnl['name']}")
        print(f"   ${best_total_pnl['total_pnl']:,.2f} vs baseline ${baseline['total_pnl']:,.2f}")
        print()

        print(f"🏆 Best Win Rate: {best_win_rate['name']}")
        print(f"   {best_win_rate['win_rate']:.1f}% vs baseline {baseline['win_rate']:.1f}%")
        print()

        print(f"🏆 Best Per-Trade Profit: {best_per_trade['name']}")
        print(f"   ${best_per_trade['avg_pnl_per_trade']:.2f} vs baseline ${baseline['avg_pnl_per_trade']:.2f}")
        print()

        # Warnings
        print("⚠️  KEY FINDINGS:")

        cap60 = [s for s in self.scenarios if 'Cap Hold Time at 60' in s['name']][0]
        if cap60['total_pnl'] < baseline['total_pnl'] * 0.5:
            print(f"   - Capping at 60 days would DESTROY performance (-{(1 - cap60['total_pnl']/baseline['total_pnl'])*100:.1f}%)")

        best_setups = [s for s in self.scenarios if 'Only Best Setups' in s['name']][0]
        if best_setups['win_rate'] > baseline['win_rate']:
            print(f"   - Trading only best setups improves win rate by {best_setups['win_rate'] - baseline['win_rate']:.1f}%")

        weak_excluded = [s for s in self.scenarios if 'Exclude Weak Setups' in s['name']][0]
        if weak_excluded['total_pnl'] > baseline['total_pnl']:
            print(f"   - Excluding weak setups would add ${weak_excluded['total_pnl'] - baseline['total_pnl']:.2f}")


if __name__ == "__main__":
    tester = ScenarioTester()
    tester.load_data()
    tester.run_all_scenarios()
