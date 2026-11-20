"""
Synaptix Multi-Agent Orchestration Service (Milestone 3)
Runs Google ADK multi-agent workflows using InMemoryRunner.
Tracks agent transfers, tool calls, and strictly enforces ₹0 budget safeguards.
"""

import json
import logging
import uuid
from datetime import datetime, date, timedelta, timezone
import zoneinfo
from typing import Optional, List, Dict, Any

from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

from app.config import get_settings
from app.core.usage_tracker import usage_tracker
from app.agents.coordinator import coordinator_agent
from app.agents.context import set_user_context, get_user_context
from app.agents.tools import (
    task_create,
    task_list,
    task_update,
    note_save,
    note_list,
    note_search,
    calendar_create_event,
    calendar_list_events,
    get_current_weather,
    get_today_date,
    get_tomorrow_date,
    email_draft_create,
    email_draft_send,
    email_draft_list,
    set_reminder,
    list_reminders,
    dismiss_reminder,
    snooze_reminder,
)

logger = logging.getLogger("synaptix.agents.orchestrator")

APP_NAME = "synaptix"
USER_ID = "default_user"


class MultiAgentOrchestrator:
    def __init__(self):
        self.settings = get_settings()
        self.runner = InMemoryRunner(agent=coordinator_agent, app_name=APP_NAME)
        self.active_sessions: set = set()

    async def _ensure_session(self, session_id: str, user_id: str = "default_user") -> None:
        """Create or verify ADK session existence."""
        session_key = f"{user_id}:{session_id}"
        if session_key not in self.active_sessions:
            try:
                await self.runner.session_service.create_session(
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=session_id
                )
                self.active_sessions.add(session_key)
            except Exception as e:
                # Session may already exist
                logger.debug("Session check: %s", e)
                self.active_sessions.add(session_key)

    async def run_workflow(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        user_tz: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Execute multi-agent workflow for user query.
        Delegates from Coordinator to Task, Notes, Calendar, Gmail, or Planner agents.
        Supports multi-user execution context with live local time injection.
        """
        uid = user_id or "default_user"
        set_user_context(user_id=uid, name=user_name, email=user_email, timezone=user_tz)

        # 1. Enforce ₹0 budget limit
        usage_tracker.enforce_quota_or_raise()

        sid = session_id or str(uuid.uuid4())

        # 2. Check if Gemini API key is configured or MOCK_MODE is enabled
        api_key = self.settings.GEMINI_API_KEY
        if not api_key or not api_key.strip() or self.settings.MOCK_MODE or os.getenv("MOCK_MODE", "").lower() == "true":
            # If no API key configured or in MOCK_MODE, use deterministic agent routing for testing/offline mode
            return await self._deterministic_offline_delegation(
                user_input, sid, user_id=uid, user_name=user_name, user_email=user_email, user_tz=user_tz
            )

        await self._ensure_session(sid, user_id=uid)

        # Set environment variable so Google ADK Gemini model authenticates automatically
        import os
        os.environ["GEMINI_API_KEY"] = api_key.strip()

        # 3. Live Google ADK Execution with Gemini
        usage_tracker.record_agent_run()

        # Compute live current time dynamically on every request turn (never static/at import)
        now_local = datetime.now().astimezone()
        if user_tz:
            try:
                import zoneinfo
                now_local = datetime.now(zoneinfo.ZoneInfo(user_tz))
            except Exception:
                now_local = datetime.now().astimezone()

        tz_name = now_local.tzname() or "Local Time"
        time_display = now_local.strftime("%I:%M:%S %p")
        date_display = now_local.strftime("%Y-%m-%d (%A)")
        iso_display = now_local.isoformat()

        context_lines = [
            f"[Live System Context: Current Date: {date_display}, Current Time: {time_display} {tz_name} (ISO: {iso_display})]"
        ]
        if user_name:
            context_lines.append(f"[Current User: {user_name} ({user_email or 'logged-in'})]")

        if conversation_history:
            history_lines = []
            for m in conversation_history:
                r = m.get("role")
                c = (m.get("content") or "").strip()
                if c and not (r == "user" and c == user_input.strip() and m == conversation_history[-1]):
                    speaker = "User" if r == "user" else "Assistant"
                    history_lines.append(f"{speaker}: {c}")
            if history_lines:
                context_lines.append("[Prior Conversation Context (Sliding Window):]")
                context_lines.extend(history_lines)
                context_lines.append("[End Prior Conversation Context]")

        prompt_text = "\n".join(context_lines) + f"\n\n{user_input}"

        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=prompt_text)],
        )

        max_attempts = 2
        for attempt in range(max_attempts):
            response_parts: List[str] = []
            activated_agents: List[str] = []
            tools_executed: List[str] = []

            try:
                async for event in self.runner.run_async(
                    user_id=uid,
                    session_id=sid,
                    new_message=content,
                ):
                    # Track agent node activity
                    if hasattr(event, "node_name") and event.node_name:
                        if event.node_name not in activated_agents:
                            activated_agents.append(event.node_name)

                    # Track tool calls
                    if hasattr(event, "get_function_calls"):
                        calls = event.get_function_calls()
                        if calls:
                            for call in calls:
                                tool_name = call.name if hasattr(call, "name") else str(call)
                                tools_executed.append(tool_name)
                                usage_tracker.record_tool_call(tool_name)

                    # Collect final response text
                    if hasattr(event, "is_final_response") and event.is_final_response():
                        target_content = getattr(event, "content", None) or getattr(event, "message", None)
                        if target_content and hasattr(target_content, "parts"):
                            for part in target_content.parts:
                                if hasattr(part, "text") and part.text:
                                    response_parts.append(part.text)

                final_text = "\n".join(response_parts) if response_parts else "Coordinator completed the task."
                usage_tracker.record_llm_request(tokens_used=len(final_text) // 4)

                return {
                    "session_id": sid,
                    "reply": final_text,
                    "orchestration": {
                        "root_agent": "SynaptixCoordinator",
                        "activated_agent": activated_agents[-1] if activated_agents else "SynaptixCoordinator",
                        "activated_agents": activated_agents or ["SynaptixCoordinator"],
                        "tools_executed": tools_executed,
                        "delegation_mode": "google_adk_live",
                    },
                    "budget_telemetry": usage_tracker.get_stats(),
                }

            except Exception as exc:
                err_str = str(exc)
                if ("503" in err_str or "UNAVAILABLE" in err_str) and attempt < max_attempts - 1:
                    logger.warning("Gemini 503 capacity spike on attempt %d. Retrying in 1.5s...", attempt + 1)
                    import asyncio
                    await asyncio.sleep(1.5)
                    continue

                logger.error("ADK runner execution failed: %s. Falling back to zero-cost offline engine.", exc)
                fallback = await self._deterministic_offline_delegation(
                    user_input, sid, user_id=uid, user_name=user_name, user_email=user_email, user_tz=user_tz
                )
                if "402" in err_str or "prepayment" in err_str.lower():
                    banner = (
                        "⚠️ **Google AI Studio 402 Notice:** The configured Gemini API key is linked to a project requiring prepayment credits. "
                        "To use the 100% Free Tier (₹0), create a key using **'Create API key in new project'** at [Google AI Studio](https://aistudio.google.com/).\n\n"
                        "---\n\n"
                    )
                elif "429" in err_str or "quota" in err_str.lower():
                    banner = (
                        "⚠️ **Rate Limit Notice:** Google AI Studio free tier rate limit reached. "
                        "Serving request via zero-cost local agent engine.\n\n---\n\n"
                    )
                else:
                    banner = f"⚠️ *Note: Live Gemini call encountered an issue ({err_str[:90]}). Fulfilled via zero-cost local engine:*\n\n---\n\n"

                fallback["reply"] = banner + fallback["reply"]
                fallback["orchestration"]["live_adk_error"] = str(exc)
                return fallback

    def _parse_natural_reminder_delay(self, text: str) -> Optional[int]:
        """Parse relative minute delay from natural phrases like 'in 1 minute' or 'in 30 mins'."""
        import re
        t_lower = text.lower()
        m_min = re.search(r"\bin\s+(\d+)\s*(?:minutes|minute|mins|min)\b", t_lower)
        if m_min:
            return int(m_min.group(1))
        m_hr = re.search(r"\bin\s+(\d+)\s*(?:hours|hour|hrs|hr)\b", t_lower)
        if m_hr:
            return int(m_hr.group(1)) * 60
        return None

    def _parse_natural_reminder_time(self, text: str, user_tz: Optional[str] = None) -> str:
        """Parse natural language phrases into an ISO 8601 reminder timestamp."""
        import re
        from datetime import datetime, date, timedelta, timezone
        now = datetime.now(timezone.utc)
        t_lower = text.lower()

        # Match "in X minutes" / "in X mins" / "in X min"
        m_min = re.search(r"\bin\s+(\d+)\s*(?:minutes|minute|mins|min)\b", t_lower)
        if m_min:
            mins = int(m_min.group(1))
            return (now + timedelta(minutes=mins)).replace(microsecond=0).isoformat()

        # Match "in X hours" / "in X hr" / "in X hrs"
        m_hr = re.search(r"\bin\s+(\d+)\s*(?:hours|hour|hrs|hr)\b", t_lower)
        if m_hr:
            hrs = int(m_hr.group(1))
            return (now + timedelta(hours=hrs)).replace(microsecond=0).isoformat()

        # Match "tomorrow at 6 pm", "tomorrow at 18:00", "tomorrow at 9 am"
        if "tomorrow" in t_lower:
            tomorrow_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
            m_time = re.search(r"(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", t_lower)
            if m_time and ("pm" in t_lower or "am" in t_lower or ":" in t_lower):
                hr = int(m_time.group(1))
                mn = int(m_time.group(2)) if m_time.group(2) else 0
                meridiem = m_time.group(3)
                if meridiem == "pm" and hr < 12:
                    hr += 12
                elif meridiem == "am" and hr == 12:
                    hr = 0
                return f"{tomorrow_date}T{hr:02d}:{mn:02d}:00"
            return f"{tomorrow_date}T09:00:00"

        # Default 1 hour from now
        return (now + timedelta(hours=1)).replace(microsecond=0).isoformat()

    async def _deterministic_offline_delegation(
        self,
        user_input: str,
        session_id: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        user_tz: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deterministic intent router for testing and offline execution without API keys.
        Ensures agents actually execute tools and demonstrate genuine delegation.
        """
        uid = user_id or "default_user"
        set_user_context(user_id=uid, name=user_name, email=user_email)
        usage_tracker.record_agent_run()
        lower = user_input.lower()
        activated_agent = "SynaptixCoordinator"
        tools_called = []
        reply = ""

        # ROUTING RULE 1: Smart Day Planner Intent (Evaluated first to capture multi-domain planning queries)
        if any(kw in lower for kw in ["plan my day", "plan tomorrow", "daily plan", "organize my day", "daily schedule", "smart plan", "plan"]):
            activated_agent = "SmartDayPlannerAgent"
            target_date = get_tomorrow_date() if "tomorrow" in lower else get_today_date()
            tasks_data = json.loads(task_list(status="pending"))
            events_data = json.loads(calendar_list_events(target_date))
            weather_data = json.loads(get_current_weather())
            tools_called.extend(["task_list", "calendar_list_events", "get_current_weather"])

            tasks_lines = [f"{i+1}. [Priority: {t['priority'].upper()}] {t['title']} (Due: {t['due_date']})" for i, t in enumerate(tasks_data.get("tasks", []))]
            events_lines = [f"• {e['start_time'][11:16]} - {e['end_time'][11:16]}: {e['summary']}" for e in events_data.get("events", [])]

            reply = f"""```
╔══════════════════════════════════════════════════════╗
║  📅  SYNAPTIX SMART DAY PLAN — {target_date}         ║
╚══════════════════════════════════════════════════════╝
```

🌤️ **WEATHER & ACTIVITY OUTLOOK**
• **{weather_data.get('condition', 'Clear')}**, {weather_data.get('temperature_c', 24.0)}°C (Feels like {weather_data.get('feels_like_c', 24.0)}°C, Humidity {weather_data.get('humidity_pct', 50)}%, Wind {weather_data.get('wind_kmh', 10.0)} km/h).
• {weather_data.get('activity_recommendation', 'Mild conditions favorable for outdoor breaks and desk productivity.')}

📅 **CALENDAR EVENTS**
{chr(10).join(events_lines) if events_lines else "• No scheduled meetings — full day available for focused deep work."}

✅ **PENDING TASKS (Prioritized)**
{chr(10).join(tasks_lines) if tasks_lines else "• No pending tasks! All clear."}

💡 **AI RECOMMENDATIONS**
• Dedicate 09:00 - 11:30 for high-priority task completion before lunch.
• Block 30 minutes in the afternoon for reviewing and capturing project notes."""

            # Automatically persist generated plan in Firestore day_plans collection
            try:
                from app.database.firestore import firestore_service
                firestore_service.save_day_plan(
                    user_id=uid,
                    date_str=target_date,
                    plan_data={
                        "plan": reply,
                        "formatted_markdown": reply,
                        "weather_summary": weather_data,
                        "pending_tasks_count": len(tasks_data.get("tasks", [])),
                        "scheduled_events_count": len(events_data.get("events", [])),
                    }
                )
            except Exception as save_err:
                logger.warning("Failed to auto-persist day plan: %s", save_err)

        # ROUTING RULE 2: Email Intent (Human-in-the-Loop Draft -> Approve -> Send)
        elif any(kw in lower for kw in ["email", "mail", "draft", "compose", "approve and send", "approve draft", "send the draft"]):
            activated_agent = "GmailAgent"
            # Check for explicit user approval to send an existing draft
            if any(kw in lower for kw in ["approve and send", "approve draft", "send the draft", "approved send", "approve", "send it", "looks good send", "send draft"]):
                import re
                match = re.search(r"draft-[a-f0-9]+", lower)
                draft_id = match.group(0) if match else None
                if not draft_id:
                    drafts_data = json.loads(email_draft_list())
                    drafts = drafts_data.get("drafts", [])
                    pending = [d for d in drafts if d.get("status") == "draft"]
                    if pending:
                        draft_id = pending[0].get("draft_id") or pending[0].get("id")

                if draft_id:
                    send_res = json.loads(email_draft_send(draft_id=draft_id))
                    tools_called.append("email_draft_send")
                    if send_res.get("success"):
                        reply = (
                            f"🚀 **Email Dispatched Successfully! (via GmailAgent)**\n\n"
                            f"• **Draft ID:** `{draft_id}`\n"
                            f"• **Status:** Sent\n"
                            f"• **Destination:** {send_res.get('result', {}).get('to', 'Recipient')}\n"
                            f"• **Mode:** {'Live Gmail API' if send_res.get('result', {}).get('is_live_gmail') else 'Zero-Cost Local Adapter'}\n\n"
                            f"Your email has been safely delivered."
                        )
                    else:
                        reply = f"❌ **Dispatch Failed:** {send_res.get('error', 'Unable to send draft.')}"
                else:
                    reply = "⚠️ No pending draft ID found to send. Please specify the draft ID, e.g., 'Approve and send draft [draft-id]'."
            else:
                # Drafting step: create complete preview and pause for user approval
                to_target = "recipient@example.com"
                if " to " in lower:
                    parts = user_input.split(" to ", 1)[1].split(" about ", 1)
                    to_target = parts[0].strip()
                elif "email " in lower:
                    to_target = user_input.split("email ", 1)[1].split(" ", 1)[0].strip()

                signoff = user_name or "Synaptix AI Assistant"
                subject = f"Follow-up: {user_input[:40]}"
                body = (
                    f"Hi {to_target.split('@')[0].title()},\n\n"
                    f"I hope you're having a productive week.\n\n"
                    f"Regarding our discussion:\n"
                    f"• {user_input}\n\n"
                    f"Please let me know if this works for you or if you need any adjustments.\n\n"
                    f"Best regards,\n{signoff}"
                )
                draft_res = json.loads(email_draft_create(to=to_target, subject=subject, body=body))
                tools_called.append("email_draft_create")
                d = draft_res.get("draft", {})
                d_id = d.get("draft_id", "draft-101")
                reply = (
                    f"📧 **Email Draft Created (GmailAgent)**\n\n"
                    f"• **To:** {d.get('to', to_target)}\n"
                    f"• **Subject:** {d.get('subject', subject)}\n"
                    f"• **Draft ID:** `{d_id}`\n\n"
                    f"---\n"
                    f"{d.get('body', body)}\n"
                    f"---\n\n"
                    f"⚠️ **Human-in-the-Loop Approval Required:**\n"
                    f"Please review the draft above. To dispatch this email, reply with:\n"
                    f"👉 **`Approve and send draft {d_id}`** (or *'looks good, send it'*).\n\n"
                    f"If you'd like to adjust the tone, subject, or details, let me know what changes to make!"
                )

        # ROUTING RULE 3: Notes Intent (Evaluated before tasks so 'save a note and remind me' activates NotesAgent)
        elif any(kw in lower for kw in ["note", "remember", "save note", "write down"]):
            activated_agent = "NotesAgent"
            if "search" in lower or "find" in lower:
                term = lower.replace("search notes for", "").replace("search notes", "").strip()
                raw_res = json.loads(note_search(term))
                tools_called.append("note_search")
                matches = raw_res.get("notes", [])
                lines = [f"- **{n['title']}**: {n['content']}" for n in matches]
                reply = f"🔍 **Notes Found (NotesAgent):**\n" + ("\n".join(lines) if lines else f"No notes matching '{term}'.")
            elif "list" in lower or "show" in lower or "recent" in lower:
                raw_res = json.loads(note_list())
                tools_called.append("note_list")
                notes = raw_res.get("notes", [])
                lines = [f"- **{n['title']}** (Created: {n['created_at'][:10]}): {n['content']}" for n in notes]
                reply = f"📝 **Recent Notes (NotesAgent):**\n" + ("\n".join(lines) if lines else "No notes saved yet.")
            else:
                content = user_input.replace("save note:", "").replace("save note", "").strip()
                raw_res = json.loads(note_save(content=content or "Personal note"))
                tools_called.append("note_save")
                n = raw_res["note"]
                if "remind" in lower:
                    delay = self._parse_natural_reminder_delay(user_input)
                    if delay is not None:
                        r_res = json.loads(set_reminder(
                            title=f"Note: {n['title']}",
                            delay_minutes=delay,
                            source_type="note",
                            source_id=n["id"]
                        ))
                    else:
                        remind_iso = self._parse_natural_reminder_time(user_input, user_tz=user_tz)
                        r_res = json.loads(set_reminder(
                            title=f"Note: {n['title']}",
                            remind_at_iso=remind_iso,
                            source_type="note",
                            source_id=n["id"]
                        ))
                    tools_called.append("set_reminder")
                    r = r_res["reminder"]
                    formatted_time = r_res.get("formatted_time", r.get("remind_at", ""))
                    reply = (
                        f"📝 **Note Saved & Reminder Attached (NotesAgent):**\n"
                        f"- **Note ID:** `{n['id']}`\n"
                        f"- **Title:** {n['title']}\n"
                        f"- **Content:** {n['content']}\n"
                        f"- **Reminder ID:** `{r['id']}`\n"
                        f"- **Alert Time:** `{formatted_time}` (`{r['remind_at']}`)"
                    )
                else:
                    reply = f"📝 **Note Saved by NotesAgent:**\n- **ID:** `{n['id']}`\n- **Title:** {n['title']}\n- **Content:** {n['content']}"

        # ROUTING RULE 4: Task & Reminder Intent
        elif any(kw in lower for kw in ["task", "todo", "remind me", "reminder", "reminders", "pending", "complete task"]):
            activated_agent = "TaskAgent"
            if "dismiss" in lower and "reminder" in lower:
                import re
                match = re.search(r"reminder-[a-f0-9]+", lower)
                rem_id = match.group(0) if match else None
                if not rem_id:
                    rems_data = json.loads(list_reminders(status="pending"))
                    rems = rems_data.get("reminders", [])
                    if rems:
                        rem_id = rems[0].get("id")
                if rem_id:
                    d_res = json.loads(dismiss_reminder(rem_id))
                    tools_called.append("dismiss_reminder")
                    reply = f"✅ **Reminder Dismissed:** `{rem_id}` has been cleared."
                else:
                    reply = "⚠️ No pending reminder ID found to dismiss."
            elif "reminder" in lower and any(w in lower for w in ["list", "show", "my", "all"]):
                r_res = json.loads(list_reminders())
                tools_called.append("list_reminders")
                rems = r_res.get("reminders", [])
                lines = [f"- [`{r['id']}`] **{r['title']}** (Time: {r['remind_at']}, Status: {r['status']})" for r in rems]
                reply = f"⏰ **Your Reminders (via TaskAgent):**\n" + ("\n".join(lines) if lines else "No reminders scheduled.")
            elif "remind" in lower:
                title = user_input.replace("set reminder for", "").replace("set reminder to", "").replace("set reminder", "").replace("remind me to", "").replace("remind me", "").strip(": ")
                import re
                clean_title = re.sub(r"\s+in\s+\d+\s*(?:minutes|minute|mins|min|hours|hour|hrs|hr|days|day)", "", title, flags=re.IGNORECASE)
                clean_title = re.sub(r"\s+tomorrow\s*(?:at\s*\d+(?::\d+)?\s*(?:am|pm)?)?", "", clean_title, flags=re.IGNORECASE).strip()
                raw_t = json.loads(task_create(title=clean_title or title or "New Task"))
                tools_called.append("task_create")
                t = raw_t["task"]

                delay = self._parse_natural_reminder_delay(user_input)
                if delay is not None:
                    raw_r = json.loads(set_reminder(
                        title=t["title"],
                        delay_minutes=delay,
                        source_type="task",
                        source_id=t["id"]
                    ))
                else:
                    remind_iso = self._parse_natural_reminder_time(user_input, user_tz=user_tz)
                    raw_r = json.loads(set_reminder(
                        title=t["title"],
                        remind_at_iso=remind_iso,
                        source_type="task",
                        source_id=t["id"]
                    ))
                tools_called.append("set_reminder")
                r = raw_r["reminder"]
                formatted_time = raw_r.get("formatted_time", r.get("remind_at", ""))
                reply = (
                    f"⏰ **Smart Reminder Created (TaskAgent):**\n"
                    f"- **Reminder ID:** `{r['id']}`\n"
                    f"- **Title:** {r['title']}\n"
                    f"- **Alert Time:** `{formatted_time}` (`{r['remind_at']}`)\n"
                    f"- **Linked Task:** `{t['id']}`\n"
                    f"- **Status:** {r['status'].capitalize()}"
                )
            elif "add" in lower or "create" in lower:
                title = user_input.replace("add task", "").strip(": ")
                raw_res = json.loads(task_create(title=title or "New Task"))
                tools_called.append("task_create")
                t = raw_res["task"]
                reply = f"✅ **Task Created by TaskAgent:**\n- **ID:** `{t['id']}`\n- **Title:** {t['title']}\n- **Due Date:** {t['due_date']}\n- **Priority:** {t['priority'].upper()}\n- **Status:** {t['status']}"
            elif "pending" in lower or "show" in lower or "list" in lower:
                raw_res = json.loads(task_list(status="pending"))
                tools_called.append("task_list")
                tasks = raw_res.get("tasks", [])
                lines = [f"- [`{t['id']}`] **{t['title']}** (Due: {t['due_date']}, Priority: {t['priority']})" for t in tasks]
                reply = f"📋 **Pending Tasks (via TaskAgent):**\n" + ("\n".join(lines) if lines else "No pending tasks found!")
            else:
                raw_res = json.loads(task_list())
                tools_called.append("task_list")
                reply = f"📋 **Tasks Overview (TaskAgent):** Found {raw_res['count']} tasks in storage."

        # ROUTING RULE 4: Calendar Intent
        elif any(kw in lower for kw in ["calendar", "schedule", "meeting", "event", "appointment"]):
            activated_agent = "CalendarAgent"
            if "schedule" in lower or "book" in lower:
                summary = user_input.replace("schedule meeting", "").replace("schedule", "").strip() or "Productivity Session"
                tomorrow = get_tomorrow_date()
                raw_res = json.loads(calendar_create_event(
                    summary=summary,
                    start_time=f"{tomorrow}T11:00:00",
                    end_time=f"{tomorrow}T12:00:00",
                    description="Scheduled via Synaptix CalendarAgent",
                    location="Virtual Meet"
                ))
                tools_called.append("calendar_create_event")
                ev = raw_res["event"]
                reply = f"📅 **Meeting Scheduled by CalendarAgent:**\n- **Event:** {ev['summary']}\n- **Start:** {ev['start_time']}\n- **End:** {ev['end_time']}\n- **Location:** {ev['location']}"
            else:
                raw_res = json.loads(calendar_list_events())
                tools_called.append("calendar_list_events")
                events = raw_res.get("events", [])
                lines = [f"- **{e['summary']}** ({e['start_time'][11:16]} - {e['end_time'][11:16]})" for e in events]
                reply = f"📅 **Calendar Schedule for Today (CalendarAgent):**\n" + ("\n".join(lines) if lines else "No events scheduled for today.")

        # DEFAULT: Coordinator Greeting
        else:
            reply = (
                "👋 Hello! I am the **Synaptix Coordinator Agent**.\n\n"
                "I delegate your requests across my 4 specialized agents:\n"
                "- ✅ **TaskAgent:** Manage to-dos and deadlines (e.g. *'Add task: prepare slides'*).\n"
                "- 📝 **NotesAgent:** Store and search ideas (e.g. *'Save note: meeting highlights'*).\n"
                "- 📅 **CalendarAgent:** Schedule and check events (e.g. *'Schedule meeting tomorrow'*).\n"
                "- 🧭 **SmartDayPlannerAgent:** Synthesize your daily timetable (e.g. *'Plan my day tomorrow'*)."
            )

        for t in tools_called:
            usage_tracker.record_tool_call(t)

        return {
            "session_id": session_id,
            "reply": reply,
            "orchestration": {
                "root_agent": "SynaptixCoordinator",
                "activated_agent": activated_agent,
                "tools_executed": tools_called,
                "delegation_mode": "deterministic_offline",
            },
            "budget_telemetry": usage_tracker.get_stats(),
        }


# Singleton orchestrator instance
orchestrator = MultiAgentOrchestrator()
