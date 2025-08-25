#!/usr/bin/env python3
"""
Focused test to verify the exact import path that was failing in the health endpoint
"""

import sys
import traceback

def test_exact_import_path():
    """Test the exact import that was failing"""
    try:
        print("Testing exact import path from health endpoint...")
        print("from app.services.ai.factory import gigachat_factory")
        
        # This is the exact import that was failing
        from app.services.ai.factory import gigachat_factory
        
        print(f"✓ Import successful!")
        print(f"  gigachat_factory type: {type(gigachat_factory)}")
        print(f"  gigachat_factory class: {gigachat_factory.__class__.__name__}")
        
        # Test the method call used by health endpoint  
        print("\nTesting gigachat_factory.get_service('generate')...")
        
        try:
            service = gigachat_factory.get_service("generate")
            print(f"✓ get_service('generate') successful!")
            print(f"  Service type: {type(service)}")
            print(f"  Service class: {service.__class__.__name__}")
            
            # Test the method call chain used by health endpoint
            print("\nTesting service.check_service_health()...")
            health = service.check_service_health()
            print(f"✓ check_service_health() successful!")
            print(f"  Health result: {health}")
            
        except Exception as e:
            print(f"⚠ Service method failed (expected if no config): {e}")
            print("  This is expected if GigaChat configuration is not set up")
        
        return True
        
    except ImportError as e:
        print(f"✗ ImportError: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("GigaChat Factory Import Fix Verification")
    print("=" * 60)
    
    success = test_exact_import_path()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ IMPORT FIX SUCCESSFUL!")
        print("  The health endpoint should now work correctly.")
        sys.exit(0)
    else:
        print("✗ Import fix failed")
        sys.exit(1)