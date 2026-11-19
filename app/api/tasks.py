"""
Tasks API Router (Milestone 4 — Firestore CRUD)
Direct REST endpoints for task retrieval, creation, updates, and deletion.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.database.firestore import firestore_service
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/tasks", tags=["Tasks Management"])


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    due_date: Optional[str] = Field(default=None, description="Due date YYYY-MM-DD")
    priority: str = Field(default="medium", description="Priority: low, medium, high")
    status: str = Field(default="pending", description="Status: pending, in_progress, completed")


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


@router.get("")
async def list_tasks(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    priority: Optional[str] = Query(default=None, description="Filter by priority"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve all tasks stored in Firestore for the current user."""
    uid = current_user.get("user_id")
    filter_uid = uid if uid != "default_user" else None
    tasks = firestore_service.get_tasks(status=status, priority=priority, user_id=filter_uid)
    return {"count": len(tasks), "tasks": tasks}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_task(
    req: TaskCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new task in Firestore associated with the current user."""
    uid = current_user.get("user_id", "default_user")
    task = firestore_service.add_task(
        title=req.title,
        due_date=req.due_date,
        priority=req.priority,
        status=req.status,
        user_id=uid
    )
    return {"success": True, "task": task}


@router.patch("/{task_id}")
async def update_task(task_id: str, req: TaskUpdateRequest):
    """Update task details in Firestore."""
    updated = firestore_service.update_task(task_id, req.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    return {"success": True, "task": updated}


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """Delete a task from Firestore."""
    deleted = firestore_service.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    return {"success": True, "task_id": task_id}
