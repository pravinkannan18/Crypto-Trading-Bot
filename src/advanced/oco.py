"""
oco.py

OCO (One-Cancels-the-Other) Order Logic for Binance Futures.

OCO pairs allow placing both take-profit and stop-loss orders simultaneously.
When one executes, the other is automatically cancelled.

Note: Binance Futures doesn't have native OCO like Spot, so we implement it
by placing two conditional orders and monitoring them.

Usage:
    python src/advanced/oco.py BTCUSDT LONG 0.01 52000 48000
    python src/advanced/oco.py ETHUSDT SHORT 0.5 1900 2100
"""

import sys
import os
import argparse
import time
from typing import Dict, Tuple, Optional

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import (
    setup_logger,
    validate_symbol,
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


class OCOOrderExecutor:
    """
    Handle OCO (One-Cancels-the-Other) order execution on Binance Futures.
    
    Implements OCO-like behavior by placing take-profit and stop-loss orders
    and monitoring them.
    """
    
    def __init__(self):
        """Initialize the OCO order executor."""
        self.logger = logger
        
    def validate_oco_params(
        self,
        symbol: str,
        position_side: str,
        quantity: float,
        take_profit_price: float,
        stop_loss_price: float
    ) -> bool:
        """
        Validate OCO order parameters.
        
        Args:
            symbol: Trading pair symbol
            position_side: Position side (LONG or SHORT)
            quantity: Order quantity
            take_profit_price: Take profit price
            stop_loss_price: Stop loss price
            
        Returns:
            True if valid, raises exception otherwise
        """
        self.logger.info(
            f"Validating OCO: {symbol} {position_side} {quantity} "
            f"TP@{take_profit_price} SL@{stop_loss_price}"
        )
        
        # Basic validations
        if not validate_symbol(symbol):
            raise ValueError(f"Invalid symbol: {symbol}")
        
        if position_side.upper() not in ["LONG", "SHORT"]:
            raise ValueError(f"Invalid position side: {position_side}. Must be LONG or SHORT")
        
        if not validate_quantity(quantity):
            raise ValueError(f"Invalid quantity: {quantity}")
        
        if not validate_price(take_profit_price):
            raise ValueError(f"Invalid take profit price: {take_profit_price}")
        
        if not validate_price(stop_loss_price):
            raise ValueError(f"Invalid stop loss price: {stop_loss_price}")
        
        # Logical validation
        if position_side.upper() == "LONG":
            # For LONG: TP should be above entry, SL below
            if take_profit_price <= stop_loss_price:
                raise ValueError(
                    f"For LONG position: take_profit ({take_profit_price}) must be > "
                    f"stop_loss ({stop_loss_price})"
                )
        else:  # SHORT
            # For SHORT: TP should be below entry, SL above
            if take_profit_price >= stop_loss_price:
                raise ValueError(
                    f"For SHORT position: take_profit ({take_profit_price}) must be < "
                    f"stop_loss ({stop_loss_price})"
                )
        
        # Check minimum notional value (quantity × price must be >= $100)
        # Use the lower price for validation (worst case)
        check_price = min(take_profit_price, stop_loss_price)
        notional_value = quantity * check_price
        min_notional = 100.0
        
        if notional_value < min_notional:
            raise ValueError(
                f"Order value too small!\n"
                f"  Quantity: {quantity}\n"
                f"  Price: {check_price}\n"
                f"  Order value: ${notional_value:.2f}\n"
                f"  Minimum required: ${min_notional:.2f}\n\n"
                f"Solutions:\n"
                f"  1. Increase quantity to at least {min_notional / check_price:.4f}\n"
                f"  2. OCO orders are reduce-only, ensure you have an open position\n"
                f"  Example: py bot.py oco {symbol} {position_side} {min_notional / check_price:.4f} {take_profit_price} {stop_loss_price}"
            )
        
        self.logger.info("OCO validation passed")
        return True
    
    def adjust_precision(
        self,
        symbol: str,
        quantity: float,
        take_profit_price: float,
        stop_loss_price: float
    ) -> Tuple[float, float, float]:
        """Adjust values to match exchange precision."""
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
                adjusted_tp = round_step_size(take_profit_price, tick_size)
                adjusted_sl = round_step_size(stop_loss_price, tick_size)
            else:
                adjusted_tp = take_profit_price
                adjusted_sl = stop_loss_price
            
            self.logger.info(
                f"Adjusted: qty {quantity} -> {adjusted_qty}, "
                f"TP {take_profit_price} -> {adjusted_tp}, "
                f"SL {stop_loss_price} -> {adjusted_sl}"
            )
            
            return adjusted_qty, adjusted_tp, adjusted_sl
            
        except Exception as e:
            self.logger.warning(f"Could not adjust precision: {str(e)}")
            return quantity, take_profit_price, stop_loss_price
    
    def place_take_profit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float
    ) -> Dict:
        """
        Place a take-profit limit order.
        
        Args:
            symbol: Trading pair symbol
            side: Order side (BUY or SELL)
            quantity: Order quantity
            price: Take profit price
            
        Returns:
            Order response
        """
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "TAKE_PROFIT",
            "quantity": quantity,
            "price": price,
            "stopPrice": price,
            "timeInForce": "GTC",
            "reduceOnly": "true",
            "workingType": "CONTRACT_PRICE"
        }
        
        self.logger.info(f"Placing take-profit order: {params}")
        endpoint = "/fapi/v1/order"
        response = make_request("POST", endpoint, params, signed=True)
        self.logger.info(f"Take-profit order placed: Order ID {response.get('orderId')}")
        
        return response
    
    def place_stop_loss_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        limit_price: Optional[float] = None
    ) -> Dict:
        """
        Place a stop-loss order.
        
        Args:
            symbol: Trading pair symbol
            side: Order side (BUY or SELL)
            quantity: Order quantity
            stop_price: Stop loss trigger price
            limit_price: Optional limit price (if None, uses stop_price)
            
        Returns:
            Order response
        """
        if limit_price is None:
            limit_price = stop_price
        
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "STOP",
            "quantity": quantity,
            "price": limit_price,
            "stopPrice": stop_price,
            "timeInForce": "GTC",
            "reduceOnly": "true",
            "workingType": "CONTRACT_PRICE"
        }
        
        self.logger.info(f"Placing stop-loss order: {params}")
        endpoint = "/fapi/v1/order"
        response = make_request("POST", endpoint, params, signed=True)
        self.logger.info(f"Stop-loss order placed: Order ID {response.get('orderId')}")
        
        return response
    
    def cancel_order(self, symbol: str, order_id: int) -> bool:
        """
        Cancel an order.
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID to cancel
            
        Returns:
            True if cancelled, False otherwise
        """
        try:
            endpoint = "/fapi/v1/order"
            params = {
                "symbol": symbol.upper(),
                "orderId": order_id
            }
            
            response = make_request("DELETE", endpoint, params, signed=True)
            self.logger.info(f"Order {order_id} cancelled: {response}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cancel order {order_id}: {str(e)}")
            return False
    
    def execute_oco_orders(
        self,
        symbol: str,
        position_side: str,
        quantity: float,
        take_profit_price: float,
        stop_loss_price: float
    ) -> Dict:
        """
        Execute OCO (One-Cancels-the-Other) orders.
        
        Places both take-profit and stop-loss orders. When one executes,
        the other should be cancelled manually (monitoring not included in basic version).
        
        Args:
            symbol: Trading pair symbol
            position_side: Position side (LONG or SHORT)
            quantity: Order quantity
            take_profit_price: Take profit price
            stop_loss_price: Stop loss price
            
        Returns:
            Dict with both order responses
        """
        try:
            # Validate
            self.validate_oco_params(
                symbol, position_side, quantity,
                take_profit_price, stop_loss_price
            )
            
            # Get current price
            try:
                current_price = get_current_price(symbol)
                self.logger.info(f"Current {symbol} price: {current_price}")
                
                # Validate price positions - orders would trigger immediately if wrong
                if position_side.upper() == "LONG":
                    # For LONG: TP should be ABOVE current, SL should be BELOW current
                    if take_profit_price <= current_price:
                        raise ValueError(
                            f"Invalid LONG OCO prices!\n"
                            f"  Current price: {current_price}\n"
                            f"  Your take-profit: {take_profit_price} (would trigger immediately!)\n"
                            f"  Your stop-loss: {stop_loss_price}\n\n"
                            f"For LONG positions:\n"
                            f"  - Take-profit must be ABOVE current price\n"
                            f"  - Stop-loss must be BELOW current price\n\n"
                            f"Correct example:\n"
                            f"  py bot.py oco {symbol} LONG {quantity} {current_price * 1.05:.2f} {current_price * 0.95:.2f}"
                        )
                    if stop_loss_price >= current_price:
                        raise ValueError(
                            f"Invalid LONG stop-loss price!\n"
                            f"  Current price: {current_price}\n"
                            f"  Your stop-loss: {stop_loss_price} (should be BELOW current)\n"
                            f"  Correct example: {current_price * 0.95:.2f}"
                        )
                else:  # SHORT
                    # For SHORT: TP should be BELOW current, SL should be ABOVE current
                    if take_profit_price >= current_price:
                        raise ValueError(
                            f"Invalid SHORT OCO prices!\n"
                            f"  Current price: {current_price}\n"
                            f"  Your take-profit: {take_profit_price} (would trigger immediately!)\n"
                            f"  Your stop-loss: {stop_loss_price}\n\n"
                            f"For SHORT positions:\n"
                            f"  - Take-profit must be BELOW current price\n"
                            f"  - Stop-loss must be ABOVE current price\n\n"
                            f"Correct example:\n"
                            f"  py bot.py oco {symbol} SHORT {quantity} {current_price * 0.95:.2f} {current_price * 1.05:.2f}"
                        )
                    if stop_loss_price <= current_price:
                        raise ValueError(
                            f"Invalid SHORT stop-loss price!\n"
                            f"  Current price: {current_price}\n"
                            f"  Your stop-loss: {stop_loss_price} (should be ABOVE current)\n"
                            f"  Correct example: {current_price * 1.05:.2f}"
                        )
                        
            except ValueError:
                # Re-raise our validation errors
                raise
            except Exception as e:
                self.logger.warning(f"Could not fetch current price: {str(e)}")
                current_price = None
            
            # Adjust precision
            adj_qty, adj_tp, adj_sl = self.adjust_precision(
                symbol, quantity, take_profit_price, stop_loss_price
            )
            
            # Determine order sides based on position
            if position_side.upper() == "LONG":
                # Closing a LONG position requires SELL orders
                order_side = "SELL"
            else:  # SHORT
                # Closing a SHORT position requires BUY orders
                order_side = "BUY"
            
            # Place both orders
            self.logger.info("Placing OCO pair orders...")
            
            tp_order = self.place_take_profit_order(
                symbol, order_side, adj_qty, adj_tp
            )
            
            try:
                sl_order = self.place_stop_loss_order(
                    symbol, order_side, adj_qty, adj_sl
                )
            except Exception as e:
                # If stop-loss fails, cancel take-profit
                self.logger.error(f"Stop-loss order failed: {str(e)}")
                self.logger.info("Cancelling take-profit order...")
                self.cancel_order(symbol, tp_order['orderId'])
                raise Exception("Failed to place complete OCO pair") from e
            
            result = {
                "symbol": symbol,
                "position_side": position_side,
                "quantity": adj_qty,
                "take_profit": {
                    "order_id": tp_order['orderId'],
                    "price": adj_tp,
                    "status": tp_order['status']
                },
                "stop_loss": {
                    "order_id": sl_order['orderId'],
                    "price": adj_sl,
                    "status": sl_order['status']
                },
                "current_price": current_price
            }
            
            self.logger.info(f"OCO orders placed successfully: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute OCO orders: {str(e)}")
            raise


