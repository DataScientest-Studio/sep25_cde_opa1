"""
Validation script to test the API setup.
Run this after starting the API to verify everything works.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import requests
from colorama import init, Fore, Style

# Initialize colorama for colored output
try:
  init(autoreset=True)
except:
  # Colorama not installed, define dummy colors
  class DummyColor:
    def __getattr__(self, item):
      return ""


  Fore = DummyColor()
  Style = DummyColor()

API_BASE_URL = "http://localhost:8000"


def print_header(text):
  """Print a formatted header."""
  print(f"\n{Fore.CYAN}{'=' * 60}")
  print(f"{Fore.CYAN}{text:^60}")
  print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")


def print_success(text):
  """Print success message."""
  print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")


def print_error(text):
  """Print error message."""
  print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")


def print_info(text):
  """Print info message."""
  print(f"{Fore.YELLOW}ℹ {text}{Style.RESET_ALL}")


def test_connection():
  """Test if API is reachable."""
  print_header("Testing API Connection")
  try:
    response = requests.get(f"{API_BASE_URL}/", timeout=5)
    if response.status_code == 200:
      print_success(f"API is reachable at {API_BASE_URL}")
      return True
    else:
      print_error(f"API returned status code {response.status_code}")
      return False
  except requests.exceptions.ConnectionError:
    print_error(f"Cannot connect to API at {API_BASE_URL}")
    print_info("Make sure the API is running with: python run_api.py")
    return False
  except Exception as e:
    print_error(f"Error: {e}")
    return False


def test_health():
  """Test health check endpoint."""
  print_header("Testing Health Check")
  try:
    response = requests.get(f"{API_BASE_URL}/health", timeout=5)
    if response.status_code == 200:
      data = response.json()
      print_success(f"Health check passed: {data['status']}")
      print_info(f"Message: {data['message']}")
      return True
    else:
      print_error(f"Health check failed with status {response.status_code}")
      return False
  except Exception as e:
    print_error(f"Health check error: {e}")
    return False


def test_symbols():
  """Test symbols endpoint."""
  print_header("Testing Symbols Endpoint")
  try:
    response = requests.get(f"{API_BASE_URL}/api/symbols", timeout=5)
    if response.status_code == 200:
      data = response.json()
      symbols = data.get('symbols', [])
      if symbols:
        print_success(f"Found {len(symbols)} symbols")
        print_info(f"Symbols: {', '.join(symbols)}")
        return True
      else:
        print_error("No symbols found in database")
        print_info("Run: python src/main.py to populate data")
        return False
    else:
      print_error(f"Symbols endpoint failed with status {response.status_code}")
      return False
  except Exception as e:
    print_error(f"Symbols endpoint error: {e}")
    return False


def test_historical_data():
  """Test historical data endpoint."""
  print_header("Testing Historical Data Endpoint")
  try:
    response = requests.get(
      f"{API_BASE_URL}/api/historical/BTCUSDT",
      params={"limit": 5},
      timeout=5
    )
    if response.status_code == 200:
      data = response.json()
      if data:
        print_success(f"Retrieved {len(data)} records for BTCUSDT")
        latest = data[-1]
        print_info(f"Latest record:")
        print(f"  Time: {latest['open_time']}")
        print(f"  Open: ${latest['open']:,.2f}")
        print(f"  Close: ${latest['close']:,.2f}")
        print(f"  Volume: {latest['volume']:,.2f}")
        return True
      else:
        print_error("No data returned")
        print_info("Run: python src/main.py to populate data")
        return False
    elif response.status_code == 404:
      print_error("No data found for BTCUSDT")
      print_info("Run: python src/main.py to populate data")
      return False
    else:
      print_error(f"Historical data endpoint failed with status {response.status_code}")
      return False
  except Exception as e:
    print_error(f"Historical data endpoint error: {e}")
    return False


def test_latest_data():
  """Test latest data endpoint."""
  print_header("Testing Latest Data Endpoint")
  try:
    response = requests.get(
      f"{API_BASE_URL}/api/latest/BTCUSDT",
      params={"count": 5},
      timeout=5
    )
    if response.status_code == 200:
      data = response.json()
      if data:
        print_success(f"Retrieved {len(data)} latest records")
        return True
      else:
        print_error("No data returned")
        return False
    elif response.status_code == 404:
      print_error("No data found")
      print_info("Run: python src/main.py to populate data")
      return False
    else:
      print_error(f"Latest data endpoint failed with status {response.status_code}")
      return False
  except Exception as e:
    print_error(f"Latest data endpoint error: {e}")
    return False


def test_statistics():
  """Test statistics endpoint."""
  print_header("Testing Statistics Endpoint")
  try:
    response = requests.get(
      f"{API_BASE_URL}/api/stats/BTCUSDT",
      timeout=5
    )
    if response.status_code == 200:
      data = response.json()
      print_success("Statistics retrieved successfully")
      print_info(f"Total records: {data.get('count', 0)}")
      if data.get('avg_close'):
        print(f"  Average close: ${data['avg_close']:,.2f}")
        print(f"  Min low: ${data['min_low']:,.2f}")
        print(f"  Max high: ${data['max_high']:,.2f}")
        print(f"  Total volume: {data['total_volume']:,.2f}")
      return True
    elif response.status_code == 404:
      print_error("No data found for statistics")
      print_info("Run: python src/main.py to populate data")
      return False
    else:
      print_error(f"Statistics endpoint failed with status {response.status_code}")
      return False
  except Exception as e:
    print_error(f"Statistics endpoint error: {e}")
    return False


def main():
  """Run all tests."""
  print(f"\n{Fore.MAGENTA}{'*' * 60}")
  print(f"{Fore.MAGENTA}{'API Validation Script':^60}")
  print(f"{Fore.MAGENTA}{'*' * 60}{Style.RESET_ALL}")

  tests = [
    ("Connection", test_connection),
    ("Health Check", test_health),
    ("Symbols", test_symbols),
    ("Historical Data", test_historical_data),
    ("Latest Data", test_latest_data),
    ("Statistics", test_statistics),
  ]

  results = []
  for name, test_func in tests:
    result = test_func()
    results.append((name, result))

  # Summary
  print_header("Test Summary")
  passed = sum(1 for _, result in results if result)
  total = len(results)

  for name, result in results:
    status = f"{Fore.GREEN}PASS" if result else f"{Fore.RED}FAIL"
    print(f"{status:20} {Style.RESET_ALL}{name}")

  print(f"\n{Fore.CYAN}Results: {passed}/{total} tests passed{Style.RESET_ALL}")

  if passed == total:
    print(f"\n{Fore.GREEN}🎉 All tests passed! API is working correctly.{Style.RESET_ALL}")
    print_info("You can now:")
    print("  - Access Swagger docs: http://localhost:8000/docs")
    print("  - Use the Python client in notebooks")
    print("  - Build your frontend application")
    return 0
  else:
    print(f"\n{Fore.RED}⚠ Some tests failed. Please check the errors above.{Style.RESET_ALL}")
    if not results[0][1]:  # Connection failed
      print_info("Start the API with: python run_api.py")
    elif not results[2][1]:  # No symbols
      print_info("Populate data with: python src/main.py")
    return 1


if __name__ == "__main__":
  sys.exit(main())
