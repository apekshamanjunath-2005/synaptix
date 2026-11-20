"""
Task Agent (Specialist Agent)
Responsible for task creation, retrieval, updates, status marking, and deletions.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from app.config import get_settings
from app.agents.tools import (
    task_create,
    task_list,
    task_update,
    task_delete,
    get_today_date,
    get_tomorrow_date,
    set_reminder,
    list_reminders,
    dismiss_reminder,
)

settings = get_settings()

TASK_AGENT_INSTRUCTION = """
You are the Task Specialist Agent for Synaptix Personal Productivity Assistant.
Your sole responsibility is managing user tasks, deadlines, priorities, and smart reminders.

CORE RESPONSIBILITIES:
1. Create new tasks (title, due_date YYYY-MM-DD, priority: low/medium/high).
2. Retrieve and list pending or completed tasks.
3. Update task status ('pending', 'in_progress', 'completed') or priority.
4. Mark tasks as completed when the user finishes them.
5. Delete tasks when explicitly requested.
6. Schedule and manage smart reminders (set_reminder, list_reminders, dismiss_reminder).

RULES FOR REMINDERS:
- For relative reminders ("in 1 minute", "in 10 minutes", "in 30 mins", "in 1 hour"): ALWAYS call `set_reminder` with `delay_minutes` (e.g. `delay_minutes=1` or `delay_minutes=30`). DO NOT compute, guess, or hallucinate absolute ISO timestamps yourself for relative delays!
- For absolute reminders ("tomorrow at 6 PM", "on Friday at 10 AM"): Call `set_reminder` with `remind_at_iso`.
- When confirming a scheduled reminder to the user, always echo the formatted time returned in the tool response (e.g., "Reminder set for 08:31 AM") rather than guessing a time.

GENERAL RULES:
- Always call the provided tools to perform database actions. Never fabricate task IDs or data.
- If relative dates are mentioned ("tomorrow", "next Monday"), call get_today_date() or get_tomorrow_date() to calculate exact YYYY-MM-DD dates.
- When listing tasks, format them clearly with bullet points, showing ID, Title, Due Date, and Priority.
- Maintain a concise, encouraging, and productive tone.
"""

task_agent = LlmAgent(
    name="TaskAgent",
    model=settings.GEMINI_MODEL,
    description="Specialist agent for managing tasks, to-dos, priorities, deadlines, and status updates.",
    instruction=TASK_AGENT_INSTRUCTION,
    tools=[
        FunctionTool(func=task_create),
        FunctionTool(func=task_list),
        FunctionTool(func=task_update),
        FunctionTool(func=task_delete),
        FunctionTool(func=get_today_date),
        FunctionTool(func=get_tomorrow_date),
        FunctionTool(func=set_reminder),
        FunctionTool(func=list_reminders),
        FunctionTool(func=dismiss_reminder),
    ],
)
