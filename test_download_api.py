#!/usr/bin/env python3
"""
Simple test script for the download API functionality.
"""

import os
import sys
import tempfile
import json
from datetime import datetime, timezone, timedelta

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pylogtrail.server.download_api import parse_timeframe, flatten_metadata, logs_to_csv
from pylogtrail.db.models import LogEntry, LogLevel


def test_parse_timeframe():
    """Test the timeframe parsing function."""
    print("Testing parse_timeframe...")
    
    # Test relative formats
    now = datetime.now(timezone.utc)
    
    # Test days
    result = parse_timeframe("3d")
    expected = now - timedelta(days=3)
    assert abs((result - expected).total_seconds()) < 10, f"3d failed: {result} vs {expected}"
    
    result = parse_timeframe("7days")
    expected = now - timedelta(days=7)
    assert abs((result - expected).total_seconds()) < 10, f"7days failed"
    
    # Test weeks
    result = parse_timeframe("2w")
    expected = now - timedelta(weeks=2)
    assert abs((result - expected).total_seconds()) < 10, f"2w failed"
    
    # Test hours
    result = parse_timeframe("6h")
    expected = now - timedelta(hours=6)
    assert abs((result - expected).total_seconds()) < 10, f"6h failed"
    
    # Test invalid format
    result = parse_timeframe("invalid")
    assert result is None, "Invalid format should return None"
    
    print("✓ parse_timeframe tests passed")


def test_flatten_metadata():
    """Test metadata flattening function."""
    print("Testing flatten_metadata...")
    
    # Test nested metadata
    metadata = {
        "service": "myapp",
        "version": "1.0.0",
        "environment": {
            "type": "production",
            "region": "us-east-1"
        },
        "tags": ["web", "api"],
        "numbers": [1, 2, 3]
    }
    
    result = flatten_metadata(metadata)
    expected = {
        "service": "myapp",
        "version": "1.0.0",
        "environment.type": "production",
        "environment.region": "us-east-1",
        "tags": "web,api",
        "numbers": "1,2,3"
    }
    
    assert result == expected, f"Flattening failed: {result} vs {expected}"
    
    # Test empty metadata
    result = flatten_metadata(None)
    assert result == {}, "None metadata should return empty dict"
    
    result = flatten_metadata({})
    assert result == {}, "Empty metadata should return empty dict"
    
    print("✓ flatten_metadata tests passed")


def test_logs_to_csv():
    """Test CSV conversion function."""
    print("Testing logs_to_csv...")
    
    # Create sample log entries
    base_timestamp = datetime.now(timezone.utc).timestamp()
    logs = [
        LogEntry(
            id=1,
            timestamp=base_timestamp,
            name="test.logger",
            level=LogLevel.INFO,
            msg="Test message 1",
            pathname="/path/to/file.py",
            lineno=42,
            func="test_function",
            args=None,
            exc_info=None,
            extra_metadata={"service": "web", "version": "1.0"}
        ),
        LogEntry(
            id=2,
            timestamp=base_timestamp + 1,
            name="test.logger",
            level=LogLevel.ERROR,
            msg="Test message 2",
            pathname=None,
            lineno=None,
            func=None,
            args=None,
            exc_info=None,
            extra_metadata={"service": "api", "env": {"type": "prod"}}
        )
    ]
    
    csv_content = logs_to_csv(logs)
    lines = csv_content.strip().split('\n')
    
    # Check header
    header = lines[0]
    expected_cols = ['id', 'timestamp', 'datetime', 'name', 'level', 'pathname', 'lineno', 'msg', 'args', 'exc_info', 'func']
    assert all(col in header for col in expected_cols), f"Missing expected columns in header: {header}"
    
    # Check metadata columns
    assert 'metadata.service' in header, "Metadata columns not found"
    
    # Check data rows
    assert len(lines) == 3, f"Expected 3 lines (header + 2 data), got {len(lines)}"
    
    print("✓ logs_to_csv tests passed")


def main():
    """Run all tests."""
    try:
        test_parse_timeframe()
        test_flatten_metadata()
        test_logs_to_csv()
        print("\n✅ All tests passed!")
        return 0
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())