"""
stop_limit.py

Stop-Limit Order Logic for Binance Futures.

A Stop-Limit order triggers a limit order when the stop price is reached.

Usage:
    python src/advanced/stop_limit.py BTCUSDT BUY 0.01 49000 49500
    python src/advanced/stop_limit.py ETHUSDT SELL 0.5 2100 2050
"""

import sys
import os
import argparse
from typing import Dict

# Add parent directory to path to import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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


class StopLimitOrderExecutor:
    """Handle stop-limit order execution on Binance Futures."""
    
    def __init__(self):
        """Initialize the stop-limit order executor."""
        self.logger = logger
        
    def validate_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        limit_price: float
    ) -> bool:
        """
        Validate stop-limit order parameters.
        
        Args:
            symbol: Trading pair symbol
            side: Order side (BUY or SELL)
            quantity: Order quantity
            stop_price: Stop/trigger price
            limit_price: Limit price after trigger
            
        Returns:
            True if valid, raises exception otherwise
        """
        self.logger.info(
            f"Validating stop-limit order: {symbol} {side} {quantity} "
            f"stop@{stop_price} limit@{limit_price}"
        )
        
        # Basic validations
        if not validate_symbol(symbol):
            raise ValueError(f"Invalid symbol: {symbol}")
        
        if not validate_side(side):
            raise ValueError(f"Invalid side: {side}")
        
        if not validate_quantity(quantity):
            raise ValueError(f"Invalid quantity: {quantity}")
        
        if not validate_price(stop_price):
            raise ValueError(f"Invalid stop price: {stop_price}")
        
        if not validate_price(limit_price):
            raise ValueError(f"Invalid limit price: {limit_price}")
        
        # Check minimum notional value (quantity × price must be >= $100)
        notional_value = quantity * limit_price
        min_notional = 100.0
        
        if notional_value < min_notional:
            raise ValueError(
                f"Order value too small!\n"
                f"  Quantity: {quantity}\n"
                f"  Price: {limit_price}\n"
                f"  Order value: ${notional_value:.2f}\n"
                f"  Minimum required: ${min_notional:.2f}\n\n"
                f"Solutions:\n"
                f"  1. Increase quantity to at least {min_notional / limit_price:.4f}\n"
                f"  2. Use --reduce-only flag if closing a position\n"
                f"  Example: py bot.py stop-limit {symbol} {side} {min_notional / limit_price:.4f} {stop_price} {limit_price} --reduce-only"
            )
        
        # Logical validation: check price relationship
        if side.upper() == "BUY":
            # For BUY stop-limit: stop_price should be above current market
            # and limit_price should be >= stop_price (to ensure execution)
            if limit_price < stop_price:
                self.logger.warning(
                    f"BUY stop-limit: limit_price ({limit_price}) < stop_price ({stop_price}). "
                    "Order may not execute after trigger."
                )
        else:  # SELL
            # For SELL stop-limit: stop_price should be below current market
            # and limit_price should be <= stop_price
            if limit_price > stop_price:
                self.logger.warning(
                    f"SELL stop-limit: limit_price ({limit_price}) > stop_price ({stop_price}). "
                    "Order may not execute after trigger."
                )
        
        self.logger.info("Order validation passed")
        return True
    
    def adjust_precision(
        self,
        symbol: str,
        quantity: float,
        stop_price: float,
        limit_price: float
    ) -> tuple:
        """
        Adjust values to match exchange precision.
        
        Args:
            symbol: Trading pair symbol
            quantity: Original quantity
            stop_price: Original stop price
            limit_price: Original limit price
            
        Returns:
            Tuple of (adjusted_quantity, adjusted_stop_price, adjusted_limit_price)
        """
        try:
            filters = get_symbol_filters(symbol)
            
            # Adjust quantity
            lot_size = filters["filters"].get("LOT_SIZE", {})
            if lot_size:
                step_size = float(lot_size.get("stepSize", "0.001"))
                adjusted_qty = round_step_size(quantity, step_size)
            else:
                adjusted_qty = quantity
            
            # Adjust prices
            price_filter = filters["filters"].get("PRICE_FILTER", {})
            if price_filter:
                tick_size = float(price_filter.get("tickSize", "0.01"))
                adjusted_stop = round_step_size(stop_price, tick_size)
                adjusted_limit = round_step_size(limit_price, tick_size)
            else:
                adjusted_stop = stop_price
                adjusted_limit = limit_price
            
            self.logger.info(
                f"Adjusted: qty {quantity} -> {adjusted_qty}, "
                f"stop {stop_price} -> {adjusted_stop}, "
                f"limit {limit_price} -> {adjusted_limit}"
            )
            
            return adjusted_qty, adjusted_stop, adjusted_limit
            
        except Exception as e:
            self.logger.warning(f"Could not adjust precision: {str(e)}")
            return quantity, stop_price, limit_price
    
    def execute_stop_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        limit_price: float,
        reduce_only: bool = False,
        working_type: str = "CONTRACT_PRICE"
    ) -> Dict:
        """
        Execute a stop-limit order on Binance Futures.
        
        Args:
            symbol: Trading pair symbol
            side: Order side (BUY or SELL)
            quantity: Order quantity
            stop_price: Stop/trigger price
            limit_price: Limit price after trigger
            reduce_only: If True, order will only reduce position
            working_type: Price type for stop trigger (CONTRACT_PRICE or MARK_PRICE)
            
        Returns:
            Order response from exchange
        """
        try:
            # Validate
            self.validate_order(symbol, side, quantity, stop_price, limit_price)
            
            # Get current price for context
            try:
                current_price = get_current_price(symbol)
                self.logger.info(f"Current {symbol} price: {current_price}")
                
                # Provide helpful context
                if side.upper() == "BUY":
                    if stop_price <= current_price:
                        self.logger.warning(
                            f"BUY stop-limit: stop_price ({stop_price}) <= current price ({current_price}). "
                            "This will trigger immediately!"
                        )
                else:  # SELL
                    if stop_price >= current_price:
                        self.logger.warning(
                            f"SELL stop-limit: stop_price ({stop_price}) >= current price ({current_price}). "
                            "This will trigger immediately!"
                        )
                        
            except Exception as e:
                self.logger.warning(f"Could not fetch current price: {str(e)}")
            
            # Adjust precision
            adj_qty, adj_stop, adj_limit = self.adjust_precision(
                symbol, quantity, stop_price, limit_price
            )
            
            # Build order parameters
            params = {
                "symbol": symbol.upper(),
                "side": side.upper(),
                "type": "STOP",  # Binance Futures uses "STOP" for stop-limit
                "quantity": adj_qty,
                "price": adj_limit,
                "stopPrice": adj_stop,
                "timeInForce": "GTC",
                "workingType": working_type
            }
            
            if reduce_only:
                params["reduceOnly"] = "true"
            
            self.logger.info(f"Placing stop-limit order: {params}")
            
            # Execute order
            endpoint = "/fapi/v1/order"
            response = make_request("POST", endpoint, params, signed=True)
            
            self.logger.info(
                f"Stop-limit order placed successfully: Order ID {response.get('orderId')}"
            )
            self.logger.info(f"Order details: {response}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to execute stop-limit order: {str(e)}")
            raise
    
    def cancel_order(self, symbol: str, order_id: int) -> Dict:
        """Cancel a stop-limit order."""
        endpoint = "/fapi/v1/order"
        params = {
            "symbol": symbol.upper(),
            "orderId": order_id
        }
        
        try:
            self.logger.info(f"Cancelling order {order_id}")
            response = make_request("DELETE", endpoint, params, signed=True)
            self.logger.info(f"Order {order_id} cancelled successfully")
            return response
        except Exception as e:
            self.logger.error(f"Failed to cancel order: {str(e)}")
            raise


