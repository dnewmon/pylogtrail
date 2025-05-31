## PyLogTrail
---

A dirt simple, centralized Python log trail server with real-time web UI.

PyLogTrail is a lightweight log aggregation server that accepts Python log records via HTTP and UDP, stores them in a SQLite database, and provides a real-time web interface for viewing logs.

## Features

- **Python HTTP Handler**: Built-in logging handler for seamless integration
- **Python UDP Handler**: Built-in UDP handler with metadata support and context manager
- **UDP Log Handler**: Accept pickled log records from Python's `DatagramHandler`  
- **Real-time Web UI**: WebSocket-based interface for live log streaming
- **SQLite Storage**: Persistent log storage with structured data
- **Multiple Client Options**: HTTP handler, UDP handler, context managers, and direct UDP support
- **Metadata Support**: Add custom metadata to logs via handler configuration
- **Generic Context Management**: Base context manager class with inheritance for specific handlers
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
from pylogtrail.client.handlers import PyLogTrailHTTPContext

# Temporarily send all logs to PyLogTrail via HTTP
with PyLogTrailHTTPContext('localhost:5000', metadata={'session': 'temp'}):
    logging.info('This will be sent to PyLogTrail')
    logging.error('So will this error')
# Handler is automatically removed after the context
```

**Available Client Handlers:**

- `create_http_handler()`: Helper function to quickly create a configured HTTP handler
- `PyLogTrailHTTPHandler`: Full-featured HTTP handler class with all options
- `PyLogTrailHTTPContext`: Context manager for temporary HTTP logging to PyLogTrail

All HTTP handlers support:
- Custom metadata injection
- HTTPS connections with SSL context
- Basic authentication
- Automatic log record formatting
- Error handling and retries

### Python UDP Handler

The Python UDP handler provides native UDP support with metadata capabilities:

**Basic Usage:**
```python
import logging
from pylogtrail.client import create_udp_handler

