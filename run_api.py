#!/usr/bin/env python3
"""Script to run the FastAPI application."""
import sys
import os

# Add src directory to Python path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if src_dir not in sys.path:
  sys.path.insert(0, src_dir)

if __name__ == "__main__":
  import uvicorn

  # Run the FastAPI app
  uvicorn.run(
    "api.app:app",
    host="0.0.0.0",
    port=8000,
    reload=True,  # Enable auto-reload during development
    log_level="info"
  )
