"""
Agent Tools Definition for Synaptix (Milestone 3)
Provides functional data contracts and tools for all 5 agents.
In-memory repositories allow independent testing right now;
in Milestones 4-6, Firestore, Calendar MCP, and OpenWeatherMap wire in seamlessly.
"""

import json
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger("synaptix.agents.tools")

# ════════════════════════════════════════════════════════════════════════════════
# IN-MEMORY DATA STORES (Seed data for testing & initial operation)
# ════════════════════════════════════════════════════════════════════════════════

TASKS_DB: Dict[str, Dict[str, Any]] = {
    "task-1": {
        "id": "task-1",
        "title": "Complete AI project architecture",
        "due_date": (date.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "priority": "high",
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    "task-2": {
        "id": "task-2",
        "title": "Review Multi-Agent delegation tests",
        "due_date": (date.today() + timedelta(days=2)).strftime("%Y-%m-%d"),
        "priority": "medium",
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
}

NOTES_DB: Dict[str, Dict[str, Any]] = {
    "note-1": {
        "id": "note-1",
        "title": "Synaptix Architecture Decisions",
        "content": "Using Google ADK LlmAgent for modular routing and zero-cost local testing.",
        "tags": ["architecture", "ai"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
}

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


# ════════════════════════════════════════════════════════════════════════════════
# 1. TASK AGENT TOOLS
# ════════════════════════════════════════════════════════════════════════════════

def task_create(
    title: str,
    due_date: Optional[str] = None,
    priority: str = "medium",
    status: str = "pending"
) -> str:
    """
    Create a new task in the task management system.

    Args:
        title: Title or description of the task.
        due_date: Due date formatted as YYYY-MM-DD.
        priority: Priority level ('low', 'medium', 'high'). Default: 'medium'.
        status: Status ('pending', 'in_progress', 'completed'). Default: 'pending'.

    Returns:
        JSON string confirming task creation with assigned ID.
    """
    task_id = f"task-{uuid.uuid4().hex[:6]}"
    task_record = {
        "id": task_id,
        "title": title,
        "due_date": due_date or (date.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "priority": priority.lower(),
        "status": status.lower(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    TASKS_DB[task_id] = task_record
    logger.info("Task created: %s (%s)", title, task_id)
    return json.dumps({"success": True, "action": "created", "task": task_record})


def task_list(status: Optional[str] = None, priority: Optional[str] = None) -> str:
    """
    List all tasks with optional status and priority filters.

    Args:
        status: Optional filter ('pending', 'in_progress', 'completed').
        priority: Optional filter ('low', 'medium', 'high').

    Returns:
        JSON string containing list of matching tasks.
    """
    results = list(TASKS_DB.values())
    if status:
        results = [t for t in results if t["status"] == status.lower()]
    if priority:
        results = [t for t in results if t["priority"] == priority.lower()]

    if not results:
        return json.dumps({"count": 0, "tasks": [], "message": "No tasks found matching criteria."})
    return json.dumps({"count": len(results), "tasks": results})


def task_update(
    task_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[str] = None
) -> str:
    """
    Update an existing task's status, priority, or due date.

    Args:
        task_id: ID of the task to update (e.g. 'task-1').
        status: New status ('pending', 'in_progress', 'completed').
        priority: New priority ('low', 'medium', 'high').
        due_date: New due date YYYY-MM-DD.

    Returns:
        JSON string confirming updated task details.
    """
    task = TASKS_DB.get(task_id)
    if not task:
        # Search by partial ID or title if exact match not found
        for tid, tval in TASKS_DB.items():
            if task_id in tid or task_id.lower() in tval["title"].lower():
                task = tval
                task_id = tid
                break

    if not task:
        return json.dumps({"success": False, "error": f"Task '{task_id}' not found."})

    if status:
        task["status"] = status.lower()
    if priority:
        task["priority"] = priority.lower()
    if due_date:
        task["due_date"] = due_date

    logger.info("Task updated: %s -> status=%s", task_id, task["status"])
    return json.dumps({"success": True, "action": "updated", "task": task})


def task_delete(task_id: str) -> str:
    """
    Delete a task by ID.

    Args:
        task_id: ID of the task to delete.

    Returns:
        JSON string confirming task deletion.
    """
    if task_id in TASKS_DB:
        deleted = TASKS_DB.pop(task_id)
        logger.info("Task deleted: %s", task_id)
        return json.dumps({"success": True, "action": "deleted", "deleted_task": deleted})

    return json.dumps({"success": False, "error": f"Task '{task_id}' not found."})


# ════════════════════════════════════════════════════════════════════════════════
# 2. NOTES AGENT TOOLS
# ════════════════════════════════════════════════════════════════════════════════

def note_save(content: str, title: Optional[str] = None, tags: Optional[str] = None) -> str:
    """
    Save a new personal note or meeting summary.

    Args:
        content: The text content of the note.
        title: Optional title. Defaults to first few words of content.
        tags: Optional comma-separated tags (e.g. 'work, meetings').

    Returns:
        JSON string confirming note was saved.
    """
    note_id = f"note-{uuid.uuid4().hex[:6]}"
    note_title = title or (content[:30] + "..." if len(content) > 30 else content)
    tag_list = [t.strip().lower() for t in tags.split(",")] if tags else []

    note_record = {
        "id": note_id,
        "title": note_title,
        "content": content,
        "tags": tag_list,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    NOTES_DB[note_id] = note_record
    logger.info("Note saved: %s (%s)", note_title, note_id)
    return json.dumps({"success": True, "action": "saved", "note": note_record})


def note_list(limit: int = 10) -> str:
    """
    Retrieve recently saved notes.

    Args:
        limit: Maximum number of notes to return.

    Returns:
        JSON string containing list of notes.
    """
    notes = list(NOTES_DB.values())[:limit]
    return json.dumps({"count": len(notes), "notes": notes})


def note_search(query: str) -> str:
    """
    Search notes by keyword in title, content, or tags.

    Args:
        query: Keyword to search for.

    Returns:
        JSON string containing matching notes.
    """
    q = query.lower()
    matches = [
        n for n in NOTES_DB.values()
        if q in n["title"].lower() or q in n["content"].lower() or any(q in t for t in n["tags"])
    ]
    return json.dumps({"count": len(matches), "query": query, "notes": matches})


def note_delete(note_id: str) -> str:
    """
    Delete a note by ID.

    Args:
        note_id: ID of the note to delete.

    Returns:
        JSON string confirming note deletion.
    """
    if note_id in NOTES_DB:
        deleted = NOTES_DB.pop(note_id)
        return json.dumps({"success": True, "action": "deleted", "note": deleted})
    return json.dumps({"success": False, "error": f"Note '{note_id}' not found."})


# ════════════════════════════════════════════════════════════════════════════════
# 3. CALENDAR AGENT TOOLS (Google Calendar MCP interface)
# ════════════════════════════════════════════════════════════════════════════════

def calendar_create_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: Optional[str] = "",
    location: Optional[str] = ""
) -> str:
    """
    Schedule an event on the user's calendar.

    Args:
        summary: Event title or name.
        start_time: Start datetime in ISO 8601 (YYYY-MM-DDTHH:MM:SS).
        end_time: End datetime in ISO 8601 (YYYY-MM-DDTHH:MM:SS).
        description: Agenda or details.
        location: Meeting link or physical address.

    Returns:
        JSON string confirming event creation.
    """
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
    logger.info("Calendar event scheduled: %s (%s to %s)", summary, start_time, end_time)
    return json.dumps({"success": True, "action": "scheduled", "event": event_record})


def calendar_list_events(date_str: Optional[str] = None) -> str:
    """
    Fetch calendar events for a specific date (defaults to today).

    Args:
        date_str: Target date in YYYY-MM-DD format.

    Returns:
        JSON string with scheduled events.
    """
    target = date_str or date.today().strftime("%Y-%m-%d")
    matches = [e for e in CALENDAR_DB.values() if e["start_time"].startswith(target)]
    return json.dumps({"count": len(matches), "date": target, "events": matches})


def calendar_check_availability(start_time: str, end_time: str) -> str:
    """
    Check if a given timeslot conflicts with existing scheduled events.

    Args:
        start_time: Proposed start time (ISO 8601 string).
        end_time: Proposed end time (ISO 8601 string).

    Returns:
        JSON string with availability boolean and conflicting events list.
    """
    conflicts = []
    for e in CALENDAR_DB.values():
        # Check overlap: (StartA < EndB) and (EndA > StartB)
        if e["start_time"] < end_time and e["end_time"] > start_time:
            conflicts.append(e)

    is_available = len(conflicts) == 0
    return json.dumps({
        "available": is_available,
        "start_time": start_time,
        "end_time": end_time,
        "conflicts": conflicts
    })


# ════════════════════════════════════════════════════════════════════════════════
# 4. SMART DAY PLANNER AGENT TOOLS
# ════════════════════════════════════════════════════════════════════════════════

def get_today_date() -> str:
    """Return today's date formatted as YYYY-MM-DD."""
    return date.today().strftime("%Y-%m-%d")


def get_tomorrow_date() -> str:
    """Return tomorrow's date formatted as YYYY-MM-DD."""
    return (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")


def get_current_weather(city: str = "Bengaluru") -> str:
    """
    Retrieve current weather conditions for city.

    Args:
        city: City name. Default: Bengaluru.

    Returns:
        JSON string with temperature, condition, humidity, and recommendations.
    """
    # Deterministic weather mock for testing / fallback (real API connects in Milestone 6)
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
