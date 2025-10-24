"""
market_orders.py

Market Order Logic for Binance Futures with full validation, logging, and API integration.

Usage:
    python src/market_orders.py BTCUSDT BUY 0.01
    python src/market_orders.py ETHUSDT SELL 0.5
"""

import sys
import argparse
from typing import Dict, Optional
from config import (
    setup_logger,
    validate_symbol,
    validate_side,
    validate_quantity,
    make_request,
    get_current_price,
    get_symbol_filters,
    round_step_size,
    check_api_credentials,
    validate_api_connection
)

logger = setup_logger(__name__)


class MarketOrderExecutor:
    """Handle market order execution on Binance Futures."""
    
    def __init__(self):
        """Initialize the market order executor."""
        self.logger = logger
        
    def validate_order(self, symbol: str, side: str, quantity: float) -> bool:
        """
        Validate market order parameters.
        
        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
            side: Order side (BUY or SELL)
            quantity: Order quantity
            
        Returns:
            True if valid, raises exception otherwise
        """
        self.logger.info(f"Validating market order: {symbol} {side} {quantity}")
        
        # Validate symbol
        if not validate_symbol(symbol):
            raise ValueError(f"Invalid symbol format: {symbol}. Must be a valid futures symbol (e.g., BTCUSDT)")
        
        # Validate side
        if not validate_side(side):
            raise ValueError(f"Invalid side: {side}. Must be BUY or SELL")
        
        # Validate quantity
        if not validate_quantity(quantity):
            raise ValueError(f"Invalid quantity: {quantity}. Must be a positive number")
        
        self.logger.info("Order validation passed")
        return True
    
    def adjust_quantity_precision(self, symbol: str, quantity: float) -> float:
        """
        Adjust quantity to match exchange precision requirements.
        
        Args:
            symbol: Trading pair symbol
            quantity: Original quantity
            
        Returns:
            Adjusted quantity
        """
        try:
            filters = get_symbol_filters(symbol)
            lot_size = filters["filters"].get("LOT_SIZE", {})
            
            if lot_size:
                step_size = float(lot_size.get("stepSize", "0.001"))
                min_qty = float(lot_size.get("minQty", "0"))
                max_qty = float(lot_size.get("maxQty", "9000000"))
                
                # Round to step size
                adjusted_qty = round_step_size(quantity, step_size)
                
                # Check min/max
                if adjusted_qty < min_qty:
                    raise ValueError(f"Quantity {adjusted_qty} is below minimum {min_qty}")
                if adjusted_qty > max_qty:
                    raise ValueError(f"Quantity {adjusted_qty} exceeds maximum {max_qty}")
                
                self.logger.info(f"Adjusted quantity from {quantity} to {adjusted_qty}")
                return adjusted_qty
            else:
                return quantity
                
        except Exception as e:
            self.logger.warning(f"Could not adjust quantity precision: {str(e)}. Using original quantity.")
            return quantity
    
    def build_market_order_params(self, symbol: str, side: str, quantity: float) -> Dict:
        """
        Build market order parameters.
        
        Args:
            symbol: Trading pair symbol
            side: Order side (BUY or SELL)
            quantity: Order quantity
            
        Returns:
            Dictionary of order parameters
        """
        return {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "MARKET",
            "quantity": quantity,
        }
    
    def execute_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        reduce_only: bool = False
    ) -> Dict:
        """
        Execute a market order on Binance Futures.
        
        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
            side: Order side (BUY or SELL)
            quantity: Order quantity
            reduce_only: If True, order will only reduce position
            
        Returns:
            Order response from exchange
            
        Raises:
            Exception: If order execution fails
        """
        try:
            # Validate inputs
            self.validate_order(symbol, side, quantity)
            
            # Get current price for logging
            try:
                current_price = get_current_price(symbol)
                self.logger.info(f"Current {symbol} price: {current_price}")
            except Exception as e:
                self.logger.warning(f"Could not fetch current price: {str(e)}")
                current_price = None
            
            # Adjust quantity precision
            adjusted_quantity = self.adjust_quantity_precision(symbol, quantity)
            
            # Build order parameters
            params = self.build_market_order_params(symbol, side, adjusted_quantity)
            
            if reduce_only:
                params["reduceOnly"] = "true"
            
            self.logger.info(f"Placing market order: {params}")
            
            # Execute order
            endpoint = "/fapi/v1/order"
            response = make_request("POST", endpoint, params, signed=True)
            
            self.logger.info(f"Market order executed successfully: Order ID {response.get('orderId')}")
            self.logger.info(f"Order details: {response}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to execute market order: {str(e)}")
            raise
    
    def get_order_status(self, symbol: str, order_id: int) -> Dict:
        """
        Query order status.
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID
            
        Returns:
            Order status information
        """
        endpoint = "/fapi/v1/order"
        params = {
            "symbol": symbol.upper(),
            "orderId": order_id
        }
        
        try:
            response = make_request("GET", endpoint, params, signed=True)
            self.logger.info(f"Order {order_id} status: {response.get('status')}")
            return response
        except Exception as e:
            self.logger.error(f"Failed to get order status: {str(e)}")
            raise


def main():
    """Main function for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Execute market orders on Binance Futures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/market_orders.py BTCUSDT BUY 0.01
  python src/market_orders.py ETHUSDT SELL 0.5
  python src/market_orders.py BTCUSDT BUY 0.01 --reduce-only
        """
    )
    
    parser.add_argument("symbol", type=str, help="Trading pair symbol (e.g., BTCUSDT)")
    parser.add_argument("side", type=str, choices=["BUY", "SELL", "buy", "sell"],
                       help="Order side")
    parser.add_argument("quantity", type=float, help="Order quantity")
    parser.add_argument("--reduce-only", action="store_true",
                       help="Order will only reduce position")
    
    args = parser.parse_args()
    
    # Check API credentials
    if not check_api_credentials():
        logger.error("API credentials not configured. Please set environment variables:")
        logger.error("  BINANCE_TESTNET_API_KEY")
        logger.error("  BINANCE_TESTNET_SECRET_KEY")
        sys.exit(1)
    
    # Validate API connection
    if not validate_api_connection():
        logger.error("Failed to connect to Binance API")
        sys.exit(1)
    
    # Execute order
    executor = MarketOrderExecutor()
    
    try:
        result = executor.execute_market_order(
            symbol=args.symbol,
            side=args.side.upper(),
            quantity=args.quantity,
            reduce_only=args.reduce_only
        )
        
        print("\n" + "="*50)
        print("ORDER EXECUTED SUCCESSFULLY")
        print("="*50)
        print(f"Order ID: {result.get('orderId')}")
        print(f"Symbol: {result.get('symbol')}")
        print(f"Side: {result.get('side')}")
        print(f"Type: {result.get('type')}")
        print(f"Quantity: {result.get('origQty')}")
        print(f"Status: {result.get('status')}")
        print(f"Executed Quantity: {result.get('executedQty')}")
        if result.get('avgPrice'):
            print(f"Average Price: {result.get('avgPrice')}")
        print("="*50)
        
    except Exception as e:
        logger.error(f"Order execution failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        # Demo mode
        print("Market Orders Demo")
        print("==================")
        print("\nUsage: python src/market_orders.py SYMBOL SIDE QUANTITY")
        print("\nExample: python src/market_orders.py BTCUSDT BUY 0.01")
        
        executor = MarketOrderExecutor()
        params = executor.build_market_order_params("BTCUSDT", "BUY", 0.01)
        print(f"\nSample order params: {params}")
