import os
import logging
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv
import google.generativeai as genai
from binance.client import Client
from binance.enums import *

# Constants
ORDER_TYPES = ["MARKET", "LIMIT", "STOP_LIMIT"]

# Configure logging
def setup_logging():
    # Main bot logger
    bot_logger = logging.getLogger('bot')
    bot_logger.setLevel(logging.INFO)
    bot_handler = logging.FileHandler('logs/bot.log')
    bot_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    bot_logger.addHandler(bot_handler)
    
    # Raw requests logger
    req_logger = logging.getLogger('requests')
    req_logger.setLevel(logging.DEBUG)
    req_handler = logging.FileHandler('logs/raw_requests.log')
    req_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    req_logger.addHandler(req_handler)
    
    return bot_logger, req_logger

class GeminiAnalyzer:
    def __init__(self, api_key: str):
        """Initialize Gemini model with API key."""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        self.logger = logging.getLogger('bot')
    
    def analyze_trend(self, symbol: str) -> str:
        """Analyze market trend using Gemini model."""
        try:
            prompt = f"""
            Analyze {symbol} cryptocurrency trend and suggest whether to BUY, SELL, or HOLD.
            Consider current market conditions and give a brief explanation.
            Format response as: <DECISION>: <EXPLANATION>
            """
            response = self.model.generate_content(prompt)
            self.logger.info(f"Gemini Analysis for {symbol}: {response.text}")
            return response.text
        except Exception as e:
            self.logger.error(f"Gemini analysis error: {str(e)}")
            return "ERROR: Unable to get market analysis"

