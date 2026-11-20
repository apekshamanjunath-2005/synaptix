"""
Unit and Integration Test Suite for User-Editable Timetable and Date-Aware Calendar
Verifies:
1. GET /api/timetable returns user's weekly timetable structure across all 7 days.
2. POST /api/timetable saves/updates time blocks for a specific day.
3. POST /api/timetable with apply_to_week=True replicates blocks across the full week.
4. POST /api/timetable with days=['monday', 'tuesday', ...] replicates to specified days.
5. DELETE /api/timetable/{day}/{block_id} removes a block and handles 404s gracefully.
6. Calendar month & date filtering via GET /api/calendar/events?month=... and ?date=...
7. Dual-mode resilience (Mock Mode + Live Mode compatible).
"""

import sys
import unittest
import uuid
from datetime import date
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app
from app.database.firestore import firestore_service
from app.tools.calendar_mcp import calendar_mcp
from app.api.auth import create_session_token


class TestTimetableAndCalendar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.user_id = f"test_tt_user_{uuid.uuid4().hex[:6]}"
        cls.token = create_session_token(user_id=cls.user_id, email="tt_tester@example.com", name="Timetable Tester")
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def test_01_get_default_timetable(self):
        """GET /api/timetable returns weekly schedule with all 7 days."""
        resp = self.client.get("/api/timetable", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        self.assertIn("days", data)
        days = data["days"]
        for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            self.assertIn(d, days)
            self.assertIsInstance(days[d], list)
            self.assertGreater(len(days[d]), 0)

    def test_02_get_timetable_with_day_filter(self):
        """GET /api/timetable?day=wednesday returns blocks for that specific day."""
        resp = self.client.get("/api/timetable?day=wednesday", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("selected_day"), "wednesday")
        self.assertIn("blocks", data)
        self.assertIsInstance(data["blocks"], list)

    def test_03_post_save_single_day_timetable(self):
        """POST /api/timetable updates blocks for a single day."""
        payload = {
            "day": "tuesday",
            "blocks": [
                {
                    "start_time": "08:00",
                    "end_time": "09:30",
                    "title": "Algorithms & Problem Solving",
                    "category": "focus"
                },
                {
                    "start_time": "12:00",
                    "end_time": "13:00",
                    "title": "Healthy Lunch",
                    "category": "break"
                }
            ],
            "apply_to_week": False
        }
        resp = self.client.post("/api/timetable", json=payload, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("saved_day"), "tuesday")

        # Verify Tuesday has exactly 2 blocks
        tue_blocks = data["days"]["tuesday"]
        self.assertEqual(len(tue_blocks), 2)
        self.assertEqual(tue_blocks[0]["title"], "Algorithms & Problem Solving")
        self.assertEqual(tue_blocks[0]["category"], "focus")
        self.assertTrue(tue_blocks[0]["id"].startswith("blk-"))

    def test_04_post_apply_to_entire_week(self):
        """POST /api/timetable with apply_to_week=True replicates blocks across all 7 days."""
        blocks = [
            {"start_time": "09:15", "end_time": "10:45", "title": "Morning Focus", "category": "focus"},
            {"start_time": "13:00", "end_time": "14:00", "title": "Lunch Break", "category": "break"},
            {"start_time": "16:00", "end_time": "17:00", "title": "Wrap-up", "category": "wrapup"}
        ]
        payload = {
            "day": "monday",
            "blocks": blocks,
            "apply_to_week": True
        }
        resp = self.client.post("/api/timetable", json=payload, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("applied_to_week"))

        days = data["days"]
        for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            self.assertEqual(len(days[d]), 3, f"Day {d} should have 3 blocks")
            self.assertEqual(days[d][0]["title"], "Morning Focus")
            self.assertEqual(days[d][1]["title"], "Lunch Break")
            self.assertEqual(days[d][2]["title"], "Wrap-up")

    def test_05_post_apply_to_target_weekdays(self):
        """POST /api/timetable with target_days replicates only to selected weekdays."""
        blocks = [
            {"start_time": "10:00", "end_time": "11:30", "title": "Mid-morning Sync", "category": "meeting"}
        ]
        payload = {
            "day": "monday",
            "blocks": blocks,
            "apply_to_week": False,
            "days": ["monday", "wednesday", "friday"]
        }
        resp = self.client.post("/api/timetable", json=payload, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        days = data["days"]
        self.assertEqual(len(days["monday"]), 1)
        self.assertEqual(len(days["wednesday"]), 1)
        self.assertEqual(len(days["friday"]), 1)
        self.assertEqual(days["monday"][0]["title"], "Mid-morning Sync")

    def test_06_delete_timetable_block(self):
        """DELETE /api/timetable/{day}/{block_id} removes a block."""
        # 1. First add a block to Friday
        add_payload = {
            "day": "friday",
            "blocks": [
                {"id": "blk-test-del", "start_time": "15:00", "end_time": "16:00", "title": "Code Review", "category": "focus"}
            ]
        }
        self.client.post("/api/timetable", json=add_payload, headers=self.headers)

        # 2. Delete it
        del_resp = self.client.delete("/api/timetable/friday/blk-test-del", headers=self.headers)
        self.assertEqual(del_resp.status_code, 200)
        del_data = del_resp.json()
        self.assertTrue(del_data.get("success"))

        # 3. Verify it is gone
        get_resp = self.client.get("/api/timetable?day=friday", headers=self.headers)
        blocks = get_resp.json().get("blocks", [])
        self.assertFalse(any(b.get("id") == "blk-test-del" for b in blocks))

        # 4. Deleting non-existent block returns 404
        bad_del = self.client.delete("/api/timetable/friday/non-existent-id-999", headers=self.headers)
        self.assertEqual(bad_del.status_code, 404)

    def test_07_calendar_month_and_date_filtering(self):
        """Calendar MCP events endpoint supports date and month filtering."""
        today_str = date.today().strftime("%Y-%m-%d")
        current_month = today_str[:7]

        # 1. Create a test event for today
        ev = calendar_mcp.create_event(
            summary="Interactive Grid Review Meeting",
            start_time=f"{today_str}T14:30:00",
            end_time=f"{today_str}T15:30:00",
            description="Testing interactive calendar grid"
        )
        self.assertIsNotNone(ev.get("id"))

        # 2. Query by specific date
        date_resp = self.client.get(f"/api/calendar/events?date={today_str}", headers=self.headers)
        self.assertEqual(date_resp.status_code, 200)
        date_data = date_resp.json()
        self.assertGreater(date_data.get("count", 0), 0)
        self.assertTrue(any(e["summary"] == "Interactive Grid Review Meeting" for e in date_data.get("events", [])))

        # 3. Query by month
        month_resp = self.client.get(f"/api/calendar/events?month={current_month}", headers=self.headers)
        self.assertEqual(month_resp.status_code, 200)
        month_data = month_resp.json()
        self.assertGreater(month_data.get("count", 0), 0)
        self.assertTrue(any(e["summary"] == "Interactive Grid Review Meeting" for e in month_data.get("events", [])))

        # Clean up
        calendar_mcp.delete_event(ev["id"])


if __name__ == "__main__":
    unittest.main()
