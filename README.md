## PyLogTrail
---

A dirt simple, centralized Python log trail server with real-time web UI.

PyLogTrail is a lightweight log aggregation server that accepts Python log records via HTTP and UDP, stores them in a SQLite database, and provides a real-time web interface for viewing logs.

## Features

- **Python HTTP Handler**: Built-in logging handler for seamless integration
- **UDP Log Handler**: Accept pickled log records from Python's `DatagramHandler`  
- **Real-time Web UI**: WebSocket-based interface for live log streaming
- **SQLite Storage**: Persistent log storage with structured data
- **Multiple Client Options**: HTTP handler, context manager, and direct UDP support
- **Metadata Support**: Add custom metadata to logs via handler configuration
- **Filtering & Search**: Web UI with filtering capabilities

## Installation

Install PyLogTrail:
```bash
pip install pylogtrail
```

## Quick Start

Start the server:
```bash
pylogtrail-server --port 5000 --udp-port 9999
```

Access the web UI at `http://localhost:5000`

## Log Ingestion

### Python HTTP Handler

The recommended way to send logs to PyLogTrail is using the provided Python HTTP handler:

**Basic Usage:**
```python
import logging
from pylogtrail.client import create_http_handler

# Create and configure the handler
handler = create_http_handler(
    host='localhost:5000',
    metadata={'service': 'myapp', 'version': '1.2.3'}
)

# Add to your logger
logger = logging.getLogger('myapp')
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Send logs normally
logger.info("User login successful")
logger.error("Database connection failed")
```

**Using the Handler Class Directly:**
```python
import logging
from pylogtrail.client import PyLogTrailHTTPHandler

# Create handler with advanced options
handler = PyLogTrailHTTPHandler(
    host='localhost:5000',
    url='/log',
    metadata={'app': 'myservice'},
    secure=False,  # Set to True for HTTPS
    credentials=('username', 'password')  # Optional basic auth
)

logger = logging.getLogger('myapp')
logger.addHandler(handler)
logger.info("This log will be sent to PyLogTrail")
```

**Context Manager (Temporary Logging):**
```python
import logging
from pylogtrail.client.handlers import PyLogTrailContext

# Temporarily send all logs to PyLogTrail
with PyLogTrailContext('localhost:5000', metadata={'session': 'temp'}):
    logging.info('This will be sent to PyLogTrail')
    logging.error('So will this error')
# Handler is automatically removed after the context
```

**Available Client Handlers:**

- `create_http_handler()`: Helper function to quickly create a configured handler
- `PyLogTrailHTTPHandler`: Full-featured HTTP handler class with all options
- `PyLogTrailContext`: Context manager for temporary logging to PyLogTrail

All handlers support:
- Custom metadata injection
- HTTPS connections with SSL context
- Basic authentication
- Automatic log record formatting
- Error handling and retries

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