class BinanceTrader:
    def __init__(self, api_key: str, api_secret: str):
        """Initialize Binance trader with API credentials."""
        # Strip quotes if present in the API credentials
        api_key = api_key.strip('"').strip("'")
        api_secret = api_secret.strip('"').strip("'")
        
        # Initialize Binance client with testnet=True for testing
        self.client = Client(api_key, api_secret, testnet=True)
        self.logger = logging.getLogger('bot')
        self.req_logger = logging.getLogger('requests')
    
    def place_order(
        self, 
        symbol: str, 
        side: str, 
        order_type: str, 
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Dict:
        """Place an order on Binance Futures."""
        try:
            # Prepare order parameters
            params = {
                "symbol": symbol,
                "side": side,
                "quantity": quantity
            }
            
            if order_type == "MARKET":
                params["type"] = Client.ORDER_TYPE_MARKET
            elif order_type == "LIMIT":
                params["type"] = Client.ORDER_TYPE_LIMIT
                params["price"] = price
                params["timeInForce"] = Client.TIME_IN_FORCE_GTC
            elif order_type == "STOP_LIMIT":
                params["type"] = Client.ORDER_TYPE_STOP_LOSS_LIMIT
                params["price"] = price
                params["stopPrice"] = stop_price
                params["timeInForce"] = Client.TIME_IN_FORCE_GTC
            
            # Log order parameters
            self.req_logger.debug(f"Placing order with params: {params}")
            
            # Place futures order
            response = self.client.futures_create_order(**params)
            
            self.logger.info(f"Order placed successfully: {response}")
            return response
                
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Error placing order: {error_msg}")
            return {"error": error_msg}
    
    def get_account_balance(self) -> Dict:
        """Get account balance information."""
        try:
            balance = self.client.futures_account_balance()
            self.logger.info("Account balance retrieved successfully")
            return balance
        
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Error getting balance: {error_msg}")
            return {"error": error_msg}

def validate_symbol(symbol: str) -> bool:
    """Validate if symbol is a proper trading pair."""
    # Common quote currencies for Binance Futures
    quote_currencies = ['USDT', 'BUSD', 'USDC']
    
    # Symbol must end with a quote currency
    valid = any(symbol.endswith(quote) for quote in quote_currencies)
    
    # Symbol cannot BE just the quote currency
    valid = valid and symbol not in quote_currencies
    
    return valid

def get_user_input() -> Dict:
    """Get trading parameters from user."""
    inputs = {}
    
    # Get symbol with validation
    while True:
        symbol = input("Enter symbol (e.g., BTCUSDT): ").upper().strip()
        
        if validate_symbol(symbol):
            inputs["symbol"] = symbol
            break
        else:
            print("❌ Invalid symbol!")
            print("   Symbol must be a trading pair like BTCUSDT, ETHUSDT, BNBUSDT")
            print("   (Cannot use just 'USDT', 'BTC', etc.)")
            print("   Examples: BTCUSDT, ETHUSDT, DOGEUSDT, LINKUSDT")
    
    # Get side
    while True:
        side = input("Enter side (BUY/SELL): ").upper().strip()
        if side in ["BUY", "SELL"]:
            inputs["side"] = side
            break
        print("Invalid side. Please enter BUY or SELL.")
    
    # Get order type
    while True:
        order_type = input("Enter order type (MARKET/LIMIT/STOP_LIMIT): ").upper().strip()
        if order_type in ORDER_TYPES:
            inputs["order_type"] = order_type
            break
        print(f"Invalid order type. Please enter one of: {', '.join(ORDER_TYPES)}")
    
    # Get quantity
    while True:
        try:
            quantity_input = input("Enter quantity: ").strip()
            inputs["quantity"] = float(quantity_input)
            if inputs["quantity"] <= 0:
                print("❌ Quantity must be greater than 0.")
                continue
            break
        except ValueError:
            print("❌ Invalid quantity. Please enter a number.")
    
    # Get price for LIMIT and STOP_LIMIT orders
    if inputs["order_type"] in ["LIMIT", "STOP_LIMIT"]:
        while True:
            try:
                inputs["price"] = float(input("Enter limit price: "))
                break
            except ValueError:
                print("Invalid price. Please enter a number.")
    
    # Get stop price for STOP_LIMIT orders
    if inputs["order_type"] == "STOP_LIMIT":
        while True:
            try:
                inputs["stop_price"] = float(input("Enter stop price: "))
                break
            except ValueError:
                print("Invalid stop price. Please enter a number.")
    
    return inputs

def main():
    # Load environment variables
    load_dotenv()
    
    # Setup logging
    bot_logger, _ = setup_logging()
    
    # Initialize components
    gemini = GeminiAnalyzer(os.getenv("GEMINI_API_KEY"))
    
    try:
        # Initialize Binance trader
        trader = BinanceTrader(
            os.getenv("BINANCE_API_KEY"),
            os.getenv("BINANCE_API_SECRET")
        )
        
        # Show account balance before trading
        balance = trader.get_account_balance()
        if "error" not in balance:
            print("\nCurrent Account Balance:")
            for asset in balance:
                if float(asset['balance']) > 0:
                    print(f"{asset['asset']}: {asset['balance']}")
        
        # Get user inputs
        inputs = get_user_input()
        
        # Get Gemini analysis
        analysis = gemini.analyze_trend(inputs["symbol"])
        print(f"\nGemini Analysis:\n{analysis}")
        
        # Ask for confirmation
        confirm = input("\nProceed with trade? (y/n): ").lower()
        if confirm != 'y':
            print("Trade cancelled.")
            return
        
        # Place order
        order_result = trader.place_order(
            symbol=inputs["symbol"],
            side=inputs["side"],
            order_type=inputs["order_type"],
            quantity=inputs["quantity"],
            price=inputs.get("price"),
            stop_price=inputs.get("stop_price")
        )
        
        # Print result
        if "error" in order_result:
            print(f"❌ Order failed: {order_result['error']}")
        else:
            print(f"✅ Order executed successfully. Order ID: {order_result.get('orderId')}")
            
            # Show updated balance
            updated_balance = trader.get_account_balance()
            if "error" not in updated_balance:
                print("\nUpdated Account Balance:")
                for asset in updated_balance:
                    if float(asset['balance']) > 0:
                        print(f"{asset['asset']}: {asset['balance']}")
            
    except Exception as e:
        bot_logger.error(f"Main execution error: {str(e)}")
        print(f"❌ An error occurred: {str(e)}")

if __name__ == "__main__":
    main()