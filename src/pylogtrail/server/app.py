import logging
import argparse
import os
import json
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_socketio import SocketIO, emit
from datetime import datetime
from typing import Dict, Any, Optional, Set, List
from pylogtrail.db.session import get_db_session, init_db
from pylogtrail.db.models import LogEntry, LogLevel

app = Flask(
    __name__,
    static_folder=Path(__file__).parent / "static",
    template_folder=Path(__file__).parent / "templates",
)
socketio = SocketIO(app, cors_allowed_origins="*")

logger = logging.getLogger(__name__)

# Store connected clients
connected_clients: Set[str] = set()


def get_log_data(log_entry: LogEntry) -> Dict[str, Any]:
    """Convert a log entry to a dictionary format for sending to clients."""
    entry_extras = log_entry.extra_metadata or {}
    return {
        "timestamp": datetime.fromtimestamp(log_entry.timestamp).isoformat(),
        "level": log_entry.level.value,
        "name": log_entry.name,
        "msg": log_entry.msg,
        "pathname": log_entry.pathname,
        "lineno": log_entry.lineno,
        "func": log_entry.func,
        **entry_extras,
    }


@socketio.on("connect")
def handle_connect():
    """Handle client connection."""
    client_id = request.sid
    connected_clients.add(client_id)
    logger.info(f"Client connected: {client_id}")


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection."""
    client_id = request.sid
    if client_id in connected_clients:
        connected_clients.remove(client_id)
    logger.info(f"Client disconnected: {client_id}")


@socketio.on("get_initial_logs")
def handle_get_initial_logs(*args, **kwargs):
    """Handle request for initial log dump."""
    client_id = request.sid
    limit = request.args.get("limit", 1000, type=int)

    with get_db_session() as session:
        # Get recent logs
        log_entries = (
            session.query(LogEntry)
            .order_by(LogEntry.timestamp.desc())
            .limit(limit)
            .all()
        )

        # Convert all entries to dict format and send in a single message
        logs = [get_log_data(entry) for entry in reversed(log_entries)]
        emit("initial_logs", {"logs": logs})


def broadcast_log(log_entry: LogEntry):
    """Broadcast a log entry to all connected clients."""
    log_data = get_log_data(log_entry)
    socketio.emit("new_log", log_data)


@app.route("/log", methods=["POST"])
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

            # Broadcast the new log entry to all connected clients
            broadcast_log(log_entry)

        return jsonify({"status": "success"}), 200

    except ValueError as e:
        # Handle invalid log level
        app.logger.error(f"Invalid log level: {str(e)}")
        return jsonify({"error": "Invalid log level"}), 400
    except Exception as e:
        app.logger.error(f"Error processing log record: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/")
def serve_homepage():
    """Serve the main UI page."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def serve_static_file(path: str):
    """Serve static files."""
    return send_from_directory(app.static_folder, path)


def create_app(config: Optional[Dict[str, Any]] = None) -> Flask:
    """
    Create and configure the Flask application.

    Args:
        config: Optional configuration dictionary to override defaults

    Returns:
        Flask application instance
    """
    if config:
        app.config.update(config)

    # Ensure static and template directories exist
    os.makedirs(app.static_folder, exist_ok=True)
    os.makedirs(app.template_folder, exist_ok=True)

    # Initialize database on startup
    with app.app_context():
        init_db()

    return app


def main():
    """Entry point for the pylogtrail-server CLI command."""
    parser = argparse.ArgumentParser(description="Run the pylogtrail server")
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port number to run the server on (default: 5000)",
    )
    args = parser.parse_args()

    app = create_app()
    app.debug = True
    socketio.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
