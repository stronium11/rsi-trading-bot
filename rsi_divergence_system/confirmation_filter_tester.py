"""
Confirmation Filter Tester

FLIPPED LOGIC: Use market conditions as ENTRY CONFIRMATION, not exit filters.

Only take trades when market structure AGREES with divergence direction.

Rules:
- Bullish divergence → Only enter if market structure is BULLISH
- Bearish divergence → Only enter if market structure is BEARISH

Test each filter independently as confirmation requirement.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from data_fetcher import get_data_fetcher
import ta


class ConfirmationFilterTester:
    """
    Tests market condition filters as ENTRY CONFIRMATION (not exit filters)
    """

    def __init__(self, baseline_csv='backtest/optimized_results/trades_summary.csv'):
        """Initialize tester"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.baseline_csv = os.path.join(script_dir, baseline_csv)
        self.baseline_df = None
        self.data_fetcher = get_data_fetcher()

        # Market data
        self.spy_data = None
        self.vix_data = None

        # Output
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

        # SPY
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
            print(f"    SPY: {len(self.spy_data)} days")

        # VIX
        print("  Fetching VIX...")
        for ticker in ['VIX', '^VIX', 'VIXM']:
            try:
                self.vix_data = self.data_fetcher.fetch_historical_data(
                    ticker,
                    start_date=start_date,
                    end_date=end_date,
                    interval='1day'
                )
                if self.vix_data is not None and len(self.vix_data) > 0:
                    print(f"    VIX: {len(self.vix_data)} days (using {ticker})")
                    break
            except:
                continue

        if self.vix_data is None:
            print(f"    WARNING: VIX data unavailable")

        print()

    def get_spy_value(self, date, column):
        """Get SPY value at date"""
        if self.spy_data is None:
            return None
        before = self.spy_data[self.spy_data.index <= date]
        return before.iloc[-1][column] if len(before) > 0 else None

    def get_vix_value(self, date):
        """Get VIX value at date"""
        if self.vix_data is None:
            return None
        before = self.vix_data[self.vix_data.index <= date]
        return before.iloc[-1]['close'] if len(before) > 0 else None

    # ========================================================================
    # CONFIRMATION FILTER 1: Market Trend
    # ========================================================================

    def test_market_trend_confirmation(self):
        """
        Market Trend Confirmation Filter

        ONLY take trades when divergence AGREES with market trend:
        - Bullish divergence → Require bull market (SPY > 200 MA, 50 > 200)
        - Bearish divergence → Require bear market (SPY < 200 MA, 50 < 200)
        """
        print("="*70)
        print("CONFIRMATION FILTER 1: Market Trend (SPY MA)")
        print("="*70)
        print()
        print("Logic (FLIPPED):")
        print("  Bullish divergence → ONLY take if SPY > 200 MA AND 50 > 200 (bull market)")
        print("  Bearish divergence → ONLY take if SPY < 200 MA AND 50 < 200 (bear market)")
        print()

        filtered_df = self.baseline_df.copy()
        filtered_df['passed_filter'] = False

        for idx, row in filtered_df.iterrows():
            signal_date = row['signal_date']
            is_bullish = row['divergence_type'] == 'Bullish'
            is_bearish = row['divergence_type'] == 'Bearish'

            spy_close = self.get_spy_value(signal_date, 'close')
            spy_ma50 = self.get_spy_value(signal_date, 'ma_50')
            spy_ma200 = self.get_spy_value(signal_date, 'ma_200')

            if not all([spy_close, spy_ma50, spy_ma200]):
                continue

            # Check market structure
            bull_market = (spy_close > spy_ma200) and (spy_ma50 > spy_ma200)
            bear_market = (spy_close < spy_ma200) and (spy_ma50 < spy_ma200)

            # ONLY take if divergence AGREES with market
            if (is_bullish and bull_market) or (is_bearish and bear_market):
                filtered_df.at[idx, 'passed_filter'] = True

        self._generate_confirmation_report(
            filtered_df,
            filter_name="Market_Trend_Confirmation",
            filter_description="Only trade WITH the market trend (SPY 50/200 MA)"
        )

    # ========================================================================
    # CONFIRMATION FILTER 2: Volatility
    # ========================================================================

    def test_volatility_confirmation(self):
        """
        Volatility Confirmation Filter

        ONLY take trades when VIX > 15 (higher volatility = divergences work better)
        """
        print("="*70)
        print("CONFIRMATION FILTER 2: Volatility (VIX)")
        print("="*70)
        print()
        print("Logic (FLIPPED):")
        print("  ONLY take trades when VIX > 15 (higher volatility)")
        print("  Skip when VIX < 15 (low volatility = strong trends, divergences less reliable)")
        print()

        filtered_df = self.baseline_df.copy()
        filtered_df['passed_filter'] = False

        for idx, row in filtered_df.iterrows():
            signal_date = row['signal_date']
            vix = self.get_vix_value(signal_date)

            if vix is None:
                continue

            # ONLY take if VIX > 15
            if vix > 15:
                filtered_df.at[idx, 'passed_filter'] = True

        self._generate_confirmation_report(
            filtered_df,
            filter_name="Volatility_Confirmation",
            filter_description="Only trade when VIX > 15 (higher volatility)"
        )

    # ========================================================================
    # CONFIRMATION FILTER 3: Market Breadth
    # ========================================================================

    def test_market_breadth_confirmation(self):
        """
        Market Breadth Confirmation Filter

        ONLY take trades in STRONG directional markets:
        - Bullish divergence → SPY must be >10% above 200 MA
        - Bearish divergence → SPY must be >10% below 200 MA
        """
        print("="*70)
        print("CONFIRMATION FILTER 3: Market Breadth (SPY Distance from MA)")
        print("="*70)
        print()
        print("Logic (FLIPPED):")
        print("  Bullish divergence → ONLY take if SPY >10% above 200 MA (strong bull)")
        print("  Bearish divergence → ONLY take if SPY >10% below 200 MA (strong bear)")
        print()

        filtered_df = self.baseline_df.copy()
        filtered_df['passed_filter'] = False

        for idx, row in filtered_df.iterrows():
            signal_date = row['signal_date']
            is_bullish = row['divergence_type'] == 'Bullish'
            is_bearish = row['divergence_type'] == 'Bearish'

            spy_close = self.get_spy_value(signal_date, 'close')
            spy_ma200 = self.get_spy_value(signal_date, 'ma_200')

            if not all([spy_close, spy_ma200]):
                continue

            pct_from_ma = ((spy_close - spy_ma200) / spy_ma200) * 100

            # ONLY take if divergence AGREES with strong market movement
            if (is_bullish and pct_from_ma > 10) or (is_bearish and pct_from_ma < -10):
                filtered_df.at[idx, 'passed_filter'] = True

        self._generate_confirmation_report(
            filtered_df,
            filter_name="Market_Breadth_Confirmation",
            filter_description="Only trade in strong directional markets (±10% from MA)"
        )

    # ========================================================================
    # CONFIRMATION FILTER 4: Trend Strength (ADX)
    # ========================================================================

    def test_trend_strength_confirmation(self):
        """
        Trend Strength Confirmation Filter

        ONLY take trades when ADX > 25 AND trend agrees with divergence:
        - Bullish divergence → ADX > 25 AND SPY > 50 MA (strong uptrend)
        - Bearish divergence → ADX > 25 AND SPY < 50 MA (strong downtrend)
        """
        print("="*70)
        print("CONFIRMATION FILTER 4: Trend Strength (ADX)")
        print("="*70)
        print()
        print("Logic (FLIPPED):")
        print("  Bullish divergence → ONLY take if ADX > 25 AND SPY > 50 MA (strong uptrend)")
        print("  Bearish divergence → ONLY take if ADX > 25 AND SPY < 50 MA (strong downtrend)")
        print()

        filtered_df = self.baseline_df.copy()
        filtered_df['passed_filter'] = False

        for idx, row in filtered_df.iterrows():
            signal_date = row['signal_date']
            is_bullish = row['divergence_type'] == 'Bullish'
            is_bearish = row['divergence_type'] == 'Bearish'

            adx = self.get_spy_value(signal_date, 'adx')
            spy_close = self.get_spy_value(signal_date, 'close')
            spy_ma50 = self.get_spy_value(signal_date, 'ma_50')

            if adx is None or pd.isna(adx) or not all([spy_close, spy_ma50]):
                continue

            # Check trend direction
            spy_uptrend = spy_close > spy_ma50
            spy_downtrend = spy_close < spy_ma50

            # ONLY take if strong trend AND agrees with divergence
            if adx > 25:
                if (is_bullish and spy_uptrend) or (is_bearish and spy_downtrend):
                    filtered_df.at[idx, 'passed_filter'] = True

        self._generate_confirmation_report(
            filtered_df,
            filter_name="Trend_Strength_Confirmation",
            filter_description="Only trade WITH strong trends (ADX > 25 + direction match)"
        )

    # ========================================================================
    # CONFIRMATION FILTER 5: Beta/Correlation
    # ========================================================================

    def test_beta_confirmation(self):
        """
        Beta/Correlation Confirmation Filter

        Same as Trend Strength but more selective - requires BOTH:
        - Strong trend (ADX > 25)
        - Clear direction match with divergence
        """
        print("="*70)
        print("CONFIRMATION FILTER 5: Beta/Correlation (Same as Trend Strength)")
        print("="*70)
        print()
        print("Note: This is essentially the same as Filter 4 - testing same logic")
        print()

        # This is the same as Filter 4 for confirmation purposes
        self.test_trend_strength_confirmation()

    # ========================================================================
    # Report Generation
    # ========================================================================

    def _generate_confirmation_report(self, filtered_df, filter_name, filter_description):
        """Generate report for confirmation filter"""

        # Baseline
        baseline_trades = len(filtered_df)
        baseline_pnl = filtered_df['total_pnl'].sum()
        baseline_winners = len(filtered_df[filtered_df['total_pnl'] > 0])
        baseline_wr = (baseline_winners / baseline_trades) * 100

        # With confirmation filter
        passed_df = filtered_df[filtered_df['passed_filter']]
        filtered_trades = len(passed_df)
        filtered_pnl = passed_df['total_pnl'].sum()
        filtered_winners = len(passed_df[passed_df['total_pnl'] > 0])
        filtered_wr = (filtered_winners / filtered_trades) * 100 if filtered_trades > 0 else 0

        # Rejected
        rejected_df = filtered_df[~filtered_df['passed_filter']]
        rejected_trades = len(rejected_df)
        rejected_pnl = rejected_df['total_pnl'].sum()
        rejected_winners = len(rejected_df[rejected_df['total_pnl'] > 0])

        # Print
        print("RESULTS")
        print("-"*70)
        print()

        print("BASELINE (All Trades):")
        print(f"  Total Trades: {baseline_trades}")
        print(f"  Winners: {baseline_winners} | Win Rate: {baseline_wr:.1f}%")
        print(f"  Total P&L: ${baseline_pnl:,.2f}")
        print()

        print(f"WITH CONFIRMATION FILTER (Only trades that passed):")
        print(f"  Trades Taken: {filtered_trades} ({filtered_trades/baseline_trades*100:.1f}%)")
        print(f"  Trades Rejected: {rejected_trades} ({rejected_trades/baseline_trades*100:.1f}%)")
        print(f"  Winners: {filtered_winners} | Win Rate: {filtered_wr:.1f}%")
        print(f"  Total P&L: ${filtered_pnl:,.2f}")
        print()

        print("IMPACT:")
        pnl_change = filtered_pnl - baseline_pnl
        pnl_change_pct = (pnl_change / baseline_pnl * 100) if baseline_pnl != 0 else 0
        print(f"  P&L Change: ${pnl_change:,.2f} ({pnl_change_pct:+.1f}%)")
        print(f"  Win Rate Change: {filtered_wr - baseline_wr:+.1f}%")
        print(f"  Rejected Trades P&L: ${rejected_pnl:,.2f}")
        print()

        if rejected_trades > 0:
            print("REJECTED TRADES ANALYSIS:")
            rejected_losers = rejected_trades - rejected_winners
            print(f"  Winners Rejected: {rejected_winners} | Losers Rejected: {rejected_losers}")
            print(f"  Rejected Win Rate: {(rejected_winners/rejected_trades*100):.1f}%")

            # By type
            print()
            print("  By divergence type:")
            for div_type in rejected_df['divergence_type'].unique():
                type_df = rejected_df[rejected_df['divergence_type'] == div_type]
                type_winners = len(type_df[type_df['total_pnl'] > 0])
                type_pnl = type_df['total_pnl'].sum()
                print(f"    {div_type}: {len(type_df)} trades, {type_winners} winners, ${type_pnl:,.2f} P&L")

        print()

        # Export
        output_csv = os.path.join(self.output_dir, f'{filter_name}_results.csv')
        filtered_df.to_csv(output_csv, index=False)
        print(f"Detailed results: {output_csv}")
        print()
        print("="*70)
        print()

    def run_all_tests(self):
        """Run all confirmation filter tests"""
        print("="*70)
        print("CONFIRMATION FILTER TESTING (FLIPPED LOGIC)")
        print("="*70)
        print()
        print("Testing filters as ENTRY CONFIRMATION (not exit filters)")
        print("Only take trades when market structure AGREES with divergence")
        print()

        self.load_baseline()
        self.fetch_market_data()

        print("\n")
        self.test_market_trend_confirmation()
        input("Press Enter to continue...")

        print("\n")
        self.test_volatility_confirmation()
        input("Press Enter to continue...")

        print("\n")
        self.test_market_breadth_confirmation()
        input("Press Enter to continue...")

        print("\n")
        self.test_trend_strength_confirmation()

        print("\n")
        print("="*70)
        print("ALL CONFIRMATION FILTER TESTS COMPLETE")
        print("="*70)
        print(f"Results: {self.output_dir}")


def main():
    """Run confirmation filter tests"""
    tester = ConfirmationFilterTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
