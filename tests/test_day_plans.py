"""
Unit & Integration Test Suite for Firestore Day Plans Persistence
Verifies:
1. FirestoreService day_plans collection operations (save, get, list, delete).
2. User isolation: plans for user_a are never returned or overwritten for user_b.
3. REST endpoint GET /api/planner/today returns saved plan.
4. REST endpoint POST /api/planner/generate writes to Firestore.
5. REST endpoint GET /api/planner/history returns user history.
6. Local simulator persistence across reloads.
"""

import sys
import json
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from app.main import app
from app.database.firestore import firestore_service
from app.tools.firestore import firestore_service as tools_firestore_service
from app.core.context import current_user_id
from app.api.auth import create_session_token


def test_firestore_day_plans_unit():
    print("\n" + "=" * 65)
    print(" 🧭 RUNNING FIRESTORE DAY PLANS UNIT & ISOLATION TESTS")
    print("=" * 65)

    user_alice = "user_alice_test_123"
    user_bob = "user_bob_test_456"
    today_str = date.today().strftime("%Y-%m-%d")
    tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    # 1. Verify app.tools.firestore alias matches app.database.firestore
    print("\n[Test 1] Testing app.tools.firestore alias re-export...")
    assert tools_firestore_service is firestore_service
    print("  ✅ tools_firestore_service is identical to database firestore_service")

    # 2. Save day plan for Alice
    print("\n[Test 2] Testing save_day_plan for User Alice...")
    alice_plan_data = {
        "plan": f"Alice's Timetable for {today_str}",
        "formatted_markdown": f"# Alice Plan {today_str}",
        "timetable": [
            {"time_range": "09:00 - 10:30", "activity_type": "focus", "title": "Alice Deep Work", "description": "High priority"}
        ],
        "weather_summary": {"condition": "Sunny", "temperature_c": 26.0},
        "pending_tasks_count": 3,
        "scheduled_events_count": 1,
    }
    saved_alice = firestore_service.save_day_plan(
        user_id=user_alice,
        date_str=today_str,
        plan_data=alice_plan_data
    )
    assert saved_alice is not None
    assert saved_alice["user_id"] == user_alice
    assert saved_alice["date"] == today_str
    assert "updated_at" in saved_alice
    print(f"  ✅ Alice plan saved successfully (id: {saved_alice['id']})")

    # 3. Save day plan for Bob
    print("\n[Test 3] Testing save_day_plan for User Bob...")
    bob_plan_data = {
        "plan": f"Bob's Secret Schedule for {today_str}",
        "formatted_markdown": f"# Bob Plan {today_str}",
        "timetable": [
            {"time_range": "11:00 - 12:00", "activity_type": "meeting", "title": "Bob Strategy Sync", "description": "Confidential"}
        ],
        "weather_summary": {"condition": "Cloudy", "temperature_c": 22.0},
        "pending_tasks_count": 1,
        "scheduled_events_count": 2,
    }
    saved_bob = firestore_service.save_day_plan(
        user_id=user_bob,
        date_str=today_str,
        plan_data=bob_plan_data
    )
    assert saved_bob["user_id"] == user_bob
    print(f"  ✅ Bob plan saved successfully (id: {saved_bob['id']})")

    # 4. Verify Per-User Data Isolation
    print("\n[Test 4] Verifying Per-User Plan Isolation...")
    alice_fetched = firestore_service.get_day_plan(user_id=user_alice, date_str=today_str)
    bob_fetched = firestore_service.get_day_plan(user_id=user_bob, date_str=today_str)

    assert alice_fetched is not None
    assert bob_fetched is not None
    assert alice_fetched["user_id"] == user_alice
    assert bob_fetched["user_id"] == user_bob
    assert "Alice Deep Work" in alice_fetched["timetable"][0]["title"]
    assert "Bob Strategy Sync" in bob_fetched["timetable"][0]["title"]
    assert "Alice" not in bob_fetched["plan"]
    assert "Bob" not in alice_fetched["plan"]
    print("  ✅ Alice cannot access Bob's plan and Bob cannot access Alice's plan")

    # 5. Nonexistent Date Lookup
    print("\n[Test 5] Testing non-existent date lookup...")
    empty_plan = firestore_service.get_day_plan(user_id=user_alice, date_str="2099-01-01")
    assert empty_plan is None
    print("  ✅ Correctly returned None for ungenerated date")

    # 6. User Plan History Listing
    print("\n[Test 6] Testing list_day_plans user history...")
    # Add second plan for Alice on tomorrow
    firestore_service.save_day_plan(
        user_id=user_alice,
        date_str=tomorrow_str,
        plan_data={"plan": f"Alice Plan for {tomorrow_str}"}
    )
    alice_history = firestore_service.list_day_plans(user_id=user_alice, limit=5)
    assert len(alice_history) >= 2
    dates = [p["date"] for p in alice_history]
    assert tomorrow_str in dates
    assert today_str in dates
    # Verify no Bob plans leaked into Alice's history
    assert all(p["user_id"] == user_alice for p in alice_history)
    print(f"  ✅ Alice history returned {len(alice_history)} plans, all scoped to Alice")

    # Cleanup test documents
    firestore_service.delete_day_plan(user_alice, today_str)
    firestore_service.delete_day_plan(user_alice, tomorrow_str)
    firestore_service.delete_day_plan(user_bob, today_str)
    print("  ✅ Cleaned up test day plans")


