#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Banner function
print_banner() {
    echo -e "${PURPLE}"
    echo "=============================================="
    echo "       PyLogTrail Docker Container"
    echo "=============================================="
    echo -e "${NC}"
}

# Logging function
log() {
    echo -e "${CYAN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✓ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠ $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ✗ $1${NC}"
}

# Start banner
print_banner

# Function to wait for MySQL to be ready
wait_for_mysql() {
    log "Waiting for MySQL to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if mysqladmin ping --silent --user=root; then
            log_success "MySQL is ready!"
            return 0
        fi
        
        log "MySQL not ready yet (attempt $attempt/$max_attempts). Waiting 2 seconds..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "MySQL failed to start within 60 seconds"
    return 1
}

# Function to initialize MySQL
init_mysql() {
    log "Initializing MySQL server..."
    
    # Initialize MySQL data directory if it doesn't exist
    if [ ! -d "/var/lib/mysql/mysql" ]; then
        log "Creating MySQL data directory..."
        mysqld --initialize-insecure --user=mysql --datadir=/var/lib/mysql
        log_success "MySQL data directory created"
    else
        log "MySQL data directory already exists"
    fi
    
    # Start MySQL in background
    log "Starting MySQL server..."
    mysqld_safe --user=mysql --datadir=/var/lib/mysql &
    
    # Wait for MySQL to be ready
    wait_for_mysql
    
    # Run initialization script if database doesn't exist
    if ! mysql -u root -e "USE pylogtrail;" 2>/dev/null; then
        log "Running database initialization script..."
        mysql -u root < /docker-entrypoint-initdb.d/init-db.sql
        log_success "Database initialization completed"
    else
        log "Database already exists, skipping initialization"
    fi
}

# Function to display configuration
show_config() {
    echo -e "${BLUE}"
    echo "=============================================="
    echo "           CONFIGURATION"
    echo "=============================================="
    echo -e "${NC}"
    
    echo -e "${CYAN}Database Configuration:${NC}"
    echo "  - Host: localhost:3306"
    echo "  - Database: pylogtrail"
    echo "  - User: pylogtrail"
    echo "  - URL: ${PYLOGTRAIL_DATABASE_URL}"
    echo ""
    
    echo -e "${CYAN}PyLogTrail Configuration:${NC}"
    echo "  - Web UI Port: 5000"
    echo "  - UDP Log Port: 9999"
    echo "  - Web UI URL: http://localhost:5000"
    echo ""
    
    echo -e "${CYAN}Docker Environment:${NC}"
    echo "  - Python Version: $(python --version)"
    echo "  - MySQL Version: $(mysql --version | head -1)"
    echo "  - Working Directory: $(pwd)"
    echo ""
    
    echo -e "${BLUE}=============================================="
    echo -e "${NC}"
}

# Function to test database connection
test_db_connection() {
    log "Testing database connection..."
    
    # Test MySQL connection
    if mysql -u pylogtrail -ppylogtrail_password -h localhost pylogtrail -e "SELECT 1;" > /dev/null 2>&1; then
        log_success "Database connection test passed"
    else
        log_error "Database connection test failed"
        exit 1
    fi
    
    # Test PyLogTrail database initialization
    log "Testing PyLogTrail database initialization..."
    cd /app
    export PYTHONPATH="/app/src:$PYTHONPATH"
    if python -c "from pylogtrail.db.session import init_db; init_db()" 2>&1; then
        log_success "PyLogTrail database tables created successfully"
    else
        log_error "Failed to create PyLogTrail database tables"
        python -c "from pylogtrail.db.session import init_db; init_db()" || true
        exit 1
    fi
}

# Function to start PyLogTrail
start_pylogtrail() {
    log "Starting PyLogTrail server..."
    log "Access the web UI at: http://localhost:5000"
    log "Send UDP logs to: localhost:9999"
    
    echo -e "${GREEN}"
    echo "=============================================="
    echo "       PyLogTrail is now running!"
    echo "=============================================="
    echo -e "${NC}"
    
    # Change to app directory and start the server
    cd /app
    export PYTHONPATH="/app/src:$PYTHONPATH"
    exec "$@"
}

# Main execution
main() {
    # Initialize MySQL
    init_mysql
    
    # Show configuration
    show_config
    
    # Test database connection
    test_db_connection
    
    # Start PyLogTrail
    start_pylogtrail "$@"
}

# Trap SIGTERM and SIGINT to gracefully shutdown
cleanup() {
    log "Shutting down services..."
    killall mysqld 2>/dev/null || true
    exit 0
}

trap cleanup SIGTERM SIGINT

# Run main function
main "$@"