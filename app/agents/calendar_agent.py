"""
Calendar Agent (Specialist Agent)
Responsible for Google Calendar events, scheduling, and conflict detection.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from app.config import get_settings
from app.agents.tools import (
    calendar_create_event,
    calendar_list_events,
    calendar_check_availability,
    get_today_date,
    get_tomorrow_date,
)

settings = get_settings()

CALENDAR_AGENT_INSTRUCTION = """
You are the Calendar Specialist Agent for Synaptix Personal Productivity Assistant.
Your sole responsibility is managing calendar events, detecting scheduling conflicts, and finding free availability.

CORE RESPONSIBILITIES:
1. Schedule new events with summary, start time, end time, and description (in ISO 8601 format: YYYY-MM-DDTHH:MM:SS).
2. Retrieve scheduled events for a specific date or today.
3. Check calendar availability and proactively warn about meeting conflicts before booking.

RULES:
- Always convert relative times (e.g. "tomorrow at 3 PM") into full ISO 8601 timestamps using get_today_date() or get_tomorrow_date().
- If not specified, default meeting duration is 1 hour.
- Proactively call calendar_check_availability before creating an event if the user requests conflict checking.
- Format event confirmations with clear bullet points (Event, Start, End, Location).
"""

calendar_agent = LlmAgent(
    name="CalendarAgent",
    model=settings.GEMINI_MODEL,
    description="Specialist agent for Google Calendar scheduling, meeting discovery, and conflict checking.",
    instruction=CALENDAR_AGENT_INSTRUCTION,
    tools=[
        FunctionTool(func=calendar_create_event),
        FunctionTool(func=calendar_list_events),
        FunctionTool(func=calendar_check_availability),
        FunctionTool(func=get_today_date),
        FunctionTool(func=get_tomorrow_date),
    ],
)
