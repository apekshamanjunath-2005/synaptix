"""
Health Check and Diagnostics Endpoint
Provides system telemetry, uptime, version, and budget usage metrics.
"""

import sys
import time
from datetime import datetime, timezone
from fastapi import APIRouter
from app.config import get_settings
from app.core.usage_tracker import usage_tracker

router = APIRouter(prefix="/api", tags=["Health & Diagnostics"])

START_TIME = time.time()


@router.get("/health")
async def get_health():
    """
    Returns application health status, runtime environment,
    uptime, and zero-cost budget usage metrics.
    """
    settings = get_settings()
    uptime_seconds = round(time.time() - START_TIME, 2)

    return {
        "status": "healthy",
        "service": "Synaptix AI Personal Productivity Assistant",
        "version": "0.1.0",
        "milestone": "Milestone 1 — Foundation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds,
        "environment": settings.ENVIRONMENT,
        "runtime": {
            "python_version": sys.version.split()[0],
            "debug": settings.DEBUG,
            "host": settings.HOST,
            "port": settings.PORT,
        },
        "integrations_status": {
            "gemini_configured": bool(settings.GEMINI_API_KEY),
            "firebase_configured": bool(settings.FIREBASE_PROJECT_ID),
            "google_calendar_configured": bool(settings.GOOGLE_CALENDAR_CLIENT_ID),
            "weather_configured": bool(settings.OPENWEATHERMAP_API_KEY),
        },
        "budget_telemetry": usage_tracker.get_stats(),
    }
