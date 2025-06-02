import logging
import pickle
import socket
import struct
import threading
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from pylogtrail.db.session import get_db_session
from pylogtrail.db.models import LogEntry, LogLevel


class UDPLogHandler:
    """
    UDP server that accepts log records from Python's logging.handlers.DatagramHandler.
    The DatagramHandler sends pickled LogRecord objects over UDP.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 9999,
        broadcast_callback: Optional[Callable[[LogEntry], None]] = None,
    ):
        """
        Initialize the UDP log handler.

        Args:
            host: The host to bind to (default: "0.0.0.0")
            port: The port to listen on (default: 9999)
            broadcast_callback: Optional callback function to broadcast logs (dependency injection)
        """
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.logger = logging.getLogger(__name__)
        self.broadcast_callback = broadcast_callback

    def start(self) -> None:
        """Start the UDP server in a background thread."""
        if self.running:
            self.logger.warning("UDP handler is already running")
            return

        try:
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))

            self.running = True
            self.thread = threading.Thread(target=self._listen, daemon=True)
            self.thread.start()

            self.logger.info(f"UDP log handler started on {self.host}:{self.port}")

        except Exception as e:
            self.logger.error(f"Failed to start UDP handler: {e}")
            self.running = False
            if self.socket:
                self.socket.close()
                self.socket = None
            raise

    def stop(self) -> None:
        """Stop the UDP server."""
        if not self.running:
            return

        self.running = False

        if self.socket:
            self.socket.close()
            self.socket = None

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)

        self.logger.info("UDP log handler stopped")

    def _listen(self) -> None:
        """Main loop to listen for incoming UDP packets."""
        while self.running and self.socket:
            try:
                # Receive data from client
                data, addr = self.socket.recvfrom(65535)  # Max UDP packet size
                self.logger.info(f"Received data from {addr}: {len(data)} bytes")
                self._process_log_data(data, addr)

            except socket.error as e:
                if self.running:  # Only log if we're supposed to be running
                    self.logger.error(f"Socket error in UDP handler: {e}")
                break
            except Exception as e:
                self.logger.error(f"Error processing UDP log data: {e}")

        self.logger.info("UDP log handler stopped")

    def _process_log_data(self, data: bytes, addr: tuple) -> None:
        """
        Process incoming log data from DatagramHandler.

        Args:
            data: The raw UDP packet data
            addr: The client address (host, port)
        """
        try:
            # DatagramHandler sends the record length as a 4-byte integer,
            # followed by the pickled LogRecord
            if len(data) < 4:
                self.logger.warning(f"Received malformed packet from {addr}: too short")
                return

            # Unpack the length (first 4 bytes, big-endian)
            record_length = struct.unpack(">L", data[:4])[0]

            # Extract the pickled record
            if len(data) < record_length + 4:
                self.logger.warning(
                    f"Received malformed packet from {addr}: length mismatch: {len(data)} >= {record_length + 4}"
                )
                return

            pickled_record = data[4 : record_length + 4]

            # Unpickle the LogRecord
            pickled_record = pickle.loads(pickled_record)
            log_record = logging.makeLogRecord(pickled_record)

            # Convert to our LogEntry format and store
            self._store_log_record(log_record, addr)

        except pickle.PickleError as e:
            self.logger.error(f"Failed to unpickle log record from {addr}: {e}")
        except Exception as e:
            self.logger.error(f"Error processing log record from {addr}: {e}")

    def _store_log_record(self, record: logging.LogRecord, addr: tuple) -> None:
        """
        Convert a LogRecord to a LogEntry and store it in the database.

        Args:
            record: The Python LogRecord object
            addr: The client address (host, port)
        """
        try:
            # Convert log level
            try:
                level = LogLevel(record.levelname)
            except ValueError:
                # Fallback to INFO for unknown levels
                level = LogLevel.INFO

            # Extract timestamp
            timestamp = record.created

            # Get the formatted message
            msg = (
                record.getMessage()
                if hasattr(record, "getMessage")
                else str(record.msg)
            )

            # Extract metadata (any extra attributes on the record)
            metadata = {}
            for key, value in record.__dict__.items():
                if key not in {
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                } and not key.startswith("_"):
                    # Only include serializable values
                    try:
                        import json

                        json.dumps(value)  # Test if serializable
                        metadata[key] = value
                    except (TypeError, ValueError):
                        metadata[key] = str(value)

            # Add client address to metadata
            metadata["udp_client_host"] = addr[0]
            metadata["udp_client_port"] = addr[1]

            # Create LogEntry
            with get_db_session() as session:
                log_entry = LogEntry(
                    timestamp=timestamp,
                    level=level,
                    name=record.name,
                    msg=msg,
                    pathname=getattr(record, "pathname", None),
                    lineno=getattr(record, "lineno", None),
                    args=getattr(record, "args", None),
                    exc_info=getattr(record, "exc_info", None),
                    func=getattr(record, "funcName", None),
                    extra_metadata=metadata if metadata else None,
                )
                session.add(log_entry)
                session.commit()

                # Broadcast to connected clients if callback is provided
                if self.broadcast_callback:
                    self.broadcast_callback(log_entry)

        except Exception as e:
            self.logger.error(f"Failed to store log record: {e}")
