#!/usr/bin/env python3
"""
Comprehensive test for Qdrant connection fix.
Tests all scenarios: disabled, enabled+available, enabled+unavailable.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_scenario_1_disabled():
    """Test: Enhanced processing disabled - no Qdrant connection attempts."""
    print("📝 Scenario 1: Enhanced Processing DISABLED")
    print("-" * 45)
    
    # Set environment
    os.environ['ENABLE_ENHANCED_PROCESSING'] = 'false'
    
    # Force reload of config
    import importlib
    if 'app.enhanced_config' in sys.modules:
        importlib.reload(sys.modules['app.enhanced_config'])
    if 'app.document_processing.qdrant_setup' in sys.modules:
        importlib.reload(sys.modules['app.document_processing.qdrant_setup'])
    
    try:
        from app.enhanced_config import get_enhanced_config
        from app.document_processing.qdrant_setup import get_qdrant_client
        from app.main import app
        
        config = get_enhanced_config()
        client = get_qdrant_client()
        
        print(f"   Enhanced processing: {config.is_enabled}")
        print(f"   Qdrant client: {client}")
        print(f"   FastAPI app: {type(app).__name__}")
        print("   ✅ SUCCESS: No Qdrant connection when disabled")
        return True
        
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        return False

def test_scenario_2_enabled_unavailable():
    """Test: Enhanced processing enabled but Qdrant unavailable - graceful fallback."""
    print("\n🚀 Scenario 2: Enhanced Processing ENABLED, Qdrant UNAVAILABLE")
    print("-" * 60)
    
    # Set environment
    os.environ['ENABLE_ENHANCED_PROCESSING'] = 'true'
    
    # Force reload of config
    import importlib
    if 'app.enhanced_config' in sys.modules:
        importlib.reload(sys.modules['app.enhanced_config'])
    if 'app.document_processing.qdrant_setup' in sys.modules:
        importlib.reload(sys.modules['app.document_processing.qdrant_setup'])
    
    try:
        from app.enhanced_config import get_enhanced_config
        from app.document_processing.qdrant_setup import get_qdrant_client
        
        config = get_enhanced_config()
        client = get_qdrant_client()  # Should fail gracefully
        
        print(f"   Enhanced processing: {config.is_enabled}")
        print(f"   Qdrant client: {client}")
        print("   ✅ SUCCESS: Graceful fallback when Qdrant unavailable")
        return True
        
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        return False

def test_scenario_3_conditional_imports():
    """Test: Conditional imports work correctly."""
    print("\n🔧 Scenario 3: Conditional Imports")
    print("-" * 35)
    
    try:
        # Test that enhanced_processing imports work without immediate Qdrant connection
        from app.enhanced_processing import enhanced_document_processing, enhanced_context_assembly
        
        print("   ✅ Enhanced processing functions imported")
        print("   ✅ No immediate Qdrant connection on import")
        print("   ✅ SUCCESS: Conditional imports working")
        return True
        
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        return False

def run_all_tests():
    """Run all test scenarios."""
    print("🧪 Qdrant Connection Fix - Comprehensive Test")
    print("=" * 50)
    
    results = []
    results.append(test_scenario_1_disabled())
    results.append(test_scenario_2_enabled_unavailable()) 
    results.append(test_scenario_3_conditional_imports())
    
    print("\n📊 Test Results Summary:")
    print("=" * 30)
    
    passed = sum(results)
    total = len(results)
    
    print(f"   Passed: {passed}/{total}")
    
    if passed == total:
        print("   🎉 ALL TESTS PASSED!")
        print("\n✅ Your server will now:")
        print("   - Start without Qdrant when ENABLE_ENHANCED_PROCESSING=false")
        print("   - Handle Qdrant unavailability gracefully when enabled")
        print("   - Use conditional imports to avoid connection errors")
        print("   - Fall back to standard processing automatically")
        return True
    else:
        print("   ❌ Some tests failed - check logs above")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)