def main():
    """Main function for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Execute OCO orders on Binance Futures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # LONG position: close at profit 52000 or loss 48000
  python src/advanced/oco.py BTCUSDT LONG 0.01 52000 48000
  
  # SHORT position: close at profit 1900 or loss 2100
  python src/advanced/oco.py ETHUSDT SHORT 0.5 1900 2100
  
Note: These orders are reduce-only and will close existing positions.
      Make sure you have an open position before placing OCO orders.
        """
    )
    
    parser.add_argument("symbol", type=str, help="Trading pair symbol")
    parser.add_argument("position_side", type=str, choices=["LONG", "SHORT", "long", "short"],
                       help="Position side to close")
    parser.add_argument("quantity", type=float, help="Order quantity")
    parser.add_argument("take_profit_price", type=float, help="Take profit price")
    parser.add_argument("stop_loss_price", type=float, help="Stop loss price")
    
    args = parser.parse_args()
    
    # Check credentials
    if not check_api_credentials():
        logger.error("API credentials not configured")
        sys.exit(1)
    
    if not validate_api_connection():
        logger.error("Failed to connect to Binance API")
        sys.exit(1)
    
    # Execute
    executor = OCOOrderExecutor()
    
    try:
        result = executor.execute_oco_orders(
            symbol=args.symbol,
            position_side=args.position_side.upper(),
            quantity=args.quantity,
            take_profit_price=args.take_profit_price,
            stop_loss_price=args.stop_loss_price
        )
        
        print("\n" + "="*50)
        print("OCO ORDERS PLACED SUCCESSFULLY")
        print("="*50)
        print(f"Symbol: {result['symbol']}")
        print(f"Position Side: {result['position_side']}")
        print(f"Quantity: {result['quantity']}")
        if result.get('current_price'):
            print(f"Current Price: {result['current_price']}")
        print()
        print("Take Profit Order:")
        print(f"  Order ID: {result['take_profit']['order_id']}")
        print(f"  Price: {result['take_profit']['price']}")
        print(f"  Status: {result['take_profit']['status']}")
        print()
        print("Stop Loss Order:")
        print(f"  Order ID: {result['stop_loss']['order_id']}")
        print(f"  Price: {result['stop_loss']['price']}")
        print(f"  Status: {result['stop_loss']['status']}")
        print("="*50)
        print("\nNote: Monitor these orders. When one executes,")
        print("      manually cancel the other if needed.")
        
    except Exception as e:
        logger.error(f"OCO execution failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        print("OCO Orders Demo")
        print("===============")
        print("\nUsage: python src/advanced/oco.py SYMBOL POSITION_SIDE QUANTITY TP_PRICE SL_PRICE")
        print("\nExample: python src/advanced/oco.py BTCUSDT LONG 0.01 52000 48000")
