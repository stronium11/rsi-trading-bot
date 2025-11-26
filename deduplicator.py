"""
Deduplication module - prevents duplicate signals
"""
import json
import os
from typing import Dict, List
from datetime import datetime, timedelta
import config


class SignalDeduplicator:
    """Manages signal history to prevent duplicates"""

    def __init__(self, history_file: str = config.SIGNALS_HISTORY_FILE):
        self.history_file = history_file
        self.history = self._load_history()

    def _load_history(self) -> Dict:
        """Load signal history from file"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading history: {e}")
                return {}
        return {}

    def _save_history(self):
        """Save signal history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    def _get_signal_key(self, ticker: str, sma_period: int, timeframe: str) -> str:
        """Generate unique key for a signal type"""
        return f"{ticker}_{sma_period}_{timeframe}"

    def is_duplicate(self, signal: Dict) -> bool:
        """
        Check if this signal was already registered recently

        Args:
            signal: Signal dictionary with ticker, sma_period, timeframe, date

        Returns:
            True if this is a duplicate, False otherwise
        """
        key = self._get_signal_key(
            signal['ticker'],
            signal['sma_period'],
            signal['timeframe']
        )

        if key not in self.history:
            return False

        last_signal_date_str = self.history[key]
        current_date_str = signal['date']

        try:
            last_date = datetime.strptime(last_signal_date_str, '%Y-%m-%d')
            current_date = datetime.strptime(current_date_str, '%Y-%m-%d')

            # For daily timeframe, check if signal was yesterday
            if signal['timeframe'] == '1d':
                # If last signal was yesterday or today, it's a duplicate
                if (current_date - last_date).days <= 1:
                    return True
            else:
                # For 3d and 1w, check if signals are within a few days
                if (current_date - last_date).days <= 3:
                    return True

            return False

        except Exception as e:
            print(f"Error checking duplicate: {e}")
            return False

    def register_signal(self, signal: Dict):
        """
        Register a signal in history

        Args:
            signal: Signal dictionary with ticker, sma_period, timeframe, date
        """
        key = self._get_signal_key(
            signal['ticker'],
            signal['sma_period'],
            signal['timeframe']
        )
        self.history[key] = signal['date']
        self._save_history()

    def filter_duplicates(self, signals: List[Dict]) -> List[Dict]:
        """
        Filter out duplicate signals from a list

        Args:
            signals: List of signal dictionaries

        Returns:
            List of non-duplicate signals
        """
        filtered = []
        for signal in signals:
            if not self.is_duplicate(signal):
                filtered.append(signal)
                self.register_signal(signal)
        return filtered
