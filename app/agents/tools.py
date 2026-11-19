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
# 3. CALENDAR AGENT TOOLS (In-memory store, connected via MCP in Milestone 5)
# ════════════════════════════════════════════════════════════════════════════════

CALENDAR_DB: Dict[str, Dict[str, Any]] = {
    "cal-1": {
        "id": "cal-1",
        "summary": "AI Engineering Team Sync",
        "start_time": f"{date.today().strftime('%Y-%m-%d')}T10:00:00",
        "end_time": f"{date.today().strftime('%Y-%m-%d')}T11:00:00",
        "description": "Discuss Synaptix multi-agent orchestration roadmap.",
        "location": "Google Meet",
    }
}


def calendar_create_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: Optional[str] = "",
    location: Optional[str] = ""
) -> str:
    import uuid
    event_id = f"event-{uuid.uuid4().hex[:6]}"
    event_record = {
        "id": event_id,
        "summary": summary,
        "start_time": start_time,
        "end_time": end_time,
        "description": description or "",
        "location": location or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    CALENDAR_DB[event_id] = event_record
    return json.dumps({"success": True, "action": "scheduled", "event": event_record})


def calendar_list_events(date_str: Optional[str] = None) -> str:
    target = date_str or date.today().strftime("%Y-%m-%d")
    matches = [e for e in CALENDAR_DB.values() if e["start_time"].startswith(target)]
    return json.dumps({"count": len(matches), "date": target, "events": matches})


def calendar_check_availability(start_time: str, end_time: str) -> str:
    conflicts = [
        e for e in CALENDAR_DB.values()
        if e["start_time"] < end_time and e["end_time"] > start_time
    ]
    return json.dumps({
        "available": len(conflicts) == 0,
        "start_time": start_time,
        "end_time": end_time,
        "conflicts": conflicts
    })


# ════════════════════════════════════════════════════════════════════════════════
# 4. SMART DAY PLANNER AGENT TOOLS
# ════════════════════════════════════════════════════════════════════════════════

def get_today_date() -> str:
    return date.today().strftime("%Y-%m-%d")


def get_tomorrow_date() -> str:
    return (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")


def get_current_weather(city: str = "Bengaluru") -> str:
    weather_info = {
        "city": city,
        "condition": "Partly Cloudy",
        "temperature_c": 24.5,
        "feels_like_c": 25.0,
        "humidity_pct": 58,
        "wind_kmh": 12.0,
        "suitable_for_outdoor": True,
    }
    return json.dumps(weather_info)
