"""FastAPI application for cryptocurrency data API."""
import logging
import sys
import os
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pymongo.database import Database

# Add src directory to Python path to allow imports
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from data.config import SETTINGS
from api.queries import (
  get_symbols,
  get_intervals,
  get_historical_data_query,
  get_latest_data,
  get_aggregated_stats
)
from api.models import (
  HistoricalDataResponse,
  StatsResponse,
  SymbolsResponse,
  IntervalsResponse,
  HealthResponse
)

# Configure logging
logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CRYPTO_API")

# Global database connection
mongo_client: Optional[MongoClient] = None
mongo_db: Optional[Database] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
  """Lifespan context manager for database connections."""
  global mongo_client, mongo_db

  # Startup: Connect to MongoDB
  try:
    db_name = SETTINGS["MONGO_DB"]
    host = SETTINGS["MONGO_HOST"]
    port = int(SETTINGS["MONGO_PORT"])
    user = SETTINGS.get("MONGO_USER", "")
    password = SETTINGS.get("MONGO_PASSWORD", "")

    if user and password:
      mongo_uri = f"mongodb://{user}:{password}@{host}:{port}/"
      mongo_client = MongoClient(mongo_uri)
    else:
      mongo_client = MongoClient(host=host, port=port)

    mongo_db = mongo_client[db_name]

    # Test connection
    mongo_db.list_collection_names()
    logger.info(f"Connected to MongoDB at {host}:{port}, database: {db_name}")

  except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

  yield

  # Shutdown: Close MongoDB connection
  if mongo_client:
    mongo_client.close()
    logger.info("Closed MongoDB connection")


# Create FastAPI app
app = FastAPI(
  title="Cryptocurrency Data API",
  description="API to query historical cryptocurrency data from MongoDB",
  version="1.0.0",
  lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse)
async def root():
  """Root endpoint."""
  return {
    "status": "ok",
    "message": "Cryptocurrency Data API is running"
  }


@app.get("/health", response_model=HealthResponse)
async def health_check():
  """Health check endpoint."""
  try:
    if mongo_db is None:
      raise HTTPException(status_code=503, detail="Database not connected")

    # Test database connection
    mongo_db.list_collection_names()

    return {
      "status": "healthy",
      "message": "All services are operational"
    }
  except Exception as e:
    logger.error(f"Health check failed: {e}")
    raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.get("/api/symbols", response_model=SymbolsResponse)
async def get_available_symbols():
  """Get list of available cryptocurrency symbols."""
  try:
    if mongo_db is None:
      raise HTTPException(status_code=503, detail="Database not connected")

    symbols = get_symbols(mongo_db)
    return {"symbols": symbols}

  except Exception as e:
    logger.error(f"Error fetching symbols: {e}")
    raise HTTPException(status_code=500, detail=f"Error fetching symbols: {str(e)}")


@app.get("/api/intervals", response_model=IntervalsResponse)
async def get_available_intervals():
  """Get list of available time intervals."""
  try:
    if mongo_db is None:
      raise HTTPException(status_code=503, detail="Database not connected")

    intervals = get_intervals(mongo_db)
    return {"intervals": intervals}

  except Exception as e:
    logger.error(f"Error fetching intervals: {e}")
    raise HTTPException(status_code=500, detail=f"Error fetching intervals: {str(e)}")


@app.get("/api/historical/{symbol}", response_model=List[HistoricalDataResponse])
async def get_historical_data(
        symbol: str,
        interval: str = Query("1d", description="Time interval (e.g., '1d', '1h')"),
        start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
        end_time: Optional[str] = Query(None, description="End time (ISO format)"),
        limit: int = Query(1000, ge=1, le=10000, description="Maximum number of records")
):
  """
  Get historical data for a specific symbol.

  - **symbol**: Cryptocurrency symbol (e.g., BTCUSDT)
  - **interval**: Time interval (default: 1d)
  - **start_time**: Start time in ISO format (optional)
  - **end_time**: End time in ISO format (optional)
  - **limit**: Maximum number of records to return (default: 1000, max: 10000)
  """
  try:
    if mongo_db is None:
      raise HTTPException(status_code=503, detail="Database not connected")

    # Parse datetime strings if provided
    start_dt = None
    end_dt = None

    if start_time:
      try:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
      except ValueError:
        raise HTTPException(status_code=400, detail="Invalid start_time format. Use ISO format.")

    if end_time:
      try:
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
      except ValueError:
        raise HTTPException(status_code=400, detail="Invalid end_time format. Use ISO format.")

    # Query data
    data = get_historical_data_query(
      db=mongo_db,
      symbol=symbol,
      interval=interval,
      start_time=start_dt,
      end_time=end_dt,
      limit=limit
    )

    if not data:
      raise HTTPException(
        status_code=404,
        detail=f"No data found for symbol {symbol} with interval {interval}"
      )

    return data

  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"Error fetching historical data: {e}")
    raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")


@app.get("/api/latest/{symbol}", response_model=List[HistoricalDataResponse])
async def get_latest(
        symbol: str,
        interval: str = Query("1d", description="Time interval (e.g., '1d', '1h')"),
        count: int = Query(30, ge=1, le=365, description="Number of recent records")
):
  """
  Get the most recent data for a specific symbol.

  - **symbol**: Cryptocurrency symbol (e.g., BTCUSDT)
  - **interval**: Time interval (default: 1d)
  - **count**: Number of recent records to return (default: 30, max: 365)
  """
  try:
    if mongo_db is None:
      raise HTTPException(status_code=503, detail="Database not connected")

    data = get_latest_data(
      db=mongo_db,
      symbol=symbol,
      interval=interval,
      count=count
    )

    if not data:
      raise HTTPException(
        status_code=404,
        detail=f"No data found for symbol {symbol} with interval {interval}"
      )

    return data

  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"Error fetching latest data: {e}")
    raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")


@app.get("/api/stats/{symbol}", response_model=StatsResponse)
async def get_statistics(
        symbol: str,
        interval: str = Query("1d", description="Time interval (e.g., '1d', '1h')"),
        start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
        end_time: Optional[str] = Query(None, description="End time (ISO format)")
):
  """
  Get aggregated statistics for a specific symbol.

  - **symbol**: Cryptocurrency symbol (e.g., BTCUSDT)
  - **interval**: Time interval (default: 1d)
  - **start_time**: Start time in ISO format (optional)
  - **end_time**: End time in ISO format (optional)
  """
  try:
    if mongo_db is None:
      raise HTTPException(status_code=503, detail="Database not connected")

    # Parse datetime strings if provided
    start_dt = None
    end_dt = None

    if start_time:
      try:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
      except ValueError:
        raise HTTPException(status_code=400, detail="Invalid start_time format. Use ISO format.")

    if end_time:
      try:
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
      except ValueError:
        raise HTTPException(status_code=400, detail="Invalid end_time format. Use ISO format.")

    # Get statistics
    stats = get_aggregated_stats(
      db=mongo_db,
      symbol=symbol,
      interval=interval,
      start_time=start_dt,
      end_time=end_dt
    )

    if stats.get("count", 0) == 0:
      raise HTTPException(
        status_code=404,
        detail=f"No data found for symbol {symbol} with interval {interval}"
      )

    return stats

  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"Error fetching statistics: {e}")
    raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")


if __name__ == "__main__":
  import uvicorn

  uvicorn.run(app, host="0.0.0.0", port=8000)
