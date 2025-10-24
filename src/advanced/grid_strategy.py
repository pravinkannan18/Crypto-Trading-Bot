"""
grid_strategy.py

Grid Trading Strategy for Binance Futures.

Automates buy-low/sell-high within a price range by placing multiple
limit orders at different price levels (grid).

Usage:
    python src/advanced/grid_strategy.py BTCUSDT 48000 52000 10 0.01
    python src/advanced/grid_strategy.py ETHUSDT 1800 2200 20 0.1 --dry-run
"""

import sys
import os
import argparse
import time
from typing import List, Dict, Tuple
from datetime import datetime

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


class GridTradingStrategy:
    """
    Implement Grid Trading Strategy on Binance Futures.
    
    Places multiple buy and sell limit orders at different price levels
    within a specified range to profit from price oscillations.
    """
    
    def __init__(self):
        """Initialize the grid trading strategy."""
        self.logger = logger
        self.active_orders = []
        
    def validate_grid_params(
        self,
        symbol: str,
        lower_price: float,
        upper_price: float,
        num_grids: int,
        quantity_per_grid: float
    ) -> bool:
        """
        Validate grid strategy parameters.
        
        Args:
            symbol: Trading pair symbol
            lower_price: Lower bound of price range
            upper_price: Upper bound of price range
            num_grids: Number of grid levels
            quantity_per_grid: Quantity for each grid order
            
        Returns:
            True if valid, raises exception otherwise
        """
        self.logger.info(
            f"Validating grid: {symbol} range [{lower_price}, {upper_price}] "
            f"with {num_grids} grids, {quantity_per_grid} each"
        )
        
        if not validate_symbol(symbol):
            raise ValueError(f"Invalid symbol: {symbol}")
        
        if not validate_price(lower_price):
            raise ValueError(f"Invalid lower price: {lower_price}")
        
        if not validate_price(upper_price):
            raise ValueError(f"Invalid upper price: {upper_price}")
        
        if lower_price >= upper_price:
            raise ValueError(
                f"Lower price ({lower_price}) must be less than "
                f"upper price ({upper_price})"
            )
        
        if num_grids < 2:
            raise ValueError(f"Number of grids must be at least 2: {num_grids}")
        
        if num_grids > 50:
            raise ValueError(f"Number of grids too large: {num_grids}. Max is 50")
        
        if not validate_quantity(quantity_per_grid):
            raise ValueError(f"Invalid quantity per grid: {quantity_per_grid}")
        
        # Check price range is reasonable
        price_range_pct = ((upper_price - lower_price) / lower_price) * 100
        if price_range_pct < 1:
            self.logger.warning(f"Price range is very small: {price_range_pct:.2f}%")
        
        self.logger.info("Grid validation passed")
        return True
    
    def calculate_grid_levels(
        self,
        lower_price: float,
        upper_price: float,
        num_grids: int
    ) -> List[float]:
        """
        Calculate price levels for the grid.
        
        Args:
            lower_price: Lower bound
            upper_price: Upper bound
            num_grids: Number of grids
            
        Returns:
            List of price levels
        """
        # Calculate grid spacing
        price_range = upper_price - lower_price
        grid_spacing = price_range / (num_grids - 1)
        
        # Generate price levels
        levels = []
        for i in range(num_grids):
            price_level = lower_price + (i * grid_spacing)
            levels.append(price_level)
        
        self.logger.info(f"Grid levels: {levels}")
        return levels
    
    def adjust_precision(
        self,
        symbol: str,
        quantity: float,
        prices: List[float]
    ) -> Tuple[float, List[float]]:
        """
        Adjust quantity and prices to match exchange precision.
        
        Args:
            symbol: Trading pair symbol
            quantity: Order quantity
            prices: List of prices
            
        Returns:
            Tuple of (adjusted_quantity, adjusted_prices)
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
                adjusted_prices = [round_step_size(p, tick_size) for p in prices]
            else:
                adjusted_prices = prices
            
            return adjusted_qty, adjusted_prices
            
        except Exception as e:
            self.logger.warning(f"Could not adjust precision: {str(e)}")
            return quantity, prices
    
    def place_grid_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        grid_num: int
    ) -> Dict:
        """
        Place a single grid order.
        
        Args:
            symbol: Trading pair symbol
            side: Order side (BUY or SELL)
            quantity: Order quantity
            price: Order price
            grid_num: Grid number for tracking
            
        Returns:
            Order response
        """
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "LIMIT",
            "quantity": quantity,
            "price": price,
            "timeInForce": "GTC",
        }
        
        self.logger.info(f"Placing grid order #{grid_num}: {params}")
        
        endpoint = "/fapi/v1/order"
        response = make_request("POST", endpoint, params, signed=True)
        
        self.logger.info(f"Grid order #{grid_num} placed: Order ID {response.get('orderId')}")
        return response
    
    def cancel_all_orders(self, symbol: str) -> int:
        """
        Cancel all open orders for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Number of orders cancelled
        """
        try:
            endpoint = "/fapi/v1/allOpenOrders"
            params = {"symbol": symbol.upper()}
            
            self.logger.info(f"Cancelling all orders for {symbol}")
            response = make_request("DELETE", endpoint, params, signed=True)
            
            count = response.get('code', 0)
            if isinstance(response, list):
                count = len(response)
            
            self.logger.info(f"Cancelled {count} orders")
            return count
            
        except Exception as e:
            self.logger.error(f"Failed to cancel orders: {str(e)}")
            return 0
    
    def setup_grid(
        self,
        symbol: str,
        lower_price: float,
        upper_price: float,
        num_grids: int,
        quantity_per_grid: float,
        dry_run: bool = False
    ) -> Dict:
        """
        Setup grid trading strategy.
        
        Args:
            symbol: Trading pair symbol
            lower_price: Lower bound of price range
            upper_price: Upper bound of price range
            num_grids: Number of grid levels
            quantity_per_grid: Quantity for each grid order
            dry_run: If True, simulate without placing real orders
            
        Returns:
            Dict with grid setup summary
        """
        try:
            # Validate
            self.validate_grid_params(
                symbol, lower_price, upper_price, num_grids, quantity_per_grid
            )
            
            # Get current price
            try:
                current_price = get_current_price(symbol)
                self.logger.info(f"Current {symbol} price: {current_price}")
                
                if current_price < lower_price or current_price > upper_price:
                    self.logger.warning(
                        f"Current price {current_price} is outside grid range "
                        f"[{lower_price}, {upper_price}]"
                    )
            except Exception as e:
                self.logger.warning(f"Could not fetch current price: {str(e)}")
                current_price = None
            
            # Calculate grid levels
            grid_levels = self.calculate_grid_levels(lower_price, upper_price, num_grids)
            
            # Adjust precision
            adj_qty, adj_prices = self.adjust_precision(symbol, quantity_per_grid, grid_levels)
            
            # Setup summary
            summary = {
                "symbol": symbol,
                "lower_price": lower_price,
                "upper_price": upper_price,
                "num_grids": num_grids,
                "quantity_per_grid": adj_qty,
                "current_price": current_price,
                "grid_levels": adj_prices,
                "buy_orders": [],
                "sell_orders": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # Place grid orders
            self.logger.info("Setting up grid orders...")
            
            for i, price_level in enumerate(adj_prices, 1):
                try:
                    # Determine order side based on current price
                    if current_price is None:
                        # If we don't have current price, place both buy and sell at each level
                        # This is more conservative
                        side = "BUY" if i <= num_grids // 2 else "SELL"
                    elif price_level < current_price:
                        # Buy orders below current price
                        side = "BUY"
                    elif price_level > current_price:
                        # Sell orders above current price
                        side = "SELL"
                    else:
                        # Skip if price level equals current price
                        self.logger.info(f"Skipping grid level {i} at current price")
                        continue
                    
                    if dry_run:
                        self.logger.info(
                            f"[DRY RUN] Would place {side} order at {price_level} "
                            f"for {adj_qty} {symbol}"
                        )
                        order_result = {
                            "orderId": f"dry_run_{i}",
                            "symbol": symbol,
                            "side": side,
                            "price": price_level,
                            "origQty": adj_qty,
                            "status": "NEW"
                        }
                    else:
                        # Place real order
                        order_result = self.place_grid_order(
                            symbol, side, adj_qty, price_level, i
                        )
                    
                    # Track order
                    order_info = {
                        "grid_num": i,
                        "order_id": order_result.get('orderId'),
                        "side": side,
                        "price": price_level,
                        "quantity": adj_qty,
                        "status": order_result.get('status', 'NEW')
                    }
                    
                    if side == "BUY":
                        summary["buy_orders"].append(order_info)
                    else:
                        summary["sell_orders"].append(order_info)
                    
                    self.active_orders.append(order_result)
                    
                except Exception as e:
                    self.logger.error(f"Failed to place grid order {i}: {str(e)}")
                    summary.get("buy_orders" if side == "BUY" else "sell_orders").append({
                        "grid_num": i,
                        "error": str(e)
                    })
            
            self.logger.info(f"Grid setup completed: {len(self.active_orders)} orders placed")
            return summary
            
        except Exception as e:
            self.logger.error(f"Grid setup failed: {str(e)}")
            raise


def main():
    """Main function for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Setup Grid Trading Strategy on Binance Futures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Setup 10-level grid for BTCUSDT between 48000-52000
  python src/advanced/grid_strategy.py BTCUSDT 48000 52000 10 0.01
  
  # Setup 20-level grid for ETHUSDT with larger range
  python src/advanced/grid_strategy.py ETHUSDT 1800 2200 20 0.1
  
  # Dry run (simulate without placing orders)
  python src/advanced/grid_strategy.py BTCUSDT 48000 52000 5 0.01 --dry-run
  
  # Cancel all open orders for a symbol
  python src/advanced/grid_strategy.py BTCUSDT --cancel-all
        """
    )
    
    parser.add_argument("symbol", type=str, help="Trading pair symbol")
    parser.add_argument("lower_price", type=float, nargs='?',
                       help="Lower bound of price range")
    parser.add_argument("upper_price", type=float, nargs='?',
                       help="Upper bound of price range")
    parser.add_argument("num_grids", type=int, nargs='?',
                       help="Number of grid levels")
    parser.add_argument("quantity_per_grid", type=float, nargs='?',
                       help="Quantity for each grid order")
    parser.add_argument("--dry-run", action="store_true",
                       help="Simulate without placing real orders")
    parser.add_argument("--cancel-all", action="store_true",
                       help="Cancel all open orders for symbol")
    
    args = parser.parse_args()
    
    # Handle cancel-all
    if args.cancel_all:
        if not check_api_credentials():
            logger.error("API credentials not configured")
            sys.exit(1)
        
        if not validate_api_connection():
            logger.error("Failed to connect to Binance API")
            sys.exit(1)
        
        strategy = GridTradingStrategy()
        count = strategy.cancel_all_orders(args.symbol)
        print(f"\nCancelled {count} orders for {args.symbol}")
        sys.exit(0)
    
    # Validate required arguments for grid setup
    if not all([args.lower_price, args.upper_price, args.num_grids, args.quantity_per_grid]):
        parser.error("lower_price, upper_price, num_grids, and quantity_per_grid are required")
    
    # Check credentials (skip for dry run)
    if not args.dry_run:
        if not check_api_credentials():
            logger.error("API credentials not configured")
            sys.exit(1)
        
        if not validate_api_connection():
            logger.error("Failed to connect to Binance API")
            sys.exit(1)
    
    # Setup grid
    strategy = GridTradingStrategy()
    
    try:
        print("\n" + "="*50)
        print("GRID TRADING STRATEGY SETUP")
        print("="*50)
        print(f"Symbol: {args.symbol}")
        print(f"Price Range: {args.lower_price} - {args.upper_price}")
        print(f"Number of Grids: {args.num_grids}")
        print(f"Quantity per Grid: {args.quantity_per_grid}")
        if args.dry_run:
            print("MODE: DRY RUN (no real orders)")
        print("="*50 + "\n")
        
        result = strategy.setup_grid(
            symbol=args.symbol,
            lower_price=args.lower_price,
            upper_price=args.upper_price,
            num_grids=args.num_grids,
            quantity_per_grid=args.quantity_per_grid,
            dry_run=args.dry_run
        )
        
        print("\n" + "="*50)
        print("GRID SETUP COMPLETED")
        print("="*50)
        print(f"Symbol: {result['symbol']}")
        if result.get('current_price'):
            print(f"Current Price: {result['current_price']}")
        print(f"Buy Orders: {len(result['buy_orders'])}")
        print(f"Sell Orders: {len(result['sell_orders'])}")
        print(f"Total Orders: {len(result['buy_orders']) + len(result['sell_orders'])}")
        print("="*50)
        
        # Show order details
        if result['buy_orders']:
            print("\nBuy Orders (below current price):")
            for order in result['buy_orders']:
                if 'error' in order:
                    print(f"  Grid {order['grid_num']}: ERROR - {order['error']}")
                else:
                    print(f"  Grid {order['grid_num']}: {order['quantity']} @ {order['price']}")
        
        if result['sell_orders']:
            print("\nSell Orders (above current price):")
            for order in result['sell_orders']:
                if 'error' in order:
                    print(f"  Grid {order['grid_num']}: ERROR - {order['error']}")
                else:
                    print(f"  Grid {order['grid_num']}: {order['quantity']} @ {order['price']}")
        
        print("\n" + "="*50)
        print("Grid is now active!")
        print("Monitor orders and adjust as needed.")
        print(f"To cancel all orders: python src/advanced/grid_strategy.py {args.symbol} --cancel-all")
        print("="*50)
        
    except Exception as e:
        logger.error(f"Grid setup failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        print("Grid Trading Strategy Demo")
        print("===========================")
        print("\nUsage: python src/advanced/grid_strategy.py SYMBOL LOWER UPPER NUM_GRIDS QTY_PER_GRID")
        print("\nExample: python src/advanced/grid_strategy.py BTCUSDT 48000 52000 10 0.01")
