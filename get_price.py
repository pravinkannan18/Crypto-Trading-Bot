"""
Get Current Price - Helper Script

Quickly check current prices for any trading pair.

Usage:
    py get_price.py BTCUSDT
    py get_price.py ETHUSDT
    py get_price.py BNBUSDT
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import get_current_price, setup_logger

logger = setup_logger(__name__)


def main():
    if len(sys.argv) < 2:
        print("\n" + "="*60)
        print("Get Current Price - Helper Script".center(60))
        print("="*60)
        print("\nUsage:")
        print("  py get_price.py BTCUSDT")
        print("  py get_price.py ETHUSDT")
        print("  py get_price.py BNBUSDT")
        print("\nThis helps you find the right price for limit orders!")
        print("="*60 + "\n")
        sys.exit(0)
    
    symbol = sys.argv[1].upper()
    
    try:
        print("\n" + "="*60)
        print(f"Fetching current price for {symbol}...")
        print("="*60)
        
        price = get_current_price(symbol)
        
        print(f"\n✅ Current {symbol} Price: ${price:,.2f}")
        print("\n" + "-"*60)
        print("Suggested Limit Order Prices:")
        print("-"*60)
        
        # Calculate suggested prices
        buy_price_1pct = price * 0.99
        buy_price_2pct = price * 0.98
        sell_price_1pct = price * 1.01
        sell_price_2pct = price * 1.02
        
        print(f"\nFor BUY orders (below market):")
        print(f"  -1%: ${buy_price_1pct:,.2f}")
        print(f"  -2%: ${buy_price_2pct:,.2f}")
        
        print(f"\nFor SELL orders (above market):")
        print(f"  +1%: ${sell_price_1pct:,.2f}")
        print(f"  +2%: ${sell_price_2pct:,.2f}")
        
        print("\n" + "="*60)
        print("Example Commands:")
        print("="*60)
        print(f"\n# Buy {symbol} at 1% below market")
        print(f"py bot.py limit {symbol} BUY 0.001 {buy_price_1pct:.2f}")
        
        print(f"\n# Sell {symbol} at 1% above market")
        print(f"py bot.py limit {symbol} SELL 0.001 {sell_price_1pct:.2f}")
        
        print(f"\n# Market orders (instant execution)")
        print(f"py bot.py market {symbol} BUY 0.001")
        print(f"py bot.py market {symbol} SELL 0.001")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nMake sure:")
        print("  1. API credentials are configured")
        print("  2. Symbol is valid (e.g., BTCUSDT, ETHUSDT)")
        print("  3. Internet connection is active")
        print("\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
