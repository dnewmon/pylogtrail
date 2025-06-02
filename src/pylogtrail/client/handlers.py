import logging
import logging.handlers
from typing import Dict, Any, Optional
import json
import pickle
import socket
import struct


class PyLogTrailHTTPHandler(logging.handlers.HTTPHandler):
    """
    A custom HTTP handler that sends log records to a PyLogTrail server endpoint.
    Supports additional metadata through URL parameters.
    """

    def __init__(
        self,
        host: str,
        url: str = "/log",
        method: str = "POST",
        metadata: Optional[Dict[str, Any]] = None,
        secure: bool = False,
        credentials: Optional[tuple[str, str]] = None,
        context: Optional[Any] = None,
    ):
        """
        Initialize the handler.

        Args:
            host: The host to send logs to (e.g., 'localhost:5000')
            url: The URL path to send logs to (default: '/log')
            method: The HTTP method to use (default: 'POST')
            metadata: Optional dictionary of metadata to include in URL parameters
            secure: Whether to use HTTPS (default: False)
            credentials: Optional tuple of (username, password) for basic auth
            context: Optional SSL context for HTTPS connections
        """
        super().__init__(host, url, method, secure, credentials, context)
        self.metadata = metadata or {}

    def mapLogRecord(self, record: logging.LogRecord) -> Dict[str, Any]:
        """
        Convert the log record to a dictionary format expected by the server.
        Includes any additional metadata in the JSON payload.
        """

        # Get the base record data
        data = {
            "created": record.created,
            "levelname": record.levelname,
            "msg": record.getMessage(),
            "name": record.name,
            "pathname": record.pathname,
            "lineno": record.lineno,
            "args": record.args,
            "exc_info": record.exc_info,
            "funcName": record.funcName,
        }

        # Add any additional attributes from the record
        for key, value in record.__dict__.items():
            if key not in data and not key.startswith("_"):
                data[key] = value

        # Add metadata to the JSON payload
        data.update(self.metadata)

        return data


def create_http_handler(
    host: str,
    url: str = "/log",
    metadata: Optional[Dict[str, Any]] = None,
    secure: bool = False,
    credentials: Optional[tuple[str, str]] = None,
    level: int = logging.NOTSET,
) -> PyLogTrailHTTPHandler:
    """
    Create and configure a PyLogTrail HTTP handler.

    Args:
        host: The host to send logs to (e.g., 'localhost:5000')
        url: The URL path to send logs to (default: '/log')
        metadata: Optional dictionary of metadata to include in URL parameters
        secure: Whether to use HTTPS (default: False)
        credentials: Optional tuple of (username, password) for basic auth
        level: The logging level for this handler (default: INFO)

    Returns:
        A configured PyLogTrailHTTPHandler instance
    """
    handler = PyLogTrailHTTPHandler(
        host=host,
        url=url,
        metadata=metadata,
        secure=secure,
        credentials=credentials,
    )
    handler.setLevel(level)
    return handler


class PyLogTrailContext:
    """
    A generic context manager that temporarily adds a PyLogTrail handler to a specified logger.
    The handler is automatically removed when exiting the context.
    
    This is the base class for specific context managers like HTTP and UDP.
    """

    def __init__(self, handler: logging.Handler, logger: Optional[logging.Logger] = None):
        """
        Initialize the context manager.

        Args:
            handler: The logging handler to add/remove
            logger: The logger to attach the handler to (default: root logger)
        """
        self.handler = handler
        self.logger = logger or logging.root

    def __enter__(self) -> None:
        """Add the PyLogTrail handler to the logger when entering the context."""
        self.logger.addHandler(self.handler)
        return None

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Remove the PyLogTrail handler from the logger when exiting the context."""
        self.logger.removeHandler(self.handler)
        self.handler.flush()
        self.handler.close()


class PyLogTrailHTTPContext(PyLogTrailContext):
    """
    A context manager that temporarily adds a PyLogTrail HTTP handler to a logger.
    The handler is automatically removed when exiting the context.

    Example:
        with PyLogTrailHTTPContext('localhost:5000', metadata={'app': 'myapp'}):
            # All logging during this block will be sent to the PyLogTrail server
            logging.info('This will be sent to PyLogTrail')
    """

    def __init__(
        self,
        host: str,
        url: str = "/log",
        metadata: Optional[Dict[str, Any]] = None,
        secure: bool = False,
        credentials: Optional[tuple[str, str]] = None,
        level: int = logging.NOTSET,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the HTTP context logger.

        Args:
            host: The host to send logs to (e.g., 'localhost:5000')
            url: The URL path to send logs to (default: '/log')
            metadata: Optional dictionary of metadata to include in URL parameters
            secure: Whether to use HTTPS (default: False)
            credentials: Optional tuple of (username, password) for basic auth
            level: The logging level for this handler (default: NOTSET)
            logger: The logger to attach the handler to (default: root logger)
        """
        handler = create_http_handler(
            host=host,
            url=url,
            metadata=metadata,
            secure=secure,
            credentials=credentials,
            level=level,
        )
        super().__init__(handler, logger)


