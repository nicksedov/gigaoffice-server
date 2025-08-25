#!/usr/bin/env python3
"""
Test Database Initialization
Simple test to verify the new initialize() method works correctly
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.db.session import db_manager
    from app.core.config import get_settings
    from loguru import logger

    async def test_database_initialization():
        """Test the database initialization process"""
        print("Testing database initialization...")
        
        try:
            # Test the initialize method
            await db_manager.initialize()
            print("✓ Database initialization completed successfully")
            
            # Test connection check
            is_connected = db_manager.check_connection()
            print(f"✓ Database connection: {'connected' if is_connected else 'failed'}")
            
            # Test database info
            db_info = db_manager.get_db_info()
            print(f"✓ Database info: {db_info.get('database_name', 'unknown')}")
            
            # Test cleanup
            await db_manager.cleanup()
            print("✓ Database cleanup completed successfully")
            
            return True
            
        except Exception as e:
            print(f"✗ Database initialization failed: {e}")
            logger.error(f"Test failed: {e}")
            return False

    if __name__ == "__main__":
        print("Running database initialization test...")
        print("=" * 50)
        
        # Run the test
        success = asyncio.run(test_database_initialization())
        
        if success:
            print("\n✓ All tests passed!")
            sys.exit(0)
        else:
            print("\n✗ Tests failed!")
            sys.exit(1)

except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)