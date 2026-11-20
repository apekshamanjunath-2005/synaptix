"""
Agent Tools Definition for Synaptix (Milestone 4 — Firestore Connected)
Connects TaskAgent and NotesAgent directly to Firebase Firestore.
"""

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Union

from app.database.firestore import firestore_service
from app.tools.gmail_service import gmail_service
from app.agents.context import current_user_id, current_user_name, current_user_timezone

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
        uid = current_user_id.get("default_user")
        task_data = firestore_service.add_task(
            title=title,
            due_date=due_date,
            priority=priority,
            status=status,
            user_id=uid
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
        uid = current_user_id.get("default_user")
        tasks = firestore_service.get_tasks(status=status, priority=priority, user_id=uid)
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
        uid = current_user_id.get("default_user")
        note_data = firestore_service.add_note(content=content, title=title, tags=tag_list, user_id=uid)
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
        uid = current_user_id.get("default_user")
        notes = firestore_service.get_notes(limit=limit, user_id=uid)
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
        uid = current_user_id.get("default_user")
        matches = firestore_service.search_notes(query, user_id=uid)
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
    location: Optional[str] = "",
    reminder_minutes: int = 15
) -> str:
    """
    Schedule an event on the user's calendar via Calendar MCP with default popup reminder.

    Args:
        summary: Event title or name.
        start_time: Start datetime in ISO 8601 (YYYY-MM-DDTHH:MM:SS).
        end_time: End datetime in ISO 8601 (YYYY-MM-DDTHH:MM:SS).
        description: Agenda or details.
        location: Meeting link or physical address.
        reminder_minutes: Minutes before the event to trigger popup reminder (default: 15).

    Returns:
        JSON string confirming event creation.
    """
    try:
        event_record = calendar_mcp.create_event(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            description=description or "",
            location=location or "",
            reminder_minutes=reminder_minutes
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


# ════════════════════════════════════════════════════════════════════════════════
# 5. GMAIL AGENT TOOLS (Human-in-the-Loop Email Drafting & Dispatch)
# ════════════════════════════════════════════════════════════════════════════════

def email_draft_create(to: str, subject: str, body: str) -> str:
    """
    Create an email draft with recipient, subject, and body.
    Does NOT send the email. Always call this tool first and present the complete
    draft preview (To, Subject, Body, Draft ID) to the user for explicit confirmation
    before dispatching.

    Args:
        to: Email address or recipient name.
        subject: Subject line of the email.
        body: Complete, well-structured email body text.

    Returns:
        JSON string confirming draft creation with draft_id and status='draft'.
    """
    try:
        uid = current_user_id.get("default_user")
        draft = gmail_service.create_email_draft(to=to, subject=subject, body=body, user_id=uid)
        return json.dumps({"success": True, "action": "draft_created", "draft": draft})
    except Exception as exc:
        logger.error("Error creating email draft: %s", exc)
        return json.dumps({"success": False, "error": str(exc)})


def email_draft_send(draft_id: str) -> str:
    """
    Send an existing email draft after receiving explicit user confirmation.
    CRITICAL: NEVER call this tool without explicit user approval ('send it',
    'approve draft', etc.).

    Args:
        draft_id: Unique identifier of the draft to send (e.g. 'draft-abc123' or Gmail draft ID).

    Returns:
        JSON string confirming dispatch status.
    """
    try:
        uid = current_user_id.get("default_user")
        result = gmail_service.send_email_draft(draft_id=draft_id, user_id=uid)
        return json.dumps({"success": result.get("sent", False), "action": "draft_sent", "result": result})
    except Exception as exc:
        logger.error("Error sending email draft %s: %s", draft_id, exc)
        return json.dumps({"success": False, "error": str(exc)})


def email_draft_list() -> str:
    """
    List existing email drafts and their statuses ('draft', 'sent').

    Returns:
        JSON string containing the list of drafts.
    """
    try:
        uid = current_user_id.get("default_user")
        drafts = gmail_service.list_drafts(user_id=uid)
        return json.dumps({"success": True, "count": len(drafts), "drafts": drafts})
    except Exception as exc:
        logger.error("Error listing email drafts: %s", exc)
        return json.dumps({"success": False, "error": str(exc)})


# ════════════════════════════════════════════════════════════════════════════════
# 6. REMINDER TOOLS (User-scoped Notifications & Timely Alerts)
# ════════════════════════════════════════════════════════════════════════════════

def set_reminder(
    title: str,
    remind_at_iso: Optional[str] = None,
    delay_minutes: Optional[Union[int, float]] = None,
    source_type: str = "custom",
    source_id: Optional[str] = None,
    remind_at: Optional[str] = None
) -> str:
    """
    Schedule a smart reminder for the user.

    Args:
        title: What the reminder is about (e.g. "Review DBMS notes", "Call Disha", "Test notifications").
        remind_at_iso: Absolute target date/time to trigger reminder (ISO 8601 string, e.g. '2026-11-20T18:00:00+00:00').
        delay_minutes: Relative delay in minutes from right now (e.g. 1 for 'in 1 minute', 30 for 'in 30 mins'). Strongly preferred for relative requests.
        source_type: Type of source item ('note', 'task', 'event', 'custom'). Default is 'custom'.
        source_id: Optional ID of the linked note, task, or event.
        remind_at: Backwards-compatible alias for remind_at_iso.

    Returns:
        JSON string confirming reminder creation with ID, exact trigger time, and formatted local time message.
    """
    try:
        uid = current_user_id.get("default_user")

        target_iso: str = ""
        target_dt: Optional[datetime] = None

        if delay_minutes is not None:
            now_utc = datetime.now(timezone.utc)
            target_dt = now_utc + timedelta(minutes=float(delay_minutes))
            target_iso = target_dt.replace(microsecond=0).isoformat()
        else:
            raw_target = remind_at_iso or remind_at
            if raw_target:
                target_iso = raw_target
                try:
                    clean = raw_target.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(clean)
                    if dt.tzinfo is None:
                        dt = dt.astimezone()
                    target_dt = dt
                except Exception:
                    target_dt = datetime.now().astimezone()
            else:
                now_utc = datetime.now(timezone.utc)
                target_dt = now_utc + timedelta(minutes=10)
                target_iso = target_dt.replace(microsecond=0).isoformat()

        # Format local time for user-facing echo
        try:
            if target_dt is not None:
                user_tz = current_user_timezone.get(None)
                if user_tz:
                    try:
                        import zoneinfo
                        local_dt = target_dt.astimezone(zoneinfo.ZoneInfo(user_tz))
                    except Exception:
                        local_dt = target_dt.astimezone()
                else:
                    local_dt = target_dt.astimezone()
                local_time_str = local_dt.strftime("%I:%M %p")
            else:
                local_time_str = target_iso
        except Exception:
            local_time_str = target_iso

        reminder = firestore_service.create_reminder(
            user_id=uid,
            title=title,
            remind_at_iso=target_iso,
            source_type=source_type,
            source_id=source_id,
        )

        display_msg = f"Reminder set for {local_time_str}"
        return json.dumps({
            "success": True,
            "action": "reminder_created",
            "reminder": reminder,
            "formatted_time": local_time_str,
            "message": display_msg,
            "display": f"⏰ {display_msg}: '{title}'"
        })
    except Exception as exc:
        logger.error("Error creating reminder: %s", exc)
        return json.dumps({"success": False, "error": str(exc)})


def list_reminders(status: Optional[str] = None) -> str:
    """
    List user reminders, optionally filtering by status ('pending', 'snoozed', 'dismissed', 'triggered').

    Args:
        status: Optional status filter.

    Returns:
        JSON string with list of user reminders ordered by time.
    """
    try:
        uid = current_user_id.get("default_user")
        reminders = firestore_service.list_reminders(user_id=uid, status=status)
        return json.dumps({"success": True, "count": len(reminders), "reminders": reminders})
    except Exception as exc:
        logger.error("Error listing reminders: %s", exc)
        return json.dumps({"success": False, "error": str(exc)})


def dismiss_reminder(reminder_id: str) -> str:
    """
    Dismiss a reminder so it no longer triggers.

    Args:
        reminder_id: The ID of the reminder to dismiss (e.g. 'reminder-123abc').

    Returns:
        JSON string confirming reminder status update.
    """
    try:
        uid = current_user_id.get("default_user")
        res = firestore_service.update_reminder_status(user_id=uid, reminder_id=reminder_id, status="dismissed")
        if res:
            return json.dumps({"success": True, "action": "dismissed", "reminder": res})
        return json.dumps({"success": False, "error": f"Reminder '{reminder_id}' not found."})
    except Exception as exc:
        logger.error("Error dismissing reminder: %s", exc)
        return json.dumps({"success": False, "error": str(exc)})


def snooze_reminder(reminder_id: str, minutes: int = 10) -> str:
    """
    Snooze a reminder by the specified number of minutes (defaults to 10 minutes).

    Args:
        reminder_id: The ID of the reminder to snooze.
        minutes: Number of minutes to snooze for (default: 10).

    Returns:
        JSON string confirming updated snooze trigger time.
    """
    try:
        uid = current_user_id.get("default_user")
        res = firestore_service.update_reminder_status(user_id=uid, reminder_id=reminder_id, status="snoozed", snooze_minutes=minutes)
        if res:
            return json.dumps({"success": True, "action": "snoozed", "reminder": res})
        return json.dumps({"success": False, "error": f"Reminder '{reminder_id}' not found."})
    except Exception as exc:
        logger.error("Error snoozing reminder: %s", exc)
        return json.dumps({"success": False, "error": str(exc)})


# Aliases
reminder_create = set_reminder
reminder_list = list_reminders
reminder_dismiss = dismiss_reminder
reminder_snooze = snooze_reminder


