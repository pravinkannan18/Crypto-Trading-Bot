# Binance Futures Trading Bot

A comprehensive CLI-based trading bot for Binance USDT-M Futures with support for multiple order types, advanced trading strategies, and robust logging.

## 📋 Features

### Core Orders (Mandatory)
- ✅ **Market Orders** - Instant execution at current market price
- ✅ **Limit Orders** - Execute at specified price with time-in-force options

### Advanced Orders (Bonus)
- ✅ **Stop-Limit Orders** - Trigger limit orders when stop price is reached
- ✅ **OCO Orders** - One-Cancels-the-Other (Take-Profit + Stop-Loss pairs)
- ✅ **TWAP Strategy** - Time-Weighted Average Price for large orders
- ✅ **Grid Trading** - Automated buy-low/sell-high within price ranges

### Additional Features
- 🔒 Complete input validation (symbol, quantity, price, thresholds)
- 📊 Structured logging with timestamps and error traces
- 🎯 Precision adjustment for exchange requirements
- ⚡ API connection validation and error handling
- 🧪 Dry-run mode for testing without real orders

## 📁 Project Structure

```
Pravin_binance_bot/
│
├── src/
│   ├── config.py              # Core configuration, logging, and utilities
│   ├── market_orders.py       # Market order execution
│   ├── limit_orders.py        # Limit order execution
│   └── advanced/
│       ├── stop_limit.py      # Stop-limit orders
│       ├── oco.py             # OCO (One-Cancels-the-Other) orders
│       ├── twap.py            # TWAP strategy implementation
│       └── grid_strategy.py   # Grid trading strategy
│
├── bot.log                    # Structured logs (auto-generated)
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🚀 Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- Binance Futures account (Testnet or Production)
- API Keys (with Futures trading permissions)

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure API Credentials

Set environment variables for your API keys:

**For Testnet (Recommended for testing):**
```powershell
$env:BINANCE_TESTNET_API_KEY = "your_testnet_api_key"
$env:BINANCE_TESTNET_SECRET_KEY = "your_testnet_secret_key"
```

**For Production (Real trading):**
Edit `src/config.py` and set `USE_TESTNET = False`, then:
```powershell
$env:BINANCE_API_KEY = "your_production_api_key"
$env:BINANCE_SECRET_KEY = "your_production_secret_key"
```

### 4. Get API Keys

**Testnet:**
- Visit: https://testnet.binancefuture.com/
- Login and generate API keys
- No real funds required

**Production:**
- Login to Binance
- Go to API Management
- Create new API key with Futures trading enabled
- Enable spot & futures trading permissions

## 📖 Usage Guide

### Market Orders

Execute orders at current market price:

```powershell
# Buy 0.01 BTC at market price
python src/market_orders.py BTCUSDT BUY 0.01

# Sell 0.5 ETH at market price
python src/market_orders.py ETHUSDT SELL 0.5

# Reduce-only order (close position)
python src/market_orders.py BTCUSDT SELL 0.01 --reduce-only
```

### Limit Orders

Place orders at specific prices:

```powershell
# Buy 0.01 BTC at $50,000
python src/limit_orders.py BTCUSDT BUY 0.01 50000

# Sell 0.5 ETH at $2,000 with IOC time-in-force
python src/limit_orders.py ETHUSDT SELL 0.5 2000 --time-in-force IOC

# Post-only order (maker-only, no taker fee)
python src/limit_orders.py BTCUSDT BUY 0.01 50000 --post-only
```

**Time-in-Force Options:**
- `GTC` (Good-Till-Cancel) - Default, remains active until filled or cancelled
- `IOC` (Immediate-or-Cancel) - Fill immediately or cancel
- `FOK` (Fill-or-Kill) - Fill completely or cancel
- `GTX` (Good-Till-Crossing) - Post-only, maker orders only

### Stop-Limit Orders

Trigger limit orders when stop price is reached:

```powershell
# BUY: Trigger at 49000, place limit at 49500
python src/advanced/stop_limit.py BTCUSDT BUY 0.01 49000 49500

# SELL: Stop-loss at 48000, limit at 47900
python src/advanced/stop_limit.py BTCUSDT SELL 0.01 48000 47900 --reduce-only

# Use MARK_PRICE instead of CONTRACT_PRICE
python src/advanced/stop_limit.py ETHUSDT SELL 0.5 2100 2050 --working-type MARK_PRICE
```

### OCO Orders (One-Cancels-the-Other)

Place take-profit and stop-loss simultaneously:

```powershell
# Close LONG position: TP at 52000 or SL at 48000
python src/advanced/oco.py BTCUSDT LONG 0.01 52000 48000

