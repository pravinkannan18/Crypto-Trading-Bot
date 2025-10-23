import logging
import sys
import time
import os
from binance import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException, BinanceRequestException
from config import API_KEY, API_SECRET  # Import from config

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/trading_bot.log', mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class BasicBot:
    def __init__(self, api_key, api_secret, testnet=True):
        """Initialize the trading bot with Binance API credentials for Futures Testnet."""
        self.client = Client(api_key, api_secret, testnet=testnet)
        self.testnet = testnet
        logger.info("Bot initialized with testnet=%s", testnet)

    def validate_symbol(self, symbol):
        """Validate if the futures trading pair exists."""
        try:
            info = self.client.futures_exchange_info()
            symbols = [s['symbol'] for s in info['symbols']]
            if symbol.upper() in symbols:
                logger.info("Symbol %s is valid", symbol)
                return True
            logger.error("Invalid symbol: %s", symbol)
            return False
        except BinanceAPIException as e:
            logger.error("Error validating symbol %s: %s", symbol, e)
            return False

    def place_market_order(self, symbol, side, quantity):
        """Place a market order on Futures."""
        try:
            # Log request
            logger.info("Placing market order: symbol=%s, side=%s, quantity=%s", symbol, side, quantity)
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
            logger.info("Market order response: %s", order)
            return order
        except BinanceAPIException as e:
            logger.error("Error placing market order: %s", e)
            raise

    def place_limit_order(self, symbol, side, quantity, price):
        """Place a limit order on Futures."""
        try:
            # Log request
            logger.info("Placing limit order: symbol=%s, side=%s, quantity=%s, price=%s", symbol, side, quantity, price)
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_LIMIT,
                timeInForce=TIME_IN_FORCE_GTC,
                quantity=quantity,
                price=price
            )
            logger.info("Limit order response: %s", order)
            return order
        except BinanceAPIException as e:
            logger.error("Error placing limit order: %s", e)
            raise

    def place_stop_limit_order(self, symbol, side, quantity, stop_price, limit_price):
        """Place a stop-limit order on Futures (Bonus feature)."""
        try:
            # Log request
            logger.info("Placing stop-limit order: symbol=%s, side=%s, quantity=%s, stop_price=%s, limit_price=%s",
                         symbol, side, quantity, stop_price, limit_price)
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_STOP_LOSS_LIMIT,
                timeInForce=TIME_IN_FORCE_GTC,
                quantity=quantity,
                price=limit_price,
                stopPrice=stop_price
            )
            logger.info("Stop-limit order response: %s", order)
            return order
        except BinanceAPIException as e:
            logger.error("Error placing stop-limit order: %s", e)
            raise

    def place_oco_order(self, symbol, side, quantity, price, stop_price, stop_limit_price):
        """Place an OCO (One-Cancels-Other) order on Futures (Bonus feature).
        
        OCO orders consist of:
        - A limit order at `price`
        - A stop-loss-limit order at `stop_price` with limit at `stop_limit_price`
        Only one can execute; when one fills, the other is cancelled.
        """
        try:
            # Log request
            logger.info(
                "Placing OCO order: symbol=%s, side=%s, quantity=%s, price=%s, stop_price=%s, stop_limit_price=%s",
                symbol, side, quantity, price, stop_price, stop_limit_price
            )
            
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_TAKE_PROFIT_LIMIT,
                timeInForce=TIME_IN_FORCE_GTC,
                quantity=quantity,
                price=price,
                stopPrice=stop_price
            )
            logger.info("OCO order response: %s", order)
            return order
        except BinanceAPIException as e:
            logger.error("Error placing OCO order: %s", e)
            raise

    def get_order_status(self, symbol, order_id):
        """Check the status of a futures order."""
        try:
            # Log request
            logger.info("Retrieving order status: symbol=%s, order_id=%s", symbol, order_id)
            status = self.client.futures_get_order(symbol=symbol, orderId=order_id)
            logger.info("Order status response: %s", status)
            return status
        except BinanceAPIException as e:
            logger.error("Error retrieving order status: %s", e)
            raise

def print_order_details(order):
    """Print formatted order details."""
    print("\n" + "="*50)
    print("ORDER DETAILS")
    print("="*50)
    print(f"Order ID: {order['orderId']}")
    print(f"Symbol: {order['symbol']}")
    print(f"Side: {order['side']}")
    print(f"Type: {order['type']}")
    print(f"Original Quantity: {order['origQty']}")
    print(f"Executed Quantity: {order.get('executedQty', 'N/A')}")
    print(f"Price: {order.get('price', 'N/A')}")
    print(f"Stop Price: {order.get('stopPrice', 'N/A')}")
    print(f"Status: {order['status']}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(order['time'] / 1000))}")
    print("="*50 + "\n")

