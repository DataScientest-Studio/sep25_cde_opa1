import os
import sys

# Add src directory to Python path to allow imports
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(test_dir)
src_dir = os.path.join(project_root, 'src')

if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from data.config import SETTINGS


def test_settings_exist():
  """Vérifie que les settings sont chargés"""
  assert SETTINGS is not None
  assert isinstance(SETTINGS, dict)


def test_mongo_config():
  """Vérifie que les variables MongoDB sont définies"""
  assert 'MONGO_HOST' in SETTINGS
  assert 'MONGO_PORT' in SETTINGS
  assert 'MONGO_DB' in SETTINGS
  assert SETTINGS['MONGO_DB'] is not None


def test_collection_names():
  """Vérifie que les noms de collections sont définis"""
  assert 'MONGO_COLLECTION_HISTORICAL' in SETTINGS
  assert 'MONGO_COLLECTION_STREAMING' in SETTINGS
  assert SETTINGS['MONGO_COLLECTION_HISTORICAL'] == 'historical_daily_data'
  assert SETTINGS['MONGO_COLLECTION_STREAMING'] == 'streaming_trades'
