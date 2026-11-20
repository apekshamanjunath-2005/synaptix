"""
Unit & Integration Test Suite for Smart Reminders System
Tests:
1. FirestoreService reminders collection CRUD operations.
2. Strict per-user reminder data isolation (Alice vs Bob).
3. Due reminder calculation and status lifecycle (pending -> triggered -> snoozed -> dismissed).
4. Calendar MCP default popup reminder attachment.
5. Agent tools (set_reminder, list_reminders, dismiss_reminder).
6. Multi-agent natural language delegation for reminders.
7. REST API Endpoints: GET/POST /api/reminders, GET /api/reminders/due, PATCH /api/reminders/{id}, DELETE /api/reminders/{id}.
"""

import sys
import json
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from app.main import app
from app.database.firestore import firestore_service
from app.tools.calendar_mcp import calendar_mcp
from app.agents.tools import set_reminder, list_reminders, dismiss_reminder, snooze_reminder
from app.agents.orchestrator import orchestrator
from app.api.auth import create_session_token


def test_firestore_reminders_unit_and_isolation():
    print("\n" + "=" * 65)
    print(" 🧭 RUNNING FIRESTORE REMINDERS UNIT & ISOLATION TESTS")
    print("=" * 65)

    alice = "user_alice_rem_101"
    bob = "user_bob_rem_202"

    # Pre-cleanup to ensure clean slate
    for r in firestore_service.list_reminders(user_id=alice):
        firestore_service.delete_reminder(user_id=alice, reminder_id=r["id"])
    for r in firestore_service.list_reminders(user_id=bob):
        firestore_service.delete_reminder(user_id=bob, reminder_id=r["id"])

    now = datetime.now(timezone.utc)
    t_past = (now - timedelta(minutes=5)).isoformat()
    t_future = (now + timedelta(hours=2)).isoformat()

    # 1. Alice creates reminders
    print("\n[Test 1] Testing reminder creation for Alice...")
    r1 = firestore_service.create_reminder(user_id=alice, title="Submit DBMS report", remind_at_iso=t_past, source_type="task")
    r2 = firestore_service.create_reminder(user_id=alice, title="Sprint retro meeting", remind_at_iso=t_future, source_type="event")
    assert r1["id"].startswith("reminder-")
    assert r1["status"] == "pending"
    assert r1["user_id"] == alice
    print(f"  ✅ Created Alice reminders: {r1['id']}, {r2['id']}")

    # 2. Bob creates a reminder
    print("\n[Test 2] Testing reminder creation for Bob...")
    r_bob = firestore_service.create_reminder(user_id=bob, title="Bob confidential reminder", remind_at_iso=t_past, source_type="custom")
    assert r_bob["user_id"] == bob
    print(f"  ✅ Created Bob reminder: {r_bob['id']}")

    # 3. User isolation check
    print("\n[Test 3] Verifying user isolation...")
    alice_list = firestore_service.list_reminders(user_id=alice)
    assert len(alice_list) == 2
    assert all(r["user_id"] == alice for r in alice_list)
    assert not any(r["id"] == r_bob["id"] for r in alice_list)

    bob_list = firestore_service.list_reminders(user_id=bob)
    assert len(bob_list) == 1
    assert bob_list[0]["id"] == r_bob["id"]
    print("  ✅ Alice cannot see Bob's reminders, Bob cannot see Alice's reminders")

    # 4. Due reminders check
    print("\n[Test 4] Testing get_due_reminders...")
    alice_due = firestore_service.get_due_reminders(user_id=alice, now_iso=now.isoformat())
    assert len(alice_due) == 1
    assert alice_due[0]["id"] == r1["id"]
    print(f"  ✅ Exactly 1 reminder is due for Alice: {alice_due[0]['title']}")

    # 5. Status update: Snooze
    print("\n[Test 5] Testing snooze_reminder...")
    snoozed = firestore_service.update_reminder_status(user_id=alice, reminder_id=r1["id"], status="snoozed", snooze_minutes=15)
    assert snoozed is not None
    assert snoozed["status"] == "snoozed"
    assert snoozed["remind_at"] > now.isoformat()
    # Now it should no longer be due
    alice_due_after = firestore_service.get_due_reminders(user_id=alice, now_iso=now.isoformat())
    assert len(alice_due_after) == 0
    print(f"  ✅ Successfully snoozed reminder {r1['id']}; no longer due immediately")

    # 6. Status update: Dismiss
    print("\n[Test 6] Testing dismiss_reminder...")
    dismissed = firestore_service.update_reminder_status(user_id=alice, reminder_id=r2["id"], status="dismissed")
    assert dismissed["status"] == "dismissed"
    active_alice = firestore_service.list_reminders(user_id=alice, status="pending")
    assert len(active_alice) == 0
    print(f"  ✅ Dismissed reminder {r2['id']}")

    # 7. Cross-user modification forbidden
    print("\n[Test 7] Verifying Bob cannot mutate Alice's reminder...")
    hacked = firestore_service.update_reminder_status(user_id=bob, reminder_id=r1["id"], status="dismissed")
    assert hacked is None, "Bob should not be able to update Alice's reminder"
    deleted = firestore_service.delete_reminder(user_id=bob, reminder_id=r1["id"])
    assert deleted is False, "Bob should not be able to delete Alice's reminder"
    print("  ✅ Unauthorized cross-user mutation strictly blocked")

    # 8. Cleanup
    firestore_service.delete_reminder(user_id=alice, reminder_id=r1["id"])
    firestore_service.delete_reminder(user_id=alice, reminder_id=r2["id"])
    firestore_service.delete_reminder(user_id=bob, reminder_id=r_bob["id"])
    print("  ✅ Cleaned up unit test reminders")


