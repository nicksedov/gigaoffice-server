#!/usr/bin/env python3
"""
Test script to verify gigachat_factory import works correctly
"""

import sys
import traceback

def test_factory_import():
    """Test that the gigachat_factory can be imported successfully"""
    try:
        print("Testing gigachat_factory import...")
        
        # Test the import
        from app.services.ai.factory import gigachat_factory
        print(f"✓ Successfully imported gigachat_factory: {type(gigachat_factory)}")
        
        # Test that it has the expected methods
        expected_methods = ['get_service', 'get_health', 'get_statistics', 'recreate_services']
        for method in expected_methods:
            if hasattr(gigachat_factory, method):
                print(f"✓ gigachat_factory has method: {method}")
            else:
                print(f"✗ gigachat_factory missing method: {method}")
                return False
        
        # Test getting a service (this will test the compatibility wrapper)
        print("\nTesting get_service method...")
        try:
            # This should work with the compatibility wrapper
            service = gigachat_factory.get_service("generate")
            print(f"✓ Successfully got generate service: {type(service)}")
        except Exception as e:
            print(f"⚠ get_service failed (expected if no configuration): {e}")
        
        try:
            service = gigachat_factory.get_service("classify")
            print(f"✓ Successfully got classify service: {type(service)}")
        except Exception as e:
            print(f"⚠ get_service failed (expected if no configuration): {e}")
        
        print("\n✓ All import tests passed!")
        return True
        
    except ImportError as e:
        print(f"✗ ImportError: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        traceback.print_exc()
        return False

def test_health_endpoint_import():
    """Test that the health endpoint can import successfully"""
    try:
        print("\nTesting health endpoint import...")
        
        # Test importing the health endpoint
        from app.api.endpoints.health import router
        print(f"✓ Successfully imported health router: {type(router)}")
        
        print("✓ Health endpoint import test passed!")
        return True
        
    except ImportError as e:
        print(f"✗ Health endpoint ImportError: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ Health endpoint unexpected error: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("GigaChat Factory Import Test")
    print("=" * 50)
    
    success = True
    success &= test_factory_import()
    success &= test_health_endpoint_import()
    
    print("\n" + "=" * 50)
    if success:
        print("✓ ALL TESTS PASSED - Import fix successful!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)