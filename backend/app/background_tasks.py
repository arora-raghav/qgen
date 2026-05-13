"""
Background task management for document processing
"""

import asyncio
import logging
import uuid
from datetime import datetime,timezone
from typing import Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, asdict
from .supabase_client import supabase_service

logger = logging.getLogger(__name__)

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskType(str, Enum):
    SCHEMA_GENERATION = "schema_generation"
    DATASET_GENERATION = "dataset_generation"
    DOCUMENT_PROCESSING = "document_processing"

@dataclass
class TaskInfo:
    task_id: str
    task_type: TaskType
    status: TaskStatus
    project_id: str
    user_id: str
    progress: int = 0
    message: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat() if value else None
        return data

class BackgroundTaskManager:
    def __init__(self):
        self.tasks: Dict[str, TaskInfo] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}

    def create_task(
        self, 
        task_type: TaskType, 
        project_id: str, 
        user_id: str, 
        task_func: Callable,
        **kwargs
    ) -> str:
        """Create and start a new background task"""
        task_id = str(uuid.uuid4())
        
        # Create task info
        task_info = TaskInfo(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            project_id=project_id,
            user_id=user_id,
            message="Task created"
        )
        
        self.tasks[task_id] = task_info
        
        # Start the async task
        async_task = asyncio.create_task(
            self._run_task(task_id, task_func, **kwargs)
        )
        self.running_tasks[task_id] = async_task
        
        logger.info(f"Created task {task_id} of type {task_type} for project {project_id}")
        return task_id

    async def _run_task(self, task_id: str, task_func: Callable, **kwargs):
        """Run a background task with error handling and status updates"""
        try:
            # Update task status to running
            await self._update_task_status(
                task_id, 
                TaskStatus.RUNNING, 
                message="Task started",
                started_at=datetime.now(timezone.utc)
            )
            
            # Execute the actual task function
            if asyncio.iscoroutinefunction(task_func):
                result = await task_func(
                    task_id,
                    self.tasks[task_id].project_id,
                    self.tasks[task_id].user_id,
                    **kwargs,
                )
            else:
                result = await asyncio.to_thread(
                    task_func,
                    task_id,
                    self.tasks[task_id].project_id,
                    self.tasks[task_id].user_id,
                    **kwargs,
                )
            # Update task status to completed
            await self._update_task_status(
                task_id,
                TaskStatus.COMPLETED,
                message="Task completed successfully",
                progress=100,
                result=result,
                completed_at=datetime.now(timezone.utc)
            )
            
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Task {task_id} failed: {error_msg}", exc_info=True)
            
            # Update task status to failed
            await self._update_task_status(
                task_id,
                TaskStatus.FAILED,
                message="Task failed",
                error=error_msg,
                completed_at=datetime.now(timezone.utc)
            )
        finally:
            # Clean up the running task reference
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]

    async def _update_task_status(
        self, 
        task_id: str, 
        status: TaskStatus, 
        message: str = "", 
        progress: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ):
        """Update task status in memory and database"""
        if task_id not in self.tasks:
            return
        
        task_info = self.tasks[task_id]
        task_info.status = status
        task_info.message = message
        
        if progress is not None:
            task_info.progress = progress
        if result is not None:
            task_info.result = result
        if error is not None:
            task_info.error = error
        if started_at is not None:
            task_info.started_at = started_at
        if completed_at is not None:
            task_info.completed_at = completed_at
        
        # Save to database
        try:
            # Prepare result data (include error in result if present)
            result_data = result or {}
            if error:
                result_data["error"] = error
                result_data["message"] = message
            
            processing_job_data = {
                "id": task_id,
                "project_id": task_info.project_id,
                "job_type": task_info.task_type.value,
                "status": status.value,
                "progress": task_info.progress,
                "result": result_data,
                "started_at": started_at.isoformat() if started_at else None,
                "completed_at": completed_at.isoformat() if completed_at else None
            }
            
            # Upsert to processing_jobs table using service client
            supabase_service.get_service_client().table("processing_jobs").upsert(processing_job_data).execute()
            
        except Exception as db_error:
            logger.error(f"Failed to update task status in database: {db_error}")

    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get current task status, falling back to database if not in memory."""
        task = self.tasks.get(task_id)
        if task:
            return task
        
        # Fallback: check database
        try:
            from .supabase_client import supabase_service
            result = supabase_service.get_service_client().table("processing_jobs").select("*").eq("id", task_id).single().execute()
            if result.data:
                row = result.data[0] if isinstance(result.data, list) else result.data
                task_info = TaskInfo(
                    task_id=row["id"],
                    task_type=TaskType(row.get("task_type", "schema_generation")),
                    status=TaskStatus(row.get("status", "pending")),
                    project_id=row.get("project_id", ""),
                    user_id="",
                    progress=row.get("progress", 0),
                    message=row.get("message", ""),
                    result=row.get("result"),
                    error=row.get("error_message"),
                )
                # Cache it in memory for future lookups
                self.tasks[task_id] = task_info
                return task_info
        except Exception as e:
            logger.warning(f"Failed to load task {task_id} from database: {e}")
        
        return None

    def get_project_tasks(self, project_id: str) -> list[TaskInfo]:
        """Get all tasks for a project"""
        return [task for task in self.tasks.values() if task.project_id == project_id]

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        task = self.tasks.get(task_id)
        if task and task.status not in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
            await self._update_task_status(
                task_id, 
                TaskStatus.CANCELLED, 
                message="Task cancelled by user",
                completed_at=datetime.now(timezone.utc)
            )
            return True
        return False

    async def update_task_progress(self, task_id: str, progress: int, message: str = ""):
        """Update task progress (called from within task functions)"""
        # Only update if still active
        task = self.tasks.get(task_id)
        if task and task.status not in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
            await self._update_task_status(task_id, TaskStatus.RUNNING, message, progress)

# Global task manager instance
task_manager = BackgroundTaskManager()

# Helper function to get task manager
def get_task_manager() -> BackgroundTaskManager:
    return task_manager
