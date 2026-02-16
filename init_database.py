#!/usr/bin/env python3
"""Script to create the PostgreSQL database if it doesn't exist."""
import sys
import os
from dotenv import load_dotenv
import psycopg
from psycopg import sql

# Load environment variables
load_dotenv()

POSTGRES_USER = os.getenv("POSTGRES_USER", "sep25opa1")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "sep25opa1")
POSTGRES_DB = os.getenv("POSTGRES_DB", "binance_data")
DB_HOST = os.getenv("DB_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5435"))


def create_database():
  """Create the PostgreSQL database if it doesn't exist."""
  print(f"Attempting to create database '{POSTGRES_DB}' on {DB_HOST}:{POSTGRES_PORT}...")

  try:
    # Connect to PostgreSQL server (to 'postgres' default database)
    # psycopg v3 uses connection string format
    conninfo = f"dbname=postgres user={POSTGRES_USER} password={POSTGRES_PASSWORD} host={DB_HOST} port={POSTGRES_PORT}"

    # Use context manager with autocommit=True for database creation
    with psycopg.connect(conninfo, autocommit=True) as conn:
      with conn.cursor() as cursor:
        # Check if database exists
        cursor.execute(
          "SELECT 1 FROM pg_database WHERE datname = %s",
          (POSTGRES_DB,)
        )
        exists = cursor.fetchone()

        if exists:
          print(f"✓ Database '{POSTGRES_DB}' already exists.")
        else:
          # Create database using sql.Identifier to prevent SQL injection
          cursor.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(POSTGRES_DB))
          )
          print(f"✓ Database '{POSTGRES_DB}' created successfully!")

    # Test connection to new database
    print(f"\nTesting connection to '{POSTGRES_DB}'...")
    test_conninfo = f"dbname={POSTGRES_DB} user={POSTGRES_USER} password={POSTGRES_PASSWORD} host={DB_HOST} port={POSTGRES_PORT}"

    with psycopg.connect(test_conninfo) as test_conn:
      print(f"✓ Successfully connected to database '{POSTGRES_DB}'!")

    return True

  except psycopg.OperationalError as e:
    print(f"✗ Connection error: {e}")
    print(f"\nPossible issues:")
    print(f"  1. PostgreSQL server is not running")
    print(f"  2. Wrong host/port: {DB_HOST}:{POSTGRES_PORT}")
    print(f"  3. Wrong credentials: {POSTGRES_USER}/{POSTGRES_PASSWORD}")
    print(f"\nTo check if PostgreSQL is running:")
    print(f"  docker ps | grep postgres")
    return False

  except Exception as e:
    print(f"✗ Error: {e}")
    return False


if __name__ == "__main__":
  print("=" * 60)
  print("PostgreSQL Database Initialization")
  print("=" * 60)
  print(f"Host: {DB_HOST}")
  print(f"Port: {POSTGRES_PORT}")
  print(f"User: {POSTGRES_USER}")
  print(f"Database: {POSTGRES_DB}")
  print("=" * 60)
  print()

  success = create_database()

  if success:
    print("\n✅ Database initialization complete!")
    print(f"\nConnection string:")
    print(f"  postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    sys.exit(0)
  else:
    print("\n❌ Database initialization failed!")
    sys.exit(1)