class PyLogTrailUDPHandler(logging.Handler):
    """
    A custom UDP handler that sends log records to a PyLogTrail UDP server.
    Supports additional metadata by adding attributes to the log record.
    Uses the same protocol as Python's logging.handlers.DatagramHandler.
    """

    def __init__(
        self,
        host: str,
        port: int = 9999,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the UDP handler.

        Args:
            host: The host to send logs to (e.g., 'localhost')
            port: The port to send logs to (default: 9999)
            metadata: Optional dictionary of metadata to include as record attributes
        """
        super().__init__()
        self.host = host
        self.port = port
        self.metadata = metadata or {}
        self.socket = None

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record by sending it to the UDP server.
        """
        try:
            # Add metadata to the record
            for key, value in self.metadata.items():
                setattr(record, key, value)

            # Pickle the record
            pickled_record = pickle.dumps(record)
            
            # Create the packet with length prefix (same format as DatagramHandler)
            packet = struct.pack(">L", len(pickled_record)) + pickled_record
            
            # Send via UDP
            self._send_packet(packet)
            
        except Exception as e:
            self.handleError(record)

    def _send_packet(self, packet: bytes) -> None:
        """
        Send a packet to the UDP server.
        Creates a new socket for each send to avoid connection state issues.
        """
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(packet, (self.host, self.port))
        finally:
            if sock:
                sock.close()

    def close(self) -> None:
        """
        Close the handler and clean up resources.
        """
        super().close()


def create_udp_handler(
    host: str,
    port: int = 9999,
    metadata: Optional[Dict[str, Any]] = None,
    level: int = logging.NOTSET,
) -> PyLogTrailUDPHandler:
    """
    Create and configure a PyLogTrail UDP handler.

    Args:
        host: The host to send logs to (e.g., 'localhost')
        port: The port to send logs to (default: 9999)
        metadata: Optional dictionary of metadata to include as record attributes
        level: The logging level for this handler (default: NOTSET)

    Returns:
        A configured PyLogTrailUDPHandler instance
    """
    handler = PyLogTrailUDPHandler(
        host=host,
        port=port,
        metadata=metadata,
    )
    handler.setLevel(level)
    return handler


class PyLogTrailUDPContext(PyLogTrailContext):
    """
    A context manager that temporarily adds a PyLogTrail UDP handler to a logger.
    The handler is automatically removed when exiting the context.

    Example:
        with PyLogTrailUDPContext('localhost', metadata={'app': 'myapp'}):
            # All logging during this block will be sent to the PyLogTrail UDP server
            logging.info('This will be sent to PyLogTrail via UDP')
    """

    def __init__(
        self,
        host: str,
        port: int = 9999,
        metadata: Optional[Dict[str, Any]] = None,
        level: int = logging.NOTSET,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the UDP context logger.

        Args:
            host: The host to send logs to (e.g., 'localhost')
            port: The port to send logs to (default: 9999)
            metadata: Optional dictionary of metadata to include as record attributes
            level: The logging level for this handler (default: NOTSET)
            logger: The logger to attach the handler to (default: root logger)
        """
        handler = create_udp_handler(
            host=host,
            port=port,
            metadata=metadata,
            level=level,
        )
        super().__init__(handler, logger)
