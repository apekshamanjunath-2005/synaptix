"""
Conversational Chat Endpoint (Milestone 2)
Provides API for natural language interactions powered by Gemini 2.5 Flash.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.gemini_client import gemini_service
from app.core.usage_tracker import verify_budget_quota

router = APIRouter(prefix="/api", tags=["Conversational Chat"])


class ChatMessage(BaseModel):
    role: str = Field(description="Role: 'user' or 'model'")
    content: str = Field(description="Message text")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2500, description="User prompt or inquiry")
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Prior conversation turns for multi-turn context"
    )


class ChatResponse(BaseModel):
    reply: str
    model: str
    configured: bool
    usage: Optional[Dict[str, Any]] = None
    budget_telemetry: Optional[Dict[str, Any]] = None


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_budget_quota)])
async def chat_endpoint(request: ChatRequest):
    """
    Handle natural language user requests using Gemini 2.5 Flash.
    Protected by daily ₹0 quota limits and 15 RPM burst limiter.
    """
    history_dicts = None
    if request.conversation_history:
        history_dicts = [{"role": msg.role, "content": msg.content} for msg in request.conversation_history]

    result = await gemini_service.generate_response(
        prompt=request.message,
        conversation_history=history_dicts
    )

    return ChatResponse(
        reply=result.get("reply", "No reply generated."),
        model=result.get("model", "gemini-2.5-flash"),
        configured=result.get("configured", False),
        usage=result.get("usage"),
        budget_telemetry=result.get("budget_telemetry"),
    )
