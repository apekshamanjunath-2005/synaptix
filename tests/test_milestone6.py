"""
Milestone 6: Weather Integration Verification Test Suite
Verifies:
1. Weather Tool Provider (live HTTP + graceful zero-cost fallback)
2. Outdoor activity suitability recommendation algorithm
3. ADK FunctionTool wrapper (get_current_weather) integration
4. REST endpoint GET /api/weather via live HTTP server
5. End-to-end multi-agent SmartDayPlannerAgent synthesis with weather via POST /api/chat
"""

import sys
import json
import logging
import threading
import time
import urllib.request
import urllib.parse
from datetime import date
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from app.tools.weather_tool import WeatherTool, weather_tool
from app.agents.tools import get_current_weather
from app.main import app

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("test_milestone6")

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8003
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


def test_milestone6_weather():
    print("\n" + "=" * 65)
    print(" 🌤️  RUNNING MILESTONE 6: WEATHER INTEGRATION VERIFICATION")
    print("=" * 65)

    # ─────────────────────────────────────────────────────────────
    # [Test 1] Weather Tool Provider Unit Tests
    # ─────────────────────────────────────────────────────────────
    print("\n[Test 1] Testing Weather Tool Provider & Zero-Cost Engine...")
    wt = WeatherTool(api_key=None, default_city="Bengaluru")
    w_sync = wt.get_weather_sync("Bengaluru")
    
    assert "city" in w_sync, "City missing in weather response"
    assert "condition" in w_sync, "Condition missing in weather response"
    assert "temperature_c" in w_sync, "Temperature missing in weather response"
    assert "feels_like_c" in w_sync, "Feels-like missing in weather response"
    assert "suitable_for_outdoor" in w_sync, "Suitability flag missing"
    assert "activity_recommendation" in w_sync, "Recommendation missing"
    assert w_sync["live_api_active"] is False, "Fallback mode should be active when no key provided"
    print(f"  ✅ Fallback weather generated: {w_sync['city']} — {w_sync['condition']}, {w_sync['temperature_c']}°C")
    print(f"  ✅ Outdoor suitability: {w_sync['suitable_for_outdoor']} ({w_sync['activity_recommendation'][:60]}...)")

    # ─────────────────────────────────────────────────────────────
    # [Test 2] Testing Outdoor Suitability Heuristics
    # ─────────────────────────────────────────────────────────────
    print("\n[Test 2] Testing Outdoor Suitability Decision Logic...")
    suitable_rain, advice_rain = wt._assess_outdoor_suitability("Heavy Rain", 22.0, 15.0)
    assert suitable_rain is False, "Rain should flag outdoor as unsuitable"
    assert "indoor" in advice_rain.lower() or "rain" in advice_rain.lower()
    print("  ✅ Rain check accurately recommends indoor focus")

    suitable_heat, advice_heat = wt._assess_outdoor_suitability("Clear Sky", 41.0, 10.0)
    assert suitable_heat is False, "Extreme heat should flag outdoor as unsuitable"
    print("  ✅ Extreme heat (>38°C) accurately triggers indoor warning")

    suitable_fair, advice_fair = wt._assess_outdoor_suitability("Clear Sky", 24.0, 12.0)
    assert suitable_fair is True, "Mild clear weather should be favorable for outdoors"
    print("  ✅ Mild clear weather accurately marked favorable for outdoors")

    # ─────────────────────────────────────────────────────────────
    # [Test 3] Testing ADK FunctionTool Integration
    # ─────────────────────────────────────────────────────────────
    print("\n[Test 3] Testing ADK FunctionTool (get_current_weather)...")
    tool_output_str = get_current_weather(city="Bengaluru")
    tool_data = json.loads(tool_output_str)
    assert tool_data["city"] == "Bengaluru"
    assert "condition" in tool_data
    assert "temperature_c" in tool_data
    print(f"  ✅ ADK get_current_weather() returned valid JSON: {tool_data['condition']}, {tool_data['temperature_c']}°C")

    # ─────────────────────────────────────────────────────────────
    # [Test 4] Testing Weather REST Endpoints via Live HTTP Server
    # ─────────────────────────────────────────────────────────────
    print("\n[Test 4] Testing GET /api/weather REST Endpoint...")
    config = uvicorn.Config(app=app, host=SERVER_HOST, port=SERVER_PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.5)

    try:
        # Default city weather
        code, body = make_request(f"{BASE_URL}/api/weather")
        assert code == 200, f"Expected 200, got {code}"
        assert body["city"] == "Bengaluru"
        assert "suitable_for_outdoor" in body
        print(f"  ✅ GET /api/weather returned 200 OK for {body['city']}: {body['condition']}, {body['temperature_c']}°C")

        # Custom city query
        code_mumbai, body_mumbai = make_request(f"{BASE_URL}/api/weather?city=Mumbai")
        assert code_mumbai == 200, f"Expected 200, got {code_mumbai}"
        assert body_mumbai["city"] == "Mumbai"
        print(f"  ✅ GET /api/weather?city=Mumbai returned 200 OK: {body_mumbai['condition']}, {body_mumbai['temperature_c']}°C")

        # Verify integration status in /api/health
        code_h, body_h = make_request(f"{BASE_URL}/api/health")
        assert code_h == 200
        print(f"  ✅ GET /api/health reflects integrations: {body_h['integrations_status']}")

        # ─────────────────────────────────────────────────────────────
        # [Test 5] End-to-End Multi-Agent Synthesis (SmartDayPlannerAgent)
        # ─────────────────────────────────────────────────────────────
        print("\n[Test 5] Testing End-to-End: SmartDayPlannerAgent synthesizes plan with weather via /api/chat...")
        chat_code, chat_body = make_request(
            f"{BASE_URL}/api/chat",
            method="POST",
            payload={"message": "Plan my day today based on my pending tasks, calendar commitments, and the weather forecast."}
        )
        assert chat_code == 200, f"Expected 200 from /api/chat, got {chat_code}: {chat_body}"
        assert chat_body["orchestration"]["activated_agent"] == "SmartDayPlannerAgent", (
            f"Expected SmartDayPlannerAgent, got {chat_body['orchestration']['activated_agent']}"
        )
        tools_used = chat_body["orchestration"]["tools_executed"]
        assert "get_current_weather" in tools_used, f"Expected get_current_weather in tools_used, got {tools_used}"
        print(f"  ✅ SmartDayPlannerAgent activated! Tools invoked: {tools_used}")
        
        reply_text = chat_body["reply"]
        assert "WEATHER" in reply_text.upper() or "PLAN" in reply_text.upper()
        print(f"  ✅ Synthesized Plan Generated ({len(reply_text)} chars):")
        for line in reply_text.split("\n")[:8]:
            print(f"     {line}")
        print("     ...")

    finally:
        server.should_exit = True
        time.sleep(0.5)

    print("\n" + "=" * 65)
    print(" 🎉 ALL MILESTONE 6 WEATHER INTEGRATION TESTS PASSED!")
    print("=" * 65)


if __name__ == "__main__":
    test_milestone6_weather()
