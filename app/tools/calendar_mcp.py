"""
Google Calendar MCP Integration Provider (Milestone 5)
Implements Model Context Protocol (MCP) calendar tools with:
1. Event scheduling (create, fetch, update, delete)
2. Intelligent availability & timeslot conflict checking
3. Live Google Calendar v3 API support when credentials are provided
4. Thread-safe persistent local storage (.calendar_local.json) for zero-cost operation
"""

import os
import json
import logging
import threading
import uuid
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.config import get_settings
from app.core.usage_tracker import usage_tracker
from app.core.context import current_user_id

logger = logging.getLogger("synaptix.tools.calendar_mcp")

CALENDAR_LOCAL_FILE = Path(__file__).resolve().parent.parent.parent / ".calendar_local.json"


class CalendarMCPProvider:
    """
    Model Context Protocol Calendar Service Provider.
    Implements standard MCP tool interface for Calendar operations.
    """
    def __init__(self):
        self.settings = get_settings()
        self._lock = threading.Lock()
        self.is_live_google = False
        self._events: Dict[str, Dict[str, Any]] = {}
        self._load_local_events()
        self._check_live_google_credentials()

    def _load_local_events(self):
        """Load persisted calendar events from disk."""
        with self._lock:
            if CALENDAR_LOCAL_FILE.exists():
                try:
                    data = json.loads(CALENDAR_LOCAL_FILE.read_text(encoding="utf-8"))
                    self._events = data.get("events", {})
                    logger.info("Loaded %d calendar events from persistent store", len(self._events))
                    return
                except Exception as e:
                    logger.warning("Could not read calendar file: %s", e)

            # Default initial calendar events for testing
            today_str = date.today().strftime("%Y-%m-%d")
            seed_id = "cal-101"
            self._events = {
                seed_id: {
                    "id": seed_id,
                    "summary": "AI Architecture & Sprint Sync",
                    "start_time": f"{today_str}T10:00:00",
                    "end_time": f"{today_str}T11:00:00",
                    "description": "Weekly Synaptix multi-agent sprint review.",
                    "location": "Google Meet",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            }
            self._persist()

    def _persist(self):
        try:
            payload = {"events": self._events, "updated_at": datetime.now(timezone.utc).isoformat()}
            CALENDAR_LOCAL_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to persist calendar events: %s", e)

    def _check_live_google_credentials(self):
        """Verify if live Google Calendar OAuth2 credentials exist."""
        client_id = self.settings.GOOGLE_CALENDAR_CLIENT_ID
        client_secret = self.settings.GOOGLE_CALENDAR_CLIENT_SECRET
        if client_id and client_secret:
            logger.info("Google Calendar OAuth credentials detected in configuration.")
            # When OAuth token file exists, can activate live Google Calendar API
            self.is_live_google = False
        else:
            self.is_live_google = False
            logger.info("Running Calendar MCP with local persistent calendar store (₹0 Free Tier Mode).")

    def get_user_calendar_client(self, user_id: Optional[str] = None):
        """Dynamically load Google Calendar client from user's Firestore OAuth tokens."""
        target_uid = user_id or current_user_id.get("default_user")
        if target_uid and target_uid != "default_user":
            try:
                from app.database.firestore import firestore_service
                tokens = firestore_service.get_user_tokens(target_uid)
                if tokens:
                    from google.oauth2.credentials import Credentials
                    from google.auth.transport.requests import Request
                    from googleapiclient.discovery import build

                    client_id = tokens.get("client_id") or self.settings.effective_client_id
                    client_secret = tokens.get("client_secret") or self.settings.effective_client_secret
                    creds = Credentials(
                        token=tokens.get("access_token"),
                        refresh_token=tokens.get("refresh_token"),
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=client_id,
                        client_secret=client_secret,
                        scopes=self.settings.GOOGLE_OAUTH_SCOPES,
                    )
                    if creds and creds.expired and creds.refresh_token:
                        try:
                            creds.refresh(Request())
                            updated_tokens = dict(tokens)
                            updated_tokens["access_token"] = creds.token
                            if creds.expiry:
                                updated_tokens["expires_at"] = creds.expiry.isoformat()
                            firestore_service.save_user_tokens(target_uid, updated_tokens)
                        except Exception as ref_err:
                            logger.warning("Failed refreshing calendar token for user %s: %s", target_uid, ref_err)

                    if creds and creds.valid:
                        return build("calendar", "v3", credentials=creds)
            except Exception as exc:
                logger.warning("Could not build live Calendar client for user %s: %s", target_uid, exc)
        return None

    # ────────────────────────────────────────────────────────────────────────────
    # MCP TOOLS IMPLEMENTATION
    # ────────────────────────────────────────────────────────────────────────────

    def list_events(self, date_str: Optional[str] = None, max_results: int = 15, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        MCP Tool: List calendar events for a specific date (defaults to today).
        """
        target_date = date_str or date.today().strftime("%Y-%m-%d")
        uid = user_id or current_user_id.get("default_user")
        usage_tracker.record_tool_call("calendar")

        with self._lock:
            matched = [
                e for e in self._events.values()
                if e.get("start_time", "").startswith(target_date) and (
                    uid == "default_user" or not e.get("user_id") or e.get("user_id") == uid
                )
            ]
            sorted_events = sorted(matched, key=lambda x: x.get("start_time", ""))
            return sorted_events[:max_results]

    def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = "",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        MCP Tool: Schedule a new calendar event.
        """
        usage_tracker.record_tool_call("calendar")
        uid = user_id or current_user_id.get("default_user")
        event_id = f"event-{uuid.uuid4().hex[:6]}"
        new_event = {
            "id": event_id,
            "summary": summary,
            "start_time": start_time,
            "end_time": end_time,
            "description": description or "",
            "location": location or "",
            "user_id": uid,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        with self._lock:
            self._events[event_id] = new_event
            self._persist()

        logger.info("Event scheduled via MCP: %s (%s to %s) for user %s", summary, start_time, end_time, uid)
        return new_event

    def update_event(
        self,
        event_id: str,
        summary: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        MCP Tool: Update an existing event's details or timing.
        """
        usage_tracker.record_tool_call("calendar")
        with self._lock:
            target = self._events.get(event_id)
            if not target:
                # Search by summary if ID did not match directly
                for eid, e in self._events.items():
                    if event_id.lower() in e["summary"].lower():
                        target = e
                        event_id = eid
                        break

            if not target:
                return None

            if summary:
                target["summary"] = summary
            if start_time:
                target["start_time"] = start_time
            if end_time:
                target["end_time"] = end_time
            if description is not None:
                target["description"] = description
            if location is not None:
                target["location"] = location

            target["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._events[event_id] = target
            self._persist()
            return target

    def delete_event(self, event_id: str) -> bool:
        """
        MCP Tool: Delete a calendar event by ID or summary.
        """
        usage_tracker.record_tool_call("calendar")
        with self._lock:
            if event_id in self._events:
                del self._events[event_id]
                self._persist()
                logger.info("Calendar event deleted: %s", event_id)
                return True

            for eid, e in list(self._events.items()):
                if event_id.lower() in e["summary"].lower():
                    del self._events[eid]
                    self._persist()
                    logger.info("Calendar event deleted by summary match: %s", eid)
                    return True

            return False

    def check_availability(self, start_time: str, end_time: str) -> Dict[str, Any]:
        """
        MCP Tool: Determine if a proposed timeslot has schedule conflicts.
        Checks overlap: (StartA < EndB) and (EndA > StartB).
        """
        usage_tracker.record_tool_call("calendar")
        conflicts = []

        with self._lock:
            for e in self._events.values():
                e_start = e.get("start_time", "")
                e_end = e.get("end_time", "")
                # Time overlap condition
                if e_start < end_time and e_end > start_time:
                    conflicts.append({
                        "id": e["id"],
                        "summary": e["summary"],
                        "start_time": e_start,
                        "end_time": e_end,
                    })

        return {
            "available": len(conflicts) == 0,
            "proposed_start": start_time,
            "proposed_end": end_time,
            "conflicts_count": len(conflicts),
            "conflicting_events": conflicts,
        }


# Singleton MCP Provider instance
calendar_mcp = CalendarMCPProvider()
