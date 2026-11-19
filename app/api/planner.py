"""
Smart Day Planner API Router for Synaptix (Milestone 7 & Firestore Persistence)
Coordinates TaskAgent (Firestore), CalendarAgent (MCP), and Weather Tool
to synthesize conflict-free, prioritized daily timetables.
Persists generated daily plans in Firebase Firestore ('day_plans' collection) scoped by user_id.
"""

import json
from datetime import date, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.tools import (
    task_list,
    calendar_list_events,
    get_current_weather,
    get_today_date,
    get_tomorrow_date,
)
from app.database.firestore import firestore_service
from app.api.auth import get_optional_user
from app.core.context import current_user_id

router = APIRouter(prefix="/api/planner", tags=["Smart Day Planner"])


class PlanRequest(BaseModel):
    target_date: Optional[str] = Field(
        default=None,
        description="Target date in YYYY-MM-DD format (defaults to today)"
    )
    city: Optional[str] = Field(
        default="Bengaluru",
        description="City for weather forecast"
    )


class TimetableBlock(BaseModel):
    time_range: str
    activity_type: str  # 'focus', 'meeting', 'break', 'wrapup'
    title: str
    description: str


class PlanResponse(BaseModel):
    target_date: str
    weather: Dict[str, Any]
    scheduled_events_count: int
    pending_tasks_count: int
    scheduled_events: List[Dict[str, Any]]
    prioritized_tasks: List[Dict[str, Any]]
    timetable: List[TimetableBlock]
    productivity_insights: List[str]
    formatted_markdown: str
    updated_at: Optional[str] = None
    saved: Optional[bool] = True


def synthesize_daily_plan(
    target_date: str,
    city: str = "Bengaluru",
    user_id: Optional[str] = None
) -> PlanResponse:
    """
    Core synthesis engine combining Firestore pending tasks, MCP calendar events,
    and weather metrics into an intelligent timetable.
    Automatically persists the synthesized plan in Firestore ('day_plans' collection).
    """
    effective_uid = user_id or current_user_id.get("default_user")
    current_user_id.set(effective_uid)

    # 1. Fetch domain context
    raw_tasks = json.loads(task_list(status="pending"))
    raw_events = json.loads(calendar_list_events(date_str=target_date))
    weather = json.loads(get_current_weather(city=city))

    pending_tasks = raw_tasks.get("tasks", [])
    events = raw_events.get("events", [])

    # Sort tasks by priority: high -> medium -> low
    priority_weight = {"high": 3, "medium": 2, "low": 1}
    sorted_tasks = sorted(
        pending_tasks,
        key=lambda t: priority_weight.get(t.get("priority", "medium").lower(), 2),
        reverse=True
    )

    # 2. Build Intelligent Timetable (Non-overlapping blocks)
    timetable: List[TimetableBlock] = []

    # Morning Kickoff
    timetable.append(TimetableBlock(
        time_range="08:30 - 09:00",
        activity_type="break",
        title="Morning Prep & Day Review",
        description=f"Review goals. Weather: {weather.get('condition')}, {weather.get('temperature_c')}°C."
    ))

    # Priority Task 1: Morning Deep Focus Block
    if sorted_tasks:
        top_task = sorted_tasks[0]
        timetable.append(TimetableBlock(
            time_range="09:00 - 10:30",
            activity_type="focus",
            title=f"Deep Work: {top_task['title']}",
            description=f"Priority: {top_task['priority'].upper()} | Due: {top_task.get('due_date', 'N/A')}"
        ))
    else:
        timetable.append(TimetableBlock(
            time_range="09:00 - 10:30",
            activity_type="focus",
            title="Deep Focus: Strategic Project Planning",
            description="Uninterrupted focus time on key technical milestones."
        ))

    # Add Calendar Events
    for event in events:
        start_str = event["start_time"][11:16] if len(event["start_time"]) >= 16 else "10:30"
        end_str = event["end_time"][11:16] if len(event["end_time"]) >= 16 else "11:30"
        timetable.append(TimetableBlock(
            time_range=f"{start_str} - {end_str}",
            activity_type="meeting",
            title=f"Meeting: {event['summary']}",
            description=f"Location: {event.get('location') or 'Virtual Meet'}"
        ))

    # Midday Re-alignment & Lunch
    outdoor_note = "Enjoy a 15-min walk outside." if weather.get("suitable_for_outdoor") else "Stay indoors away from rain/heat."
    timetable.append(TimetableBlock(
        time_range="12:30 - 13:30",
        activity_type="break",
        title="Lunch & Mindful Reset",
        description=f"{outdoor_note} Recharge cognitive stamina."
    ))

    # Afternoon Focus: Task 2 or Backlog
    if len(sorted_tasks) > 1:
        second_task = sorted_tasks[1]
        timetable.append(TimetableBlock(
            time_range="13:30 - 15:00",
            activity_type="focus",
            title=f"Afternoon Sprint: {second_task['title']}",
            description=f"Priority: {second_task['priority'].upper()} | Due: {second_task.get('due_date', 'N/A')}"
        ))
    else:
        timetable.append(TimetableBlock(
            time_range="13:30 - 15:00",
            activity_type="focus",
            title="Focus Block: Code Execution & Notes Review",
            description="Execute secondary milestones and document progress."
        ))

    # Late Afternoon Wrap-up & Notes
    timetable.append(TimetableBlock(
        time_range="16:30 - 17:30",
        activity_type="wrapup",
        title="Day Wrap-up & Task Logging",
        description="Mark completed tasks in Firestore, save key insights to NotesAgent."
    ))

    # Sort timetable chronologically
    timetable.sort(key=lambda b: b.time_range[:5])

    # 3. Actionable Insights
    insights = [
        f"🌤️ {weather.get('activity_recommendation', 'Mild weather forecast.')}",
        f"✅ {len(sorted_tasks)} pending task(s) tracked in Firestore. Focus on highest priority first.",
        f"📅 {len(events)} meeting(s) scheduled. Time blocks built around meetings to eliminate conflict."
    ]

    # 4. Synthesized Markdown Output
    task_bullets = "\n".join([f"{i+1}. **[{t['priority'].upper()}]** {t['title']} (Due: {t.get('due_date', 'Today')})" for i, t in enumerate(sorted_tasks[:5])]) or "• No pending tasks! All clear."
    event_bullets = "\n".join([f"• **{e['summary']}** ({e['start_time'][11:16]} - {e['end_time'][11:16]})" for e in events]) or "• No meetings scheduled — complete freedom for deep work."
    timetable_bullets = "\n".join([f"• **{b.time_range}**: [{b.activity_type.upper()}] {b.title}" for b in timetable])

    markdown = f"""```
╔══════════════════════════════════════════════════════╗
║  📅  SYNAPTIX SMART DAY PLAN — {target_date}         ║
╚══════════════════════════════════════════════════════╝
```

🌤️ **WEATHER & OUTDOOR OUTLOOK**
• **{weather.get('condition')}**, {weather.get('temperature_c')}°C (Feels like {weather.get('feels_like_c')}°C, Humidity {weather.get('humidity_pct')}%, Wind {weather.get('wind_kmh')} km/h).
• {weather.get('activity_recommendation')}

📅 **CALENDAR COMMITMENTS**
{event_bullets}

✅ **PRIORITIZED PENDING TASKS**
{task_bullets}

⏱️ **RECOMMENDED HOURLY TIMETABLE**
{timetable_bullets}

💡 **AI PRODUCTIVITY INSIGHTS**
• {insights[0]}
• {insights[1]}
• {insights[2]}
"""

    # 5. Persist into Firestore 'day_plans' collection
    plan_dict = {
        "target_date": target_date,
        "weather": weather,
        "scheduled_events_count": len(events),
        "pending_tasks_count": len(sorted_tasks),
        "scheduled_events": events,
        "prioritized_tasks": sorted_tasks,
        "timetable": [b.dict() if hasattr(b, "dict") else b.model_dump() for b in timetable],
        "productivity_insights": insights,
        "formatted_markdown": markdown,
        "plan": markdown,
    }

    saved_doc = firestore_service.save_day_plan(
        user_id=effective_uid,
        date_str=target_date,
        plan_data=plan_dict
    )

    return PlanResponse(
        target_date=target_date,
        weather=weather,
        scheduled_events_count=len(events),
        pending_tasks_count=len(sorted_tasks),
        scheduled_events=events,
        prioritized_tasks=sorted_tasks,
        timetable=timetable,
        productivity_insights=insights,
        formatted_markdown=markdown,
        updated_at=saved_doc.get("updated_at"),
        saved=True,
    )