def main():
    """Main function for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Execute stop-limit orders on Binance Futures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # BUY stop-limit: trigger at 49000, then place limit buy at 49500
  python src/advanced/stop_limit.py BTCUSDT BUY 0.01 49000 49500
  
  # SELL stop-limit: trigger at 2100, then place limit sell at 2050
  python src/advanced/stop_limit.py ETHUSDT SELL 0.5 2100 2050
  
  # Stop-loss: SELL when price drops to 48000, limit at 47900
  python src/advanced/stop_limit.py BTCUSDT SELL 0.01 48000 47900 --reduce-only
        """
    )
    
    parser.add_argument("symbol", type=str, help="Trading pair symbol")
    parser.add_argument("side", type=str, choices=["BUY", "SELL", "buy", "sell"],
                       help="Order side")
    parser.add_argument("quantity", type=float, help="Order quantity")
    parser.add_argument("stop_price", type=float, help="Stop/trigger price")
    parser.add_argument("limit_price", type=float, help="Limit price after trigger")
    parser.add_argument("--reduce-only", action="store_true",
                       help="Order will only reduce position")
    parser.add_argument("--working-type", type=str, default="CONTRACT_PRICE",
                       choices=["CONTRACT_PRICE", "MARK_PRICE"],
                       help="Price type for stop trigger")
    
    args = parser.parse_args()
    
    # Check credentials
    if not check_api_credentials():
        logger.error("API credentials not configured")
        sys.exit(1)
    
    if not validate_api_connection():
        logger.error("Failed to connect to Binance API")
        sys.exit(1)
    
    # Execute
    executor = StopLimitOrderExecutor()
    
    try:
        result = executor.execute_stop_limit_order(
            symbol=args.symbol,
            side=args.side.upper(),
            quantity=args.quantity,
            stop_price=args.stop_price,
            limit_price=args.limit_price,
            reduce_only=args.reduce_only,
            working_type=args.working_type
        )
        
        print("\n" + "="*50)
        print("STOP-LIMIT ORDER PLACED SUCCESSFULLY")
        print("="*50)
        print(f"Order ID: {result.get('orderId')}")
        print(f"Symbol: {result.get('symbol')}")
        print(f"Side: {result.get('side')}")
        print(f"Type: {result.get('type')}")
        print(f"Quantity: {result.get('origQty')}")
        print(f"Stop Price: {result.get('stopPrice')}")
        print(f"Limit Price: {result.get('price')}")
        print(f"Status: {result.get('status')}")
        print(f"Working Type: {result.get('workingType')}")
        print("="*50)
        print("\nOrder will trigger when market reaches stop price")
        
    except Exception as e:
        logger.error(f"Order execution failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        print("Stop-Limit Orders Demo")
        print("======================")
        print("\nUsage: python src/advanced/stop_limit.py SYMBOL SIDE QUANTITY STOP_PRICE LIMIT_PRICE")
        print("\nExample: python src/advanced/stop_limit.py BTCUSDT BUY 0.01 49000 49500")
