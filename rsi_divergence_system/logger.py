"""
Signal logging module for RSI divergences
"""
import pandas as pd
import os
from datetime import datetime
import config


class DivergenceLogger:
    """Logs RSI divergence signals to CSV"""

    def __init__(self, output_file: str = config.OUTPUT_FILE):
        self.output_file = output_file
        self.columns = [
            'Date',
            'Ticker',
            'Timeframe',
            'Divergence Type',
            'First Peak Price',
            'Second Peak Price',
            'First Peak RSI',
            'Second Peak RSI'
        ]
        self._initialize_file()

    def _initialize_file(self):
        """Create CSV with headers if it doesn't exist"""
        if not os.path.exists(self.output_file):
            df = pd.DataFrame(columns=self.columns)
            df.to_csv(self.output_file, index=False)
            print(f"Created: {self.output_file}")

    def log_signals(self, ticker: str, timeframe: str, signals: list):
        """Log divergence signals to CSV"""
        if not signals:
            return

        rows = []
        for signal in signals:
            row = {
                'Date': signal['date'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(signal['date'], 'strftime') else str(signal['date']),
                'Ticker': ticker,
                'Timeframe': timeframe,
                'Divergence Type': signal['type'],
                'First Peak Price': signal['first_peak_price'],
                'Second Peak Price': signal['second_peak_price'],
                'First Peak RSI': signal['first_peak_rsi'],
                'Second Peak RSI': signal['second_peak_rsi']
            }
            rows.append(row)

        df = pd.DataFrame(rows)
        df.to_csv(self.output_file, mode='a', header=False, index=False)

    def get_summary(self):
        """Print summary"""
        if not os.path.exists(self.output_file):
            print("No divergences logged yet")
            return

        df = pd.read_csv(self.output_file)
        if df.empty:
            print("No divergences logged yet")
            return

        print(f"\n{'='*60}")
        print(f"RSI DIVERGENCE SUMMARY - Total: {len(df)}")
        print(f"{'='*60}")
        print(f"\nBy Type:")
        print(df['Divergence Type'].value_counts())
        print(f"\nBy Timeframe:")
        print(df['Timeframe'].value_counts())
        print(f"\nTop 10 Tickers:")
        print(df['Ticker'].value_counts().head(10))
        print(f"{'='*60}\n")
