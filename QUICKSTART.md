# Binance Futures Trading Bot - Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Step 1: Install Dependencies (30 seconds)

```powershell
pip install -r requirements.txt
```

### Step 2: Get Testnet API Keys (2 minutes)

1. Visit: https://testnet.binancefuture.com/
2. Login with your Binance account (or create one)
3. Click on "API Key" in the top right
4. Generate new API key
5. Copy your API Key and Secret Key

### Step 3: Configure Credentials (30 seconds)

Set environment variables in PowerShell:

```powershell
$env:BINANCE_TESTNET_API_KEY = "paste_your_api_key_here"
$env:BINANCE_TESTNET_SECRET_KEY = "paste_your_secret_key_here"
```

### Step 4: Verify Setup (30 seconds)

```powershell
python test_setup.py
```

All checks should pass ✅

### Step 5: Place Your First Order (30 seconds)

```powershell
# Market order - Buy 0.001 BTC
python bot.py market BTCUSDT BUY 0.001

# Or using individual scripts
python src/market_orders.py BTCUSDT BUY 0.001
```

---

## 📝 Common Commands

### Basic Orders

```powershell
# Market Order
python bot.py market BTCUSDT BUY 0.001

# Limit Order
python bot.py limit ETHUSDT SELL 0.01 2000

# Stop-Limit (Stop-Loss)
python bot.py stop-limit BTCUSDT SELL 0.001 48000 47900 --reduce-only
```

### Advanced Strategies

```powershell
# OCO (Take-Profit + Stop-Loss)
python bot.py oco BTCUSDT LONG 0.001 52000 48000

# TWAP (Split order over time)
python bot.py twap BTCUSDT BUY 0.01 5 60 --dry-run

# Grid Trading
python bot.py grid BTCUSDT 48000 52000 10 0.001 --dry-run
```

---

## 🎯 Tips for Testing

1. **Start Small**: Use very small quantities (0.001 BTC)
2. **Use Dry Run**: Test TWAP and Grid with `--dry-run` first
3. **Check Logs**: Review `bot.log` for detailed information
4. **Testnet First**: Always test on testnet before production
5. **Monitor Orders**: Check Binance Futures Testnet UI for order status

---

## 🆘 Troubleshooting

### "API credentials not configured"
```powershell
# Re-run credential setup
$env:BINANCE_TESTNET_API_KEY = "your_key"
$env:BINANCE_TESTNET_SECRET_KEY = "your_secret"
```

### "Failed to connect to Binance API"
- Check your internet connection
- Verify API keys are correct
- Ensure API permissions include Futures trading
- Check if IP is whitelisted (if enabled)

### "Invalid quantity"
- Check minimum order size for the symbol
- Testnet may have different minimums than production

### Import Errors
```powershell
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

---

## 📚 Learn More

- Read `README.md` for comprehensive documentation
- Check `REPORT_TEMPLATE.md` for implementation details
- Review `bot.log` for execution traces
- Visit Binance API docs: https://binance-docs.github.io/apidocs/futures/en/

---

## ⚡ Quick Reference

### Order Types
| Command | Description | Example |
|---------|-------------|---------|
| `market` | Instant execution | `python bot.py market BTCUSDT BUY 0.001` |
| `limit` | Execute at price | `python bot.py limit BTCUSDT BUY 0.001 50000` |
| `stop-limit` | Trigger at price | `python bot.py stop-limit BTCUSDT SELL 0.001 48000 47900` |
| `oco` | TP + SL pair | `python bot.py oco BTCUSDT LONG 0.001 52000 48000` |
| `twap` | Split over time | `python bot.py twap BTCUSDT BUY 0.01 5 60` |
| `grid` | Auto trading | `python bot.py grid BTCUSDT 48000 52000 10 0.001` |

### Useful Flags
- `--reduce-only`: Only reduce position, don't open new
- `--time-in-force GTC/IOC/FOK`: Order time validity
- `--post-only`: Maker-only orders
- `--dry-run`: Simulate without real orders
- `--randomize`: Randomize TWAP slices
- `--cancel-all`: Cancel all grid orders

---

## 🎓 Example Workflow

### 1. Open a Position
```powershell
# Buy 0.01 BTC at market
python bot.py market BTCUSDT BUY 0.01
```

### 2. Set Take-Profit and Stop-Loss
```powershell
# OCO: TP at $52k, SL at $48k
python bot.py oco BTCUSDT LONG 0.01 52000 48000
```

### 3. Close Position
```powershell
# Market sell to close
python bot.py market BTCUSDT SELL 0.01 --reduce-only
```

---

## 📊 Check Your Orders

1. Visit: https://testnet.binancefuture.com/
2. Login to your account
3. Go to "Orders" tab
4. See your bot's orders in real-time

---

## 🔐 Security Reminders

- ✅ Use testnet for learning
- ✅ Never share API keys
- ✅ Enable IP whitelist in production
- ✅ Set read-only permissions when possible
- ✅ Use separate keys for bots
- ❌ Never commit keys to Git
- ❌ Don't use production keys for testing

---

**Ready? Let's trade!** 🚀

Start with:
```powershell
python test_setup.py
python bot.py --help
```
