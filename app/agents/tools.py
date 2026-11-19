"""
Agent Tools Definition for Synaptix (Milestone 4 — Firestore Connected)
Connects TaskAgent and NotesAgent directly to Firebase Firestore.
"""

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from app.database.firestore import firestore_service

logger = logging.getLogger("synaptix.agents.tools")


# ════════════════════════════════════════════════════════════════════════════════
# 1. TASK AGENT TOOLS (Backed by Firestore 'tasks' collection)
# ════════════════════════════════════════════════════════════════════════════════

def task_create(
    title: str,
    due_date: Optional[str] = None,
    priority: str = "medium",
    status: str = "pending"
) -> str:
    """
    Create a new task in Firestore.

    Args:
        title: Title or description of the task.
        due_date: Due date formatted as YYYY-MM-DD.
        priority: Priority level ('low', 'medium', 'high'). Default: 'medium'.
        status: Status ('pending', 'in_progress', 'completed'). Default: 'pending'.

    Returns:
        JSON string confirming task creation with assigned ID.
    """
    try:
        task_data = firestore_service.add_task(
            title=title,
            due_date=due_date,
            priority=priority,
            status=status
        )
        return json.dumps({"success": True, "action": "created", "task": task_data})
    except Exception as e:
        logger.error("Error creating task: %s", e)
        return json.dumps({"success": False, "error": str(e)})


def task_list(status: Optional[str] = None, priority: Optional[str] = None) -> str:
    """
    List tasks from Firestore with optional status and priority filters.

    Args:
        status: Optional filter ('pending', 'in_progress', 'completed').
        priority: Optional filter ('low', 'medium', 'high').

    Returns:
        JSON string containing list of matching tasks.
    """
    try:
        tasks = firestore_service.get_tasks(status=status, priority=priority)
        return json.dumps({"count": len(tasks), "tasks": tasks})
    except Exception as e:
        logger.error("Error listing tasks: %s", e)
        return json.dumps({"count": 0, "tasks": [], "error": str(e)})


def task_update(
    task_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[str] = None
) -> str:
    """
    Update an existing task in Firestore.

    Args:
        task_id: ID of the task to update (e.g. 'task-1').
        status: New status ('pending', 'in_progress', 'completed').
        priority: New priority ('low', 'medium', 'high').
        due_date: New due date YYYY-MM-DD.

    Returns:
        JSON string confirming updated task details.
    """
    try:
        updates = {}
        if status:
            updates["status"] = status
        if priority:
            updates["priority"] = priority
        if due_date:
            updates["due_date"] = due_date

        updated_task = firestore_service.update_task(task_id, updates)
        if not updated_task:
            return json.dumps({"success": False, "error": f"Task '{task_id}' not found."})

        return json.dumps({"success": True, "action": "updated", "task": updated_task})
    except Exception as e:
        logger.error("Error updating task: %s", e)
        return json.dumps({"success": False, "error": str(e)})


def task_delete(task_id: str) -> str:
    """
    Delete a task document from Firestore.

    Args:
        task_id: ID of the task to delete.

    Returns:
        JSON string confirming task deletion.
    """
    try:
        success = firestore_service.delete_task(task_id)
        return json.dumps({"success": success, "task_id": task_id})
    except Exception as e:
        logger.error("Error deleting task: %s", e)
        return json.dumps({"success": False, "error": str(e)})


# ════════════════════════════════════════════════════════════════════════════════
# 2. NOTES AGENT TOOLS (Backed by Firestore 'notes' collection)
# ════════════════════════════════════════════════════════════════════════════════

def note_save(content: str, title: Optional[str] = None, tags: Optional[str] = None) -> str:
    """
    Save a new note document in Firestore.

    Args:
        content: The text content of the note.
        title: Optional title. Defaults to first few words of content.
        tags: Optional comma-separated tags (e.g. 'work, meeting').

    Returns:
        JSON string confirming note was saved.
    """
    try:
        tag_list = [t.strip().lower() for t in tags.split(",")] if tags else []
        note_data = firestore_service.add_note(content=content, title=title, tags=tag_list)
        return json.dumps({"success": True, "action": "saved", "note": note_data})
    except Exception as e:
        logger.error("Error saving note: %s", e)
        return json.dumps({"success": False, "error": str(e)})


def note_list(limit: int = 10) -> str:
    """
    Retrieve recently saved notes from Firestore.

    Args:
        limit: Maximum number of notes to return.

    Returns:
        JSON string containing list of notes.
    """
    try:
        notes = firestore_service.get_notes(limit=limit)
        return json.dumps({"count": len(notes), "notes": notes})
    except Exception as e:
        logger.error("Error listing notes: %s", e)
        return json.dumps({"count": 0, "notes": [], "error": str(e)})


def note_search(query: str) -> str:
    """
    Search notes in Firestore by keyword in title, content, or tags.

    Args:
        query: Keyword to search for.

    Returns:
        JSON string containing matching notes.
    """
    try:
        matches = firestore_service.search_notes(query)
        return json.dumps({"count": len(matches), "query": query, "notes": matches})
    except Exception as e:
        logger.error("Error searching notes: %s", e)
        return json.dumps({"count": 0, "notes": [], "error": str(e)})


