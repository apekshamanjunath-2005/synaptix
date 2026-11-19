"""
Milestone 5 — Google Calendar MCP Integration Verification Tests
Tests Calendar MCP Provider, event CRUD, timeslot conflict checking,
REST API endpoints, and end-to-end CalendarAgent delegation.
"""

import sys
import json
import time
import threading
import urllib.request
import urllib.error
from datetime import date, timedelta
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from app.main import app
from app.tools.calendar_mcp import calendar_mcp


class LiveCalendarServer(threading.Thread):
    def __init__(self, port=8893):
        super().__init__(daemon=True)
        config = uvicorn.Config(app=app, host="127.0.0.1", port=port, log_level="error")
        self.server = uvicorn.Server(config=config)
        self.port = port

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True


def make_request(url, method="GET", payload=None):
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


def test_milestone5_calendar_mcp():
    print("=================================================================")
    print(" 📅 RUNNING MILESTONE 5: CALENDAR MCP INTEGRATION VERIFICATION")
    print("=================================================================")

    target_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")

    # 1. Test Calendar MCP Provider Initialization
    print("\n[Test 1] Testing Calendar MCP Provider Initialization...")
    assert calendar_mcp is not None
    print(f"  ✅ Calendar MCP Provider initialized (Live Google API configured: {calendar_mcp.is_live_google})")

    # 2. Test MCP Event CRUD
    print("\n[Test 2] Testing Calendar MCP Event CRUD Operations...")
    # 2a: Create event
    start_time = f"{target_date}T14:00:00"
    end_time = f"{target_date}T15:00:00"
    event = calendar_mcp.create_event(
        summary="Deep Learning Reading Group",
        start_time=start_time,
        end_time=end_time,
        description="Discuss Transformer attention mechanisms",
        location="Discord Voice Room"
    )
    assert event["id"].startswith("event-")
    event_id = event["id"]
    print(f"  ✅ create_event scheduled: {event['summary']} (ID: {event_id})")

    # 2b: List events for date
    events_list = calendar_mcp.list_events(date_str=target_date)
    assert any(e["id"] == event_id for e in events_list)
    print(f"  ✅ list_events found {len(events_list)} event(s) for {target_date}")

    # 2c: Update event
    updated = calendar_mcp.update_event(event_id, summary="Advanced Transformers & Multi-Agent Study")
    assert updated is not None
    assert updated["summary"] == "Advanced Transformers & Multi-Agent Study"
    print(f"  ✅ update_event verified: {updated['summary']}")

    # 3. Test Conflict and Availability Checking
    print("\n[Test 3] Testing Timeslot Conflict & Availability Checking...")
    # 3a: Conflicting timeslot (overlaps 14:00 - 15:00 with 14:30 - 15:30)
    conflict_check = calendar_mcp.check_availability(
        start_time=f"{target_date}T14:30:00",
        end_time=f"{target_date}T15:30:00"
    )
    assert conflict_check["available"] is False, "Conflict check must identify overlapping event"
    assert conflict_check["conflicts_count"] >= 1
    assert any(c["id"] == event_id for c in conflict_check["conflicting_events"])
    print(f"  ✅ Conflict accurately detected: {conflict_check['conflicts_count']} conflict(s) found for overlapping slot")

    # 3b: Clear timeslot (no overlap: 16:00 - 17:00)
    free_check = calendar_mcp.check_availability(
        start_time=f"{target_date}T16:00:00",
        end_time=f"{target_date}T17:00:00"
    )
    assert free_check["available"] is True
    assert free_check["conflicts_count"] == 0
    print("  ✅ Availability check accurately verified clear timeslot (available: True)")

    # 2d: Delete event
    del_res = calendar_mcp.delete_event(event_id)
    assert del_res is True
    post_del_events = calendar_mcp.list_events(date_str=target_date)
    assert not any(e["id"] == event_id for e in post_del_events)
    print(f"  ✅ delete_event successfully removed: {event_id}")

    # 4. Live REST Endpoints Testing
    print("\n[Test 4] Testing Calendar REST Endpoints via Live HTTP Server...")
    server = LiveCalendarServer(port=8893)
    server.start()
    time.sleep(1.2)
    base_url = "http://127.0.0.1:8893"

    try:
        # 4a: POST /api/calendar/events
        post_code, post_body = make_request(
            f"{base_url}/api/calendar/events",
            method="POST",
            payload={
                "summary": "AI Product Review",
                "start_time": f"{target_date}T09:00:00",
                "end_time": f"{target_date}T10:00:00",
                "location": "Meet"
            }
        )
        assert post_code == 201
        api_event_id = post_body["event"]["id"]
        print(f"  ✅ POST /api/calendar/events returned 201 Created: {api_event_id}")

        # 4b: GET /api/calendar/events?date=...
        get_code, get_body = make_request(f"{base_url}/api/calendar/events?date={target_date}")
        assert get_code == 200
        assert any(e["id"] == api_event_id for e in get_body["events"])
        print(f"  ✅ GET /api/calendar/events returned 200 OK: found {get_body['count']} events")

        # 4c: POST /api/calendar/check-availability
        check_code, check_body = make_request(
            f"{base_url}/api/calendar/check-availability",
            method="POST",
            payload={
                "start_time": f"{target_date}T09:30:00",
                "end_time": f"{target_date}T10:30:00"
            }
        )
        assert check_code == 200
        assert check_body["available"] is False
        print(f"  ✅ POST /api/calendar/check-availability detected conflict as expected: {check_body['conflicting_events'][0]['summary']}")

        # 4d: DELETE /api/calendar/events/{event_id}
        del_code, _ = make_request(f"{base_url}/api/calendar/events/{api_event_id}", method="DELETE")
        assert del_code == 200
        print(f"  ✅ DELETE /api/calendar/events/{api_event_id} returned 200 OK")

        # 5. End-to-End: CalendarAgent natural language delegation
        print("\n[Test 5] Testing End-to-End: CalendarAgent schedules event via natural language...")
        chat_code, chat_body = make_request(
            f"{base_url}/api/chat",
            method="POST",
            payload={"message": "Schedule meeting with design team tomorrow at 3 PM for 1 hour"}
        )
        assert chat_code == 200
        orch = chat_body.get("orchestration", {})
        assert orch.get("activated_agent") == "CalendarAgent"
        assert "calendar_create_event" in orch.get("tools_executed", [])
        print(f"  ✅ End-to-End verified: CalendarAgent scheduled event via MCP! Tool: {orch['tools_executed']}")

    finally:
        server.stop()

    print("\n=================================================================")
    print(" 🎉 ALL MILESTONE 5 CALENDAR MCP TESTS PASSED SUCCESSFULLY!")
    print("=================================================================")


if __name__ == "__main__":
    test_milestone5_calendar_mcp()
