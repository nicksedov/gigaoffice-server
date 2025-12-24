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
from .tool_schemas import get_tools_list_for_prompt


# Configuration from environment
MCP_SERVER_URL = os.getenv("MCP_EXCEL_SERVER_URL", "")
LLM_API_URL = os.getenv("GIGACHAT_BASE_URL", "https://ollama.ai-gateway.ru/v1")
LLM_API_KEY = os.getenv("GIGACHAT_API_KEY", "none")
LLM_MODEL_NAME = os.getenv("GIGACHAT_MODEL_NAME", "gpt-oss")
LLM_TEMPERATURE = float(os.getenv("GIGACHAT_TEMPERATURE", "0.2"))  # Reduced from 0.7 to reduce hallucination
MAX_AGENT_ITERATIONS = int(os.getenv("MAX_AGENT_ITERATIONS", "30"))  # Reduced from 50 to limit hallucination accumulation
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
                api_key=LLM_API_KEY,
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
        # Generate the complete tool list
        tools_list = get_tools_list_for_prompt()
        
        system_prompt = f"""You are a helpful assistant that executes Excel spreadsheet tasks.
Your task is to methodically execute the user's request step-by-step:

1. Analyze the task requirements carefully
2. Use the available MCP Excel tools to accomplish each operation
3. Verify each step completes successfully before moving to the next
4. Report progress clearly at each stage
5. Handle errors gracefully and provide informative messages

IMPORTANT NOTES ABOUT TOOL USAGE:

- Each tool has detailed parameter schemas that specify:
  * Required vs optional parameters
  * Parameter types and descriptions
  * Default values for optional parameters

- The 'filepath' parameter is AUTOMATICALLY resolved from the file_id and injected by the system
  * DO NOT attempt to provide or specify the 'filepath' parameter in your tool calls
  * The system handles file path resolution internally
  * Focus on providing the other required parameters for each tool

- Consult each tool's parameter schema to understand:
  * Which parameters are required (must be provided)
  * Which parameters are optional (can be omitted, have defaults)
  * What each parameter expects (data types, format)

- When calling tools, provide parameters according to their schemas:
  * Use exact parameter names as specified
  * Provide values of the correct type
  * Include all required parameters
  * Optional parameters can be omitted or explicitly set

TASK COMPLETION CHECKLIST:
- Before finishing, re-read the original user request carefully
- List all operations explicitly or implicitly required by the request
- Verify each operation has been executed successfully
- Only provide final answer when ALL operations are complete
- If uncertain whether task is complete, continue with the next logical step
- Multi-step tasks (e.g., "create and populate") require multiple tool calls

{tools_list}

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
        
        # Tools are already decorated with @tool and have schemas attached
        # Convert dict to list
        langchain_tools = list(tools_dict.values())
        
        logger.info(f"Loaded {len(langchain_tools)} MCP tools with complete parameter schemas")
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
                handle_parsing_errors=True,
                return_intermediate_steps=True,
                early_stopping_method="generate"
            )
            task_tracker.update_progress(task_id, 4, 10, "Agent created")
            
            # Step 5: Prepare task input
            task_input = {
                "input": self._format_task_prompt(task)
            }
            task_tracker.update_progress(task_id, 5, 10, "Executing agent")
            
            # Step 6: Execute agent with timeout
            logger.info(f"Task {task_id}: Starting agent execution with intermediate steps enabled")
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(agent_executor.invoke, task_input),
                    timeout=TASK_EXECUTION_TIMEOUT
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Task execution exceeded {TASK_EXECUTION_TIMEOUT}s timeout")
            
            # Log agent execution details
            num_intermediate_steps = len(result.get("intermediate_steps", []))
            logger.info(
                f"Task {task_id}: Agent completed with {num_intermediate_steps} intermediate steps, "
                f"{result.get('agent_iterations', 0)} total iterations"
            )
            
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
            # ValueError can be from file validation or tool name validation
            error_str = str(e)
            if "Invalid tool name" in error_str or "Did you mean" in error_str:
                # Tool validation error with helpful suggestions
                self._handle_error(
                    task_id, 
                    error_str, 
                    "Tool name validation", 
                    ErrorType.MCP_TOOL_ERROR
                )
            else:
                # File validation error
                self._handle_error(task_id, error_str, "File validation", ErrorType.FILE_NOT_FOUND_ERROR)
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Task {task_id} failed: {e}\n{error_trace}")
            
            # Check if it's a tool-related error
            error_str = str(e)
            if "not a valid tool" in error_str or "tool" in error_str.lower():
                # Enhanced error message for tool issues
                enhanced_msg = f"{error_str}\n\nThis may be due to:\n"
                enhanced_msg += "- Using incorrect tool name (check spelling)\n"
                enhanced_msg += "- Adding invalid prefix like 'excel.' to tool name\n"
                enhanced_msg += "- Tool not available in current configuration\n"
                self._handle_error(task_id, enhanced_msg, "Tool invocation", ErrorType.MCP_TOOL_ERROR)
            else:
                self._handle_error(task_id, error_str, "Task execution", ErrorType.MCP_TOOL_ERROR)
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
        
        # Log extracted operations for debugging
        if operations:
            logger.debug(f"Extracted {len(operations)} operations: {operations}")
        else:
            logger.warning("No operations extracted from agent result")
        
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
