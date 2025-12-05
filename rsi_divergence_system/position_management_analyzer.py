#!/usr/bin/env python3
"""
Position Management Analyzer
Analyzes actual trade data to find patterns and optimize position management rules
"""

import pandas as pd
import numpy as np
import ast
from datetime import datetime, timedelta


class PositionManagementAnalyzer:
    """
    Analyzes historical trade performance to optimize position management
    """

    def __init__(self, results_csv='backtest/backtest_results.csv'):
        """Initialize analyzer with backtest results"""
        self.results_csv = results_csv
        self.df = None
        self.findings = []

    def load_data(self):
        """Load backtest results"""
        print("Loading backtest results...")
        self.df = pd.read_csv(self.results_csv)

        # Parse exits column from string to list (handle numpy types and Timestamps)
        def safe_eval_exits(exits_str):
            """Safely evaluate exits string with numpy types and Timestamps"""
            # Create safe namespace with Timestamp and np.float64
            safe_dict = {
                'Timestamp': pd.Timestamp,
                'np': np,
                '__builtins__': {}
            }
            try:
                return eval(exits_str, safe_dict)
            except Exception as e:
                print(f"Error parsing exits: {e}")
                return []

        self.df['exits'] = self.df['exits'].apply(safe_eval_exits)

        # Convert dates
        self.df['signal_date'] = pd.to_datetime(self.df['signal_date'])
        self.df['entry_date'] = pd.to_datetime(self.df['entry_date'])

        print(f"Loaded {len(self.df)} trades")
        print(f"Winners: {len(self.df[self.df['total_pnl'] > 0])}")
        print(f"Losers: {len(self.df[self.df['total_pnl'] <= 0])}")
        print()

    def analyze_stop_loss_effectiveness(self):
        """Analyze if -5% stop is optimal"""
        print("="*70)
        print("ANALYSIS 1: STOP LOSS EFFECTIVENESS")
        print("="*70)

        # Count trades that hit stop
        stop_loss_trades = []
        for idx, row in self.df.iterrows():
            for exit in row['exits']:
                if 'Stop Loss' in str(exit.get('exit_reason', '')):
                    stop_loss_trades.append({
                        'ticker': row['ticker'],
                        'timeframe': row['timeframe'],
                        'entry_date': row['entry_date'],
                        'entry_price': row['entry_price'],
                        'direction': row['direction'],
                        'total_pnl': row['total_pnl'],
                        'total_pnl_pct': row['total_pnl_pct'],
                        'exit_reason': exit.get('exit_reason'),
                        'pnl': exit.get('pnl')
                    })

        stop_df = pd.DataFrame(stop_loss_trades)

        # Initial stop (-5%)
        initial_stops = stop_df[stop_df['total_pnl_pct'] == -5.0]
        breakeven_stops = stop_df[(stop_df['total_pnl_pct'] >= 0) & (stop_df['total_pnl_pct'] < 5)]
        profit_stops = stop_df[stop_df['total_pnl_pct'] >= 5]

        print(f"\nTotal trades hitting stop loss: {len(stop_df)}")
        print(f"  - Hit initial -5% stop: {len(initial_stops)} ({len(initial_stops)/len(self.df)*100:.1f}% of all trades)")
        print(f"  - Hit breakeven stop (0-5%): {len(breakeven_stops)} ({len(breakeven_stops)/len(self.df)*100:.1f}% of all trades)")
        print(f"  - Hit +3% or +10% profit stop: {len(profit_stops)} ({len(profit_stops)/len(self.df)*100:.1f}% of all trades)")

        # Calculate average loss from initial stop
        if len(initial_stops) > 0:
            avg_stop_loss = initial_stops['total_pnl'].mean()
            print(f"\nAverage P&L when hitting -5% stop: ${avg_stop_loss:.2f}")

        finding = {
            'title': 'Stop Loss Hit Rate',
            'metric': f"{len(initial_stops)} trades ({len(initial_stops)/len(self.df)*100:.1f}%) hit -5% stop",
            'details': f"Lost ${initial_stops['total_pnl'].sum():.2f} total from initial stops"
        }
        self.findings.append(finding)
        print()

        return stop_df

    def analyze_target_reachability(self):
        """Analyze what % of trades reach each target level"""
        print("="*70)
        print("ANALYSIS 2: PROFIT TARGET REACHABILITY")
        print("="*70)

        target1_count = 0  # +10%
        target2_count = 0  # +20%
        target3_count = 0  # +50%

        for idx, row in self.df.iterrows():
            exit_reasons = [exit.get('exit_reason', '') for exit in row['exits']]

            if any('Take Profit +10%' in str(reason) for reason in exit_reasons):
                target1_count += 1

            if any('Take Profit +20%' in str(reason) for reason in exit_reasons):
                target2_count += 1

            if any('Take Profit +50%' in str(reason) for reason in exit_reasons):
                target3_count += 1

        total_trades = len(self.df)
        t1_pct = (target1_count / total_trades) * 100
        t2_pct = (target2_count / total_trades) * 100
        t3_pct = (target3_count / total_trades) * 100

        print(f"\nTarget 1 (+10%, close 50%): {target1_count} trades ({t1_pct:.1f}%)")
        print(f"Target 2 (+20%, close 25%): {target2_count} trades ({t2_pct:.1f}%)")
        print(f"Target 3 (+50%, close remaining): {target3_count} trades ({t3_pct:.1f}%)")

        # Conditional probabilities
        if target1_count > 0:
            t2_given_t1 = (target2_count / target1_count) * 100
            print(f"\nOf trades reaching T1, {t2_given_t1:.1f}% reach T2")

        if target2_count > 0:
            t3_given_t2 = (target3_count / target2_count) * 100
            print(f"Of trades reaching T2, {t3_given_t2:.1f}% reach T3")

        finding = {
            'title': 'Target Reachability',
            'metric': f"T1: {t1_pct:.1f}%, T2: {t2_pct:.1f}%, T3: {t3_pct:.1f}%",
            'details': f"Only {t3_pct:.1f}% of trades reach the +50% target"
        }
        self.findings.append(finding)
        print()

        return {
            't1_count': target1_count,
            't2_count': target2_count,
            't3_count': target3_count,
            't1_pct': t1_pct,
            't2_pct': t2_pct,
            't3_pct': t3_pct
        }

    def analyze_hold_time(self):
        """Analyze if 120 day max hold is optimal"""
        print("="*70)
        print("ANALYSIS 3: HOLD TIME EFFICIENCY")
        print("="*70)

        # Categorize by hold time
        short_hold = self.df[self.df['days_in_trade'] <= 30]
        medium_hold = self.df[(self.df['days_in_trade'] > 30) & (self.df['days_in_trade'] <= 60)]
        long_hold = self.df[(self.df['days_in_trade'] > 60) & (self.df['days_in_trade'] <= 90)]
        very_long_hold = self.df[self.df['days_in_trade'] > 90]

        print(f"\nHold time distribution:")
        print(f"  0-30 days: {len(short_hold)} trades, avg P&L: ${short_hold['total_pnl'].mean():.2f}")
        print(f"  31-60 days: {len(medium_hold)} trades, avg P&L: ${medium_hold['total_pnl'].mean():.2f}")
        print(f"  61-90 days: {len(long_hold)} trades, avg P&L: ${long_hold['total_pnl'].mean():.2f}")
        print(f"  90+ days: {len(very_long_hold)} trades, avg P&L: ${very_long_hold['total_pnl'].mean():.2f}")

        # Win rates by hold time
        print(f"\nWin rates by hold time:")
        print(f"  0-30 days: {len(short_hold[short_hold['total_pnl'] > 0])/len(short_hold)*100:.1f}%")
        print(f"  31-60 days: {len(medium_hold[medium_hold['total_pnl'] > 0])/len(medium_hold)*100:.1f}%")
        print(f"  61-90 days: {len(long_hold[long_hold['total_pnl'] > 0])/len(long_hold)*100:.1f}%")
        print(f"  90+ days: {len(very_long_hold[very_long_hold['total_pnl'] > 0])/len(very_long_hold)*100:.1f}%")

        # Check max hold trades
        max_hold_trades = []
        for idx, row in self.df.iterrows():
            for exit in row['exits']:
                if 'Max Hold' in str(exit.get('exit_reason', '')):
                    max_hold_trades.append({
                        'ticker': row['ticker'],
                        'total_pnl': row['total_pnl'],
                        'days_in_trade': row['days_in_trade']
                    })

        if len(max_hold_trades) > 0:
            max_hold_df = pd.DataFrame(max_hold_trades)
            print(f"\n{len(max_hold_trades)} trades hit 120-day max hold")
            print(f"  Avg P&L: ${max_hold_df['total_pnl'].mean():.2f}")
            print(f"  Total P&L: ${max_hold_df['total_pnl'].sum():.2f}")

        finding = {
            'title': 'Hold Time Efficiency',
            'metric': f"Trades >90 days avg ${very_long_hold['total_pnl'].mean():.2f}",
            'details': f"{len(very_long_hold)} trades held >90 days"
        }
        self.findings.append(finding)
        print()

    def analyze_exit_leg_contribution(self):
        """Analyze which exit legs contribute most profit"""
        print("="*70)
        print("ANALYSIS 4: EXIT LEG PROFIT CONTRIBUTION")
        print("="*70)

        leg1_profits = []  # Target 1 (+10%, 50%)
        leg2_profits = []  # Target 2 (+20%, 25%)
        leg3_profits = []  # Target 3 (+50%, 25%)
        stop_losses = []

        for idx, row in self.df.iterrows():
            for exit in row['exits']:
                reason = str(exit.get('exit_reason', ''))
                pnl = exit.get('pnl', 0)

                if 'Take Profit +10%' in reason:
                    leg1_profits.append(pnl)
                elif 'Take Profit +20%' in reason:
                    leg2_profits.append(pnl)
                elif 'Take Profit +50%' in reason:
                    leg3_profits.append(pnl)
                elif 'Stop Loss' in reason:
                    stop_losses.append(pnl)

        total_leg1 = sum(leg1_profits)
        total_leg2 = sum(leg2_profits)
        total_leg3 = sum(leg3_profits)
        total_stops = sum(stop_losses)

        print(f"\nLeg 1 (T1 at +10%, 50% of position):")
        print(f"  Count: {len(leg1_profits)}")
        print(f"  Total P&L: ${total_leg1:.2f}")
        print(f"  Avg P&L per leg: ${np.mean(leg1_profits) if leg1_profits else 0:.2f}")

        print(f"\nLeg 2 (T2 at +20%, 25% of position):")
        print(f"  Count: {len(leg2_profits)}")
        print(f"  Total P&L: ${total_leg2:.2f}")
        print(f"  Avg P&L per leg: ${np.mean(leg2_profits) if leg2_profits else 0:.2f}")

        print(f"\nLeg 3 (T3 at +50%, remaining 25%):")
        print(f"  Count: {len(leg3_profits)}")
        print(f"  Total P&L: ${total_leg3:.2f}")
        print(f"  Avg P&L per leg: ${np.mean(leg3_profits) if leg3_profits else 0:.2f}")

        print(f"\nStop Losses:")
        print(f"  Count: {len(stop_losses)}")
        print(f"  Total P&L: ${total_stops:.2f}")
        print(f"  Avg P&L per stop: ${np.mean(stop_losses) if stop_losses else 0:.2f}")

        # Contribution percentages
        total_pnl = self.df['total_pnl'].sum()
        print(f"\nContribution to total P&L:")
        print(f"  Leg 1: {total_leg1/total_pnl*100:.1f}%")
        print(f"  Leg 2: {total_leg2/total_pnl*100:.1f}%")
        print(f"  Leg 3: {total_leg3/total_pnl*100:.1f}%")
        print(f"  Stops: {total_stops/total_pnl*100:.1f}%")

        finding = {
            'title': 'Exit Leg Contribution',
            'metric': f"T1: ${total_leg1:.0f}, T2: ${total_leg2:.0f}, T3: ${total_leg3:.0f}",
            'details': f"Leg 1 contributes {total_leg1/total_pnl*100:.1f}% of total profit"
        }
        self.findings.append(finding)
        print()

    def analyze_timeframe_divergence_patterns(self):
        """Analyze performance by timeframe and divergence type"""
        print("="*70)
        print("ANALYSIS 5: TIMEFRAME & DIVERGENCE PATTERNS")
        print("="*70)

        # Group by timeframe
        print("\nBy Timeframe:")
        for tf in ['1d', '3d', '1w']:
            tf_df = self.df[self.df['timeframe'] == tf]
            if len(tf_df) > 0:
                win_rate = len(tf_df[tf_df['total_pnl'] > 0]) / len(tf_df) * 100
                avg_pnl = tf_df['total_pnl'].mean()
                print(f"  {tf}: {len(tf_df)} trades, {win_rate:.1f}% win rate, ${avg_pnl:.2f} avg P&L")

        # Group by divergence type
        print("\nBy Divergence Type:")
        for div_type in ['Bullish', 'Bearish']:
            div_df = self.df[self.df['divergence_type'] == div_type]
            if len(div_df) > 0:
                win_rate = len(div_df[div_df['total_pnl'] > 0]) / len(div_df) * 100
                avg_pnl = div_df['total_pnl'].mean()
                print(f"  {div_type}: {len(div_df)} trades, {win_rate:.1f}% win rate, ${avg_pnl:.2f} avg P&L")

        # Combined
        print("\nCombined (Timeframe + Type):")
        for tf in ['1d', '3d', '1w']:
            for div_type in ['Bullish', 'Bearish']:
                combo_df = self.df[(self.df['timeframe'] == tf) & (self.df['divergence_type'] == div_type)]
                if len(combo_df) > 0:
                    win_rate = len(combo_df[combo_df['total_pnl'] > 0]) / len(combo_df) * 100
                    avg_pnl = combo_df['total_pnl'].mean()
                    print(f"  {tf} {div_type}: {len(combo_df)} trades, {win_rate:.1f}% win rate, ${avg_pnl:.2f} avg P&L")

        print()

    def generate_recommendations(self):
        """Generate actionable recommendations based on analysis"""
        print("="*70)
        print("RECOMMENDATIONS")
        print("="*70)
        print()

        # Current system stats
        win_rate = len(self.df[self.df['total_pnl'] > 0]) / len(self.df) * 100
        avg_winner = self.df[self.df['total_pnl'] > 0]['total_pnl'].mean()
        avg_loser = self.df[self.df['total_pnl'] <= 0]['total_pnl'].mean()
        total_pnl = self.df['total_pnl'].sum()

        print(f"CURRENT SYSTEM PERFORMANCE:")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Avg Winner: ${avg_winner:.2f}")
        print(f"  Avg Loser: ${avg_loser:.2f}")
        print(f"  Total P&L: ${total_pnl:.2f}")
        print()

        # Recommendations
        recommendations = []

        # Rec 1: Stop loss analysis
        initial_stops = len(self.df[self.df['total_pnl_pct'] == -5.0])
        if initial_stops > len(self.df) * 0.5:
            recommendations.append({
                'priority': 'HIGH',
                'title': 'Consider Wider Initial Stop Loss',
                'finding': f'{initial_stops} trades ({initial_stops/len(self.df)*100:.1f}%) hit -5% stop',
                'suggestion': 'Test -7% or -8% stop to see if more trades recover',
                'rationale': 'High stop hit rate suggests stop may be too tight for normal volatility'
            })

        # Rec 2: Target optimization
        target_stats = self.analyze_target_reachability()
        if target_stats['t3_pct'] < 10:
            recommendations.append({
                'priority': 'MEDIUM',
                'title': 'Lower Target 3 from +50% to +35%',
                'finding': f'Only {target_stats["t3_count"]} trades ({target_stats["t3_pct"]:.1f}%) reach +50%',
                'suggestion': 'Change T3 from +50% to +30-35% to capture more profit',
                'rationale': 'Most winning trades peak before reaching +50% target'
            })

        # Rec 3: Hold time
        long_holds = self.df[self.df['days_in_trade'] > 90]
        if len(long_holds) > 0 and long_holds['total_pnl'].mean() < 20:
            recommendations.append({
                'priority': 'MEDIUM',
                'title': 'Reduce Max Hold Time to 60-90 Days',
                'finding': f'{len(long_holds)} trades held >90 days, avg P&L ${long_holds["total_pnl"].mean():.2f}',
                'suggestion': 'Cap max hold at 60-75 days instead of 120',
                'rationale': 'Long holds underperform and tie up capital'
            })

        # Print recommendations
        for i, rec in enumerate(recommendations, 1):
            print(f"RECOMMENDATION #{i} - {rec['priority']} PRIORITY")
            print(f"  Title: {rec['title']}")
            print(f"  Finding: {rec['finding']}")
            print(f"  Suggestion: {rec['suggestion']}")
            print(f"  Rationale: {rec['rationale']}")
            print()

        return recommendations

    def run_full_analysis(self):
        """Run all analyses"""
        print("\n" + "#"*70)
        print("# POSITION MANAGEMENT ANALYSIS")
        print("# Analyzing 5-Year Backtest Results")
        print("#"*70)
        print()

        self.load_data()
        self.analyze_stop_loss_effectiveness()
        self.analyze_target_reachability()
        self.analyze_hold_time()
        self.analyze_exit_leg_contribution()
        self.analyze_timeframe_divergence_patterns()
        self.generate_recommendations()

        print("\n" + "#"*70)
        print("# ANALYSIS COMPLETE")
        print("#"*70)


if __name__ == "__main__":
    analyzer = PositionManagementAnalyzer()
    analyzer.run_full_analysis()
