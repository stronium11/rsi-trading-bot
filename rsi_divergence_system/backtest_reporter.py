"""
Backtest Reporting System
Generates comprehensive backtest reports and exports to CSV
"""

import pandas as pd
from datetime import datetime
from backtest_analyzer import BacktestAnalyzer
import os


class BacktestReporter:
    """
    Generates comprehensive backtest reports
    """

    def __init__(self, results_csv='backtest/backtest_results.csv', output_dir='backtest/reports'):
        """
        Initialize backtest reporter

        Parameters:
        - results_csv: Path to backtest results CSV
        - output_dir: Directory for report outputs
        """
        self.results_csv = results_csv
        self.output_dir = output_dir
        self.analyzer = BacktestAnalyzer(results_csv)

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_summary_report(self):
        """
        Generate overall summary report

        Returns:
        - DataFrame with summary metrics
        """
        # Run full analysis
        metrics = self.analyzer.run_full_analysis()

        # Create summary DataFrame
        overall = metrics['overall']
        drawdown = metrics['drawdown']
        sharpe = metrics['sharpe']

        summary_data = {
            'Metric': [
                'Total Trades',
                'Winning Trades',
                'Losing Trades',
                'Win Rate (%)',
                'Avg Profit per Winner ($)',
                'Avg Loss per Loser ($)',
                'Profit Factor',
                'Total Wins ($)',
                'Total Losses ($)',
                'Total P&L ($)',
                'Total Capital Deployed ($)',
                'Total Return (%)',
                'Avg P&L per Trade ($)',
                'Median P&L per Trade ($)',
                'Max Drawdown ($)',
                'Max Drawdown (%)',
                'Longest Drawdown (days)',
                'Sharpe Ratio',
                'Avg Days in Trade',
                'Annualized Return (%)',
                'Annualized Volatility (%)'
            ],
            'Value': [
                overall['total_trades'],
                overall['winning_trades'],
                overall['losing_trades'],
                overall['win_rate'],
                overall['avg_profit_per_winner'],
                overall['avg_loss_per_loser'],
                overall['profit_factor'],
                overall['total_wins'],
                overall['total_losses'],
                overall['total_pnl'],
                overall['total_capital_deployed'],
                overall['total_return_pct'],
                overall['avg_pnl_per_trade'],
                overall['median_pnl_per_trade'],
                drawdown['max_drawdown'],
                drawdown['max_drawdown_pct'],
                drawdown['longest_drawdown_days'],
                sharpe['sharpe_ratio'],
                sharpe['avg_days_in_trade'],
                sharpe['annualized_return'],
                sharpe['annualized_volatility']
            ]
        }

        df_summary = pd.DataFrame(summary_data)
        return df_summary

    def generate_timeframe_report(self):
        """
        Generate timeframe breakdown report

        Returns:
        - DataFrame with metrics by timeframe
        """
        if not self.analyzer.metrics:
            self.analyzer.run_full_analysis()

        return self.analyzer.metrics['by_timeframe']

    def generate_type_report(self):
        """
        Generate divergence type breakdown report

        Returns:
        - DataFrame with metrics by type
        """
        if not self.analyzer.metrics:
            self.analyzer.run_full_analysis()

        return self.analyzer.metrics['by_type']

    def generate_timeframe_type_report(self):
        """
        Generate combined timeframe + type breakdown report

        Returns:
        - DataFrame with metrics by timeframe and type
        """
        if not self.analyzer.metrics:
            self.analyzer.run_full_analysis()

        return self.analyzer.metrics['by_timeframe_and_type']

    def generate_quarterly_report(self):
        """
        Generate quarterly performance report

        Returns:
        - DataFrame with quarterly metrics
        """
        if not self.analyzer.metrics:
            self.analyzer.run_full_analysis()

        return self.analyzer.metrics['by_quarter']

    def generate_trade_details_report(self):
        """
        Generate detailed trade report with exit information

        Returns:
        - DataFrame with detailed trade information
        """
        # Load results
        df = pd.read_csv(self.results_csv)

        # Select relevant columns
        columns = [
            'ticker',
            'timeframe',
            'divergence_type',
            'signal_date',
            'entry_date',
            'entry_price',
            'initial_shares',
            'initial_capital',
            'total_pnl',
            'total_pnl_pct',
            'num_exits',
            'days_in_trade'
        ]

        df_report = df[columns].copy()

        # Sort by entry date
        df_report['entry_date'] = pd.to_datetime(df_report['entry_date'])
        df_report = df_report.sort_values('entry_date')

        # Add performance category
        df_report['result'] = df_report['total_pnl'].apply(
            lambda x: 'Win' if x > 0 else ('Loss' if x < 0 else 'Breakeven')
        )

        return df_report

    def generate_equity_curve(self):
        """
        Generate equity curve data

        Returns:
        - DataFrame with cumulative P&L over time
        """
        df = pd.read_csv(self.results_csv)

        # Sort by entry date
        df['entry_date'] = pd.to_datetime(df['entry_date'])
        df = df.sort_values('entry_date')

        # Calculate cumulative P&L
        df['cumulative_pnl'] = df['total_pnl'].cumsum()

        # Calculate cumulative capital
        df['cumulative_capital'] = df['initial_capital'].cumsum()

        # Calculate cumulative return %
        df['cumulative_return_pct'] = (df['cumulative_pnl'] / df['cumulative_capital']) * 100

        equity_curve = df[['entry_date', 'ticker', 'total_pnl', 'cumulative_pnl', 'cumulative_return_pct']].copy()

        return equity_curve

    def generate_all_reports(self):
        """
        Generate all reports and save to CSV files

        Returns:
        - Dictionary with all report DataFrames
        """
        print(f"\n{'='*70}")
        print(f"GENERATING BACKTEST REPORTS")
        print(f"{'='*70}\n")

        reports = {}

        # 1. Summary Report
        print("Generating summary report...")
        summary = self.generate_summary_report()
        summary_path = os.path.join(self.output_dir, 'summary_report.csv')
        summary.to_csv(summary_path, index=False)
        reports['summary'] = summary
        print(f"  Saved: {summary_path}")

        # 2. Timeframe Report
        print("Generating timeframe report...")
        timeframe = self.generate_timeframe_report()
        timeframe_path = os.path.join(self.output_dir, 'timeframe_report.csv')
        timeframe.to_csv(timeframe_path, index=False)
        reports['timeframe'] = timeframe
        print(f"  Saved: {timeframe_path}")

        # 3. Type Report
        print("Generating divergence type report...")
        type_report = self.generate_type_report()
        type_path = os.path.join(self.output_dir, 'type_report.csv')
        type_report.to_csv(type_path, index=False)
        reports['type'] = type_report
        print(f"  Saved: {type_path}")

        # 4. Timeframe + Type Combined Report
        print("Generating timeframe + type breakdown...")
        timeframe_type = self.generate_timeframe_type_report()
        timeframe_type_path = os.path.join(self.output_dir, 'timeframe_type_report.csv')
        timeframe_type.to_csv(timeframe_type_path, index=False)
        reports['timeframe_type'] = timeframe_type
        print(f"  Saved: {timeframe_type_path}")

        # 5. Quarterly Report
        print("Generating quarterly report...")
        quarterly = self.generate_quarterly_report()
        quarterly_path = os.path.join(self.output_dir, 'quarterly_report.csv')
        quarterly.to_csv(quarterly_path, index=False)
        reports['quarterly'] = quarterly
        print(f"  Saved: {quarterly_path}")

        # 6. Trade Details Report
        print("Generating trade details report...")
        trade_details = self.generate_trade_details_report()
        details_path = os.path.join(self.output_dir, 'trade_details_report.csv')
        trade_details.to_csv(details_path, index=False)
        reports['trade_details'] = trade_details
        print(f"  Saved: {details_path}")

        # 7. Equity Curve
        print("Generating equity curve...")
        equity_curve = self.generate_equity_curve()
        equity_path = os.path.join(self.output_dir, 'equity_curve.csv')
        equity_curve.to_csv(equity_path, index=False)
        reports['equity_curve'] = equity_curve
        print(f"  Saved: {equity_path}")

        print(f"\n{'='*70}")
        print(f"ALL REPORTS GENERATED")
        print(f"{'='*70}")
        print(f"Reports saved to: {self.output_dir}")
        print(f"{'='*70}\n")

        return reports

    def print_full_report(self):
        """
        Print a comprehensive text report to console
        """
        # Generate all reports
        reports = self.generate_all_reports()

        print(f"\n{'='*70}")
        print(f"COMPREHENSIVE BACKTEST REPORT")
        print(f"{'='*70}\n")

        # 1. Summary
        print("=" * 70)
        print("OVERALL PERFORMANCE SUMMARY")
        print("=" * 70)
        print(reports['summary'].to_string(index=False))

        # 2. Timeframe Breakdown
        print(f"\n{'='*70}")
        print("PERFORMANCE BY TIMEFRAME")
        print("=" * 70)
        print(reports['timeframe'].to_string(index=False))

        # 3. Type Breakdown
        print(f"\n{'='*70}")
        print("PERFORMANCE BY DIVERGENCE TYPE")
        print("=" * 70)
        print(reports['type'].to_string(index=False))

        # 4. Combined Timeframe + Type Breakdown
        print(f"\n{'='*70}")
        print("PERFORMANCE BY TIMEFRAME + DIVERGENCE TYPE")
        print("=" * 70)
        print(reports['timeframe_type'].to_string(index=False))

        # 5. Quarterly Performance
        print(f"\n{'='*70}")
        print("QUARTERLY PERFORMANCE")
        print("=" * 70)
        print(reports['quarterly'].to_string(index=False))

        # 6. Best and Worst Trades
        print(f"\n{'='*70}")
        print("BEST AND WORST TRADES")
        print("=" * 70)
        trade_details = reports['trade_details'].sort_values('total_pnl', ascending=False)

        print("\nTOP 10 WINNERS:")
        top_winners = trade_details.head(10)[['ticker', 'timeframe', 'divergence_type', 'entry_date', 'total_pnl', 'total_pnl_pct', 'days_in_trade']]
        print(top_winners.to_string(index=False))

        print("\nTOP 10 LOSERS:")
        top_losers = trade_details.tail(10)[['ticker', 'timeframe', 'divergence_type', 'entry_date', 'total_pnl', 'total_pnl_pct', 'days_in_trade']]
        print(top_losers.to_string(index=False))

        # 7. Equity Curve Summary
        print(f"\n{'='*70}")
        print("EQUITY CURVE SUMMARY")
        print("=" * 70)
        equity = reports['equity_curve']
        print(f"Starting Capital (first trade):   ${equity.iloc[0]['cumulative_pnl']:.2f}")
        print(f"Ending Cumulative P&L:            ${equity.iloc[-1]['cumulative_pnl']:.2f}")
        print(f"Final Cumulative Return:          {equity.iloc[-1]['cumulative_return_pct']:.2f}%")
        print(f"Number of Trades:                 {len(equity)}")
        print(f"Date Range:                       {equity.iloc[0]['entry_date'].strftime('%Y-%m-%d')} to {equity.iloc[-1]['entry_date'].strftime('%Y-%m-%d')}")

        print(f"\n{'='*70}")
        print("REPORT COMPLETE")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    reporter = BacktestReporter()
    reporter.print_full_report()
