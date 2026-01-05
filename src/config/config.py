from dotenv import load_dotenv
import os


config = {
    "DB_HOST": os.getenv("DB_HOST", "localhost"),
    "POSTGRES_USER": os.getenv("POSTGRES_USER", "user"),
    "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", "password"),
    "POSTGRES_DB": os.getenv("POSTGRES_DB", "database"),
    "POSTGRES_PORT": os.getenv("POSTGRES_PORT", "5432"),
    "MONGO_USER": os.getenv("MONGO_USER", "mongo_user"),
    "MONGO_PASSWORD": os.getenv("MONGO_PASSWORD", "mongo_password"),
    "MONGO_HOST": os.getenv("MONGO_HOST", "localhost"),
    "MONGO_PORT": os.getenv("MONGO_PORT", "27017"),
    "MONGO_DB": os.getenv("MONGO_DB", "binance_data"),
}