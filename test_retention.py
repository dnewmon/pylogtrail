#!/usr/bin/env python3
"""
Simple test script to verify the retention system implementation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_config_manager():
    """Test the retention configuration manager"""
    try:
        from pylogtrail.config.retention import RetentionConfigManager
        
        config_manager = RetentionConfigManager()
        config = config_manager.get_config()
        
        print("✅ Configuration Manager Test Passed")
        print(f"   - Time-based retention: {config.time_based.enabled} ({config.time_based.duration})")
        print(f"   - Count-based retention: {config.count_based.enabled} ({config.count_based.max_entries})")
        print(f"   - Export enabled: {config.export.enabled}")
        
        # Test duration parsing
        duration_seconds = config_manager.parse_duration("7d")
        expected_seconds = 7 * 24 * 60 * 60  # 7 days
        assert duration_seconds == expected_seconds, f"Expected {expected_seconds}, got {duration_seconds}"
        
        print("✅ Duration parsing test passed")
        return True
        
    except Exception as e:
        print(f"❌ Configuration Manager Test Failed: {e}")
        return False

def test_retention_manager():
    """Test the retention manager (without database operations)"""
    try:
        from pylogtrail.retention.manager import RetentionManager
        from pylogtrail.config.retention import RetentionConfigManager
        
        # This will test initialization and basic functionality
        config_manager = RetentionConfigManager()
        manager = RetentionManager(config_manager)
        
        print("✅ Retention Manager initialization passed")
        return True
        
    except Exception as e:
        print(f"❌ Retention Manager Test Failed: {e}")
        return False

def test_api_endpoints():
    """Test that API endpoints can be imported"""
    try:
        from pylogtrail.server.retention_api import retention_bp
        
        # Check that the blueprint has the expected routes
        rules = [rule.rule for rule in retention_bp.url_map.iter_rules()]
        expected_routes = ['/api/retention/settings', '/api/retention/cleanup', '/api/retention/preview']
        
        for route in expected_routes:
            if not any(route in rule for rule in rules):
                print(f"❌ Missing route: {route}")
                return False
        
        print("✅ API Endpoints test passed")
        print(f"   - Available routes: {len(rules)}")
        return True
        
    except Exception as e:
        print(f"❌ API Endpoints Test Failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing PyLogTrail Retention System Implementation")
    print("=" * 55)
    
    tests = [
        test_config_manager,
        test_retention_manager,
        test_api_endpoints
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The retention system is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)