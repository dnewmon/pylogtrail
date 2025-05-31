"""
Unit tests for pylogtrail.client.handlers module.
"""
import json
import logging
import unittest.mock
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock

import pytest

from pylogtrail.client.handlers import (
    PyLogTrailHTTPHandler,
    create_http_handler,
    PyLogTrailContext,
)


class TestPyLogTrailHTTPHandler:
    """Test cases for PyLogTrailHTTPHandler class."""

    def test_init_default_values(self):
        """Test handler initialization with default values."""
        handler = PyLogTrailHTTPHandler("localhost:5000")
        
        assert handler.host == "localhost:5000"
        assert handler.url == "/log"
        assert handler.method == "POST"
        assert handler.metadata == {}
        assert handler.secure is False

    def test_init_custom_values(self):
        """Test handler initialization with custom values."""
        metadata = {"app": "test", "version": "1.0"}
        credentials = ("user", "pass")
        
        handler = PyLogTrailHTTPHandler(
            host="example.com:8080",
            url="/api/logs",
            method="GET",
            metadata=metadata,
            secure=True,
            credentials=credentials,
        )
        
        assert handler.host == "example.com:8080"
        assert handler.url == "/api/logs"
        assert handler.method == "GET"
        assert handler.metadata == metadata
        assert handler.secure is True
        assert handler.credentials == credentials

    def test_mapLogRecord_basic(self, capfd):
        """Test mapLogRecord with basic log record."""
        handler = PyLogTrailHTTPHandler("localhost:5000")
        
        # Create a mock log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_function",
        )
        record.created = 1234567890.0
        
        result = handler.mapLogRecord(record)
        
        # Verify basic fields are mapped correctly
        assert result["created"] == 1234567890.0
        assert result["levelname"] == "INFO"
        assert result["msg"] == "Test message"
        assert result["name"] == "test.logger"
        assert result["pathname"] == "/path/to/file.py"
        assert result["lineno"] == 42
        assert result["args"] == ()
        assert result["exc_info"] is None
        assert result["funcName"] == "test_function"

    def test_mapLogRecord_with_metadata(self, capfd):
        """Test mapLogRecord includes metadata in result."""
        metadata = {"app": "test_app", "environment": "dev"}
        handler = PyLogTrailHTTPHandler("localhost:5000", metadata=metadata)
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.created = 1234567890.0
        
        result = handler.mapLogRecord(record)
        
        # Verify metadata is included
        assert result["app"] == "test_app"
        assert result["environment"] == "dev"

    def test_mapLogRecord_with_custom_attributes(self, capfd):
        """Test mapLogRecord includes custom attributes from log record."""
        handler = PyLogTrailHTTPHandler("localhost:5000")
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.created = 1234567890.0
        record.custom_field = "custom_value"
        record.user_id = 12345
        
        result = handler.mapLogRecord(record)
        
        # Verify custom attributes are included
        assert result["custom_field"] == "custom_value"
        assert result["user_id"] == 12345

    def test_mapLogRecord_excludes_private_attributes(self, capfd):
        """Test mapLogRecord excludes private attributes."""
        handler = PyLogTrailHTTPHandler("localhost:5000")
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.created = 1234567890.0
        record._private_field = "should_be_excluded"
        
        result = handler.mapLogRecord(record)
        
        # Verify private attributes are excluded
        assert "_private_field" not in result

    def test_mapLogRecord_formatted_message(self, capfd):
        """Test mapLogRecord with formatted message."""
        handler = PyLogTrailHTTPHandler("localhost:5000")
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Hello %s, you have %d messages",
            args=("Alice", 5),
            exc_info=None,
        )
        record.created = 1234567890.0
        
        result = handler.mapLogRecord(record)
        
        # Verify message is formatted correctly
        assert result["msg"] == "Hello Alice, you have 5 messages"


