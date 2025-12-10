"""
Alpaca API Client Wrapper
Handles all interactions with Alpaca trading API
"""

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, StopLossRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from config import Config
import logging

logger = logging.getLogger(__name__)


class AlpacaClient:
    """Wrapper for Alpaca trading and data APIs"""

    def __init__(self):
        """Initialize Alpaca clients"""
        self.trading_client = TradingClient(
            api_key=Config.ALPACA_API_KEY,
            secret_key=Config.ALPACA_SECRET_KEY,
            paper=True  # Always start with paper trading
        )

        self.data_client = StockHistoricalDataClient(
            api_key=Config.ALPACA_API_KEY,
            secret_key=Config.ALPACA_SECRET_KEY
        )

        logger.info("Alpaca clients initialized (Paper Trading)")

    def get_account(self):
        """Get account information"""
        try:
            account = self.trading_client.get_account()
            return {
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value),
                'buying_power': float(account.buying_power),
                'equity': float(account.equity),
                'status': account.status
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None

    def get_positions(self):
        """Get all open positions"""
        try:
            positions = self.trading_client.get_all_positions()
            return [{
                'symbol': pos.symbol,
                'qty': float(pos.qty),
                'side': pos.side,
                'avg_entry_price': float(pos.avg_entry_price),
                'current_price': float(pos.current_price),
                'market_value': float(pos.market_value),
                'unrealized_pl': float(pos.unrealized_pl),
                'unrealized_plpc': float(pos.unrealized_plpc)
            } for pos in positions]
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    def get_position(self, symbol):
        """Get specific position"""
        try:
            pos = self.trading_client.get_open_position(symbol)
            return {
                'symbol': pos.symbol,
                'qty': float(pos.qty),
                'side': pos.side,
                'avg_entry_price': float(pos.avg_entry_price),
                'current_price': float(pos.current_price),
                'market_value': float(pos.market_value),
                'unrealized_pl': float(pos.unrealized_pl),
                'unrealized_plpc': float(pos.unrealized_plpc)
            }
        except Exception as e:
            logger.debug(f"No position for {symbol}: {e}")
            return None

    def place_market_order(self, symbol, direction, position_size):
        """
        Place market order

        Args:
            symbol: Stock ticker
            direction: 'LONG' or 'SHORT'
            position_size: Dollar amount to invest

        Returns:
            Order object or None
        """
        try:
            # Get current price to calculate shares
            bars = self.get_latest_bars([symbol])
            if not bars or symbol not in bars:
                logger.error(f"Cannot get price for {symbol}")
                return None

            current_price = bars[symbol]['close']

            # Calculate shares (fractional allowed)
            shares = position_size / current_price

            # Determine side
            side = OrderSide.BUY if direction == 'LONG' else OrderSide.SELL

            # Create market order
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=shares,
                side=side,
                time_in_force=TimeInForce.DAY
            )

            order = self.trading_client.submit_order(order_data)

            logger.info(f"Market order placed: {symbol} {direction} {shares:.4f} shares @ ${current_price:.2f}")

            return {
                'order_id': order.id,
                'symbol': symbol,
                'qty': shares,
                'side': direction,
                'price': current_price,
                'status': order.status
            }

        except Exception as e:
            logger.error(f"Error placing market order for {symbol}: {e}")
            return None

    def place_stop_loss_order(self, symbol, direction, stop_price, qty):
        """
        Place stop loss order

        Args:
            symbol: Stock ticker
            direction: 'LONG' or 'SHORT'
            stop_price: Stop loss trigger price
            qty: Number of shares

        Returns:
            Order object or None
        """
        try:
            # For LONG, stop is below entry (sell stop)
            # For SHORT, stop is above entry (buy stop)
            side = OrderSide.SELL if direction == 'LONG' else OrderSide.BUY

            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side,
                time_in_force=TimeInForce.GTC,
                stop_loss={'stop_price': stop_price}
            )

            order = self.trading_client.submit_order(order_data)

            logger.info(f"Stop loss order placed: {symbol} @ ${stop_price:.2f}")

            return {
                'order_id': order.id,
                'symbol': symbol,
                'type': 'stop_loss',
                'stop_price': stop_price
            }

        except Exception as e:
            logger.error(f"Error placing stop loss for {symbol}: {e}")
            return None

    def cancel_order(self, order_id):
        """Cancel an order"""
        try:
            self.trading_client.cancel_order_by_id(order_id)
            logger.info(f"Order {order_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False

    def cancel_all_orders(self, symbol=None):
        """Cancel all orders (optionally for specific symbol)"""
        try:
            if symbol:
                orders = self.trading_client.get_orders(filter={'symbols': [symbol]})
                for order in orders:
                    self.trading_client.cancel_order_by_id(order.id)
            else:
                self.trading_client.cancel_orders()

            logger.info(f"All orders cancelled{' for ' + symbol if symbol else ''}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")
            return False

    def close_position(self, symbol, qty=None):
        """
        Close position (partial or full)

        Args:
            symbol: Stock ticker
            qty: Number of shares (None = close all)

        Returns:
            Order object or None
        """
        try:
            if qty:
                self.trading_client.close_position(symbol, qty=qty)
                logger.info(f"Closed {qty} shares of {symbol}")
            else:
                self.trading_client.close_position(symbol)
                logger.info(f"Closed full position of {symbol}")
            return True
        except Exception as e:
            logger.error(f"Error closing position {symbol}: {e}")
            return False

    def get_latest_bars(self, symbols, timeframe='1Min'):
        """
        Get latest price bars for symbols

        Args:
            symbols: List of ticker symbols
            timeframe: '1Min', '1Hour', '1Day', etc.

        Returns:
            Dict of {symbol: {open, high, low, close, volume}}
        """
        try:
            # Map timeframe string to Alpaca TimeFrame
            tf_map = {
                '1Min': TimeFrame.Minute,
                '5Min': TimeFrame.Minute * 5,
                '15Min': TimeFrame.Minute * 15,
                '1Hour': TimeFrame.Hour,
                '1Day': TimeFrame.Day
            }

            tf = tf_map.get(timeframe, TimeFrame.Minute)

            request = StockBarsRequest(
                symbol_or_symbols=symbols,
                timeframe=tf,
                start=datetime.now() - timedelta(days=1),
                end=datetime.now()
            )

            bars = self.data_client.get_stock_bars(request)

            result = {}
            for symbol in symbols:
                if symbol in bars:
                    latest = bars[symbol][-1]  # Get most recent bar
                    result[symbol] = {
                        'open': float(latest.open),
                        'high': float(latest.high),
                        'low': float(latest.low),
                        'close': float(latest.close),
                        'volume': int(latest.volume),
                        'timestamp': latest.timestamp
                    }

            return result

        except Exception as e:
            logger.error(f"Error getting latest bars: {e}")
            return {}

    def is_market_open(self):
        """Check if market is currently open"""
        try:
            clock = self.trading_client.get_clock()
            return clock.is_open
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False

    def get_market_hours(self):
        """Get next market open/close times"""
        try:
            clock = self.trading_client.get_clock()
            return {
                'is_open': clock.is_open,
                'next_open': clock.next_open,
                'next_close': clock.next_close
            }
        except Exception as e:
            logger.error(f"Error getting market hours: {e}")
            return None


# Singleton instance
_client_instance = None

def get_alpaca_client():
    """Get singleton Alpaca client instance"""
    global _client_instance
    if _client_instance is None:
        _client_instance = AlpacaClient()
    return _client_instance
