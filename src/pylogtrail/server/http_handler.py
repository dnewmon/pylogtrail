import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from flask import request, jsonify
from pylogtrail.db.session import get_db_session
from pylogtrail.db.models import LogEntry, LogLevel


logger = logging.getLogger(__name__)


def create_log_endpoint(broadcast_callback: Optional[Callable[[LogEntry], None]] = None):
    """
    Create the log endpoint handler with dependency injection for broadcast function.
    
    Args:
        broadcast_callback: Optional callback function to broadcast logs
        
    Returns:
        The log endpoint handler function
    """
    
    def log_endpoint():
        """
        Endpoint that accepts log records from Python's HTTPHandler.
        The endpoint accepts both JSON and form-urlencoded data.
        Additional metadata can be provided through URL query parameters.
        """
        try:
            # Determine content type and parse request data accordingly
            content_type = request.headers.get("Content-Type", "")
            if "application/x-www-form-urlencoded" in content_type:
                log_record = dict(request.form)
                # Convert form values to appropriate types
                if "created" in log_record:
                    log_record["created"] = float(log_record["created"])
                if "lineno" in log_record:
                    log_record["lineno"] = int(log_record["lineno"])
            else:
                # Default to JSON handling
                log_record = (
                    json.loads(request.data.decode("utf-8")) if request.data else {}
                )

            # Extract metadata from URL parameters
            url_metadata = {
                k: v
                for k, v in request.args.items()
                if k
                not in {
                    "created",
                    "levelname",
                    "msg",
                    "name",
                    "pathname",
                    "lineno",
                    "args",
                    "exc_info",
                    "funcName",
                }
            }

            # Extract required fields
            # Combine seconds and milliseconds if both are present
            if "created" in log_record and "msecs" in log_record:
                seconds = float(log_record["created"])
                msecs = float(log_record["msecs"]) / 1000.0
                timestamp = seconds + msecs
            else:
                timestamp = float(log_record.get("created", datetime.now().timestamp()))

            level = LogLevel(log_record.get("levelname", "INFO"))
            name = log_record.get("name", "root")  # logger name
            msg = log_record.get("msg", "")  # the actual log message

            # Extract optional fields
            pathname = log_record.get("pathname")  # path to source file
            lineno = log_record.get("lineno")  # line number in source file
            args = log_record.get("args")  # arguments to the logging call
            exc_info = log_record.get("exc_info")  # exception info if any
            func = log_record.get("func")  # function name

            # Extract metadata from request body and merge with URL metadata
            body_metadata = {
                k: v
                for k, v in log_record.items()
                if k
                not in {
                    "created",
                    "levelname",
                    "msg",
                    "name",
                    "pathname",
                    "lineno",
                    "args",
                    "exc_info",
                    "funcName",
                }
            }

            # Merge metadata, with URL parameters taking precedence
            metadata = {**body_metadata, **url_metadata}

            with get_db_session() as session:
                print(f"Timestamp: {timestamp}")
                # Create log entry
                log_entry = LogEntry(
                    timestamp=timestamp,  # Now storing as float
                    level=level,
                    name=name,
                    msg=msg,
                    pathname=pathname,
                    lineno=lineno,
                    args=args,
                    exc_info=exc_info,
                    func=func,
                    extra_metadata=metadata if metadata else None,
                )
                session.add(log_entry)
                session.commit()

                # Broadcast the new log entry to all connected clients if callback provided
                if broadcast_callback:
                    broadcast_callback(log_entry)

            return jsonify({"status": "success"}), 200

        except ValueError as e:
            # Handle invalid log level
            logger.error(f"Invalid log level: {str(e)}")
            return jsonify({"error": "Invalid log level"}), 400
        except Exception as e:
            logger.error(f"Error processing log record: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500
    
    return log_endpoint