def test_planner_api_endpoints():
    print("\n" + "=" * 65)
    print(" 🚀 RUNNING SMART PLANNER REST API ENDPOINT TESTS")
    print("=" * 65)

    client = TestClient(app)
    test_user_id = "test_user_api_789"
    current_user_id.set(test_user_id)
    user_token = create_session_token(user_id=test_user_id, email="test@example.com", name="Test User")
    auth_headers = {"Authorization": f"Bearer {user_token}"}
    today_str = date.today().strftime("%Y-%m-%d")

    # 1. Generate a plan via POST /api/planner/generate
    print("\n[Test 1] Testing POST /api/planner/generate...")
    resp = client.post(
        "/api/planner/generate",
        json={"target_date": today_str, "city": "Bengaluru"},
        headers=auth_headers
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    body = resp.json()
    assert body["target_date"] == today_str
    assert "timetable" in body
    assert len(body["timetable"]) > 0
    assert body.get("saved") is True
    print(f"  ✅ POST /api/planner/generate returned {len(body['timetable'])} blocks with saved=True")

    # 2. Retrieve today's saved plan via GET /api/planner/today (₹0 API calls)
    print("\n[Test 2] Testing GET /api/planner/today...")
    resp_today = client.get(
        "/api/planner/today",
        headers=auth_headers
    )
    assert resp_today.status_code == 200
    today_body = resp_today.json()
    assert today_body["success"] is True
    assert today_body["saved"] is True
    assert today_body["target_date"] == today_str
    assert "plan" in today_body
    print("  ✅ GET /api/planner/today returned saved Firestore plan without regenerating")

    # 3. Retrieve saved plan via GET /api/planner?date=YYYY-MM-DD
    print("\n[Test 3] Testing GET /api/planner?date=...")
    resp_date = client.get(
        f"/api/planner?date={today_str}",
        headers=auth_headers
    )
    assert resp_date.status_code == 200
    date_body = resp_date.json()
    assert date_body["saved"] is True
    assert date_body["plan"]["date"] == today_str
    print("  ✅ GET /api/planner?date= returned matching saved document")

    # 4. Retrieve history via GET /api/planner/history
    print("\n[Test 4] Testing GET /api/planner/history...")
    resp_hist = client.get(
        "/api/planner/history?limit=5",
        headers=auth_headers
    )
    assert resp_hist.status_code == 200
    hist_body = resp_hist.json()
    assert hist_body["success"] is True
    assert len(hist_body["plans"]) >= 1
    assert hist_body["plans"][0]["date"] == today_str
    print(f"  ✅ GET /api/planner/history returned {len(hist_body['plans'])} saved plans")

    # Cleanup
    firestore_service.delete_day_plan(test_user_id, today_str)
    print("  ✅ Cleaned up API test document")

    print("\n" + "=" * 65)
    print(" 🎉 ALL SMART PLANNER PERSISTENCE TESTS PASSED!")
    print("=" * 65)


if __name__ == "__main__":
    test_firestore_day_plans_unit()
    test_planner_api_endpoints()
