"""
Milestone 1 — Foundation Verification Tests
Tests health endpoint, static file serving, configuration loading, and usage tracker.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from app.main import app
from app.config import get_settings
from app.core.usage_tracker import usage_tracker


def test_settings_loading():
    """Verify settings are loaded properly with default values."""
    settings = get_settings()
    assert settings.PORT == 8000
    assert settings.ENVIRONMENT == "development"
    assert settings.MAX_DAILY_LLM_REQUESTS == 100
    print("✅ test_settings_loading PASSED")


def test_usage_tracker_initialization():
    """Verify usage tracker initialized with ₹0 limits."""
    stats = usage_tracker.get_stats()
    assert stats["budget_tier"] == "Strict ₹0 (Free Tier Only)"
    assert stats["total_llm_requests"] == 0
    assert stats["remaining_daily_requests"] == 100
    print("✅ test_usage_tracker_initialization PASSED")


async def test_api_and_frontend():
    """Verify /api/health and / index via ASGITransport."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Test /api/health
        health_resp = await client.get("/api/health")
        assert health_resp.status_code == 200
        data = health_resp.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert "uptime_seconds" in data
        assert data["runtime"]["python_version"].startswith("3.12")
        assert data["budget_telemetry"]["total_llm_requests"] == 0
        print("✅ test_health_endpoint PASSED: Service is", data["service"])

        # Test frontend index
        frontend_resp = await client.get("/")
        assert frontend_resp.status_code == 200
        assert "Synaptix" in frontend_resp.text
        assert "Multi-Agent AI" in frontend_resp.text
        print("✅ test_frontend_serving PASSED: Dashboard HTML served successfully")


async def main():
    print("Running Milestone 1 Foundation Tests...")
    test_settings_loading()
    test_usage_tracker_initialization()
    await test_api_and_frontend()
    print("🎉 ALL MILESTONE 1 FOUNDATION TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(main())