# Close SHORT position: TP at 1900 or SL at 2100
python src/advanced/oco.py ETHUSDT SHORT 0.5 1900 2100
```

**Note:** OCO orders are reduce-only and close existing positions.

### TWAP Strategy (Time-Weighted Average Price)

Split large orders into smaller chunks over time:

```powershell
# Buy 0.1 BTC in 5 slices over 60 seconds
python src/advanced/twap.py BTCUSDT BUY 0.1 5 60

# Sell 2 ETH in 10 slices over 120 seconds with randomization
python src/advanced/twap.py ETHUSDT SELL 2.0 10 120 --randomize

# Dry run (test without placing real orders)
python src/advanced/twap.py BTCUSDT BUY 0.05 3 30 --dry-run
```

**Benefits:**
- Reduces market impact
- Better average execution price
- Ideal for large orders

### Grid Trading Strategy

Automate buy-low/sell-high within a price range:

```powershell
# Setup 10-level grid between $48,000-$52,000
python src/advanced/grid_strategy.py BTCUSDT 48000 52000 10 0.01

# Setup 20-level grid for ETH
python src/advanced/grid_strategy.py ETHUSDT 1800 2200 20 0.1

# Test with dry run
python src/advanced/grid_strategy.py BTCUSDT 48000 52000 5 0.01 --dry-run

# Cancel all grid orders
python src/advanced/grid_strategy.py BTCUSDT --cancel-all
```

**How it works:**
- Places buy orders below current price
- Places sell orders above current price
- Profits from price oscillations
- Best for ranging markets

## 📊 Logging

All actions are logged to `bot.log` with the following information:
- Timestamps
- Order details (symbol, side, quantity, price)
- API responses
- Error messages with full tracebacks
- Execution status

Example log entry:
```
2025-10-24 14:30:15 - market_orders - INFO - Placing market order: {'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'MARKET', 'quantity': 0.01}
2025-10-24 14:30:16 - config - INFO - Request successful: {'orderId': 12345, 'symbol': 'BTCUSDT', 'status': 'FILLED'}
2025-10-24 14:30:16 - market_orders - INFO - Market order executed successfully: Order ID 12345
```

## 🔍 Validation Features

The bot includes comprehensive validation:

1. **Symbol Validation** - Ensures valid format (e.g., BTCUSDT)
2. **Quantity Validation** - Checks positive values and exchange minimums
3. **Price Validation** - Validates price ranges and precision
4. **Precision Adjustment** - Automatically adjusts to exchange requirements
5. **API Connection Check** - Validates connection before execution
6. **Logical Validation** - Checks stop-loss/take-profit relationships

## 🛡️ Error Handling

The bot handles various error scenarios:

- API connection failures
- Invalid credentials
- Insufficient balance
- Invalid order parameters
- Rate limiting
- Network timeouts

All errors are logged with detailed information for troubleshooting.

## 🧪 Testing

### Dry Run Mode

Most advanced strategies support `--dry-run` for testing:

```powershell
python src/advanced/twap.py BTCUSDT BUY 0.1 5 60 --dry-run
python src/advanced/grid_strategy.py BTCUSDT 48000 52000 5 0.01 --dry-run
```

### Using Testnet

Always test with Binance Futures Testnet before using real funds:
1. Set `USE_TESTNET = True` in `src/config.py` (default)
2. Use testnet API keys
3. Test all order types thoroughly
4. Verify logging and error handling

## 📚 Resources

- **Binance Futures API Docs**: https://binance-docs.github.io/apidocs/futures/en/
- **Testnet**: https://testnet.binancefuture.com/
- **API Management**: https://www.binance.com/en/my/settings/api-management

## ⚠️ Disclaimer

This bot is for educational purposes. Always:
- Test thoroughly on testnet first
- Start with small amounts
- Understand the risks of futures trading
- Never share your API keys
- Use API key restrictions (IP whitelist, permissions)

## 🤝 Support

For issues or questions:
1. Check `bot.log` for error details
2. Verify API credentials and permissions
3. Ensure sufficient balance
4. Check Binance API status

## 📝 License

This project is submitted as part of the Binance Futures Order Bot assignment.

---

**Author**: Pravin  
**Submission Date**: October 2025  
**Version**: 1.0
