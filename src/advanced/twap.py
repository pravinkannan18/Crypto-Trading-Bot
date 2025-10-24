"""
twap.py

TWAP (Time-Weighted Average Price) Strategy for Binance Futures.

Splits large orders into smaller chunks executed over time to minimize
market impact and achieve better average execution price.

Usage:
    python src/advanced/twap.py BTCUSDT BUY 0.1 5 60
    python src/advanced/twap.py ETHUSDT SELL 2.0 10 120 --randomize
"""

import sys
import os
import argparse
import time
import random
from typing import List, Dict
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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


class TWAPExecutor:
    """
    Handle TWAP (Time-Weighted Average Price) order execution.
    
    Splits a large order into smaller slices and executes them at regular
    intervals to minimize market impact.
    """
    
    def __init__(self):
        """Initialize the TWAP executor."""
        self.logger = logger
        self.executed_orders = []
        
    def validate_twap_params(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        num_slices: int,
        interval_seconds: int
    ) -> bool:
        """
        Validate TWAP parameters.
        
        Args:
            symbol: Trading pair symbol
            side: Order side (BUY or SELL)
            total_quantity: Total quantity to execute
            num_slices: Number of slices to split into
            interval_seconds: Time interval between slices
            
        Returns:
            True if valid, raises exception otherwise
        """
        self.logger.info(
            f"Validating TWAP: {symbol} {side} {total_quantity} "
            f"in {num_slices} slices every {interval_seconds}s"
        )
        
        if not validate_symbol(symbol):
            raise ValueError(f"Invalid symbol: {symbol}")
        
        if not validate_side(side):
            raise ValueError(f"Invalid side: {side}")
        
        if not validate_quantity(total_quantity):
            raise ValueError(f"Invalid total quantity: {total_quantity}")
        
        if num_slices <= 0:
            raise ValueError(f"Number of slices must be positive: {num_slices}")
        
        if num_slices > 100:
            raise ValueError(f"Number of slices too large: {num_slices}. Max is 100")
        
        if interval_seconds < 1:
            raise ValueError(f"Interval must be at least 1 second: {interval_seconds}")
        
        # Check if slice size is meaningful
        slice_quantity = total_quantity / num_slices
        if slice_quantity <= 0:
            raise ValueError("Slice quantity too small")
        
        self.logger.info("TWAP validation passed")
        return True
    
    def calculate_slices(
        self,
        total_quantity: float,
        num_slices: int,
        randomize: bool = False,
        randomize_pct: float = 10.0
    ) -> List[float]:
        """
        Calculate quantity for each slice.
        
        Args:
            total_quantity: Total quantity to split
            num_slices: Number of slices
            randomize: Whether to randomize slice sizes
            randomize_pct: Max randomization percentage (default 10%)
            
        Returns:
            List of quantities for each slice
        """
        if not randomize:
            # Equal slices
            slice_qty = total_quantity / num_slices
            slices = [slice_qty] * num_slices
        else:
            # Randomized slices
            slices = []
            remaining = total_quantity
            
            for i in range(num_slices - 1):
                # Target slice with random variation
                target = total_quantity / num_slices
                variation = target * (randomize_pct / 100)
                
                # Random quantity within bounds
                min_qty = max(target - variation, 0.001)
                max_qty = min(target + variation, remaining - (num_slices - i - 1) * 0.001)
                
                if max_qty < min_qty:
                    max_qty = min_qty
                
                slice_qty = random.uniform(min_qty, max_qty)
                slices.append(slice_qty)
                remaining -= slice_qty
            
            # Last slice gets remaining quantity
            slices.append(remaining)
        
        self.logger.info(f"Calculated {len(slices)} slices: {slices}")
        return slices
    
    def adjust_slice_precision(self, symbol: str, quantity: float) -> float:
        """Adjust slice quantity to match exchange precision."""
        try:
            filters = get_symbol_filters(symbol)
            lot_size = filters["filters"].get("LOT_SIZE", {})
            
            if lot_size:
                step_size = float(lot_size.get("stepSize", "0.001"))
                min_qty = float(lot_size.get("minQty", "0"))
                
                adjusted = round_step_size(quantity, step_size)
                
                if adjusted < min_qty:
                    self.logger.warning(
                        f"Slice quantity {adjusted} below minimum {min_qty}. "
                        "Consider reducing number of slices."
                    )
                    adjusted = min_qty
                
                return adjusted
            else:
                return quantity
                
        except Exception as e:
            self.logger.warning(f"Could not adjust precision: {str(e)}")
            return quantity
    
    def execute_slice(
        self,
        symbol: str,
        side: str,
        quantity: float,
        slice_num: int,
        total_slices: int
    ) -> Dict:
        """
        Execute a single TWAP slice.
        
        Args:
            symbol: Trading pair symbol
            side: Order side
            quantity: Slice quantity
            slice_num: Current slice number (1-indexed)
            total_slices: Total number of slices
            
        Returns:
            Order response
        """
        self.logger.info(
            f"Executing TWAP slice {slice_num}/{total_slices}: "
            f"{symbol} {side} {quantity}"
        )
        
        # Adjust precision
        adjusted_qty = self.adjust_slice_precision(symbol, quantity)
        
        # Build and execute market order
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "MARKET",
            "quantity": adjusted_qty,
        }
        
        endpoint = "/fapi/v1/order"
        response = make_request("POST", endpoint, params, signed=True)
        
        self.logger.info(
            f"Slice {slice_num} executed: Order ID {response.get('orderId')}, "
            f"Filled: {response.get('executedQty')}"
        )
        
        return response
    
    def execute_twap(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        num_slices: int,
        interval_seconds: int,
        randomize: bool = False,
        randomize_pct: float = 10.0,
        dry_run: bool = False
    ) -> Dict:
        """
        Execute TWAP strategy.
        
        Args:
            symbol: Trading pair symbol
            side: Order side (BUY or SELL)
            total_quantity: Total quantity to execute
            num_slices: Number of slices
            interval_seconds: Time interval between slices in seconds
            randomize: Whether to randomize slice sizes
            randomize_pct: Max randomization percentage
            dry_run: If True, simulate without placing real orders
            
        Returns:
            Dict with execution summary
        """
        try:
            # Validate
            self.validate_twap_params(
                symbol, side, total_quantity, num_slices, interval_seconds
            )
            
            # Get initial price
            try:
                start_price = get_current_price(symbol)
                self.logger.info(f"Starting price: {start_price}")
            except:
                start_price = None
            
            # Calculate slices
            slices = self.calculate_slices(
                total_quantity, num_slices, randomize, randomize_pct
            )
            
            # Execution summary
            summary = {
                "symbol": symbol,
                "side": side,
                "total_quantity": total_quantity,
                "num_slices": num_slices,
                "interval_seconds": interval_seconds,
                "start_time": datetime.now().isoformat(),
                "start_price": start_price,
                "orders": [],
                "total_executed": 0.0,
                "average_price": 0.0
            }
            
            # Execute slices
            total_executed_qty = 0.0
            total_cost = 0.0
            
            for i, slice_qty in enumerate(slices, 1):
                try:
                    if dry_run:
                        self.logger.info(
                            f"[DRY RUN] Would execute slice {i}/{num_slices}: "
                            f"{slice_qty} {symbol}"
                        )
                        order_result = {
                            "orderId": f"dry_run_{i}",
                            "executedQty": slice_qty,
                            "avgPrice": start_price if start_price else 0
                        }
                    else:
                        # Execute real order
                        order_result = self.execute_slice(
                            symbol, side, slice_qty, i, num_slices
                        )
                    
                    # Track execution
                    executed_qty = float(order_result.get('executedQty', slice_qty))
                    avg_price = float(order_result.get('avgPrice', 0))
                    
                    total_executed_qty += executed_qty
                    total_cost += executed_qty * avg_price
                    
                    summary["orders"].append({
                        "slice_num": i,
                        "order_id": order_result.get('orderId'),
                        "quantity": slice_qty,
                        "executed_qty": executed_qty,
                        "price": avg_price,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    self.logger.info(
                        f"Slice {i} completed. "
                        f"Total executed: {total_executed_qty}/{total_quantity}"
                    )
                    
                    # Wait before next slice (except last one)
                    if i < num_slices:
                        self.logger.info(f"Waiting {interval_seconds} seconds...")
                        time.sleep(interval_seconds)
                    
                except Exception as e:
                    self.logger.error(f"Failed to execute slice {i}: {str(e)}")
                    summary["orders"].append({
                        "slice_num": i,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
            
            # Calculate summary stats
            summary["total_executed"] = total_executed_qty
            if total_executed_qty > 0:
                summary["average_price"] = total_cost / total_executed_qty
            
            summary["end_time"] = datetime.now().isoformat()
            
            # Get final price
            try:
                end_price = get_current_price(symbol)
                summary["end_price"] = end_price
                if start_price:
                    price_change = ((end_price - start_price) / start_price) * 100
                    summary["price_change_pct"] = price_change
            except:
                pass
            
            self.logger.info(f"TWAP execution completed: {summary}")
            return summary
            
        except Exception as e:
            self.logger.error(f"TWAP execution failed: {str(e)}")
            raise


def main():
    """Main function for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Execute TWAP strategy on Binance Futures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Buy 0.1 BTC split into 5 slices over 60 seconds (12s intervals)
  python src/advanced/twap.py BTCUSDT BUY 0.1 5 60
  
  # Sell 2 ETH split into 10 slices over 120 seconds with randomization
  python src/advanced/twap.py ETHUSDT SELL 2.0 10 120 --randomize
  
  # Dry run (simulate without placing orders)
  python src/advanced/twap.py BTCUSDT BUY 0.05 3 30 --dry-run
        """
    )
    
    parser.add_argument("symbol", type=str, help="Trading pair symbol")
    parser.add_argument("side", type=str, choices=["BUY", "SELL", "buy", "sell"],
                       help="Order side")
    parser.add_argument("total_quantity", type=float, help="Total quantity to execute")
    parser.add_argument("num_slices", type=int, help="Number of slices")
    parser.add_argument("total_duration", type=int,
                       help="Total duration in seconds")
    parser.add_argument("--randomize", action="store_true",
                       help="Randomize slice sizes (default: equal slices)")
    parser.add_argument("--randomize-pct", type=float, default=10.0,
                       help="Max randomization percentage (default: 10)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Simulate without placing real orders")
    
    args = parser.parse_args()
    
    # Calculate interval
    interval_seconds = args.total_duration // args.num_slices
    if interval_seconds < 1:
        logger.error("Duration too short for number of slices. Minimum 1 second per slice.")
        sys.exit(1)
    
    # Check credentials (skip for dry run)
    if not args.dry_run:
        if not check_api_credentials():
            logger.error("API credentials not configured")
            sys.exit(1)
        
        if not validate_api_connection():
            logger.error("Failed to connect to Binance API")
            sys.exit(1)
    
    # Execute TWAP
    executor = TWAPExecutor()
    
    try:
        print("\n" + "="*50)
        print("TWAP EXECUTION STARTING")
        print("="*50)
        print(f"Symbol: {args.symbol}")
        print(f"Side: {args.side.upper()}")
        print(f"Total Quantity: {args.total_quantity}")
        print(f"Number of Slices: {args.num_slices}")
        print(f"Interval: {interval_seconds} seconds")
        print(f"Total Duration: ~{args.total_duration} seconds")
        if args.randomize:
            print(f"Randomization: ±{args.randomize_pct}%")
        if args.dry_run:
            print("MODE: DRY RUN (no real orders)")
        print("="*50 + "\n")
        
        result = executor.execute_twap(
            symbol=args.symbol,
            side=args.side.upper(),
            total_quantity=args.total_quantity,
            num_slices=args.num_slices,
            interval_seconds=interval_seconds,
            randomize=args.randomize,
            randomize_pct=args.randomize_pct,
            dry_run=args.dry_run
        )
        
        print("\n" + "="*50)
        print("TWAP EXECUTION COMPLETED")
        print("="*50)
        print(f"Total Executed: {result['total_executed']}/{result['total_quantity']}")
        print(f"Average Price: {result.get('average_price', 'N/A')}")
        if result.get('start_price') and result.get('end_price'):
            print(f"Price Change: {result.get('start_price')} → {result.get('end_price')} "
                  f"({result.get('price_change_pct', 0):.2f}%)")
        print(f"Orders Placed: {len(result['orders'])}")
        print("="*50)
        
        # Show order details
        print("\nOrder Details:")
        for order in result['orders']:
            if 'error' in order:
                print(f"  Slice {order['slice_num']}: ERROR - {order['error']}")
            else:
                print(f"  Slice {order['slice_num']}: {order['executed_qty']} @ {order.get('price', 'N/A')}")
        
    except KeyboardInterrupt:
        logger.warning("TWAP execution interrupted by user")
        print("\n\nTWAP execution interrupted!")
        sys.exit(1)
    except Exception as e:
        logger.error(f"TWAP execution failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        print("TWAP Strategy Demo")
        print("==================")
        print("\nUsage: python src/advanced/twap.py SYMBOL SIDE TOTAL_QTY NUM_SLICES DURATION")
        print("\nExample: python src/advanced/twap.py BTCUSDT BUY 0.1 5 60")