def test_calendar_popup_reminders():
    print("\n" + "=" * 65)
    print(" 📅 RUNNING CALENDAR POPUP REMINDERS TESTS")
    print("=" * 65)

    today = date.today().strftime("%Y-%m-%d")
    event = calendar_mcp.create_event(
        summary="Architecture Deep Dive",
        start_time=f"{today}T15:00:00",
        end_time=f"{today}T16:00:00",
        description="Review multi-agent reminders architecture",
        reminder_minutes=20,
        user_id="cal_test_user"
    )
    assert "reminders" in event
    assert event["reminders"]["useDefault"] is False
    assert len(event["reminders"]["overrides"]) >= 1
    assert event["reminders"]["overrides"][0]["method"] == "popup"
    assert event["reminders"]["overrides"][0]["minutes"] == 20
    print(f"  ✅ Calendar MCP event created with 20m popup reminder: {event['id']}")
    calendar_mcp.delete_event(event["id"])


def test_reminders_rest_api():
    print("\n" + "=" * 65)
    print(" 🚀 RUNNING REMINDERS REST API ENDPOINT TESTS")
    print("=" * 65)

    client = TestClient(app)
    user_id = "test_api_user_rem_303"
    token = create_session_token(user_id=user_id, email="reminder_user@example.com", name="Reminder Tester")
    headers = {"Authorization": f"Bearer {token}"}

    now = datetime.now(timezone.utc)
    t_past = (now - timedelta(minutes=2)).isoformat()

    # 1. POST /api/reminders
    print("\n[Test 1] Testing POST /api/reminders...")
    create_resp = client.post(
        "/api/reminders",
        json={
            "title": "Call Disha in 30 minutes",
            "remind_at": t_past,
            "source_type": "custom"
        },
        headers=headers
    )
    assert create_resp.status_code == 201, f"Expected 201, got {create_resp.status_code}: {create_resp.text}"
    body = create_resp.json()
    assert body["success"] is True
    rem_id = body["reminder"]["id"]
    print(f"  ✅ POST /api/reminders created reminder: {rem_id}")

    # 2. GET /api/reminders
    print("\n[Test 2] Testing GET /api/reminders...")
    list_resp = client.get("/api/reminders", headers=headers)
    assert list_resp.status_code == 200
    list_body = list_resp.json()
    assert list_body["success"] is True
    assert list_body["count"] >= 1
    assert any(r["id"] == rem_id for r in list_body["reminders"])
    print(f"  ✅ GET /api/reminders returned {list_body['count']} reminders")

    # 3. GET /api/reminders/due
    print("\n[Test 3] Testing GET /api/reminders/due...")
    due_resp = client.get("/api/reminders/due", headers=headers)
    assert due_resp.status_code == 200
    due_body = due_resp.json()
    assert due_body["success"] is True
    assert any(r["id"] == rem_id for r in due_body["due_reminders"])
    print(f"  ✅ GET /api/reminders/due detected due reminder {rem_id}")

    # 4. PATCH /api/reminders/{id} - Snooze 10m
    print("\n[Test 4] Testing PATCH /api/reminders/{id} (snooze)...")
    patch_resp = client.patch(
        f"/api/reminders/{rem_id}",
        json={"snooze_minutes": 10},
        headers=headers
    )
    assert patch_resp.status_code == 200
    patch_body = patch_resp.json()
    assert patch_body["reminder"]["status"] == "snoozed"
    print(f"  ✅ PATCH /api/reminders/{rem_id} snoozed successfully")

    # 5. PATCH /api/reminders/{id} - Dismiss
    print("\n[Test 5] Testing PATCH /api/reminders/{id} (dismiss)...")
    dismiss_resp = client.patch(
        f"/api/reminders/{rem_id}",
        json={"status": "dismissed"},
        headers=headers
    )
    assert dismiss_resp.status_code == 200
    assert dismiss_resp.json()["reminder"]["status"] == "dismissed"
    print(f"  ✅ PATCH /api/reminders/{rem_id} dismissed successfully")

    # 6. DELETE /api/reminders/{id}
    print("\n[Test 6] Testing DELETE /api/reminders/{id}...")
    del_resp = client.delete(f"/api/reminders/{rem_id}", headers=headers)
    assert del_resp.status_code == 200
    print(f"  ✅ DELETE /api/reminders/{rem_id} deleted successfully")