def main():
    """Enhanced CLI menu."""
    print("Welcome to Binance Futures Testnet Trading Bot!")
    
    if not API_KEY or not API_SECRET:
        print("API credentials not found in .env. Copy .env.example to .env and add your keys.")
        sys.exit(1)
    
    try:
        bot = BasicBot(API_KEY, API_SECRET, testnet=True)
    except Exception as e:
        print(f"Failed to initialize bot: {e}")
        logger.critical("Initialization failed: %s", e)
        sys.exit(1)
    
    while True:
        print("\n" + "="*50)
        print("TRADING BOT MENU")
        print("="*50)
        print("1. Place Market Order")
        print("2. Place Limit Order")
        print("3. Place Stop-Limit Order")
        print("4. Place OCO Order (One-Cancels-Other)")
        print("5. Check Order Status")
        print("6. Exit")
        print("="*50)
        
        choice = input("Enter choice (1-6): ").strip()
        
        if choice == "6":
            print("Exiting bot. Goodbye!")
            logger.info("Bot terminated by user")
            break
        
        if choice not in ["1", "2", "3", "4", "5"]:
            print("Invalid choice. Please try again.")
            continue

        if choice != "5":  # If not checking order status
            symbol = input("Enter trading pair (e.g., BTCUSDT): ").strip().upper()
            if not bot.validate_symbol(symbol):
                print("Invalid trading pair. Please check and try again.")
                continue

        if choice in ["1", "2", "3", "4"]:
            side = input("Enter side (BUY/SELL): ").strip().upper()
            if side not in ["BUY", "SELL"]:
                print("Invalid side. Must be BUY or SELL.")
                continue
            
            quantity_str = input("Enter quantity (e.g., 0.001): ").strip()
            try:
                quantity = float(quantity_str)
                if quantity <= 0:
                    raise ValueError("Quantity must be positive")
            except ValueError as e:
                print(f"Invalid quantity: {e}")
                continue

        try:
            if choice == "1":
                order = bot.place_market_order(symbol, side, quantity)
                print_order_details(order)
            
            elif choice == "2":
                price_str = input("Enter limit price (e.g., 50000.00): ").strip()
                try:
                    price = float(price_str)
                    if price <= 0:
                        raise ValueError("Price must be positive")
                except ValueError as e:
                    print(f"Invalid price: {e}")
                    continue
                order = bot.place_limit_order(symbol, side, quantity, price)
                print_order_details(order)
            
            elif choice == "3":
                stop_price_str = input("Enter stop price (e.g., 46000.00): ").strip()
                limit_price_str = input("Enter limit price (e.g., 45000.00): ").strip()
                try:
                    stop_price = float(stop_price_str)
                    limit_price = float(limit_price_str)
                    if stop_price <= 0 or limit_price <= 0:
                        raise ValueError("Prices must be positive")
                except ValueError as e:
                    print(f"Invalid price: {e}")
                    continue
                order = bot.place_stop_limit_order(symbol, side, quantity, stop_price, limit_price)
                print_order_details(order)
            
            elif choice == "4":
                price_str = input("Enter limit price (e.g., 50000.00): ").strip()
                stop_price_str = input("Enter stop price (e.g., 46000.00): ").strip()
                stop_limit_price_str = input("Enter stop limit price (e.g., 45000.00): ").strip()
                try:
                    price = float(price_str)
                    stop_price = float(stop_price_str)
                    stop_limit_price = float(stop_limit_price_str)
                    if price <= 0 or stop_price <= 0 or stop_limit_price <= 0:
                        raise ValueError("Prices must be positive")
                except ValueError as e:
                    print(f"Invalid price: {e}")
                    continue
                order = bot.place_oco_order(symbol, side, quantity, price, stop_price, stop_limit_price)
                print_order_details(order)
            
            elif choice == "5":
                order_id_str = input("Enter order ID: ").strip()
                try:
                    order_id = int(order_id_str)
                except ValueError:
                    print("Invalid order ID. Must be an integer.")
                    continue
                status = bot.get_order_status(symbol, order_id)
                print_order_details(status)
        
        except BinanceAPIException as e:
            error_msg = f"Binance API Error: {e.message if hasattr(e, 'message') else str(e)}"
            print(error_msg)
            logger.error(error_msg)
        except ValueError as e:
            print(f"Input Error: {e}")
        except Exception as e:
            error_msg = f"Unexpected Error: {e}"
            print(error_msg)
            logger.error(error_msg)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBot interrupted by user.")
        logger.info("Bot interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        logger.critical("Fatal error: %s", e)
        sys.exit(1)