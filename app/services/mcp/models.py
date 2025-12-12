"""
Internal data models for MCP task execution
Task state, progress tracking, and error handling models
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from uuid import UUID


class TaskStatus(str, Enum):
    """Task execution status"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ErrorType(str, Enum):
    """Error classification types"""
    MCP_CONNECTION_ERROR = "mcp_connection_error"
    MCP_TOOL_ERROR = "mcp_tool_error"
    LLM_ERROR = "llm_error"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT_ERROR = "timeout_error"
    FILE_NOT_FOUND_ERROR = "file_not_found_error"


@dataclass
class ProgressData:
    """Progress information for task execution"""
    current_step: int = 0
    total_steps: int = 0
    step_description: str = ""
    percentage: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "step_description": self.step_description,
            "percentage": self.percentage
        }


@dataclass
class ResultData:
    """Execution result data"""
    output_file_id: str
    output_filepath: str
    operations_performed: List[str] = field(default_factory=list)
    execution_time_seconds: float = 0.0
    agent_iterations: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "output_file_id": self.output_file_id,
            "operations_performed": self.operations_performed,
            "execution_time": self.execution_time_seconds
        }


@dataclass
class ErrorData:
    """Execution error data"""
    error_message: str
    failed_step: str
    error_type: ErrorType
    stack_trace: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "message": self.error_message,
            "failed_step": self.failed_step,
            "error_type": self.error_type.value
        }


@dataclass
class TaskState:
    """Complete state of an MCP execution task"""
    task_id: str
    user_id: int
    status: TaskStatus
    prompt: str
    file_id: str
    resolved_filepath: Optional[str] = None
    source_range: Optional[Dict[str, Any]] = None
    progress: ProgressData = field(default_factory=ProgressData)
    result_data: Optional[ResultData] = None
    error_data: Optional[ErrorData] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    priority: int = 0

    def update_progress(self, current_step: int, total_steps: int, description: str):
        """Update task progress"""
        self.progress.current_step = current_step
        self.progress.total_steps = total_steps
        self.progress.step_description = description
        
        # Calculate percentage
        if total_steps > 0:
            self.progress.percentage = int((current_step / total_steps) * 100)
        else:
            self.progress.percentage = 0
        
        self.updated_at = datetime.now()

    def set_status(self, status: TaskStatus):
        """Update task status"""
        self.status = status
        self.updated_at = datetime.now()

    def set_result(self, result: ResultData):
        """Set task result and mark as completed"""
        self.result_data = result
        self.status = TaskStatus.COMPLETED
        self.progress.percentage = 100
        self.updated_at = datetime.now()

    def set_error(self, error: ErrorData):
        """Set task error and mark as failed"""
        self.error_data = error
        self.status = TaskStatus.FAILED
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert task state to dictionary for API response"""
        data = {
            "task_id": self.task_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

        # Add progress if task is queued or running
        if self.status in [TaskStatus.QUEUED, TaskStatus.RUNNING]:
            data["progress"] = self.progress.to_dict()

        # Add result if completed
        if self.status == TaskStatus.COMPLETED and self.result_data:
            data["result"] = self.result_data.to_dict()

        # Add error if failed
        if self.status == TaskStatus.FAILED and self.error_data:
            data["error"] = self.error_data.to_dict()

        return data
