"""
MCP Task Execution Service
Orchestrates LangChain agent execution with MCP tools for spreadsheet tasks
"""

import asyncio
import os
import time
import traceback
from typing import Optional
from pathlib import Path
from loguru import logger

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from app.services.file_storage import file_storage_manager
from .models import TaskState, TaskStatus, ResultData, ErrorData, ErrorType
from .task_tracker import task_tracker
from .mcp_client import create_mcp_client, MCPExcelClient


# Configuration from environment
MCP_SERVER_URL = os.getenv("MCP_EXCEL_SERVER_URL", "")
LLM_API_URL = os.getenv("GIGACHAT_API_URL", "https://ollama.ai-gateway.ru/v1")
LLM_MODEL_NAME = os.getenv("GIGACHAT_MODEL_NAME", "gpt-oss")
LLM_TEMPERATURE = float(os.getenv("GIGACHAT_TEMPERATURE", "0.7"))
MAX_AGENT_ITERATIONS = int(os.getenv("MAX_AGENT_ITERATIONS", "50"))
TASK_EXECUTION_TIMEOUT = int(os.getenv("TASK_EXECUTION_TIMEOUT", "300"))


class MCPExecutor:
    """
    MCP task executor with LangChain agent orchestration
    
    Manages the complete lifecycle of MCP task execution including:
    - File path resolution
    - Agent initialization with MCP tools
    - Task execution with progress tracking
    - Error handling and recovery
    """
    
    def __init__(self):
        """Initialize MCP executor"""
        self._llm = None
        self._mcp_client: Optional[MCPExcelClient] = None
        logger.info("MCPExecutor initialized")
    
    def _get_llm(self) -> ChatOpenAI:
        """
        Get or create LLM client for agent
        
        Returns:
            Configured ChatOpenAI client
        """
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=LLM_MODEL_NAME,
                temperature=LLM_TEMPERATURE,
                api_key="none",  # API key not required for internal LLM
                base_url=LLM_API_URL
            )
            logger.info(f"LLM client created: {LLM_MODEL_NAME} @ {LLM_API_URL}")
        return self._llm
    
    def _create_agent_prompt(self) -> ChatPromptTemplate:
        """
        Create agent prompt template
        
        Returns:
            ChatPromptTemplate for agent
        """
        system_prompt = """You are a helpful assistant that executes Excel spreadsheet tasks.
Your task is to methodically execute the user's request step-by-step:

1. Analyze the task requirements carefully
2. Use the available MCP Excel tools to accomplish each operation
3. Verify each step completes successfully before moving to the next
4. Report progress clearly at each stage
5. Handle errors gracefully and provide informative messages

Available tools:
Workbook Operations:
- create_workbook: Create a new Excel workbook
- create_worksheet: Create a new worksheet
- get_workbook_metadata: Get metadata about workbook including sheets and ranges

Data Operations:
- write_data_to_excel: Write data to cells
- read_data_from_excel: Read data from cells

Formatting Operations:
- format_range: Apply formatting to cells

Formula Operations:
- apply_formula: Apply Excel formulas
- validate_formula_syntax: Validate formula syntax without applying

Chart Operations:
- create_chart: Create charts

Pivot & Table Operations:
- create_pivot_table: Create pivot table from data range
- create_table: Create native Excel table from range

Cell Operations:
- merge_cells: Merge cell ranges
- unmerge_cells: Unmerge previously merged cells
- get_merged_cells: Get list of merged cell ranges

Worksheet Operations:
- copy_worksheet: Copy worksheet within workbook
- delete_worksheet: Delete worksheet from workbook
- rename_worksheet: Rename existing worksheet

Range Operations:
- copy_range: Copy cell range to another location
- delete_range: Delete range and shift cells
- validate_excel_range: Validate range existence and format

Row & Column Operations:
- insert_rows: Insert rows at position
- insert_columns: Insert columns at position
- delete_sheet_rows: Delete rows starting at position
- delete_sheet_columns: Delete columns starting at position

Data Validation:
- get_data_validation_info: Get data validation rules and metadata

Important: The filepath parameter is automatically set for all tools. 
Do not specify filepath in your tool calls.

Execute the task systematically and report your progress."""

        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
    
    def _create_langchain_tools(self, mcp_client: MCPExcelClient):
        """
        Create LangChain tools from MCP client
        
        Args:
            mcp_client: Configured MCP client
            
        Returns:
            List of LangChain tool functions
        """
        tools_dict = mcp_client.get_standard_tools()
        
        # Wrap each tool with @tool decorator for LangChain
        langchain_tools = []
        for tool_name, tool_func in tools_dict.items():
            # Create tool with decorator
            decorated_tool = tool(tool_func)
            langchain_tools.append(decorated_tool)
        
        return langchain_tools
    
    async def execute_task(self, task_id: str):
        """
        Execute MCP task asynchronously
        
        Args:
            task_id: Task identifier
        """
        start_time = time.time()
        task = task_tracker.get_task(task_id)
        
        if not task:
            logger.error(f"Task not found: {task_id}")
            return
        
        try:
            logger.info(f"Starting task execution: {task_id}")
            
            # Update status to running
            task_tracker.update_status(task_id, TaskStatus.RUNNING)
            task_tracker.update_progress(task_id, 0, 10, "Initializing task")
            
            # Step 1: Resolve file path
            file_path = file_storage_manager.get_file_path(task.file_id)
            if not file_path:
                raise ValueError(f"File not found for file_id: {task.file_id}")
            
            resolved_filepath = str(file_path.absolute())
            task.resolved_filepath = resolved_filepath
            task_tracker.update_task(task_id, task)
            
            logger.info(f"File resolved: {task.file_id} -> {resolved_filepath}")
            task_tracker.update_progress(task_id, 1, 10, "File path resolved")
            
            # Step 2: Initialize MCP client
            self._mcp_client = create_mcp_client(
                filepath=resolved_filepath,
                base_url=MCP_SERVER_URL,
                debug=True
            )
            task_tracker.update_progress(task_id, 2, 10, "MCP client initialized")
            
            # Step 3: Create LangChain tools
            tools = self._create_langchain_tools(self._mcp_client)
            task_tracker.update_progress(task_id, 3, 10, "Tools created")
            
            # Step 4: Create agent
            llm = self._get_llm()
            prompt = self._create_agent_prompt()
            agent = create_tool_calling_agent(llm, tools, prompt)
            
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                max_iterations=MAX_AGENT_ITERATIONS,
                handle_parsing_errors=True
            )
            task_tracker.update_progress(task_id, 4, 10, "Agent created")
            
            # Step 5: Prepare task input
            task_input = {
                "input": self._format_task_prompt(task)
            }
            task_tracker.update_progress(task_id, 5, 10, "Executing agent")
            
            # Step 6: Execute agent with timeout
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(agent_executor.invoke, task_input),
                    timeout=TASK_EXECUTION_TIMEOUT
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Task execution exceeded {TASK_EXECUTION_TIMEOUT}s timeout")
            
            task_tracker.update_progress(task_id, 9, 10, "Agent completed")
            
            # Step 7: Prepare result
            execution_time = time.time() - start_time
            
            result_data = ResultData(
                output_file_id=task.file_id,
                output_filepath=resolved_filepath,
                operations_performed=self._extract_operations(result),
                execution_time_seconds=execution_time,
                agent_iterations=result.get("agent_iterations", 0)
            )
            
            task.set_result(result_data)
            task_tracker.update_task(task_id, task)
            
            logger.info(
                f"Task {task_id} completed successfully in {execution_time:.2f}s"
            )
            
        except TimeoutError as e:
            self._handle_error(task_id, str(e), "Task execution", ErrorType.TIMEOUT_ERROR)
        except ValueError as e:
            self._handle_error(task_id, str(e), "File validation", ErrorType.FILE_NOT_FOUND_ERROR)
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Task {task_id} failed: {e}\n{error_trace}")
            self._handle_error(task_id, str(e), "Task execution", ErrorType.MCP_TOOL_ERROR)
        finally:
            # Cleanup MCP client
            if self._mcp_client:
                await self._mcp_client.cleanup()
                self._mcp_client = None
    
    def _format_task_prompt(self, task: TaskState) -> str:
        """
        Format task prompt for agent
        
        Args:
            task: Task state
            
        Returns:
            Formatted prompt string
        """
        prompt = task.prompt
        
        # Add source range info if provided
        if task.source_range:
            range_info = f"\n\nSource data range:\n"
            range_info += f"- Sheet: {task.source_range.get('sheet_name', 'Sheet1')}\n"
            if task.source_range.get('start_cell'):
                range_info += f"- Start cell: {task.source_range['start_cell']}\n"
            if task.source_range.get('end_cell'):
                range_info += f"- End cell: {task.source_range['end_cell']}\n"
            prompt += range_info
        
        return prompt
    
    def _extract_operations(self, agent_result: dict) -> list:
        """
        Extract operations performed from agent result
        
        Args:
            agent_result: Agent execution result
            
        Returns:
            List of operation names
        """
        operations = []
        
        # Try to extract from intermediate steps
        if "intermediate_steps" in agent_result:
            for step in agent_result["intermediate_steps"]:
                if isinstance(step, tuple) and len(step) > 0:
                    action = step[0]
                    if hasattr(action, "tool"):
                        operations.append(action.tool)
        
        return operations if operations else ["task_completed"]
    
    def _handle_error(
        self,
        task_id: str,
        error_message: str,
        failed_step: str,
        error_type: ErrorType
    ):
        """
        Handle task execution error
        
        Args:
            task_id: Task identifier
            error_message: Error description
            failed_step: Step where error occurred
            error_type: Error classification
        """
        task = task_tracker.get_task(task_id)
        if task:
            error_data = ErrorData(
                error_message=error_message,
                failed_step=failed_step,
                error_type=error_type
            )
            task.set_error(error_data)
            task_tracker.update_task(task_id, task)
            
            logger.error(
                f"Task {task_id} failed at '{failed_step}': "
                f"{error_type.value} - {error_message}"
            )


# Global executor instance
mcp_executor = MCPExecutor()
