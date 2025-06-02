import logging
from flask import request
from flask_socketio import SocketIO, emit
from datetime import datetime
from typing import Dict, Any, Set
from pylogtrail.db.session import get_db_session
from pylogtrail.db.models import LogEntry

logger = logging.getLogger(__name__)

# Store connected clients
connected_clients: Set[str] = set()

# Global SocketIO instance
socketio: SocketIO = None


def init_socketio(app):
    """Initialize SocketIO with the Flask app and register event handlers."""
    global socketio
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # Register event handlers
    socketio.on_event("connect", handle_connect)
    socketio.on_event("disconnect", handle_disconnect)
    socketio.on_event("get_initial_logs", handle_get_initial_logs)
    
    return socketio


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


def handle_connect():
    """Handle client connection."""
    client_id = request.sid
    connected_clients.add(client_id)
    logger.info(f"Client connected: {client_id}")


def handle_disconnect():
    """Handle client disconnection."""
    client_id = request.sid
    if client_id in connected_clients:
        connected_clients.remove(client_id)
    logger.info(f"Client disconnected: {client_id}")


def handle_get_initial_logs(data=None):
    """Handle request for initial log dump with optional filters."""
    client_id = request.sid
    
    # Extract parameters from data or use defaults
    if data is None:
        data = {}
    
    limit = data.get("limit", 1000)
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    with get_db_session() as session:
        # Build query with optional date/time filters
        query = session.query(LogEntry)
        
        # Apply time filters if provided
        if start_time:
            try:
                start_timestamp = datetime.fromisoformat(start_time.replace('Z', '+00:00')).timestamp()
                query = query.filter(LogEntry.timestamp >= start_timestamp)
            except ValueError:
                logger.warning(f"Invalid start_time format: {start_time}")
        
        if end_time:
            try:
                end_timestamp = datetime.fromisoformat(end_time.replace('Z', '+00:00')).timestamp()
                query = query.filter(LogEntry.timestamp <= end_timestamp)
            except ValueError:
                logger.warning(f"Invalid end_time format: {end_time}")
        
        # Get logs ordered by timestamp descending and apply limit
        log_entries = (
            query.order_by(LogEntry.timestamp.desc())
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