"""
Reminders API Router (Smart Reminders System)
Endpoints for creating, listing, retrieving due alerts, snoozing, dismissing, and deleting reminders.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.database.firestore import firestore_service
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/reminders", tags=["Reminders Management"])


class ReminderCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Reminder title/description")
    remind_at: str = Field(..., description="Target trigger time (ISO 8601 string)")
    source_type: Optional[str] = Field(default="custom", description="Source type: note, task, event, custom")
    source_id: Optional[str] = Field(default=None, description="Linked note, task, or event ID")


class ReminderUpdateRequest(BaseModel):
    status: Optional[str] = Field(default=None, description="Status: triggered, dismissed, snoozed, pending")
    remind_at: Optional[str] = Field(default=None, description="Updated trigger time ISO string")
    snooze_minutes: Optional[int] = Field(default=None, description="Minutes to snooze (default: 10)")


@router.get("")
@router.get("/")
async def list_user_reminders(
    status: Optional[str] = Query(default=None, description="Filter by status: pending, triggered, dismissed, snoozed"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve all reminders for current user, ordered by remind_at."""
    uid = current_user.get("user_id", "default_user")
    reminders = firestore_service.list_reminders(user_id=uid, status=status)
    return {"success": True, "count": len(reminders), "reminders": reminders}


@router.get("/due")
async def get_due_reminders(
    now: Optional[str] = Query(default=None, description="Optional ISO timestamp threshold (defaults to current UTC time)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Fetch due pending and snoozed reminders for the logged-in user."""
    uid = current_user.get("user_id", "default_user")
    due = firestore_service.get_due_reminders(user_id=uid, now_iso=now)
    return {"success": True, "count": len(due), "due_reminders": due}


@router.post("", status_code=status.HTTP_201_CREATED)
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_reminder(
    req: ReminderCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new user-scoped reminder."""
    uid = current_user.get("user_id", "default_user")
    reminder = firestore_service.create_reminder(
        user_id=uid,
        title=req.title,
        remind_at_iso=req.remind_at,
        source_type=req.source_type or "custom",
        source_id=req.source_id
    )
    return {"success": True, "reminder": reminder}


@router.patch("/{reminder_id}")
async def update_reminder(
    reminder_id: str,
    req: ReminderUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Dismiss, snooze, or update status of an existing reminder."""
    uid = current_user.get("user_id", "default_user")
    new_status = req.status or ("snoozed" if req.snooze_minutes else "dismissed")
    updated = firestore_service.update_reminder_status(
        user_id=uid,
        reminder_id=reminder_id,
        status=new_status,
        remind_at_iso=req.remind_at,
        snooze_minutes=req.snooze_minutes
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reminder '{reminder_id}' not found or unauthorized."
        )
    return {"success": True, "reminder": updated}


@router.delete("/{reminder_id}")
async def delete_reminder(
    reminder_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a reminder."""
    uid = current_user.get("user_id", "default_user")
    deleted = firestore_service.delete_reminder(user_id=uid, reminder_id=reminder_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reminder '{reminder_id}' not found or unauthorized."
        )
    return {"success": True, "deleted_id": reminder_id}
