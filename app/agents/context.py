"""
Synaptix Agent Execution Context
Re-exports from app.core.context for backwards compatibility.
"""

from app.core.context import (
    current_user_id,
    current_user_name,
    current_user_email,
    set_user_context,
    get_user_context,
)

__all__ = [
    "current_user_id",
    "current_user_name",
    "current_user_email",
    "set_user_context",
    "get_user_context",
]
