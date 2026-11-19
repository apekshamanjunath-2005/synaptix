"""
Calendar API Router (Milestone 5 — Calendar MCP Integration)
REST endpoints exposing Calendar MCP tools for events and conflict detection.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.tools.calendar_mcp import calendar_mcp

router = APIRouter(prefix="/api/calendar", tags=["Calendar MCP Management"])


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
    max_results: int = Query(default=15, ge=1, le=50)
):
    """Retrieve scheduled calendar events via Calendar MCP."""
    events = calendar_mcp.list_events(date_str=date, max_results=max_results)
    return {"count": len(events), "date": date, "events": events}


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
