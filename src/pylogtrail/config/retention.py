import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class TimeBasedConfig:
    enabled: bool
    duration: str


@dataclass
class CountBasedConfig:
    enabled: bool
    max_entries: int


@dataclass
class ExportConfig:
    enabled: bool
    format: str
    output_directory: str
    include_timestamp: bool


@dataclass
class ScheduleConfig:
    on_startup: bool
    interval_hours: int
    last_execution: Optional[str] = None  # ISO format UTC timestamp


@dataclass
class RetentionConfig:
    time_based: TimeBasedConfig
    count_based: CountBasedConfig
    export: ExportConfig
    schedule: ScheduleConfig


class RetentionConfigManager:
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # Look for config file in project root
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "retention_config.yml"
        
        self.config_path = Path(config_path)
        self._config: Optional[RetentionConfig] = None
    
    def load_config(self) -> RetentionConfig:
        """Load retention configuration from YAML file"""
        if not self.config_path.exists():
            # Return default configuration if file doesn't exist
            return self._get_default_config()
        
        with open(self.config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        retention_data = config_data.get('retention', {})
        
        time_based_data = retention_data.get('time_based', {})
        time_based = TimeBasedConfig(
            enabled=time_based_data.get('enabled', True),
            duration=time_based_data.get('duration', '7d')
        )
        
        count_based_data = retention_data.get('count_based', {})
        count_based = CountBasedConfig(
            enabled=count_based_data.get('enabled', False),
            max_entries=count_based_data.get('max_entries', 10000)
        )
        
        export_data = retention_data.get('export', {})
        export = ExportConfig(
            enabled=export_data.get('enabled', True),
            format=export_data.get('format', 'csv_zip'),
            output_directory=export_data.get('output_directory', 'exports'),
            include_timestamp=export_data.get('include_timestamp', True)
        )
        
        schedule_data = retention_data.get('schedule', {})
        schedule = ScheduleConfig(
            on_startup=schedule_data.get('on_startup', True),
            interval_hours=schedule_data.get('interval_hours', 24),
            last_execution=schedule_data.get('last_execution')
        )
        
        self._config = RetentionConfig(
            time_based=time_based,
            count_based=count_based,
            export=export,
            schedule=schedule
        )
        
        return self._config
    
    def save_config(self, config: RetentionConfig) -> None:
        """Save retention configuration to YAML file"""
        config_data = {
            'retention': {
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
                    'output_directory': config.export.output_directory,
                    'include_timestamp': config.export.include_timestamp
                },
                'schedule': {
                    'on_startup': config.schedule.on_startup,
                    'interval_hours': config.schedule.interval_hours,
                    'last_execution': config.schedule.last_execution
                }
            }
        }
        
        # Ensure parent directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, indent=2)
        
        self._config = config
    
    def get_config(self) -> RetentionConfig:
        """Get current configuration, loading from file if not already loaded"""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def update_last_execution(self, timestamp: str) -> None:
        """Update the last execution timestamp and save to file"""
        config = self.get_config()
        config.schedule.last_execution = timestamp
        self.save_config(config)
    
    def _get_default_config(self) -> RetentionConfig:
        """Return default retention configuration"""
        return RetentionConfig(
            time_based=TimeBasedConfig(enabled=True, duration='7d'),
            count_based=CountBasedConfig(enabled=False, max_entries=10000),
            export=ExportConfig(
                enabled=True,
                format='csv_zip',
                output_directory='exports',
                include_timestamp=True
            ),
            schedule=ScheduleConfig(on_startup=True, interval_hours=24, last_execution=None)
        )
    
    @staticmethod
    def parse_duration(duration_str: str) -> int:
        """Parse duration string to seconds
        
        Supports formats like:
        - "7d" (7 days)
        - "2d12h" (2 days 12 hours)
        - "1h30m" (1 hour 30 minutes)
        - "45m" (45 minutes)
        """
        # Pattern to match days, hours, minutes
        pattern = r'(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?'
        match = re.match(pattern, duration_str.strip())
        
        if not match:
            raise ValueError(f"Invalid duration format: {duration_str}")
        
        days, hours, minutes = match.groups()
        
        total_seconds = 0
        if days:
            total_seconds += int(days) * 24 * 60 * 60
        if hours:
            total_seconds += int(hours) * 60 * 60
        if minutes:
            total_seconds += int(minutes) * 60
        
        if total_seconds == 0:
            raise ValueError(f"Duration must be greater than 0: {duration_str}")
        
        return total_seconds


# Global config manager instance
_config_manager = None


def get_retention_config_manager() -> RetentionConfigManager:
    """Get global retention config manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = RetentionConfigManager()
    return _config_manager