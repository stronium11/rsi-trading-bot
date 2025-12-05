#!/usr/bin/env python3
"""
Iterative Rule Optimizer with Price Data Caching
Optimizes position management rules phase-by-phase with cached price data
"""

import pandas as pd
import numpy as np
import ast
import os
import pickle
from datetime import datetime, timedelta
from data_fetcher import get_data_fetcher
import time
from advanced_rule_optimizer import TradeSimulator


class PriceDataCache:
    """
    Manages price data caching to avoid repeated API calls
    """

    def __init__(self, cache_dir='backtest/price_cache'):
        """Initialize cache"""
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def get_cache_path(self, ticker, entry_date):
        """Get cache file path for a specific trade"""
        # Use ticker and entry date as unique identifier
        date_str = entry_date.strftime('%Y%m%d')
        return os.path.join(self.cache_dir, f"{ticker}_{date_str}.pkl")

    def load(self, ticker, entry_date):
        """Load cached price data if available"""
        cache_path = self.get_cache_path(ticker, entry_date)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Error loading cache for {ticker}: {e}")
                return None
        return None

    def save(self, ticker, entry_date, price_df):
        """Save price data to cache"""
        cache_path = self.get_cache_path(ticker, entry_date)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(price_df, f)
        except Exception as e:
            print(f"Error saving cache for {ticker}: {e}")

    def clear(self):
        """Clear all cached data"""
        import shutil
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)


