"""
Application Configuration
Loads and validates environment variables using Pydantic Settings.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Server Configuration
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    DEBUG: bool = True

    # Google Gemini API (Configured in Milestone 2)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"

    # Firebase Firestore (Configured in Milestone 4)
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None

    # Google Calendar & Gmail OAuth (synaptix-68373)
    GOOGLE_CALENDAR_CLIENT_ID: Optional[str] = None
    GOOGLE_CALENDAR_CLIENT_SECRET: Optional[str] = None
    GOOGLE_TOKEN_PATH: str = "token.json"
    GOOGLE_OAUTH_SCOPES: list[str] = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/gmail.compose",
    ]

    # OpenWeatherMap API (Configured in Milestone 6)
    OPENWEATHERMAP_API_KEY: Optional[str] = None
    DEFAULT_CITY: str = "Bengaluru"

    # Zero-Cost Safety Limits (Enforced at application layer)
    MAX_DAILY_LLM_REQUESTS: int = 100
    MAX_TOOL_CALLS_PER_RUN: int = 5
    MAX_TOKENS_PER_RESPONSE: int = 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance so we don't re-read .env on every request.
    Automatically mirrors GEMINI_API_KEY to os.environ for Google ADK compatibility.
    """
    s = Settings()
    if s.GEMINI_API_KEY and s.GEMINI_API_KEY.strip():
        import os
        os.environ.setdefault("GEMINI_API_KEY", s.GEMINI_API_KEY.strip())
    return s
