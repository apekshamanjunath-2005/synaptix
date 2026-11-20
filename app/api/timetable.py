"""
Timetable API Router for Synaptix
Provides user-editable daily & weekly timetable schedules persisted in Firestore.
Supports day-level customization, instant week-wide replication, and per-block management.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.database.firestore import firestore_service
from app.api.auth import get_optional_user

router = APIRouter(prefix="/api/timetable", tags=["User Timetable Management"])


class TimeBlock(BaseModel):
    id: Optional[str] = Field(default=None, description="Unique block identifier (auto-assigned if omitted)")
    start_time: str = Field(..., description="Start time in 24-hr format (e.g. '09:00')")
    end_time: str = Field(..., description="End time in 24-hr format (e.g. '10:30')")
    title: str = Field(..., min_length=1, max_length=200, description="Block title or activity name")
    category: str = Field(
        default="focus",
        description="Activity category: 'focus', 'meeting', 'break', 'wrapup', or 'personal'"
    )


class DayTimetableRequest(BaseModel):
    day: str = Field(..., description="Day of the week (e.g. 'monday', 'tuesday')")
    blocks: List[TimeBlock] = Field(default_factory=list, description="List of time blocks for the specified day")
    apply_to_week: Optional[bool] = Field(
        default=False,
        description="When true, copies these blocks across all 7 days of the week"
    )
    days: Optional[List[str]] = Field(
        default=None,
        description="Optional list of target days to replicate to (e.g. ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'])"
    )


class TimetableResponse(BaseModel):
    user_id: str
    updated_at: str
    days: Dict[str, List[Dict[str, Any]]]


@router.get("", response_model=Dict[str, Any])
@router.get("/", response_model=Dict[str, Any])
async def get_timetable(
    day: Optional[str] = Query(default=None, description="Optional weekday to filter (e.g. 'monday')"),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Retrieve user-editable weekly timetable from Firestore.
    If day is supplied, also returns that specific day's blocks.
    """
    uid = current_user.get("user_id", "default_user") if current_user else "default_user"
    table = firestore_service.get_user_timetable(uid)

    response = {
        "success": True,
        "user_id": uid,
        "updated_at": table.get("updated_at"),
        "days": table.get("days", {}),
    }

    if day:
        normalized_day = day.strip().lower()
        response["selected_day"] = normalized_day
        response["blocks"] = table.get("days", {}).get(normalized_day, [])

    return response


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def save_timetable_day(
    req: DayTimetableRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Save or update time blocks for a day, with optional replication across the full week or target days.
    """
    uid = current_user.get("user_id", "default_user") if current_user else "default_user"
    raw_blocks = [b.model_dump() if hasattr(b, "model_dump") else b.dict() for b in req.blocks]

    target_days = req.days
    updated_table = firestore_service.save_timetable_day(
        user_id=uid,
        day=req.day,
        blocks=raw_blocks,
        apply_to_week=bool(req.apply_to_week),
        target_days=target_days
    )

    return {
        "success": True,
        "user_id": uid,
        "updated_at": updated_table.get("updated_at"),
        "days": updated_table.get("days", {}),
        "saved_day": req.day.lower(),
        "applied_to_week": req.apply_to_week,
        "target_days": target_days
    }


@router.delete("/{day}/{block_id}", response_model=Dict[str, Any])
async def delete_timetable_block(
    day: str,
    block_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Remove a specific time block from a user's weekday schedule.
    """
    uid = current_user.get("user_id", "default_user") if current_user else "default_user"
    deleted = firestore_service.delete_timetable_block(user_id=uid, day=day, block_id=block_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Time block '{block_id}' not found for day '{day}'"
        )

    return {
        "success": True,
        "message": f"Time block '{block_id}' deleted successfully from {day}",
        "day": day.lower(),
        "block_id": block_id
    }
