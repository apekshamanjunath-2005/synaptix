"""
Conversational Chat Endpoint (Milestone 3 — Multi-Agent Orchestration)
Routes natural language user requests through the Coordinator Agent
and specialized agents using Google ADK.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.orchestrator import orchestrator
from app.api.auth import get_current_user
from app.agents.context import set_user_context
from app.core.usage_tracker import verify_budget_quota

router = APIRouter(prefix="/api", tags=["Multi-Agent Chat"])


class ChatMessage(BaseModel):
    role: str = Field(description="Role: 'user' or 'model'")
    content: str = Field(description="Message text")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2500, description="User prompt or inquiry")
    session_id: Optional[str] = Field(default=None, description="Session ID for multi-turn continuity")
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Prior conversation turns for multi-turn context"
    )
    timezone: Optional[str] = Field(
        default=None,
        description="User browser IANA timezone (e.g. 'Asia/Kolkata', 'America/New_York')"
    )


class ChatResponse(BaseModel):
    reply: str
    model: str = "gemini-2.5-flash"
    configured: bool = True
    session_id: Optional[str] = None
    orchestration: Optional[Dict[str, Any]] = None
    budget_telemetry: Optional[Dict[str, Any]] = None


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_budget_quota)])
async def chat_endpoint(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Handle natural language user requests via Synaptix Coordinator Agent.
    Delegates to TaskAgent, NotesAgent, CalendarAgent, GmailAgent, or SmartDayPlannerAgent.
    Protected by daily ₹0 quota limits and scoped to active authenticated user.
    """
    uid = current_user.get("user_id", "default_user")
    uname = current_user.get("name")
    uemail = current_user.get("email")

    set_user_context(user_id=uid, name=uname, email=uemail, timezone=request.timezone)

    result = await orchestrator.run_workflow(
        user_input=request.message,
        session_id=request.session_id,
        user_id=uid,
        user_name=uname,
        user_email=uemail,
        user_tz=request.timezone,
    )

    return ChatResponse(
        reply=result.get("reply", "Coordinator completed the task."),
        model=result.get("model", "gemini-2.5-flash"),
        session_id=result.get("session_id"),
        orchestration=result.get("orchestration"),
        budget_telemetry=result.get("budget_telemetry"),
    )
