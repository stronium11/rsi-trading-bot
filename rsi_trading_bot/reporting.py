"""
Reporting Module for RSI Trading Bot
Exports signals, trades, and analytics to CSV files
"""

import csv
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
from database import get_database


class TradingReporter:
    """
    Generates comprehensive reports and exports for the trading bot
    - Signals spreadsheet (matches backtest format)
    - Trades spreadsheet (matches backtest format)
    - Analytics with quarterly and yearly P&L
    """

    def __init__(self, output_dir: str = "reports"):
        """Initialize the reporter"""
        self.db = get_database()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def export_signals_csv(self, filename: str = None) -> str:
        """
        Export all signals to CSV in backtest format

        Returns:
        - Path to the generated CSV file
        """
        if filename is None:
            filename = f"signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        filepath = self.output_dir / filename

        # Get all signals from database
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    s.ticker,
                    s.timeframe,
                    s.detected_at as signal_date,
                    s.divergence_type,
                    s.entry_price as signal_close,
                    s.rsi_value,
                    s.status,
                    s.notes
                FROM signals s
                ORDER BY s.detected_at DESC
            """)
            signals = [dict(row) for row in cursor.fetchall()]

        # Write to CSV
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header matching backtest format
            writer.writerow([
                'ticker',
                'timeframe',
                'signal_date',
                'divergence_type',
                'signal_close',
                'rsi_value',
                'status',
                'notes'
            ])

            # Data rows
            for signal in signals:
                writer.writerow([
                    signal['ticker'],
                    signal['timeframe'],
                    signal['signal_date'],
                    signal['divergence_type'],
                    f"{signal['signal_close']:.2f}",
                    f"{signal['rsi_value']:.2f}" if signal['rsi_value'] else '',
                    signal['status'],
                    signal['notes'] or ''
                ])

        print(f"✅ Signals exported to: {filepath}")
        print(f"   Total signals: {len(signals)}")
        return str(filepath)

    def export_trades_csv(self, filename: str = None) -> str:
        """
        Export all trades to CSV in backtest format
        Aggregates partial exits by position

        Returns:
        - Path to the generated CSV file
        """
        if filename is None:
            filename = f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        filepath = self.output_dir / filename

        # Get all trades with signal and position info
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    t.position_id,
                    t.ticker,
                    t.direction,
                    t.entry_price,
                    t.exit_price,
                    t.quantity,
                    t.opened_at,
                    t.closed_at,
                    t.hold_days,
                    t.exit_reason,
                    t.gross_pnl,
                    t.net_pnl,
                    t.return_pct,
                    s.timeframe,
                    s.detected_at as signal_date,
                    s.divergence_type,
                    p.quantity as initial_quantity,
                    p.entry_price as position_entry_price
                FROM trades t
                LEFT JOIN signals s ON t.signal_id = s.id
                LEFT JOIN positions p ON t.position_id = p.id
                ORDER BY t.position_id, t.closed_at
            """)
            all_trades = [dict(row) for row in cursor.fetchall()]

        # Group trades by position
        positions = defaultdict(list)
        for trade in all_trades:
            positions[trade['position_id']].append(trade)

        # Aggregate trades by position
        aggregated_trades = []
        for position_id, trades in positions.items():
            if not trades:
                continue

            first_trade = trades[0]

            # Calculate totals
            total_pnl = sum(t['net_pnl'] for t in trades)
            total_quantity = sum(t['quantity'] for t in trades)
            initial_capital = first_trade['position_entry_price'] * first_trade['initial_quantity']
            total_pnl_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0

            # Build exits list
            exits = []
            for trade in trades:
                exit_dict = {
                    'exit_date': trade['closed_at'],
                    'exit_price': trade['exit_price'],
                    'shares_closed': trade['quantity'],
                    'exit_reason': trade['exit_reason'],
                    'pnl': trade['net_pnl'],
                    'pnl_pct': trade['return_pct']
                }
                exits.append(str(exit_dict))

            aggregated_trades.append({
                'ticker': first_trade['ticker'],
                'timeframe': first_trade['timeframe'] or '1d',
                'signal_date': first_trade['signal_date'] or '',
                'entry_date': first_trade['opened_at'],
                'entry_price': first_trade['entry_price'],
                'divergence_type': first_trade['divergence_type'] or '',
                'direction': first_trade['direction'],
                'initial_shares': first_trade['initial_quantity'],
                'initial_capital': initial_capital,
                'total_pnl': total_pnl,
                'total_pnl_pct': total_pnl_pct,
                'num_exits': len(trades),
                'days_in_trade': max(t['hold_days'] for t in trades),
                'exits': ' | '.join(exits)
            })

        # Write to CSV
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header matching backtest format
            writer.writerow([
                'ticker',
                'timeframe',
                'signal_date',
                'entry_date',
                'entry_price',
                'divergence_type',
                'direction',
                'initial_shares',
                'initial_capital',
                'total_pnl',
                'total_pnl_pct',
                'num_exits',
                'days_in_trade',
                'exits'
            ])

            # Data rows
            for trade in aggregated_trades:
                writer.writerow([
                    trade['ticker'],
                    trade['timeframe'],
                    trade['signal_date'],
                    trade['entry_date'],
                    f"{trade['entry_price']:.2f}",
                    trade['divergence_type'],
                    trade['direction'],
                    f"{trade['initial_shares']:.4f}",
                    f"{trade['initial_capital']:.2f}",
                    f"{trade['total_pnl']:.2f}",
                    f"{trade['total_pnl_pct']:.2f}",
                    trade['num_exits'],
                    trade['days_in_trade'],
                    trade['exits']
                ])

        print(f"✅ Trades exported to: {filepath}")
        print(f"   Total positions: {len(aggregated_trades)}")
        return str(filepath)

    def generate_analytics(self, filename: str = None) -> str:
        """
        Generate comprehensive analytics report with:
        - Overall performance metrics
        - Quarterly P&L breakdown
        - Yearly P&L breakdown (NEW)
        - Monthly statistics
        - Win/loss analysis

        Returns:
        - Path to the generated CSV file
        """
        if filename is None:
            filename = f"analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        filepath = self.output_dir / filename

        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)

            # ==================== OVERALL PERFORMANCE ====================
            writer.writerow(['OVERALL PERFORMANCE'])
            writer.writerow(['Metric', 'Value'])

            stats = self.db.get_statistics()
            all_trades = self.db.get_all_trades()

            # Calculate additional metrics
            total_trades = len(all_trades)
            winning_trades = sum(1 for t in all_trades if t['net_pnl'] > 0)
            losing_trades = sum(1 for t in all_trades if t['net_pnl'] < 0)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            total_pnl = sum(t['net_pnl'] for t in all_trades)
            total_wins = sum(t['net_pnl'] for t in all_trades if t['net_pnl'] > 0)
            total_losses = sum(t['net_pnl'] for t in all_trades if t['net_pnl'] < 0)

            avg_win = total_wins / winning_trades if winning_trades > 0 else 0
            avg_loss = total_losses / losing_trades if losing_trades > 0 else 0
            profit_factor = abs(total_wins / total_losses) if total_losses != 0 else 0

            largest_win = max((t['net_pnl'] for t in all_trades), default=0)
            largest_loss = min((t['net_pnl'] for t in all_trades), default=0)

            avg_hold_days = sum(t['hold_days'] for t in all_trades) / total_trades if total_trades > 0 else 0

            writer.writerow(['Total Signals', stats['total_signals']])
            writer.writerow(['Total Trades', total_trades])
            writer.writerow(['Open Positions', stats['open_positions']])
            writer.writerow(['Winning Trades', winning_trades])
            writer.writerow(['Losing Trades', losing_trades])
            writer.writerow(['Win Rate %', f"{win_rate:.2f}"])
            writer.writerow(['Total P&L', f"${total_pnl:,.2f}"])
            writer.writerow(['Total Wins', f"${total_wins:,.2f}"])
            writer.writerow(['Total Losses', f"${total_losses:,.2f}"])
            writer.writerow(['Average Win', f"${avg_win:,.2f}"])
            writer.writerow(['Average Loss', f"${avg_loss:,.2f}"])
            writer.writerow(['Profit Factor', f"{profit_factor:.2f}"])
            writer.writerow(['Largest Win', f"${largest_win:,.2f}"])
            writer.writerow(['Largest Loss', f"${largest_loss:,.2f}"])
            writer.writerow(['Average Hold Days', f"{avg_hold_days:.1f}"])
            writer.writerow([])

            # ==================== YEARLY P&L ====================
            writer.writerow(['YEARLY P&L'])
            writer.writerow(['Year', 'Trades', 'Wins', 'Losses', 'Win Rate %', 'Total P&L', 'Avg P&L'])

            # Group by year
            yearly_stats = defaultdict(lambda: {'trades': [], 'pnl': 0})
            for trade in all_trades:
                year = trade['closed_at'][:4]  # Extract year from timestamp
                yearly_stats[year]['trades'].append(trade)
                yearly_stats[year]['pnl'] += trade['net_pnl']

            for year in sorted(yearly_stats.keys()):
                year_data = yearly_stats[year]
                trades = year_data['trades']
                num_trades = len(trades)
                wins = sum(1 for t in trades if t['net_pnl'] > 0)
                losses = sum(1 for t in trades if t['net_pnl'] < 0)
                win_rate = (wins / num_trades * 100) if num_trades > 0 else 0
                total_pnl = year_data['pnl']
                avg_pnl = total_pnl / num_trades if num_trades > 0 else 0

                writer.writerow([
                    year,
                    num_trades,
                    wins,
                    losses,
                    f"{win_rate:.2f}",
                    f"${total_pnl:,.2f}",
                    f"${avg_pnl:,.2f}"
                ])

            writer.writerow([])

            # ==================== QUARTERLY P&L ====================
            writer.writerow(['QUARTERLY P&L'])
            writer.writerow(['Quarter', 'Trades', 'Wins', 'Losses', 'Win Rate %', 'Total P&L', 'Avg P&L'])

            # Group by quarter
            quarterly_stats = defaultdict(lambda: {'trades': [], 'pnl': 0})
            for trade in all_trades:
                date = datetime.strptime(trade['closed_at'], '%Y-%m-%d %H:%M:%S')
                quarter = f"{date.year}-Q{(date.month-1)//3 + 1}"
                quarterly_stats[quarter]['trades'].append(trade)
                quarterly_stats[quarter]['pnl'] += trade['net_pnl']

            for quarter in sorted(quarterly_stats.keys()):
                quarter_data = quarterly_stats[quarter]
                trades = quarter_data['trades']
                num_trades = len(trades)
                wins = sum(1 for t in trades if t['net_pnl'] > 0)
                losses = sum(1 for t in trades if t['net_pnl'] < 0)
                win_rate = (wins / num_trades * 100) if num_trades > 0 else 0
                total_pnl = quarter_data['pnl']
                avg_pnl = total_pnl / num_trades if num_trades > 0 else 0

                writer.writerow([
                    quarter,
                    num_trades,
                    wins,
                    losses,
                    f"{win_rate:.2f}",
                    f"${total_pnl:,.2f}",
                    f"${avg_pnl:,.2f}"
                ])

            writer.writerow([])

            # ==================== MONTHLY P&L ====================
            writer.writerow(['MONTHLY P&L'])
            writer.writerow(['Month', 'Trades', 'Wins', 'Losses', 'Win Rate %', 'Total P&L', 'Avg P&L'])

            # Group by month
            monthly_stats = defaultdict(lambda: {'trades': [], 'pnl': 0})
            for trade in all_trades:
                month = trade['closed_at'][:7]  # YYYY-MM
                monthly_stats[month]['trades'].append(trade)
                monthly_stats[month]['pnl'] += trade['net_pnl']

            for month in sorted(monthly_stats.keys()):
                month_data = monthly_stats[month]
                trades = month_data['trades']
                num_trades = len(trades)
                wins = sum(1 for t in trades if t['net_pnl'] > 0)
                losses = sum(1 for t in trades if t['net_pnl'] < 0)
                win_rate = (wins / num_trades * 100) if num_trades > 0 else 0
                total_pnl = month_data['pnl']
                avg_pnl = total_pnl / num_trades if num_trades > 0 else 0

                writer.writerow([
                    month,
                    num_trades,
                    wins,
                    losses,
                    f"{win_rate:.2f}",
                    f"${total_pnl:,.2f}",
                    f"${avg_pnl:,.2f}"
                ])

            writer.writerow([])

            # ==================== BY TIMEFRAME ====================
            writer.writerow(['PERFORMANCE BY TIMEFRAME'])
            writer.writerow(['Timeframe', 'Trades', 'Win Rate %', 'Total P&L', 'Avg P&L'])

            timeframe_stats = defaultdict(lambda: {'trades': [], 'pnl': 0})
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT t.*, s.timeframe
                    FROM trades t
                    LEFT JOIN signals s ON t.signal_id = s.id
                """)
                trades_with_tf = [dict(row) for row in cursor.fetchall()]

            for trade in trades_with_tf:
                tf = trade['timeframe'] or 'Unknown'
                timeframe_stats[tf]['trades'].append(trade)
                timeframe_stats[tf]['pnl'] += trade['net_pnl']

            for tf in sorted(timeframe_stats.keys()):
                tf_data = timeframe_stats[tf]
                trades = tf_data['trades']
                num_trades = len(trades)
                wins = sum(1 for t in trades if t['net_pnl'] > 0)
                win_rate = (wins / num_trades * 100) if num_trades > 0 else 0
                total_pnl = tf_data['pnl']
                avg_pnl = total_pnl / num_trades if num_trades > 0 else 0

                writer.writerow([
                    tf,
                    num_trades,
                    f"{win_rate:.2f}",
                    f"${total_pnl:,.2f}",
                    f"${avg_pnl:,.2f}"
                ])

            writer.writerow([])

            # ==================== BY EXIT REASON ====================
            writer.writerow(['PERFORMANCE BY EXIT REASON'])
            writer.writerow(['Exit Reason', 'Count', 'Total P&L', 'Avg P&L'])

            exit_stats = defaultdict(lambda: {'count': 0, 'pnl': 0})
            for trade in all_trades:
                reason = trade['exit_reason'] or 'Unknown'
                exit_stats[reason]['count'] += 1
                exit_stats[reason]['pnl'] += trade['net_pnl']

            for reason in sorted(exit_stats.keys()):
                data = exit_stats[reason]
                avg_pnl = data['pnl'] / data['count'] if data['count'] > 0 else 0

                writer.writerow([
                    reason.replace('_', ' ').title(),
                    data['count'],
                    f"${data['pnl']:,.2f}",
                    f"${avg_pnl:,.2f}"
                ])

        print(f"✅ Analytics exported to: {filepath}")
        return str(filepath)

    def generate_all_reports(self) -> Dict[str, str]:
        """
        Generate all reports at once

        Returns:
        - Dictionary with paths to all generated files
        """
        print("\n" + "="*70)
        print("GENERATING TRADING REPORTS")
        print("="*70 + "\n")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        reports = {
            'signals': self.export_signals_csv(f"signals_{timestamp}.csv"),
            'trades': self.export_trades_csv(f"trades_{timestamp}.csv"),
            'analytics': self.generate_analytics(f"analytics_{timestamp}.csv")
        }

        print("\n" + "="*70)
        print("✅ ALL REPORTS GENERATED SUCCESSFULLY")
        print("="*70 + "\n")

        return reports


def main():
    """Main entry point for command-line usage"""
    reporter = TradingReporter()
    reports = reporter.generate_all_reports()

    print("\nGenerated files:")
    for report_type, filepath in reports.items():
        print(f"  • {report_type.title()}: {filepath}")
    print()


if __name__ == "__main__":
    main()
