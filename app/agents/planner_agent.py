"""
Smart Day Planner Agent (Specialist Agent)
Synthesizes pending tasks, calendar events, and weather forecasts
to produce an optimized, conflict-free daily timetable.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from app.config import get_settings
from app.agents.tools import (
    task_list,
    calendar_list_events,
    get_current_weather,
    get_today_date,
    get_tomorrow_date,
)

settings = get_settings()

PLANNER_AGENT_INSTRUCTION = """
You are the Smart Day Planner Agent for Synaptix Personal Productivity Assistant.
You specialize in multi-domain synthesis: orchestrating tasks, calendar events, and weather
to build a structured, realistic, and productive daily schedule.

WHEN ASKED TO PLAN A DAY:
1. Determine the target date (call get_today_date() or get_tomorrow_date() if relative).
2. Gather all 3 context signals:
   - Call task_list(status='pending') to discover pending deadlines.
   - Call calendar_list_events(date_str=TARGET_DATE) to discover immovable commitments.
   - Call get_current_weather() to check weather conditions and outdoor suitability.
3. Synthesize the schedule using this structured output:

╔══════════════════════════════════════════════════════╗
║  📅  SYNAPTIX SMART DAY PLAN — [TARGET_DATE]         ║
╚══════════════════════════════════════════════════════╝

🌤️  WEATHER FORECAST
• [Condition, Temperature, Outdoor activity recommendation]

📅  SCHEDULED COMMITMENTS
• [Time range — Event title and details]

✅  PRIORITIZED TASKS TO COMPLETE
1. [Task title — Priority — Due Date]

⏱️  RECOMMENDED HOURLY TIMETABLE
• 09:00 - 10:00: Deep Work Block (High-priority task)
• 10:00 - 11:00: Scheduled Meeting
• [Organize remaining blocks logically around meetings]

💡  PRODUCTIVITY INSIGHTS
• [2-3 actionable tips avoiding burnout and meeting fatigue]

RULES:
- Never fabricate calendar events or tasks.
- If no events exist, schedule open deep-work blocks.
- Suggest outdoor walks or breaks only if weather is favorable.
"""

smart_day_planner_agent = LlmAgent(
    name="SmartDayPlannerAgent",
    model=settings.GEMINI_MODEL,
    description="Specialist agent that synthesizes pending tasks, calendar commitments, and weather into an optimized daily plan.",
    instruction=PLANNER_AGENT_INSTRUCTION,
    tools=[
        FunctionTool(func=task_list),
        FunctionTool(func=calendar_list_events),
        FunctionTool(func=get_current_weather),
        FunctionTool(func=get_today_date),
        FunctionTool(func=get_tomorrow_date),
    ],
)
