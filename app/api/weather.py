"""
Weather API Router for Synaptix
Provides endpoints to fetch current weather and outdoor suitability ratings.
"""

from typing import Optional
from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field

from app.tools.weather_tool import weather_tool

router = APIRouter(prefix="/api/weather", tags=["Weather"])


class WeatherResponse(BaseModel):
    city: str
    condition: str
    temperature_c: float
    feels_like_c: float
    humidity_pct: int
    wind_kmh: float
    suitable_for_outdoor: bool
    activity_recommendation: str
    source: str
    live_api_active: bool
    note: Optional[str] = None
    api_warning: Optional[str] = None


@router.get("", response_model=WeatherResponse, status_code=status.HTTP_200_OK)
async def get_weather(
    city: Optional[str] = Query(default=None, description="City name to fetch weather for")
):
    """
    Fetch current weather metrics, outdoor activity recommendation, and source info.
    Zero-Cost: Calls OpenWeatherMap if key is provided; otherwise returns deterministic simulation.
    """
    result = await weather_tool.get_weather_async(city=city)
    return result