# Create and configure the UDP handler
handler = create_udp_handler(
    host='localhost',
    port=9999,
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
from pylogtrail.client import PyLogTrailUDPHandler

# Create handler with metadata
handler = PyLogTrailUDPHandler(
    host='localhost',
    port=9999,
    metadata={'app': 'myservice', 'environment': 'production'}
)

logger = logging.getLogger('myapp')
logger.addHandler(handler)
logger.info("This log will be sent to PyLogTrail via UDP")
```

**Context Manager (Temporary UDP Logging):**
```python
import logging
from pylogtrail.client.handlers import PyLogTrailUDPContext

# Temporarily send all logs to PyLogTrail via UDP
with PyLogTrailUDPContext('localhost', port=9999, metadata={'session': 'temp'}):
    logging.info('This will be sent to PyLogTrail via UDP')
    logging.error('So will this error')
# Handler is automatically removed after the context
```

**Available UDP Client Handlers:**

- `create_udp_handler()`: Helper function to quickly create a configured UDP handler
- `PyLogTrailUDPHandler`: Full-featured UDP handler class with metadata support
- `PyLogTrailUDPContext`: Context manager for temporary UDP logging to PyLogTrail

### Generic Context Manager

PyLogTrail provides a generic context manager base class that can work with any logging handler:

**Using Generic Context with Custom Logger:**
```python
import logging
from pylogtrail.client.handlers import PyLogTrailContext, create_http_handler

# Create a custom logger
app_logger = logging.getLogger('myapp.module')

# Use any handler with the generic context manager
handler = create_http_handler('localhost:5000', metadata={'component': 'auth'})
with PyLogTrailContext(handler, logger=app_logger):
    app_logger.info('This goes to the specific logger')
    app_logger.error('This error also goes to the specific logger')
```

**Context Manager Inheritance:**
- `PyLogTrailContext`: Base context manager that accepts any handler and optional logger
- `PyLogTrailHTTPContext`: Inherits from base, creates HTTP handler internally
- `PyLogTrailUDPContext`: Inherits from base, creates UDP handler internally

All context managers support:
- Custom logger specification (defaults to root logger)
- Automatic handler cleanup on context exit
- Metadata injection through handler configuration
- Error handling and graceful degradation

### Standard UDP Socket (Alternative)

You can also use Python's standard `DatagramHandler` for basic UDP logging:

```python
import logging
from logging.handlers import DatagramHandler

# Setup basic UDP handler (no metadata support)
udp_handler = DatagramHandler('localhost', 9999)
logger = logging.getLogger('myapp')
logger.addHandler(udp_handler)
logger.setLevel(logging.INFO)

# Send logs
logger.info("This will be sent via UDP")
```

Note: The standard `DatagramHandler` doesn't support metadata injection. For enhanced features like metadata and better error handling, use the `PyLogTrailUDPHandler` instead.

The UDP server automatically extracts client IP/port and stores them as metadata for all UDP connections.

## Docker Deployment

PyLogTrail can be easily deployed using Docker with a built-in MySQL database.

### Quick Start with Docker

**Build and run with docker-compose (recommended):**
```bash
# Clone the repository
git clone <repository-url>
cd pylogtrail

# Build and start the container
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

**Build and run with Docker directly:**
```bash
# Build the image
docker build -t pylogtrail .

# Run the container
docker run -d \
  --name pylogtrail-server \
  -p 5000:5000 \
  -p 9999:9999 \
  -v pylogtrail_mysql_data:/var/lib/mysql \
  pylogtrail
```

### Docker Configuration

The Docker container includes:
- **Python 3.11** runtime environment
- **MySQL 8.0** database server
- **Automatic database initialization** on first run
- **Persistent data storage** via Docker volumes
- **Health checks** for service monitoring

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PYLOGTRAIL_DATABASE_URL` | `mysql+pymysql://pylogtrail:pylogtrail_password@localhost:3306/pylogtrail` | Database connection URL |
| `PYTHONUNBUFFERED` | `1` | Ensure Python output is sent straight to terminal |

### Ports

| Port | Service | Description |
|------|---------|-------------|
| `5000` | Web UI | Access the PyLogTrail web interface |
| `9999` | UDP Logs | Send UDP log messages |
| `3306` | MySQL | Database connection (optional external access) |

### Data Persistence

The container uses Docker volumes to persist data:
- `mysql_data`: MySQL database files
- `log_data`: MySQL log files

### Container Health

The container includes health checks that verify:
- Web UI is responding on port 5000
- MySQL database is running
- PyLogTrail application is healthy

### First Run Setup

When the container starts for the first time, it will:

1. **Initialize MySQL** with a new data directory
2. **Create the database** and user accounts
3. **Run initialization scripts** to set up tables
4. **Test database connectivity** 
5. **Start PyLogTrail server** with clear configuration output

All configuration details are printed during startup in a clearly formatted output showing:
- Database connection details
- Server ports and URLs
- Environment information

### Logs and Monitoring

View container logs:
```bash
# Follow logs in real-time
docker-compose logs -f pylogtrail

# View recent logs
docker logs pylogtrail-server
```

Connect to the running container:
```bash
docker exec -it pylogtrail-server bash
```

### Stopping the Container

```bash
# With docker-compose
docker-compose down

# With Docker directly
docker stop pylogtrail-server
docker rm pylogtrail-server
```

## Native Installation

For development or non-Docker deployments:

### Configuration

- `--port`: HTTP server port (default: 5000)
- `--udp-port`: UDP listener port (optional, disabled if not specified)
- `--database-url`: Database URL (default: SQLite)

## Architecture

- **Flask**: HTTP server with `/log` endpoint
- **SocketIO**: WebSocket communication for real-time updates
- **SQLAlchemy**: Database ORM supporting SQLite, MySQL, PostgreSQL
- **MySQL**: Default database in Docker deployment
- **Threading**: Background UDP listener
- **React**: Frontend web UI (built assets served statically)
