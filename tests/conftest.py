"""
Test configuration and shared fixtures for Signa4 tests.
"""
import sys
import os
from pathlib import Path
import pytest

# Add the backend directory to the Python path so we can import signa4 modules
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

@pytest.fixture
def sample_data():
    """Fixture providing sample test data."""
    return {
        "test_string": "Hello, World!",
        "test_number": 42,
        "test_list": [1, 2, 3, 4, 5],
        "test_dict": {"key1": "value1", "key2": "value2"}
    }

@pytest.fixture
def mock_environment():
    """Fixture for setting up mock environment variables."""
    original_env = dict(os.environ)
    test_env = {
        "TESTING": "true",
        "FLASK_ENV": "testing"
    }
    os.environ.update(test_env)
    
    yield test_env
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)