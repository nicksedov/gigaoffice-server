"""
Task Tracker Service
Manages task state storage and retrieval with thread-safe operations
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
from threading import Lock
from loguru import logger

from .models import TaskState, TaskStatus


class TaskTracker:
    """
    Task tracker for managing MCP task state
    
    Provides thread-safe access to task information with in-memory storage
    and automatic cleanup of old tasks.
    """
    
    def __init__(self, retention_hours: int = 24):
        """
        Initialize task tracker
        
        Args:
            retention_hours: How long to keep completed tasks (default: 24 hours)
        """
        self._tasks: Dict[str, TaskState] = {}
        self._lock = Lock()
        self._retention_hours = retention_hours
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info(f"TaskTracker initialized with {retention_hours}h retention")
    
    def create_task(self, task_state: TaskState) -> TaskState:
        """
        Create a new task record
        
        Args:
            task_state: Initial task state
            
        Returns:
            Created task state
        """
        with self._lock:
            self._tasks[task_state.task_id] = task_state
            logger.info(
                f"Task created: {task_state.task_id} "
                f"(user: {task_state.user_id}, file: {task_state.file_id})"
            )
        return task_state
    
    def get_task(self, task_id: str) -> Optional[TaskState]:
        """
        Retrieve task state by UUID
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task state if found, None otherwise
        """
        with self._lock:
            return self._tasks.get(task_id)
    
    def update_task(self, task_id: str, task_state: TaskState):
        """
        Update task state
        
        Args:
            task_id: Task identifier
            task_state: Updated task state
        """
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id] = task_state
                logger.debug(f"Task updated: {task_id} (status: {task_state.status.value})")
    
    def update_status(self, task_id: str, status: TaskStatus):
        """
        Update task status
        
        Args:
            task_id: Task identifier
            status: New status
        """
        task = self.get_task(task_id)
        if task:
            task.set_status(status)
            self.update_task(task_id, task)
            logger.info(f"Task {task_id} status changed to: {status.value}")
    
    def update_progress(
        self,
        task_id: str,
        current_step: int,
        total_steps: int,
        description: str
    ):
        """
        Update task progress
        
        Args:
            task_id: Task identifier
            current_step: Current step number
            total_steps: Total estimated steps
            description: Step description
        """
        task = self.get_task(task_id)
        if task:
            task.update_progress(current_step, total_steps, description)
            self.update_task(task_id, task)
            logger.debug(
                f"Task {task_id} progress: {current_step}/{total_steps} "
                f"({task.progress.percentage}%) - {description}"
            )
    
    def get_all_tasks(self) -> Dict[str, TaskState]:
        """
        Get all tasks (for debugging/monitoring)
        
        Returns:
            Dictionary of all tasks
        """
        with self._lock:
            return self._tasks.copy()
    
    def count_by_status(self) -> Dict[TaskStatus, int]:
        """
        Count tasks by status
        
        Returns:
            Dictionary mapping status to count
        """
        counts = {status: 0 for status in TaskStatus}
        with self._lock:
            for task in self._tasks.values():
                counts[task.status] += 1
        return counts
    
    async def cleanup_old_tasks(self):
        """
        Background task to clean up completed tasks after retention period
        """
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                cutoff_time = datetime.now() - timedelta(hours=self._retention_hours)
                tasks_to_remove = []
                
                with self._lock:
                    for task_id, task in self._tasks.items():
                        # Remove completed or failed tasks older than retention period
                        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                            if task.updated_at < cutoff_time:
                                tasks_to_remove.append(task_id)
                    
                    for task_id in tasks_to_remove:
                        del self._tasks[task_id]
                
                if tasks_to_remove:
                    logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
                    
            except Exception as e:
                logger.error(f"Error in task cleanup: {e}")
    
    def start_cleanup_task(self):
        """Start background cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self.cleanup_old_tasks())
            logger.info("Background task cleanup started")
    
    def stop_cleanup_task(self):
        """Stop background cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
            logger.info("Background task cleanup stopped")


# Create global task tracker instance
_retention_hours = int(os.getenv("TASK_RETENTION_HOURS", "24"))
task_tracker = TaskTracker(retention_hours=_retention_hours)
