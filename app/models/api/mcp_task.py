"""
API Models for MCP Task Execution
Data models for MCP-based spreadsheet task execution requests and responses
"""

from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class SourceRange(BaseModel):
    """Source data range specification"""
    sheet_name: str = Field(..., description="Sheet name")
    start_cell: Optional[str] = Field(None, description="Starting cell (e.g., 'A1')")
    end_cell: Optional[str] = Field(None, description="Ending cell (e.g., 'D10')")


class MCPTaskExecuteRequest(BaseModel):
    """Request model for MCP task execution"""
    prompt: str = Field(..., min_length=1, max_length=10000, description="Natural language task description")
    file_id: str = Field(..., description="UUID of uploaded Excel file")
    source_range: Optional[SourceRange] = Field(None, description="Source data range information")
    user_id: int = Field(..., gt=0, description="User identifier")
    priority: int = Field(0, ge=0, le=10, description="Task priority (0-10)")

    @field_validator('file_id')
    @classmethod
    def validate_file_id(cls, v: str) -> str:
        """Validate file_id is a valid UUID format"""
        try:
            UUID(v)
            return v
        except ValueError:
            raise ValueError("file_id must be a valid UUID")


class MCPTaskExecuteResponse(BaseModel):
    """Response model for task execution initiation"""
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field("queued", description="Task status")
    created_at: datetime = Field(..., description="Task creation timestamp")


class ProgressInfo(BaseModel):
    """Progress information"""
    current_step: int = Field(..., ge=0, description="Current step number (1-based)")
    total_steps: int = Field(..., ge=0, description="Total estimated steps")
    step_description: str = Field(..., description="Description of current operation")
    percentage: int = Field(..., ge=0, le=100, description="Completion percentage")


class ExecutionResult(BaseModel):
    """Execution result information"""
    output_file_id: str = Field(..., description="UUID of result file")
    operations_performed: List[str] = Field(..., description="List of completed operations")
    execution_time: float = Field(..., ge=0, description="Total execution time in seconds")


class ExecutionError(BaseModel):
    """Execution error information"""
    message: str = Field(..., description="Error description")
    failed_step: str = Field(..., description="Step where failure occurred")
    error_type: str = Field(..., description="Error classification")


class MCPTaskProgressResponse(BaseModel):
    """Response model for task progress retrieval"""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Current status: queued, running, completed, failed")
    current_phase: Optional[str] = Field(None, description="Current workflow phase")
    progress: Optional[ProgressInfo] = Field(None, description="Progress information")
    result: Optional[ExecutionResult] = Field(None, description="Task result (only when completed)")
    error: Optional[ExecutionError] = Field(None, description="Error information (only when failed)")
    clarifications: Optional[Dict] = Field(None, description="Pending clarification questions")
    plan_summary: Optional[Dict] = Field(None, description="Execution plan (if available)")
    analysis_result: Optional[Dict] = Field(None, description="Analysis results (if available)")
    verification_result: Optional[Dict] = Field(None, description="Verification results (if available)")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class ClarificationResponseItem(BaseModel):
    """Single clarification response"""
    clarification_id: str = Field(..., description="Unique question identifier")
    answer: str = Field(..., min_length=1, description="User's answer")


class MCPTaskClarifyRequest(BaseModel):
    """Request model for submitting clarification responses"""
    responses: List[ClarificationResponseItem] = Field(
        ..., 
        min_length=1,
        description="List of clarification responses"
    )


class MCPTaskClarifyResponse(BaseModel):
    """Response model for clarification submission"""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Updated task status")
    accepted_count: int = Field(..., ge=0, description="Number of responses accepted")
    updated_at: datetime = Field(..., description="Status update timestamp")


class MCPTaskCancelResponse(BaseModel):
    """Response model for task cancellation"""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field("cancelled", description="Task status after cancellation")
    cancelled_at: datetime = Field(..., description="Cancellation timestamp")
