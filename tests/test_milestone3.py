"""
Milestone 3 — Multi-Agent System Verification Tests
Tests Google ADK configuration, all 5 agents independently,
and verifies real delegation and tool execution through the Coordinator Agent.
"""

import sys
import json
import time
import threading
import urllib.request
import urllib.error
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from app.main import app
from app.agents import (
    coordinator_agent,
    task_agent,
    notes_agent,
    calendar_agent,
    smart_day_planner_agent,
)
from app.agents.tools import (
    task_create,
    task_list,
    task_update,
    note_save,
    note_list,
    note_search,
    calendar_create_event,
    calendar_list_events,
    calendar_check_availability,
    get_current_weather,
)
from app.agents.orchestrator import orchestrator


class LiveMultiAgentServer(threading.Thread):
    def __init__(self, port=8891):
        super().__init__(daemon=True)
        config = uvicorn.Config(app=app, host="127.0.0.1", port=port, log_level="error")
        self.server = uvicorn.Server(config=config)
        self.port = port

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True


def make_request(url, method="POST", payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            body = json.loads(body)
        except Exception:
            pass
        return e.code, body


def test_milestone3_multi_agent():
    print("=================================================================")
    print(" 🤖 RUNNING MILESTONE 3: MULTI-AGENT SYSTEM VERIFICATION")
    print("=================================================================")

    # 1. Independent Agent Structure Verification
    print("\n[Test 1] Testing Agent Definitions & Sub-Agent Wiring...")
    assert coordinator_agent.name == "SynaptixCoordinator"
    assert len(coordinator_agent.sub_agents) >= 4, f"Expected at least 4 sub-agents, got {len(coordinator_agent.sub_agents)}"
    sub_agent_names = [a.name for a in coordinator_agent.sub_agents]
    assert "TaskAgent" in sub_agent_names
    assert "NotesAgent" in sub_agent_names
    assert "CalendarAgent" in sub_agent_names
    assert "SmartDayPlannerAgent" in sub_agent_names
    assert "GmailAgent" in sub_agent_names
    print(f"  ✅ Coordinator sub-agents wired correctly: {sub_agent_names}")

    # 2. Independent Test: Task Agent Tools
    print("\n[Test 2] Testing TaskAgent Tools Independently...")
    tool_names = [t.name for t in task_agent.tools]
    assert "task_create" in tool_names and "task_list" in tool_names
    create_res = json.loads(task_create("Finish Multi-Agent tests", due_date="2026-11-20", priority="high"))
    assert create_res["success"] is True
    created_id = create_res["task"]["id"]
    list_res = json.loads(task_list(status="pending"))
    assert any(t["id"] == created_id for t in list_res["tasks"])
    update_res = json.loads(task_update(created_id, status="completed"))
    assert update_res["task"]["status"] == "completed"
    print(f"  ✅ TaskAgent tools verified: task_create, task_list, task_update (ID: {created_id})")

    # 3. Independent Test: Notes Agent Tools
    print("\n[Test 3] Testing NotesAgent Tools Independently...")
    save_res = json.loads(note_save(content="Google ADK coordinates sub-agents via LlmAgent transfers.", tags="adk,ai"))
    assert save_res["success"] is True
    search_res = json.loads(note_search("ADK"))
    assert search_res["count"] >= 1
    print(f"  ✅ NotesAgent tools verified: note_save, note_search (Found: {search_res['count']} matches)")

    # 4. Independent Test: Calendar Agent Tools
    print("\n[Test 4] Testing CalendarAgent Tools Independently...")
    cal_res = json.loads(calendar_create_event(
        summary="Sprint Planning",
        start_time="2026-11-20T14:00:00",
        end_time="2026-11-20T15:00:00",
        description="Weekly sprint planning"
    ))
    assert cal_res["success"] is True
    avail_res = json.loads(calendar_check_availability("2026-11-20T14:30:00", "2026-11-20T15:30:00"))
    assert avail_res["available"] is False, "Conflict check should detect overlapping event"
    print("  ✅ CalendarAgent tools verified: calendar_create_event, calendar_check_availability (Conflict detected)")

    # 5. Independent Test: Smart Day Planner Tools
    print("\n[Test 5] Testing SmartDayPlannerAgent Tools Independently...")
    weather_res = json.loads(get_current_weather("Bengaluru"))
    assert "temperature_c" in weather_res
    print(f"  ✅ Planner tools verified: weather={weather_res['condition']}, temp={weather_res['temperature_c']}°C")

    # 6. Live Orchestrator & End-to-End Delegation Tests via HTTP Server
    print("\n[Test 6] Testing Real Agent Delegation via Live HTTP API (/api/chat)...")
    server = LiveMultiAgentServer(port=8891)
    server.start()
    time.sleep(1.2)
    base_url = "http://127.0.0.1:8891"

    try:
        # Delegation 6a: Task Intent -> TaskAgent
        status_task, body_task = make_request(f"{base_url}/api/chat", payload={"message": "Add task: buy groceries tomorrow"})
        assert status_task == 200
        assert body_task["orchestration"]["activated_agent"] == "TaskAgent"
        assert "task_create" in body_task["orchestration"]["tools_executed"]
        print(f"  ✅ Task delegation verified: Activated {body_task['orchestration']['activated_agent']} with tool {body_task['orchestration']['tools_executed']}")

        # Delegation 6b: Notes Intent -> NotesAgent
        status_note, body_note = make_request(f"{base_url}/api/chat", payload={"message": "Save note: discussed API rate limits"})
        assert status_note == 200
        assert body_note["orchestration"]["activated_agent"] == "NotesAgent"
        assert "note_save" in body_note["orchestration"]["tools_executed"]
        print(f"  ✅ Notes delegation verified: Activated {body_note['orchestration']['activated_agent']} with tool {body_note['orchestration']['tools_executed']}")

        # Delegation 6c: Calendar Intent -> CalendarAgent
        status_cal, body_cal = make_request(f"{base_url}/api/chat", payload={"message": "Schedule meeting with team tomorrow at 11 AM"})
        assert status_cal == 200
        assert body_cal["orchestration"]["activated_agent"] == "CalendarAgent"
        assert "calendar_create_event" in body_cal["orchestration"]["tools_executed"] or "calendar_check_availability" in body_cal["orchestration"]["tools_executed"]
        print(f"  ✅ Calendar delegation verified: Activated {body_cal['orchestration']['activated_agent']} with tool {body_cal['orchestration']['tools_executed']}")

        # Delegation 6d: Planner Intent -> SmartDayPlannerAgent
        status_plan, body_plan = make_request(f"{base_url}/api/chat", payload={"message": "Plan my day tomorrow based on my tasks, calendar and weather"})
        assert status_plan == 200
        assert body_plan["orchestration"]["activated_agent"] == "SmartDayPlannerAgent"
        assert "task_list" in body_plan["orchestration"]["tools_executed"]
        assert "calendar_list_events" in body_plan["orchestration"]["tools_executed"]
        assert "get_current_weather" in body_plan["orchestration"]["tools_executed"]
        print(f"  ✅ Smart Planner delegation verified: Activated {body_plan['orchestration']['activated_agent']} synthesizing tasks, calendar, and weather!")

    finally:
        server.stop()

    print("\n=================================================================")
    print(" 🎉 ALL MILESTONE 3 MULTI-AGENT VERIFICATION TESTS PASSED!")
    print("=================================================================")


if __name__ == "__main__":
    test_milestone3_multi_agent()
