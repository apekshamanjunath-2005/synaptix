"""
Test Suite: Persistent Multi-Session Chat History & Sliding Window Context
Validates Firestore sessions data model, subcollection messages,
FastAPI REST endpoints (/sessions, /sessions/{id}/messages, DELETE /sessions/{id}),
and multi-user security isolation.
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient

# Enforce MOCK_MODE for ₹0 safe local testing
os.environ["MOCK_MODE"] = "true"

from app.main import app
from app.database.firestore import firestore_service
from app.api.auth import get_current_user


class TestSessionsMultiHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        self.user_a = "test_user_alice"
        self.user_b = "test_user_bob"

    def test_01_firestore_session_crud(self):
        """Test Firestore sessions model, subcollection messages, and title truncation."""
        long_title = "Please help me organize my entire research paper schedule for the final semester submission"
        session = firestore_service.create_or_get_session(
            user_id=self.user_a,
            session_id=None,
            title=long_title
        )

        self.assertIsNotNone(session.get("session_id"))
        sid = session["session_id"]
        # Title should be truncated to ~40 chars
        self.assertTrue(len(session["title"]) <= 44)
        self.assertTrue(session["title"].endswith("..."))
        self.assertEqual(session["user_id"], self.user_a)

        # Add user message
        msg1 = firestore_service.add_message_to_session(
            session_id=sid,
            role="user",
            content="Can you summarize chapter 1?",
            user_id=self.user_a
        )
        self.assertEqual(msg1["role"], "user")
        self.assertEqual(msg1["session_id"], sid)

        # Add assistant message
        msg2 = firestore_service.add_message_to_session(
            session_id=sid,
            role="assistant",
            content="Chapter 1 introduces neural architectures.",
            user_id=self.user_a
        )
        self.assertEqual(msg2["role"], "assistant")

        # Load messages
        messages = firestore_service.get_session_messages(session_id=sid, user_id=self.user_a)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["content"], "Can you summarize chapter 1?")
        self.assertEqual(messages[1]["content"], "Chapter 1 introduces neural architectures.")

        # Test deletion
        deleted = firestore_service.delete_session(session_id=sid, user_id=self.user_a)
        self.assertTrue(deleted)
        self.assertIsNone(firestore_service.get_session(session_id=sid, user_id=self.user_a))
        self.assertEqual(firestore_service.get_session_messages(session_id=sid, user_id=self.user_a), [])

    def test_02_sliding_window_limit(self):
        """Test that get_session_messages honors the sliding window limit (last 10)."""
        sid = f"sess-sliding-{uuid.uuid4().hex[:6]}"
        firestore_service.create_or_get_session(user_id=self.user_a, session_id=sid, title="Sliding Test")

        # Insert 15 messages
        for i in range(15):
            role = "user" if i % 2 == 0 else "assistant"
            firestore_service.add_message_to_session(
                session_id=sid,
                role=role,
                content=f"Turn message #{i+1}",
                user_id=self.user_a
            )

        # Fetch with limit=10
        recent = firestore_service.get_session_messages(session_id=sid, limit=10, user_id=self.user_a)
        self.assertEqual(len(recent), 10)
        self.assertEqual(recent[0]["content"], "Turn message #6")
        self.assertEqual(recent[-1]["content"], "Turn message #15")

        firestore_service.delete_session(session_id=sid, user_id=self.user_a)

    def test_03_multi_user_isolation(self):
        """Verify strict multi-user isolation: User B cannot access or delete User A's sessions."""
        sid_a = f"sess-alice-{uuid.uuid4().hex[:6]}"
        firestore_service.create_or_get_session(user_id=self.user_a, session_id=sid_a, title="Alice Secret")
        firestore_service.add_message_to_session(
            session_id=sid_a,
            role="user",
            content="Alice private notes",
            user_id=self.user_a
        )

        # User B cannot get session or messages
        self.assertIsNone(firestore_service.get_session(session_id=sid_a, user_id=self.user_b))
        self.assertEqual(firestore_service.get_session_messages(session_id=sid_a, user_id=self.user_b), [])

        # User B cannot delete User A's session
        del_attempt = firestore_service.delete_session(session_id=sid_a, user_id=self.user_b)
        self.assertFalse(del_attempt)

        # Alice's session remains intact
        alice_session = firestore_service.get_session(session_id=sid_a, user_id=self.user_a)
        self.assertIsNotNone(alice_session)

        firestore_service.delete_session(session_id=sid_a, user_id=self.user_a)

    def test_04_api_chat_flow_and_sessions_endpoints(self):
        """Test full chat turn creates session, persists turns, and supports REST session management."""
        mock_auth = {"user_id": "user_api_tester", "email": "tester@synaptix.ai", "name": "API Tester"}
        app.dependency_overrides[get_current_user] = lambda: mock_auth

        try:
            # 1. Send first message without session_id
            resp1 = self.client.post("/api/chat", json={"message": "Add task: prepare slides"})
            self.assertEqual(resp1.status_code, 200)
            data1 = resp1.json()
            sid = data1.get("session_id")
            self.assertIsNotNone(sid)
            self.assertTrue(len(sid) > 0)

            # 2. Send follow-up message using returned session_id
            resp2 = self.client.post("/api/chat", json={
                "message": "Add task: review code",
                "session_id": sid
            })
            self.assertEqual(resp2.status_code, 200)
            data2 = resp2.json()
            self.assertEqual(data2.get("session_id"), sid)

            # 3. GET /sessions (and GET /api/sessions)
            resp_list = self.client.get("/api/sessions")
            self.assertEqual(resp_list.status_code, 200)
            sessions_list = resp_list.json().get("sessions", [])
            matching = [s for s in sessions_list if s["session_id"] == sid]
            self.assertEqual(len(matching), 1)

            # 4. GET /sessions/{session_id}/messages
            resp_msgs = self.client.get(f"/api/sessions/{sid}/messages")
            self.assertEqual(resp_msgs.status_code, 200)
            messages = resp_msgs.json().get("messages", [])
            self.assertGreaterEqual(len(messages), 4)  # 2 user msgs + 2 assistant msgs
            self.assertEqual(messages[0]["role"], "user")
            self.assertEqual(messages[0]["content"], "Add task: prepare slides")

            # 5. DELETE /sessions/{session_id}
            del_resp = self.client.delete(f"/api/sessions/{sid}")
            self.assertEqual(del_resp.status_code, 200)

            # 6. Verify session is gone
            get_again = self.client.get(f"/api/sessions/{sid}/messages")
            self.assertEqual(get_again.status_code, 404)

        finally:
            app.dependency_overrides.pop(get_current_user, None)


if __name__ == "__main__":
    unittest.main()
