import os
import csv
import zipfile
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from pylogtrail.db.session import get_db_session
from pylogtrail.db.models import LogEntry
from pylogtrail.config.retention import get_retention_config_manager, RetentionConfigManager


logger = logging.getLogger(__name__)


class RetentionManager:
    """Manages log data retention based on time and count limits"""
    
    def __init__(self, config_manager: Optional[RetentionConfigManager] = None):
        self.config_manager = config_manager or get_retention_config_manager()
    
    def cleanup_logs(self, dry_run: bool = False) -> dict:
        """
        Clean up logs based on retention policy
        
        Args:
            dry_run: If True, don't actually delete records, just return what would be deleted
            
        Returns:
            Dictionary with cleanup statistics
        """
        config = self.config_manager.get_config()
        
        with get_db_session() as session:
            # Find records to delete based on time-based retention
            time_based_ids = []
            if config.time_based.enabled:
                time_based_ids = self._get_time_based_deletion_ids(session, config.time_based.duration)
            
            # Find records to delete based on count-based retention  
            count_based_ids = []
            if config.count_based.enabled:
                count_based_ids = self._get_count_based_deletion_ids(session, config.count_based.max_entries)
            
            # Combine deletion IDs (union of both sets)
            deletion_ids = set(time_based_ids) | set(count_based_ids)
            
            if not deletion_ids:
                logger.info("No log records need to be cleaned up")
                return {
                    'records_deleted': 0,
                    'export_file': None,
                    'time_based_deletions': 0,
                    'count_based_deletions': 0
                }
            
            # Export records before deletion if enabled
            export_file = None
            if config.export.enabled and not dry_run:
                export_file = self._export_records(session, list(deletion_ids), config.export)
            
            # Delete records
            records_deleted = 0
            if not dry_run:
                records_deleted = self._delete_records(session, list(deletion_ids))
                logger.info(f"Deleted {records_deleted} log records")
            else:
                records_deleted = len(deletion_ids)
                logger.info(f"Dry run: Would delete {records_deleted} log records")
            
            return {
                'records_deleted': records_deleted,
                'export_file': export_file,
                'time_based_deletions': len(time_based_ids),
                'count_based_deletions': len(count_based_ids),
                'dry_run': dry_run
            }
    
    def _get_time_based_deletion_ids(self, session: Session, duration: str) -> List[int]:
        """Get IDs of records older than the specified duration"""
        try:
            duration_seconds = self.config_manager.parse_duration(duration)
            cutoff_timestamp = time.time() - duration_seconds
            
            # Query for records older than cutoff
            query = session.query(LogEntry.id).filter(LogEntry.timestamp < cutoff_timestamp)
            return [row.id for row in query.all()]
            
        except Exception as e:
            logger.error(f"Error finding time-based deletion records: {e}")
            return []
    
    def _get_count_based_deletion_ids(self, session: Session, max_entries: int) -> List[int]:
        """Get IDs of records beyond the maximum count limit"""
        try:
            # Count total records
            total_count = session.query(func.count(LogEntry.id)).scalar()
            
            if total_count <= max_entries:
                return []
            
            # Find records to delete (oldest ones beyond the limit)
            records_to_delete = total_count - max_entries
            
            # Get the oldest records
            query = session.query(LogEntry.id).order_by(LogEntry.timestamp).limit(records_to_delete)
            return [row.id for row in query.all()]
            
        except Exception as e:
            logger.error(f"Error finding count-based deletion records: {e}")
            return []
    
    def _export_records(self, session: Session, record_ids: List[int], export_config) -> Optional[str]:
        """Export records to CSV in ZIP file before deletion"""
        try:
            if not record_ids:
                return None
            
            # Create export directory
            export_dir = Path(export_config.output_directory)
            export_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S") if export_config.include_timestamp else ""
            base_name = f"deleted_logs_{timestamp_str}" if timestamp_str else "deleted_logs"
            zip_filename = export_dir / f"{base_name}.zip"
            csv_filename = f"{base_name}.csv"
            
            # Query records to export
            records = session.query(LogEntry).filter(LogEntry.id.in_(record_ids)).all()
            
            # Create ZIP file with CSV
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Create CSV in memory and add to ZIP
                csv_content = self._create_csv_content(records)
                zipf.writestr(csv_filename, csv_content)
            
            logger.info(f"Exported {len(records)} records to {zip_filename}")
            return str(zip_filename)
            
        except Exception as e:
            logger.error(f"Error exporting records: {e}")
            return None
    
    def _create_csv_content(self, records: List[LogEntry]) -> str:
        """Create CSV content from log records"""
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'id', 'timestamp', 'datetime', 'name', 'level', 'message',
            'pathname', 'lineno', 'function', 'args', 'exc_info', 'extra_metadata'
        ])
        
        # Write records
        for record in records:
            # Convert timestamp to readable datetime
            dt = datetime.fromtimestamp(record.timestamp)
            
            writer.writerow([
                record.id,
                record.timestamp,
                dt.isoformat(),
                record.name,
                record.level.value,
                record.msg,
                record.pathname,
                record.lineno,
                record.func,
                record.args,
                record.exc_info,
                record.extra_metadata
            ])
        
        return output.getvalue()
    
    def _delete_records(self, session: Session, record_ids: List[int]) -> int:
        """Delete records by ID"""
        try:
            if not record_ids:
                return 0
            
            # Delete in batches to avoid memory issues with large deletions
            batch_size = 1000
            total_deleted = 0
            
            for i in range(0, len(record_ids), batch_size):
                batch_ids = record_ids[i:i + batch_size]
                deleted_count = session.query(LogEntry).filter(LogEntry.id.in_(batch_ids)).delete(synchronize_session=False)
                total_deleted += deleted_count
                session.commit()
            
            return total_deleted
            
        except Exception as e:
            logger.error(f"Error deleting records: {e}")
            session.rollback()
            return 0
    
    def get_retention_info(self) -> dict:
        """Get current retention configuration and statistics"""
        config = self.config_manager.get_config()
        
        with get_db_session() as session:
            total_records = session.query(func.count(LogEntry.id)).scalar()
            
            # Get oldest and newest record timestamps
            oldest_record = session.query(func.min(LogEntry.timestamp)).scalar()
            newest_record = session.query(func.max(LogEntry.timestamp)).scalar()
            
            # Calculate what would be deleted
            time_based_deletions = 0
            count_based_deletions = 0
            
            if config.time_based.enabled:
                duration_seconds = self.config_manager.parse_duration(config.time_based.duration)
                cutoff_timestamp = time.time() - duration_seconds
                time_based_deletions = session.query(func.count(LogEntry.id)).filter(
                    LogEntry.timestamp < cutoff_timestamp
                ).scalar()
            
            if config.count_based.enabled and total_records > config.count_based.max_entries:
                count_based_deletions = total_records - config.count_based.max_entries
            
            oldest_dt = datetime.fromtimestamp(oldest_record) if oldest_record else None
            newest_dt = datetime.fromtimestamp(newest_record) if newest_record else None
            
            return {
                'config': {
                    'time_based': {
                        'enabled': config.time_based.enabled,
                        'duration': config.time_based.duration
                    },
                    'count_based': {
                        'enabled': config.count_based.enabled,
                        'max_entries': config.count_based.max_entries
                    },
                    'export': {
                        'enabled': config.export.enabled,
                        'format': config.export.format,
                        'output_directory': config.export.output_directory
                    }
                },
                'statistics': {
                    'total_records': total_records,
                    'oldest_record': oldest_dt.isoformat() if oldest_dt else None,
                    'newest_record': newest_dt.isoformat() if newest_dt else None,
                    'records_to_delete_time_based': time_based_deletions,
                    'records_to_delete_count_based': count_based_deletions,
                    'total_records_to_delete': len(set(
                        self._get_time_based_deletion_ids(session, config.time_based.duration) if config.time_based.enabled else []
                    ) | set(
                        self._get_count_based_deletion_ids(session, config.count_based.max_entries) if config.count_based.enabled else []
                    ))
                }
            }