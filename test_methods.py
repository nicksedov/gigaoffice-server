#!/usr/bin/env python3
"""
Simple test to validate DatabaseManager has the required methods
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.db.session import db_manager
    
    print("Testing DatabaseManager methods...")
    print("=" * 40)
    
    # Check if initialize method exists
    if hasattr(db_manager, 'initialize'):
        print("✓ initialize() method exists")
    else:
        print("✗ initialize() method missing")
        sys.exit(1)
    
    # Check if cleanup method exists
    if hasattr(db_manager, 'cleanup'):
        print("✓ cleanup() method exists")
    else:
        print("✗ cleanup() method missing")
        sys.exit(1)
    
    # Check if init_default_data method exists
    if hasattr(db_manager, 'init_default_data'):
        print("✓ init_default_data() method exists")
    else:
        print("✗ init_default_data() method missing")
        sys.exit(1)
    
    print("\n✓ All required methods are present!")
    print("The AttributeError should be fixed.")
    
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)