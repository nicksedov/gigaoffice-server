"""
MCP Task Execution API Router
FastAPI router for MCP-based spreadsheet task execution endpoints
"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from loguru import logger

from app.models.api.mcp_task import (
    MCPTaskExecuteRequest,
    MCPTaskExecuteResponse,
    MCPTaskProgressResponse,
    ProgressInfo,
    ExecutionResult,
    ExecutionError
)
from app.services.mcp import task_tracker, mcp_executor, TaskState, TaskStatus
from app.services.file_storage import file_storage_manager


mcp_router = APIRouter(prefix="/api/v1/spreadsheets/mcp", tags=["MCP Task Execution"])


@mcp_router.post("/execute", response_model=MCPTaskExecuteResponse)
async def execute_mcp_task(
    request: MCPTaskExecuteRequest,
    background_tasks: BackgroundTasks
):
    """
    Execute MCP task asynchronously
    
    Initiates asynchronous execution of spreadsheet task using MCP and LLM agent.
    Returns immediately with task UUID for progress tracking.
    
    Args:
        request: Task execution request
        background_tasks: FastAPI background tasks
        
    Returns:
        Task execution response with task_id
        
    Raises:
        HTTPException 400: Invalid request parameters
        HTTPException 404: File not found
        HTTPException 500: Internal server error
    """
    try:
        logger.info(
            f"MCP task execution requested: user={request.user_id}, "
            f"file_id={request.file_id}"
        )
        
        # Validate file exists
        file_path = file_storage_manager.get_file_path(request.file_id)
        if not file_path:
            logger.warning(f"File not found: {request.file_id}")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "file_not_found",
                    "message": f"File with ID {request.file_id} not found",
                    "details": None
                }
            )
        
        # Generate task UUID
        task_id = str(uuid.uuid4())
        
        # Convert source_range to dict if provided
        source_range_dict = None
        if request.source_range:
            source_range_dict = request.source_range.model_dump()
        
        # Create task state
        task_state = TaskState(
            task_id=task_id,
            user_id=request.user_id,
            status=TaskStatus.QUEUED,
            prompt=request.prompt,
            file_id=request.file_id,
            source_range=source_range_dict,
            priority=request.priority,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Register task
        task_tracker.create_task(task_state)
        
        # Schedule background execution
        background_tasks.add_task(mcp_executor.execute_task, task_id)
        
        logger.info(f"Task {task_id} queued for execution")
        
        return MCPTaskExecuteResponse(
            task_id=task_id,
            status="queued",
            created_at=task_state.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating MCP task: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Failed to create task",
                "details": {"internal_error": str(e)}
            }
        )


@mcp_router.get("/progress/{task_id}", response_model=MCPTaskProgressResponse)
async def get_task_progress(task_id: str):
    """
    Get MCP task progress
    
    Retrieves current execution status and progress of MCP task.
    
    Args:
        task_id: Task identifier UUID
        
    Returns:
        Task progress response
        
    Raises:
        HTTPException 404: Task not found
        HTTPException 500: Internal server error
    """
    try:
        logger.debug(f"Task progress requested: {task_id}")
        
        # Validate UUID format
        try:
            uuid.UUID(task_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_task_id",
                    "message": "Task ID must be a valid UUID",
                    "details": None
                }
            )
        
        # Get task state
        task = task_tracker.get_task(task_id)
        if not task:
            logger.warning(f"Task not found: {task_id}")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "task_not_found",
                    "message": f"Task with ID {task_id} not found",
                    "details": None
                }
            )
        
        # Build response
        response_data = {
            "task_id": task.task_id,
            "status": task.status.value,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
        
        # Add progress if task is queued or running
        if task.status in [TaskStatus.QUEUED, TaskStatus.RUNNING]:
            response_data["progress"] = ProgressInfo(
                current_step=task.progress.current_step,
                total_steps=task.progress.total_steps,
                step_description=task.progress.step_description,
                percentage=task.progress.percentage
            )
        
        # Add result if completed
        if task.status == TaskStatus.COMPLETED and task.result_data:
            response_data["result"] = ExecutionResult(
                output_file_id=task.result_data.output_file_id,
                operations_performed=task.result_data.operations_performed,
                execution_time=task.result_data.execution_time_seconds
            )
        
        # Add error if failed
        if task.status == TaskStatus.FAILED and task.error_data:
            response_data["error"] = ExecutionError(
                message=task.error_data.error_message,
                failed_step=task.error_data.failed_step,
                error_type=task.error_data.error_type.value
            )
        
        return MCPTaskProgressResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving task progress: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Failed to retrieve task progress",
                "details": {"internal_error": str(e)}
            }
        )
