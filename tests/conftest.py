"""
Test configuration and shared fixtures for pylogtrail tests.
"""
import sys
from pathlib import Path

# Add src directory to Python path so imports work without package installation
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
