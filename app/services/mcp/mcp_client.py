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
        Call MCP Excel server tool
        
        Args:
            tool_name: Name of the MCP tool to call
            arguments: Tool arguments (filepath will be auto-injected)
            
        Returns:
            Tool result
            
        Raises:
            Exception: If tool invocation fails
        """
        try:
            await self.initialize()
            
            # Inject resolved filepath if tool requires it
            if "filepath" in arguments and self._filepath:
                arguments["filepath"] = self._filepath
            
            self._log_debug(f"Calling MCP tool: {tool_name}")
            self._log_debug(f"Arguments: {arguments}")
            
            async with self.client:
                result = await self.client.call_tool(
                    name=tool_name,
                    arguments=arguments
                )
                
                self._log_debug(f"Tool result: {result}")
                return result
        
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            raise Exception(f"MCP tool {tool_name} failed: {str(e)}")
    
    def create_langchain_tool(
        self,
        tool_name: str,
        description: str,
        args_schema: Optional[Dict] = None
    ) -> Callable:
        """
        Create a LangChain-compatible tool function
        
        Args:
            tool_name: MCP tool name
            description: Tool description
            args_schema: Argument schema (optional)
            
        Returns:
            Synchronous function that can be used as LangChain tool
        """
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
        sync_tool_func.__doc__ = description
        
        return sync_tool_func
    
    def get_standard_tools(self) -> Dict[str, Callable]:
        """
        Get standard MCP Excel tools for LangChain
        
        Returns:
            Dictionary of tool name to function mappings
        """
        tools = {
            # Workbook Operations
            "create_workbook": self.create_langchain_tool(
                "create_workbook",
                "Create a new Excel workbook"
            ),
            "create_worksheet": self.create_langchain_tool(
                "create_worksheet",
                "Create a new worksheet in the Excel file"
            ),
            "get_workbook_metadata": self.create_langchain_tool(
                "get_workbook_metadata",
                "Get metadata about workbook including sheets and ranges"
            ),
            
            # Data Operations
            "write_data_to_excel": self.create_langchain_tool(
                "write_data_to_excel",
                "Write data to Excel worksheet"
            ),
            "read_data_from_excel": self.create_langchain_tool(
                "read_data_from_excel",
                "Read data from Excel worksheet"
            ),
            
            # Formatting Operations
            "format_range": self.create_langchain_tool(
                "format_range",
                "Apply formatting to a range of cells"
            ),
            
            # Formula Operations
            "apply_formula": self.create_langchain_tool(
                "apply_formula",
                "Apply Excel formula to a cell"
            ),
            "validate_formula_syntax": self.create_langchain_tool(
                "validate_formula_syntax",
                "Validate Excel formula syntax without applying it"
            ),
            
            # Chart Operations
            "create_chart": self.create_langchain_tool(
                "create_chart",
                "Create a chart in the worksheet"
            ),
            
            # Pivot & Table Operations
            "create_pivot_table": self.create_langchain_tool(
                "create_pivot_table",
                "Create pivot table in worksheet"
            ),
            "create_table": self.create_langchain_tool(
                "create_table",
                "Create a native Excel table from a specified range of data"
            ),
            
            # Cell Operations
            "merge_cells": self.create_langchain_tool(
                "merge_cells",
                "Merge a range of cells"
            ),
            "unmerge_cells": self.create_langchain_tool(
                "unmerge_cells",
                "Unmerge a previously merged range of cells"
            ),
            "get_merged_cells": self.create_langchain_tool(
                "get_merged_cells",
                "Get merged cells in a worksheet"
            ),
            
            # Worksheet Operations
            "copy_worksheet": self.create_langchain_tool(
                "copy_worksheet",
                "Copy worksheet within workbook"
            ),
            "delete_worksheet": self.create_langchain_tool(
                "delete_worksheet",
                "Delete worksheet from workbook"
            ),
            "rename_worksheet": self.create_langchain_tool(
                "rename_worksheet",
                "Rename worksheet in workbook"
            ),
            
            # Range Operations
            "copy_range": self.create_langchain_tool(
                "copy_range",
                "Copy a range of cells to another location"
            ),
            "delete_range": self.create_langchain_tool(
                "delete_range",
                "Delete a range of cells and shift remaining cells"
            ),
            "validate_excel_range": self.create_langchain_tool(
                "validate_excel_range",
                "Validate if a range exists and is properly formatted"
            ),
            
            # Row & Column Operations
            "insert_rows": self.create_langchain_tool(
                "insert_rows",
                "Insert one or more rows starting at the specified row"
            ),
            "insert_columns": self.create_langchain_tool(
                "insert_columns",
                "Insert one or more columns starting at the specified column"
            ),
            "delete_sheet_rows": self.create_langchain_tool(
                "delete_sheet_rows",
                "Delete one or more rows starting at the specified row"
            ),
            "delete_sheet_columns": self.create_langchain_tool(
                "delete_sheet_columns",
                "Delete one or more columns starting at the specified column"
            ),
            
            # Data Validation
            "get_data_validation_info": self.create_langchain_tool(
                "get_data_validation_info",
                "Get data validation rules and metadata for a worksheet"
            ),
        }
        
        logger.info(f"Created {len(tools)} LangChain tools from MCP server")
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
