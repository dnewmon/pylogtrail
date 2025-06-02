# PyLogTrail Data Retention System

The PyLogTrail retention system automatically manages log data by cleaning up old records based on configurable time and count limits.

## Features

- **Time-based retention**: Keep logs for a specified duration (e.g., 1 week, 30 days)
- **Count-based retention**: Keep only the most recent N log entries
- **Export before deletion**: Automatically export deleted records to CSV files in ZIP archives
- **REST API**: Manage retention settings via HTTP endpoints
- **Automatic cleanup**: Run cleanup on server startup and at scheduled intervals

## Configuration

Retention settings are stored in `retention_config.yml` in the project root:

```yaml
retention:
  # Time-based retention: Keep logs for this amount of time
  time_based:
    enabled: true
    duration: "7d"  # 1 week (default)
  
  # Count-based retention: Keep only this many most recent log entries
  count_based:
    enabled: false
    max_entries: 10000
  
  # Export settings for records marked for deletion
  export:
    enabled: true
    format: "csv_zip"
    output_directory: "exports"
    include_timestamp: true
  
  # Cleanup schedule
  schedule:
    on_startup: true     # Run cleanup when server starts
    interval_hours: 24   # Run cleanup every 24 hours
```

### Duration Format

Time-based retention supports flexible duration formats:
- `"7d"` - 7 days
- `"2d12h"` - 2 days and 12 hours
- `"1h30m"` - 1 hour and 30 minutes
- `"45m"` - 45 minutes

## REST API

### Get Current Settings
```http
GET /api/retention/settings
```

Returns current configuration and database statistics.

### Update Settings
```http
PUT /api/retention/settings
Content-Type: application/json

{
  "time_based": {
    "enabled": true,
    "duration": "14d"
  },
  "count_based": {
    "enabled": true,
    "max_entries": 5000
  },
  "export": {
    "enabled": true,
    "output_directory": "exports"
  }
}
```

### Manual Cleanup
```http
POST /api/retention/cleanup
Content-Type: application/json

{
  "dry_run": false
}
```

### Preview Cleanup
```http
GET /api/retention/preview
```

Shows what would be deleted without actually deleting records.

### Validate Duration Format
```http
POST /api/retention/validate-duration
Content-Type: application/json

{
  "duration": "30d"
}
```

## Export Format

When records are deleted, they can be automatically exported to preserve data:

- **Format**: CSV files compressed in ZIP archives
- **Location**: Configurable output directory (default: `exports/`)
- **Filename**: `deleted_logs_YYYYMMDD_HHMMSS.zip` (timestamp optional)
- **Content**: Complete log record data including metadata

The CSV contains these columns:
- `id` - Log entry ID
- `timestamp` - Unix timestamp
- `datetime` - Human-readable timestamp
- `name` - Logger name
- `level` - Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `message` - Log message
- `pathname` - Source file path
- `lineno` - Line number
- `function` - Function name
- `args` - Log arguments
- `exc_info` - Exception information
- `extra_metadata` - Additional metadata

## Automatic Cleanup

Cleanup runs automatically based on configuration:

1. **On Startup**: When `schedule.on_startup` is true
2. **Periodic**: Every `schedule.interval_hours` hours (if > 0)

The server logs cleanup activity including number of records deleted and export file locations.

## Integration

The retention system integrates seamlessly with the PyLogTrail server:

- Automatically initializes with default 1-week retention
- No configuration required for basic operation
- All endpoints accessible via the web server
- Thread-safe database operations
- Graceful error handling

## Example Usage

```python
from pylogtrail.retention.manager import RetentionManager
from pylogtrail.config.retention import get_retention_config_manager

# Get retention manager
manager = RetentionManager()

# Get current statistics
info = manager.get_retention_info()
print(f"Total records: {info['statistics']['total_records']}")

# Run cleanup
result = manager.cleanup_logs()
print(f"Deleted {result['records_deleted']} records")

# Update configuration
config_manager = get_retention_config_manager()
config = config_manager.get_config()
config.time_based.duration = "30d"  # Change to 30 days
config_manager.save_config(config)
```