@router.post("/generate", response_model=PlanResponse, status_code=status.HTTP_200_OK)
async def generate_day_plan(
    req: Optional[PlanRequest] = None,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Generate an optimized daily schedule synthesizing Firestore tasks, MCP calendar, and weather.
    Automatically saves the result in Firestore 'day_plans' scoped to current user.
    """
    target_date = (req.target_date if req and req.target_date else None) or get_today_date()
    city = (req.city if req and req.city else None) or "Bengaluru"
    uid = current_user.get("user_id", "default_user") if current_user else "default_user"
    return synthesize_daily_plan(target_date=target_date, city=city, user_id=uid)


@router.get("/today")
async def get_today_plan(current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    """
    Retrieve today's saved plan from Firestore without burning Gemini API calls.
    """
    uid = current_user.get("user_id", "default_user") if current_user else "default_user"
    today_str = get_today_date()
    plan = firestore_service.get_day_plan(user_id=uid, date_str=today_str)
    if plan:
        return {"success": True, "saved": True, "target_date": today_str, "plan": plan}
    return {"success": False, "saved": False, "target_date": today_str, "message": "No saved plan found for today"}


@router.get("")
@router.get("/")
async def get_saved_plan(
    date: Optional[str] = Query(default=None, description="Date in YYYY-MM-DD format"),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Retrieve a saved plan from Firestore for a specific date (defaults to today).
    """
    uid = current_user.get("user_id", "default_user") if current_user else "default_user"
    target_date = date or get_today_date()
    plan = firestore_service.get_day_plan(user_id=uid, date_str=target_date)
    if plan:
        return {"success": True, "saved": True, "target_date": target_date, "plan": plan}
    return {"success": False, "saved": False, "target_date": target_date, "message": f"No saved plan found for {target_date}"}


@router.get("/history")
async def get_plan_history(
    limit: int = Query(default=7, ge=1, le=30),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Retrieve user's recent saved plans from Firestore.
    """
    uid = current_user.get("user_id", "default_user") if current_user else "default_user"
    plans = firestore_service.list_day_plans(user_id=uid, limit=limit)
    return {"success": True, "count": len(plans), "plans": plans}
