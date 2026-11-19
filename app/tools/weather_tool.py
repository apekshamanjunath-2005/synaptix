"""
Weather Tool Provider for Synaptix Smart Day Planner
Integrates with OpenWeatherMap Current Weather API (Free Tier: 1,000,000 calls/month).

Features:
- Live OpenWeatherMap API v2.5 integration via httpx
- Graceful offline / simulated fallback when API key is unconfigured or network is unavailable
- Activity recommendation engine (indoor vs. outdoor suitability)
- Zero-cost guarantee (never requires paid API credits or billing accounts)
"""

import logging
import hashlib
from typing import Optional, Dict, Any
import httpx

from app.config import get_settings

logger = logging.getLogger("synaptix.tools.weather")

OWM_API_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


_USE_CONFIG_DEFAULT = object()


class WeatherTool:
    """
    OpenWeatherMap tool provider with live HTTP and graceful zero-cost fallback modes.
    """

    def __init__(self, api_key: Any = _USE_CONFIG_DEFAULT, default_city: Optional[str] = None):
        settings = get_settings()
        if api_key is _USE_CONFIG_DEFAULT:
            self.api_key = settings.OPENWEATHERMAP_API_KEY
        else:
            self.api_key = api_key
        self.default_city = default_city or settings.DEFAULT_CITY or "Bengaluru"

    def _assess_outdoor_suitability(self, condition: str, temp_c: float, wind_kmh: float) -> tuple[bool, str]:
        """
        Calculates whether conditions are favorable for outdoor productivity/exercise.
        """
        condition_lower = condition.lower()
        
        # Severe weather conditions
        if any(w in condition_lower for w in ["rain", "drizzle", "storm", "thunder", "snow", "squall", "tornado"]):
            return (
                False,
                f"Rain or adverse weather detected ({condition}). Recommended: prioritize indoor focus work, reading, or home gym sessions."
            )
        
        # Extreme temperatures
        if temp_c > 38.0:
            return (
                False,
                f"High heat warning ({temp_c:.1f}°C). Recommended: stay hydrated and schedule deep work indoors during peak afternoon hours."
            )
        if temp_c < 5.0:
            return (
                False,
                f"Chilly weather ({temp_c:.1f}°C). Recommended: dress warmly for morning commutes and schedule outdoor activities during midday sun."
            )
        
        # High wind
        if wind_kmh > 45.0:
            return (
                False,
                f"High gusty winds ({wind_kmh:.1f} km/h). Recommended: avoid cycling or open-air meetings."
            )
            
        # Ideal conditions
        return (
            True,
            f"Pleasant conditions ({condition}, {temp_c:.1f}°C). Excellent for a morning walk, outdoor coffee break, or open-air work session."
        )

    def _generate_simulated_weather(self, city: str) -> Dict[str, Any]:
        """
        Generates realistic, deterministic weather metrics when no live API key is configured.
        Guarantees Synaptix works 100% out-of-the-box at zero cost.
        """
        city_clean = city.strip()
        hash_val = int(hashlib.md5(city_clean.lower().encode()).hexdigest(), 16)
        
        # Derive pseudo-realistic variations from city name hash
        temp_options = [21.5, 23.0, 25.5, 27.0, 19.5, 28.5]
        conditions = [
            ("Clear Sky", 45, 10.5),
            ("Partly Cloudy", 55, 12.0),
            ("Sunny", 40, 8.5),
            ("Scattered Clouds", 60, 14.0),
            ("Passing Showers", 78, 18.5)
        ]
        
        temp_c = temp_options[hash_val % len(temp_options)]
        condition, humidity, wind_kmh = conditions[hash_val % len(conditions)]
        feels_like_c = round(temp_c + (1.2 if humidity > 60 else -0.5), 1)
        
        suitable, recommendation = self._assess_outdoor_suitability(condition, temp_c, wind_kmh)
        
        return {
            "city": city_clean.title(),
            "condition": condition,
            "temperature_c": temp_c,
            "feels_like_c": feels_like_c,
            "humidity_pct": humidity,
            "wind_kmh": wind_kmh,
            "suitable_for_outdoor": suitable,
            "activity_recommendation": recommendation,
            "source": "simulated_fallback",
            "live_api_active": False,
            "note": "Free-tier fallback active. Provide OPENWEATHERMAP_API_KEY in .env for live satellite weather."
        }

    async def get_weather_async(self, city: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetches current weather asynchronously via OpenWeatherMap API with graceful fallback.
        """
        target_city = (city or self.default_city).strip()
        
        if not self.api_key:
            logger.info("OPENWEATHERMAP_API_KEY not configured — using zero-cost fallback for %s", target_city)
            return self._generate_simulated_weather(target_city)

        params = {
            "q": target_city,
            "appid": self.api_key,
            "units": "metric"
        }

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                response = await client.get(OWM_API_BASE_URL, params=params)
                
            if response.status_code == 200:
                data = response.json()
                weather_desc = data["weather"][0]["description"].title() if data.get("weather") else "Clear"
                temp = float(data["main"]["temp"])
                feels_like = float(data["main"]["feels_like"])
                humidity = int(data["main"]["humidity"])
                wind_speed_ms = float(data.get("wind", {}).get("speed", 0.0))
                wind_kmh = round(wind_speed_ms * 3.6, 1)
                
                suitable, recommendation = self._assess_outdoor_suitability(weather_desc, temp, wind_kmh)
                
                logger.info("Live weather retrieved for %s: %s, %.1f°C", target_city, weather_desc, temp)
                return {
                    "city": data.get("name", target_city),
                    "condition": weather_desc,
                    "temperature_c": round(temp, 1),
                    "feels_like_c": round(feels_like, 1),
                    "humidity_pct": humidity,
                    "wind_kmh": wind_kmh,
                    "suitable_for_outdoor": suitable,
                    "activity_recommendation": recommendation,
                    "source": "live_openweathermap",
                    "live_api_active": True
                }
            else:
                logger.warning(
                    "OpenWeatherMap returned status %d: %s. Reverting to zero-cost fallback.",
                    response.status_code,
                    response.text
                )
                fallback = self._generate_simulated_weather(target_city)
                fallback["api_warning"] = f"OpenWeatherMap HTTP {response.status_code}"
                return fallback

        except Exception as exc:
            logger.error("Weather fetch failed for '%s': %s. Reverting to fallback.", target_city, exc)
            fallback = self._generate_simulated_weather(target_city)
            fallback["api_warning"] = f"Network or lookup error: {str(exc)}"
            return fallback

    def get_weather_sync(self, city: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronous weather fetcher using httpx.Client (safe to invoke inside ADK tool wrappers
        without event loop conflicts or run_until_complete crashes).
        """
        target_city = (city or self.default_city).strip()
        
        if not self.api_key:
            return self._generate_simulated_weather(target_city)

        params = {
            "q": target_city,
            "appid": self.api_key,
            "units": "metric"
        }

        try:
            with httpx.Client(timeout=6.0) as client:
                response = client.get(OWM_API_BASE_URL, params=params)
                
            if response.status_code == 200:
                data = response.json()
                weather_desc = data["weather"][0]["description"].title() if data.get("weather") else "Clear"
                temp = float(data["main"]["temp"])
                feels_like = float(data["main"]["feels_like"])
                humidity = int(data["main"]["humidity"])
                wind_kmh = round(float(data.get("wind", {}).get("speed", 0.0)) * 3.6, 1)
                
                suitable, recommendation = self._assess_outdoor_suitability(weather_desc, temp, wind_kmh)
                
                return {
                    "city": data.get("name", target_city),
                    "condition": weather_desc,
                    "temperature_c": round(temp, 1),
                    "feels_like_c": round(feels_like, 1),
                    "humidity_pct": humidity,
                    "wind_kmh": wind_kmh,
                    "suitable_for_outdoor": suitable,
                    "activity_recommendation": recommendation,
                    "source": "live_openweathermap",
                    "live_api_active": True
                }
            else:
                fallback = self._generate_simulated_weather(target_city)
                fallback["api_warning"] = f"OpenWeatherMap HTTP {response.status_code}"
                return fallback

        except Exception as exc:
            fallback = self._generate_simulated_weather(target_city)
            fallback["api_warning"] = f"Network or lookup error: {str(exc)}"
            return fallback


# Singleton instance
weather_tool = WeatherTool()
