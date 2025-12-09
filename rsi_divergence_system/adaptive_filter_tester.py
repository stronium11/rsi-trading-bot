"""
Adaptive Stop Loss Filter Tester

Tests adaptive trading rules that respond to consecutive losses:
- Scenario A: Stop trading divergence type after 3 consecutive stop losses
- Scenario B: Reduce position size to 50% after 3 consecutive stop losses

Rules reset at start of each new quarter.
Tracks Bullish and Bearish divergences separately.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime


class AdaptiveFilterTester:
    """
    Tests adaptive filters that respond to consecutive stop losses
    """

    def __init__(self, signals_csv='backtest/backtest_signals.csv',
                 baseline_results='backtest/optimized_results/trades_summary.csv'):
        """Initialize tester"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.signals_csv = os.path.join(script_dir, signals_csv)
        self.baseline_csv = os.path.join(script_dir, baseline_results)

        self.signals_df = None
        self.baseline_df = None

        # Output
        self.output_dir = os.path.join(script_dir, 'backtest', 'filter_tests')
        os.makedirs(self.output_dir, exist_ok=True)

    def load_data(self):
        """Load signals and baseline results"""
        print("Loading data...")

        # Load baseline results
        self.baseline_df = pd.read_csv(self.baseline_csv)
        self.baseline_df['entry_date'] = pd.to_datetime(self.baseline_df['entry_date'])
        self.baseline_df['signal_date'] = pd.to_datetime(self.baseline_df['signal_date'])

        # Check if we need to parse exits column or if exit_reasons/final_exit_date already exist
        if 'exit_reasons' not in self.baseline_df.columns or 'final_exit_date' not in self.baseline_df.columns:
            # Parse exits column to extract final_exit_date and exit_reasons
            import ast
            import re

            def extract_exit_info(exits_str):
                """Extract final exit date and exit reasons from exits string"""
                try:
                    # Handle pandas objects in the string
                    exits_str = str(exits_str)

                    # Extract all exit_date timestamps
                    date_matches = re.findall(r"'exit_date': Timestamp\('([^']+)'\)", exits_str)
                    # Extract all exit_reason strings
                    reason_matches = re.findall(r"'exit_reason': '([^']+)'", exits_str)

                    if date_matches and reason_matches:
                        # Get final exit date (last one)
                        final_exit_date = pd.to_datetime(date_matches[-1])
                        # Get all exit reasons
                        exit_reasons = ', '.join(reason_matches)
                        return final_exit_date, exit_reasons
                    else:
                        return pd.NaT, ''
                except Exception as e:
                    return pd.NaT, ''

            self.baseline_df[['final_exit_date', 'exit_reasons']] = self.baseline_df['exits'].apply(
                lambda x: pd.Series(extract_exit_info(x))
            )
        else:
            # Columns already exist, just parse dates
            self.baseline_df['final_exit_date'] = pd.to_datetime(self.baseline_df['final_exit_date'])

        # Add quarter column
        self.baseline_df['quarter'] = self.baseline_df['entry_date'].dt.to_period('Q')

        # Sort chronologically
        self.baseline_df = self.baseline_df.sort_values('entry_date').reset_index(drop=True)

        print(f"Loaded {len(self.baseline_df)} trades")
        print(f"Date range: {self.baseline_df['entry_date'].min()} to {self.baseline_df['entry_date'].max()}")
        print()

    def is_stop_loss(self, row):
        """Check if trade was a LOSING stop loss"""
        # Only count as stop loss if:
        # 1. "Stop Loss" is in exit reasons
        # 2. Trade was a net loser
        has_stop_loss = 'Stop Loss' in str(row['exit_reasons'])
        is_loser = row['total_pnl'] <= 0

        return has_stop_loss and is_loser

    def test_skip_after_n_losses(self, n_losses):
        """
        Generic: Skip divergence type after N consecutive stop losses

        Rules:
        - Track consecutive stop losses by type (Bullish/Bearish separately)
        - After N consecutive stops of same type → skip that type
        - Reset at start of new quarter
        """
        print("="*70)
        print(f"SCENARIO: Skip After {n_losses} Consecutive Stop Losses")
        print("="*70)
        print()
        print("Rules:")
        print("  - Track stop losses by divergence type (Bullish/Bearish separately)")
        print(f"  - After {n_losses} consecutive stops → skip that divergence type")
        print("  - Reset at start of each new quarter")
        print(f"  - Do NOT mix types ({n_losses} Bullish stops ≠ {n_losses-1} Bullish + 1 Bearish)")
        print()

        # Track state
        consecutive_stops = {'Bullish': 0, 'Bearish': 0}
        blocked_types = {'Bullish': False, 'Bearish': False}
        current_quarter = None

        # Results
        results_df = self.baseline_df.copy()
        results_df['would_take_trade'] = True
        results_df['consecutive_stops_before'] = 0
        results_df['blocked_before_trade'] = False

        for idx, row in results_df.iterrows():
            div_type = row['divergence_type']
            trade_quarter = row['quarter']

            # Reset at start of new quarter
            if current_quarter is None or trade_quarter != current_quarter:
                consecutive_stops = {'Bullish': 0, 'Bearish': 0}
                blocked_types = {'Bullish': False, 'Bearish': False}
                current_quarter = trade_quarter

            # Record state before this trade
            results_df.at[idx, 'consecutive_stops_before'] = consecutive_stops[div_type]
            results_df.at[idx, 'blocked_before_trade'] = blocked_types[div_type]

            # Check if we would skip this trade
            if blocked_types[div_type]:
                results_df.at[idx, 'would_take_trade'] = False
                # Don't update counters for skipped trades
                continue

            # We took the trade - check if it was a stop loss
            if self.is_stop_loss(row):
                consecutive_stops[div_type] += 1

                # Check if we hit N consecutive stops
                if consecutive_stops[div_type] >= n_losses:
                    blocked_types[div_type] = True
            else:
                # Non-stop loss resets consecutive counter for this type
                consecutive_stops[div_type] = 0

        # Generate report
        self._generate_scenario_report(
            results_df,
            scenario_name=f"Skip_After_{n_losses}_Stops",
            scenario_description=f"Skip divergence type after {n_losses} consecutive stop losses"
        )

    def test_scenario_a_skip_after_3_losses(self):
        """Scenario A: Skip after 3 consecutive stop losses"""
        self.test_skip_after_n_losses(3)

    def test_reduce_size_after_n_losses(self, n_losses):
        """
        Generic: Reduce position size to 50% after N consecutive stop losses

        Rules:
        - Track consecutive stop losses by type (Bullish/Bearish separately)
        - After N consecutive stops → reduce position to 50% for that type
        - Reset at start of new quarter
        """
        print("="*70)
        print(f"SCENARIO: Reduce Position 50% After {n_losses} Consecutive Stop Losses")
        print("="*70)
        print()
        print("Rules:")
        print("  - Track stop losses by divergence type (Bullish/Bearish separately)")
        print(f"  - After {n_losses} consecutive stops → reduce position to 50% ($500 instead of $1000)")
        print("  - Reset at start of each new quarter")
        print(f"  - Do NOT mix types ({n_losses} Bullish stops ≠ {n_losses-1} Bullish + 1 Bearish)")
        print()

        # Track state
        consecutive_stops = {'Bullish': 0, 'Bearish': 0}
        reduced_size = {'Bullish': False, 'Bearish': False}
        current_quarter = None

        # Results
        results_df = self.baseline_df.copy()
        results_df['position_size_pct'] = 100  # 100% = full size
        results_df['consecutive_stops_before'] = 0
        results_df['size_reduced_before_trade'] = False
        results_df['adjusted_pnl'] = results_df['total_pnl']

        for idx, row in results_df.iterrows():
            div_type = row['divergence_type']
            trade_quarter = row['quarter']

            # Reset at start of new quarter
            if current_quarter is None or trade_quarter != current_quarter:
                consecutive_stops = {'Bullish': 0, 'Bearish': 0}
                reduced_size = {'Bullish': False, 'Bearish': False}
                current_quarter = trade_quarter

            # Record state before this trade
            results_df.at[idx, 'consecutive_stops_before'] = consecutive_stops[div_type]
            results_df.at[idx, 'size_reduced_before_trade'] = reduced_size[div_type]

            # Apply position size reduction if active
            if reduced_size[div_type]:
                results_df.at[idx, 'position_size_pct'] = 50
                # Reduce P&L by 50%
                results_df.at[idx, 'adjusted_pnl'] = row['total_pnl'] * 0.5

            # Check if this trade was a stop loss
            if self.is_stop_loss(row):
                consecutive_stops[div_type] += 1

                # Check if we hit N consecutive stops
                if consecutive_stops[div_type] >= n_losses:
                    reduced_size[div_type] = True
            else:
                # Non-stop loss resets consecutive counter for this type
                consecutive_stops[div_type] = 0

        # Generate report
        self._generate_position_sizing_report(
            results_df,
            scenario_name=f"Reduce_50pct_After_{n_losses}_Stops",
            scenario_description=f"Reduce position size to 50% after {n_losses} consecutive stop losses"
        )

    def test_scenario_b_reduce_size_after_3_losses(self):
        """Scenario B: Reduce size after 3 consecutive stop losses"""
        self.test_reduce_size_after_n_losses(3)

    def test_scenario_c_skip_after_6_losses(self):
        """Scenario C: Skip after 6 consecutive stop losses"""
        self.test_skip_after_n_losses(6)

    def test_scenario_d_reduce_size_after_6_losses(self):
        """Scenario D: Reduce size after 6 consecutive stop losses"""
        self.test_reduce_size_after_n_losses(6)

    def test_scenario_e_skip_after_10_losses(self):
        """Scenario E: Skip after 10 consecutive stop losses"""
        self.test_skip_after_n_losses(10)

    def test_scenario_f_reduce_size_after_10_losses(self):
        """Scenario F: Reduce size after 10 consecutive stop losses"""
        self.test_reduce_size_after_n_losses(10)

    def _generate_scenario_report(self, results_df, scenario_name, scenario_description):
        """Generate report for skip scenario"""

        # Baseline
        baseline_trades = len(results_df)
        baseline_pnl = results_df['total_pnl'].sum()
        baseline_winners = len(results_df[results_df['total_pnl'] > 0])
        baseline_wr = (baseline_winners / baseline_trades) * 100

        # With filter
        taken_df = results_df[results_df['would_take_trade']]
        taken_trades = len(taken_df)
        taken_pnl = taken_df['total_pnl'].sum()
        taken_winners = len(taken_df[taken_df['total_pnl'] > 0])
        taken_wr = (taken_winners / taken_trades) * 100 if taken_trades > 0 else 0

        # Skipped
        skipped_df = results_df[~results_df['would_take_trade']]
        skipped_trades = len(skipped_df)
        skipped_pnl = skipped_df['total_pnl'].sum()
        skipped_winners = len(skipped_df[skipped_df['total_pnl'] > 0])

        # Print report
        print("RESULTS")
        print("-"*70)
        print()

        print("BASELINE (No Filter):")
        print(f"  Total Trades: {baseline_trades}")
        print(f"  Winners: {baseline_winners} | Win Rate: {baseline_wr:.1f}%")
        print(f"  Total P&L: ${baseline_pnl:,.2f}")
        print()

        print("WITH ADAPTIVE FILTER:")
        print(f"  Trades Taken: {taken_trades}")
        print(f"  Trades Skipped: {skipped_trades} ({skipped_trades/baseline_trades*100:.1f}%)")
        print(f"  Winners: {taken_winners} | Win Rate: {taken_wr:.1f}%")
        print(f"  Total P&L: ${taken_pnl:,.2f}")
        print()

        print("IMPACT:")
        pnl_change = taken_pnl - baseline_pnl
        pnl_change_pct = (pnl_change / baseline_pnl * 100) if baseline_pnl != 0 else 0
        print(f"  P&L Change: ${pnl_change:,.2f} ({pnl_change_pct:+.1f}%)")
        print(f"  Win Rate Change: {taken_wr - baseline_wr:+.1f}%")
        print(f"  Skipped Trades P&L: ${skipped_pnl:,.2f}")
        print()

        if skipped_trades > 0:
            print("SKIPPED TRADES ANALYSIS:")
            print(f"  Winners Skipped: {skipped_winners} | Losers Skipped: {skipped_trades - skipped_winners}")
            print(f"  Skipped Win Rate: {(skipped_winners/skipped_trades*100):.1f}%")

            # By type
            print()
            print("  By divergence type:")
            for div_type in ['Bullish', 'Bearish']:
                type_df = skipped_df[skipped_df['divergence_type'] == div_type]
                if len(type_df) > 0:
                    type_winners = len(type_df[type_df['total_pnl'] > 0])
                    type_pnl = type_df['total_pnl'].sum()
                    print(f"    {div_type}: {len(type_df)} trades, {type_winners} winners, ${type_pnl:,.2f} P&L")

            # Show some trigger examples
            print()
            print("  Example trigger events (first 5):")
            trigger_trades = results_df[results_df['consecutive_stops_before'] >= 2].head(5)
            for idx, row in trigger_trades.iterrows():
                status = "BLOCKED" if not row['would_take_trade'] else "TAKEN"
                print(f"    {row['entry_date'].strftime('%Y-%m-%d')} | {row['ticker']} | "
                      f"{row['divergence_type']} | {row['consecutive_stops_before']} prior stops | "
                      f"{status} | P&L: ${row['total_pnl']:.2f}")

        print()

        # Export
        output_csv = os.path.join(self.output_dir, f'{scenario_name}_results.csv')
        results_df.to_csv(output_csv, index=False)
        print(f"Detailed results: {output_csv}")
        print()
        print("="*70)
        print()

    def _generate_position_sizing_report(self, results_df, scenario_name, scenario_description):
        """Generate report for position sizing scenario"""

        # Baseline
        baseline_trades = len(results_df)
        baseline_pnl = results_df['total_pnl'].sum()
        baseline_winners = len(results_df[results_df['total_pnl'] > 0])
        baseline_wr = (baseline_winners / baseline_trades) * 100

        # With sizing adjustment
        adjusted_pnl = results_df['adjusted_pnl'].sum()
        reduced_trades = len(results_df[results_df['position_size_pct'] < 100])

        # Print report
        print("RESULTS")
        print("-"*70)
        print()

        print("BASELINE (No Position Sizing):")
        print(f"  Total Trades: {baseline_trades}")
        print(f"  Winners: {baseline_winners} | Win Rate: {baseline_wr:.1f}%")
        print(f"  Total P&L: ${baseline_pnl:,.2f}")
        print()

        print("WITH ADAPTIVE POSITION SIZING:")
        print(f"  Total Trades: {baseline_trades} (all taken)")
        print(f"  Trades at 50% size: {reduced_trades} ({reduced_trades/baseline_trades*100:.1f}%)")
        print(f"  Winners: {baseline_winners} | Win Rate: {baseline_wr:.1f}% (unchanged)")
        print(f"  Total P&L: ${adjusted_pnl:,.2f}")
        print()

        print("IMPACT:")
        pnl_change = adjusted_pnl - baseline_pnl
        pnl_change_pct = (pnl_change / baseline_pnl * 100) if baseline_pnl != 0 else 0
        print(f"  P&L Change: ${pnl_change:,.2f} ({pnl_change_pct:+.1f}%)")
        print(f"  Impact from reduced sizing: ${pnl_change:,.2f}")
        print()

        if reduced_trades > 0:
            print("REDUCED SIZE TRADES ANALYSIS:")
            reduced_df = results_df[results_df['position_size_pct'] < 100]
            reduced_winners = len(reduced_df[reduced_df['total_pnl'] > 0])
            reduced_full_pnl = reduced_df['total_pnl'].sum()
            reduced_actual_pnl = reduced_df['adjusted_pnl'].sum()

            print(f"  Winners: {reduced_winners} | Losers: {reduced_trades - reduced_winners}")
            print(f"  Win Rate: {(reduced_winners/reduced_trades*100):.1f}%")
            print(f"  P&L at full size: ${reduced_full_pnl:,.2f}")
            print(f"  P&L at 50% size: ${reduced_actual_pnl:,.2f}")
            print(f"  Saved/Lost: ${reduced_actual_pnl - reduced_full_pnl:,.2f}")

            # By type
            print()
            print("  By divergence type:")
            for div_type in ['Bullish', 'Bearish']:
                type_df = reduced_df[reduced_df['divergence_type'] == div_type]
                if len(type_df) > 0:
                    type_winners = len(type_df[type_df['total_pnl'] > 0])
                    type_full_pnl = type_df['total_pnl'].sum()
                    type_actual_pnl = type_df['adjusted_pnl'].sum()
                    print(f"    {div_type}: {len(type_df)} trades, {type_winners} winners")
                    print(f"      Full size P&L: ${type_full_pnl:,.2f} → 50% size: ${type_actual_pnl:,.2f}")

            # Show trigger examples
            print()
            print("  Example size reductions (first 5):")
            trigger_trades = reduced_df.head(5)
            for idx, row in trigger_trades.iterrows():
                print(f"    {row['entry_date'].strftime('%Y-%m-%d')} | {row['ticker']} | "
                      f"{row['divergence_type']} | {row['consecutive_stops_before']} prior stops | "
                      f"50% size | P&L: ${row['total_pnl']:.2f} → ${row['adjusted_pnl']:.2f}")

        print()

        # Export
        output_csv = os.path.join(self.output_dir, f'{scenario_name}_results.csv')
        results_df.to_csv(output_csv, index=False)
        print(f"Detailed results: {output_csv}")
        print()
        print("="*70)
        print()

    def run_all_scenarios(self):
        """Run all adaptive filter scenarios"""
        print("="*70)
        print("ADAPTIVE FILTER TESTING - 10 Consecutive Losses")
        print("="*70)
        print()
        print("Testing adaptive filters that respond to consecutive stop losses")
        print("Separate tracking for Bullish and Bearish divergences")
        print("Reset at start of each new quarter")
        print()

        self.load_data()

        print("\n")
        self.test_scenario_e_skip_after_10_losses()

        print("\n")
        self.test_scenario_f_reduce_size_after_10_losses()

        print("="*70)
        print("ADAPTIVE FILTER TESTING COMPLETE")
        print("="*70)
        print(f"Results: {self.output_dir}")


def main():
    """Run adaptive filter tests"""
    tester = AdaptiveFilterTester()
    tester.run_all_scenarios()


if __name__ == "__main__":
    main()
