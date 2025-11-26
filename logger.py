"""
Signal logging module - writes signals to CSV file
"""
import pandas as pd
import os
from typing import List, Dict
from datetime import datetime
import config


class SignalLogger:
    """Logs trading signals to CSV file"""

    def __init__(self, output_file: str = config.OUTPUT_FILE):
        self.output_file = output_file
        self.columns = [
            'Date',
            'Asset Name',
            'SMA Affected',
            'Timeframe',
            'Trend',
            'Signal Price',
            'SMA Value',
            'Distance %',
            'Timestamp'
        ]
        self._initialize_file()

    def _initialize_file(self):
        """Create CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.output_file):
            df = pd.DataFrame(columns=self.columns)
            df.to_csv(self.output_file, index=False)
            print(f"Created new signal log file: {self.output_file}")

    def log_signals(self, signals: List[Dict]):
        """
        Log signals to CSV file

        Args:
            signals: List of signal dictionaries
        """
        if not signals:
            return

        # Convert signals to DataFrame format
        rows = []
        for signal in signals:
            row = {
                'Date': signal['date'],
                'Asset Name': signal['ticker'],
                'SMA Affected': signal['sma_period'],
                'Timeframe': signal['timeframe'],
                'Trend': signal['trend'],
                'Signal Price': signal['price'],
                'SMA Value': signal['sma_value'],
                'Distance %': signal['distance_pct'],
                'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            rows.append(row)

        # Append to CSV
        df = pd.DataFrame(rows)
        df.to_csv(self.output_file, mode='a', header=False, index=False)

        print(f"Logged {len(signals)} signals to {self.output_file}")

    def get_recent_signals(self, days: int = 7) -> pd.DataFrame:
        """
        Read recent signals from CSV

        Args:
            days: Number of days to look back

        Returns:
            DataFrame with recent signals
        """
        if not os.path.exists(self.output_file):
            return pd.DataFrame()

        df = pd.read_csv(self.output_file)
        if df.empty:
            return df

        # Filter by date
        df['Date'] = pd.to_datetime(df['Date'])
        cutoff_date = datetime.now() - pd.Timedelta(days=days)
        recent = df[df['Date'] >= cutoff_date]

        return recent

    def print_summary(self):
        """Print summary of logged signals"""
        if not os.path.exists(self.output_file):
            print("No signals logged yet")
            return

        df = pd.read_csv(self.output_file)
        if df.empty:
            print("No signals logged yet")
            return

        print(f"\n{'='*60}")
        print(f"SIGNAL SUMMARY - Total Signals: {len(df)}")
        print(f"{'='*60}")
        print(f"\nSignals by Asset:")
        print(df['Asset Name'].value_counts().head(10))
        print(f"\nSignals by SMA Period:")
        print(df['SMA Affected'].value_counts())
        print(f"\nSignals by Timeframe:")
        print(df['Timeframe'].value_counts())
        print(f"\nSignals by Trend:")
        print(df['Trend'].value_counts())
        print(f"{'='*60}\n")
