import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trading_bot import BasicBot, print_order_details
from binance.exceptions import BinanceAPIException

class TestBasicBot(unittest.TestCase):
    """Test suite for BasicBot class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.api_key = 'test_key'
        self.api_secret = 'test_secret'
    
    @patch('trading_bot.Client')
    def test_init_testnet(self, mock_client):
        """Test bot initialization with testnet enabled."""
        bot = BasicBot(self.api_key, self.api_secret, testnet=True)
        self.assertTrue(bot.testnet)
        mock_client.assert_called_once_with(self.api_key, self.api_secret, testnet=True)
    
    @patch('trading_bot.Client')
    def test_init_mainnet(self, mock_client):
        """Test bot initialization with testnet disabled."""
        bot = BasicBot(self.api_key, self.api_secret, testnet=False)
        self.assertFalse(bot.testnet)
        mock_client.assert_called_once_with(self.api_key, self.api_secret, testnet=False)
    
    @patch('trading_bot.Client')
    def test_validate_symbol_valid(self, mock_client):
        """Test validation of a valid trading pair."""
        # Setup mock
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.futures_exchange_info.return_value = {
            'symbols': [
                {'symbol': 'BTCUSDT'},
                {'symbol': 'ETHUSDT'},
                {'symbol': 'BNBUSDT'}
            ]
        }
        
        bot = BasicBot(self.api_key, self.api_secret, testnet=True)
        result = bot.validate_symbol('BTCUSDT')
        self.assertTrue(result)
    
    @patch('trading_bot.Client')
    def test_validate_symbol_invalid(self, mock_client):
        """Test validation of an invalid trading pair."""
        # Setup mock
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.futures_exchange_info.return_value = {
            'symbols': [
                {'symbol': 'BTCUSDT'},
                {'symbol': 'ETHUSDT'}
            ]
        }
        
        bot = BasicBot(self.api_key, self.api_secret, testnet=True)
        result = bot.validate_symbol('INVALIDPAIR')
        self.assertFalse(result)
    
    @patch('trading_bot.Client')
    def test_validate_symbol_api_error(self, mock_client):
        """Test validation when API returns an error."""
        # Setup mock
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.futures_exchange_info.side_effect = BinanceAPIException(
            Mock(status_code=400), 'API Error'
        )
        
        bot = BasicBot(self.api_key, self.api_secret, testnet=True)
        result = bot.validate_symbol('BTCUSDT')
        self.assertFalse(result)
    
    @patch('trading_bot.Client')
    def test_place_market_order_success(self, mock_client):
        """Test successful market order placement."""
        # Setup mock
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.futures_create_order.return_value = {
            'orderId': 123456,
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'type': 'MARKET',
            'origQty': '0.001',
            'executedQty': '0.001',
            'status': 'FILLED',
            'time': 1635340000000
        }
        
        bot = BasicBot(self.api_key, self.api_secret, testnet=True)
        order = bot.place_market_order('BTCUSDT', 'BUY', 0.001)
        
        self.assertEqual(order['orderId'], 123456)
        self.assertEqual(order['symbol'], 'BTCUSDT')
        self.assertEqual(order['side'], 'BUY')
        self.assertEqual(order['type'], 'MARKET')
    
    @patch('trading_bot.Client')
    def test_place_limit_order_success(self, mock_client):
        """Test successful limit order placement."""
        # Setup mock
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.futures_create_order.return_value = {
            'orderId': 123457,
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'type': 'LIMIT',
            'price': '50000.00',
            'origQty': '0.001',
            'status': 'NEW',
            'time': 1635340000000
        }
        
        bot = BasicBot(self.api_key, self.api_secret, testnet=True)
        order = bot.place_limit_order('BTCUSDT', 'BUY', 0.001, 50000.00)
        
        self.assertEqual(order['orderId'], 123457)
        self.assertEqual(order['type'], 'LIMIT')
        self.assertEqual(order['price'], '50000.00')
    
    @patch('trading_bot.Client')
    def test_place_stop_limit_order_success(self, mock_client):
        """Test successful stop-limit order placement."""
        # Setup mock
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.futures_create_order.return_value = {
            'orderId': 123458,
            'symbol': 'BTCUSDT',
            'side': 'SELL',
            'type': 'STOP_LOSS_LIMIT',
            'price': '45000.00',
            'stopPrice': '46000.00',
            'origQty': '0.001',
            'status': 'NEW',
            'time': 1635340000000
        }
        
        bot = BasicBot(self.api_key, self.api_secret, testnet=True)
        order = bot.place_stop_limit_order('BTCUSDT', 'SELL', 0.001, 46000.00, 45000.00)
        
        self.assertEqual(order['orderId'], 123458)
        self.assertEqual(order['type'], 'STOP_LOSS_LIMIT')
        self.assertEqual(order['stopPrice'], '46000.00')
    
    @patch('trading_bot.Client')
    def test_place_oco_order_success(self, mock_client):
        """Test successful OCO order placement."""
        # Setup mock
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.futures_create_order.return_value = {
            'orderId': 123459,
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'type': 'TAKE_PROFIT_LIMIT',
            'price': '52000.00',
            'stopPrice': '48000.00',
            'origQty': '0.001',
            'status': 'NEW',
            'time': 1635340000000
        }
        
        bot = BasicBot(self.api_key, self.api_secret, testnet=True)
        order = bot.place_oco_order('BTCUSDT', 'BUY', 0.001, 52000.00, 48000.00, 47000.00)
        
        self.assertEqual(order['orderId'], 123459)
        self.assertEqual(order['type'], 'TAKE_PROFIT_LIMIT')
    
    @patch('trading_bot.Client')
    def test_get_order_status_success(self, mock_client):
        """Test successful order status retrieval."""
        # Setup mock
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.futures_get_order.return_value = {
            'orderId': 123456,
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'type': 'MARKET',
            'status': 'FILLED',
            'time': 1635340000000
        }
        
        bot = BasicBot(self.api_key, self.api_secret, testnet=True)
        status = bot.get_order_status('BTCUSDT', 123456)
        
        self.assertEqual(status['orderId'], 123456)
        self.assertEqual(status['status'], 'FILLED')
    
    @patch('trading_bot.Client')
    def test_place_market_order_api_error(self, mock_client):
        """Test market order placement with API error."""
        # Setup mock
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.futures_create_order.side_effect = BinanceAPIException(
            Mock(status_code=400), 'Insufficient Balance'
        )
        
        bot = BasicBot(self.api_key, self.api_secret, testnet=True)
        
        with self.assertRaises(BinanceAPIException):
            bot.place_market_order('BTCUSDT', 'BUY', 100)

class TestPrintOrderDetails(unittest.TestCase):
    """Test suite for print_order_details function."""
    
    def test_print_order_details(self):
        """Test printing order details."""
        order = {
            'orderId': 123456,
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'type': 'MARKET',
            'origQty': '0.001',
            'executedQty': '0.001',
            'price': '0',
            'stopPrice': '0',
            'status': 'FILLED',
            'time': 1635340000000
        }
        
        # This should not raise an exception
        try:
            print_order_details(order)
        except Exception as e:
            self.fail(f"print_order_details raised {type(e).__name__} unexpectedly!")

if __name__ == '__main__':
    unittest.main()
