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
from app.database.firestore import firestore_service

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
    target_agent: Optional[str] = Field(
        default=None,
        description="Explicit target agent route: auto, tasks, notes, calendar, gmail, planner"
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

    # 1. Resolve or initialize persistent chat session
    incoming_sid = request.session_id.strip() if request.session_id else None
    if incoming_sid:
        session_obj = firestore_service.create_or_get_session(
            user_id=uid,
            session_id=incoming_sid,
            title=request.message[:40]
        )
        effective_sid = session_obj["session_id"]
    else:
        auto_title = request.message.strip()[:40]
        if len(request.message.strip()) > 40:
            auto_title += "..."
        session_obj = firestore_service.create_or_get_session(
            user_id=uid,
            session_id=None,
            title=auto_title or "New Chat"
        )
        effective_sid = session_obj["session_id"]

    # 2. Persist incoming user message to Firestore subcollection
    firestore_service.add_message_to_session(
        session_id=effective_sid,
        role="user",
        content=request.message,
        user_id=uid
    )

    # 3. Load sliding window (last 10 messages) for multi-turn context
    recent_history = firestore_service.get_session_messages(
        session_id=effective_sid,
        limit=10,
        user_id=uid
    )

    # 4. Execute multi-agent orchestration
    result = await orchestrator.run_workflow(
        user_input=request.message,
        session_id=effective_sid,
        user_id=uid,
        user_name=uname,
        user_email=uemail,
        user_tz=request.timezone,
        conversation_history=recent_history,
        target_agent=request.target_agent,
    )

    assistant_reply = result.get("reply", "Coordinator completed the task.")

    # 5. Persist assistant response to Firestore subcollection
    firestore_service.add_message_to_session(
        session_id=effective_sid,
        role="assistant",
        content=assistant_reply,
        user_id=uid
    )

    return ChatResponse(
        reply=assistant_reply,
        model=result.get("model", "gemini-2.5-flash"),
        session_id=effective_sid,
        orchestration=result.get("orchestration"),
        budget_telemetry=result.get("budget_telemetry"),
    )
