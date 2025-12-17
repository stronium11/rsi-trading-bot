"""
Live RSI Divergence Scanner
Scans for new RSI divergence signals daily before market open
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'rsi_divergence_system'))

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
from rsi_divergence_detector import calculate_rsi, detect_divergence
from nasdaq100_tickers import get_nasdaq100_tickers
from sp500_tickers import get_sp500_tickers
from data_fetcher import get_data_fetcher
from database import get_database
from telegram_bot import get_bot
from config import Config


class LiveScanner:
    """
    Scans for RSI divergence signals in real-time
    Runs daily before market open (7:00 AM ET)
    """

    def __init__(self):
        """Initialize the live scanner"""
        self.timeframes = ['1d', '3d', '1w']

        # Combine Nasdaq 100 and S&P 500 tickers
        nasdaq_tickers = get_nasdaq100_tickers()
        sp500_tickers = get_sp500_tickers()
        combined = list(set(nasdaq_tickers + sp500_tickers))
        self.tickers = sorted(combined)

        self.data_fetcher = get_data_fetcher()
        self.db = get_database()
        self.telegram = get_bot()

        # Filters
        self.min_price = 5.0          # Minimum price $5
        self.min_volume = 500000      # Minimum volume 500k

    def fetch_recent_data(self, ticker: str, timeframe: str, days: int = 60) -> pd.DataFrame:
        """
        Fetch recent data for scanning

        Parameters:
        - ticker: Stock ticker symbol
        - timeframe: Timeframe interval ('1d', '3d', '1w')
        - days: Number of days to fetch (default 60)

        Returns:
        - DataFrame with recent data or None
        """
        try:
            # Fetch recent daily data
            df = self.data_fetcher.fetch_historical_data(ticker, period=f'{days}d', interval='1day')

            if df is None or len(df) == 0:
                return None

            # Resample for 3d or 1w if needed
            if timeframe == '3d':
                df = self.data_fetcher.resample_to_3d(df)
            elif timeframe == '1w':
                df = self.data_fetcher.resample_to_weekly(df)

            return df

        except Exception as e:
            print(f"Error fetching data for {ticker} ({timeframe}): {str(e)}")
            return None

    def passes_filters(self, ticker: str, df: pd.DataFrame) -> bool:
        """
        Check if ticker passes minimum filters

        Parameters:
        - ticker: Stock ticker symbol
        - df: DataFrame with price data

        Returns:
        - True if passes filters, False otherwise
        """
        try:
            if df is None or len(df) == 0:
                return False

            # Get latest price and volume
            latest_price = df['close'].iloc[-1]
            latest_volume = df['volume'].iloc[-1] if 'volume' in df.columns else 0

            # Check filters
            if latest_price < self.min_price:
                return False

            if latest_volume < self.min_volume:
                return False

            return True

        except Exception as e:
            print(f"Error checking filters for {ticker}: {str(e)}")
            return False

    def detect_recent_divergence(self, ticker: str, timeframe: str) -> List[Dict]:
        """
        Detect divergence in recent data (last 5 candles only)

        Parameters:
        - ticker: Stock ticker symbol
        - timeframe: Timeframe to scan

        Returns:
        - List of new signals
        """
        try:
            # Fetch recent data (60 days provides enough history for RSI)
            df = self.fetch_recent_data(ticker, timeframe, days=60)

            if df is None or len(df) < 50:
                return []

            # Apply filters
            if not self.passes_filters(ticker, df):
                return []

            # Calculate RSI
            rsi_values = calculate_rsi(df)

            # Detect divergences
            df_with_divergence = detect_divergence(df, rsi_values)

            # Only look at last 5 candles for NEW signals
            recent_df = df_with_divergence.tail(5)

            signals = []

            # Extract bearish divergences
            bearish = recent_df[recent_df['bearish_divergence'] == True]
            for idx, row in bearish.iterrows():
                signal = {
                    'ticker': ticker,
                    'timeframe': timeframe,
                    'signal_date': idx,
                    'divergence_type': 'Bearish',
                    'entry_price': float(df_with_divergence.loc[idx, 'close']),
                    'rsi_value': float(rsi_values.loc[idx]),
                    'first_peak_price': float(row['divergence_first_peak_price']),
                    'second_peak_price': float(row['divergence_second_peak_price']),
                    'first_peak_rsi': float(row['divergence_first_peak_rsi']),
                    'second_peak_rsi': float(row['divergence_second_peak_rsi'])
                }
                signals.append(signal)

            # Extract bullish divergences
            bullish = recent_df[recent_df['bullish_divergence'] == True]
            for idx, row in bullish.iterrows():
                signal = {
                    'ticker': ticker,
                    'timeframe': timeframe,
                    'signal_date': idx,
                    'divergence_type': 'Bullish',
                    'entry_price': float(df_with_divergence.loc[idx, 'close']),
                    'rsi_value': float(rsi_values.loc[idx]),
                    'first_peak_price': float(row['divergence_first_peak_price']),
                    'second_peak_price': float(row['divergence_second_peak_price']),
                    'first_peak_rsi': float(row['divergence_first_peak_rsi']),
                    'second_peak_rsi': float(row['divergence_second_peak_rsi'])
                }
                signals.append(signal)

            return signals

        except Exception as e:
            print(f"Error detecting divergence for {ticker} ({timeframe}): {str(e)}")
            return []

    def scan_all_tickers(self) -> List[Dict]:
        """
        Scan all tickers for new RSI divergence signals

        Returns:
        - List of all signals found
        """
        print(f"\n{'='*70}")
        print(f"LIVE RSI DIVERGENCE SCANNER")
        print(f"Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}")
        print(f"{'='*70}\n")

        all_signals = []
        total_tickers = len(self.tickers)

        for i, ticker in enumerate(self.tickers, 1):
            print(f"Scanning {i}/{total_tickers}: {ticker}...", end='\r')

            for timeframe in self.timeframes:
                signals = self.detect_recent_divergence(ticker, timeframe)
                all_signals.extend(signals)

        print(f"\n{'='*70}")
        print(f"Scan Complete: {len(all_signals)} signals detected")
        print(f"{'='*70}\n")

        return all_signals

    async def save_and_notify_signals(self, signals: List[Dict]):
        """
        Save signals to database and send Telegram notifications

        Parameters:
        - signals: List of signal dictionaries
        """
        if len(signals) == 0:
            print("No new signals to save.")
            await self.telegram.send_message("✅ Daily scan complete. No new signals detected.")
            return

        print(f"\nSaving {len(signals)} signals to database...")

        saved_count = 0
        skipped_count = 0
        duplicate_details = []

        for signal in signals:
            try:
                ticker = signal['ticker']
                divergence_type = signal['divergence_type']
                timeframe = signal['timeframe']
                entry_price = signal['entry_price']

                # SOPHISTICATED DUPLICATE CHECK
                # Compares: ticker, timeframe, direction, AND close price within 2 weeks
                duplicate_check = self.db.check_for_duplicate_signal(
                    ticker=ticker,
                    divergence_type=divergence_type,
                    timeframe=timeframe,
                    entry_price=entry_price
                )

                if duplicate_check['is_duplicate']:
                    original = duplicate_check['original']
                    print(f"⚠️  Skipping {ticker} - duplicate signal")
                    print(f"   Current: {divergence_type} {timeframe} @ ${entry_price:.2f}")
                    print(f"   Original: Signal #{original['id']} from {original['detected_at']}")
                    skipped_count += 1

                    # Store details for summary notification
                    duplicate_details.append({
                        'ticker': ticker,
                        'divergence_type': divergence_type,
                        'timeframe': timeframe,
                        'entry_price': entry_price,
                        'original_id': original['id'],
                        'original_date': original['detected_at']
                    })
                    continue

                # Add signal to database
                signal_id = self.db.add_signal(
                    ticker=ticker,
                    divergence_type=divergence_type,
                    timeframe=timeframe,
                    entry_price=entry_price,
                    rsi_value=signal['rsi_value'],
                    notes=f"Detected on {signal['signal_date']}"
                )

                saved_count += 1

                # Send Telegram notification for NEW signals
                await self.telegram.send_signal_alert(
                    ticker=ticker,
                    divergence_type=divergence_type,
                    timeframe=timeframe,
                    entry_price=entry_price
                )

            except Exception as e:
                print(f"Error saving signal {signal['ticker']}: {str(e)}")

        print(f"✅ Saved {saved_count}/{len(signals)} signals to database")
        if skipped_count > 0:
            print(f"⚠️  Skipped {skipped_count} duplicate signals")

        # Send summary notification
        summary = f"""