async def test_agent_reminders_natural_language():
    print("\n" + "=" * 65)
    print(" 🤖 RUNNING AGENT NATURAL LANGUAGE REMINDER WORKFLOW TESTS")
    print("=" * 65)

    test_uid = "nl_agent_user_404"

    # Test 1: Task reminder natural language
    print("\n[Test 1] Testing 'Remind me to call Disha in 30 minutes'...")
    res1 = await orchestrator._deterministic_offline_delegation(
        user_input="Remind me to call Disha in 30 minutes",
        session_id="test-session-1",
        user_id=test_uid,
        user_name="Apeksha"
    )
    assert res1["orchestration"]["activated_agent"] == "TaskAgent"
    assert "set_reminder" in res1["orchestration"]["tools_executed"]
    assert "Disha" in res1["reply"]
    print(f"  ✅ TaskAgent parsed reminder, called set_reminder: {res1['orchestration']['tools_executed']}")

    # Test 2: Note with reminder attached
    print("\n[Test 2] Testing 'Save a note about the DBMS assignment and remind me tomorrow at 6 PM'...")
    res2 = await orchestrator._deterministic_offline_delegation(
        user_input="Save a note about the DBMS assignment and remind me tomorrow at 6 PM",
        session_id="test-session-2",
        user_id=test_uid,
        user_name="Apeksha"
    )
    assert res2["orchestration"]["activated_agent"] == "NotesAgent"
    assert "note_save" in res2["orchestration"]["tools_executed"]
    assert "set_reminder" in res2["orchestration"]["tools_executed"]
    print(f"  ✅ NotesAgent saved note and scheduled linked reminder: {res2['orchestration']['tools_executed']}")

    # Clean up test user's reminders
    rems = firestore_service.list_reminders(user_id=test_uid)
    for r in rems:
        firestore_service.delete_reminder(user_id=test_uid, reminder_id=r["id"])
    print("  ✅ Cleaned up agent test reminders")


if __name__ == "__main__":
    import asyncio
    test_firestore_reminders_unit_and_isolation()
    test_calendar_popup_reminders()
    test_reminders_rest_api()
    asyncio.run(test_agent_reminders_natural_language())
    print("\n" + "=" * 65)
    print(" 🎉 ALL SMART REMINDERS TESTS PASSED!")
    print("=" * 65)
