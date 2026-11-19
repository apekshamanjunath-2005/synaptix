"""
Notes API Router (Milestone 4 — Firestore CRUD)
Direct REST endpoints for notes retrieval, semantic search, creation, and deletion.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.database.firestore import firestore_service

router = APIRouter(prefix="/api/notes", tags=["Notes Management"])


class NoteCreateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    title: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)


@router.get("")
async def list_or_search_notes(
    query: Optional[str] = Query(default=None, description="Search term"),
    limit: int = Query(default=20, ge=1, le=100)
):
    """Retrieve or search notes stored in Firestore."""
    if query:
        notes = firestore_service.search_notes(query)
    else:
        notes = firestore_service.get_notes(limit=limit)
    return {"count": len(notes), "notes": notes}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_note(req: NoteCreateRequest):
    """Save a new note in Firestore."""
    note = firestore_service.add_note(
        content=req.content,
        title=req.title,
        tags=req.tags
    )
    return {"success": True, "note": note}


@router.delete("/{note_id}")
async def delete_note(note_id: str):
    """Delete a note from Firestore."""
    deleted = firestore_service.delete_note(note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Note '{note_id}' not found.")
    return {"success": True, "note_id": note_id}
