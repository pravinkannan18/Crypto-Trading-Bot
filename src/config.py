"""
config.py

Core configuration, logging setup, and validation utilities for Binance Futures Bot.
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict
import hmac
import hashlib
import requests
from urllib.parse import urlencode

# ============================================================================
# API Configuration
# ============================================================================

# Binance Futures Testnet (for testing)
TESTNET_API_KEY = os.getenv("BINANCE_TESTNET_API_KEY", "rle4CGBafo6rdxI6DDwVWiHosx7VRDCEIvXxzFZQ0qDg4w1XrH60ug0iQVsd3fqw")
TESTNET_SECRET_KEY = os.getenv("BINANCE_TESTNET_SECRET_KEY", "tmNWxvQxVpzvSg2jJ6CkI6UdwKXG59kmBnXBBLQqqHoGv2a2juqGWBM4iJeJ5Tk5")
TESTNET_BASE_URL = "https://testnet.binancefuture.com"

# Binance Futures Production (comment out if using testnet)
# PROD_API_KEY = os.getenv("BINANCE_API_KEY", "")
# PROD_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")
# PROD_BASE_URL = "https://fapi.binance.com"

# Use testnet by default (switch to production for live trading)
USE_TESTNET = True

if USE_TESTNET:
    API_KEY = TESTNET_API_KEY
    SECRET_KEY = TESTNET_SECRET_KEY
    BASE_URL = TESTNET_BASE_URL
else:
    # API_KEY = PROD_API_KEY
    # SECRET_KEY = PROD_SECRET_KEY
    # BASE_URL = PROD_BASE_URL
    pass

# ============================================================================
# Logging Configuration
# ============================================================================

LOG_FILE = "bot.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logger(name: str) -> logging.Logger:
    """
    Setup and return a logger with both file and console handlers.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# ============================================================================
# Validation Utilities
# ============================================================================

def validate_symbol(symbol: str) -> bool:
    """
    Validate if symbol format is correct (e.g., BTCUSDT).
    
    Args:
        symbol: Trading pair symbol
        
    Returns:
        True if valid, False otherwise
    """
    if not symbol or not isinstance(symbol, str):
        return False
    
    symbol = symbol.upper()
    
    # Basic checks
    if len(symbol) < 6 or not symbol.isalnum():
        return False
    
    # Most futures symbols end with USDT
    if not symbol.endswith("USDT"):
        return False
    
    return True

def validate_side(side: str) -> bool:
    """
    Validate order side (BUY or SELL).
    
    Args:
        side: Order side
        
    Returns:
        True if valid, False otherwise
    """
    return side.upper() in ["BUY", "SELL"]

def validate_quantity(quantity: float) -> bool:
    """
    Validate order quantity.
    
    Args:
        quantity: Order quantity
        
    Returns:
        True if valid, False otherwise
    """
    try:
        qty = float(quantity)
        return qty > 0
    except (ValueError, TypeError):
        return False

def validate_price(price: float) -> bool:
    """
    Validate order price.
    
    Args:
        price: Order price
        
    Returns:
        True if valid, False otherwise
    """
    try:
        p = float(price)
        return p > 0
    except (ValueError, TypeError):
        return False

# ============================================================================
# API Utilities
# ============================================================================

def get_timestamp() -> int:
    """Get current timestamp in milliseconds."""
    return int(datetime.now().timestamp() * 1000)

def generate_signature(params: Dict) -> str:
    """
    Generate HMAC SHA256 signature for Binance API.
    
    Args:
        params: Request parameters
        
    Returns:
        Signature string
    """
    query_string = urlencode(params)
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def make_request(
    method: str,
    endpoint: str,
    params: Optional[Dict] = None,
    signed: bool = False
) -> Dict:
    """
    Make a request to Binance API.
    
    Args:
        method: HTTP method (GET, POST, DELETE)
        endpoint: API endpoint
        params: Request parameters
        signed: Whether request requires signature
        
    Returns:
        Response JSON
        
    Raises:
        Exception: If request fails
    """
    logger = logging.getLogger(__name__)
    
    if params is None:
        params = {}
    
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "X-MBX-APIKEY": API_KEY
    }
    
    if signed:
        params["timestamp"] = get_timestamp()
        params["signature"] = generate_signature(params)
    
    logger.info(f"Making {method} request to {endpoint}")
    logger.debug(f"Parameters: {params}")
    
    try:
        if method == "GET":
            response = requests.get(url, params=params, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, params=params, headers=headers, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, params=params, headers=headers, timeout=10)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        result = response.json()
        logger.info(f"Request successful: {result}")
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                logger.error(f"Error details: {error_detail}")
            except:
                logger.error(f"Response text: {e.response.text}")
        raise

def get_exchange_info(symbol: Optional[str] = None) -> Dict:
    """
    Get exchange trading rules and symbol information.
    
    Args:
        symbol: Optional symbol to filter (e.g., BTCUSDT)
        
    Returns:
        Exchange info dict
    """
    endpoint = "/fapi/v1/exchangeInfo"
    params = {}
    if symbol:
        params["symbol"] = symbol.upper()
    
    return make_request("GET", endpoint, params, signed=False)

def get_account_balance() -> Dict:
    """
    Get futures account balance.
    
    Returns:
        Account information
    """
    endpoint = "/fapi/v2/account"
    return make_request("GET", endpoint, signed=True)

def get_current_price(symbol: str) -> float:
    """
    Get current market price for a symbol.
    
    Args:
        symbol: Trading pair symbol
        
    Returns:
        Current price
    """
    endpoint = "/fapi/v1/ticker/price"
    params = {"symbol": symbol.upper()}
    response = make_request("GET", endpoint, params, signed=False)
    return float(response["price"])

# ============================================================================
# Symbol Precision Utilities
# ============================================================================

def get_symbol_filters(symbol: str) -> Dict:
    """
    Get trading filters for a symbol (price, quantity precision, etc.).
    
    Args:
        symbol: Trading pair symbol
        
    Returns:
        Dict containing filters
    """
    exchange_info = get_exchange_info(symbol)
    
    for symbol_info in exchange_info["symbols"]:
        if symbol_info["symbol"] == symbol.upper():
            filters = {}
            for f in symbol_info["filters"]:
                filters[f["filterType"]] = f
            
            return {
                "pricePrecision": symbol_info["pricePrecision"],
                "quantityPrecision": symbol_info["quantityPrecision"],
                "filters": filters
            }
    
    raise ValueError(f"Symbol {symbol} not found")

def round_step_size(quantity: float, step_size: float) -> float:
    """
    Round quantity to valid step size.
    
    Args:
        quantity: Original quantity
        step_size: Step size from exchange filters
        
    Returns:
        Rounded quantity
    """
    precision = len(str(step_size).split('.')[-1].rstrip('0'))
    return round(quantity - (quantity % step_size), precision)

# ============================================================================
# Initialization Check
# ============================================================================

def check_api_credentials() -> bool:
    """
    Check if API credentials are configured.
    
    Returns:
        True if credentials exist, False otherwise
    """
    if not API_KEY or not SECRET_KEY:
        return False
    return True

def validate_api_connection() -> bool:
    """
    Test API connection by fetching server time.
    
    Returns:
        True if connection successful, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    try:
        endpoint = "/fapi/v1/time"
        response = make_request("GET", endpoint, signed=False)
        logger.info(f"API connection successful. Server time: {response['serverTime']}")
        return True
    except Exception as e:
        logger.error(f"API connection failed: {str(e)}")
        return False
