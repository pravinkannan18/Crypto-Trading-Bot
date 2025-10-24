"""
Binance Futures Trading Bot - Main Entry Point

A comprehensive CLI-based trading bot for Binance USDT-M Futures.

Usage:
    python bot.py --help
    python bot.py market BTCUSDT BUY 0.01
    python bot.py limit ETHUSDT SELL 0.5 2000
    python bot.py stop-limit BTCUSDT BUY 0.01 49000 49500
    python bot.py oco BTCUSDT LONG 0.01 52000 48000
    python bot.py twap BTCUSDT BUY 0.1 5 60
    python bot.py grid BTCUSDT 48000 52000 10 0.01
"""

import sys
import argparse
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from config import setup_logger, check_api_credentials, validate_api_connection

logger = setup_logger(__name__)


def main():
    """Main entry point for the trading bot."""
    
    parser = argparse.ArgumentParser(
        description="Binance Futures Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Order Types:
  market      Market orders (instant execution)
  limit       Limit orders (execute at specific price)
  stop-limit  Stop-limit orders (trigger limit order at stop price)
  oco         OCO orders (one-cancels-the-other)
  twap        TWAP strategy (time-weighted average price)
  grid        Grid trading strategy (automated buy-low/sell-high)

Examples:
  python bot.py market BTCUSDT BUY 0.01
  python bot.py limit ETHUSDT SELL 0.5 2000
  python bot.py stop-limit BTCUSDT BUY 0.01 49000 49500
  python bot.py oco BTCUSDT LONG 0.01 52000 48000
  python bot.py twap BTCUSDT BUY 0.1 5 60
  python bot.py grid BTCUSDT 48000 52000 10 0.01

For detailed help on each order type:
  python bot.py market --help
  python bot.py limit --help
  python bot.py stop-limit --help
  python bot.py oco --help
  python bot.py twap --help
  python bot.py grid --help
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Order type')
    
    # Market orders
    market_parser = subparsers.add_parser('market', help='Execute market orders')
    market_parser.add_argument('symbol', type=str, help='Trading pair symbol')
    market_parser.add_argument('side', type=str, choices=['BUY', 'SELL'],
                               help='Order side')
    market_parser.add_argument('quantity', type=float, help='Order quantity')
    market_parser.add_argument('--reduce-only', action='store_true',
                               help='Order will only reduce position')
    
    # Limit orders
    limit_parser = subparsers.add_parser('limit', help='Execute limit orders')
    limit_parser.add_argument('symbol', type=str, help='Trading pair symbol')
    limit_parser.add_argument('side', type=str, choices=['BUY', 'SELL'],
                              help='Order side')
    limit_parser.add_argument('quantity', type=float, help='Order quantity')
    limit_parser.add_argument('price', type=float, help='Limit price')
    limit_parser.add_argument('--time-in-force', type=str, default='GTC',
                              choices=['GTC', 'IOC', 'FOK', 'GTX'],
                              help='Time in force')
    limit_parser.add_argument('--reduce-only', action='store_true',
                              help='Order will only reduce position')
    limit_parser.add_argument('--post-only', action='store_true',
                              help='Maker-only order')
    
    # Stop-limit orders
    stop_parser = subparsers.add_parser('stop-limit', help='Execute stop-limit orders')
    stop_parser.add_argument('symbol', type=str, help='Trading pair symbol')
    stop_parser.add_argument('side', type=str, choices=['BUY', 'SELL'],
                             help='Order side')
    stop_parser.add_argument('quantity', type=float, help='Order quantity')
    stop_parser.add_argument('stop_price', type=float, help='Stop price')
    stop_parser.add_argument('limit_price', type=float, help='Limit price')
    stop_parser.add_argument('--reduce-only', action='store_true',
                             help='Order will only reduce position')
    
    # OCO orders
    oco_parser = subparsers.add_parser('oco', help='Execute OCO orders')
    oco_parser.add_argument('symbol', type=str, help='Trading pair symbol')
    oco_parser.add_argument('position_side', type=str, choices=['LONG', 'SHORT'],
                            help='Position side to close')
    oco_parser.add_argument('quantity', type=float, help='Order quantity')
    oco_parser.add_argument('take_profit_price', type=float, help='Take profit price')
    oco_parser.add_argument('stop_loss_price', type=float, help='Stop loss price')
    
    # TWAP strategy
    twap_parser = subparsers.add_parser('twap', help='Execute TWAP strategy')
    twap_parser.add_argument('symbol', type=str, help='Trading pair symbol')
    twap_parser.add_argument('side', type=str, choices=['BUY', 'SELL'],
                             help='Order side')
    twap_parser.add_argument('total_quantity', type=float, help='Total quantity')
    twap_parser.add_argument('num_slices', type=int, help='Number of slices')
    twap_parser.add_argument('total_duration', type=int, help='Total duration (seconds)')
    twap_parser.add_argument('--randomize', action='store_true',
                             help='Randomize slice sizes')
    twap_parser.add_argument('--dry-run', action='store_true',
                             help='Simulate without placing orders')
    
    # Grid trading
    grid_parser = subparsers.add_parser('grid', help='Setup grid trading')
    grid_parser.add_argument('symbol', type=str, help='Trading pair symbol')
    grid_parser.add_argument('lower_price', type=float, nargs='?',
                             help='Lower price bound')
    grid_parser.add_argument('upper_price', type=float, nargs='?',
                             help='Upper price bound')
    grid_parser.add_argument('num_grids', type=int, nargs='?',
                             help='Number of grid levels')
    grid_parser.add_argument('quantity_per_grid', type=float, nargs='?',
                             help='Quantity per grid')
    grid_parser.add_argument('--dry-run', action='store_true',
                             help='Simulate without placing orders')
    grid_parser.add_argument('--cancel-all', action='store_true',
                             help='Cancel all orders for symbol')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    # Check API credentials (skip for dry-run)
    skip_check = hasattr(args, 'dry_run') and args.dry_run
    
    if not skip_check:
        if not check_api_credentials():
            logger.error("API credentials not configured")
            print("\nError: API credentials not configured!")
            print("\nPlease set environment variables:")
            print("  $env:BINANCE_TESTNET_API_KEY = 'your_api_key'")
            print("  $env:BINANCE_TESTNET_SECRET_KEY = 'your_secret_key'")
            sys.exit(1)
        
        if not validate_api_connection():
            logger.error("Failed to connect to Binance API")
            print("\nError: Failed to connect to Binance API!")
            print("Please check your internet connection and API credentials.")
            sys.exit(1)
    
    # Execute command
    try:
        if args.command == 'market':
            from market_orders import MarketOrderExecutor
            executor = MarketOrderExecutor()
            result = executor.execute_market_order(
                args.symbol, args.side, args.quantity, args.reduce_only
            )
            print(f"\n✅ Market order executed: Order ID {result['orderId']}")
            
        elif args.command == 'limit':
            from limit_orders import LimitOrderExecutor
            executor = LimitOrderExecutor()
            result = executor.execute_limit_order(
                args.symbol, args.side, args.quantity, args.price,
                args.time_in_force, args.reduce_only, args.post_only
            )
            print(f"\n✅ Limit order placed: Order ID {result['orderId']}")
            
        elif args.command == 'stop-limit':
            sys.path.insert(0, str(src_path / 'advanced'))
            from stop_limit import StopLimitOrderExecutor
            executor = StopLimitOrderExecutor()
            result = executor.execute_stop_limit_order(
                args.symbol, args.side, args.quantity,
                args.stop_price, args.limit_price, args.reduce_only
            )
            print(f"\n✅ Stop-limit order placed: Order ID {result['orderId']}")
            
        elif args.command == 'oco':
            sys.path.insert(0, str(src_path / 'advanced'))
            from oco import OCOOrderExecutor
            executor = OCOOrderExecutor()
            result = executor.execute_oco_orders(
                args.symbol, args.position_side, args.quantity,
                args.take_profit_price, args.stop_loss_price
            )
            print(f"\n✅ OCO orders placed:")
            print(f"   Take-Profit: Order ID {result['take_profit']['order_id']}")
            print(f"   Stop-Loss: Order ID {result['stop_loss']['order_id']}")
            
        elif args.command == 'twap':
            sys.path.insert(0, str(src_path / 'advanced'))
            from twap import TWAPExecutor
            executor = TWAPExecutor()
            interval = args.total_duration // args.num_slices
            result = executor.execute_twap(
                args.symbol, args.side, args.total_quantity,
                args.num_slices, interval, args.randomize, dry_run=args.dry_run
            )
            print(f"\n✅ TWAP execution completed:")
            print(f"   Executed: {result['total_executed']}/{result['total_quantity']}")
            print(f"   Orders: {len(result['orders'])}")
            
        elif args.command == 'grid':
            sys.path.insert(0, str(src_path / 'advanced'))
            from grid_strategy import GridTradingStrategy
            strategy = GridTradingStrategy()
            
            if args.cancel_all:
                count = strategy.cancel_all_orders(args.symbol)
                print(f"\n✅ Cancelled {count} orders for {args.symbol}")
            else:
                if not all([args.lower_price, args.upper_price, args.num_grids, args.quantity_per_grid]):
                    print("Error: All grid parameters required")
                    grid_parser.print_help()
                    sys.exit(1)
                    
                result = strategy.setup_grid(
                    args.symbol, args.lower_price, args.upper_price,
                    args.num_grids, args.quantity_per_grid, args.dry_run
                )
                total_orders = len(result['buy_orders']) + len(result['sell_orders'])
                print(f"\n✅ Grid setup completed: {total_orders} orders placed")
        
        logger.info(f"Command '{args.command}' executed successfully")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Command execution failed: {str(e)}")
        print(f"\n❌ Error: {str(e)}")
        print("\nCheck bot.log for details")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("Binance Futures Trading Bot".center(60))
    print("=" * 60)
    main()
