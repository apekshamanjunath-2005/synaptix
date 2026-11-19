"""
Synaptix Multi-Agent System Package
Exports the Coordinator Agent and all 4 Specialist Agents.
"""

from app.agents.coordinator import coordinator_agent
from app.agents.task_agent import task_agent
from app.agents.notes_agent import notes_agent
from app.agents.calendar_agent import calendar_agent
from app.agents.planner_agent import smart_day_planner_agent

root_agent = coordinator_agent

__all__ = [
    "root_agent",
    "coordinator_agent",
    "task_agent",
    "notes_agent",
    "calendar_agent",
    "smart_day_planner_agent",
]
