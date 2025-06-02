import logging
import argparse
import os
import threading
import time
from pathlib import Path
from datetime import datetime, timezone
from flask import Flask, send_from_directory
from typing import Dict, Any, Optional
from pylogtrail.db.session import init_db
from pylogtrail.server.udp_handler import UDPLogHandler
from pylogtrail.server.http_handler import create_log_endpoint
from pylogtrail.server.socketio import init_socketio, broadcast_log
from pylogtrail.server.retention_api import retention_bp
from pylogtrail.server.download_api import download_bp
from pylogtrail.retention.manager import RetentionManager
from pylogtrail.config.retention import get_retention_config_manager

app = Flask(
    __name__,
    static_folder=Path(__file__).parent / "static",
    template_folder=Path(__file__).parent / "templates",
)

logger = logging.getLogger(__name__)

# Global UDP handler instance
udp_handler: Optional[UDPLogHandler] = None

# Global retention thread instance
retention_thread: Optional[threading.Thread] = None
retention_stop_event: Optional[threading.Event] = None


def retention_background_thread():
    """Background thread that runs retention cleanup daily"""
    global retention_stop_event
    
    if retention_stop_event is None:
        logger.error("Retention thread started without stop event")
        return
    
    logger.info("Retention background thread started")
    
    while not retention_stop_event.is_set():
        try:
            config_manager = get_retention_config_manager()
            config = config_manager.get_config()
            
            # Check if we should run retention cleanup
            should_run = False
            now_utc = datetime.now(timezone.utc)
            
            if config.schedule.last_execution is None:
                # Never run before, run now
                should_run = True
                logger.info("Retention cleanup has never run, executing now")
            else:
                try:
                    last_execution = datetime.fromisoformat(config.schedule.last_execution.replace('Z', '+00:00'))
                    if last_execution.tzinfo is None:
                        last_execution = last_execution.replace(tzinfo=timezone.utc)
                    
                    # Check if it's been more than interval_hours since last execution
                    hours_since_last = (now_utc - last_execution).total_seconds() / 3600
                    
                    if hours_since_last >= config.schedule.interval_hours:
                        should_run = True
                        logger.info(f"Retention cleanup due (last run: {last_execution.isoformat()}, {hours_since_last:.1f} hours ago)")
                    
                except Exception as e:
                    logger.error(f"Error parsing last execution time: {e}")
                    should_run = True  # Run on error to be safe
            
            if should_run:
                try:
                    retention_manager = RetentionManager(config_manager)
                    result = retention_manager.cleanup_logs()
                    
                    # Update last execution time
                    config_manager.update_last_execution(now_utc.isoformat())
                    
                    if result['records_deleted'] > 0:
                        logger.info(f"Background retention cleanup: deleted {result['records_deleted']} log records")
                        if result['export_file']:
                            logger.info(f"Exported deleted records to: {result['export_file']}")
                    else:
                        logger.info("Background retention cleanup: no records needed deletion")
                        
                except Exception as e:
                    logger.error(f"Error during background retention cleanup: {e}")
            
        except Exception as e:
            logger.error(f"Error in retention background thread: {e}")
        
        # Sleep for 1 hour before checking again
        retention_stop_event.wait(3600)  # 1 hour = 3600 seconds
    
    logger.info("Retention background thread stopped")


@app.route("/")
def serve_homepage():
    """Serve the main UI page."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def serve_static_file(path: str):
    """Serve static files."""
    return send_from_directory(app.static_folder, path)


def create_app(config: Optional[Dict[str, Any]] = None, udp_port: Optional[int] = None):
    """
    Create and configure the Flask application.

    Args:
        config: Optional configuration dictionary to override defaults
        udp_port: Optional UDP port for log handler (if None, UDP handler won't start)

    Returns:
        Flask application instance
    """
    global udp_handler, retention_thread, retention_stop_event
    
    if config:
        app.config.update(config)

    # Initialize SocketIO
    socketio = init_socketio(app)

    # Ensure static and template directories exist
    os.makedirs(app.static_folder, exist_ok=True)
    os.makedirs(app.template_folder, exist_ok=True)

    # Initialize database on startup
    with app.app_context():
        init_db()
        
        # Run retention cleanup on startup if configured
        try:
            config_manager = get_retention_config_manager()
            config = config_manager.get_config()
            if config.schedule.on_startup:
                retention_manager = RetentionManager(config_manager)
                result = retention_manager.cleanup_logs()
                if result['records_deleted'] > 0:
                    logger.info(f"Startup cleanup: deleted {result['records_deleted']} log records")
                    if result['export_file']:
                        logger.info(f"Exported deleted records to: {result['export_file']}")
        except Exception as e:
            logger.error(f"Error during startup retention cleanup: {e}")

    # Register the log endpoint with dependency injection
    app.add_url_rule("/log", "log_endpoint", create_log_endpoint(broadcast_log), methods=["POST"])
    
    # Register retention API blueprint
    app.register_blueprint(retention_bp)
    
    # Register download API blueprint
    app.register_blueprint(download_bp)

    # Start UDP handler if port is specified
    if udp_port is not None:
        try:
            udp_handler = UDPLogHandler(port=udp_port, broadcast_callback=broadcast_log)
            udp_handler.start()
            logger.info(f"UDP log handler started on port {udp_port}")
        except Exception as e:
            logger.error(f"Failed to start UDP handler: {e}")
            udp_handler = None

    # Start retention background thread
    if retention_thread is None or not retention_thread.is_alive():
        try:
            retention_stop_event = threading.Event()
            retention_thread = threading.Thread(target=retention_background_thread, daemon=True)
            retention_thread.start()
            logger.info("Retention background thread started")
        except Exception as e:
            logger.error(f"Failed to start retention background thread: {e}")

    return app


def main():
    """Entry point for the pylogtrail-server CLI command."""
    parser = argparse.ArgumentParser(description="Run the pylogtrail server")
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port number to run the HTTP server on (default: 5000)",
    )
    parser.add_argument(
        "--udp-port",
        type=int,
        default=None,
        help="Port number for UDP log handler (optional, disabled if not specified)",
    )
    args = parser.parse_args()

    app = create_app(udp_port=args.udp_port)
    app.debug = True
    
    try:
        from pylogtrail.server.socketio import socketio
        socketio.run(app, host="0.0.0.0", port=args.port, allow_unsafe_werkzeug=True)
    finally:
        # Cleanup UDP handler on shutdown
        global udp_handler, retention_stop_event, retention_thread
        if udp_handler:
            udp_handler.stop()
        
        # Stop retention background thread
        if retention_stop_event:
            retention_stop_event.set()
        if retention_thread and retention_thread.is_alive():
            retention_thread.join(timeout=5)  # Wait up to 5 seconds for thread to stop


if __name__ == "__main__":
    main()
