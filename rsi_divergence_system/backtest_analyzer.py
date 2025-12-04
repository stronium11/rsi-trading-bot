"""
Backtest Performance Analyzer
Analyzes backtest results and calculates performance metrics
"""

import pandas as pd
import numpy as np
from datetime import datetime


class BacktestAnalyzer:
    """
    Analyzes backtest results and generates performance metrics
    """

    def __init__(self, results_csv='backtest/backtest_results.csv'):
        """
        Initialize backtest analyzer

        Parameters:
        - results_csv: Path to backtest results CSV
        """
        self.results_csv = results_csv
        self.df = None
        self.metrics = {}

    def load_results(self):
        """Load backtest results from CSV"""
        print("Loading backtest results...")
        self.df = pd.read_csv(self.results_csv)

        # Convert date columns to datetime
        self.df['signal_date'] = pd.to_datetime(self.df['signal_date'])
        self.df['entry_date'] = pd.to_datetime(self.df['entry_date'])

        print(f"Loaded {len(self.df)} trades")
        return self.df

    def calculate_overall_metrics(self):
        """
        Calculate overall performance metrics

        Returns:
        - Dictionary with overall metrics
        """
        if self.df is None:
            self.load_results()

        total_trades = len(self.df)

        if total_trades == 0:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_profit_per_winner': 0,
                'avg_loss_per_loser': 0,
                'profit_factor': 0,
                'total_return_pct': 0,
                'total_pnl': 0,
                'total_capital_deployed': 0
            }

        # Separate winning and losing trades
        winning_trades = self.df[self.df['total_pnl'] > 0]
        losing_trades = self.df[self.df['total_pnl'] <= 0]

        num_winners = len(winning_trades)
        num_losers = len(losing_trades)

        # Win rate
        win_rate = (num_winners / total_trades) * 100

        # Average profit/loss
        avg_profit_per_winner = winning_trades['total_pnl'].mean() if num_winners > 0 else 0
        avg_loss_per_loser = losing_trades['total_pnl'].mean() if num_losers > 0 else 0

        # Profit factor
        total_wins = winning_trades['total_pnl'].sum() if num_winners > 0 else 0
        total_losses = abs(losing_trades['total_pnl'].sum()) if num_losers > 0 else 0

        if total_losses > 0:
            profit_factor = total_wins / total_losses
        else:
            profit_factor = float('inf') if total_wins > 0 else 0

        # Total return
        total_pnl = self.df['total_pnl'].sum()
        total_capital_deployed = self.df['initial_capital'].sum()
        total_return_pct = (total_pnl / total_capital_deployed) * 100 if total_capital_deployed > 0 else 0

        metrics = {
            'total_trades': total_trades,
            'winning_trades': num_winners,
            'losing_trades': num_losers,
            'win_rate': round(win_rate, 2),
            'avg_profit_per_winner': round(avg_profit_per_winner, 2),
            'avg_loss_per_loser': round(avg_loss_per_loser, 2),
            'profit_factor': round(profit_factor, 2),
            'total_wins': round(total_wins, 2),
            'total_losses': round(total_losses, 2),
            'total_pnl': round(total_pnl, 2),
            'total_capital_deployed': round(total_capital_deployed, 2),
            'total_return_pct': round(total_return_pct, 2),
            'avg_pnl_per_trade': round(self.df['total_pnl'].mean(), 2),
            'median_pnl_per_trade': round(self.df['total_pnl'].median(), 2)
        }

        self.metrics['overall'] = metrics
        return metrics

    def calculate_max_drawdown(self):
        """
        Calculate maximum drawdown

        Returns:
        - Dictionary with drawdown metrics
        """
        if self.df is None:
            self.load_results()

        # Sort by entry date to get chronological order
        df_sorted = self.df.sort_values('entry_date').copy()

        # Calculate cumulative P&L
        df_sorted['cumulative_pnl'] = df_sorted['total_pnl'].cumsum()

        # Calculate running maximum
        df_sorted['running_max'] = df_sorted['cumulative_pnl'].cummax()

        # Calculate drawdown
        df_sorted['drawdown'] = df_sorted['cumulative_pnl'] - df_sorted['running_max']

        # Find maximum drawdown
        max_drawdown = df_sorted['drawdown'].min()
        max_drawdown_pct = (max_drawdown / df_sorted['running_max'].max() * 100) if df_sorted['running_max'].max() > 0 else 0

        # Find longest drawdown period
        df_sorted['in_drawdown'] = df_sorted['drawdown'] < 0
        drawdown_periods = []
        current_period_start = None

        for idx, row in df_sorted.iterrows():
            if row['in_drawdown'] and current_period_start is None:
                current_period_start = row['entry_date']
            elif not row['in_drawdown'] and current_period_start is not None:
                drawdown_periods.append((current_period_start, row['entry_date']))
                current_period_start = None

        longest_drawdown_days = 0
        if drawdown_periods:
            longest_drawdown_days = max([(end - start).days for start, end in drawdown_periods])

        drawdown_metrics = {
            'max_drawdown': round(max_drawdown, 2),
            'max_drawdown_pct': round(max_drawdown_pct, 2),
            'longest_drawdown_days': longest_drawdown_days
        }

        self.metrics['drawdown'] = drawdown_metrics
        return drawdown_metrics

    def calculate_sharpe_ratio(self, risk_free_rate=0.02):
        """
        Calculate Sharpe ratio (annualized)

        Parameters:
        - risk_free_rate: Annual risk-free rate (default: 2%)

        Returns:
        - Sharpe ratio
        """
        if self.df is None:
            self.load_results()

        # Calculate returns per trade as percentage
        returns = self.df['total_pnl_pct'] / 100  # Convert to decimal

        if len(returns) == 0 or returns.std() == 0:
            # Create default metrics for edge cases
            sharpe_metrics = {
                'sharpe_ratio': 0,
                'avg_days_in_trade': 0,
                'annualized_return': 0,
                'annualized_volatility': 0
            }
            self.metrics['sharpe'] = sharpe_metrics
            return sharpe_metrics

        # Calculate average return per trade
        avg_return = returns.mean()

        # Calculate standard deviation of returns
        std_return = returns.std()

        # Estimate trades per year (rough approximation)
        # Use average holding period from days_in_trade
        avg_days_in_trade = self.df['days_in_trade'].mean()
        if avg_days_in_trade > 0:
            trades_per_year = 252 / avg_days_in_trade  # 252 trading days per year
        else:
            trades_per_year = 1

        # Annualize return and volatility
        annualized_return = avg_return * trades_per_year
        annualized_volatility = std_return * np.sqrt(trades_per_year)

        # Calculate Sharpe ratio
        if annualized_volatility > 0:
            sharpe_ratio = (annualized_return - risk_free_rate) / annualized_volatility
        else:
            sharpe_ratio = 0

        sharpe_metrics = {
            'sharpe_ratio': round(sharpe_ratio, 2),
            'avg_days_in_trade': round(avg_days_in_trade, 1),
            'annualized_return': round(annualized_return * 100, 2),
            'annualized_volatility': round(annualized_volatility * 100, 2)
        }

        self.metrics['sharpe'] = sharpe_metrics
        return sharpe_metrics

    def analyze_by_timeframe(self):
        """
        Analyze performance by timeframe

        Returns:
        - DataFrame with metrics by timeframe
        """
        if self.df is None:
            self.load_results()

        timeframes = self.df['timeframe'].unique()
        results = []

        for tf in timeframes:
            tf_df = self.df[self.df['timeframe'] == tf]

            total_trades = len(tf_df)
            winning_trades = len(tf_df[tf_df['total_pnl'] > 0])
            losing_trades = len(tf_df[tf_df['total_pnl'] <= 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            total_pnl = tf_df['total_pnl'].sum()
            total_capital = tf_df['initial_capital'].sum()
            return_pct = (total_pnl / total_capital * 100) if total_capital > 0 else 0

            results.append({
                'timeframe': tf,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 2),
                'avg_pnl': round(tf_df['total_pnl'].mean(), 2),
                'return_pct': round(return_pct, 2)
            })

        df_results = pd.DataFrame(results)
        self.metrics['by_timeframe'] = df_results
        return df_results

    def analyze_by_type(self):
        """
        Analyze performance by divergence type (Bullish vs Bearish)

        Returns:
        - DataFrame with metrics by type
        """
        if self.df is None:
            self.load_results()

        types = self.df['divergence_type'].unique()
        results = []

        for div_type in types:
            type_df = self.df[self.df['divergence_type'] == div_type]

            total_trades = len(type_df)
            winning_trades = len(type_df[type_df['total_pnl'] > 0])
            losing_trades = len(type_df[type_df['total_pnl'] <= 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            total_pnl = type_df['total_pnl'].sum()
            total_capital = type_df['initial_capital'].sum()
            return_pct = (total_pnl / total_capital * 100) if total_capital > 0 else 0

            results.append({
                'divergence_type': div_type,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 2),
                'avg_pnl': round(type_df['total_pnl'].mean(), 2),
                'return_pct': round(return_pct, 2)
            })

        df_results = pd.DataFrame(results)
        self.metrics['by_type'] = df_results
        return df_results

    def analyze_by_timeframe_and_type(self):
        """
        Analyze performance by timeframe AND divergence type combined

        Returns:
        - DataFrame with metrics by timeframe and type
        """
        if self.df is None:
            self.load_results()

        # Get all unique combinations
        combinations = self.df.groupby(['timeframe', 'divergence_type'])
        results = []

        for (timeframe, div_type), group_df in combinations:
            total_trades = len(group_df)
            winning_trades = len(group_df[group_df['total_pnl'] > 0])
            losing_trades = len(group_df[group_df['total_pnl'] <= 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            total_pnl = group_df['total_pnl'].sum()
            total_capital = group_df['initial_capital'].sum()
            return_pct = (total_pnl / total_capital * 100) if total_capital > 0 else 0

            results.append({
                'timeframe': timeframe,
                'divergence_type': div_type,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 2),
                'avg_pnl': round(group_df['total_pnl'].mean(), 2),
                'return_pct': round(return_pct, 2)
            })

        df_results = pd.DataFrame(results)
        # Sort by timeframe first, then by divergence type
        df_results = df_results.sort_values(['timeframe', 'divergence_type'])
        self.metrics['by_timeframe_and_type'] = df_results
        return df_results

    def analyze_by_quarter(self):
        """
        Analyze performance by quarter

        Returns:
        - DataFrame with quarterly performance
        """
        if self.df is None:
            self.load_results()

        df_sorted = self.df.sort_values('entry_date').copy()

        # Extract quarter and year
        df_sorted['quarter'] = df_sorted['entry_date'].dt.to_period('Q')

        quarters = df_sorted['quarter'].unique()
        results = []

        for quarter in sorted(quarters):
            quarter_df = df_sorted[df_sorted['quarter'] == quarter]

            total_trades = len(quarter_df)
            winning_trades = len(quarter_df[quarter_df['total_pnl'] > 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            total_pnl = quarter_df['total_pnl'].sum()
            total_capital = quarter_df['initial_capital'].sum()
            return_pct = (total_pnl / total_capital * 100) if total_capital > 0 else 0

            results.append({
                'quarter': str(quarter),
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 2),
                'return_pct': round(return_pct, 2)
            })

        df_results = pd.DataFrame(results)
        self.metrics['by_quarter'] = df_results
        return df_results

    def run_full_analysis(self):
        """
        Run complete analysis and return all metrics

        Returns:
        - Dictionary with all analysis results
        """
        print(f"\n{'='*70}")
        print(f"BACKTEST PERFORMANCE ANALYSIS")
        print(f"{'='*70}\n")

        # Load data
        self.load_results()

        # Calculate all metrics
        print("Calculating overall metrics...")
        self.calculate_overall_metrics()

        print("Calculating drawdown metrics...")
        self.calculate_max_drawdown()

        print("Calculating Sharpe ratio...")
        self.calculate_sharpe_ratio()

        print("Analyzing by timeframe...")
        self.analyze_by_timeframe()

        print("Analyzing by divergence type...")
        self.analyze_by_type()

        print("Analyzing by timeframe + type combined...")
        self.analyze_by_timeframe_and_type()

        print("Analyzing by quarter...")
        self.analyze_by_quarter()

        print(f"\n{'='*70}")
        print(f"ANALYSIS COMPLETE")
        print(f"{'='*70}\n")

        return self.metrics

    def print_summary(self):
        """Print a formatted summary of key metrics"""
        if not self.metrics:
            self.run_full_analysis()

        overall = self.metrics['overall']
        drawdown = self.metrics['drawdown']
        sharpe = self.metrics['sharpe']

        print(f"\n{'='*70}")
        print(f"BACKTEST SUMMARY")
        print(f"{'='*70}\n")

        print("OVERALL PERFORMANCE:")
        print(f"  Total Trades:              {overall['total_trades']}")
        print(f"  Winning Trades:            {overall['winning_trades']}")
        print(f"  Losing Trades:             {overall['losing_trades']}")
        print(f"  Win Rate:                  {overall['win_rate']}%")
        print(f"  Avg Profit per Winner:     ${overall['avg_profit_per_winner']}")
        print(f"  Avg Loss per Loser:        ${overall['avg_loss_per_loser']}")
        print(f"  Profit Factor:             {overall['profit_factor']}")
        print(f"  Total P&L:                 ${overall['total_pnl']}")
        print(f"  Total Return:              {overall['total_return_pct']}%")
        print(f"  Avg P&L per Trade:         ${overall['avg_pnl_per_trade']}")
        print(f"  Median P&L per Trade:      ${overall['median_pnl_per_trade']}")

        print(f"\nRISK METRICS:")
        print(f"  Max Drawdown:              ${drawdown['max_drawdown']}")
        print(f"  Max Drawdown %:            {drawdown['max_drawdown_pct']}%")
        print(f"  Longest Drawdown:          {drawdown['longest_drawdown_days']} days")
        print(f"  Sharpe Ratio:              {sharpe['sharpe_ratio']}")
        print(f"  Avg Days in Trade:         {sharpe['avg_days_in_trade']}")
        print(f"  Annualized Return:         {sharpe['annualized_return']}%")
        print(f"  Annualized Volatility:     {sharpe['annualized_volatility']}%")

        print(f"\nBY TIMEFRAME:")
        print(self.metrics['by_timeframe'].to_string(index=False))

        print(f"\nBY DIVERGENCE TYPE:")
        print(self.metrics['by_type'].to_string(index=False))

        print(f"\n{'='*70}\n")


if __name__ == "__main__":
    analyzer = BacktestAnalyzer()
    analyzer.run_full_analysis()
    analyzer.print_summary()
