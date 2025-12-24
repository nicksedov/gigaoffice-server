"""
MCP Excel Client Wrapper
Wraps FastMCP client to provide LangChain-compatible tools for Excel operations
"""

import asyncio
import os
from typing import Any, Dict, Optional, Callable
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from loguru import logger
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from langchain.tools import tool

from .tool_schemas import (
    get_tool_schema,
    create_pydantic_schema,
    generate_enhanced_docstring,
    list_available_tools,
    validate_tool_name
)


def _run_async_in_sync_context(coro):
    """
    Execute async coroutine in synchronous context
    
    This utility function bridges the async/sync gap by managing event loop context.
    It detects if an event loop is already running and handles execution accordingly.
    
    Args:
        coro: Coroutine to execute
        
    Returns:
        Result of coroutine execution
        
    Raises:
        Exception: Any exception raised by the coroutine
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        
        # Check if loop is already running
        if loop.is_running():
            # Loop is running - execute in new thread with new event loop
            with ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            # No loop running - use existing loop
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop exists - create and run
        return asyncio.run(coro)


class MCPExcelClient:
    """
    MCP Excel client wrapper for LangChain integration
    
    Handles MCP server communication and tool invocation with automatic
    file path resolution from file_id.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 30,
        debug: bool = False
    ):
        """
        Initialize MCP Excel client
        
        Args:
            base_url: MCP server URL (defaults to MCP_EXCEL_SERVER_URL env var)
            timeout: Request timeout in seconds
            debug: Enable debug logging
        """
        self.base_url = (base_url or os.getenv("MCP_EXCEL_SERVER_URL", "")).rstrip("/")
        self.timeout = timeout
        self.debug = debug
        self.client: Optional[Client] = None
        self.transport: Optional[StreamableHttpTransport] = None
        self._filepath: Optional[str] = None  # Resolved filepath for current task
        
        if not self.base_url:
            raise ValueError("MCP_EXCEL_SERVER_URL environment variable not set")
        
        logger.info(f"MCPExcelClient initialized with URL: {self.base_url}")
    
    def set_filepath(self, filepath: str):
        """
        Set the resolved filepath for MCP operations
        
        Args:
            filepath: Absolute path to Excel file
        """
        self._filepath = filepath
        logger.debug(f"MCP client filepath set to: {filepath}")
    
    def _log_debug(self, message: str):
        """Log debug message if enabled"""
        if self.debug:
            logger.debug(f"[MCP Client] {message}")
    
    async def initialize(self):
        """Initialize FastMCP client and transport"""
        if self.client is None:
            self._log_debug("Initializing FastMCP client...")
            self.transport = StreamableHttpTransport(url=self.base_url)
            self.client = Client(self.transport)
            self._log_debug("FastMCP client initialized successfully")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call MCP Excel server tool with validation
        
        Args:
            tool_name: Name of the MCP tool to call
            arguments: Tool arguments (filepath will be auto-injected)
            
        Returns:
            Tool result
            
        Raises:
            Exception: If tool invocation fails or tool name is invalid
        """
        try:
            # Validate tool name and get suggestions if invalid
            validation = validate_tool_name(tool_name)
            
            if not validation["valid"]:
                error_msg = validation["error_message"]
                logger.error(f"Invalid tool name: {tool_name}")
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Use corrected name if prefix was stripped
            actual_tool_name = validation.get("corrected_name") or tool_name
            
            if validation.get("corrected_name"):
                logger.info(f"Auto-corrected tool name: '{tool_name}' -> '{actual_tool_name}'")
            
            await self.initialize()
            
            # Inject resolved filepath if tool requires it
            if "filepath" in arguments and self._filepath:
                arguments["filepath"] = self._filepath
            
            self._log_debug(f"Calling MCP tool: {actual_tool_name}")
            self._log_debug(f"Arguments: {arguments}")
            
            async with self.client:
                result = await self.client.call_tool(
                    name=actual_tool_name,
                    arguments=arguments
                )
                
                self._log_debug(f"Tool result: {result}")
                return result
        
        except ValueError as e:
            # Re-raise validation errors with helpful message
            raise e
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            raise Exception(f"MCP tool {tool_name} failed: {str(e)}")
    
    def create_langchain_tool(
        self,
        tool_name: str
    ) -> Callable:
        """
        Create a LangChain-compatible tool function with full schema
        
        Args:
            tool_name: MCP tool name
            
        Returns:
            LangChain tool with complete parameter schema
        """
        # Retrieve schema from registry
        schema = get_tool_schema(tool_name)
        if not schema:
            logger.error(f"No schema found for tool: {tool_name}")
            raise ValueError(f"Tool schema not found: {tool_name}")
        
        # Generate Pydantic model for args_schema
        pydantic_model = create_pydantic_schema(tool_name, schema)
        
        # Generate enhanced docstring
        enhanced_docstring = generate_enhanced_docstring(tool_name, schema)
        
        # Inner async function that performs the actual MCP call
        async def async_tool_func(**kwargs) -> str:
            """Async LangChain tool wrapper"""
            try:
                result = await self.call_tool(tool_name, kwargs)
                return str(result)
            except Exception as e:
                return f"Error: {str(e)}"
        
        # Outer synchronous wrapper that bridges async/sync gap
        def sync_tool_func(**kwargs) -> str:
            """Synchronous LangChain tool wrapper"""
            return _run_async_in_sync_context(async_tool_func(**kwargs))
        
        # Set function metadata for LangChain
        sync_tool_func.__name__ = tool_name
        sync_tool_func.__doc__ = enhanced_docstring
        
        # Apply @tool decorator with args_schema
        decorated_tool = tool(sync_tool_func, args_schema=pydantic_model)
        
        logger.debug(f"Created LangChain tool with schema: {tool_name}")
        return decorated_tool
    
    def get_standard_tools(self) -> Dict[str, Callable]:
        """
        Get standard MCP Excel tools for LangChain with complete schemas
        
        Returns:
            Dictionary of tool name to function mappings
        """
        tools = {}
        available_tool_names = list_available_tools()
        
        for tool_name in available_tool_names:
            try:
                tool_func = self.create_langchain_tool(tool_name)
                tools[tool_name] = tool_func
            except Exception as e:
                logger.error(f"Failed to create tool {tool_name}: {e}")
        
        logger.info(f"Created {len(tools)} LangChain tools with complete schemas from MCP server")
        return tools
    
    async def cleanup(self):
        """Cleanup client resources"""
        if self.client:
            await self.client.__aexit__(None, None, None)
        self.client = None
        self.transport = None
        logger.debug("MCP client cleaned up")


def create_mcp_client(
    filepath: str,
    base_url: Optional[str] = None,
    debug: bool = False
) -> MCPExcelClient:
    """
    Factory function to create and configure MCP client
    
    Args:
        filepath: Resolved absolute path to Excel file
        base_url: MCP server URL (optional)
        debug: Enable debug logging
        
    Returns:
        Configured MCP Excel client
    """
    client = MCPExcelClient(base_url=base_url, debug=debug)
    client.set_filepath(filepath)
    return client
    filepath: str,
    base_url: Optional[str] = None,
    debug: bool = False
) -> MCPExcelClient:
    """
    Factory function to create and configure MCP client
    
    Args:
        filepath: Resolved absolute path to Excel file
        base_url: MCP server URL (optional)
        debug: Enable debug logging
        
    Returns:
        Configured MCP Excel client
    """
    client = MCPExcelClient(base_url=base_url, debug=debug)
    client.set_filepath(filepath)
    return client
