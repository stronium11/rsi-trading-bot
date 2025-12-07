"""
Filter Testing Framework

Tests individual market filters against baseline backtest results.
Each filter is tested in isolation to evaluate its impact.

Filters to test:
1. Market Trend Filter (SPY 50/200 MA)
2. Volatility Filter (VIX regime)
3. Market Breadth Filter (% stocks above 200 MA)
4. Trend Strength Filter (ADX on SPY)
5. Beta/Correlation Filter

Each filter is tested independently - NO COMBINATIONS.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from data_fetcher import get_data_fetcher
import ta  # For technical indicators


class FilterTester:
    """
    Tests individual market filters against baseline results
    """

    def __init__(self, baseline_csv='backtest/optimized_results/trades_summary.csv'):
        """Initialize filter tester"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.baseline_csv = os.path.join(script_dir, baseline_csv)
        self.baseline_df = None
        self.data_fetcher = get_data_fetcher()

        # Cache for market data
        self.spy_data = None
        self.vix_data = None

        # Output directory
        self.output_dir = os.path.join(script_dir, 'backtest', 'filter_tests')
        os.makedirs(self.output_dir, exist_ok=True)

    def load_baseline(self):
        """Load baseline backtest results"""
        print("Loading baseline results...")
        self.baseline_df = pd.read_csv(self.baseline_csv)
        self.baseline_df['entry_date'] = pd.to_datetime(self.baseline_df['entry_date'])
        self.baseline_df['signal_date'] = pd.to_datetime(self.baseline_df['signal_date'])
        print(f"Loaded {len(self.baseline_df)} baseline trades\n")

    def fetch_spy_data(self):
        """Fetch SPY historical data for the full backtest period"""
        print("Fetching SPY data...")

        start_date = self.baseline_df['signal_date'].min() - timedelta(days=250)  # Extra for 200 MA
        end_date = self.baseline_df['signal_date'].max()

        self.spy_data = self.data_fetcher.fetch_historical_data(
            'SPY',
            start_date=start_date,
            end_date=end_date,
            interval='1day'
        )

        if self.spy_data is not None:
            # Calculate indicators
            self.spy_data['ma_50'] = self.spy_data['close'].rolling(window=50).mean()
            self.spy_data['ma_200'] = self.spy_data['close'].rolling(window=200).mean()

            # Calculate ADX
            self.spy_data['adx'] = ta.trend.ADXIndicator(
                high=self.spy_data['high'],
                low=self.spy_data['low'],
                close=self.spy_data['close'],
                window=14
            ).adx()

            print(f"  SPY data loaded: {len(self.spy_data)} days")
        else:
            print("  ERROR: Failed to fetch SPY data")

    def fetch_vix_data(self):
        """Fetch VIX historical data"""
        print("Fetching VIX data...")

        start_date = self.baseline_df['signal_date'].min()
        end_date = self.baseline_df['signal_date'].max()

        self.vix_data = self.data_fetcher.fetch_historical_data(
            '^VIX',
            start_date=start_date,
            end_date=end_date,
            interval='1day'
        )

        if self.vix_data is not None:
            print(f"  VIX data loaded: {len(self.vix_data)} days")
        else:
            print("  ERROR: Failed to fetch VIX data")

    def get_spy_value_at_date(self, date, column):
        """Get SPY indicator value on or before given date"""
        if self.spy_data is None:
            return None

        # Get closest date on or before signal date
        spy_before = self.spy_data[self.spy_data.index <= date]
        if len(spy_before) == 0:
            return None

        return spy_before.iloc[-1][column]

    def get_vix_value_at_date(self, date):
        """Get VIX value on or before given date"""
        if self.vix_data is None:
            return None

        vix_before = self.vix_data[self.vix_data.index <= date]
        if len(vix_before) == 0:
            return None

        return vix_before.iloc[-1]['close']

    # ========================================================================
    # FILTER 1: Market Trend Filter (SPY MA)
    # ========================================================================

    def test_market_trend_filter(self):
        """
        Test Market Trend Filter

        Rule: Skip Bearish divergences when:
        - SPY > 200-day MA AND
        - 50-day MA > 200-day MA (Golden Cross)
        """
        print("="*70)
        print("FILTER TEST 1: Market Trend Filter (SPY Moving Averages)")
        print("="*70)
        print()
        print("Filter Rule:")
        print("  IF SPY > 200 MA AND 50 MA > 200 MA (Strong Bull Market)")
        print("  THEN skip Bearish divergences")
        print()

        if self.spy_data is None:
            self.fetch_spy_data()

        # Apply filter
        filtered_df = self.baseline_df.copy()
        filtered_df['filter_applied'] = False

        for idx, row in filtered_df.iterrows():
            signal_date = row['signal_date']

            # Get SPY values at signal date
            spy_close = self.get_spy_value_at_date(signal_date, 'close')
            spy_ma50 = self.get_spy_value_at_date(signal_date, 'ma_50')
            spy_ma200 = self.get_spy_value_at_date(signal_date, 'ma_200')

            if spy_close is None or spy_ma50 is None or spy_ma200 is None:
                continue

            # Check filter condition
            strong_bull = (spy_close > spy_ma200) and (spy_ma50 > spy_ma200)
            is_bearish = row['divergence_type'] == 'Bearish'

            if strong_bull and is_bearish:
                filtered_df.at[idx, 'filter_applied'] = True

        # Calculate metrics
        self._generate_filter_report(
            filtered_df,
            filter_name="Market_Trend_Filter",
            filter_description="SPY 50/200 MA - Skip Bearish in strong bull markets"
        )

    # ========================================================================
    # FILTER 2: Volatility Filter (VIX)
    # ========================================================================

    def test_volatility_filter(self):
        """
        Test Volatility Filter

        Rule: Skip trades when VIX < 15 (low volatility = strong trends)
        """
        print("="*70)
        print("FILTER TEST 2: Volatility Filter (VIX Regime)")
        print("="*70)
        print()
        print("Filter Rule:")
        print("  IF VIX < 15 (Low Volatility = Strong Directional Moves)")
        print("  THEN skip ALL trades (divergences less reliable)")
        print()

        if self.vix_data is None:
            self.fetch_vix_data()

        # Apply filter
        filtered_df = self.baseline_df.copy()
        filtered_df['filter_applied'] = False

        for idx, row in filtered_df.iterrows():
            signal_date = row['signal_date']
            vix_value = self.get_vix_value_at_date(signal_date)

            if vix_value is None:
                continue

            # Filter: Skip if VIX < 15
            if vix_value < 15:
                filtered_df.at[idx, 'filter_applied'] = True

        self._generate_filter_report(
            filtered_df,
            filter_name="Volatility_Filter",
            filter_description="VIX < 15 - Skip all trades in low volatility"
        )

    # ========================================================================
    # FILTER 3: Market Breadth Filter
    # ========================================================================

    def test_market_breadth_filter(self):
        """
        Test Market Breadth Filter

        Rule:
        - Skip Bearish when breadth > 70% (strong bull)
        - Skip Bullish when breadth < 30% (strong bear)

        Note: This requires fetching S&P 500 constituents - simplified version
        uses SPY position relative to MA as proxy
        """
        print("="*70)
        print("FILTER TEST 3: Market Breadth Filter (Simplified)")
        print("="*70)
        print()
        print("Filter Rule (Simplified - using SPY vs MAs as proxy):")
        print("  IF SPY is > 10% above 200 MA (Strong Bull)")
        print("  THEN skip Bearish divergences")
        print("  ")
        print("  IF SPY is > 10% below 200 MA (Strong Bear)")
        print("  THEN skip Bullish divergences")
        print()

        if self.spy_data is None:
            self.fetch_spy_data()

        # Apply filter
        filtered_df = self.baseline_df.copy()
        filtered_df['filter_applied'] = False

        for idx, row in filtered_df.iterrows():
            signal_date = row['signal_date']

            spy_close = self.get_spy_value_at_date(signal_date, 'close')
            spy_ma200 = self.get_spy_value_at_date(signal_date, 'ma_200')

            if spy_close is None or spy_ma200 is None:
                continue

            # Calculate % above/below 200 MA
            pct_from_ma = ((spy_close - spy_ma200) / spy_ma200) * 100

            is_bearish = row['divergence_type'] == 'Bearish'
            is_bullish = row['divergence_type'] == 'Bullish'

            # Strong bull market (>10% above MA) - skip Bearish
            if pct_from_ma > 10 and is_bearish:
                filtered_df.at[idx, 'filter_applied'] = True

            # Strong bear market (>10% below MA) - skip Bullish
            if pct_from_ma < -10 and is_bullish:
                filtered_df.at[idx, 'filter_applied'] = True

        self._generate_filter_report(
            filtered_df,
            filter_name="Market_Breadth_Filter",
            filter_description="SPY ±10% from 200 MA - Skip counter-trend trades"
        )

    # ========================================================================
    # FILTER 4: Trend Strength Filter (ADX)
    # ========================================================================

    def test_trend_strength_filter(self):
        """
        Test Trend Strength Filter (ADX)

        Rule: Skip trades when ADX > 25 (strong trend, divergences less reliable)
        """
        print("="*70)
        print("FILTER TEST 4: Trend Strength Filter (ADX)")
        print("="*70)
        print()
        print("Filter Rule:")
        print("  IF SPY ADX > 25 (Strong Trend)")
        print("  THEN skip ALL trades (divergences less reliable in trending markets)")
        print()

        if self.spy_data is None:
            self.fetch_spy_data()

        # Apply filter
        filtered_df = self.baseline_df.copy()
        filtered_df['filter_applied'] = False

        for idx, row in filtered_df.iterrows():
            signal_date = row['signal_date']
            adx_value = self.get_spy_value_at_date(signal_date, 'adx')

            if adx_value is None or pd.isna(adx_value):
                continue

            # Filter: Skip if ADX > 25
            if adx_value > 25:
                filtered_df.at[idx, 'filter_applied'] = True

        self._generate_filter_report(
            filtered_df,
            filter_name="Trend_Strength_Filter",
            filter_description="ADX > 25 - Skip all trades in strong trends"
        )

    # ========================================================================
    # FILTER 5: Beta/Correlation Filter
    # ========================================================================

    def test_beta_filter(self):
        """
        Test Beta/Correlation Filter

        Rule: Skip trades on high-beta stocks when market is trending strongly

        Note: This requires calculating beta for each stock - simplified version
        skips trades when both ADX > 25 AND stock is moving with SPY
        """
        print("="*70)
        print("FILTER TEST 5: Beta/Correlation Filter (Simplified)")
        print("="*70)
        print()
        print("Filter Rule (Simplified):")
        print("  IF SPY ADX > 25 (Strong Trend)")
        print("  AND SPY is trending in OPPOSITE direction to signal")
        print("  THEN skip trade")
        print()
        print("  Example: Skip Bearish when SPY trending up strongly")
        print()

        if self.spy_data is None:
            self.fetch_spy_data()

        # Apply filter
        filtered_df = self.baseline_df.copy()
        filtered_df['filter_applied'] = False

        for idx, row in filtered_df.iterrows():
            signal_date = row['signal_date']

            adx_value = self.get_spy_value_at_date(signal_date, 'adx')
            spy_close = self.get_spy_value_at_date(signal_date, 'close')
            spy_ma50 = self.get_spy_value_at_date(signal_date, 'ma_50')

            if adx_value is None or pd.isna(adx_value) or spy_close is None or spy_ma50 is None:
                continue

            # Strong trend condition
            strong_trend = adx_value > 25

            # Determine SPY direction
            spy_bullish = spy_close > spy_ma50
            spy_bearish = spy_close < spy_ma50

            is_bearish_signal = row['divergence_type'] == 'Bearish'
            is_bullish_signal = row['divergence_type'] == 'Bullish'

            # Skip counter-trend trades in strong trending markets
            if strong_trend and spy_bullish and is_bearish_signal:
                filtered_df.at[idx, 'filter_applied'] = True

            if strong_trend and spy_bearish and is_bullish_signal:
                filtered_df.at[idx, 'filter_applied'] = True

        self._generate_filter_report(
            filtered_df,
            filter_name="Beta_Filter",
            filter_description="ADX > 25 + Counter-trend - Skip when fighting strong market"
        )

    # ========================================================================
    # Report Generation
    # ========================================================================

    def _generate_filter_report(self, filtered_df, filter_name, filter_description):
        """Generate comprehensive comparison report"""

        # Baseline metrics (all trades)
        baseline_trades = len(filtered_df)
        baseline_pnl = filtered_df['total_pnl'].sum()
        baseline_winners = len(filtered_df[filtered_df['total_pnl'] > 0])
        baseline_wr = (baseline_winners / baseline_trades) * 100

        # Filtered metrics (trades that passed filter)
        passed_df = filtered_df[~filtered_df['filter_applied']]
        filtered_trades = len(passed_df)
        filtered_pnl = passed_df['total_pnl'].sum()
        filtered_winners = len(passed_df[passed_df['total_pnl'] > 0])
        filtered_wr = (filtered_winners / filtered_trades) * 100 if filtered_trades > 0 else 0

        # Skipped trades analysis
        skipped_df = filtered_df[filtered_df['filter_applied']]
        skipped_trades = len(skipped_df)
        skipped_pnl = skipped_df['total_pnl'].sum()

        # Print report
        print(f"RESULTS")
        print("-"*70)
        print()

        print(f"BASELINE (No Filter):")
        print(f"  Total Trades: {baseline_trades}")
        print(f"  Winners: {baseline_winners} | Win Rate: {baseline_wr:.1f}%")
        print(f"  Total P&L: ${baseline_pnl:,.2f}")
        print()

        print(f"WITH FILTER APPLIED:")
        print(f"  Trades Passed: {filtered_trades}")
        print(f"  Trades Skipped: {skipped_trades} ({skipped_trades/baseline_trades*100:.1f}%)")
        print(f"  Winners: {filtered_winners} | Win Rate: {filtered_wr:.1f}%")
        print(f"  Total P&L: ${filtered_pnl:,.2f}")
        print()

        print(f"IMPACT OF FILTER:")
        print(f"  P&L Change: ${filtered_pnl - baseline_pnl:,.2f} ({((filtered_pnl - baseline_pnl) / baseline_pnl * 100):.1f}%)")
        print(f"  Win Rate Change: {filtered_wr - baseline_wr:+.1f}%")
        print(f"  Skipped Trades P&L: ${skipped_pnl:,.2f}")
        print()

        # Analyze what was filtered
        if skipped_trades > 0:
            print(f"SKIPPED TRADES BREAKDOWN:")

            # By type
            skipped_bullish = len(skipped_df[skipped_df['divergence_type'] == 'Bullish'])
            skipped_bearish = len(skipped_df[skipped_df['divergence_type'] == 'Bearish'])
            print(f"  Bullish: {skipped_bullish} | Bearish: {skipped_bearish}")

            # By timeframe
            for tf in skipped_df['timeframe'].unique():
                tf_count = len(skipped_df[skipped_df['timeframe'] == tf])
                tf_pnl = skipped_df[skipped_df['timeframe'] == tf]['total_pnl'].sum()
                print(f"  {tf}: {tf_count} trades, ${tf_pnl:,.2f} P&L")

            # Winners vs losers in skipped
            skipped_winners = len(skipped_df[skipped_df['total_pnl'] > 0])
            skipped_losers = len(skipped_df[skipped_df['total_pnl'] <= 0])
            print(f"  Skipped Winners: {skipped_winners} | Skipped Losers: {skipped_losers}")
            print()

        # Export detailed results
        output_csv = os.path.join(self.output_dir, f'{filter_name}_results.csv')
        filtered_df.to_csv(output_csv, index=False)
        print(f"Detailed results exported to: {output_csv}")
        print()
        print("="*70)
        print()

    def run_all_tests(self):
        """Run all filter tests sequentially"""
        print("\n")
        print("="*70)
        print("FILTER TESTING FRAMEWORK")
        print("="*70)
        print()
        print("Testing 5 filters independently against baseline results")
        print()

        # Load baseline
        self.load_baseline()

        # Test each filter
        print("\n\n")
        self.test_market_trend_filter()

        input("Press Enter to continue to next filter test...")
        print("\n\n")
        self.test_volatility_filter()

        input("Press Enter to continue to next filter test...")
        print("\n\n")
        self.test_market_breadth_filter()

        input("Press Enter to continue to next filter test...")
        print("\n\n")
        self.test_trend_strength_filter()

        input("Press Enter to continue to next filter test...")
        print("\n\n")
        self.test_beta_filter()

        print("\n")
        print("="*70)
        print("ALL FILTER TESTS COMPLETE")
        print("="*70)
        print(f"Results saved to: {self.output_dir}")
        print()


def main():
    """Run filter tests"""
    tester = FilterTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
