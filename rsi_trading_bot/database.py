"""
Database module for RSI Trading Bot
Handles all data persistence using SQLite
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from config import Config


class TradingDatabase:
    """Singleton database manager for trading bot"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.db_path = 'trading_bot.db'
        self._create_tables()
        self._initialized = True

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _create_tables(self):
        """Create all required database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Signals table - RSI divergence signals detected
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ticker TEXT NOT NULL,
                    divergence_type TEXT NOT NULL,  -- 'Bullish' or 'Bearish'
                    timeframe TEXT NOT NULL,        -- '1d', '3d', '1w'
                    entry_price REAL NOT NULL,
                    rsi_value REAL,
                    status TEXT DEFAULT 'pending',   -- 'pending', 'executed', 'skipped', 'failed'
                    notes TEXT,
                    UNIQUE(ticker, detected_at, divergence_type, timeframe)
                )
            """)

            # Orders table - All orders placed (market, stop loss, limit)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER,
                    alpaca_order_id TEXT UNIQUE,
                    ticker TEXT NOT NULL,
                    order_type TEXT NOT NULL,       -- 'market', 'stop', 'limit'
                    side TEXT NOT NULL,             -- 'buy', 'sell'
                    quantity REAL NOT NULL,
                    price REAL,
                    filled_price REAL,
                    status TEXT NOT NULL,           -- 'pending', 'filled', 'cancelled', 'rejected'
                    placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    filled_at TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (signal_id) REFERENCES signals(id)
                )
            """)

            # Positions table - Current open positions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER,
                    ticker TEXT NOT NULL,
                    direction TEXT NOT NULL,        -- 'LONG' or 'SHORT'
                    entry_price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    initial_stop REAL NOT NULL,
                    current_stop REAL NOT NULL,
                    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    t1_executed BOOLEAN DEFAULT 0,
                    t1_price REAL,
                    t1_at TIMESTAMP,
                    t2_executed BOOLEAN DEFAULT 0,
                    t2_price REAL,
                    t2_at TIMESTAMP,
                    remaining_quantity REAL,
                    status TEXT DEFAULT 'open',      -- 'open', 'closed'
                    FOREIGN KEY (signal_id) REFERENCES signals(id)
                )
            """)

            # Trades table - Completed trades with P&L
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    position_id INTEGER NOT NULL,
                    signal_id INTEGER,
                    ticker TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    opened_at TIMESTAMP NOT NULL,
                    closed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    hold_days INTEGER,
                    exit_reason TEXT,               -- 'target1', 'target2', 'target3', 'stop_loss', 'max_hold'
                    gross_pnl REAL NOT NULL,
                    net_pnl REAL NOT NULL,
                    return_pct REAL NOT NULL,
                    FOREIGN KEY (position_id) REFERENCES positions(id),
                    FOREIGN KEY (signal_id) REFERENCES signals(id)
                )
            """)

            # Performance table - Daily performance metrics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
                    signals_detected INTEGER DEFAULT 0,
                    trades_opened INTEGER DEFAULT 0,
                    trades_closed INTEGER DEFAULT 0,
                    daily_pnl REAL DEFAULT 0,
                    cumulative_pnl REAL DEFAULT 0,
                    win_count INTEGER DEFAULT 0,
                    loss_count INTEGER DEFAULT 0,
                    largest_win REAL DEFAULT 0,
                    largest_loss REAL DEFAULT 0,
                    open_positions INTEGER DEFAULT 0,
                    notes TEXT
                )
            """)

            # Create indices for faster queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_ticker ON orders(ticker)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_ticker ON positions(ticker)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_date ON performance(date)")

    # ==================== SIGNAL METHODS ====================

    def add_signal(self, ticker: str, divergence_type: str, timeframe: str,
                   entry_price: float, rsi_value: float = None, notes: str = None) -> int:
        """Add a new RSI divergence signal"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO signals (ticker, divergence_type, timeframe, entry_price, rsi_value, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ticker, divergence_type, timeframe, entry_price, rsi_value, notes))
            return cursor.lastrowid

    def get_pending_signals(self) -> List[Dict]:
        """Get all pending signals that haven't been executed"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM signals
                WHERE status = 'pending'
                ORDER BY detected_at
            """)
            return [dict(row) for row in cursor.fetchall()]

    def update_signal_status(self, signal_id: int, status: str, notes: str = None):
        """Update signal status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if notes:
                cursor.execute("""
                    UPDATE signals SET status = ?, notes = ? WHERE id = ?
                """, (status, notes, signal_id))
            else:
                cursor.execute("""
                    UPDATE signals SET status = ? WHERE id = ?
                """, (status, signal_id))

    def check_for_duplicate_signal(self, ticker: str, divergence_type: str,
                                   timeframe: str, entry_price: float) -> Dict:
        """
        Check if an identical signal already exists in the last 2 weeks

        Compares: ticker, divergence_type, timeframe, and close price

        Args:
            ticker: Stock ticker symbol
            divergence_type: 'Bullish' or 'Bearish'
            timeframe: '1d', '3d', '1w'
            entry_price: Signal close price

        Returns:
            Dict with 'is_duplicate' (bool) and 'original' (dict) if duplicate found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get datetime 2 weeks ago
            from datetime import datetime, timedelta
            two_weeks_ago = (datetime.now() - timedelta(weeks=2)).strftime('%Y-%m-%d %H:%M:%S')

            # Look for matching signal in last 2 weeks
            cursor.execute("""
                SELECT id, ticker, divergence_type, timeframe, entry_price,
                       detected_at, status
                FROM signals
                WHERE ticker = ?
                AND divergence_type = ?
                AND timeframe = ?
                AND ABS(entry_price - ?) < 0.01
                AND detected_at >= ?
                ORDER BY detected_at DESC
                LIMIT 1
            """, (ticker, divergence_type, timeframe, entry_price, two_weeks_ago))

            result = cursor.fetchone()

            if result:
                # Found a duplicate
                return {
                    'is_duplicate': True,
                    'original': {
                        'id': result[0],
                        'ticker': result[1],
                        'divergence_type': result[2],
                        'timeframe': result[3],
                        'entry_price': result[4],
                        'detected_at': result[5],
                        'status': result[6]
                    }
                }
            else:
                return {'is_duplicate': False}

    def get_executed_signals_today(self, ticker: str) -> bool:
        """
        Check if we already executed a signal for this ticker today

        Args:
            ticker: Stock ticker symbol

        Returns:
            True if ticker was executed today, False otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get today's date
            from datetime import datetime
            today = datetime.now().strftime('%Y-%m-%d')

            # Check for executed signals today
            cursor.execute("""
                SELECT COUNT(*) FROM signals
                WHERE ticker = ?
                AND status = 'executed'
                AND DATE(detected_at) = ?
            """, (ticker, today))

            count = cursor.fetchone()[0]
            return count > 0

    def has_active_signal_or_position(self, ticker: str) -> bool:
        """
        Check if ticker already has a pending signal or open position

        Args:
            ticker: Stock ticker symbol

        Returns:
            True if ticker should be skipped (has active signal/position), False if safe to add
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check for pending signals
            cursor.execute("""
                SELECT COUNT(*) FROM signals
                WHERE ticker = ? AND status = 'pending'
            """, (ticker,))
            pending_count = cursor.fetchone()[0]

            if pending_count > 0:
                return True

            # Check for open positions
            cursor.execute("""
                SELECT COUNT(*) FROM positions
                WHERE ticker = ? AND status = 'open'
            """, (ticker,))
            open_count = cursor.fetchone()[0]

            return open_count > 0

    # ==================== ORDER METHODS ====================

    def add_order(self, signal_id: int, alpaca_order_id: str, ticker: str,
                  order_type: str, side: str, quantity: float, price: float = None) -> int:
        """Add a new order"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO orders (signal_id, alpaca_order_id, ticker, order_type, side, quantity, price, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (signal_id, alpaca_order_id, ticker, order_type, side, quantity, price))
            return cursor.lastrowid

    def update_order_status(self, alpaca_order_id: str, status: str,
                           filled_price: float = None, filled_at: datetime = None):
        """Update order status when filled/cancelled"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE orders
                SET status = ?, filled_price = ?, filled_at = ?
                WHERE alpaca_order_id = ?
            """, (status, filled_price, filled_at, alpaca_order_id))

    def get_order_by_alpaca_id(self, alpaca_order_id: str) -> Optional[Dict]:
        """Get order by Alpaca order ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM orders WHERE alpaca_order_id = ?", (alpaca_order_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # ==================== POSITION METHODS ====================

    def add_position(self, signal_id: int, ticker: str, direction: str,
                     entry_price: float, quantity: float, initial_stop: float) -> int:
        """Add a new open position"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO positions
                (signal_id, ticker, direction, entry_price, quantity, initial_stop,
                 current_stop, remaining_quantity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (signal_id, ticker, direction, entry_price, quantity, initial_stop,
                  initial_stop, quantity))
            return cursor.lastrowid

    def get_open_positions(self) -> List[Dict]:
        """Get all open positions"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM positions
                WHERE status = 'open'
                ORDER BY opened_at
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_position_by_ticker(self, ticker: str) -> Optional[Dict]:
        """Get open position for a specific ticker"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM positions
                WHERE ticker = ? AND status = 'open'
                LIMIT 1
            """, (ticker,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_position_target(self, position_id: int, target: int, price: float):
        """Update when a profit target is hit (target: 1 or 2)"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if target == 1:
                cursor.execute("""
                    UPDATE positions
                    SET t1_executed = 1, t1_price = ?, t1_at = ?
                    WHERE id = ?
                """, (price, timestamp, position_id))
            elif target == 2:
                cursor.execute("""
                    UPDATE positions
                    SET t2_executed = 1, t2_price = ?, t2_at = ?
                    WHERE id = ?
                """, (price, timestamp, position_id))

    def update_position_stop(self, position_id: int, new_stop: float):
        """Update position's current stop loss"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE positions SET current_stop = ? WHERE id = ?
            """, (new_stop, position_id))

    def update_position_quantity(self, position_id: int, new_quantity: float):
        """Update remaining quantity after partial exit"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE positions SET remaining_quantity = ? WHERE id = ?
            """, (new_quantity, position_id))

    def close_position(self, position_id: int):
        """Mark position as closed"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE positions SET status = 'closed' WHERE id = ?
            """, (position_id,))

    # ==================== TRADE METHODS ====================

    def add_trade(self, position_id: int, signal_id: int, ticker: str, direction: str,
                  entry_price: float, exit_price: float, quantity: float,
                  opened_at: datetime, hold_days: int, exit_reason: str,
                  gross_pnl: float, net_pnl: float, return_pct: float) -> int:
        """Add a completed trade"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades
                (position_id, signal_id, ticker, direction, entry_price, exit_price,
                 quantity, opened_at, hold_days, exit_reason, gross_pnl, net_pnl, return_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (position_id, signal_id, ticker, direction, entry_price, exit_price,
                  quantity, opened_at, hold_days, exit_reason, gross_pnl, net_pnl, return_pct))
            return cursor.lastrowid

    def get_all_trades(self) -> List[Dict]:
        """Get all completed trades"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades ORDER BY closed_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_trades_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Get trades within date range"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades
                WHERE DATE(closed_at) BETWEEN ? AND ?
                ORDER BY closed_at
            """, (start_date, end_date))
            return [dict(row) for row in cursor.fetchall()]

    # ==================== PERFORMANCE METHODS ====================

    def update_daily_performance(self, date: str, **metrics):
        """Update daily performance metrics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Build dynamic update query
            columns = ', '.join([f"{k} = ?" for k in metrics.keys()])
            values = list(metrics.values()) + [date]

            cursor.execute(f"""
                INSERT INTO performance (date) VALUES (?)
                ON CONFLICT(date) DO UPDATE SET {columns}
            """, [date] + values)

    def get_performance_summary(self, days: int = 30) -> Dict:
        """Get performance summary for last N days"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    SUM(trades_opened) as total_trades,
                    SUM(trades_closed) as closed_trades,
                    SUM(daily_pnl) as total_pnl,
                    SUM(win_count) as wins,
                    SUM(loss_count) as losses,
                    MAX(largest_win) as best_trade,
                    MIN(largest_loss) as worst_trade
                FROM performance
                WHERE date >= DATE('now', '-' || ? || ' days')
            """, (days,))

            row = cursor.fetchone()
            return dict(row) if row else {}

    # ==================== UTILITY METHODS ====================

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall bot statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Total signals
            cursor.execute("SELECT COUNT(*) as count FROM signals")
            stats['total_signals'] = cursor.fetchone()['count']

            # Open positions
            cursor.execute("SELECT COUNT(*) as count FROM positions WHERE status = 'open'")
            stats['open_positions'] = cursor.fetchone()['count']

            # Total trades
            cursor.execute("SELECT COUNT(*) as count FROM trades")
            stats['total_trades'] = cursor.fetchone()['count']

            # Win rate
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as wins
                FROM trades
            """)
            result = cursor.fetchone()
            total = result['total']
            wins = result['wins'] or 0
            stats['win_rate'] = (wins / total * 100) if total > 0 else 0

            # Total P&L
            cursor.execute("SELECT SUM(net_pnl) as total_pnl FROM trades")
            stats['total_pnl'] = cursor.fetchone()['total_pnl'] or 0

            return stats


# Singleton instance
def get_database() -> TradingDatabase:
    """Get the singleton database instance"""
    return TradingDatabase()
