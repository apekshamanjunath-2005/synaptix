"""
Milestone 8: UI and User Experience Verification Test Suite
Verifies:
1. Static asset delivery (index.html, styles.css, app.js) via live HTTP
2. Comprehensive UI section coverage (Chat, Tasks, Notes, Calendar, Planner, Telemetry)
3. Agent status chips and execution indicators in HTML/CSS
4. Toast notification system, Clear Chat, and Copy Plan components
5. Responsive glassmorphism stylesheet validity
"""

import sys
import json
import logging
import threading
import time
import urllib.request
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from app.main import app

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("test_milestone8")

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8005
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"


def fetch_url(path: str) -> tuple[int, str]:
    req = urllib.request.Request(f"{BASE_URL}{path}")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, content
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def test_milestone8_ui():
    print("\n" + "=" * 65)
    print(" 🎨 RUNNING MILESTONE 8: UI AND USER EXPERIENCE VERIFICATION")
    print("=" * 65)

    config = uvicorn.Config(app=app, host=SERVER_HOST, port=SERVER_PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.5)

    try:
        # [Test 1] Serve Index HTML
        print("\n[Test 1] Testing Root Index HTML Delivery...")
        code, html = fetch_url("/")
        assert code == 200, f"Expected 200, got {code}"
        assert "<!DOCTYPE html>" in html
        assert "Synaptix" in html
        print(f"  ✅ Root '/' served successfully ({len(html)} bytes)")

        # [Test 2] Verify All 6 Functional UI Sections in HTML
        print("\n[Test 2] Verifying All 6 Core Functional Tabs in Dashboard...")
        required_panes = [
            ("tab-chat", "AI Chat Interface"),
            ("tab-tasks", "Tasks Management View"),
            ("tab-notes", "Stored Notes & Search View"),
            ("tab-calendar", "Google Calendar & MCP Conflict Checker"),
            ("tab-gmail", "Gmail Drafts & Human-in-the-Loop Queue"),
            ("tab-planner", "Smart Day Planner & Weather Outlook"),
            ("tab-telemetry", "Budget Safeguards & Telemetry"),
        ]
        for pane_id, label in required_panes:
            assert f'id="{pane_id}"' in html, f"Missing tab pane '{pane_id}' for {label}"
            print(f"  ✅ Tab pane verified: {pane_id} ({label})")

        # [Test 3] Verify Agent Status Chips and Interactive Elements
        print("\n[Test 3] Verifying Multi-Agent Execution Indicators...")
        assert "agent-roster" in html
        assert "Coordinator" in html
        assert "Tasks" in html
        assert "Notes" in html
        assert "Calendar" in html
        assert "Gmail" in html
        assert "Planner" in html
        print("  ✅ All 5 agent roster chips present in top header")

        # [Test 4] Verify Stylesheet and Responsive Glassmorphism Styling
        print("\n[Test 4] Testing styles.css Delivery and Modern CSS Tokens...")
        code_css, css = fetch_url("/static/css/styles.css")
        assert code_css == 200
        assert "--accent-primary" in css
        assert ".toast-container" in css
        assert "@keyframes toastSlideIn" in css
        print(f"  ✅ styles.css delivered with toast animations ({len(css)} bytes)")

        # [Test 5] Verify JavaScript Application Logic and Helpers
        print("\n[Test 5] Testing app.js Delivery and UI Controller Logic...")
        code_js, js = fetch_url("/static/js/app.js")
        assert code_js == 200
        assert "showToast" in js
        assert "loadTimetable" in js
        assert "loadWeather" in js
        assert "loadDrafts" in js
        assert "clearChatBtn" in js
        assert "copyPlanBtn" in js
        print(f"  ✅ app.js verified with toast notifications and clipboard export ({len(js)} bytes)")

    finally:
        server.should_exit = True
        time.sleep(0.5)

    print("\n" + "=" * 65)
    print(" 🎉 ALL MILESTONE 8 UI AND USER EXPERIENCE TESTS PASSED!")
    print("=" * 65)


if __name__ == "__main__":
    test_milestone8_ui()
