"""
Sample test file to verify code analysis system functionality.

This file intentionally contains unused imports and type errors for testing.
"""

# These are intentionally unused imports for testing
import os
import sys
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import json
import re

# Actually used imports
from pathlib import Path
from dataclasses import dataclass


@dataclass
class TestClass:
    """Test class for analysis."""
    name: str
    value: int
    # This type reference is invalid - NoSuchType doesn't exist
    data: "NoSuchType"  # Should trigger type error


def test_function(param1: str, param2: int) -> Path:
    """
    Test function with type annotations.
    
    Args:
        param1: First parameter
        param2: Second parameter (unused in body)
    
    Returns:
        Path object
    """
    # Only using param1, param2 is unused
    result = Path(param1)
    return result


def function_with_missing_type_import(value) -> UserModel:
    """
    This function references UserModel in return type but doesn't import it.
    Should trigger a missing import error.
    """
    return value


# This import is used via decorator pattern (if this were FastAPI)
from typing import Any

# Using Any in type annotation
def process_data(data: Any) -> Any:
    """Process arbitrary data."""
    return data


# Unused class definition
class UnusedClass:
    """This class is defined but never instantiated or referenced."""
    pass


if __name__ == "__main__":
    # Use test_function
    result = test_function("/tmp", 42)
    print(f"Result: {result}")
    
    # Create TestClass instance
    obj = TestClass(name="test", value=123, data=None)
    print(f"Object: {obj}")
