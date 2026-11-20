"""
Chat Sessions API Router (Persistent Multi-Session History)
Provides endpoints to list sessions, retrieve conversation message history,
and delete past chat sessions with strict user isolation.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.database.firestore import firestore_service

router = APIRouter(tags=["Chat Sessions"])


# ════════════════════════════════════════════════════════════════════════════════
# PYDANTIC SCHEMAS
# ════════════════════════════════════════════════════════════════════════════════

class SessionItem(BaseModel):
    session_id: str
    title: str
    user_id: Optional[str] = None
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):
    success: bool = True
    sessions: List[SessionItem]


class SessionMessageItem(BaseModel):
    id: Optional[str] = None
    session_id: str
    role: str = Field(description="Role: 'user' or 'assistant'")
    content: str = Field(description="Message text")
    timestamp: str


class SessionMessagesResponse(BaseModel):
    success: bool = True
    session_id: str
    messages: List[SessionMessageItem]


class DeleteSessionResponse(BaseModel):
    success: bool = True
    message: str = "Session deleted successfully"


# ════════════════════════════════════════════════════════════════════════════════
# SESSION ENDPOINTS (Supporting both /sessions and /api/sessions)
# ════════════════════════════════════════════════════════════════════════════════

@router.get("/sessions", response_model=SessionListResponse)
@router.get("/api/sessions", response_model=SessionListResponse)
async def list_chat_sessions(
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List past chat sessions for current user ordered by updated_at descending.
    """
    uid = current_user.get("user_id", "default_user")
    sessions = firestore_service.list_sessions(user_id=uid, limit=limit)
    return SessionListResponse(
        success=True,
        sessions=[SessionItem(**s) for s in sessions]
    )


@router.get("/sessions/{session_id}/messages", response_model=SessionMessagesResponse)
@router.get("/api/sessions/{session_id}/messages", response_model=SessionMessagesResponse)
async def get_session_messages(
    session_id: str,
    limit: Optional[int] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Load message history for a specific chat session scoped to current user.
    """
    uid = current_user.get("user_id", "default_user")
    session = firestore_service.get_session(session_id=session_id, user_id=uid)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session '{session_id}' not found or unauthorized"
        )

    messages = firestore_service.get_session_messages(session_id=session_id, limit=limit, user_id=uid)
    return SessionMessagesResponse(
        success=True,
        session_id=session_id,
        messages=[SessionMessageItem(**m) for m in messages]
    )


@router.delete("/sessions/{session_id}", response_model=DeleteSessionResponse)
@router.delete("/api/sessions/{session_id}", response_model=DeleteSessionResponse)
async def delete_chat_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a chat session and all its stored messages for current user.
    """
    uid = current_user.get("user_id", "default_user")
    deleted = firestore_service.delete_session(session_id=session_id, user_id=uid)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session '{session_id}' not found or unauthorized"
        )

    return DeleteSessionResponse(
        success=True,
        message=f"Session '{session_id}' deleted successfully"
    )
