import csv
import json
import logging
from datetime import datetime, timezone, timedelta
from io import StringIO
from typing import Dict, Any, List, Optional, Union
from flask import Blueprint, request, jsonify, Response
from sqlalchemy import and_
from pylogtrail.db.session import get_db_session
from pylogtrail.db.models import LogEntry, LogLevel

logger = logging.getLogger(__name__)

download_bp = Blueprint('download', __name__)


def parse_timeframe(timeframe: str) -> Optional[datetime]:
    """
    Parse timeframe string and return datetime cutoff.
    
    Supported formats:
    - "3d" or "3days" -> 3 days ago
    - "2w" or "2weeks" -> 2 weeks ago
    - "1m" or "1month" -> 1 month ago (30 days)
    - "6h" or "6hours" -> 6 hours ago
    - ISO format timestamp
    
    Args:
        timeframe: String representing the time period
        
    Returns:
        datetime object representing the cutoff time, or None if invalid
    """
    if not timeframe:
        return None
        
    timeframe = timeframe.strip()
    now = datetime.now(timezone.utc)
    
    try:
        # Try parsing as ISO format first
        if 'T' in timeframe or '-' in timeframe:
            # Handle different ISO format variations
            iso_string = timeframe
            if iso_string.endswith('Z'):
                iso_string = iso_string[:-1] + '+00:00'
            
            dt = datetime.fromisoformat(iso_string)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
    except (ValueError, TypeError):
        pass
    
    # Parse relative time formats (convert to lowercase for pattern matching)
    timeframe_lower = timeframe.lower()
    if timeframe_lower.endswith(('d', 'day', 'days')):
        # Extract number of days
        num_str = timeframe_lower.rstrip('days').rstrip('day').rstrip('d')
        try:
            days = int(num_str)
            return now - timedelta(days=days)
        except ValueError:
            pass
    
    elif timeframe_lower.endswith(('w', 'week', 'weeks')):
        # Extract number of weeks
        num_str = timeframe_lower.rstrip('weeks').rstrip('week').rstrip('w')
        try:
            weeks = int(num_str)
            return now - timedelta(weeks=weeks)
        except ValueError:
            pass
    
    elif timeframe_lower.endswith(('m', 'month', 'months')):
        # Extract number of months (approximate as 30 days each)
        num_str = timeframe_lower.rstrip('months').rstrip('month').rstrip('m')
        try:
            months = int(num_str)
            return now - timedelta(days=months * 30)
        except ValueError:
            pass
    
    elif timeframe_lower.endswith(('h', 'hour', 'hours')):
        # Extract number of hours
        num_str = timeframe_lower.rstrip('hours').rstrip('hour').rstrip('h')
        try:
            hours = int(num_str)
            return now - timedelta(hours=hours)
        except ValueError:
            pass
    
    return None


def flatten_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """
    Flatten nested JSON metadata into dot-notation keys with string values.
    
    Args:
        metadata: Dictionary containing metadata
        
    Returns:
        Flattened dictionary with string values
    """
    if not metadata:
        return {}
    
    def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, str]:
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Convert lists to comma-separated strings
                items.append((new_key, ','.join(str(item) for item in v)))
            else:
                items.append((new_key, str(v)))
        return dict(items)
    
    return flatten_dict(metadata)


def logs_to_csv(logs: List[LogEntry]) -> str:
    """
    Convert log entries to CSV format with flattened metadata.
    
    Args:
        logs: List of LogEntry objects
        
    Returns:
        CSV string representation
    """
    if not logs:
        return "id,timestamp,datetime,name,level,pathname,lineno,msg,args,exc_info,func\n"
    
    # Collect all unique metadata keys from all logs
    all_metadata_keys = set()
    for log in logs:
        if log.extra_metadata:
            flattened = flatten_metadata(log.extra_metadata)
            all_metadata_keys.update(flattened.keys())
    
    # Sort metadata keys for consistent column order
    metadata_keys = sorted(all_metadata_keys)
    
    # Define CSV headers
    base_headers = [
        'id', 'timestamp', 'datetime', 'name', 'level', 
        'pathname', 'lineno', 'msg', 'args', 'exc_info', 'func'
    ]
    headers = base_headers + [f'metadata.{key}' for key in metadata_keys]
    
    # Create CSV content
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    
    for log in logs:
        # Convert timestamp to readable datetime
        dt_str = datetime.fromtimestamp(log.timestamp, timezone.utc).isoformat()
        
        # Prepare base row data
        row = [
            log.id,
            log.timestamp,
            dt_str,
            log.name,
            log.level.value if log.level else '',
            log.pathname or '',
            log.lineno or '',
            log.msg or '',
            json.dumps(log.args) if log.args else '',
            log.exc_info or '',
            log.func or ''
        ]
        
        # Add metadata columns
        flattened_metadata = flatten_metadata(log.extra_metadata)
        for key in metadata_keys:
            row.append(flattened_metadata.get(key, ''))
        
        writer.writerow(row)
    
    return output.getvalue()


