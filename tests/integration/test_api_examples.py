"""
Example tests for the API endpoints.
Run with: pytest test_api_examples.py
"""
import pytest
from datetime import datetime, timedelta
import requests

API_BASE_URL = "http://localhost:8000"


class TestAPIExamples:
  """Example tests for the cryptocurrency API."""

  def test_health_check(self):
    """Test that the API is running and healthy."""
    response = requests.get(f"{API_BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

  def test_get_symbols(self):
    """Test getting available symbols."""
    response = requests.get(f"{API_BASE_URL}/api/symbols")
    assert response.status_code == 200
    data = response.json()
    assert "symbols" in data
    assert isinstance(data["symbols"], list)
    assert len(data["symbols"]) > 0
    # Check for expected symbols
    assert "BTCUSDT" in data["symbols"]

  def test_get_intervals(self):
    """Test getting available intervals."""
    response = requests.get(f"{API_BASE_URL}/api/intervals")
    assert response.status_code == 200
    data = response.json()
    assert "intervals" in data
    assert isinstance(data["intervals"], list)

  def test_get_historical_data(self):
    """Test getting historical data."""
    response = requests.get(
      f"{API_BASE_URL}/api/historical/BTCUSDT",
      params={"interval": "1d", "limit": 10}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10

    # Check data structure
    if len(data) > 0:
      record = data[0]
      assert "symbol" in record
      assert "interval" in record
      assert "open_time" in record
      assert "open" in record
      assert "high" in record
      assert "low" in record
      assert "close" in record
      assert "volume" in record

  def test_get_historical_data_with_dates(self):
    """Test getting historical data with date range."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    response = requests.get(
      f"{API_BASE_URL}/api/historical/BTCUSDT",
      params={
        "interval": "1d",
        "start_time": start_date.isoformat(),
        "end_time": end_date.isoformat()
      }
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

  def test_get_latest_data(self):
    """Test getting latest data."""
    response = requests.get(
      f"{API_BASE_URL}/api/latest/BTCUSDT",
      params={"count": 30}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 30

  def test_get_stats(self):
    """Test getting aggregated statistics."""
    response = requests.get(
      f"{API_BASE_URL}/api/stats/BTCUSDT",
      params={"interval": "1d"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "symbol" in data
    assert "interval" in data
    assert "count" in data
    assert data["count"] > 0
    assert "avg_close" in data
    assert "min_low" in data
    assert "max_high" in data
    assert "total_volume" in data

  def test_invalid_symbol(self):
    """Test requesting data for an invalid symbol."""
    response = requests.get(f"{API_BASE_URL}/api/historical/INVALIDSYMBOL")
    assert response.status_code == 404

  def test_invalid_date_format(self):
    """Test with invalid date format."""
    response = requests.get(
      f"{API_BASE_URL}/api/historical/BTCUSDT",
      params={"start_time": "invalid-date"}
    )
    assert response.status_code == 400


if __name__ == "__main__":
  # Run a simple manual test
  print("Testing API endpoints...")

  try:
    # Health check
    print("\n1. Testing health check...")
    response = requests.get(f"{API_BASE_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")

    # Get symbols
    print("\n2. Testing get symbols...")
    response = requests.get(f"{API_BASE_URL}/api/symbols")
    print(f"   Status: {response.status_code}")
    print(f"   Symbols: {response.json()['symbols']}")

    # Get latest data
    print("\n3. Testing get latest data for BTCUSDT...")
    response = requests.get(f"{API_BASE_URL}/api/latest/BTCUSDT?count=5")
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Records returned: {len(data)}")
    if data:
      print(f"   Latest record: {data[-1]}")

    # Get stats
    print("\n4. Testing get statistics for BTCUSDT...")
    response = requests.get(f"{API_BASE_URL}/api/stats/BTCUSDT")
    print(f"   Status: {response.status_code}")
    print(f"   Stats: {response.json()}")

    print("\n✅ All manual tests passed!")

  except requests.exceptions.ConnectionError:
    print("\n❌ Error: Could not connect to API. Make sure it's running on http://localhost:8000")
  except Exception as e:
    print(f"\n❌ Error: {e}")
