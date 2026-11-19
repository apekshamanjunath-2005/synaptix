"""
Notes API Router (Milestone 4 — Firestore CRUD)
Direct REST endpoints for notes retrieval, semantic search, creation, and deletion.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.database.firestore import firestore_service
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/notes", tags=["Notes Management"])


class NoteCreateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    title: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)


@router.get("")
async def list_or_search_notes(
    query: Optional[str] = Query(default=None, description="Search term"),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve or search notes stored in Firestore for the current user."""
    uid = current_user.get("user_id")
    filter_uid = uid if uid != "default_user" else None
    if query:
        notes = firestore_service.search_notes(query, user_id=filter_uid)
    else:
        notes = firestore_service.get_notes(limit=limit, user_id=filter_uid)
    return {"count": len(notes), "notes": notes}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_note(
    req: NoteCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Save a new note in Firestore associated with the current user."""
    uid = current_user.get("user_id", "default_user")
    note = firestore_service.add_note(
        content=req.content,
        title=req.title,
        tags=req.tags,
        user_id=uid
    )
    return {"success": True, "note": note}


@router.delete("/{note_id}")
async def delete_note(note_id: str):
    """Delete a note from Firestore."""
    deleted = firestore_service.delete_note(note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Note '{note_id}' not found.")
    return {"success": True, "note_id": note_id}