def note_delete(note_id: str) -> str:
    """
    Delete a note document from Firestore.

    Args:
        note_id: ID of the note to delete.

    Returns:
        JSON string confirming note deletion.
    """
    try:
        success = firestore_service.delete_note(note_id)
        return json.dumps({"success": success, "note_id": note_id})
    except Exception as e:
        logger.error("Error deleting note: %s", e)
        return json.dumps({"success": False, "error": str(e)})


# ════════════════════════════════════════════════════════════════════════════════
# 3. CALENDAR AGENT TOOLS (Connected to Calendar MCP Provider)
# ════════════════════════════════════════════════════════════════════════════════

from app.tools.calendar_mcp import calendar_mcp


def calendar_create_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: Optional[str] = "",
    location: Optional[str] = ""
) -> str:
    """
    Schedule an event on the user's calendar via Calendar MCP.

    Args:
        summary: Event title or name.
        start_time: Start datetime in ISO 8601 (YYYY-MM-DDTHH:MM:SS).
        end_time: End datetime in ISO 8601 (YYYY-MM-DDTHH:MM:SS).
        description: Agenda or details.
        location: Meeting link or physical address.

    Returns:
        JSON string confirming event creation.
    """
    try:
        event_record = calendar_mcp.create_event(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            description=description or "",
            location=location or ""
        )
        return json.dumps({"success": True, "action": "scheduled", "event": event_record})
    except Exception as e:
        logger.error("Error creating calendar event via MCP: %s", e)
        return json.dumps({"success": False, "error": str(e)})


def calendar_list_events(date_str: Optional[str] = None) -> str:
    """
    Fetch calendar events for a specific date via Calendar MCP.

    Args:
        date_str: Target date in YYYY-MM-DD format (defaults to today).

    Returns:
        JSON string with scheduled events.
    """
    try:
        events = calendar_mcp.list_events(date_str=date_str)
        return json.dumps({"count": len(events), "date": date_str or date.today().strftime("%Y-%m-%d"), "events": events})
    except Exception as e:
        logger.error("Error listing calendar events via MCP: %s", e)
        return json.dumps({"count": 0, "events": [], "error": str(e)})


def calendar_check_availability(start_time: str, end_time: str) -> str:
    """
    Check if a proposed timeslot has meeting conflicts via Calendar MCP.

    Args:
        start_time: Proposed start time (ISO 8601 string).
        end_time: Proposed end time (ISO 8601 string).

    Returns:
        JSON string with availability boolean and conflicting events list.
    """
    try:
        result = calendar_mcp.check_availability(start_time=start_time, end_time=end_time)
        return json.dumps(result)
    except Exception as e:
        logger.error("Error checking availability via MCP: %s", e)
        return json.dumps({"available": False, "error": str(e)})


def calendar_update_event(
    event_id: str,
    summary: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None
) -> str:
    """
    Update an existing calendar event via Calendar MCP.

    Args:
        event_id: ID or summary of event to update.
        summary: New event title.
        start_time: New start time.
        end_time: New end time.
        description: New description.
        location: New location.

    Returns:
        JSON string confirming update.
    """
    try:
        updated = calendar_mcp.update_event(
            event_id=event_id,
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location
        )
        if not updated:
            return json.dumps({"success": False, "error": f"Event '{event_id}' not found."})
        return json.dumps({"success": True, "action": "updated", "event": updated})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def calendar_delete_event(event_id: str) -> str:
    """
    Delete a calendar event via Calendar MCP.

    Args:
        event_id: ID or summary of the event to delete.

    Returns:
        JSON string confirming deletion.
    """
    try:
        success = calendar_mcp.delete_event(event_id)
        return json.dumps({"success": success, "event_id": event_id})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ════════════════════════════════════════════════════════════════════════════════
# 4. SMART DAY PLANNER AGENT TOOLS (Connected to Weather Tool & Dates)
# ════════════════════════════════════════════════════════════════════════════════

from app.tools.weather_tool import weather_tool


def get_today_date() -> str:
    """
    Get today's date formatted as YYYY-MM-DD.

    Returns:
        Date string (YYYY-MM-DD).
    """
    return date.today().strftime("%Y-%m-%d")


def get_tomorrow_date() -> str:
    """
    Get tomorrow's date formatted as YYYY-MM-DD.

    Returns:
        Date string (YYYY-MM-DD).
    """
    return (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")


def get_current_weather(city: str = "Bengaluru") -> str:
    """
    Retrieve live weather conditions, temperature, and outdoor activity recommendations.
    Uses OpenWeatherMap API when configured, or reliable zero-cost fallback.

    Args:
        city: City name to look up weather for (default is Bengaluru).

    Returns:
        JSON string containing condition, temperature_c, feels_like_c, humidity_pct,
        wind_kmh, suitable_for_outdoor (bool), and activity_recommendation.
    """
    try:
        weather_info = weather_tool.get_weather_sync(city=city)
        return json.dumps(weather_info)
    except Exception as e:
        logger.error("Error retrieving weather for %s: %s", city, e)
        return json.dumps({
            "city": city,
            "condition": "Clear",
            "temperature_c": 24.0,
            "suitable_for_outdoor": True,
            "activity_recommendation": "Weather data currently unavailable; assuming mild conditions.",
            "error": str(e)
        })

