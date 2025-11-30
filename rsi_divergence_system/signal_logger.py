"""
Signal Logger Module
Handles CSV logging of RSI divergence signals
"""

import pandas as pd
import os
from datetime import datetime


class SignalLogger:
    """
    Logs RSI divergence signals to CSV file
    """

    def __init__(self, csv_path='logs/rsi_divergence_signals.csv'):
        """
        Initialize the signal logger

        Parameters:
        - csv_path: Path to the CSV file for logging signals
        """
        self.csv_path = csv_path
        self.columns = [
            'detection_date',
            'ticker',
            'timeframe',
            'divergence_type',
            'first_peak_price',
            'second_peak_price',
            'first_peak_rsi',
            'second_peak_rsi'
        ]
        self._ensure_csv_exists()

    def _ensure_csv_exists(self):
        """
        Ensures the CSV file exists with proper headers
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)

        # Create CSV with headers if it doesn't exist
        if not os.path.exists(self.csv_path):
            df = pd.DataFrame(columns=self.columns)
            df.to_csv(self.csv_path, index=False)

    def log_signals(self, signals):
        """
        Log signals to CSV file

        Parameters:
        - signals: List of signal dictionaries
        """
        if not signals:
            return

        # Convert signals to DataFrame
        new_signals = []
        for signal in signals:
            new_signals.append({
                'detection_date': signal['date'],
                'ticker': signal['ticker'],
                'timeframe': signal['timeframe'],
                'divergence_type': signal['divergence_type'],
                'first_peak_price': signal['first_peak_price'],
                'second_peak_price': signal['second_peak_price'],
                'first_peak_rsi': signal['first_peak_rsi'],
                'second_peak_rsi': signal['second_peak_rsi']
            })

        new_df = pd.DataFrame(new_signals)

        # Append to existing CSV
        existing_df = pd.read_csv(self.csv_path)

        # Combine dataframes
        if existing_df.empty:
            combined_df = new_df
        else:
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)

        # Remove duplicates based on all columns
        combined_df = combined_df.drop_duplicates()

        # Sort by detection date
        combined_df = combined_df.sort_values('detection_date', ascending=False)

        # Save to CSV
        combined_df.to_csv(self.csv_path, index=False)

    def get_signal_count(self):
        """
        Get the total number of signals logged

        Returns:
        - Integer count of signals
        """
        if os.path.exists(self.csv_path):
            df = pd.read_csv(self.csv_path)
            return len(df)
        return 0

    def get_recent_signals(self, n=10):
        """
        Get the most recent signals

        Parameters:
        - n: Number of recent signals to retrieve

        Returns:
        - DataFrame with recent signals
        """
        if os.path.exists(self.csv_path):
            df = pd.read_csv(self.csv_path)
            return df.head(n)
        return pd.DataFrame(columns=self.columns)
