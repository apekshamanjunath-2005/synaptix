"""
Calendar API Router (Milestone 5 — Calendar MCP Integration)
REST endpoints exposing Calendar MCP tools for events and conflict detection.
"""

from datetime import datetime, date, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.tools.calendar_mcp import calendar_mcp

router = APIRouter(prefix="/api/calendar", tags=["Calendar MCP Management"])


def _is_event_upcoming(event: Dict[str, Any], now_dt: datetime) -> bool:
    """Determine whether an event is upcoming based on its end_time (or start_time)."""
    time_str = event.get("end_time") or event.get("start_time") or ""
    if not time_str:
        return True
    try:
        clean = time_str.replace("Z", "+00:00")
        ev_dt = datetime.fromisoformat(clean)
        if ev_dt.tzinfo is None:
            ev_dt = ev_dt.replace(tzinfo=now_dt.tzinfo)
        return ev_dt >= now_dt
    except Exception:
        local_iso = now_dt.strftime("%Y-%m-%dT%H:%M:%S")
        return time_str[:19] >= local_iso


class EventCreateRequest(BaseModel):
    summary: str = Field(..., min_length=1, max_length=200, description="Meeting title")
    start_time: str = Field(..., description="ISO 8601 start timestamp (e.g. YYYY-MM-DDTHH:MM:SS)")
    end_time: str = Field(..., description="ISO 8601 end timestamp (e.g. YYYY-MM-DDTHH:MM:SS)")
    description: Optional[str] = Field(default="", description="Agenda or meeting description")
    location: Optional[str] = Field(default="", description="Location or video call link")


class EventUpdateRequest(BaseModel):
    summary: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None


class AvailabilityCheckRequest(BaseModel):
    start_time: str = Field(..., description="Proposed start timestamp")
    end_time: str = Field(..., description="Proposed end timestamp")


@router.get("/events")
async def list_calendar_events(
    date: Optional[str] = Query(default=None, description="Target date in YYYY-MM-DD format"),
    month: Optional[str] = Query(default=None, description="Target month in YYYY-MM format"),
    days_past: Optional[int] = Query(default=None, description="Past window in days (defaults to 30)"),
    days_future: Optional[int] = Query(default=None, description="Future window in days (defaults to 60)"),
    all_events: Optional[bool] = Query(default=False, description="Return all upcoming and past events"),
    max_results: int = Query(default=150, ge=1, le=250)
):
    """
    Retrieve scheduled calendar events via Calendar MCP.
    Classifies events into 'upcoming' (soonest-first) and 'past' (most-recent-first).
    """
    events = calendar_mcp.list_events(
        date_str=date,
        month_str=month,
        days_past=days_past,
        days_future=days_future,
        all_events=bool(all_events),
        max_results=max_results
    )

    now_dt = datetime.now().astimezone()
    upcoming = []
    past = []

    for ev in events:
        if _is_event_upcoming(ev, now_dt):
            upcoming.append(ev)
        else:
            past.append(ev)

    # Upcoming sorted soonest first
    upcoming.sort(key=lambda x: x.get("start_time", ""))
    # Past sorted most recent first
    past.sort(key=lambda x: x.get("start_time", ""), reverse=True)

    return {
        "count": len(events),
        "date": date,
        "month": month,
        "events": events,
        "upcoming_count": len(upcoming),
        "past_count": len(past),
        "upcoming": upcoming,
        "past": past,
    }


@router.post("/events", status_code=status.HTTP_201_CREATED)
async def create_calendar_event(req: EventCreateRequest):
    """Schedule a calendar event via Calendar MCP."""
    event = calendar_mcp.create_event(
        summary=req.summary,
        start_time=req.start_time,
        end_time=req.end_time,
        description=req.description or "",
        location=req.location or ""
    )
    return {"success": True, "event": event}


@router.post("/check-availability")
async def check_availability(req: AvailabilityCheckRequest):
    """Check timeslot availability and detect schedule conflicts."""
    result = calendar_mcp.check_availability(
        start_time=req.start_time,
        end_time=req.end_time
    )
    return result


@router.patch("/events/{event_id}")
async def update_calendar_event(event_id: str, req: EventUpdateRequest):
    """Update event details via Calendar MCP."""
    updated = calendar_mcp.update_event(
        event_id=event_id,
        summary=req.summary,
        start_time=req.start_time,
        end_time=req.end_time,
        description=req.description,
        location=req.location
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Calendar event '{event_id}' not found.")
    return {"success": True, "event": updated}


@router.delete("/events/{event_id}")
async def delete_calendar_event(event_id: str):
    """Delete event via Calendar MCP."""
    deleted = calendar_mcp.delete_event(event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Calendar event '{event_id}' not found.")
    return {"success": True, "event_id": event_id}
