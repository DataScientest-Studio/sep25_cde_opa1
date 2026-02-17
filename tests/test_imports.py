import pytest
import os
import sys

# Add src directory to Python path
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(test_dir)
src_dir = os.path.join(project_root, 'src')

if src_dir not in sys.path:
    sys.path.insert(0, src_dir)


def test_import_data_modules():
    """Vérifie que les modules de données peuvent être importés"""
    try:
        from data import config
        from data import historical_data
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import data modules: {e}")


def test_import_api_modules():
    """Vérifie que les modules API peuvent être importés"""
    try:
        from api import models
        from api import queries
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import API modules: {e}")


def test_python_version():
    """Vérifie que Python >= 3.12 est utilisé"""
    import sys
    assert sys.version_info >= (3, 12), f"Python 3.12+ required, got {sys.version_info}"


def test_required_packages():
    """Vérifie que les packages requis sont installés"""
    try:
        import fastapi
        import pymongo
        import pandas
        import numpy
        import requests
        assert True
    except ImportError as e:
        pytest.fail(f"Missing required package: {e}")

