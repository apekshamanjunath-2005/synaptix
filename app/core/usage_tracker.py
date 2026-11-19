"""
Usage and Quota Protection Tracker (Strict ₹0 Budget Enforcer)
Keeps a persistent daily audit log and safeguards against runaway loops,
excessive token usage, or unintentional API costs.
"""

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
from fastapi import HTTPException, status

logger = logging.getLogger("synaptix.usage_tracker")

CACHE_FILE = Path(__file__).resolve().parent.parent.parent / ".usage_cache.json"


class UsageTracker:
    def __init__(self, max_daily_requests: int = 100, max_tool_calls_per_run: int = 5):
        self.max_daily_requests = max_daily_requests
        self.max_tool_calls_per_run = max_tool_calls_per_run
        self._lock = threading.Lock()
        self.started_at = datetime.now(timezone.utc)
        self.current_date = self._get_today_str()
        
        # Metrics
        self.total_llm_requests = 0
        self.total_tokens_consumed = 0
        self.total_agent_runs = 0
        self.total_tool_calls = 0
        self.service_calls: Dict[str, int] = {
            "gemini": 0,
            "firestore": 0,
            "calendar": 0,
            "weather": 0,
        }
        
        # Load persisted usage if exists
        self._load_from_cache()

    @staticmethod
    def _get_today_str() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _rollover_day_if_needed(self) -> None:
        """Reset daily counters when UTC date changes."""
        today = self._get_today_str()
        if today != self.current_date:
            logger.info("New day detected (%s vs %s). Resetting daily counters.", today, self.current_date)
            self.current_date = today
            self.total_llm_requests = 0
            self.total_tokens_consumed = 0
            self.total_agent_runs = 0
            self.total_tool_calls = 0
            for k in self.service_calls:
                self.service_calls[k] = 0
            self._save_to_cache()

    def _load_from_cache(self) -> None:
        """Load usage state from local cache file if valid for today."""
        with self._lock:
            if not CACHE_FILE.exists():
                return
            try:
                data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
                if data.get("date") == self.current_date:
                    self.total_llm_requests = data.get("total_llm_requests", 0)
                    self.total_tokens_consumed = data.get("total_tokens_consumed", 0)
                    self.total_agent_runs = data.get("total_agent_runs", 0)
                    self.total_tool_calls = data.get("total_tool_calls", 0)
                    self.service_calls.update(data.get("service_calls", {}))
                    logger.info("Loaded persisted usage cache for %s (%d requests used)", self.current_date, self.total_llm_requests)
                else:
                    # Stale cache from previous date
                    self._rollover_day_if_needed()
            except Exception as e:
                logger.warning("Could not load usage cache, starting fresh: %s", e)

    def _save_to_cache(self) -> None:
        """Persist current day usage state to disk."""
        try:
            payload = {
                "date": self.current_date,
                "total_llm_requests": self.total_llm_requests,
                "total_tokens_consumed": self.total_tokens_consumed,
                "total_agent_runs": self.total_agent_runs,
                "total_tool_calls": self.total_tool_calls,
                "service_calls": self.service_calls,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
            CACHE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Could not persist usage cache to disk: %s", e)

    def check_request_allowed(self) -> bool:
        """Verify whether an LLM request is within free-tier budget limits."""
        with self._lock:
            self._rollover_day_if_needed()
            return self.total_llm_requests < self.max_daily_requests

    def enforce_quota_or_raise(self) -> None:
        """Raise HTTP 429 if daily budget limit has been reached."""
        if not self.check_request_allowed():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "QuotaExceeded",
                    "message": (
                        f"Daily ₹0 Free-Tier quota reached ({self.max_daily_requests} requests/day). "
                        "Operation blocked to guarantee zero-cost safety."
                    ),
                    "total_llm_requests": self.total_llm_requests,
                    "max_daily_requests": self.max_daily_requests,
                    "remaining_daily_requests": 0,
                    "current_date_utc": self.current_date,
                }
            )

    def record_llm_request(self, tokens_used: int = 0) -> None:
        """Record an LLM request and accumulated tokens."""
        with self._lock:
            self._rollover_day_if_needed()
            self.total_llm_requests += 1
            self.total_tokens_consumed += tokens_used
            self.service_calls["gemini"] = self.service_calls.get("gemini", 0) + 1
            self._save_to_cache()

    def record_agent_run(self) -> None:
        """Record a multi-agent invocation."""
        with self._lock:
            self._rollover_day_if_needed()
            self.total_agent_runs += 1
            self._save_to_cache()

    def record_tool_call(self, tool_name: str) -> None:
        """Record an individual tool execution."""
        with self._lock:
            self._rollover_day_if_needed()
            self.total_tool_calls += 1
            self.service_calls[tool_name] = self.service_calls.get(tool_name, 0) + 1
            self._save_to_cache()

    def reset_counters_for_testing(self) -> None:
        """Explicitly reset counters (used in testing suites)."""
        with self._lock:
            self.total_llm_requests = 0
            self.total_tokens_consumed = 0
            self.total_agent_runs = 0
            self.total_tool_calls = 0
            for k in self.service_calls:
                self.service_calls[k] = 0
            self._save_to_cache()

    def get_stats(self) -> Dict[str, Any]:
        """Return current usage and budget status summary."""
        with self._lock:
            self._rollover_day_if_needed()
            remaining_requests = max(0, self.max_daily_requests - self.total_llm_requests)
            return {
                "budget_tier": "Strict ₹0 (Free Tier Only)",
                "date_utc": self.current_date,
                "total_llm_requests": self.total_llm_requests,
                "daily_request_limit": self.max_daily_requests,
                "remaining_daily_requests": remaining_requests,
                "total_tokens_consumed": self.total_tokens_consumed,
                "total_agent_runs": self.total_agent_runs,
                "total_tool_calls": self.total_tool_calls,
                "service_calls": self.service_calls,
                "started_at": self.started_at.isoformat(),
            }


# Global singleton instance for application lifespan
usage_tracker = UsageTracker()


async def verify_budget_quota():
    """FastAPI dependency to enforce budget guards on protected endpoints."""
    usage_tracker.enforce_quota_or_raise()
