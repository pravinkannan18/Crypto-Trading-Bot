"""
limit_orders.py

Limit Order Logic for Binance Futures with full validation, logging, and API integration.

Usage:
    python src/limit_orders.py BTCUSDT BUY 0.01 50000
    python src/limit_orders.py ETHUSDT SELL 0.5 2000 --time-in-force IOC
"""

import sys
import argparse
from typing import Dict, Optional
from config import (
    setup_logger,
    validate_symbol,
    validate_side,
    validate_quantity,
    validate_price,
    make_request,
    get_current_price,
    get_symbol_filters,
    round_step_size,
    check_api_credentials,
    validate_api_connection
)

logger = setup_logger(__name__)


class LimitOrderExecutor:
    """Handle limit order execution on Binance Futures."""
    
    VALID_TIME_IN_FORCE = ["GTC", "IOC", "FOK", "GTX"]
    
    def __init__(self):
        """Initialize the limit order executor."""
        self.logger = logger
        
    def validate_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        time_in_force: str = "GTC"
    ) -> bool:
        """
        Validate limit order parameters.
        
        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
            side: Order side (BUY or SELL)
            quantity: Order quantity
            price: Limit price
            time_in_force: Time in force (GTC, IOC, FOK, GTX)
            
        Returns:
            True if valid, raises exception otherwise
        """
        self.logger.info(f"Validating limit order: {symbol} {side} {quantity} @ {price}")
        
        # Validate symbol
        if not validate_symbol(symbol):
            raise ValueError(f"Invalid symbol format: {symbol}")
        
        # Validate side
        if not validate_side(side):
            raise ValueError(f"Invalid side: {side}. Must be BUY or SELL")
        
        # Validate quantity
        if not validate_quantity(quantity):
            raise ValueError(f"Invalid quantity: {quantity}. Must be positive")
        
        # Validate price
        if not validate_price(price):
            raise ValueError(f"Invalid price: {price}. Must be positive")
        
        # Validate time in force
        if time_in_force.upper() not in self.VALID_TIME_IN_FORCE:
            raise ValueError(
                f"Invalid time in force: {time_in_force}. "
                f"Must be one of {self.VALID_TIME_IN_FORCE}"
            )
        
        self.logger.info("Order validation passed")
        return True
    
    def adjust_precision(self, symbol: str, quantity: float, price: float) -> tuple:
        """
        Adjust quantity and price to match exchange precision requirements.
        
        Args:
            symbol: Trading pair symbol
            quantity: Original quantity
            price: Original price
            
        Returns:
            Tuple of (adjusted_quantity, adjusted_price)
        """
        try:
            filters = get_symbol_filters(symbol)
            
            # Adjust quantity
            lot_size = filters["filters"].get("LOT_SIZE", {})
            if lot_size:
                step_size = float(lot_size.get("stepSize", "0.001"))
                min_qty = float(lot_size.get("minQty", "0"))
                max_qty = float(lot_size.get("maxQty", "9000000"))
                
                adjusted_qty = round_step_size(quantity, step_size)
                
                if adjusted_qty < min_qty:
                    raise ValueError(f"Quantity {adjusted_qty} below minimum {min_qty}")
                if adjusted_qty > max_qty:
                    raise ValueError(f"Quantity {adjusted_qty} exceeds maximum {max_qty}")
            else:
                adjusted_qty = quantity
            
            # Adjust price
            price_filter = filters["filters"].get("PRICE_FILTER", {})
            if price_filter:
                tick_size = float(price_filter.get("tickSize", "0.01"))
                min_price = float(price_filter.get("minPrice", "0"))
                max_price = float(price_filter.get("maxPrice", "1000000"))
                
                adjusted_price = round_step_size(price, tick_size)
                
                if adjusted_price < min_price:
                    raise ValueError(f"Price {adjusted_price} below minimum {min_price}")
                if adjusted_price > max_price:
                    raise ValueError(f"Price {adjusted_price} exceeds maximum {max_price}")
            else:
                adjusted_price = price
            
            self.logger.info(
                f"Adjusted: qty {quantity} -> {adjusted_qty}, "
                f"price {price} -> {adjusted_price}"
            )
            
            return adjusted_qty, adjusted_price
            
        except Exception as e:
            self.logger.warning(f"Could not adjust precision: {str(e)}. Using original values.")
            return quantity, price
    
    def build_limit_order_params(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        time_in_force: str = "GTC"
    ) -> Dict:
        """
        Build limit order parameters.
        
        Args:
            symbol: Trading pair symbol
            side: Order side (BUY or SELL)
            quantity: Order quantity
            price: Limit price
            time_in_force: Time in force (GTC, IOC, FOK, GTX)
            
        Returns:
            Dictionary of order parameters
        """
        return {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "LIMIT",
            "quantity": quantity,
            "price": price,
            "timeInForce": time_in_force.upper(),
        }
    
    def execute_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
        post_only: bool = False
    ) -> Dict:
        """
        Execute a limit order on Binance Futures.
        
        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
            side: Order side (BUY or SELL)
            quantity: Order quantity
            price: Limit price
            time_in_force: Time in force (GTC, IOC, FOK, GTX)
            reduce_only: If True, order will only reduce position
            post_only: If True, order will be maker-only (GTX)
            
        Returns:
            Order response from exchange
            
        Raises:
            Exception: If order execution fails
        """
        try:
            # Override time_in_force if post_only is True
            if post_only:
                time_in_force = "GTX"
            
            # Validate inputs
            self.validate_order(symbol, side, quantity, price, time_in_force)
            
            # Get current price for logging
            try:
                current_price = get_current_price(symbol)
                self.logger.info(f"Current {symbol} price: {current_price}")
                
                # Check if limit price is too far from market (Binance has limits)
                price_diff_pct = abs(price - current_price) / current_price * 100
                
                # Binance typically allows max 5-10% deviation for limit orders
                max_deviation = 5.0
                
                if price_diff_pct > max_deviation:
                    self.logger.error(
                        f"Limit price {price} is {price_diff_pct:.2f}% away from "
                        f"market price {current_price}"
                    )
                    raise ValueError(
                        f"Limit price too far from market price!\n"
                        f"  Current price: {current_price}\n"
                        f"  Your limit price: {price}\n"
                        f"  Difference: {price_diff_pct:.2f}%\n"
                        f"  Maximum allowed: ~{max_deviation}%\n\n"
                        f"Suggestions:\n"
                        f"  - For SELL orders, use a price closer to current (e.g., {current_price * 1.01:.2f})\n"
                        f"  - For BUY orders, use a price closer to current (e.g., {current_price * 0.99:.2f})\n"
                        f"  - Use market orders if you want immediate execution"
                    )
                elif price_diff_pct > 2:
                    self.logger.warning(
                        f"Limit price {price} is {price_diff_pct:.2f}% away from "
                        f"market price {current_price}"
                    )
            except ValueError:
                # Re-raise our custom validation error
                raise
            except Exception as e:
                self.logger.warning(f"Could not fetch current price: {str(e)}")
            
            # Adjust precision
            adjusted_qty, adjusted_price = self.adjust_precision(symbol, quantity, price)
            
            # Build order parameters
            params = self.build_limit_order_params(
                symbol, side, adjusted_qty, adjusted_price, time_in_force
            )
            
            if reduce_only:
                params["reduceOnly"] = "true"
            
            self.logger.info(f"Placing limit order: {params}")
            
            # Execute order
            endpoint = "/fapi/v1/order"
            response = make_request("POST", endpoint, params, signed=True)
            
            self.logger.info(f"Limit order placed successfully: Order ID {response.get('orderId')}")
            self.logger.info(f"Order details: {response}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to execute limit order: {str(e)}")
            raise
    
    def cancel_order(self, symbol: str, order_id: int) -> Dict:
        """
        Cancel an existing order.
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID to cancel
            
        Returns:
            Cancellation response
        """
        endpoint = "/fapi/v1/order"
        params = {
            "symbol": symbol.upper(),
            "orderId": order_id
        }
        
        try:
            self.logger.info(f"Cancelling order {order_id} for {symbol}")
            response = make_request("DELETE", endpoint, params, signed=True)
            self.logger.info(f"Order {order_id} cancelled successfully")
            return response
        except Exception as e:
            self.logger.error(f"Failed to cancel order: {str(e)}")
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
        description="Execute limit orders on Binance Futures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/limit_orders.py BTCUSDT BUY 0.01 50000
  python src/limit_orders.py ETHUSDT SELL 0.5 2000 --time-in-force IOC
  python src/limit_orders.py BTCUSDT BUY 0.01 50000 --post-only
        """
    )
    
    parser.add_argument("symbol", type=str, help="Trading pair symbol (e.g., BTCUSDT)")
    parser.add_argument("side", type=str, choices=["BUY", "SELL", "buy", "sell"],
                       help="Order side")
    parser.add_argument("quantity", type=float, help="Order quantity")
    parser.add_argument("price", type=float, help="Limit price")
    parser.add_argument("--time-in-force", type=str, default="GTC",
                       choices=["GTC", "IOC", "FOK", "GTX"],
                       help="Time in force (default: GTC)")
    parser.add_argument("--reduce-only", action="store_true",
                       help="Order will only reduce position")
    parser.add_argument("--post-only", action="store_true",
                       help="Order will be maker-only (sets timeInForce to GTX)")
    
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
    executor = LimitOrderExecutor()
    
    try:
        result = executor.execute_limit_order(
            symbol=args.symbol,
            side=args.side.upper(),
            quantity=args.quantity,
            price=args.price,
            time_in_force=args.time_in_force,
            reduce_only=args.reduce_only,
            post_only=args.post_only
        )
        
        print("\n" + "="*50)
        print("ORDER PLACED SUCCESSFULLY")
        print("="*50)
        print(f"Order ID: {result.get('orderId')}")
        print(f"Symbol: {result.get('symbol')}")
        print(f"Side: {result.get('side')}")
        print(f"Type: {result.get('type')}")
        print(f"Quantity: {result.get('origQty')}")
        print(f"Price: {result.get('price')}")
        print(f"Status: {result.get('status')}")
        print(f"Time in Force: {result.get('timeInForce')}")
        if result.get('executedQty') and float(result.get('executedQty')) > 0:
            print(f"Executed Quantity: {result.get('executedQty')}")
        print("="*50)
        
    except Exception as e:
        logger.error(f"Order execution failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        # Demo mode
        print("Limit Orders Demo")
        print("=================")
        print("\nUsage: python src/limit_orders.py SYMBOL SIDE QUANTITY PRICE")
        print("\nExample: python src/limit_orders.py BTCUSDT BUY 0.01 50000")
        
        executor = LimitOrderExecutor()
        params = executor.build_limit_order_params("ETHUSDT", "BUY", 1.0, 1500.0)
        print(f"\nSample order params: {params}")
