# Binance Futures Testnet Trading Bot

A comprehensive Python trading bot for Binance USDT-M Futures Testnet. Supports market orders, limit orders, stop-limit orders, and OCO (One-Cancels-Other) orders with an intuitive CLI interface and comprehensive logging.

## 🌟 Features

### Core Features
✅ **Market Orders** - Execute immediate orders at market price (BUY/SELL)
✅ **Limit Orders** - Place orders at specific price levels (BUY/SELL)
✅ **Stop-Limit Orders** - Set stop prices with limit price execution
✅ **OCO Orders** - One-Cancels-Other orders for risk management
✅ **Order Status** - Check order execution status and details
✅ **Input Validation** - Comprehensive validation of user inputs
✅ **Error Handling** - Robust error handling with informative messages
✅ **Logging** - Full API request/response logging to file and console
✅ **Testnet Support** - Safe testing on Binance Futures Testnet

### Bonus Features
🎁 **OCO Order Type** - Advanced trading strategy support
🎁 **Comprehensive Logging** - Track all API interactions and errors
🎁 **Symbol Validation** - Verify trading pairs before order placement

## 📋 Requirements

- Python 3.7+
- Binance API credentials (Testnet)
- Internet connection

## 🚀 Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `python-binance>=1.0.19` - Official Binance API library
- `python-dotenv>=0.19.0` - Environment variable management
- `requests>=2.28.0` - HTTP requests library

### 2. Get Binance Testnet API Credentials

1. **Register/Login to Binance Testnet**
   - Navigate to: https://testnet.binancefuture.com/
   - Create or use existing account

2. **Generate API Key and Secret**
   - Go to Account Settings → API Management
   - Create new API key
   - Copy API Key and API Secret

3. **Enable Futures Trading**
   - Activate Futures trading on your testnet account
   - You'll receive test USDT for trading

### 3. Configure Environment Variables

1. **Copy the example env file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your credentials:**
   ```
   API_KEY=your_api_key_here
   API_SECRET=your_api_secret_here
   TESTNET=True
   ```

⚠️ **Security Warning**: Never commit `.env` file to version control!

### 4. Run the Bot

```bash
python trading_bot.py
```

## 📖 Usage Guide

### Menu Options

```
1. Place Market Order       - Execute immediate trades at market price
2. Place Limit Order        - Set orders at specific price levels
3. Place Stop-Limit Order   - Protective orders with stop triggers
4. Place OCO Order          - One-Cancels-Other advanced orders
5. Check Order Status       - View order execution details
6. Exit                     - Close the bot
```

### Example Workflows

#### Market Order (BUY)
```
Choice: 1
Symbol: BTCUSDT
Side: BUY
Quantity: 0.001
```

#### Limit Order (SELL)
```
Choice: 2
Symbol: ETHUSDT
Side: SELL
Quantity: 1.0
Limit Price: 2000.00
```

#### Stop-Limit Order
```
Choice: 3
Symbol: BTCUSDT
Side: SELL
Quantity: 0.001
Stop Price: 45000.00
Limit Price: 44500.00
```

#### OCO Order
```
Choice: 4
Symbol: BTCUSDT
Side: BUY
Quantity: 0.001
Limit Price: 52000.00
Stop Price: 48000.00
Stop Limit Price: 47500.00
```

#### Check Order Status
```
Choice: 5
Symbol: BTCUSDT
Order ID: 123456
```

## 📁 Project Structure

```
Crypto Trading Bot/
├── trading_bot.py              # Main bot application
├── config.py                   # Configuration (API credentials)
├── requirements.txt            # Python dependencies
├── .env.example               # Example environment variables
├── README.md                  # This file
├── logs/
│   └── trading_bot.log       # Detailed operation logs
└── tests/
    └── test_bot.py           # Unit tests
```

## 🔧 Code Architecture

### BasicBot Class

Main class for trading operations:

```python
class BasicBot:
    def __init__(self, api_key, api_secret, testnet=True)
    def validate_symbol(symbol) -> bool
    def place_market_order(symbol, side, quantity) -> dict
    def place_limit_order(symbol, side, quantity, price) -> dict
    def place_stop_limit_order(symbol, side, quantity, stop_price, limit_price) -> dict
    def place_oco_order(symbol, side, quantity, price, stop_price, stop_limit_price) -> dict
    def get_order_status(symbol, order_id) -> dict
```

### Key Methods

- **validate_symbol()**: Checks if trading pair exists on futures exchange
- **place_market_order()**: Execute immediate orders at current market price
- **place_limit_order()**: Place orders at specified price levels
- **place_stop_limit_order()**: Conditional orders with stop and limit prices
- **place_oco_order()**: Advanced orders (one fills, other cancels)
- **get_order_status()**: Retrieve order details and execution status

## 📊 Order Types Explained

### Market Order
- Executes immediately at best available market price
- No price control
- Useful for quick entry/exit

### Limit Order
- Executes only at specified price or better
- Can remain pending if price target not reached
- Better price control

### Stop-Limit Order
- Triggers when price hits stop level
- Executes as limit order at specified price
- Provides protection against slippage

### OCO Order
- Two orders linked together
- When one fills, the other automatically cancels
- Ideal for profit-taking and stop-loss pairs

## 📝 Logging

All operations are logged to `logs/trading_bot.log`:
- API requests and responses
- Order placements and updates
- Errors and exceptions
- User actions

View logs:
```bash
tail -f logs/trading_bot.log
```

## 🧪 Testing

Run the test suite:

```bash
python -m pytest tests/
```

Or with unittest:

```bash
python -m unittest discover tests/
```

Test Coverage:
- ✅ Symbol validation
- ✅ Market order placement
- ✅ Limit order placement
- ✅ Stop-limit order placement
- ✅ OCO order placement
- ✅ Order status retrieval
- ✅ Error handling
- ✅ API error responses

## ⚠️ Important Notes

### Testnet Information
- Testnet is completely separate from mainnet
- Balances and orders don't affect real trading
- Perfect for testing strategies without risk
- Test USDT is provided by Binance

### Best Practices
1. **Always validate inputs** before placing orders
2. **Start with small quantities** when testing
3. **Monitor logs** for any API issues
4. **Use stop-loss orders** for risk management
5. **Test thoroughly** before moving to mainnet

### Common Issues

**"API credentials not found"**
- Ensure `.env` file exists in project root
- Check API_KEY and API_SECRET are not empty

**"Invalid symbol"**
- Verify symbol format (e.g., BTCUSDT)
- Symbol must be in futures market

**"Insufficient Balance"**
- Check testnet account balance
- Request test funds if needed

**"Order rejected"**
- Check order quantity meets minimum
- Verify price precision
- Ensure symbol is tradeable

## 🔐 Security Considerations

- ✅ Never commit `.env` file to version control
- ✅ Use testnet for development/testing
- ✅ Rotate API keys periodically
- ✅ Limit API key permissions (IP whitelisting recommended)
- ✅ Don't share API credentials

## 📚 Additional Resources

- [Binance Futures Testnet](https://testnet.binancefuture.com/)
- [python-binance Documentation](https://python-binance.readthedocs.io/)
- [Binance API Documentation](https://binance-docs.github.io/apidocs/)
- [Futures API Reference](https://binance-docs.github.io/apidocs/futures/en/)

## 🤝 Contributing

Feel free to submit issues, fork the repository, and create pull requests for improvements.

## 📄 License

This project is provided as-is for educational purposes.

---

**Happy Trading! 🚀**

*Remember: Always test thoroughly on testnet before trading with real funds.*