class TestCreateHttpHandler:
    """Test cases for create_http_handler function."""

    def test_create_with_defaults(self):
        """Test creating handler with default values."""
        handler = create_http_handler("localhost:5000")
        
        assert isinstance(handler, PyLogTrailHTTPHandler)
        assert handler.host == "localhost:5000"
        assert handler.url == "/log"
        assert handler.metadata == {}
        assert handler.level == logging.NOTSET

    def test_create_with_custom_values(self):
        """Test creating handler with custom values."""
        metadata = {"service": "api"}
        credentials = ("admin", "secret")
        
        handler = create_http_handler(
            host="api.example.com",
            url="/logs/ingest",
            metadata=metadata,
            secure=True,
            credentials=credentials,
            level=logging.WARNING,
        )
        
        assert isinstance(handler, PyLogTrailHTTPHandler)
        assert handler.host == "api.example.com"
        assert handler.url == "/logs/ingest"
        assert handler.metadata == metadata
        assert handler.secure is True
        assert handler.credentials == credentials
        assert handler.level == logging.WARNING


class TestPyLogTrailContext:
    """Test cases for PyLogTrailContext class."""

    def test_init(self):
        """Test context manager initialization."""
        metadata = {"app": "test"}
        
        context = PyLogTrailContext(
            host="localhost:5000",
            url="/api/log",
            metadata=metadata,
            secure=True,
            level=logging.DEBUG,
        )
        
        assert isinstance(context.handler, PyLogTrailHTTPHandler)
        assert context.handler.host == "localhost:5000"
        assert context.handler.url == "/api/log"
        assert context.handler.metadata == metadata
        assert context.handler.secure is True
        assert context.handler.level == logging.DEBUG
        assert context.root_logger is logging.root

    def test_enter_adds_handler(self):
        """Test that entering context adds handler to root logger."""
        context = PyLogTrailContext("localhost:5000")
        
        # Verify handler is not in root logger initially
        assert context.handler not in logging.root.handlers
        
        # Enter context
        context.__enter__()
        
        # Verify handler is added to root logger
        assert context.handler in logging.root.handlers
        
        # Clean up
        context.__exit__(None, None, None)

    def test_exit_removes_handler(self):
        """Test that exiting context removes handler from root logger."""
        context = PyLogTrailContext("localhost:5000")
        
        # Enter and then exit context
        context.__enter__()
        assert context.handler in logging.root.handlers
        
        with patch.object(context.handler, 'flush') as mock_flush, \
             patch.object(context.handler, 'close') as mock_close:
            
            context.__exit__(None, None, None)
            
            # Verify handler is removed and cleaned up
            assert context.handler not in logging.root.handlers
            mock_flush.assert_called_once()
            mock_close.assert_called_once()

    def test_context_manager_usage(self):
        """Test using context manager with 'with' statement."""
        metadata = {"test": "value"}
        
        with patch.object(logging.root, 'addHandler') as mock_add, \
             patch.object(logging.root, 'removeHandler') as mock_remove:
            
            with PyLogTrailContext("localhost:5000", metadata=metadata) as ctx:
                # Verify handler was added
                mock_add.assert_called_once()
                handler = mock_add.call_args[0][0]
                assert isinstance(handler, PyLogTrailHTTPHandler)
                assert handler.metadata == metadata
            
            # Verify handler was removed
            mock_remove.assert_called_once()

    def test_context_manager_with_exception(self):
        """Test context manager properly cleans up when exception occurs."""
        with patch.object(logging.root, 'addHandler'), \
             patch.object(logging.root, 'removeHandler') as mock_remove:
            
            try:
                with PyLogTrailContext("localhost:5000"):
                    raise ValueError("Test exception")
            except ValueError:
                pass
            
            # Verify handler was still removed despite exception
            mock_remove.assert_called_once()

    def test_enter_returns_none(self):
        """Test that __enter__ returns None."""
        context = PyLogTrailContext("localhost:5000")
        result = context.__enter__()
        
        assert result is None
        
        # Clean up
        context.__exit__(None, None, None)