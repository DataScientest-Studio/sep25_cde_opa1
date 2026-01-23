from config import SETTINGS

from data.connector.connector import connect_to_mongo, connect_to_postgres

from data.fetch_historical_daily import upsert_daily_history

# Connexion aux bases de données
postgres_engine = connect_to_postgres(
  db_name=SETTINGS["POSTGRES_DB"],
  user=SETTINGS["POSTGRES_USER"],
  password=SETTINGS["POSTGRES_PASSWORD"],
  host=SETTINGS["DB_HOST"],
  port=int(SETTINGS["POSTGRES_PORT"])
)

mongo_db = connect_to_mongo(
  db_name=SETTINGS["MONGO_DB"],
  host=SETTINGS["MONGO_HOST"],
  port=int(SETTINGS["MONGO_PORT"]),
  user=SETTINGS["MONGO_USER"],
  password=SETTINGS["MONGO_PASSWORD"]
)


def main():
  try:
    # Test connections
    with postgres_engine.connect() as conn:
      conn.execute("SELECT 1")
    mongo_db.list_collection_names()
    print("Connections established successfully.")

    # Upsert historical daily data
    upsert_daily_history()

  except Exception as e:
    print(f"Error establishing connections: {e}")
  finally:
    postgres_engine.dispose()
    mongo_db.close()


if __name__ == '__main__':
  main()
