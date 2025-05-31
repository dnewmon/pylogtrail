## PyLogTrail
---

A dirt simple, centralized Python log trail server with real-time web UI.

PyLogTrail is a lightweight log aggregation server that accepts Python log records via HTTP and UDP, stores them in a SQLite database, and provides a real-time web interface for viewing logs.

## Features

- **HTTP Log Endpoint**: Accept log records via POST requests to `/log`
- **UDP Log Handler**: Accept pickled log records from Python's `DatagramHandler`
- **Real-time Web UI**: WebSocket-based interface for live log streaming
- **SQLite Storage**: Persistent log storage with structured data
- **Multiple Input Formats**: Support for JSON and form-encoded log data
- **Metadata Support**: Extract and store custom metadata from logs
- **Filtering & Search**: Web UI with filtering capabilities

## Quick Start

Start the server:
```bash
pylogtrail-server --port 5000 --udp-port 9999
```

Access the web UI at `http://localhost:5000`

## Log Ingestion

### HTTP Endpoint (`/log`)

Send log records via POST to `/log`. Supports both JSON and form-encoded data:

**JSON Format:**
```bash
curl -X POST http://localhost:5000/log \
  -H "Content-Type: application/json" \
  -d '{
    "levelname": "INFO",
    "name": "myapp.module",
    "msg": "User login successful",
    "created": 1672531200.123,
    "pathname": "/app/auth.py",
    "lineno": 42,
    "custom_field": "custom_value"
  }'
```

**Form-encoded Format:**
```bash
curl -X POST http://localhost:5000/log \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "levelname=ERROR&name=myapp&msg=Database connection failed&created=1672531200"
```

**URL Parameters:**
Add metadata via query parameters:
```bash
curl -X POST "http://localhost:5000/log?service=auth&version=1.2.3" \
  -H "Content-Type: application/json" \
  -d '{"levelname": "INFO", "msg": "Service started"}'
```

### UDP Socket

Configure Python's `DatagramHandler` to send logs:

```python
import logging
from logging.handlers import DatagramHandler

# Setup UDP handler
udp_handler = DatagramHandler('localhost', 9999)
logger = logging.getLogger('myapp')
logger.addHandler(udp_handler)
logger.setLevel(logging.INFO)

# Send logs
logger.info("This will be sent via UDP")
```

The UDP handler automatically extracts client IP/port and stores them as metadata.

## Configuration

- `--port`: HTTP server port (default: 5000)
- `--udp-port`: UDP listener port (optional, disabled if not specified)

## Architecture

- **Flask**: HTTP server with `/log` endpoint
- **SocketIO**: WebSocket communication for real-time updates
- **SQLite**: Log storage with SQLAlchemy ORM
- **Threading**: Background UDP listener
- **React**: Frontend web UI (built assets served statically)
