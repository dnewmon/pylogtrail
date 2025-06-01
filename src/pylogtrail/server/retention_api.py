import logging
from flask import Blueprint, request, jsonify
from typing import Any, Dict

from pylogtrail.config.retention import get_retention_config_manager, RetentionConfig, TimeBasedConfig, CountBasedConfig, ExportConfig, ScheduleConfig
from pylogtrail.retention.manager import RetentionManager

logger = logging.getLogger(__name__)

# Create Blueprint for retention API
retention_bp = Blueprint('retention', __name__, url_prefix='/api/retention')


@retention_bp.route('/settings', methods=['GET'])
def get_retention_settings():
    """Get current retention settings and statistics"""
    try:
        manager = RetentionManager()
        info = manager.get_retention_info()
        return jsonify(info), 200
    except Exception as e:
        logger.error(f"Error getting retention settings: {e}")
        return jsonify({'error': 'Failed to get retention settings'}), 500


@retention_bp.route('/settings', methods=['PUT'])
def update_retention_settings():
    """Update retention settings"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        config_manager = get_retention_config_manager()
        current_config = config_manager.get_config()
        
        # Update time-based settings
        if 'time_based' in data:
            time_data = data['time_based']
            if 'enabled' in time_data:
                current_config.time_based.enabled = bool(time_data['enabled'])
            if 'duration' in time_data:
                # Validate duration format
                try:
                    config_manager.parse_duration(time_data['duration'])
                    current_config.time_based.duration = time_data['duration']
                except ValueError as e:
                    return jsonify({'error': f'Invalid duration format: {e}'}), 400
        
        # Update count-based settings
        if 'count_based' in data:
            count_data = data['count_based']
            if 'enabled' in count_data:
                current_config.count_based.enabled = bool(count_data['enabled'])
            if 'max_entries' in count_data:
                max_entries = int(count_data['max_entries'])
                if max_entries <= 0:
                    return jsonify({'error': 'max_entries must be greater than 0'}), 400
                current_config.count_based.max_entries = max_entries
        
        # Update export settings
        if 'export' in data:
            export_data = data['export']
            if 'enabled' in export_data:
                current_config.export.enabled = bool(export_data['enabled'])
            if 'output_directory' in export_data:
                current_config.export.output_directory = export_data['output_directory']
            if 'include_timestamp' in export_data:
                current_config.export.include_timestamp = bool(export_data['include_timestamp'])
        
        # Update schedule settings
        if 'schedule' in data:
            schedule_data = data['schedule']
            if 'on_startup' in schedule_data:
                current_config.schedule.on_startup = bool(schedule_data['on_startup'])
            if 'interval_hours' in schedule_data:
                interval = int(schedule_data['interval_hours'])
                if interval < 0:
                    return jsonify({'error': 'interval_hours must be >= 0'}), 400
                current_config.schedule.interval_hours = interval
        
        # Save updated configuration
        config_manager.save_config(current_config)
        
        # Return updated settings
        manager = RetentionManager(config_manager)
        info = manager.get_retention_info()
        
        return jsonify({
            'message': 'Retention settings updated successfully',
            'settings': info
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating retention settings: {e}")
        return jsonify({'error': 'Failed to update retention settings'}), 500


@retention_bp.route('/cleanup', methods=['POST'])
def trigger_cleanup():
    """Manually trigger log cleanup"""
    try:
        data = request.get_json() or {}
        dry_run = data.get('dry_run', False)
        
        manager = RetentionManager()
        result = manager.cleanup_logs(dry_run=dry_run)
        
        return jsonify({
            'message': 'Cleanup completed' if not dry_run else 'Dry run completed',
            'result': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return jsonify({'error': 'Failed to perform cleanup'}), 500


@retention_bp.route('/preview', methods=['GET'])
def preview_cleanup():
    """Preview what would be deleted without actually deleting"""
    try:
        manager = RetentionManager()
        result = manager.cleanup_logs(dry_run=True)
        
        return jsonify({
            'message': 'Preview completed',
            'result': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error during cleanup preview: {e}")
        return jsonify({'error': 'Failed to preview cleanup'}), 500


@retention_bp.route('/validate-duration', methods=['POST'])
def validate_duration():
    """Validate a duration string format"""
    try:
        data = request.get_json()
        if not data or 'duration' not in data:
            return jsonify({'error': 'Duration string required'}), 400
        
        duration = data['duration']
        config_manager = get_retention_config_manager()
        
        try:
            seconds = config_manager.parse_duration(duration)
            return jsonify({
                'valid': True,
                'duration': duration,
                'seconds': seconds,
                'human_readable': _seconds_to_human_readable(seconds)
            }), 200
        except ValueError as e:
            return jsonify({
                'valid': False,
                'error': str(e)
            }), 400
            
    except Exception as e:
        logger.error(f"Error validating duration: {e}")
        return jsonify({'error': 'Failed to validate duration'}), 500


def _seconds_to_human_readable(seconds: int) -> str:
    """Convert seconds to human readable format"""
    days = seconds // (24 * 60 * 60)
    remaining = seconds % (24 * 60 * 60)
    hours = remaining // (60 * 60)
    remaining = remaining % (60 * 60)
    minutes = remaining // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    
    if not parts:
        return "0 minutes"
    
    return ", ".join(parts)