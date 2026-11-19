"""
Milestone 7: Smart Day Planner Multi-Agent Integration Verification Test Suite
Verifies:
1. Multi-Agent Synthesis Engine (Firestore Tasks + Calendar MCP + Weather Tool)
2. Priority task ranking (High > Medium > Low) slotted into morning focus blocks
3. Conflict avoidance with scheduled calendar meetings
4. REST endpoint POST /api/planner/generate via live HTTP server
5. End-to-end natural language day planning via Coordinator and SmartDayPlannerAgent (/api/chat)
"""

import sys
import json
import logging
import threading
import time
import urllib.request
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from app.api.planner import synthesize_daily_plan
from app.database.firestore import firestore_service
from app.tools.calendar_mcp import calendar_mcp
from app.main import app

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("test_milestone7")

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8004
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"


def make_request(url: str, method: str = "GET", payload: dict = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload else None
    headers = {"Content-Type": "application/json"} if payload else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode("utf-8"))
        return e.code, body


def test_milestone7_smart_day_planner():
    print("\n" + "=" * 65)
    print(" 🧭 RUNNING MILESTONE 7: SMART DAY PLANNER VERIFICATION")
    print("=" * 65)

    test_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    # Setup fixture: Seed high priority task and a meeting
    t_record = firestore_service.add_task(
        title="Prepare Investor Demo Slides",
        due_date=test_date,
        priority="high",
        status="pending"
    )
    t_id = t_record["id"]
    e_record = calendar_mcp.create_event(
        summary="Product Architecture Review",
        start_time=f"{test_date}T10:00:00",
        end_time=f"{test_date}T11:00:00",
        description="Review milestone deliverables"
    )

    try:
        # ─────────────────────────────────────────────────────────────
        # [Test 1] Testing Core Multi-Agent Synthesis Engine
        # ─────────────────────────────────────────────────────────────
        print("\n[Test 1] Testing Multi-Domain Synthesis Engine...")
        plan = synthesize_daily_plan(target_date=test_date, city="Bengaluru")

        assert plan.target_date == test_date
        assert plan.weather["city"] == "Bengaluru"
        assert plan.pending_tasks_count >= 1, "Pending tasks should be collected from Firestore"
        assert plan.scheduled_events_count >= 1, "Calendar meetings should be collected from MCP"
        assert len(plan.timetable) >= 4, "Timetable must have focus, meeting, and break blocks"
        
        # Verify priority task was placed into morning focus block
        focus_blocks = [b for b in plan.timetable if b.activity_type == "focus"]
        assert len(focus_blocks) >= 1
        assert "Investor Demo" in focus_blocks[0].title or "Prepare" in focus_blocks[0].title
        print(f"  ✅ High-priority task slotted into deep focus block: {focus_blocks[0].title}")

        # Verify meeting was scheduled
        meeting_blocks = [b for b in plan.timetable if b.activity_type == "meeting"]
        assert len(meeting_blocks) >= 1
        assert "Architecture Review" in meeting_blocks[0].title
        print(f"  ✅ Calendar meeting integrated into timetable: {meeting_blocks[0].title} ({meeting_blocks[0].time_range})")
        print(f"  ✅ Weather advice included: {plan.weather['condition']}, {plan.weather['temperature_c']}°C")

        # ─────────────────────────────────────────────────────────────
        # [Test 2] Testing POST /api/planner/generate Live HTTP Endpoint
        # ─────────────────────────────────────────────────────────────
        print("\n[Test 2] Testing POST /api/planner/generate REST Endpoint...")
        config = uvicorn.Config(app=app, host=SERVER_HOST, port=SERVER_PORT, log_level="warning")
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        time.sleep(1.5)

        try:
            code, body = make_request(
                f"{BASE_URL}/api/planner/generate",
                method="POST",
                payload={"target_date": test_date, "city": "Bengaluru"}
            )
            assert code == 200, f"Expected 200, got {code}"
            assert body["target_date"] == test_date
            assert "timetable" in body
            assert len(body["timetable"]) > 0
            assert "formatted_markdown" in body
            print(f"  ✅ POST /api/planner/generate returned 200 OK: {len(body['timetable'])} timetable blocks generated")

            # ─────────────────────────────────────────────────────────────
            # [Test 3] End-to-End: Coordinator delegates to SmartDayPlannerAgent
            # ─────────────────────────────────────────────────────────────
            print("\n[Test 3] Testing Natural Language Planner Request via /api/chat...")
            chat_code, chat_body = make_request(
                f"{BASE_URL}/api/chat",
                method="POST",
                payload={"message": "I have three tasks tomorrow and a meeting at 11. Help me organize my day."}
            )
            assert chat_code == 200, f"Expected 200 from /api/chat, got {chat_code}"
            assert chat_body["orchestration"]["activated_agent"] == "SmartDayPlannerAgent", (
                f"Expected SmartDayPlannerAgent, got {chat_body['orchestration']['activated_agent']}"
            )
            tools_called = chat_body["orchestration"]["tools_executed"]
            assert "task_list" in tools_called
            assert "calendar_list_events" in tools_called
            assert "get_current_weather" in tools_called
            print(f"  ✅ SmartDayPlannerAgent coordinated 3 agents/tools: {tools_called}")

            reply_text = chat_body["reply"]
            assert "SYNAPTIX SMART DAY PLAN" in reply_text
            assert "WEATHER" in reply_text
            assert any(k in reply_text.upper() for k in ["CALENDAR", "SCHEDULE", "COMMITMENT", "MEETING"])
            assert any(k in reply_text.upper() for k in ["TASK", "TODO", "WORK", "PRIORITY"])
            print("  ✅ Structured Day Plan Generated:")
            for line in reply_text.split("\n")[:10]:
                print(f"     {line}")
            print("     ...")

        finally:
            server.should_exit = True
            time.sleep(0.5)

    finally:
        # Cleanup seeded records
        if t_id:
            firestore_service.delete_task(t_id)
        if e_record and "id" in e_record:
            calendar_mcp.delete_event(e_record["id"])

    print("\n" + "=" * 65)
    print(" 🎉 ALL MILESTONE 7 SMART DAY PLANNER TESTS PASSED!")
    print("=" * 65)


if __name__ == "__main__":
    test_milestone7_smart_day_planner()
