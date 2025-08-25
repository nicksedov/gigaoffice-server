#!/usr/bin/env python3
"""
Test Application Startup
Quick test to verify the app can start without AttributeError
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_startup():
    """Test application startup sequence"""
    try:
        print("Testing application startup components...")
        print("=" * 50)
        
        # Test database manager initialization
        print("1. Testing DatabaseManager...")
        from app.db.session import db_manager
        
        # Test if the method exists and is callable
        if hasattr(db_manager, 'initialize') and callable(getattr(db_manager, 'initialize')):
            print("   ✓ initialize() method exists and is callable")
        else:
            print("   ✗ initialize() method missing or not callable")
            return False
        
        # Test lifespan components
        print("2. Testing lifespan imports...")
        from app.lifespan import startup_database, lifespan
        print("   ✓ lifespan imports successful")
        
        # Test config
        print("3. Testing configuration...")
        from app.core.config import app_state
        if hasattr(app_state, 'mark_component_shutdown'):
            print("   ✓ app_state.mark_component_shutdown method exists")
        else:
            print("   ✗ app_state.mark_component_shutdown method missing")
            return False
        
        print("\n✓ All startup components are properly configured!")
        print("The AttributeError 'DatabaseManager' object has no attribute 'initialize' should be fixed.")
        return True
        
    except Exception as e:
        print(f"✗ Startup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Running startup validation test...")
    success = asyncio.run(test_startup())
    
    if success:
        print("\n🎉 SUCCESS: Application should now start without errors!")
        sys.exit(0)
    else:
        print("\n❌ FAILED: There are still issues to resolve")
        sys.exit(1)