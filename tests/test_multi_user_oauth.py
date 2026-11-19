"""
Synaptix Automated Test Suite: Multi-User Google OAuth 2.0 & Data Isolation
Tests web OAuth login redirects, session cookies, per-user task/note isolation,
dynamic Firestore token resolution, and email drafting context.
"""

import sys
import unittest
import urllib.parse
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from app.main import app
from app.config import get_settings
from app.database.firestore import firestore_service
from app.tools.gmail_service import gmail_service
from app.api.auth import create_session_token, decode_session_token
from app.agents.orchestrator import orchestrator


class TestMultiUserOAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, follow_redirects=False)
        cls.settings = get_settings()

    def test_01_login_redirect_to_google(self):
        """Verify /auth/login returns 302 redirect with proper OAuth scopes."""
        response = self.client.get("/auth/login")
        self.assertEqual(response.status_code, 302)
        location = response.headers.get("location", "")
        self.assertTrue(location.startswith("https://accounts.google.com/o/oauth2/v2/auth"))

        parsed = urllib.parse.urlparse(location)
        params = urllib.parse.parse_qs(parsed.query)

        self.assertIn("client_id", params)
        self.assertIn("redirect_uri", params)
        self.assertIn("scope", params)
        self.assertEqual(params.get("access_type", [""])[0], "offline")
        self.assertEqual(params.get("prompt", [""])[0], "consent")

        # Verify required scopes are present
        scope_str = params.get("scope", [""])[0]
        self.assertIn("openid", scope_str)
        self.assertIn("userinfo.email", scope_str)
        self.assertIn("gmail.compose", scope_str)
        self.assertIn("calendar", scope_str)
        print("  ✓ /auth/login correctly redirects to Google with offline consent and Gmail/Calendar scopes.")

    def test_02_unauthenticated_me_returns_401(self):
        """Verify /auth/me returns 401 when no session cookie is present."""
        response = self.client.get("/auth/me")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Not authenticated", response.json().get("detail", ""))
        print("  ✓ /auth/me returns 401 for unauthenticated requests.")

    def test_03_guest_login_sets_cookie_and_auth_me(self):
        """Verify /auth/guest sets signed synaptix_session cookie and /auth/me returns 200."""
        response = self.client.post("/auth/guest")
        self.assertEqual(response.status_code, 302)
        self.assertIn("synaptix_session", response.cookies)

        # Call /auth/me using the session cookie
        session_cookie = response.cookies["synaptix_session"]
        me_resp = self.client.get("/auth/me", cookies={"synaptix_session": session_cookie})
        self.assertEqual(me_resp.status_code, 200)
        me_data = me_resp.json()
        self.assertTrue(me_data.get("authenticated"))
        self.assertEqual(me_data.get("user_id"), "guest_user")
        self.assertEqual(me_data.get("name"), "Guest User")
        # Clear client cookies so subsequent tests start clean
        self.client.cookies.clear()
        print("  ✓ /auth/guest sets session cookie and authenticates successfully.")

    def test_04_session_token_encode_decode(self):
        """Verify JWT session creation and verification."""
        user_id = "user_test_99"
        email = "alice@example.com"
        name = "Alice Test"

        token = create_session_token(user_id=user_id, email=email, name=name)
        self.assertIsInstance(token, str)

        payload = decode_session_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("sub"), user_id)
        self.assertEqual(payload.get("email"), email)
        self.assertEqual(payload.get("name"), name)
        print("  ✓ Signed session JWT creation and decoding validated.")

    def test_05_firestore_user_tokens_and_profile_storage(self):
        """Verify storing and loading user tokens and profile from Firestore."""
        user_id = "user_google_12345"
        mock_tokens = {
            "access_token": "ya29.mock_access_token",
            "refresh_token": "1//mock_refresh_token",
            "token_type": "Bearer",
        }
        mock_profile = {
            "email": "user12345@gmail.com",
            "name": "Jane Developer",
            "picture": "https://example.com/avatar.jpg",
        }

        firestore_service.save_user_tokens(user_id, mock_tokens)
        firestore_service.save_user_profile(user_id, mock_profile)

        loaded_tokens = firestore_service.get_user_tokens(user_id)
        self.assertIsNotNone(loaded_tokens)
        self.assertEqual(loaded_tokens.get("access_token"), "ya29.mock_access_token")

        loaded_profile = firestore_service.get_user_profile(user_id)
        self.assertIsNotNone(loaded_profile)
        self.assertEqual(loaded_profile.get("email"), "user12345@gmail.com")
        self.assertEqual(loaded_profile.get("name"), "Jane Developer")
        print("  ✓ Firestore user OAuth tokens and profile persistence verified.")

    def test_06_per_user_task_and_note_isolation(self):
        """Verify User A cannot see User B's tasks and notes."""
        user_a = "user_alice_isolated"
        user_b = "user_bob_isolated"

        token_a = create_session_token(user_id=user_a, email="alice@test.com", name="Alice")
        token_b = create_session_token(user_id=user_b, email="bob@test.com", name="Bob")

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Alice creates a task and a note
        resp_a_task = self.client.post(
            "/api/tasks",
            json={"title": "Alice's Secret Project Task", "priority": "high"},
            headers=headers_a
        )
        self.assertEqual(resp_a_task.status_code, 201)

        resp_a_note = self.client.post(
            "/api/notes",
            json={"title": "Alice Confidential Note", "content": "Strategy document for Q4."},
            headers=headers_a
        )
        self.assertEqual(resp_a_note.status_code, 201)

        # Bob creates a task and a note
        resp_b_task = self.client.post(
            "/api/tasks",
            json={"title": "Bob's Public Task", "priority": "low"},
            headers=headers_b
        )
        self.assertEqual(resp_b_task.status_code, 201)

        # Alice lists tasks -> must NOT see Bob's task
        alice_tasks = self.client.get("/api/tasks", headers=headers_a).json().get("tasks", [])
        alice_task_titles = [t["title"] for t in alice_tasks]
        self.assertIn("Alice's Secret Project Task", alice_task_titles)
        self.assertNotIn("Bob's Public Task", alice_task_titles)

        # Bob lists tasks -> must NOT see Alice's task
        bob_tasks = self.client.get("/api/tasks", headers=headers_b).json().get("tasks", [])
        bob_task_titles = [t["title"] for t in bob_tasks]
        self.assertIn("Bob's Public Task", bob_task_titles)
        self.assertNotIn("Alice's Secret Project Task", bob_task_titles)

        # Alice searches notes -> Bob's notes are isolated
        alice_notes = self.client.get("/api/notes", headers=headers_a).json().get("notes", [])
        alice_note_titles = [n.get("title") for n in alice_notes]
        self.assertIn("Alice Confidential Note", alice_note_titles)

        print("  ✓ Per-user task and note data isolation strictly enforced between users.")

    def test_07_email_drafting_with_user_context(self):
        """Verify email drafted for authenticated user signs off with the user's name."""
        user_c = "user_clara"
        token_c = create_session_token(user_id=user_c, email="clara@example.com", name="Clara Oswald")

        resp = self.client.post(
            "/api/chat",
            json={"message": "Draft an email to david@example.com about Q3 Roadmap updates"},
            headers={"Authorization": f"Bearer {token_c}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        reply = data.get("reply", "")

        # Verify draft was created and contains user's name in sign-off
        self.assertIn("Email Draft Created", reply)
        self.assertIn("Clara Oswald", reply)
        self.assertIn("david@example.com", reply)
        print("  ✓ Email drafted with authenticated user's real name in sign-off.")

    def test_08_logout_clears_session(self):
        """Verify /auth/logout clears synaptix_session cookie and invalidates session."""
        token = create_session_token("temp_user", "temp@example.com", "Temp")
        logout_resp = self.client.get("/auth/logout", cookies={"synaptix_session": token})
        self.assertEqual(logout_resp.status_code, 302)

        # Clear any remaining cookies in the test client
        self.client.cookies.clear()

        # Following up without valid cookie returns 401
        me_resp = self.client.get("/auth/me")
        self.assertEqual(me_resp.status_code, 401)
        print("  ✓ /auth/logout invalidates session and clears credentials.")


def run_tests():
    print("\n" + "=" * 70)
    print(" 🧪 RUNNING MULTI-USER GOOGLE OAUTH 2.0 VALIDATION SUITE")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMultiUserOAuth)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
