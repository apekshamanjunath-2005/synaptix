"""
Google Gemini 2.5 Flash Client Service
Provides async interface to Google Gemini models with strict ₹0 budget guards,
burst rate limiting (15 RPM), and graceful fallback error handling.
"""

import logging
import time
from collections import deque
from typing import Optional, List, Dict, Any
from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.config import get_settings
from app.core.usage_tracker import usage_tracker

logger = logging.getLogger("synaptix.gemini")


class RateLimiterRPM:
    """
    Sliding window rate limiter to guarantee compliance with
    Google AI Studio's 15 Requests-Per-Minute (RPM) free-tier limit.
    """
    def __init__(self, max_rpm: int = 15):
        self.max_rpm = max_rpm
        self.timestamps = deque()

    def check_and_record(self) -> bool:
        now = time.time()
        # Evict timestamps older than 60 seconds
        while self.timestamps and now - self.timestamps[0] > 60:
            self.timestamps.popleft()

        if len(self.timestamps) >= self.max_rpm:
            return False

        self.timestamps.append(now)
        return True


rpm_limiter = RateLimiterRPM(max_rpm=15)


class GeminiService:
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[genai.Client] = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize the Google GenAI client if an API key is present."""
        api_key = self.settings.GEMINI_API_KEY
        if api_key and api_key.strip():
            try:
                self._client = genai.Client(api_key=api_key.strip())
                logger.info("Google GenAI client initialized with model: %s", self.settings.GEMINI_MODEL)
            except Exception as e:
                logger.error("Failed to initialize Google GenAI client: %s", e)
                self._client = None
        else:
            self._client = None
            logger.info("GEMINI_API_KEY not configured. Running in unconfigured mode.")

    def is_configured(self) -> bool:
        """Check if a Gemini API key is currently configured."""
        return self._client is not None

    async def generate_response(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_instruction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a conversational response using Gemini 2.5 Flash.
        Enforces daily budget limits, 15 RPM rate limiting, and token ceilings.
        """
        # 1. Enforce strict daily quota limit (raises HTTP 429 if limit reached)
        usage_tracker.enforce_quota_or_raise()

        # 2. Enforce 15 RPM burst limiter
        if not rpm_limiter.check_and_record():
            return {
                "reply": "⚠️ Rate limit alert: Google AI Studio Free Tier allows up to 15 requests per minute. Please pause for a few seconds before trying again.",
                "model": self.settings.GEMINI_MODEL,
                "configured": True,
                "rate_limited": True,
            }

        # 3. Check for API key presence
        if not self._client:
            return {
                "reply": (
                    "**Gemini 2.5 Flash is ready to connect!** 🚀\n\n"
                    "To activate real AI responses at **₹0 cost**:\n"
                    "1. Visit [Google AI Studio](https://aistudio.google.com/) to get a free API key.\n"
                    "2. Add your key to your `.env` file:\n"
                    "   ```env\n"
                    "   GEMINI_API_KEY=your_actual_key_here\n"
                    "   ```\n"
                    "3. Restart the server or reload to begin chatting!"
                ),
                "model": self.settings.GEMINI_MODEL,
                "configured": False,
                "tokens_used": 0,
            }

        # 4. Construct Contents & System Prompt
        default_system_prompt = (
            "You are Synaptix, a high-performance Multi-Agent AI Personal Productivity Assistant. "
            "You help users manage tasks, personal notes, calendar events, and smart daily schedules. "
            "Be clear, concise, structured, and helpful. Format your answers in clean Markdown."
        )

        sys_prompt = system_instruction or default_system_prompt

        config = types.GenerateContentConfig(
            max_output_tokens=self.settings.MAX_TOKENS_PER_RESPONSE,
            temperature=0.7,
            system_instruction=sys_prompt,
        )

        # Build contents from conversation history if provided
        contents = []
        if conversation_history:
            for msg in conversation_history:
                role = "user" if msg.get("role") in ["user", "human"] else "model"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg.get("content", ""))]
                ))
        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        ))

        # 5. Invoke Gemini 2.5 Flash via Async Client
        try:
            response = await self._client.aio.models.generate_content(
                model=self.settings.GEMINI_MODEL,
                contents=contents,
                config=config,
            )

            # Extract token counts for usage telemetry
            total_tokens = 0
            prompt_tokens = 0
            candidate_tokens = 0

            if response.usage_metadata:
                total_tokens = response.usage_metadata.total_token_count or 0
                prompt_tokens = response.usage_metadata.prompt_token_count or 0
                candidate_tokens = response.usage_metadata.candidates_token_count or 0

            # Record telemetry in usage tracker
            usage_tracker.record_llm_request(tokens_used=total_tokens)

            reply_text = response.text or "I processed your request, but no text response was generated."

            return {
                "reply": reply_text,
                "model": self.settings.GEMINI_MODEL,
                "configured": True,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "candidate_tokens": candidate_tokens,
                    "total_tokens": total_tokens,
                },
                "budget_telemetry": usage_tracker.get_stats(),
            }

        except APIError as api_err:
            logger.error("Gemini API error occurred: %s", api_err)
            if "RESOURCE_EXHAUSTED" in str(api_err):
                return {
                    "reply": "⚠️ Free-tier quota exceeded on Google AI Studio. Please wait a minute for the rate-limit window to reset.",
                    "model": self.settings.GEMINI_MODEL,
                    "error": "RESOURCE_EXHAUSTED",
                    "configured": True,
                }
            return {
                "reply": f"Gemini API returned an error: {api_err.message if hasattr(api_err, 'message') else str(api_err)}",
                "model": self.settings.GEMINI_MODEL,
                "configured": True,
                "error": str(api_err),
            }

        except Exception as exc:
            logger.error("Unexpected error in Gemini service: %s", exc)
            return {
                "reply": f"Encountered an internal error while communicating with Gemini: {str(exc)}",
                "model": self.settings.GEMINI_MODEL,
                "configured": True,
                "error": str(exc),
            }


# Singleton service instance
gemini_service = GeminiService()
