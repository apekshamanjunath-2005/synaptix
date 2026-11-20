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
from datetime import datetime, timezone, timedelta
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

    def set(self, data: dict, merge: bool = False):
        with self._lock:
            if self.collection_name not in self._storage:
                self._storage[self.collection_name] = {}
            if merge and self.id in self._storage[self.collection_name]:
                self._storage[self.collection_name][self.id].update(data)
            else:
                self._storage[self.collection_name][self.id] = data
            self._persist()

    def collection(self, sub_collection_name: str):
        sub_key = f"{self.collection_name}/{self.id}/{sub_collection_name}"
        return LocalFirestoreCollection(sub_key, self._storage, self._lock)

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
        self._storage: Dict[str, Dict[str, Any]] = {"tasks": {}, "notes": {}, "day_plans": {}, "reminders": {}}
        self._load()

    def _load(self):
        if LOCAL_DB_FILE.exists():
            try:
                data = json.loads(LOCAL_DB_FILE.read_text(encoding="utf-8"))
                self._storage.update(data)
                logger.info("Loaded persisted Local Firestore from disk (%d tasks, %d notes, %d day_plans, %d reminders)",
                            len(self._storage.get("tasks", {})), len(self._storage.get("notes", {})), len(self._storage.get("day_plans", {})), len(self._storage.get("reminders", {})))
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

        PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
        cred_path = self.settings.FIREBASE_CREDENTIALS_PATH
        resolved_cred = None

        if cred_path:
            p = Path(cred_path)
            if p.is_file():
                resolved_cred = str(p.resolve())
            elif (PROJECT_ROOT / cred_path).is_file():
                resolved_cred = str((PROJECT_ROOT / cred_path).resolve())

        # Also auto-detect standard credential files in project root
        if not resolved_cred:
            for candidate in ["firebase-key.json", "firebase-key.json.json", "serviceAccountKey.json"]:
                cp = PROJECT_ROOT / candidate
                if cp.is_file():
                    resolved_cred = str(cp.resolve())
                    break

        if resolved_cred:
            try:
                if not firebase_admin._apps:
                    cred = credentials.Certificate(resolved_cred)
                    project_id = self.settings.FIREBASE_PROJECT_ID
                    init_opts = {"projectId": project_id} if project_id else {}
                    firebase_admin.initialize_app(cred, init_opts)
                self.client = firestore.client()
                self.is_live_firebase = True
                logger.info("✅ Connected to Live Firebase Firestore (Project: %s, File: %s)",
                            self.settings.FIREBASE_PROJECT_ID or "Default", Path(resolved_cred).name)
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
        status: str = "pending",
        user_id: Optional[str] = None
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
            "user_id": user_id or "default_user",
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        self.client.collection("tasks").document(task_id).set(task_data)
        usage_tracker.record_tool_call("firestore")
        logger.info("Firestore task added: %s (%s) for user %s", title, task_id, task_data["user_id"])
        return task_data

    def get_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve tasks with optional status, priority, and user_id filtering."""
        docs = self.client.collection("tasks").stream()
        tasks = []
        for doc in docs:
            t = doc.to_dict()
            if not t:
                continue
            if user_id and t.get("user_id") != user_id:
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
        if isinstance(task_id, dict):
            task_id = str(task_id.get("id", ""))
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
        tags: Optional[List[str]] = None,
        user_id: Optional[str] = None
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
            "user_id": user_id or "default_user",
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        self.client.collection("notes").document(note_id).set(note_data)
        usage_tracker.record_tool_call("firestore")
        logger.info("Firestore note added: %s (%s) for user %s", note_title, note_id, note_data["user_id"])
        return note_data

    def get_notes(self, limit: int = 20, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve recent notes up to limit with optional user_id filtering."""
        docs = self.client.collection("notes").stream()
        notes = []
        for doc in docs:
            n = doc.to_dict()
            if not n:
                continue
            if user_id and n.get("user_id") != user_id:
                continue
            notes.append(n)
        usage_tracker.record_tool_call("firestore")
        sorted_notes = sorted(notes, key=lambda x: x.get("created_at", ""), reverse=True)
        return sorted_notes[:limit]

    def search_notes(self, query: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search notes by keyword in title, content, or tags with optional user_id filtering."""
        q = query.lower()
        all_notes = self.get_notes(limit=100, user_id=user_id)
        matches = [
            n for n in all_notes
            if q in n.get("title", "").lower() or q in n.get("content", "").lower() or any(q in t for t in n.get("tags", []))
        ]
        return matches

    def delete_note(self, note_id: str) -> bool:
        """Delete a note document by ID."""
        if isinstance(note_id, dict):
            note_id = str(note_id.get("id", ""))
        doc_ref = self.client.collection("notes").document(note_id)
        doc = doc_ref.get()
        if doc and doc.exists:
            doc_ref.delete()
            usage_tracker.record_tool_call("firestore")
            logger.info("Firestore note deleted: %s", note_id)
            return True
        return False

    # ────────────────────────────────────────────────────────────────────────────
    # USER OAUTH & PROFILE REPOSITORY (Multi-User Google Login)
    # ────────────────────────────────────────────────────────────────────────────

    def save_user_tokens(self, user_id: str, tokens: Dict[str, Any]) -> None:
        """Store user's OAuth tokens under users/{user_id}/oauth_tokens/credentials."""
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            "tokens": tokens,
            "updated_at": now_iso,
        }
        self.client.collection("users").document(user_id).collection("oauth_tokens").document("credentials").set(payload)
        usage_tracker.record_tool_call("firestore")
        logger.info("Saved OAuth tokens for user: %s", user_id)

    def get_user_tokens(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user's OAuth tokens from users/{user_id}/oauth_tokens/credentials."""
        doc = self.client.collection("users").document(user_id).collection("oauth_tokens").document("credentials").get()
        if doc and doc.exists:
            data = doc.to_dict()
            usage_tracker.record_tool_call("firestore")
            return data.get("tokens") if data else None
        return None

    def delete_user_tokens(self, user_id: str) -> bool:
        """Remove user's stored OAuth credentials."""
        doc_ref = self.client.collection("users").document(user_id).collection("oauth_tokens").document("credentials")
        doc = doc_ref.get()
        if doc and doc.exists:
            doc_ref.delete()
            usage_tracker.record_tool_call("firestore")
            logger.info("Deleted OAuth tokens for user: %s", user_id)
            return True
        return False

    def save_user_profile(self, user_id: str, profile: Dict[str, Any]) -> None:
        """Store user profile under users/{user_id}."""
        now_iso = datetime.now(timezone.utc).isoformat()
        doc_data = {
            "user_id": user_id,
            "email": profile.get("email"),
            "name": profile.get("name"),
            "picture": profile.get("picture"),
            "updated_at": now_iso,
        }
        self.client.collection("users").document(user_id).set(doc_data)
        usage_tracker.record_tool_call("firestore")
        logger.info("Saved profile for user: %s (%s)", user_id, profile.get("email"))

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user profile from users/{user_id}."""
        doc = self.client.collection("users").document(user_id).get()
        if doc and doc.exists:
            usage_tracker.record_tool_call("firestore")
            return doc.to_dict()
        return None

    # ────────────────────────────────────────────────────────────────────────────
    # DAY PLANS REPOSITORY (Per-User Smart Day Plan Persistence)
    # ────────────────────────────────────────────────────────────────────────────

    def save_day_plan(
        self,
        user_id: str,
        date_str: str,
        plan_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Upsert a day plan document in the 'day_plans' collection, keyed by '{user_id}_{date_str}'.
        Ensures strict user scoping and persistence across reloads.
        """
        effective_uid = user_id or "default_user"
        doc_id = f"{effective_uid}_{date_str}"
        now_iso = datetime.now(timezone.utc).isoformat()

        doc_payload = {
            "id": doc_id,
            "user_id": effective_uid,
            "date": date_str,
            "plan": plan_data.get("plan") or plan_data.get("formatted_markdown", ""),
            "formatted_markdown": plan_data.get("formatted_markdown") or plan_data.get("plan", ""),
            "timetable": plan_data.get("timetable", []),
            "weather_summary": plan_data.get("weather_summary") or plan_data.get("weather", {}),
            "pending_tasks_count": plan_data.get("pending_tasks_count", 0),
            "scheduled_events_count": plan_data.get("scheduled_events_count", 0),
            "productivity_insights": plan_data.get("productivity_insights", []),
            "created_at": plan_data.get("created_at", now_iso),
            "updated_at": now_iso,
        }

        self.client.collection("day_plans").document(doc_id).set(doc_payload)
        usage_tracker.record_tool_call("firestore")
        logger.info("Saved day plan for user %s on %s (doc: %s)", effective_uid, date_str, doc_id)
        return doc_payload

    def get_day_plan(self, user_id: str, date_str: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve saved day plan document for a specific user and date.
        """
        effective_uid = user_id or "default_user"
        doc_id = f"{effective_uid}_{date_str}"
        doc = self.client.collection("day_plans").document(doc_id).get()
        if doc and doc.exists:
            usage_tracker.record_tool_call("firestore")
            return doc.to_dict()

        # Fallback stream query if document ID differed
        docs = self.client.collection("day_plans").stream()
        for d in docs:
            data = d.to_dict()
            if data and data.get("user_id") == effective_uid and data.get("date") == date_str:
                usage_tracker.record_tool_call("firestore")
                return data
        return None

    def list_day_plans(self, user_id: str, limit: int = 7) -> List[Dict[str, Any]]:
        """
        Return recent saved day plans for the given user, ordered by date descending.
        """
        effective_uid = user_id or "default_user"
        docs = self.client.collection("day_plans").stream()
        plans = []
        for d in docs:
            data = d.to_dict()
            if data and data.get("user_id") == effective_uid:
                plans.append(data)

        usage_tracker.record_tool_call("firestore")
        sorted_plans = sorted(
            plans,
            key=lambda x: (x.get("date", ""), x.get("updated_at", "")),
            reverse=True
        )
        return sorted_plans[:limit]

    def delete_day_plan(self, user_id: str, date_str: str) -> bool:
        """
        Remove a day plan document for a specific user and date.
        """
        effective_uid = user_id or "default_user"
        doc_id = f"{effective_uid}_{date_str}"
        doc_ref = self.client.collection("day_plans").document(doc_id)
        doc = doc_ref.get()
        if doc and doc.exists:
            doc_ref.delete()
            usage_tracker.record_tool_call("firestore")
            logger.info("Deleted day plan for user %s on %s", effective_uid, date_str)
            return True
        return False

    # ────────────────────────────────────────────────────────────────────────────
    # REMINDERS COLLECTION (Per-User Scoped)
    # ────────────────────────────────────────────────────────────────────────────

    def create_reminder(
        self,
        user_id: str,
        title: str,
        remind_at_iso: str,
        source_type: str = "custom",
        source_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new reminder in Firestore for the given user.
        status defaults to 'pending'.
        """
        effective_uid = user_id or "default_user"
        reminder_id = f"reminder-{uuid.uuid4().hex[:6]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        doc_payload = {
            "id": reminder_id,
            "user_id": effective_uid,
            "title": title,
            "remind_at": remind_at_iso,
            "source_type": source_type or "custom",
            "source_id": source_id,
            "status": "pending",
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        self.client.collection("reminders").document(reminder_id).set(doc_payload)
        usage_tracker.record_tool_call("firestore")
        logger.info("Created reminder %s ('%s') for user %s at %s", reminder_id, title, effective_uid, remind_at_iso)
        return doc_payload

    def list_reminders(
        self,
        user_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all reminders for user, optionally filtered by status ('pending', 'triggered', 'dismissed', 'snoozed').
        Ordered by remind_at ascending.
        """
        effective_uid = user_id or "default_user"
        docs = self.client.collection("reminders").stream()
        reminders = []
        for d in docs:
            data = d.to_dict()
            if data and data.get("user_id") == effective_uid:
                if status is None or data.get("status") == status:
                    reminders.append(data)

        usage_tracker.record_tool_call("firestore")
        sorted_reminders = sorted(reminders, key=lambda x: x.get("remind_at", ""))
        return sorted_reminders

    def get_due_reminders(
        self,
        user_id: str,
        now_iso: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Return all 'pending' and 'snoozed' reminders for user where remind_at <= now_iso.
        """
        effective_uid = user_id or "default_user"
        target_now = now_iso or datetime.now(timezone.utc).isoformat()

        def _to_dt(iso_str: str) -> datetime:
            try:
                clean = iso_str.replace("Z", "+00:00")
                dt = datetime.fromisoformat(clean)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                return datetime.max.replace(tzinfo=timezone.utc)

        threshold_dt = _to_dt(target_now)
        docs = self.client.collection("reminders").stream()
        due_list = []
        for d in docs:
            data = d.to_dict()
            if data and data.get("user_id") == effective_uid:
                if data.get("status") in ("pending", "snoozed"):
                    remind_dt = _to_dt(data.get("remind_at", ""))
                    if remind_dt <= threshold_dt:
                        due_list.append(data)

        usage_tracker.record_tool_call("firestore")
        return sorted(due_list, key=lambda x: x.get("remind_at", ""))

    def update_reminder_status(
        self,
        user_id: str,
        reminder_id: str,
        status: str,
        remind_at_iso: Optional[str] = None,
        snooze_minutes: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update a reminder's status ('triggered', 'dismissed', 'snoozed', 'pending').
        If status is 'snoozed', updates remind_at to remind_at_iso or now + snooze_minutes (default 10m).
        """
        effective_uid = user_id or "default_user"
        doc_ref = self.client.collection("reminders").document(reminder_id)
        doc = doc_ref.get()
        if not doc or not doc.exists:
            return None

        data = doc.to_dict()
        if data.get("user_id") != effective_uid:
            return None

        data["status"] = status
        now = datetime.now(timezone.utc)

        if status == "snoozed":
            if remind_at_iso:
                data["remind_at"] = remind_at_iso
            elif snooze_minutes:
                data["remind_at"] = (now + timedelta(minutes=snooze_minutes)).isoformat()
            else:
                data["remind_at"] = (now + timedelta(minutes=10)).isoformat()

        data["updated_at"] = now.isoformat()
        doc_ref.set(data)
        usage_tracker.record_tool_call("firestore")
        logger.info("Updated reminder %s status to '%s' for user %s", reminder_id, status, effective_uid)
        return data

    def delete_reminder(
        self,
        user_id: str,
        reminder_id: str
    ) -> bool:
        """
        Delete a reminder from Firestore.
        """
        effective_uid = user_id or "default_user"
        doc_ref = self.client.collection("reminders").document(reminder_id)
        doc = doc_ref.get()
        if not doc or not doc.exists:
            return False

        data = doc.to_dict()
        if data.get("user_id") != effective_uid:
            return False

        doc_ref.delete()
        usage_tracker.record_tool_call("firestore")
        logger.info("Deleted reminder %s for user %s", reminder_id, effective_uid)
        return True


# Global singleton instance
firestore_service = FirestoreService()
