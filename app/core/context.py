"""
Synaptix Execution Context (Core)
Provides thread-safe and async-safe request context for multi-user isolation.
"""

import contextvars
from typing import Optional

current_user_id: contextvars.ContextVar[str] = contextvars.ContextVar("current_user_id", default="default_user")
current_user_name: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("current_user_name", default=None)
current_user_email: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("current_user_email", default=None)


def set_user_context(user_id: str = "default_user", name: Optional[str] = None, email: Optional[str] = None):
    """Sets the active execution context for the current request/turn."""
    t_id = current_user_id.set(user_id or "default_user")
    t_name = current_user_name.set(name)
    t_email = current_user_email.set(email)
    return t_id, t_name, t_email


def get_user_context():
    """Retrieves the current execution context."""
    return {
        "user_id": current_user_id.get("default_user"),
        "name": current_user_name.get(None),
        "email": current_user_email.get(None),
    }
