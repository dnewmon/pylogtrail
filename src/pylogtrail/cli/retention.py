#!/usr/bin/env python3
"""
CLI utility for managing PyLogTrail retention settings
"""

import argparse
import sys
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pylogtrail.config.retention import get_retention_config_manager
from pylogtrail.retention.manager import RetentionManager


def cmd_show_settings(args):
    """Show current retention settings"""
    try:
        manager = RetentionManager()
        info = manager.get_retention_info()
        
        print("=== Current Retention Settings ===")
        
        # Configuration
        config = info['config']
        print(f"\nTime-based retention:")
        print(f"  Enabled: {config['time_based']['enabled']}")
        print(f"  Duration: {config['time_based']['duration']}")
        
        print(f"\nCount-based retention:")
        print(f"  Enabled: {config['count_based']['enabled']}")
        print(f"  Max entries: {config['count_based']['max_entries']:,}")
        
        print(f"\nExport settings:")
        print(f"  Enabled: {config['export']['enabled']}")
        print(f"  Format: {config['export']['format']}")
        print(f"  Output directory: {config['export']['output_directory']}")
        
        # Statistics
        stats = info['statistics']
        print(f"\n=== Database Statistics ===")
        print(f"Total records: {stats['total_records']:,}")
        print(f"Oldest record: {stats['oldest_record']}")
        print(f"Newest record: {stats['newest_record']}")
        print(f"Records to delete (time-based): {stats['records_to_delete_time_based']:,}")
        print(f"Records to delete (count-based): {stats['records_to_delete_count_based']:,}")
        print(f"Total records to delete: {stats['total_records_to_delete']:,}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


def cmd_cleanup(args):
    """Run retention cleanup"""
    try:
        manager = RetentionManager()
        
        if args.dry_run:
            print("=== Dry Run: Preview Cleanup ===")
        else:
            print("=== Running Cleanup ===")
        
        result = manager.cleanup_logs(dry_run=args.dry_run)
        
        print(f"Records deleted: {result['records_deleted']:,}")
        print(f"Time-based deletions: {result['time_based_deletions']:,}")
        print(f"Count-based deletions: {result['count_based_deletions']:,}")
        
        if result.get('export_file'):
            print(f"Export file: {result['export_file']}")
        
        if args.dry_run:
            print("\nNote: This was a dry run. No records were actually deleted.")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


def cmd_update_settings(args):
    """Update retention settings"""
    try:
        config_manager = get_retention_config_manager()
        config = config_manager.get_config()
        
        # Update time-based settings
        if args.time_duration:
            try:
                config_manager.parse_duration(args.time_duration)
                config.time_based.duration = args.time_duration
                print(f"Updated time-based duration to: {args.time_duration}")
            except ValueError as e:
                print(f"Invalid duration format: {e}")
                return 1
        
        if args.time_enabled is not None:
            config.time_based.enabled = args.time_enabled
            print(f"Time-based retention enabled: {args.time_enabled}")
        
        # Update count-based settings
        if args.count_max:
            if args.count_max <= 0:
                print("Max entries must be greater than 0")
                return 1
            config.count_based.max_entries = args.count_max
            print(f"Updated max entries to: {args.count_max:,}")
        
        if args.count_enabled is not None:
            config.count_based.enabled = args.count_enabled
            print(f"Count-based retention enabled: {args.count_enabled}")
        
        # Update export settings
        if args.export_enabled is not None:
            config.export.enabled = args.export_enabled
            print(f"Export enabled: {args.export_enabled}")
        
        if args.export_dir:
            config.export.output_directory = args.export_dir
            print(f"Export directory updated to: {args.export_dir}")
        
        # Save changes
        config_manager.save_config(config)
        print("\nSettings saved successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="PyLogTrail Retention Management CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Show settings command
    show_parser = subparsers.add_parser('show', help='Show current retention settings')
    show_parser.set_defaults(func=cmd_show_settings)
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Run retention cleanup')
    cleanup_parser.add_argument('--dry-run', action='store_true', 
                               help='Preview what would be deleted without actually deleting')
    cleanup_parser.set_defaults(func=cmd_cleanup)
    
    # Update settings command
    update_parser = subparsers.add_parser('update', help='Update retention settings')
    
    # Time-based options
    update_parser.add_argument('--time-duration', help='Set time-based retention duration (e.g., "7d", "2d12h")')
    update_parser.add_argument('--time-enabled', type=bool, help='Enable/disable time-based retention')
    
    # Count-based options
    update_parser.add_argument('--count-max', type=int, help='Set maximum number of log entries')
    update_parser.add_argument('--count-enabled', type=bool, help='Enable/disable count-based retention')
    
    # Export options
    update_parser.add_argument('--export-enabled', type=bool, help='Enable/disable export of deleted records')
    update_parser.add_argument('--export-dir', help='Set export directory path')
    
    update_parser.set_defaults(func=cmd_update_settings)
    
    # Parse arguments and run command
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())