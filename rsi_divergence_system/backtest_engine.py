"""
Backtest Trade Simulator Engine
Simulates actual trades with multi-leg position management
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np
import gc
import time
import os


class Trade:
    """
    Represents a single trade with multi-leg exits
    """

    def __init__(self, signal):
        """
        Initialize trade from signal

        Parameters:
        - signal: Dictionary with signal information
        """
        self.ticker = signal['ticker']
        self.timeframe = signal['timeframe']
        self.signal_date = pd.to_datetime(signal['signal_date'])
        self.entry_date = pd.to_datetime(signal['entry_date'])
        self.entry_price = float(signal['entry_price'])
        self.divergence_type = signal['divergence_type']
        self.direction = 'LONG' if self.divergence_type == 'Bullish' else 'SHORT'

        # Position sizing: $1000 or 1 share, whichever is smaller
        if self.entry_price >= 1000:
            self.initial_shares = 1.0
        else:
            self.initial_shares = 1000 / self.entry_price

        self.initial_capital = self.initial_shares * self.entry_price
        self.remaining_shares = self.initial_shares

        # Track stop loss level
        self.stop_price = None
        self.set_initial_stop()

        # Track exits
        self.exits = []
        self.is_closed = False
        self.days_in_trade = 0

        # Track profit milestones hit
        self.milestone_5_hit = False
        self.milestone_10_hit = False
        self.milestone_20_hit = False

    def set_initial_stop(self):
        """Set initial 5% stop loss"""
        if self.direction == 'LONG':
            self.stop_price = self.entry_price * 0.95  # 5% below entry
        else:  # SHORT
            self.stop_price = self.entry_price * 1.05  # 5% above entry

    def calculate_profit_pct(self, current_price):
        """Calculate current profit percentage"""
        if self.direction == 'LONG':
            return ((current_price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT
            return ((self.entry_price - current_price) / self.entry_price) * 100

    def is_stopped_out(self, current_price):
        """Check if stop loss is hit"""
        if self.direction == 'LONG':
            return current_price <= self.stop_price
        else:  # SHORT
            return current_price >= self.stop_price

    def execute_exit(self, exit_date, exit_price, shares_to_close, reason):
        """
        Execute a position exit

        Parameters:
        - exit_date: Date of exit
        - exit_price: Price at exit
        - shares_to_close: Number of shares to close
        - reason: Exit reason string
        """
        if shares_to_close <= 0 or self.remaining_shares <= 0:
            return

        # Ensure we don't close more than we have
        shares_to_close = min(shares_to_close, self.remaining_shares)

        # Calculate P&L for this leg
        if self.direction == 'LONG':
            pnl = (exit_price - self.entry_price) * shares_to_close
        else:  # SHORT
            pnl = (self.entry_price - exit_price) * shares_to_close

        pnl_pct = self.calculate_profit_pct(exit_price)

        exit_record = {
            'exit_date': exit_date,
            'exit_price': round(exit_price, 2),
            'shares_closed': round(shares_to_close, 4),
            'exit_reason': reason,
            'pnl': round(pnl, 2),
            'pnl_pct': round(pnl_pct, 2)
        }

        self.exits.append(exit_record)
        self.remaining_shares -= shares_to_close

        if self.remaining_shares < 0.0001:  # Essentially zero
            self.remaining_shares = 0
            self.is_closed = True

    def update_stop_to_breakeven(self):
        """Move stop to breakeven (entry price)"""
        self.stop_price = self.entry_price

    def update_stop_to_3pct_profit(self):
        """Move stop to +3% profit"""
        if self.direction == 'LONG':
            self.stop_price = self.entry_price * 1.03
        else:  # SHORT
            self.stop_price = self.entry_price * 0.97

    def update_stop_to_10pct_profit(self):
        """Move stop to +10% profit"""
        if self.direction == 'LONG':
            self.stop_price = self.entry_price * 1.10
        else:  # SHORT
            self.stop_price = self.entry_price * 0.90

    def process_day(self, date, high, low, close):
        """
        Process one trading day

        Parameters:
        - date: Trading date
        - high: Day's high price
        - low: Day's low price
        - close: Day's close price

        Returns:
        - True if trade is still open, False if closed
        """
        if self.is_closed:
            return False

        self.days_in_trade += 1

        # Check if stopped out (use intraday high/low for accuracy)
        if self.direction == 'LONG':
            if low <= self.stop_price:
                # Stopped out at stop price
                self.execute_exit(date, self.stop_price, self.remaining_shares, 'Stop Loss')
                return False
        else:  # SHORT
            if high >= self.stop_price:
                # Stopped out at stop price
                self.execute_exit(date, self.stop_price, self.remaining_shares, 'Stop Loss')
                return False

        # Calculate profit percentage
        profit_pct = self.calculate_profit_pct(close)

        # Check profit milestones and execute exits
        # +5%: Move stop to breakeven
        if not self.milestone_5_hit and profit_pct >= 5:
            self.milestone_5_hit = True
            self.update_stop_to_breakeven()

        # +10%: Close 50%, move stop to +3%
        if not self.milestone_10_hit and profit_pct >= 10:
            self.milestone_10_hit = True
            shares_to_close = self.initial_shares * 0.50
            self.execute_exit(date, close, shares_to_close, 'Take Profit +10% (50%)')
            if not self.is_closed:
                self.update_stop_to_3pct_profit()

        # +20%: Close 25%, move stop to +10%
        if not self.milestone_20_hit and profit_pct >= 20:
            self.milestone_20_hit = True
            shares_to_close = self.initial_shares * 0.25
            self.execute_exit(date, close, shares_to_close, 'Take Profit +20% (25%)')
            if not self.is_closed:
                self.update_stop_to_10pct_profit()

        # +50%: Close remaining
        if profit_pct >= 50:
            self.execute_exit(date, close, self.remaining_shares, 'Take Profit +50% (Remaining)')
            return False

        # Max holding period: 120 days
        if self.days_in_trade >= 120:
            self.execute_exit(date, close, self.remaining_shares, 'Max Hold Period (120 days)')
            return False

        return True  # Trade still open

    def get_summary(self):
        """Get trade summary"""
        total_pnl = sum([exit_record['pnl'] for exit_record in self.exits])
        total_pnl_pct = (total_pnl / self.initial_capital) * 100

        return {
            'ticker': self.ticker,
            'timeframe': self.timeframe,
            'signal_date': self.signal_date,
            'entry_date': self.entry_date,
            'entry_price': round(self.entry_price, 2),
            'divergence_type': self.divergence_type,
            'direction': self.direction,
            'initial_shares': round(self.initial_shares, 4),
            'initial_capital': round(self.initial_capital, 2),
            'total_pnl': round(total_pnl, 2),
            'total_pnl_pct': round(total_pnl_pct, 2),
            'num_exits': len(self.exits),
            'days_in_trade': self.days_in_trade,
            'exits': self.exits
        }


class BacktestEngine:
    """
    Backtesting engine that simulates trades
    """

    def __init__(self, signals_csv='backtest/backtest_signals.csv'):
        """
        Initialize backtest engine

        Parameters:
        - signals_csv: Path to signals CSV file
        """
        self.signals_csv = signals_csv
        self.signals_df = None
        self.trades = []

    def load_signals(self):
        """Load signals from CSV"""
        print("Loading signals...")
        self.signals_df = pd.read_csv(self.signals_csv)
        print(f"Loaded {len(self.signals_df)} signals")
        return self.signals_df

    def fetch_price_data(self, ticker, start_date, end_date):
        """
        Fetch daily price data for backtesting

        Parameters:
        - ticker: Stock ticker
        - start_date: Start date
        - end_date: End date

        Returns:
        - DataFrame with price data
        """
        try:
            df = yf.download(ticker, start=start_date, end=end_date, interval='1d', progress=False, auto_adjust=True)

            if df.empty:
                return None

            # Handle MultiIndex columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df.columns = [col.lower() for col in df.columns]
            return df

        except Exception as e:
            return None

    def simulate_trade(self, signal):
        """
        Simulate a single trade

        Parameters:
        - signal: Signal dictionary

        Returns:
        - Trade object
        """
        trade = Trade(signal)

        # Fetch price data from entry date forward (max 120 days + buffer)
        start_date = trade.entry_date
        end_date = start_date + timedelta(days=150)

        price_df = self.fetch_price_data(trade.ticker, start_date, end_date)

        if price_df is None or len(price_df) == 0:
            # No price data available, close trade immediately
            trade.execute_exit(trade.entry_date, trade.entry_price, trade.remaining_shares, 'No Data')
            return trade

        # Process each trading day
        for date, row in price_df.iterrows():
            if date < trade.entry_date:
                continue  # Skip dates before entry

            still_open = trade.process_day(
                date=date,
                high=row['high'],
                low=row['low'],
                close=row['close']
            )

            if not still_open:
                break  # Trade closed

        # If trade still open after data ends, force close
        if not trade.is_closed and len(price_df) > 0:
            last_date = price_df.index[-1]
            last_close = price_df.iloc[-1]['close']
            trade.execute_exit(last_date, last_close, trade.remaining_shares, 'Data End')

        return trade

    def run_backtest(self):
        """
        Run backtest on all signals

        Returns:
        - List of Trade objects
        """
        if self.signals_df is None:
            self.load_signals()

        print(f"\n{'='*70}")
        print(f"RUNNING BACKTEST SIMULATION")
        print(f"{'='*70}")
        print(f"Total signals to test: {len(self.signals_df)}")
        print(f"{'='*70}\n")

        start_time = datetime.now()

        for idx, row in self.signals_df.iterrows():
            signal = row.to_dict()
            trade = self.simulate_trade(signal)
            self.trades.append(trade)

            # Progress update and resource cleanup every 10 trades
            if (idx + 1) % 10 == 0:
                print(f"Processed {idx + 1}/{len(self.signals_df)} trades...")
                # Force garbage collection to close file handles
                gc.collect()
                time.sleep(0.1)  # Small delay to allow connections to close

            # More aggressive cleanup every 50 trades on Mac (file handle limit)
            if (idx + 1) % 50 == 0:
                gc.collect()
                time.sleep(0.5)

        print(f"\n{'='*70}")
        print(f"BACKTEST COMPLETE")
        print(f"{'='*70}")
        print(f"Total trades simulated: {len(self.trades)}")
        print(f"Duration: {datetime.now() - start_time}")
        print(f"{'='*70}\n")

        # Final cleanup
        gc.collect()

        return self.trades

    def save_results(self, output_csv='backtest/backtest_results.csv'):
        """
        Save backtest results to CSV

        Parameters:
        - output_csv: Output CSV path
        """
        results = []

        for trade in self.trades:
            summary = trade.get_summary()
            results.append(summary)

        df_results = pd.DataFrame(results)

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_csv), exist_ok=True)

        # Force garbage collection before writing
        gc.collect()
        time.sleep(0.5)

        # Write results
        try:
            df_results.to_csv(output_csv, index=False)
            print(f"Results saved to: {output_csv}")
        except Exception as e:
            print(f"Error saving results: {e}")
            # Try alternative approach
            print("Attempting alternative save method...")
            with open(output_csv, 'w') as f:
                df_results.to_csv(f, index=False)
            print(f"Results saved to: {output_csv}")

        return df_results


if __name__ == "__main__":
    engine = BacktestEngine()
    engine.load_signals()
    trades = engine.run_backtest()
    results_df = engine.save_results()

    # Quick summary
    winning_trades = [t for t in trades if sum([e['pnl'] for e in t.exits]) > 0]
    losing_trades = [t for t in trades if sum([e['pnl'] for e in t.exits]) <= 0]

    print(f"\nQuick Summary:")
    print(f"Winning trades: {len(winning_trades)}")
    print(f"Losing trades: {len(losing_trades)}")
    print(f"Win rate: {len(winning_trades) / len(trades) * 100:.2f}%")