📊 *Daily Scan Summary*

Total Signals: {len(signals)}
Saved to Database: {saved_count}
"""
        if skipped_count > 0:
            summary += f"Duplicates Skipped: {skipped_count}\n"

        summary += "\nBreakdown:\n"

        # Count by type
        bullish_count = sum(1 for s in signals if s['divergence_type'] == 'Bullish')
        bearish_count = sum(1 for s in signals if s['divergence_type'] == 'Bearish')

        summary += f"• Bullish: {bullish_count}\n"
        summary += f"• Bearish: {bearish_count}\n\n"

        # Count by timeframe
        summary += "By Timeframe:\n"
        for tf in self.timeframes:
            count = sum(1 for s in signals if s['timeframe'] == tf)
            summary += f"• {tf}: {count}\n"

        # Add duplicate details if any
        if duplicate_details:
            summary += f"\n⚠️ *Duplicate Signals Detected:*\n"
            for dup in duplicate_details:
                summary += (f"• {dup['ticker']} ({dup['divergence_type']} {dup['timeframe']}) "
                           f"@ ${dup['entry_price']:.2f}\n"
                           f"  _Duplicate of signal #{dup['original_id']} from {dup['original_date']}_\n")

        await self.telegram.send_message(summary, parse_mode='Markdown')

    def get_pending_signals_count(self) -> int:
        """Get count of pending signals in database"""
        pending = self.db.get_pending_signals()
        return len(pending)

    async def run_daily_scan(self):
        """
        Main method to run the daily scan
        Called by scheduler at 7:00 AM ET before market open
        """
        try:
            print("\n" + "="*70)
            print("STARTING DAILY RSI DIVERGENCE SCAN")
            print("="*70 + "\n")

            # Notify scan start
            await self.telegram.send_message("🔍 Starting daily RSI divergence scan...")

            # Scan all tickers
            signals = self.scan_all_tickers()

            # Save and notify
            await self.save_and_notify_signals(signals)

            # Get pending count
            pending_count = self.get_pending_signals_count()

            print(f"\n✅ Daily scan complete!")
            print(f"   Pending signals ready for trading: {pending_count}\n")

            return signals

        except Exception as e:
            error_msg = f"❌ Error during daily scan: {str(e)}"
            print(error_msg)
            await self.telegram.send_message(error_msg)
            raise


def get_scanner() -> LiveScanner:
    """Get the scanner instance"""
    return LiveScanner()


# For testing
if __name__ == "__main__":
    import asyncio

    async def test_scan():
        scanner = get_scanner()
        await scanner.run_daily_scan()

    asyncio.run(test_scan())