class IterativeOptimizer:
    """
    Iterative rule optimizer that tests parameters phase-by-phase
    """

    def __init__(self, results_csv='backtest/backtest_results.csv'):
        """Initialize optimizer"""
        self.results_csv = results_csv
        self.df = None
        self.data_fetcher = get_data_fetcher()
        self.cache = PriceDataCache()
        self.results_dir = 'backtest/optimization_results'
        os.makedirs(self.results_dir, exist_ok=True)

        # Baseline rules
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

    def fetch_and_cache_all_price_data(self):
        """
        Fetch price data for all trades and cache to disk
        This is done once at the beginning
        """
        print("="*70)
        print("PHASE 0: FETCHING & CACHING PRICE DATA")
        print("="*70)
        print(f"\nFetching price data for {len(self.df)} trades...")
        print("This will take ~8-10 minutes but only needs to be done once.\n")

        cached_count = 0
        fetched_count = 0

        start_time = time.time()

        for idx, row in self.df.iterrows():
            # Check cache first
            cached_data = self.cache.load(row['ticker'], row['entry_date'])

            if cached_data is not None:
                cached_count += 1
            else:
                # Fetch from API
                start_date = row['entry_date']
                end_date = start_date + timedelta(days=150)  # Max hold + buffer

                try:
                    price_df = self.data_fetcher.fetch_historical_data(
                        row['ticker'],
                        start_date=start_date,
                        end_date=end_date,
                        interval='1day'
                    )

                    if price_df is not None:
                        self.cache.save(row['ticker'], row['entry_date'], price_df)
                        fetched_count += 1

                except Exception as e:
                    print(f"  Error fetching {row['ticker']}: {e}")

            # Progress indicator
            if (idx + 1) % 50 == 0:
                elapsed = time.time() - start_time
                remaining = (elapsed / (idx + 1)) * (len(self.df) - idx - 1)
                print(f"  Progress: {idx + 1}/{len(self.df)} trades "
                      f"({cached_count} cached, {fetched_count} fetched) "
                      f"- ETA: {remaining/60:.1f} min")

        total_time = time.time() - start_time
        print(f"\n✅ Price data ready: {cached_count} from cache, {fetched_count} newly fetched")
        print(f"   Total time: {total_time/60:.1f} minutes\n")

    def test_rule_set(self, rules, rule_name):
        """
        Test a specific rule set using cached price data

        Parameters:
        - rules: Dictionary of rules
        - rule_name: Name for this scenario

        Returns:
        - Performance metrics dictionary
        """
        results = []

        for idx, row in self.df.iterrows():
            # Load from cache (fast!)
            price_df = self.cache.load(row['ticker'], row['entry_date'])

            if price_df is None:
                # Fallback: use original result if no cache
                results.append({
                    'ticker': row['ticker'],
                    'total_pnl': row['total_pnl'],
                    'total_pnl_pct': row['total_pnl_pct']
                })
                continue

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
            'rules': rules,
            'total_pnl': total_pnl,
            'total_trades': total_trades,
            'winners': winners,
            'win_rate': win_rate,
            'avg_winner': avg_winner,
            'avg_loser': avg_loser,
            'profit_factor': profit_factor,
            'avg_pnl_per_trade': total_pnl / total_trades if total_trades > 0 else 0
        }

    def phase1_optimize_stop_loss(self):
        """Phase 1: Optimize stop loss"""
        print("\n" + "="*70)
        print("PHASE 1: OPTIMIZING STOP LOSS")
        print("="*70)
        print("\nTesting stop losses: -3%, -4%, -5%, -6%, -7%, -8%\n")

        stop_tests = [3, 4, 5, 6, 7, 8]
        results = []

        for stop_pct in stop_tests:
            rules = self.baseline_rules.copy()
            rules['initial_stop_pct'] = stop_pct

            print(f"Testing -{stop_pct}% stop...", end=' ')
            start = time.time()

            result = self.test_rule_set(rules, f"Stop -{stop_pct}%")
            results.append(result)

            elapsed = time.time() - start
            print(f"P&L: ${result['total_pnl']:,.2f}, WR: {result['win_rate']:.1f}% ({elapsed:.1f}s)")

        # Find best
        best = max(results, key=lambda x: x['total_pnl'])

        print(f"\n🏆 BEST STOP LOSS: -{best['rules']['initial_stop_pct']}%")
        print(f"   Total P&L: ${best['total_pnl']:,.2f}")
        print(f"   Win Rate: {best['win_rate']:.1f}%")
        print(f"   Profit Factor: {best['profit_factor']:.2f}")

        # Save results
        df_results = pd.DataFrame(results)
        df_results.to_csv(f"{self.results_dir}/phase1_stop_loss.csv", index=False)

        return best['rules']

    def phase2_optimize_target1(self, best_rules_so_far):
        """Phase 2: Optimize Target 1 (price and sizing)"""
        print("\n" + "="*70)
        print("PHASE 2: OPTIMIZING TARGET 1")
        print("="*70)
        print("\nTesting T1 targets: 8%, 10%, 12%, 15%")
        print("Testing T1 sizing: 40%, 50%, 60%, 70%\n")

        target1_tests = [8, 10, 12, 15]
        sizing1_tests = [40, 50, 60, 70]
        results = []

        for target_pct in target1_tests:
            for size_pct in sizing1_tests:
                rules = best_rules_so_far.copy()
                rules['target1_pct'] = target_pct
                rules['target1_size'] = size_pct

                # Adjust T2 sizing (remaining after T1)
                rules['target2_size'] = int((100 - size_pct) * 0.625)  # 25% of original becomes larger share

                print(f"Testing T1 +{target_pct}% ({size_pct}%)...", end=' ')
                start = time.time()

                result = self.test_rule_set(rules, f"T1 +{target_pct}% ({size_pct}%)")
                results.append(result)

                elapsed = time.time() - start
                print(f"P&L: ${result['total_pnl']:,.2f}, WR: {result['win_rate']:.1f}% ({elapsed:.1f}s)")

        # Find best
        best = max(results, key=lambda x: x['total_pnl'])

        print(f"\n🏆 BEST TARGET 1: +{best['rules']['target1_pct']}% closing {best['rules']['target1_size']}%")
        print(f"   Total P&L: ${best['total_pnl']:,.2f}")
        print(f"   Win Rate: {best['win_rate']:.1f}%")
        print(f"   Profit Factor: {best['profit_factor']:.2f}")

        # Save results
        df_results = pd.DataFrame(results)
        df_results.to_csv(f"{self.results_dir}/phase2_target1.csv", index=False)

        return best['rules']

    def phase3_optimize_target2(self, best_rules_so_far):
        """Phase 3: Optimize Target 2 (price and sizing)"""
        print("\n" + "="*70)
        print("PHASE 3: OPTIMIZING TARGET 2")
        print("="*70)
        print("\nTesting T2 targets: 15%, 18%, 20%, 25%")
        print("Testing T2 sizing: 15%, 20%, 25%, 30%\n")

        target2_tests = [15, 18, 20, 25]
        sizing2_tests = [15, 20, 25, 30]
        results = []

        for target_pct in target2_tests:
            for size_pct in sizing2_tests:
                rules = best_rules_so_far.copy()
                rules['target2_pct'] = target_pct
                rules['target2_size'] = size_pct

                print(f"Testing T2 +{target_pct}% ({size_pct}%)...", end=' ')
                start = time.time()

                result = self.test_rule_set(rules, f"T2 +{target_pct}% ({size_pct}%)")
                results.append(result)

                elapsed = time.time() - start
                print(f"P&L: ${result['total_pnl']:,.2f}, WR: {result['win_rate']:.1f}% ({elapsed:.1f}s)")

        # Find best
        best = max(results, key=lambda x: x['total_pnl'])

        print(f"\n🏆 BEST TARGET 2: +{best['rules']['target2_pct']}% closing {best['rules']['target2_size']}%")
        print(f"   Total P&L: ${best['total_pnl']:,.2f}")
        print(f"   Win Rate: {best['win_rate']:.1f}%")
        print(f"   Profit Factor: {best['profit_factor']:.2f}")

        # Save results
        df_results = pd.DataFrame(results)
        df_results.to_csv(f"{self.results_dir}/phase3_target2.csv", index=False)

        return best['rules']

    def phase4_final_tuning(self, best_rules_so_far):
        """Phase 4: Test trailing stops and T3 options"""
        print("\n" + "="*70)
        print("PHASE 4: FINAL TUNING (Trailing Stops & T3)")
        print("="*70)
        print("\nTesting trailing stops: None, 10%, 15%")
        print("Testing T3 targets: 30%, 35%, 50%\n")

        results = []

        # Test trailing stops
        for trailing_pct in [None, 10, 15]:
            for t3_pct in [30, 35, 50]:
                rules = best_rules_so_far.copy()
                rules['use_trailing_stop'] = trailing_pct is not None
                if trailing_pct:
                    rules['trailing_stop_pct'] = trailing_pct
                rules['target3_pct'] = t3_pct

                trail_str = f"{trailing_pct}%" if trailing_pct else "None"
                print(f"Testing Trailing {trail_str}, T3 +{t3_pct}%...", end=' ')
                start = time.time()

                result = self.test_rule_set(rules, f"Trail {trail_str}, T3 +{t3_pct}%")
                results.append(result)

                elapsed = time.time() - start
                print(f"P&L: ${result['total_pnl']:,.2f}, WR: {result['win_rate']:.1f}% ({elapsed:.1f}s)")

        # Find best
        best = max(results, key=lambda x: x['total_pnl'])

        trail_str = f"{best['rules'].get('trailing_stop_pct', 'None')}%" if best['rules']['use_trailing_stop'] else "None"
        print(f"\n🏆 BEST FINAL CONFIG: Trailing {trail_str}, T3 +{best['rules']['target3_pct']}%")
        print(f"   Total P&L: ${best['total_pnl']:,.2f}")
        print(f"   Win Rate: {best['win_rate']:.1f}%")
        print(f"   Profit Factor: {best['profit_factor']:.2f}")

        # Save results
        df_results = pd.DataFrame(results)
        df_results.to_csv(f"{self.results_dir}/phase4_final_tuning.csv", index=False)

        return best['rules']

    def run_full_optimization(self):
        """Run complete iterative optimization"""
        print("\n" + "#"*70)
        print("# ITERATIVE RULE OPTIMIZATION")
        print("# Multi-Phase Position Management Optimizer")
        print("#"*70)

        self.load_data()

        # Phase 0: Cache price data
        self.fetch_and_cache_all_price_data()

        # Get baseline performance
        print("\n" + "="*70)
        print("BASELINE PERFORMANCE")
        print("="*70)
        baseline_result = self.test_rule_set(self.baseline_rules, "Baseline")
        print(f"\nCurrent System Performance:")
        print(f"  Total P&L: ${baseline_result['total_pnl']:,.2f}")
        print(f"  Win Rate: {baseline_result['win_rate']:.1f}%")
        print(f"  Profit Factor: {baseline_result['profit_factor']:.2f}")
        print(f"  Avg per Trade: ${baseline_result['avg_pnl_per_trade']:.2f}")

        # Run optimization phases
        best_rules = self.baseline_rules.copy()

        best_rules = self.phase1_optimize_stop_loss()
        best_rules = self.phase2_optimize_target1(best_rules)
        best_rules = self.phase3_optimize_target2(best_rules)
        best_rules = self.phase4_final_tuning(best_rules)

        # Final comparison
        print("\n" + "="*70)
        print("FINAL RESULTS")
        print("="*70)

        final_result = self.test_rule_set(best_rules, "Optimized Rules")

        print(f"\nBASELINE:")
        print(f"  Total P&L: ${baseline_result['total_pnl']:,.2f}")
        print(f"  Win Rate: {baseline_result['win_rate']:.1f}%")
        print(f"  Profit Factor: {baseline_result['profit_factor']:.2f}")

        print(f"\nOPTIMIZED:")
        print(f"  Total P&L: ${final_result['total_pnl']:,.2f}")
        print(f"  Win Rate: {final_result['win_rate']:.1f}%")
        print(f"  Profit Factor: {final_result['profit_factor']:.2f}")

        improvement = final_result['total_pnl'] - baseline_result['total_pnl']
        improvement_pct = (improvement / baseline_result['total_pnl'] * 100) if baseline_result['total_pnl'] != 0 else 0

        print(f"\nIMPROVEMENT:")
        print(f"  P&L: +${improvement:,.2f} (+{improvement_pct:.1f}%)")
        print(f"  Win Rate: +{final_result['win_rate'] - baseline_result['win_rate']:.1f}%")

        print(f"\n🏆 OPTIMAL RULES:")
        print(f"  Stop Loss: -{best_rules['initial_stop_pct']}%")
        print(f"  Target 1: +{best_rules['target1_pct']}% (close {best_rules['target1_size']}%)")
        print(f"  Target 2: +{best_rules['target2_pct']}% (close {best_rules['target2_size']}%)")
        print(f"  Target 3: +{best_rules['target3_pct']}%")
        trail_str = f"{best_rules.get('trailing_stop_pct', 'N/A')}%" if best_rules['use_trailing_stop'] else "None"
        print(f"  Trailing Stop: {trail_str}")
        print(f"  Max Hold: {best_rules['max_hold_days']} days")

        # Save final rules
        import json
        with open(f"{self.results_dir}/optimal_rules.json", 'w') as f:
            json.dump(best_rules, f, indent=2)

        print(f"\n✅ Optimization complete! Results saved to {self.results_dir}/")
        print("\n" + "#"*70)


if __name__ == "__main__":
    optimizer = IterativeOptimizer()
    optimizer.run_full_optimization()
