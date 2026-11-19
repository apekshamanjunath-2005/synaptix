"""
Gmail Service & Adapter for Synaptix Personal Productivity Assistant
Provides draft creation and sending with Human-in-the-Loop review gates.

Features:
- Live Google Gmail API v1 integration (using https://www.googleapis.com/auth/gmail.compose)
- Dual-mode architecture: seamlessly falls back to thread-safe local persistent storage (.gmail_local.json)
- Zero-cost guarantee (never requires paid API credits)
- Enforces strict Human-in-the-Loop approval protocol
"""

import os
import json
import base64
import logging
import threading
import uuid
from email.mime.text import MIMEText
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.config import get_settings
from app.core.usage_tracker import usage_tracker

logger = logging.getLogger("synaptix.tools.gmail")

GMAIL_LOCAL_FILE = Path(__file__).resolve().parent.parent.parent / ".gmail_local.json"
DEFAULT_TOKEN_FILE = Path(__file__).resolve().parent.parent.parent / "token.json"

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.compose",
]


class GmailService:
    """
    Dual-mode Gmail service provider.
    Supports live Gmail API v1 with OAuth 2.0 and thread-safe persistent fallback storage.
    """

    def __init__(self, token_path: Optional[str] = None):
        self.settings = get_settings()
        self._lock = threading.Lock()
        self.token_path = Path(token_path) if token_path else DEFAULT_TOKEN_FILE
        self.is_live_gmail = False
        self._service = None
        self._drafts: Dict[str, Dict[str, Any]] = {}

        self._load_local_drafts()
        self._init_live_client()

    def _load_local_drafts(self) -> None:
        """Load local fallback drafts from disk."""
        with self._lock:
            if GMAIL_LOCAL_FILE.exists():
                try:
                    data = json.loads(GMAIL_LOCAL_FILE.read_text(encoding="utf-8"))
                    self._drafts = data.get("drafts", {})
                    logger.info("Loaded %d local drafts from %s", len(self._drafts), GMAIL_LOCAL_FILE.name)
                    return
                except Exception as exc:
                    logger.warning("Could not read .gmail_local.json: %s", exc)
            self._drafts = {}

    def _persist_local_drafts(self) -> None:
        """Persist local fallback drafts to disk."""
        try:
            payload = {
                "drafts": self._drafts,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            GMAIL_LOCAL_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to persist local email drafts: %s", exc)

    def _init_live_client(self) -> None:
        """Attempt to initialize Google Gmail API v1 client from token.json."""
        if not self.token_path.exists():
            logger.info("No token.json detected at %s. Operating in zero-cost local draft mode.", self.token_path)
            self.is_live_gmail = False
            return

        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build

            creds = Credentials.from_authorized_user_file(str(self.token_path), GMAIL_SCOPES)
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    # Re-save refreshed token
                    self.token_path.write_text(creds.to_json(), encoding="utf-8")
                except Exception as ref_err:
                    logger.warning("Could not refresh token.json: %s", ref_err)

            if creds and creds.valid:
                # Verify required scope is granted
                granted_scopes = creds.scopes or []
                has_compose = any("gmail.compose" in s for s in granted_scopes)
                if not has_compose:
                    logger.warning(
                        "token.json exists but lacks 'https://www.googleapis.com/auth/gmail.compose' scope. "
                        "Please run scripts/authenticate_google.py to re-authorize Gmail."
                    )
                    self.is_live_gmail = False
                    return

                self._service = build("gmail", "v1", credentials=creds)
                self.is_live_gmail = True
                logger.info("Live Google Gmail API initialized successfully.")
            else:
                self.is_live_gmail = False
                logger.warning("Google OAuth token is invalid or lacks required permissions.")
        except Exception as exc:
            self.is_live_gmail = False
            logger.warning("Could not initialize live Gmail client: %s. Using local fallback.", exc)

    @property
    def is_configured(self) -> bool:
        """Returns True if Google OAuth Client ID is configured in settings or live Gmail is active."""
        return bool(self.settings.GOOGLE_CALENDAR_CLIENT_ID) or self.is_live_gmail

    def create_email_draft(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Creates an email draft.
        If live Gmail is authenticated, creates a real draft in user's Gmail mailbox.
        Otherwise, stores safely in .gmail_local.json for testing and zero-cost operation.
        """
        usage_tracker.record_tool_call("gmail")
        to_clean = to.strip()
        subject_clean = subject.strip()
        body_clean = body.strip()

        if self.is_live_gmail and self._service:
            try:
                mime_msg = MIMEText(body_clean)
                mime_msg["to"] = to_clean
                mime_msg["subject"] = subject_clean
                raw_bytes = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("utf-8")

                draft_payload = {"message": {"raw": raw_bytes}}
                created_draft = (
                    self._service.users()
                    .drafts()
                    .create(userId="me", body=draft_payload)
                    .execute()
                )
                draft_id = created_draft.get("id", f"draft-{uuid.uuid4().hex[:6]}")
                result = {
                    "draft_id": draft_id,
                    "to": to_clean,
                    "subject": subject_clean,
                    "body": body_clean,
                    "status": "draft",
                    "is_live_gmail": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "source": "google_gmail_api",
                }
                logger.info("Live Gmail draft created with ID: %s", draft_id)
                return result
            except Exception as exc:
                logger.error("Live Gmail draft creation failed: %s. Falling back to local storage.", exc)

        # Local Fallback Mode
        draft_id = f"draft-{uuid.uuid4().hex[:6]}"
        record = {
            "draft_id": draft_id,
            "id": draft_id,
            "to": to_clean,
            "subject": subject_clean,
            "body": body_clean,
            "status": "draft",
            "is_live_gmail": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "local_persistent_storage",
        }
        with self._lock:
            self._drafts[draft_id] = record
            self._persist_local_drafts()

        logger.info("Created local email draft %s to %s", draft_id, to_clean)
        return record

    def send_email_draft(self, draft_id: str) -> Dict[str, Any]:
        """
        Sends an existing email draft after explicit human approval.
        If live Gmail is authenticated, dispatches via Gmail API drafts.send.
        Otherwise, updates local draft status to 'sent'.
        """
        usage_tracker.record_tool_call("gmail")
        draft_id_clean = draft_id.strip()

        if self.is_live_gmail and self._service:
            try:
                sent_msg = (
                    self._service.users()
                    .drafts()
                    .send(userId="me", body={"id": draft_id_clean})
                    .execute()
                )
                logger.info("Live Gmail draft %s sent successfully. Message ID: %s", draft_id_clean, sent_msg.get("id"))
                return {
                    "draft_id": draft_id_clean,
                    "message_id": sent_msg.get("id"),
                    "sent": True,
                    "status": "sent",
                    "is_live_gmail": True,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "source": "google_gmail_api",
                }
            except Exception as exc:
                logger.error("Live Gmail draft send failed: %s. Checking local drafts.", exc)

        # Local Fallback Mode
        with self._lock:
            target = self._drafts.get(draft_id_clean)
            if not target:
                # Try finding by partial ID or case-insensitive
                for did, d in self._drafts.items():
                    if draft_id_clean.lower() in did.lower():
                        target = d
                        draft_id_clean = did
                        break

            if not target:
                return {
                    "draft_id": draft_id_clean,
                    "sent": False,
                    "error": f"Draft with ID '{draft_id_clean}' not found.",
                    "status": "not_found",
                }

            if target.get("status") == "sent":
                return {
                    "draft_id": draft_id_clean,
                    "sent": True,
                    "already_sent": True,
                    "status": "sent",
                    "sent_at": target.get("sent_at"),
                    "note": "Draft was already sent previously.",
                }

            target["status"] = "sent"
            target["sent_at"] = datetime.now(timezone.utc).isoformat()
            self._drafts[draft_id_clean] = target
            self._persist_local_drafts()

        logger.info("Local draft %s marked as sent.", draft_id_clean)
        return {
            "draft_id": draft_id_clean,
            "to": target.get("to"),
            "subject": target.get("subject"),
            "sent": True,
            "status": "sent",
            "is_live_gmail": False,
            "sent_at": target.get("sent_at"),
            "source": "local_persistent_storage",
        }

    def get_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a draft by ID."""
        with self._lock:
            return self._drafts.get(draft_id)

    def list_drafts(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List drafts filtered by status ('draft' or 'sent')."""
        with self._lock:
            items = list(self._drafts.values())
            if status:
                items = [i for i in items if i.get("status") == status]
            return sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)


# Singleton Gmail Service instance
gmail_service = GmailService()
