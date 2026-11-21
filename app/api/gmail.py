"""
Gmail Management API Endpoints
Provides endpoints for listing, creating, and dispatching email drafts with Human-in-the-Loop review.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.tools.gmail_service import gmail_service
from app.api.auth import get_optional_user, get_current_user
from app.agents.context import set_user_context

router = APIRouter(prefix="/api/gmail", tags=["Gmail & Drafts"])


class CreateDraftRequest(BaseModel):
    to: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body content")


class SendDraftRequest(BaseModel):
    draft_id: str = Field(..., description="Draft identifier to dispatch")


@router.get("/status")
async def get_gmail_status(current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    """Diagnostic endpoint checking active Gmail API connection and credentials status."""
    uid = current_user.get("user_id", "default_user") if current_user else "default_user"
    return gmail_service.get_connection_status(user_id=uid)


@router.get("/drafts")
async def list_drafts(current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    """List email drafts for current user."""
    uid = current_user.get("user_id", "default_user") if current_user else "default_user"
    drafts = gmail_service.list_drafts(user_id=uid)
    return {"success": True, "count": len(drafts), "drafts": drafts}


@router.post("/drafts")
async def create_draft(
    req: CreateDraftRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """Create a new email draft (does NOT send)."""
    uid = current_user.get("user_id", "default_user") if current_user else "default_user"
    draft = gmail_service.create_email_draft(
        to=req.to,
        subject=req.subject,
        body=req.body,
        user_id=uid
    )
    return {"success": True, "draft": draft}


@router.post("/send")
async def send_draft(
    req: SendDraftRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """Dispatch an email draft after receiving explicit user approval."""
    uid = current_user.get("user_id", "default_user") if current_user else "default_user"
    result = gmail_service.send_email_draft(draft_id=req.draft_id, user_id=uid)
    return {"success": result.get("sent", False), "result": result}
