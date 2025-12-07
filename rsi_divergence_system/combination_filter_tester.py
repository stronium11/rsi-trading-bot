"""
Combination Filter Tester

Tests filter combinations - only skip trades when 2 or more filters agree.

This is less aggressive than individual filters and should preserve more winning trades.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from data_fetcher import get_data_fetcher
import ta


class CombinationFilterTester:
    """
    Tests filter combinations - skip only when multiple filters agree
    """

    def __init__(self, baseline_csv='backtest/optimized_results/trades_summary.csv'):
        """Initialize tester"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.baseline_csv = os.path.join(script_dir, baseline_csv)
        self.baseline_df = None
        self.data_fetcher = get_data_fetcher()

        # Market data cache
        self.spy_data = None
        self.vix_data = None

        # Output directory
        self.output_dir = os.path.join(script_dir, 'backtest', 'filter_tests')
        os.makedirs(self.output_dir, exist_ok=True)

    def load_baseline(self):
        """Load baseline results"""
        print("Loading baseline results...")
        self.baseline_df = pd.read_csv(self.baseline_csv)
        self.baseline_df['entry_date'] = pd.to_datetime(self.baseline_df['entry_date'])
        self.baseline_df['signal_date'] = pd.to_datetime(self.baseline_df['signal_date'])
        print(f"Loaded {len(self.baseline_df)} baseline trades")
        print(f"Date range: {self.baseline_df['signal_date'].min()} to {self.baseline_df['signal_date'].max()}")
        print()

    def fetch_market_data(self):
        """Fetch SPY and VIX data"""
        print("Fetching market data...")

        start_date = self.baseline_df['signal_date'].min() - timedelta(days=250)
        end_date = self.baseline_df['signal_date'].max()

        # Fetch SPY
        print("  Fetching SPY...")
        self.spy_data = self.data_fetcher.fetch_historical_data(
            'SPY',
            start_date=start_date,
            end_date=end_date,
            interval='1day'
        )

        if self.spy_data is not None:
            self.spy_data['ma_50'] = self.spy_data['close'].rolling(window=50).mean()
            self.spy_data['ma_200'] = self.spy_data['close'].rolling(window=200).mean()
            self.spy_data['adx'] = ta.trend.ADXIndicator(
                high=self.spy_data['high'],
                low=self.spy_data['low'],
                close=self.spy_data['close'],
                window=14
            ).adx()
            print(f"    SPY: {len(self.spy_data)} days loaded")

        # Try multiple VIX tickers
        print("  Fetching VIX...")
        vix_tickers = ['VIX', '^VIX', 'VIXM']

        for ticker in vix_tickers:
            try:
                self.vix_data = self.data_fetcher.fetch_historical_data(
                    ticker,
                    start_date=start_date,
                    end_date=end_date,
                    interval='1day'
                )

                if self.vix_data is not None and len(self.vix_data) > 0:
                    print(f"    VIX: {len(self.vix_data)} days loaded (using {ticker})")
                    break
            except Exception as e:
                continue

        if self.vix_data is None or len(self.vix_data) == 0:
            print(f"    WARNING: Could not fetch VIX data. Will skip VIX filter.")
            print(f"    Tried tickers: {vix_tickers}")

        print()

    def get_spy_value(self, date, column):
        """Get SPY value at date"""
        if self.spy_data is None:
            return None
        before = self.spy_data[self.spy_data.index <= date]
        if len(before) == 0:
            return None
        return before.iloc[-1][column]

    def get_vix_value(self, date):
        """Get VIX value at date"""
        if self.vix_data is None:
            return None
        before = self.vix_data[self.vix_data.index <= date]
        if len(before) == 0:
            return None
        return before.iloc[-1]['close']

    def evaluate_filters_for_trade(self, row):
        """
        Evaluate all 5 filters for a single trade

        Returns dict with filter verdicts (True = skip, False = take)
        """
        signal_date = row['signal_date']
        is_bearish = row['divergence_type'] == 'Bearish'
        is_bullish = row['divergence_type'] == 'Bullish'

        verdicts = {}

        # Filter 1: Market Trend (SPY MA)
        spy_close = self.get_spy_value(signal_date, 'close')
        spy_ma50 = self.get_spy_value(signal_date, 'ma_50')
        spy_ma200 = self.get_spy_value(signal_date, 'ma_200')

        if spy_close and spy_ma50 and spy_ma200:
            strong_bull = (spy_close > spy_ma200) and (spy_ma50 > spy_ma200)
            verdicts['market_trend'] = strong_bull and is_bearish
        else:
            verdicts['market_trend'] = False

        # Filter 2: Volatility (VIX)
        vix = self.get_vix_value(signal_date)
        if vix:
            verdicts['volatility'] = vix < 15  # Skip all trades when VIX < 15
        else:
            verdicts['volatility'] = False

        # Filter 3: Market Breadth (SPY distance from MA)
        if spy_close and spy_ma200:
            pct_from_ma = ((spy_close - spy_ma200) / spy_ma200) * 100
            skip_bearish = pct_from_ma > 10 and is_bearish
            skip_bullish = pct_from_ma < -10 and is_bullish
            verdicts['market_breadth'] = skip_bearish or skip_bullish
        else:
            verdicts['market_breadth'] = False

        # Filter 4: Trend Strength (ADX)
        adx = self.get_spy_value(signal_date, 'adx')
        if adx and not pd.isna(adx):
            verdicts['trend_strength'] = adx > 25  # Skip all when strong trend
        else:
            verdicts['trend_strength'] = False

        # Filter 5: Beta/Correlation
        if adx and not pd.isna(adx) and spy_close and spy_ma50:
            strong_trend = adx > 25
            spy_bullish = spy_close > spy_ma50
            spy_bearish = spy_close < spy_ma50

            skip_counter_trend = (strong_trend and spy_bullish and is_bearish) or \
                                (strong_trend and spy_bearish and is_bullish)
            verdicts['beta'] = skip_counter_trend
        else:
            verdicts['beta'] = False

        return verdicts

    def test_combination_filters(self, min_filters_required=2):
        """
        Test combination: only skip when N or more filters agree

        Args:
            min_filters_required: How many filters must agree to skip (2, 3, 4, or 5)
        """
        print("="*70)
        print(f"COMBINATION FILTER TEST: Skip when {min_filters_required}+ filters agree")
        print("="*70)
        print()
        print("Filter Logic:")
        print(f"  Only skip a trade when {min_filters_required} or more filters say 'skip'")
        print()
        print("Filters:")
        print("  1. Market Trend: Skip Bearish in strong bull (SPY > 200 MA, 50 > 200)")
        print("  2. Volatility: Skip all when VIX < 15")
        print("  3. Market Breadth: Skip counter-trend when SPY ±10% from 200 MA")
        print("  4. Trend Strength: Skip all when ADX > 25")
        print("  5. Beta/Correlation: Skip counter-trend when ADX > 25")
        print()

        # Evaluate all filters for all trades
        filtered_df = self.baseline_df.copy()
        filtered_df['skip_count'] = 0
        filtered_df['filter_verdicts'] = ''

        for idx, row in filtered_df.iterrows():
            verdicts = self.evaluate_filters_for_trade(row)

            skip_count = sum(verdicts.values())
            filtered_df.at[idx, 'skip_count'] = skip_count

            # Store which filters said skip
            skip_filters = [name for name, skip in verdicts.items() if skip]
            filtered_df.at[idx, 'filter_verdicts'] = ', '.join(skip_filters) if skip_filters else 'None'

        # Apply combination filter
        filtered_df['filter_applied'] = filtered_df['skip_count'] >= min_filters_required

        # Generate report
        self._generate_combination_report(
            filtered_df,
            min_filters_required,
            filter_name=f"Combination_{min_filters_required}_Filters"
        )

    def _generate_combination_report(self, filtered_df, min_filters, filter_name):
        """Generate report for combination filter"""

        # Baseline
        baseline_trades = len(filtered_df)
        baseline_pnl = filtered_df['total_pnl'].sum()
        baseline_winners = len(filtered_df[filtered_df['total_pnl'] > 0])
        baseline_wr = (baseline_winners / baseline_trades) * 100

        # Filtered
        passed_df = filtered_df[~filtered_df['filter_applied']]
        filtered_trades = len(passed_df)
        filtered_pnl = passed_df['total_pnl'].sum()
        filtered_winners = len(passed_df[passed_df['total_pnl'] > 0])
        filtered_wr = (filtered_winners / filtered_trades) * 100 if filtered_trades > 0 else 0

        # Skipped
        skipped_df = filtered_df[filtered_df['filter_applied']]
        skipped_trades = len(skipped_df)
        skipped_pnl = skipped_df['total_pnl'].sum()
        skipped_winners = len(skipped_df[skipped_df['total_pnl'] > 0])

        # Print report
        print("RESULTS")
        print("-"*70)
        print()

        print("BASELINE (No Filters):")
        print(f"  Total Trades: {baseline_trades}")
        print(f"  Winners: {baseline_winners} | Win Rate: {baseline_wr:.1f}%")
        print(f"  Total P&L: ${baseline_pnl:,.2f}")
        print()

        print(f"WITH {min_filters}+ FILTERS REQUIRED:")
        print(f"  Trades Passed: {filtered_trades}")
        print(f"  Trades Skipped: {skipped_trades} ({skipped_trades/baseline_trades*100:.1f}%)")
        print(f"  Winners: {filtered_winners} | Win Rate: {filtered_wr:.1f}%")
        print(f"  Total P&L: ${filtered_pnl:,.2f}")
        print()

        print("IMPACT:")
        pnl_change = filtered_pnl - baseline_pnl
        pnl_change_pct = (pnl_change / baseline_pnl * 100) if baseline_pnl != 0 else 0
        print(f"  P&L Change: ${pnl_change:,.2f} ({pnl_change_pct:+.1f}%)")
        print(f"  Win Rate Change: {filtered_wr - baseline_wr:+.1f}%")
        print(f"  Skipped Trades P&L: ${skipped_pnl:,.2f}")
        print()

        if skipped_trades > 0:
            print("SKIPPED TRADES ANALYSIS:")
            print(f"  Winners Skipped: {skipped_winners} | Losers Skipped: {skipped_trades - skipped_winners}")

            # Distribution by number of filters
            print()
            print("  Distribution by agreement level:")
            for count in range(min_filters, 6):
                count_df = skipped_df[skipped_df['skip_count'] == count]
                if len(count_df) > 0:
                    count_pnl = count_df['total_pnl'].sum()
                    count_winners = len(count_df[count_df['total_pnl'] > 0])
                    print(f"    {count} filters agreed: {len(count_df)} trades, {count_winners} winners, ${count_pnl:,.2f} P&L")

            # By type
            print()
            print("  By divergence type:")
            for div_type in skipped_df['divergence_type'].unique():
                type_df = skipped_df[skipped_df['divergence_type'] == div_type]
                type_pnl = type_df['total_pnl'].sum()
                type_winners = len(type_df[type_df['total_pnl'] > 0])
                print(f"    {div_type}: {len(type_df)} trades, {type_winners} winners, ${type_pnl:,.2f} P&L")

        print()

        # Export
        output_csv = os.path.join(self.output_dir, f'{filter_name}_results.csv')
        filtered_df.to_csv(output_csv, index=False)
        print(f"Detailed results exported to: {output_csv}")
        print()
        print("="*70)
        print()

    def run_all_combinations(self):
        """Test different combination thresholds"""
        print("="*70)
        print("COMBINATION FILTER TESTING")
        print("="*70)
        print()

        self.load_baseline()
        self.fetch_market_data()

        # Test different thresholds
        for min_filters in [2, 3, 4, 5]:
            self.test_combination_filters(min_filters_required=min_filters)

            if min_filters < 5:
                input(f"\nPress Enter to test {min_filters+1}+ filters combination...")
                print("\n")

        print("="*70)
        print("ALL COMBINATION TESTS COMPLETE")
        print("="*70)
        print(f"Results saved to: {self.output_dir}")


def main():
    """Run combination filter tests"""
    tester = CombinationFilterTester()
    tester.run_all_combinations()


if __name__ == "__main__":
    main()
