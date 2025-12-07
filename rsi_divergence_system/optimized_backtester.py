"""
Optimized Backtester

Runs comprehensive backtest using optimized entry/exit rules on existing signals.
Uses Entry Day Open strategy with multi-leg profit taking.

Entry Rules:
- Enter at market OPEN on next trading day after signal
- Position size: $1,000 or 1 share (whichever is smaller)
- Allow fractional shares

Exit Rules:
- Initial Stop: -7%
- T1: +15% (close 70%, move stop to BE)
- T2: +18% (close 15%, move stop to +5%)
- T3: +50% or 120 days (close remaining 15%)

Tracking:
- Entry/exit dates
- Exit reasons
- P&L per exit leg
- % gain per exit leg

Analytics:
- Overall performance
- By timeframe (1d, 3d, 1w)
- By type (Bullish vs Bearish)
- By timeframe + type
- Quarterly breakdown
- Portfolio value tracking
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import pickle
import time


class OptimizedBacktester:
    """
    Comprehensive backtester with optimized entry/exit rules
    """

    def __init__(self, signals_csv='backtest/backtest_signals.csv'):
        """Initialize backtester"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.signals_csv = os.path.join(script_dir, signals_csv)
        self.signals_df = None

        # Results storage
        self.trades = []  # Detailed exit legs
        self.trade_summaries = []  # One per trade

        # Optimized rules
        self.rules = {
            'entry_type': 'open',  # Enter at next day OPEN
            'position_size': 1000,  # $1,000 per trade
            'initial_stop_pct': 7,  # -7%
            'target1_pct': 15,      # +15%
            'target1_size': 70,     # Close 70%
            'target2_pct': 18,      # +18%
            'target2_size': 15,     # Close 15%
            'target3_pct': 50,      # +50%
            'breakeven_trigger_pct': 5,  # Move to +5% after T2
            'max_hold_days': 120
        }

        # Create output directory
        self.output_dir = os.path.join(script_dir, 'backtest', 'optimized_results')
        os.makedirs(self.output_dir, exist_ok=True)

    def load_signals(self):
        """Load existing backtest signals"""
        print("Loading existing backtest signals...")
        self.signals_df = pd.read_csv(self.signals_csv)

        # Parse dates
        self.signals_df['signal_date'] = pd.to_datetime(self.signals_df['signal_date'])
        self.signals_df['entry_date'] = pd.to_datetime(self.signals_df['entry_date'])

        print(f"Loaded {len(self.signals_df)} signals from {self.signals_csv}\n")

    def get_entry_price(self, ticker, entry_date, price_df):
        """
        Get entry price at market OPEN on entry_date (or next trading day)

        Returns (entry_price, actual_entry_date)
        """
        # Find the actual entry day (entry_date or next trading day)
        entry_day = price_df[price_df.index == entry_date]

        if len(entry_day) == 0:
            # Entry date is weekend/holiday, use next trading day
            after_entry = price_df[price_df.index > entry_date]
            if len(after_entry) == 0:
                return None, None
            entry_day = after_entry.head(1)

        entry_price = entry_day.iloc[0]['open']  # OPEN price
        actual_entry_date = entry_day.index[0]

        return entry_price, actual_entry_date

    def simulate_trade(self, signal, price_df):
        """
        Simulate a single trade with multi-leg exits

        Returns list of exit legs (each leg is a dict)
        """
        ticker = signal['ticker']
        signal_date = signal['signal_date']
        entry_date = signal['entry_date']
        direction = 'LONG' if signal['divergence_type'] == 'Bullish' else 'SHORT'

        # Get entry price at OPEN
        entry_price, actual_entry_date = self.get_entry_price(ticker, entry_date, price_df)

        if entry_price is None:
            return None

        # Calculate position size
        if entry_price >= self.rules['position_size']:
            # Stock price >= $1000, buy exactly 1 share
            shares = 1.0
        else:
            # Stock < $1000, buy $1000 worth
            shares = self.rules['position_size'] / entry_price

        # Track position
        remaining_shares = shares
        total_pnl = 0
        exits = []

        # Calculate initial stop
        if direction == 'LONG':
            initial_stop = entry_price * (1 - self.rules['initial_stop_pct'] / 100)
        else:
            initial_stop = entry_price * (1 + self.rules['initial_stop_pct'] / 100)

        current_stop = initial_stop
        t1_hit = False
        t2_hit = False

        # Simulate price movement day by day
        trade_df = price_df[price_df.index >= actual_entry_date]

        for date, row in trade_df.iterrows():
            if date == actual_entry_date:
                continue  # Skip entry day

            # Check max hold time
            days_in_trade = (date - actual_entry_date).days
            if days_in_trade > self.rules['max_hold_days']:
                # Exit remaining position
                if remaining_shares > 0:
                    exit_price = row['close']

                    if direction == 'LONG':
                        pnl = (exit_price - entry_price) * remaining_shares
                        pct_gain = ((exit_price - entry_price) / entry_price) * 100
                    else:
                        pnl = (entry_price - exit_price) * remaining_shares
                        pct_gain = ((entry_price - exit_price) / entry_price) * 100

                    exits.append({
                        'exit_date': date,
                        'exit_reason': 'Max Hold (120 days)',
                        'exit_price': exit_price,
                        'shares_closed': remaining_shares,
                        'pct_of_position': (remaining_shares / shares) * 100,
                        'pnl': pnl,
                        'pct_gain': pct_gain
                    })

                    total_pnl += pnl
                    remaining_shares = 0
                break

            # Check stop loss
            if direction == 'LONG':
                if row['low'] <= current_stop:
                    # Stopped out
                    exit_price = current_stop
                    pnl = (exit_price - entry_price) * remaining_shares
                    pct_gain = ((exit_price - entry_price) / entry_price) * 100

                    exits.append({
                        'exit_date': date,
                        'exit_reason': 'Stop Loss',
                        'exit_price': exit_price,
                        'shares_closed': remaining_shares,
                        'pct_of_position': (remaining_shares / shares) * 100,
                        'pnl': pnl,
                        'pct_gain': pct_gain
                    })

                    total_pnl += pnl
                    remaining_shares = 0
                    break
            else:  # SHORT
                if row['high'] >= current_stop:
                    # Stopped out
                    exit_price = current_stop
                    pnl = (entry_price - exit_price) * remaining_shares
                    pct_gain = ((entry_price - exit_price) / entry_price) * 100

                    exits.append({
                        'exit_date': date,
                        'exit_reason': 'Stop Loss',
                        'exit_price': exit_price,
                        'shares_closed': remaining_shares,
                        'pct_of_position': (remaining_shares / shares) * 100,
                        'pnl': pnl,
                        'pct_gain': pct_gain
                    })

                    total_pnl += pnl
                    remaining_shares = 0
                    break

            # Check Target 1
            if not t1_hit:
                if direction == 'LONG':
                    profit_pct = ((row['high'] - entry_price) / entry_price) * 100
                    if profit_pct >= self.rules['target1_pct']:
                        # T1 hit
                        exit_price = entry_price * (1 + self.rules['target1_pct'] / 100)
                        shares_to_close = shares * (self.rules['target1_size'] / 100)
                        pnl = (exit_price - entry_price) * shares_to_close

                        exits.append({
                            'exit_date': date,
                            'exit_reason': 'Target 1 (+15%)',
                            'exit_price': exit_price,
                            'shares_closed': shares_to_close,
                            'pct_of_position': self.rules['target1_size'],
                            'pnl': pnl,
                            'pct_gain': self.rules['target1_pct']
                        })

                        total_pnl += pnl
                        remaining_shares -= shares_to_close
                        t1_hit = True

                        # Move stop to breakeven
                        current_stop = entry_price
                        continue
                else:  # SHORT
                    profit_pct = ((entry_price - row['low']) / entry_price) * 100
                    if profit_pct >= self.rules['target1_pct']:
                        # T1 hit
                        exit_price = entry_price * (1 - self.rules['target1_pct'] / 100)
                        shares_to_close = shares * (self.rules['target1_size'] / 100)
                        pnl = (entry_price - exit_price) * shares_to_close

                        exits.append({
                            'exit_date': date,
                            'exit_reason': 'Target 1 (+15%)',
                            'exit_price': exit_price,
                            'shares_closed': shares_to_close,
                            'pct_of_position': self.rules['target1_size'],
                            'pnl': pnl,
                            'pct_gain': self.rules['target1_pct']
                        })

                        total_pnl += pnl
                        remaining_shares -= shares_to_close
                        t1_hit = True

                        # Move stop to breakeven
                        current_stop = entry_price
                        continue

            # Check Target 2 (only if T1 hit)
            if t1_hit and not t2_hit:
                if direction == 'LONG':
                    profit_pct = ((row['high'] - entry_price) / entry_price) * 100
                    if profit_pct >= self.rules['target2_pct']:
                        # T2 hit
                        exit_price = entry_price * (1 + self.rules['target2_pct'] / 100)
                        shares_to_close = shares * (self.rules['target2_size'] / 100)
                        pnl = (exit_price - entry_price) * shares_to_close

                        exits.append({
                            'exit_date': date,
                            'exit_reason': 'Target 2 (+18%)',
                            'exit_price': exit_price,
                            'shares_closed': shares_to_close,
                            'pct_of_position': self.rules['target2_size'],
                            'pnl': pnl,
                            'pct_gain': self.rules['target2_pct']
                        })

                        total_pnl += pnl
                        remaining_shares -= shares_to_close
                        t2_hit = True

                        # Move stop to +5%
                        current_stop = entry_price * (1 + self.rules['breakeven_trigger_pct'] / 100)
                        continue
                else:  # SHORT
                    profit_pct = ((entry_price - row['low']) / entry_price) * 100
                    if profit_pct >= self.rules['target2_pct']:
                        # T2 hit
                        exit_price = entry_price * (1 - self.rules['target2_pct'] / 100)
                        shares_to_close = shares * (self.rules['target2_size'] / 100)
                        pnl = (entry_price - exit_price) * shares_to_close

                        exits.append({
                            'exit_date': date,
                            'exit_reason': 'Target 2 (+18%)',
                            'exit_price': exit_price,
                            'shares_closed': shares_to_close,
                            'pct_of_position': self.rules['target2_size'],
                            'pnl': pnl,
                            'pct_gain': self.rules['target2_pct']
                        })

                        total_pnl += pnl
                        remaining_shares -= shares_to_close
                        t2_hit = True

                        # Move stop to +5%
                        current_stop = entry_price * (1 - self.rules['breakeven_trigger_pct'] / 100)
                        continue

            # Check Target 3 (only if T2 hit)
            if t2_hit:
                if direction == 'LONG':
                    profit_pct = ((row['high'] - entry_price) / entry_price) * 100
                    if profit_pct >= self.rules['target3_pct']:
                        # T3 hit - exit remaining
                        exit_price = entry_price * (1 + self.rules['target3_pct'] / 100)
                        pnl = (exit_price - entry_price) * remaining_shares

                        exits.append({
                            'exit_date': date,
                            'exit_reason': 'Target 3 (+50%)',
                            'exit_price': exit_price,
                            'shares_closed': remaining_shares,
                            'pct_of_position': (remaining_shares / shares) * 100,
                            'pnl': pnl,
                            'pct_gain': self.rules['target3_pct']
                        })

                        total_pnl += pnl
                        remaining_shares = 0
                        break
                else:  # SHORT
                    profit_pct = ((entry_price - row['low']) / entry_price) * 100
                    if profit_pct >= self.rules['target3_pct']:
                        # T3 hit - exit remaining
                        exit_price = entry_price * (1 - self.rules['target3_pct'] / 100)
                        pnl = (entry_price - exit_price) * remaining_shares

                        exits.append({
                            'exit_date': date,
                            'exit_reason': 'Target 3 (+50%)',
                            'exit_price': exit_price,
                            'shares_closed': remaining_shares,
                            'pct_of_position': (remaining_shares / shares) * 100,
                            'pnl': pnl,
                            'pct_gain': self.rules['target3_pct']
                        })

                        total_pnl += pnl
                        remaining_shares = 0
                        break

        # Add metadata to each exit
        for exit_leg in exits:
            exit_leg.update({
                'ticker': ticker,
                'signal_date': signal_date,
                'entry_date': actual_entry_date,
                'entry_price': entry_price,
                'direction': direction,
                'timeframe': signal['timeframe'],
                'divergence_type': signal['divergence_type'],
                'total_shares': shares,
                'position_value': entry_price * shares
            })

        return exits

    def run_backtest(self):
        """Run backtest on all signals"""
        print("="*70)
        print("OPTIMIZED BACKTEST - Entry at Market Open")
        print("="*70)
        print(f"\nRules:")
        print(f"  Entry: Next trading day OPEN after signal")
        print(f"  Position Size: $1,000 or 1 share (fractional allowed)")
        print(f"  Stop: -{self.rules['initial_stop_pct']}%")
        print(f"  T1: +{self.rules['target1_pct']}% (close {self.rules['target1_size']}%, move stop to BE)")
        print(f"  T2: +{self.rules['target2_pct']}% (close {self.rules['target2_size']}%, move stop to +{self.rules['breakeven_trigger_pct']}%)")
        print(f"  T3: +{self.rules['target3_pct']}% or {self.rules['max_hold_days']} days (close remaining 15%)")
        print()

        print(f"Processing {len(self.signals_df)} signals...")

        # Use price cache from previous runs
        from iterative_optimizer import PriceDataCache
        cache_dir = os.path.join(os.path.dirname(self.signals_csv), 'price_cache')
        cache = PriceDataCache(cache_dir=cache_dir)

        processed = 0
        skipped = 0

        for idx, row in self.signals_df.iterrows():
            # Load price data from cache
            price_df = cache.load(row['ticker'], row['entry_date'])

            if price_df is None:
                skipped += 1
                continue

            # Simulate trade
            exits = self.simulate_trade(row, price_df)

            if exits is None:
                skipped += 1
                continue

            # Store exit legs
            self.trades.extend(exits)

            # Create trade summary
            total_pnl = sum(e['pnl'] for e in exits)
            final_exit_date = exits[-1]['exit_date']
            days_held = (final_exit_date - exits[0]['entry_date']).days

            self.trade_summaries.append({
                'ticker': row['ticker'],
                'signal_date': row['signal_date'],
                'entry_date': exits[0]['entry_date'],
                'entry_price': exits[0]['entry_price'],
                'final_exit_date': final_exit_date,
                'days_held': days_held,
                'direction': exits[0]['direction'],
                'timeframe': row['timeframe'],
                'divergence_type': row['divergence_type'],
                'total_pnl': total_pnl,
                'position_value': exits[0]['position_value'],
                'num_exits': len(exits),
                'exit_reasons': ', '.join(e['exit_reason'] for e in exits)
            })

            processed += 1

            if (processed % 50) == 0:
                print(f"  Processed {processed}/{len(self.signals_df)} signals...")

        print(f"\n✅ Backtest complete!")
        print(f"  Processed: {processed} trades")
        print(f"  Skipped: {skipped} (no price data)")
        print(f"  Total exit legs: {len(self.trades)}")
        print()

    def calculate_metrics(self):
        """Calculate comprehensive performance metrics"""
        print("Calculating performance metrics...")

        df = pd.DataFrame(self.trade_summaries)

        # Overall metrics
        total_trades = len(df)
        winners = len(df[df['total_pnl'] > 0])
        losers = len(df[df['total_pnl'] <= 0])
        win_rate = (winners / total_trades) * 100 if total_trades > 0 else 0

        avg_winner = df[df['total_pnl'] > 0]['total_pnl'].mean() if winners > 0 else 0
        avg_loser = df[df['total_pnl'] <= 0]['total_pnl'].mean() if losers > 0 else 0

        total_wins = df[df['total_pnl'] > 0]['total_pnl'].sum()
        total_losses = abs(df[df['total_pnl'] <= 0]['total_pnl'].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        total_pnl = df['total_pnl'].sum()
        total_invested = df['position_value'].sum()
        total_return_pct = (total_pnl / total_invested) * 100 if total_invested > 0 else 0

        overall = {
            'Total Trades': total_trades,
            'Winners': winners,
            'Losers': losers,
            'Win Rate %': win_rate,
            'Avg Winner $': avg_winner,
            'Avg Loser $': avg_loser,
            'Profit Factor': profit_factor,
            'Total P&L $': total_pnl,
            'Total Invested $': total_invested,
            'Total Return %': total_return_pct,
            'Final Portfolio Value $': total_invested + total_pnl
        }

        # By timeframe
        by_timeframe = []
        for tf in df['timeframe'].unique():
            tf_df = df[df['timeframe'] == tf]
            tf_winners = len(tf_df[tf_df['total_pnl'] > 0])
            tf_losers = len(tf_df[tf_df['total_pnl'] <= 0])

            by_timeframe.append({
                'Timeframe': tf,
                'Total Trades': len(tf_df),
                'Winners': tf_winners,
                'Losers': tf_losers,
                'Win Rate %': (tf_winners / len(tf_df)) * 100,
                'Total P&L $': tf_df['total_pnl'].sum(),
                'Avg P&L $': tf_df['total_pnl'].mean()
            })

        # By type
        by_type = []
        for div_type in df['divergence_type'].unique():
            type_df = df[df['divergence_type'] == div_type]
            type_winners = len(type_df[type_df['total_pnl'] > 0])
            type_losers = len(type_df[type_df['total_pnl'] <= 0])

            by_type.append({
                'Type': div_type,
                'Total Trades': len(type_df),
                'Winners': type_winners,
                'Losers': type_losers,
                'Win Rate %': (type_winners / len(type_df)) * 100,
                'Total P&L $': type_df['total_pnl'].sum(),
                'Avg P&L $': type_df['total_pnl'].mean()
            })

        # By timeframe AND type
        by_tf_type = []
        for tf in df['timeframe'].unique():
            for div_type in df['divergence_type'].unique():
                subset = df[(df['timeframe'] == tf) & (df['divergence_type'] == div_type)]
                if len(subset) > 0:
                    subset_winners = len(subset[subset['total_pnl'] > 0])
                    subset_losers = len(subset[subset['total_pnl'] <= 0])

                    by_tf_type.append({
                        'Timeframe': tf,
                        'Type': div_type,
                        'Total Trades': len(subset),
                        'Winners': subset_winners,
                        'Losers': subset_losers,
                        'Win Rate %': (subset_winners / len(subset)) * 100,
                        'Total P&L $': subset['total_pnl'].sum(),
                        'Avg P&L $': subset['total_pnl'].mean()
                    })

        # Quarterly performance
        df['quarter'] = pd.to_datetime(df['entry_date']).dt.to_period('Q')
        by_quarter = []
        for quarter in sorted(df['quarter'].unique()):
            q_df = df[df['quarter'] == quarter]
            q_winners = len(q_df[q_df['total_pnl'] > 0])

            by_quarter.append({
                'Quarter': str(quarter),
                'Total Trades': len(q_df),
                'Winners': q_winners,
                'Losers': len(q_df) - q_winners,
                'Win Rate %': (q_winners / len(q_df)) * 100,
                'Total P&L $': q_df['total_pnl'].sum(),
                'Avg P&L $': q_df['total_pnl'].mean()
            })

        return overall, by_timeframe, by_type, by_tf_type, by_quarter

    def export_results(self):
        """Export all results to CSV files"""
        print("Exporting results to CSV...")

        # 1. Detailed trades (every exit leg)
        trades_df = pd.DataFrame(self.trades)
        trades_csv = os.path.join(self.output_dir, 'trades_detailed.csv')
        trades_df.to_csv(trades_csv, index=False)
        print(f"  ✅ {trades_csv}")

        # 2. Trade summaries (one per trade)
        summaries_df = pd.DataFrame(self.trade_summaries)
        summaries_csv = os.path.join(self.output_dir, 'trades_summary.csv')
        summaries_df.to_csv(summaries_csv, index=False)
        print(f"  ✅ {summaries_csv}")

        # 3. Performance metrics
        overall, by_tf, by_type, by_tf_type, by_quarter = self.calculate_metrics()

        # Overall
        overall_df = pd.DataFrame([overall])
        overall_csv = os.path.join(self.output_dir, 'performance_overall.csv')
        overall_df.to_csv(overall_csv, index=False)
        print(f"  ✅ {overall_csv}")

        # By timeframe
        tf_df = pd.DataFrame(by_tf)
        tf_csv = os.path.join(self.output_dir, 'performance_by_timeframe.csv')
        tf_df.to_csv(tf_csv, index=False)
        print(f"  ✅ {tf_csv}")

        # By type
        type_df = pd.DataFrame(by_type)
        type_csv = os.path.join(self.output_dir, 'performance_by_type.csv')
        type_df.to_csv(type_csv, index=False)
        print(f"  ✅ {type_csv}")

        # By timeframe + type
        tf_type_df = pd.DataFrame(by_tf_type)
        tf_type_csv = os.path.join(self.output_dir, 'performance_by_timeframe_and_type.csv')
        tf_type_df.to_csv(tf_type_csv, index=False)
        print(f"  ✅ {tf_type_csv}")

        # Quarterly
        quarter_df = pd.DataFrame(by_quarter)
        quarter_csv = os.path.join(self.output_dir, 'performance_quarterly.csv')
        quarter_df.to_csv(quarter_csv, index=False)
        print(f"  ✅ {quarter_csv}")

        print()
        return overall, by_tf, by_type, by_tf_type, by_quarter

    def print_report(self, overall, by_tf, by_type, by_tf_type, by_quarter):
        """Print human-readable performance report"""
        print("="*70)
        print("PERFORMANCE REPORT")
        print("="*70)
        print()

        print("OVERALL PERFORMANCE")
        print("-"*70)
        for key, value in overall.items():
            if isinstance(value, float):
                print(f"  {key}: {value:,.2f}")
            else:
                print(f"  {key}: {value:,}")
        print()

        print("BREAKDOWN BY TIMEFRAME")
        print("-"*70)
        for row in by_tf:
            print(f"\n  {row['Timeframe']}:")
            print(f"    Total Trades: {row['Total Trades']}")
            print(f"    Winners: {row['Winners']} | Losers: {row['Losers']}")
            print(f"    Win Rate: {row['Win Rate %']:.1f}%")
            print(f"    Total P&L: ${row['Total P&L $']:,.2f}")
            print(f"    Avg P&L: ${row['Avg P&L $']:,.2f}")
        print()

        print("BREAKDOWN BY TYPE (Bullish vs Bearish)")
        print("-"*70)
        for row in by_type:
            print(f"\n  {row['Type']}:")
            print(f"    Total Trades: {row['Total Trades']}")
            print(f"    Winners: {row['Winners']} | Losers: {row['Losers']}")
            print(f"    Win Rate: {row['Win Rate %']:.1f}%")
            print(f"    Total P&L: ${row['Total P&L $']:,.2f}")
            print(f"    Avg P&L: ${row['Avg P&L $']:,.2f}")
        print()

        print("BREAKDOWN BY TIMEFRAME AND TYPE")
        print("-"*70)
        for row in by_tf_type:
            print(f"\n  {row['Timeframe']} - {row['Type']}:")
            print(f"    Total: {row['Total Trades']} | W: {row['Winners']} | L: {row['Losers']} | WR: {row['Win Rate %']:.1f}% | P&L: ${row['Total P&L $']:,.2f}")
        print()

        print("QUARTERLY PERFORMANCE")
        print("-"*70)
        for row in by_quarter:
            print(f"  {row['Quarter']}: {row['Total Trades']} trades | W: {row['Winners']} | WR: {row['Win Rate %']:.1f}% | P&L: ${row['Total P&L $']:,.2f}")
        print()

        print("="*70)


def main():
    """Run optimized backtest"""
    backtester = OptimizedBacktester()

    # Load existing signals
    backtester.load_signals()

    # Run backtest
    backtester.run_backtest()

    # Export results and print report
    overall, by_tf, by_type, by_tf_type, by_quarter = backtester.export_results()
    backtester.print_report(overall, by_tf, by_type, by_tf_type, by_quarter)

    print(f"All results saved to: {backtester.output_dir}")
    print()


if __name__ == "__main__":
    main()
