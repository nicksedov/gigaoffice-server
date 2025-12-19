"""
Simple test for sync wrapper - no external dependencies required
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.mcp.mcp_client import _run_async_in_sync_context


def test_basic_functionality():
    """Test basic sync wrapper functionality"""
    async def sample_async_func():
        await asyncio.sleep(0.01)
        return "test_result"
    
    result = _run_async_in_sync_context(sample_async_func())
    assert result == "test_result", f"Expected 'test_result', got {result}"
    print("✓ Basic functionality test passed")


def test_exception_handling():
    """Test sync wrapper exception handling"""
    async def failing_async_func():
        await asyncio.sleep(0.01)
        raise ValueError("Test error")
    
    try:
        _run_async_in_sync_context(failing_async_func())
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert str(e) == "Test error"
        print("✓ Exception handling test passed")


def test_with_parameters():
    """Test sync wrapper with function parameters"""
    async def async_func_with_params(a, b, c=None):
        await asyncio.sleep(0.01)
        return f"{a}-{b}-{c}"
    
    result = _run_async_in_sync_context(async_func_with_params(1, 2, c=3))
    assert result == "1-2-3", f"Expected '1-2-3', got {result}"
    print("✓ Parameters test passed")


def test_complex_return_types():
    """Test sync wrapper with complex return types"""
    async def async_func_dict():
        await asyncio.sleep(0.01)
        return {"key": "value", "number": 42}
    
    result = _run_async_in_sync_context(async_func_dict())
    assert isinstance(result, dict)
    assert result["key"] == "value"
    assert result["number"] == 42
    print("✓ Complex types test passed")


def test_no_event_loop():
    """Test when no event loop exists"""
    async def simple_func():
        return "no_loop_result"
    
    result = _run_async_in_sync_context(simple_func())
    assert result == "no_loop_result"
    print("✓ No event loop test passed")


if __name__ == "__main__":
    print("Running sync wrapper tests...\n")
    
    try:
        test_basic_functionality()
        test_exception_handling()
        test_with_parameters()
        test_complex_return_types()
        test_no_event_loop()
        
        print("\n" + "="*50)
        print("✓ ALL TESTS PASSED!")
        print("="*50)
        print("\nThe sync wrapper is working correctly.")
        print("This fix resolves the StructuredTool synchronous invocation error.")
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
"""
Simple test for sync wrapper - no external dependencies required
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.mcp.mcp_client import _run_async_in_sync_context


def test_basic_functionality():
    """Test basic sync wrapper functionality"""
    async def sample_async_func():
        await asyncio.sleep(0.01)
        return "test_result"
    
    result = _run_async_in_sync_context(sample_async_func())
    assert result == "test_result", f"Expected 'test_result', got {result}"
    print("✓ Basic functionality test passed")


def test_exception_handling():
    """Test sync wrapper exception handling"""
    async def failing_async_func():
        await asyncio.sleep(0.01)
        raise ValueError("Test error")
    
    try:
        _run_async_in_sync_context(failing_async_func())
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert str(e) == "Test error"
        print("✓ Exception handling test passed")


def test_with_parameters():
    """Test sync wrapper with function parameters"""
    async def async_func_with_params(a, b, c=None):
        await asyncio.sleep(0.01)
        return f"{a}-{b}-{c}"
    
    result = _run_async_in_sync_context(async_func_with_params(1, 2, c=3))
    assert result == "1-2-3", f"Expected '1-2-3', got {result}"
    print("✓ Parameters test passed")


def test_complex_return_types():
    """Test sync wrapper with complex return types"""
    async def async_func_dict():
        await asyncio.sleep(0.01)
        return {"key": "value", "number": 42}
    
    result = _run_async_in_sync_context(async_func_dict())
    assert isinstance(result, dict)
    assert result["key"] == "value"
    assert result["number"] == 42
    print("✓ Complex types test passed")


def test_no_event_loop():
    """Test when no event loop exists"""
    async def simple_func():
        return "no_loop_result"
    
    result = _run_async_in_sync_context(simple_func())
    assert result == "no_loop_result"
    print("✓ No event loop test passed")


if __name__ == "__main__":
    print("Running sync wrapper tests...\n")
    
    try:
        test_basic_functionality()
        test_exception_handling()
        test_with_parameters()
        test_complex_return_types()
        test_no_event_loop()
        
        print("\n" + "="*50)
        print("✓ ALL TESTS PASSED!")
        print("="*50)
        print("\nThe sync wrapper is working correctly.")
        print("This fix resolves the StructuredTool synchronous invocation error.")
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
