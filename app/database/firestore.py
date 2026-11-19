"""
Synaptix Firestore Database Layer (Milestone 4)
Provides dual-mode Firestore adapter:
1. Live Firebase Firestore (via Spark Plan Free Tier credentials)
2. Thread-safe Local Firestore Persistence (100% offline, zero-credentials fallback)
Ensures zero-crash boot, strict ₹0 budget, and complete Firestore collection semantics.
"""

import os
import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.config import get_settings
from app.core.usage_tracker import usage_tracker

logger = logging.getLogger("synaptix.database.firestore")

LOCAL_DB_FILE = Path(__file__).resolve().parent.parent.parent / ".firestore_local.json"


# ════════════════════════════════════════════════════════════════════════════════
# LOCAL FIRESTORE SIMULATOR (Zero-credentials fallback / offline dev)
# ════════════════════════════════════════════════════════════════════════════════

class LocalFirestoreDocument:
    def __init__(self, collection_name: str, doc_id: str, storage_ref: dict, lock: threading.Lock):
        self.collection_name = collection_name
        self.id = doc_id
        self._storage = storage_ref
        self._lock = lock

    def get(self):
        with self._lock:
            data = self._storage.get(self.collection_name, {}).get(self.id)
            return LocalDocumentSnapshot(self.id, data)

    def set(self, data: dict):
        with self._lock:
            if self.collection_name not in self._storage:
                self._storage[self.collection_name] = {}
            self._storage[self.collection_name][self.id] = data
            self._persist()

    def update(self, updates: dict):
        with self._lock:
            doc = self._storage.get(self.collection_name, {}).get(self.id)
            if not doc:
                raise ValueError(f"Document {self.id} does not exist in {self.collection_name}")
            doc.update(updates)
            self._storage[self.collection_name][self.id] = doc
            self._persist()

    def delete(self):
        with self._lock:
            if self.collection_name in self._storage and self.id in self._storage[self.collection_name]:
                del self._storage[self.collection_name][self.id]
                self._persist()

    def _persist(self):
        try:
            LOCAL_DB_FILE.write_text(json.dumps(self._storage, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to persist local Firestore to disk: %s", e)


class LocalDocumentSnapshot:
    def __init__(self, doc_id: str, data: Optional[dict]):
        self.id = doc_id
        self._data = data
        self.exists = data is not None

    def to_dict(self) -> Optional[dict]:
        return self._data.copy() if self._data else None


class LocalFirestoreCollection:
    def __init__(self, collection_name: str, storage_ref: dict, lock: threading.Lock):
        self.collection_name = collection_name
        self._storage = storage_ref
        self._lock = lock

    def document(self, doc_id: Optional[str] = None) -> LocalFirestoreDocument:
        target_id = doc_id or f"doc-{uuid.uuid4().hex[:8]}"
        return LocalFirestoreDocument(self.collection_name, target_id, self._storage, self._lock)

    def stream(self):
        with self._lock:
            docs = self._storage.get(self.collection_name, {})
            return [LocalDocumentSnapshot(did, data) for did, data in docs.items()]


class LocalFirestoreClient:
    def __init__(self):
        self._lock = threading.Lock()
        self._storage: Dict[str, Dict[str, Any]] = {"tasks": {}, "notes": {}}
        self._load()

    def _load(self):
        if LOCAL_DB_FILE.exists():
            try:
                data = json.loads(LOCAL_DB_FILE.read_text(encoding="utf-8"))
                self._storage.update(data)
                logger.info("Loaded persisted Local Firestore from disk (%d tasks, %d notes)",
                            len(self._storage.get("tasks", {})), len(self._storage.get("notes", {})))
            except Exception as e:
                logger.warning("Could not read local Firestore cache: %s", e)

    def collection(self, name: str) -> LocalFirestoreCollection:
        return LocalFirestoreCollection(name, self._storage, self._lock)


# ════════════════════════════════════════════════════════════════════════════════
# FIRESTORE SERVICE ADAPTER
# ════════════════════════════════════════════════════════════════════════════════

class FirestoreService:
    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self.is_live_firebase = False
        self._init_connection()

    def _init_connection(self):
        """Connect to Live Firebase if credentials exist; otherwise use Local Firestore."""
        import firebase_admin
        from firebase_admin import credentials, firestore

        cred_path = self.settings.FIREBASE_CREDENTIALS_PATH
        if cred_path and os.path.exists(cred_path):
            try:
                if not firebase_admin._apps:
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred, {"projectId": self.settings.FIREBASE_PROJECT_ID})
                self.client = firestore.client()
                self.is_live_firebase = True
                logger.info("✅ Connected to Live Firebase Firestore (Spark Plan - ₹0)")
                return
            except Exception as e:
                logger.error("Failed to connect to Live Firebase with credentials: %s", e)

        # Fallback to Local Firestore Simulator (₹0, zero config required)
        self.client = LocalFirestoreClient()
        self.is_live_firebase = False
        logger.info("⚡ Running Local Firestore Adapter (100%% offline, ₹0 budget safe)")

    # ────────────────────────────────────────────────────────────────────────────
    # TASKS REPOSITORY
    # ────────────────────────────────────────────────────────────────────────────

    def add_task(
        self,
        title: str,
        due_date: Optional[str] = None,
        priority: str = "medium",
        status: str = "pending"
    ) -> Dict[str, Any]:
        """Insert a task document into the 'tasks' collection."""
        task_id = f"task-{uuid.uuid4().hex[:6]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        task_data = {
            "id": task_id,
            "title": title,
            "due_date": due_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "priority": priority.lower(),
            "status": status.lower(),
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        self.client.collection("tasks").document(task_id).set(task_data)
        usage_tracker.record_tool_call("firestore")
        logger.info("Firestore task added: %s (%s)", title, task_id)
        return task_data

    def get_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve tasks with optional status and priority filtering."""
        docs = self.client.collection("tasks").stream()
        tasks = []
        for doc in docs:
            t = doc.to_dict()
            if not t:
                continue
            if status and t.get("status") != status.lower():
                continue
            if priority and t.get("priority") != priority.lower():
                continue
            tasks.append(t)

        usage_tracker.record_tool_call("firestore")
        # Sort by created_at descending
        return sorted(tasks, key=lambda x: x.get("created_at", ""), reverse=True)

    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific task document by ID."""
        doc = self.client.collection("tasks").document(task_id).get()
        if doc and doc.exists:
            usage_tracker.record_tool_call("firestore")
            return doc.to_dict()
        return None

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing task document.
        Fixes the reference code bug by returning the fresh, updated state!
        """
        doc_ref = self.client.collection("tasks").document(task_id)
        doc = doc_ref.get()
        if not doc or not doc.exists:
            # Check by search if exact ID didn't match
            all_tasks = self.get_tasks()
            for t in all_tasks:
                if task_id in t["id"] or task_id.lower() in t["title"].lower():
                    task_id = t["id"]
                    doc_ref = self.client.collection("tasks").document(task_id)
                    doc = doc_ref.get()
                    break

        if not doc or not doc.exists:
            return None

        clean_updates = {k: v for k, v in updates.items() if v is not None}
        clean_updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        doc_ref.update(clean_updates)
        usage_tracker.record_tool_call("firestore")

        # Fetch and return the fresh, updated document snapshot
        fresh_doc = doc_ref.get()
        return fresh_doc.to_dict()

    def delete_task(self, task_id: str) -> bool:
        """Delete a task document from Firestore."""
        doc_ref = self.client.collection("tasks").document(task_id)
        doc = doc_ref.get()
        if not doc or not doc.exists:
            all_tasks = self.get_tasks()
            for t in all_tasks:
                if task_id in t["id"]:
                    task_id = t["id"]
                    doc_ref = self.client.collection("tasks").document(task_id)
                    doc = doc_ref.get()
                    break

        if doc and doc.exists:
            doc_ref.delete()
            usage_tracker.record_tool_call("firestore")
            logger.info("Firestore task deleted: %s", task_id)
            return True
        return False

    # ────────────────────────────────────────────────────────────────────────────
    # NOTES REPOSITORY
    # ────────────────────────────────────────────────────────────────────────────

    def add_note(
        self,
        content: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Save a new note document into the 'notes' collection."""
        note_id = f"note-{uuid.uuid4().hex[:6]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        note_title = title or (content[:35] + "..." if len(content) > 35 else content)
        note_data = {
            "id": note_id,
            "title": note_title,
            "content": content,
            "tags": tags or [],
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        self.client.collection("notes").document(note_id).set(note_data)
        usage_tracker.record_tool_call("firestore")
        logger.info("Firestore note added: %s (%s)", note_title, note_id)
        return note_data

    def get_notes(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent notes up to limit."""
        docs = self.client.collection("notes").stream()
        notes = [doc.to_dict() for doc in docs if doc.to_dict()]
        usage_tracker.record_tool_call("firestore")
        sorted_notes = sorted(notes, key=lambda x: x.get("created_at", ""), reverse=True)
        return sorted_notes[:limit]

    def search_notes(self, query: str) -> List[Dict[str, Any]]:
        """Search notes by keyword in title, content, or tags."""
        q = query.lower()
        all_notes = self.get_notes(limit=100)
        matches = [
            n for n in all_notes
            if q in n.get("title", "").lower() or q in n.get("content", "").lower() or any(q in t for t in n.get("tags", []))
        ]
        return matches

    def delete_note(self, note_id: str) -> bool:
        """Delete a note document by ID."""
        doc_ref = self.client.collection("notes").document(note_id)
        doc = doc_ref.get()
        if doc and doc.exists:
            doc_ref.delete()
            usage_tracker.record_tool_call("firestore")
            logger.info("Firestore note deleted: %s", note_id)
            return True
        return False


# Global singleton instance
firestore_service = FirestoreService()
