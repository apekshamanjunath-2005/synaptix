"""
Milestone 2 — Gemini Integration Verification Tests
Tests GeminiService, 15 RPM sliding window rate limiter,
and the /api/chat conversational endpoint.
"""

import sys
import time
import json
import threading
import urllib.request
import urllib.error
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from app.main import app
from app.core.gemini_client import GeminiService, RateLimiterRPM, gemini_service
from app.core.usage_tracker import usage_tracker


class LiveTestServer(threading.Thread):
    def __init__(self, port=8890):
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
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            body = json.loads(body)
        except Exception:
            pass
        return e.code, body


def test_gemini_milestone2():
    print("=================================================================")
    print(" 🧪 RUNNING MILESTONE 2: GEMINI INTEGRATION TESTS")
    print("=================================================================")

    # 1. Test 15 RPM rate limiter logic
    print("\n[Test 1] Testing 15 RPM Sliding Window Rate Limiter...")
    limiter = RateLimiterRPM(max_rpm=3)  # Small bucket for unit testing
    assert limiter.check_and_record() is True
    assert limiter.check_and_record() is True
    assert limiter.check_and_record() is True
    # 4th request in the same minute should be blocked
    assert limiter.check_and_record() is False
    print("  ✅ RateLimiterRPM successfully blocked requests exceeding limit within 60s window")

    # 2. Test GeminiService fallback when unconfigured
    print("\n[Test 2] Testing GeminiService unconfigured guidance response...")
    unconfigured_svc = GeminiService()
    # Ensure unconfigured test
    unconfigured_svc._client = None
    import asyncio
    resp = asyncio.run(unconfigured_svc.generate_response(prompt="Hello Synaptix!"))
    assert resp["configured"] is False
    assert "Google AI Studio" in resp["reply"]
    print("  ✅ GeminiService returns user-friendly setup guide when key is not configured (₹0 safety)")

    # 3. Start Live Server and test /api/chat HTTP endpoint
    print("\n[Test 3] Testing /api/chat HTTP endpoint on live server...")
    server = LiveTestServer(port=8890)
    server.start()
    time.sleep(1.2)
    base_url = "http://127.0.0.1:8890"

    try:
        # Test 3a: Valid conversational request
        status, body = make_request(
            f"{base_url}/api/chat",
            payload={
                "message": "Hello, how can you help me be more productive?",
                "conversation_history": []
            }
        )
        assert status == 200, f"Expected 200, got {status}: {body}"
        assert "reply" in body
        assert body["model"] == "gemini-2.5-flash"
        print(f"  ✅ /api/chat returned 200 OK:")
        print(f"     Model: {body['model']}")
        print(f"     Configured: {body['configured']}")
        print(f"     Sample response preview: {body['reply'][:85]}...")

        # Test 3b: Multi-turn conversation history
        status_hist, body_hist = make_request(
            f"{base_url}/api/chat",
            payload={
                "message": "What is my goal again?",
                "conversation_history": [
                    {"role": "user", "content": "I want to finish my AI project by Friday."},
                    {"role": "model", "content": "I noted your goal to finish your AI project by Friday!"}
                ]
            }
        )
        assert status_hist == 200
        assert "reply" in body_hist
        print("  ✅ Multi-turn conversation history schema validated with 200 OK")

        # Test 3c: Input validation error (empty message -> 422 Unprocessable Entity)
        status_422, body_422 = make_request(
            f"{base_url}/api/chat",
            payload={"message": ""}
        )
        assert status_422 == 422, f"Expected 422 for empty message, got {status_422}"
        print(f"  ✅ Validation error (422) properly returned for invalid/empty input: {body_422['detail'][0]['msg']}")

        # Test 3d: Quota enforcement (HTTP 429) on /api/chat
        usage_tracker.total_llm_requests = 100
        usage_tracker._save_to_cache()

        status_429, body_429 = make_request(
            f"{base_url}/api/chat",
            payload={"message": "Will this request be blocked?"}
        )
        assert status_429 == 429, f"Expected 429 when quota is exhausted, got {status_429}"
        assert body_429["detail"]["error"] == "QuotaExceeded"
        print(f"  ✅ Daily ₹0 quota limit strictly enforced on /api/chat: HTTP {status_429}")

        # Reset counters
        usage_tracker.reset_counters_for_testing()

    finally:
        server.stop()

    print("\n=================================================================")
    print(" 🎉 ALL MILESTONE 2 GEMINI INTEGRATION TESTS PASSED!")
    print("=================================================================")


if __name__ == "__main__":
    test_gemini_milestone2()