@download_bp.route('/logs/download', methods=['GET'])
def download_logs():
    """
    Download logs as CSV with optional time filtering.
    
    Query parameters:
    - from: Start time (ISO format or relative like "3d", "2w")
    - to: End time (ISO format or relative like "1d")
    - level: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - name: Filter by logger name (supports partial matching)
    - limit: Maximum number of records (default: 1000, max: 10000)
    - format: Output format (csv only for now)
    
    Returns:
        CSV file download response
    """
    try:
        # Parse query parameters
        from_param = request.args.get('from')
        to_param = request.args.get('to')
        level_param = request.args.get('level')
        name_param = request.args.get('name')
        limit_param = request.args.get('limit', '1000')
        format_param = request.args.get('format', 'csv')
        
        # Validate format
        if format_param.lower() != 'csv':
            return jsonify({'error': 'Only CSV format is currently supported'}), 400
        
        # Parse limit
        try:
            limit = int(limit_param)
            if limit < 1 or limit > 10000:
                return jsonify({'error': 'Limit must be between 1 and 10000'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid limit parameter'}), 400
        
        # Parse time parameters
        from_time = parse_timeframe(from_param) if from_param else None
        to_time = parse_timeframe(to_param) if to_param else None
        
        if from_param and from_time is None:
            return jsonify({'error': f'Invalid from time format: {from_param}'}), 400
        if to_param and to_time is None:
            return jsonify({'error': f'Invalid to time format: {to_param}'}), 400
        
        # Parse level parameter
        level_filter = None
        if level_param:
            try:
                level_filter = LogLevel(level_param.upper())
            except ValueError:
                return jsonify({'error': f'Invalid log level: {level_param}'}), 400
        
        # Build query
        with get_db_session() as session:
            query = session.query(LogEntry)
            
            # Apply time filters
            if from_time:
                query = query.filter(LogEntry.timestamp >= from_time.timestamp())
            if to_time:
                query = query.filter(LogEntry.timestamp <= to_time.timestamp())
            
            # Apply level filter
            if level_filter:
                query = query.filter(LogEntry.level == level_filter)
            
            # Apply name filter (partial matching)
            if name_param:
                query = query.filter(LogEntry.name.like(f'%{name_param}%'))
            
            # Order by timestamp descending (newest first) and apply limit
            query = query.order_by(LogEntry.timestamp.desc()).limit(limit)
            
            # Execute query
            logs = query.all()
            
            # Convert to CSV
            csv_content = logs_to_csv(logs)
            
            # Create filename with timestamp
            timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filename = f'pylogtrail_logs_{timestamp_str}.csv'
            
            # Return CSV response
            return Response(
                csv_content,
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename={filename}'}
            )
    
    except Exception as e:
        logger.error(f"Error downloading logs: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@download_bp.route('/logs/upload', methods=['POST'])
def upload_logs():
    """
    Upload logs from CSV file.
    
    Expects multipart/form-data with:
    - 'file' field containing CSV
    - 'investigation' field containing investigation name
    CSV should have columns matching LogEntry fields.
    
    Returns:
        JSON response with upload status
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.csv'):
            return jsonify({'error': 'File must be a CSV'}), 400
        
        # Get investigation name
        investigation = request.form.get('investigation')
        if not investigation or not investigation.strip():
            return jsonify({'error': 'Investigation name is required'}), 400
        
        investigation = investigation.strip()
        
        # Read and parse CSV
        content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(StringIO(content))
        
        uploaded_count = 0
        errors = []
        
        with get_db_session() as session:
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 because row 1 is headers
                try:
                    # Parse required fields
                    timestamp = float(row.get('timestamp', datetime.now().timestamp()))
                    level = LogLevel(row.get('level', 'INFO').upper())
                    name = row.get('name', 'imported')
                    msg = row.get('msg', '')
                    
                    # Parse optional fields
                    pathname = row.get('pathname') or None
                    lineno = int(row.get('lineno')) if row.get('lineno') and row.get('lineno').strip() else None
                    func = row.get('func') or None
                    exc_info = row.get('exc_info') or None
                    
                    # Parse args if present
                    args = None
                    if row.get('args'):
                        try:
                            args = json.loads(row.get('args'))
                        except json.JSONDecodeError:
                            args = row.get('args')  # Keep as string if not valid JSON
                    
                    # Collect metadata from columns starting with 'metadata.'
                    metadata = {}
                    for key, value in row.items():
                        if key.startswith('metadata.') and value:
                            # Remove 'metadata.' prefix and restore nested structure
                            meta_key = key[9:]  # Remove 'metadata.' prefix
                            if '.' in meta_key:
                                # Handle nested keys like 'service.name'
                                parts = meta_key.split('.')
                                current = metadata
                                for part in parts[:-1]:
                                    if part not in current:
                                        current[part] = {}
                                    current = current[part]
                                current[parts[-1]] = value
                            else:
                                metadata[meta_key] = value
                    
                    # Add investigation metadata to every record
                    metadata['investigation'] = investigation
                    
                    # Create log entry
                    log_entry = LogEntry(
                        timestamp=timestamp,
                        level=level,
                        name=name,
                        msg=msg,
                        pathname=pathname,
                        lineno=lineno,
                        args=args,
                        exc_info=exc_info,
                        func=func,
                        extra_metadata=metadata
                    )
                    
                    session.add(log_entry)
                    uploaded_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    if len(errors) > 10:  # Limit error reporting
                        errors.append("... (additional errors truncated)")
                        break
            
            # Commit all changes
            session.commit()
        
        response_data = {
            'status': 'success',
            'uploaded_count': uploaded_count,
            'errors': errors
        }
        
        return jsonify(response_data), 200
    
    except Exception as e:
        logger.error(f"Error uploading logs: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@download_bp.route('/logs/info', methods=['GET'])
def logs_info():
    """
    Get information about available logs and supported filters.
    
    Returns:
        JSON with log statistics and available filters
    """
    try:
        with get_db_session() as session:
            # Get total count
            total_count = session.query(LogEntry).count()
            
            # Get date range
            if total_count > 0:
                earliest = session.query(LogEntry.timestamp).order_by(LogEntry.timestamp.asc()).first()[0]
                latest = session.query(LogEntry.timestamp).order_by(LogEntry.timestamp.desc()).first()[0]
                
                earliest_dt = datetime.fromtimestamp(earliest, timezone.utc).isoformat()
                latest_dt = datetime.fromtimestamp(latest, timezone.utc).isoformat()
            else:
                earliest_dt = latest_dt = None
            
            # Get unique logger names (top 20)
            logger_names = session.query(LogEntry.name).distinct().limit(20).all()
            logger_names = [name[0] for name in logger_names]
            
            # Get log level counts
            level_counts = {}
            for level in LogLevel:
                count = session.query(LogEntry).filter(LogEntry.level == level).count()
                level_counts[level.value] = count
            
            return jsonify({
                'total_logs': total_count,
                'date_range': {
                    'earliest': earliest_dt,
                    'latest': latest_dt
                },
                'log_levels': level_counts,
                'logger_names': logger_names,
                'supported_timeframes': [
                    '3d', '1w', '2w', '1m', '3m', '6m', '1y',
                    '1h', '6h', '12h', '24h'
                ],
                'max_download_limit': 10000
            }), 200
    
    except Exception as e:
        logger.error(f"Error getting logs info: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500