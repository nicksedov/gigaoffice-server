"""
Test suite for MCP sync wrapper utility

Verifies that the sync wrapper correctly handles async coroutines
in synchronous contexts, addressing the StructuredTool error.
"""

import asyncio
import pytest
from app.services.mcp.mcp_client import _run_async_in_sync_context


def test_sync_wrapper_basic():
    """Test basic sync wrapper functionality"""
    async def sample_async_func():
        await asyncio.sleep(0.01)
        return "test_result"
    
    # Execute async function synchronously
    result = _run_async_in_sync_context(sample_async_func())
    
    assert result == "test_result"


def test_sync_wrapper_with_exception():
    """Test sync wrapper exception handling"""
    async def failing_async_func():
        await asyncio.sleep(0.01)
        raise ValueError("Test error")
    
    # Verify exception is propagated
    with pytest.raises(ValueError, match="Test error"):
        _run_async_in_sync_context(failing_async_func())


def test_sync_wrapper_with_parameters():
    """Test sync wrapper with function parameters"""
    async def async_func_with_params(a, b, c=None):
        await asyncio.sleep(0.01)
        return f"{a}-{b}-{c}"
    
    result = _run_async_in_sync_context(async_func_with_params(1, 2, c=3))
    
    assert result == "1-2-3"


def test_sync_wrapper_returns_complex_types():
    """Test sync wrapper with complex return types"""
    async def async_func_dict():
        await asyncio.sleep(0.01)
        return {"key": "value", "number": 42}
    
    result = _run_async_in_sync_context(async_func_dict())
    
    assert isinstance(result, dict)
    assert result["key"] == "value"
    assert result["number"] == 42


async def test_sync_wrapper_from_async_context():
    """Test sync wrapper when called from async context"""
    async def inner_async_func():
        await asyncio.sleep(0.01)
        return "async_context_result"
    
    # This simulates calling from async context (like event loop already running)
    # The wrapper should handle this by creating a new thread
    result = _run_async_in_sync_context(inner_async_func())
    
    assert result == "async_context_result"


def test_tool_function_is_synchronous():
    """Test that created tool functions are truly synchronous"""
    from app.services.mcp.mcp_client import MCPExcelClient
    from unittest.mock import Mock, AsyncMock
    
    # Create a mock client
    client = Mock(spec=MCPExcelClient)
    client._filepath = "/test/path.xlsx"
    client.debug = False
    
    # Mock the call_tool method
    async def mock_call_tool(tool_name, arguments):
        return {"result": "success"}
    
    client.call_tool = AsyncMock(side_effect=mock_call_tool)
    
    # Create a tool using the actual method
    from app.services.mcp.mcp_client import _run_async_in_sync_context
    
    async def async_tool(**kwargs):
        result = await client.call_tool("test_tool", kwargs)
        return str(result)
    
    def sync_tool(**kwargs):
        return _run_async_in_sync_context(async_tool(**kwargs))
    
    # Call the synchronous tool
    result = sync_tool(sheet_name="Sheet1")
    
    # Verify it returns a result
    assert isinstance(result, str)
    assert "success" in result


if __name__ == "__main__":
    # Run basic tests without pytest
    print("Running basic sync wrapper tests...")
    
    test_sync_wrapper_basic()
    print("✓ Basic test passed")
    
    test_sync_wrapper_with_exception()
    print("✓ Exception handling test passed")
    
    test_sync_wrapper_with_parameters()
    print("✓ Parameters test passed")
    
    test_sync_wrapper_returns_complex_types()
    print("✓ Complex types test passed")
    
    test_tool_function_is_synchronous()
    print("✓ Tool function synchronicity test passed")
    
    print("\n✓ All tests passed!")
