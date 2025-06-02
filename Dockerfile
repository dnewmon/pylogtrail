FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYLOGTRAIL_DATABASE_URL="mysql+pymysql://pylogtrail:pylogtrail_password@localhost:3306/pylogtrail"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    default-mysql-server \
    default-mysql-client \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt pyproject.toml README.md ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -e .

# Copy application code
COPY src/ ./src/
COPY tests/ ./tests/

# Create MySQL configuration
RUN mkdir -p /etc/mysql/conf.d
COPY docker/mysql.cnf /etc/mysql/conf.d/

# Create initialization scripts directory
RUN mkdir -p /docker-entrypoint-initdb.d
COPY docker/init-db.sql /docker-entrypoint-initdb.d/

# Create startup script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create MySQL data directory
RUN mkdir -p /var/lib/mysql
RUN chown -R mysql:mysql /var/lib/mysql

# Expose ports
EXPOSE 5000 9999/udp 3306

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Start the services
ENTRYPOINT ["/entrypoint.sh"]
CMD ["pylogtrail-server", "--port", "5000", "--udp-port", "9999"]