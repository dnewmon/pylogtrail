import pytest
import json
from datetime import datetime, timezone, timedelta
from io import StringIO
from pylogtrail.server.download_api import parse_timeframe, flatten_metadata, logs_to_csv
from pylogtrail.db.models import LogEntry, LogLevel


class TestParseTimeframe:
    """Test cases for timeframe parsing function."""
    
    def test_relative_days(self):
        """Test parsing relative day formats."""
        now = datetime.now(timezone.utc)
        
        result = parse_timeframe("3d")
        expected = now - timedelta(days=3)
        assert abs((result - expected).total_seconds()) < 10
        
        result = parse_timeframe("7days")
        expected = now - timedelta(days=7)
        assert abs((result - expected).total_seconds()) < 10
    
    def test_relative_weeks(self):
        """Test parsing relative week formats."""
        now = datetime.now(timezone.utc)
        
        result = parse_timeframe("2w")
        expected = now - timedelta(weeks=2)
        assert abs((result - expected).total_seconds()) < 10
        
        result = parse_timeframe("1week")
        expected = now - timedelta(weeks=1)
        assert abs((result - expected).total_seconds()) < 10
    
    def test_relative_hours(self):
        """Test parsing relative hour formats."""
        now = datetime.now(timezone.utc)
        
        result = parse_timeframe("6h")
        expected = now - timedelta(hours=6)
        assert abs((result - expected).total_seconds()) < 10
        
        result = parse_timeframe("24hours")
        expected = now - timedelta(hours=24)
        assert abs((result - expected).total_seconds()) < 10
    
    def test_relative_months(self):
        """Test parsing relative month formats."""
        now = datetime.now(timezone.utc)
        
        result = parse_timeframe("1m")
        expected = now - timedelta(days=30)
        assert abs((result - expected).total_seconds()) < 10
        
        result = parse_timeframe("3months")
        expected = now - timedelta(days=90)
        assert abs((result - expected).total_seconds()) < 10
    
    def test_iso_format(self):
        """Test parsing ISO format timestamps."""
        # Test with timezone
        iso_str = "2023-06-01T12:00:00+00:00"
        result = parse_timeframe(iso_str)
        expected = datetime(2023, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert result == expected
        
        # Test with Z suffix
        iso_str = "2023-06-01T12:00:00Z"
        result = parse_timeframe(iso_str)
        expected = datetime(2023, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert result == expected
    
    def test_invalid_formats(self):
        """Test invalid timeframe formats."""
        assert parse_timeframe("invalid") is None
        assert parse_timeframe("") is None
        assert parse_timeframe("xyz123") is None
        assert parse_timeframe("123") is None


class TestFlattenMetadata:
    """Test cases for metadata flattening function."""
    
    def test_simple_metadata(self):
        """Test flattening simple metadata."""
        metadata = {
            "service": "myapp",
            "version": "1.0.0",
            "environment": "production"
        }
        
        result = flatten_metadata(metadata)
        expected = {
            "service": "myapp",
            "version": "1.0.0",
            "environment": "production"
        }
        
        assert result == expected
    
    def test_nested_metadata(self):
        """Test flattening nested metadata."""
        metadata = {
            "service": "myapp",
            "environment": {
                "type": "production",
                "region": "us-east-1",
                "config": {
                    "debug": False,
                    "timeout": 30
                }
            }
        }
        
        result = flatten_metadata(metadata)
        expected = {
            "service": "myapp",
            "environment.type": "production",
            "environment.region": "us-east-1",
            "environment.config.debug": "False",
            "environment.config.timeout": "30"
        }
        
        assert result == expected
    
    def test_list_metadata(self):
        """Test flattening metadata with lists."""
        metadata = {
            "tags": ["web", "api", "production"],
            "ports": [80, 443, 8080],
            "features": {
                "enabled": ["auth", "logging"],
                "disabled": ["debug"]
            }
        }
        
        result = flatten_metadata(metadata)
        expected = {
            "tags": "web,api,production",
            "ports": "80,443,8080",
            "features.enabled": "auth,logging",
            "features.disabled": "debug"
        }
        
        assert result == expected
    
    def test_empty_metadata(self):
        """Test handling empty or None metadata."""
        assert flatten_metadata(None) == {}
        assert flatten_metadata({}) == {}


class TestLogsToCSV:
    """Test cases for CSV conversion function."""
    
    def test_empty_logs(self):
        """Test CSV conversion with empty log list."""
        result = logs_to_csv([])
        lines = result.strip().split('\n')
        assert len(lines) == 1  # Only header
        assert 'id,timestamp,datetime,name,level' in lines[0]
    
    def test_basic_logs(self):
        """Test CSV conversion with basic log entries."""
        timestamp = datetime.now(timezone.utc).timestamp()
        logs = [
            LogEntry(
                id=1,
                timestamp=timestamp,
                name="test.logger",
                level=LogLevel.INFO,
                msg="Test message",
                pathname="/path/to/file.py",
                lineno=42,
                func="test_function",
                args=None,
                exc_info=None,
                extra_metadata=None
            )
        ]
        
        result = logs_to_csv(logs)
        lines = result.strip().split('\n')
        
        # Check that we have header + 1 data row
        assert len(lines) == 2
        
        # Check header contains expected columns
        header = lines[0]
        expected_cols = ['id', 'timestamp', 'datetime', 'name', 'level', 'pathname', 'lineno', 'msg']
        for col in expected_cols:
            assert col in header
        
        # Check data row
        data_row = lines[1].split(',')
        assert data_row[0] == '1'  # id
        assert data_row[3] == 'test.logger'  # name
        assert data_row[4] == 'INFO'  # level
    
    def test_logs_with_metadata(self):
        """Test CSV conversion with metadata."""
        timestamp = datetime.now(timezone.utc).timestamp()
        logs = [
            LogEntry(
                id=1,
                timestamp=timestamp,
                name="test.logger",
                level=LogLevel.ERROR,
                msg="Error message",
                args=None,
                exc_info=None,
                pathname=None,
                lineno=None,
                func=None,
                extra_metadata={
                    "service": "web",
                    "environment": {"type": "prod", "region": "us-east-1"},
                    "tags": ["critical", "backend"]
                }
            ),
            LogEntry(
                id=2,
                timestamp=timestamp + 1,
                name="test.api",
                level=LogLevel.INFO,
                msg="API call",
                args=None,
                exc_info=None,
                pathname=None,
                lineno=None,
                func=None,
                extra_metadata={
                    "service": "api",
                    "user_id": 12345
                }
            )
        ]
        
        result = logs_to_csv(logs)
        lines = result.strip().split('\n')
        
        # Check that we have header + 2 data rows
        assert len(lines) == 3
        
        # Check header includes metadata columns
        header = lines[0]
        assert 'metadata.service' in header
        assert 'metadata.environment.type' in header
        assert 'metadata.environment.region' in header
        assert 'metadata.tags' in header
        assert 'metadata.user_id' in header
        
        # Check that metadata columns are sorted
        metadata_cols = [col for col in header.split(',') if col.startswith('metadata.')]
        assert metadata_cols == sorted(metadata_cols)
    
    def test_logs_with_args_and_exc_info(self):
        """Test CSV conversion with args and exception info."""
        timestamp = datetime.now(timezone.utc).timestamp()
        logs = [
            LogEntry(
                id=1,
                timestamp=timestamp,
                name="test.logger",
                level=LogLevel.ERROR,
                msg="Error with args",
                pathname=None,
                lineno=None,
                func=None,
                args=["arg1", "arg2", 123],
                exc_info="Traceback (most recent call last):\n  File...",
                extra_metadata=None
            )
        ]
        
        result = logs_to_csv(logs)
        lines = result.strip().split('\n')
        
        # Parse CSV properly to handle quoted fields
        import csv
        csv_reader = csv.reader(StringIO(result))
        rows = list(csv_reader)
        
        assert len(rows) == 2  # header + 1 data row
        
        # Find the args column
        header = rows[0]
        args_idx = header.index('args')
        data_row = rows[1]
        
        # Args should be JSON encoded
        args_data = json.loads(data_row[args_idx])
        assert args_data == ["arg1", "arg2", 123]
        
        # Find exc_info column
        exc_info_idx = header.index('exc_info')
        assert "Traceback" in data_row[exc_info_idx]