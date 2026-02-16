from dotenv import load_dotenv
import os
from typing import TypedDict

# Load environment variables from .env file
load_dotenv()

class Settings(TypedDict):
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    DB_HOST: str
    POSTGRES_PORT: str
    MONGO_DB: str
    MONGO_HOST: str
    MONGO_PORT: str
    MONGO_USER: str
    MONGO_PASSWORD: str
    URL_HISTORIQUE: str
    URL_STREAM: str

SETTINGS: Settings = {
    "POSTGRES_DB": os.environ.get("POSTGRES_DB", "default_db"),
    "POSTGRES_USER": os.environ.get("POSTGRES_USER", "default_user"),
    "POSTGRES_PASSWORD": os.environ.get("POSTGRES_PASSWORD", "default_password"),
    "DB_HOST": os.environ.get("DB_HOST", "localhost"),
    "POSTGRES_PORT": os.environ.get("POSTGRES_PORT", "5432"),
    "MONGO_DB": os.environ.get("MONGO_DB", "default_mongo_db"),
    "MONGO_HOST": os.environ.get("MONGO_HOST", "localhost"),
    "MONGO_PORT": os.environ.get("MONGO_PORT", "27017"),
    "MONGO_USER": os.environ.get("MONGO_USER", "default_mongo_user"),
    "MONGO_PASSWORD": os.environ.get("MONGO_PASSWORD", "default_mongo_password"),
    "URL_HISTORIQUE": os.environ.get("URL_HISTORIQUE", "https://api.binance.com/api/v3/klines"),
    "URL_STREAM": os.environ.get("URL_STREAM", "wss://stream.binance.com:9443/ws"),
}