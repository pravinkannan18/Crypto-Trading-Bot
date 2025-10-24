"""
Test script to verify bot setup and configuration.

This script checks:
1. Python dependencies
2. Module imports
3. Configuration validity
4. File structure

Run this before using the bot to ensure everything is set up correctly.
"""

import sys
import os
from pathlib import Path

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_status(message, status='info'):
    """Print colored status message."""
    if status == 'success':
        print(f"{GREEN}✓{RESET} {message}")
    elif status == 'error':
        print(f"{RED}✗{RESET} {message}")
    elif status == 'warning':
        print(f"{YELLOW}⚠{RESET} {message}")
    else:
        print(f"{BLUE}ℹ{RESET} {message}")

def check_python_version():
    """Check Python version."""
    print("\n" + "="*60)
    print("Checking Python Version")
    print("="*60)
    
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print_status(f"Python {version.major}.{version.minor}.{version.micro} (✓ Compatible)", 'success')
        return True
    else:
        print_status(f"Python {version.major}.{version.minor}.{version.micro} (✗ Requires 3.8+)", 'error')
        return False

def check_dependencies():
    """Check if required dependencies are installed."""
    print("\n" + "="*60)
    print("Checking Dependencies")
    print("="*60)
    
    dependencies = ['requests', 'urllib3']
    all_ok = True
    
    for dep in dependencies:
        try:
            __import__(dep)
            print_status(f"{dep} installed", 'success')
        except ImportError:
            print_status(f"{dep} NOT installed", 'error')
            all_ok = False
    
    if not all_ok:
        print_status("\nInstall missing dependencies: pip install -r requirements.txt", 'warning')
    
    return all_ok

def check_file_structure():
    """Check if all required files exist."""
    print("\n" + "="*60)
    print("Checking File Structure")
    print("="*60)
    
    required_files = [
        'src/config.py',
        'src/market_orders.py',
        'src/limit_orders.py',
        'src/advanced/stop_limit.py',
        'src/advanced/oco.py',
        'src/advanced/twap.py',
        'src/advanced/grid_strategy.py',
        'requirements.txt',
        'README.md',
        'bot.py'
    ]
    
    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print_status(f"{file_path}", 'success')
        else:
            print_status(f"{file_path} (missing)", 'error')
            all_exist = False
    
    return all_exist

def check_imports():
    """Check if modules can be imported."""
    print("\n" + "="*60)
    print("Checking Module Imports")
    print("="*60)
    
    # Add src to path
    sys.path.insert(0, 'src')
    
    modules_to_test = [
        ('config', 'Config module'),
        ('market_orders', 'Market orders'),
        ('limit_orders', 'Limit orders'),
    ]
    
    all_ok = True
    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            print_status(f"{description}", 'success')
        except Exception as e:
            print_status(f"{description} - {str(e)}", 'error')
            all_ok = False
    
    return all_ok

def check_api_credentials():
    """Check if API credentials are configured."""
    print("\n" + "="*60)
    print("Checking API Credentials")
    print("="*60)
    
    testnet_key = os.getenv('BINANCE_TESTNET_API_KEY')
    testnet_secret = os.getenv('BINANCE_TESTNET_SECRET_KEY')
    
    if testnet_key and testnet_secret:
        print_status("Testnet API credentials configured", 'success')
        return True
    else:
        print_status("Testnet API credentials NOT configured", 'warning')
        print_status("Set environment variables:", 'info')
        print("  $env:BINANCE_TESTNET_API_KEY = 'your_key'")
        print("  $env:BINANCE_TESTNET_SECRET_KEY = 'your_secret'")
        return False

def test_api_connection():
    """Test API connection."""
    print("\n" + "="*60)
    print("Testing API Connection")
    print("="*60)
    
    sys.path.insert(0, 'src')
    
    try:
        from config import validate_api_connection, check_api_credentials
        
        if not check_api_credentials():
            print_status("Skipping API test (credentials not configured)", 'warning')
            return False
        
        if validate_api_connection():
            print_status("API connection successful", 'success')
            return True
        else:
            print_status("API connection failed", 'error')
            return False
            
    except Exception as e:
        print_status(f"API test error: {str(e)}", 'error')
        return False

def main():
    """Run all checks."""
    print("\n" + "="*60)
    print("Binance Futures Trading Bot - Setup Verification".center(60))
    print("="*60)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("File Structure", check_file_structure),
        ("Module Imports", check_imports),
        ("API Credentials", check_api_credentials),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print_status(f"Error during {name} check: {str(e)}", 'error')
            results[name] = False
    
    # Optional API connection test
    if results.get("API Credentials"):
        results["API Connection"] = test_api_connection()
    
    # Summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = 'success' if result else 'error'
        print_status(f"{name}: {'PASS' if result else 'FAIL'}", status)
    
    print("\n" + "="*60)
    print(f"Results: {passed}/{total} checks passed")
    print("="*60)
    
    if all(results.values()):
        print_status("\n🎉 All checks passed! Bot is ready to use.", 'success')
        print("\nQuick start:")
        print("  python bot.py --help")
        print("  python bot.py market BTCUSDT BUY 0.01")
    else:
        print_status("\n⚠️  Some checks failed. Please fix the issues above.", 'warning')
        print("\nFor help, check README.md")
    
    print("\n")

if __name__ == "__main__":
    main()
