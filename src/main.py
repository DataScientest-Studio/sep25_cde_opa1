import sys
import os

# Add src directory to Python path
src_dir = os.path.dirname(os.path.abspath(__file__))
if src_dir not in sys.path:
  sys.path.insert(0, src_dir)

from data.config import SETTINGS
from data.connector.connector import connect_to_mongo
from data.fetch_historical_daily import upsert_daily_history

import traceback


def main():
  """Main function to fetch and store historical cryptocurrency data."""
  print("=" * 60)
  print("Cryptocurrency Data Collection")
  print("=" * 60)

  try:
    # Connect to MongoDB
    print(f"\nConnecting to MongoDB at {SETTINGS['MONGO_HOST']}:{SETTINGS['MONGO_PORT']}...")
    mongo_client = connect_to_mongo(
      db_name=SETTINGS["MONGO_DB"],
      host=SETTINGS["MONGO_HOST"],
      port=int(SETTINGS["MONGO_PORT"]),
      user=SETTINGS.get("MONGO_USER", ""),
      password=SETTINGS.get("MONGO_PASSWORD", ""),
      auth=bool(SETTINGS.get("MONGO_USER", ""))
    )

    # Test MongoDB connection
    mongo_client[SETTINGS["MONGO_DB"]].list_collection_names()
    print(f"✓ Connected to MongoDB database: {SETTINGS['MONGO_DB']}")

    # Fetch and upsert historical daily data
    print("\n" + "=" * 60)
    print("Fetching historical data from Binance...")
    print("=" * 60)
    upsert_daily_history()

    print("\n" + "=" * 60)
    print("✅ Data collection completed successfully!")
    print("=" * 60)

  except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nTroubleshooting:")
    print("  1. Make sure MongoDB is running: docker ps | grep mongo")
    print("  2. Make sure your postgresql server is running: docker ps | grep postgres")
    print("  3. Initialize PostgreSQL database: python init_database.py")
    print("  4. Check your .env file configuration")
    print("  5. Verify network connectivity to Binance API")
    traceback.print_exc()
  finally:
    # Close MongoDB connection
    if 'mongo_client' in locals():
      mongo_client.close()
      print("\n✅ MongoDB connection closed.")


if __name__ == '__main__':
  main()
