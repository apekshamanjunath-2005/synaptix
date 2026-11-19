"""
Usage and Quota Protection Tracker (Strict ₹0 Budget Enforcer)
Keeps an in-memory audit log and safeguards against runaway loops,
excessive token usage, or unintentional API costs.
"""

from datetime import datetime, timezone
from typing import Dict, Any


class UsageTracker:
    def __init__(self, max_daily_requests: int = 100, max_tool_calls_per_run: int = 5):
        self.max_daily_requests = max_daily_requests
        self.max_tool_calls_per_run = max_tool_calls_per_run
        self.started_at = datetime.now(timezone.utc)
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

    def check_request_allowed(self) -> bool:
        """Verify whether an LLM request is within free-tier budget limits."""
        return self.total_llm_requests < self.max_daily_requests

    def record_llm_request(self, tokens_used: int = 0) -> None:
        """Record an LLM request and accumulated tokens."""
        self.total_llm_requests += 1
        self.total_tokens_consumed += tokens_used
        self.service_calls["gemini"] += 1

    def record_agent_run(self) -> None:
        """Record a multi-agent invocation."""
        self.total_agent_runs += 1

    def record_tool_call(self, tool_name: str) -> None:
        """Record an individual tool execution."""
        self.total_tool_calls += 1
        if tool_name in self.service_calls:
            self.service_calls[tool_name] += 1
        else:
            self.service_calls[tool_name] = 1

    def get_stats(self) -> Dict[str, Any]:
        """Return current usage and budget status summary."""
        remaining_requests = max(0, self.max_daily_requests - self.total_llm_requests)
        return {
            "budget_tier": "Strict ₹0 (Free Tier Only)",
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
