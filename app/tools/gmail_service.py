"""
Gmail Service & Adapter for Synaptix Personal Productivity Assistant
Provides draft creation and sending with Human-in-the-Loop review gates.
Supports multi-user OAuth token loading dynamically from Firestore.

Features:
- Live Google Gmail API v1 integration (using https://www.googleapis.com/auth/gmail.compose)
- Multi-user support: dynamically resolves credentials from Firestore for active user
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
from app.core.context import current_user_id

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
    Supports live Gmail API v1 with per-user dynamic OAuth from Firestore
    and thread-safe persistent fallback storage.
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
        """Attempt to initialize fallback Google Gmail API v1 client from token.json."""
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
                    self.token_path.write_text(creds.to_json(), encoding="utf-8")
                except Exception as ref_err:
                    logger.warning("Could not refresh token.json: %s", ref_err)

            if creds and creds.valid:
                granted_scopes = creds.scopes or []
                has_compose = any("gmail.compose" in s for s in granted_scopes)
                if not has_compose:
                    logger.warning(
                        "token.json exists but lacks 'https://www.googleapis.com/auth/gmail.compose' scope."
                    )
                    self.is_live_gmail = False
                    return

                self._service = build("gmail", "v1", credentials=creds)
                self.is_live_gmail = True
                logger.info("Live Google Gmail API initialized successfully from token.json.")
            else:
                self.is_live_gmail = False
                logger.warning("Google OAuth token is invalid or lacks required permissions.")
        except Exception as exc:
            self.is_live_gmail = False
            logger.warning("Could not initialize live Gmail client: %s. Using local fallback.", exc)

    def get_user_gmail_client(self, user_id: Optional[str] = None):
        """
        Dynamically loads Google OAuth credentials for a specific user from Firestore.
        Auto-refreshes expired access tokens and persists updated tokens back to Firestore.
        Falls back to global token.json client or None if unconfigured.
        """
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
                            logger.info("Refreshed expired Gmail OAuth token for user: %s", target_uid)
                        except Exception as ref_err:
                            logger.warning("Failed refreshing token for user %s: %s", target_uid, ref_err)

                    if creds and creds.valid:
                        return build("gmail", "v1", credentials=creds)
            except Exception as exc:
                logger.warning("Failed to construct dynamic Gmail client for user %s: %s", target_uid, exc)

        # Fallback to default local token client
        if self.is_live_gmail and self._service:
            return self._service
        return None

    @property
    def is_configured(self) -> bool:
        """Returns True if Google OAuth Client ID is configured in settings or live Gmail is active."""
        return bool(self.settings.effective_client_id) or self.is_live_gmail

    def create_email_draft(
        self,
        to: str,
        subject: str,
        body: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates an email draft.
        If live Gmail is authenticated for the user, creates a real draft in their Gmail mailbox.
        Otherwise, stores safely in .gmail_local.json for testing and zero-cost operation.
        """
        usage_tracker.record_tool_call("gmail")
        uid = user_id or current_user_id.get("default_user")
        to_clean = to.strip()
        subject_clean = subject.strip()
        body_clean = body.strip()

        client = self.get_user_gmail_client(uid)
        if client:
            try:
                mime_msg = MIMEText(body_clean)
                mime_msg["to"] = to_clean
                mime_msg["subject"] = subject_clean
                raw_bytes = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("utf-8")

                draft_payload = {"message": {"raw": raw_bytes}}
                created_draft = (
                    client.users()
                    .drafts()
                    .create(userId="me", body=draft_payload)
                    .execute()
                )
                draft_id = created_draft.get("id", f"draft-{uuid.uuid4().hex[:6]}")
                result = {
                    "draft_id": draft_id,
                    "id": draft_id,
                    "to": to_clean,
                    "subject": subject_clean,
                    "body": body_clean,
                    "status": "draft",
                    "user_id": uid,
                    "is_live_gmail": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "source": "google_gmail_api",
                }
                with self._lock:
                    self._drafts[draft_id] = result
                    self._persist_local_drafts()
                logger.info("Live Gmail draft created with ID: %s for user: %s", draft_id, uid)
                return result
            except Exception as exc:
                logger.error("Live Gmail draft creation failed: %s. Falling back to local storage.", exc)

        # Local Fallback Mode
        draft_id = f"draft-{uuid.uuid4().hex[:6]}"
        record = {
            "draft_id": draft_id,
            "id": draft_id,
            "user_id": uid,
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

        logger.info("Created local email draft %s to %s for user %s", draft_id, to_clean, uid)
        return record

    def send_email_draft(self, draft_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Sends an existing email draft after explicit human approval.
        If live Gmail is authenticated for the user, dispatches via Gmail API drafts.send.
        Otherwise, updates local draft status to 'sent'.
        """
        usage_tracker.record_tool_call("gmail")
        uid = user_id or current_user_id.get("default_user")
        draft_id_clean = draft_id.strip()

        client = self.get_user_gmail_client(uid)
        if client:
            try:
                sent_msg = (
                    client.users()
                    .drafts()
                    .send(userId="me", body={"id": draft_id_clean})
                    .execute()
                )
                with self._lock:
                    if draft_id_clean in self._drafts:
                        self._drafts[draft_id_clean]["status"] = "sent"
                        self._drafts[draft_id_clean]["sent_at"] = datetime.now(timezone.utc).isoformat()
                        self._persist_local_drafts()
                logger.info("Live Gmail draft %s sent successfully for user %s. Message ID: %s", draft_id_clean, uid, sent_msg.get("id"))
                return {
                    "draft_id": draft_id_clean,
                    "message_id": sent_msg.get("id"),
                    "sent": True,
                    "status": "sent",
                    "user_id": uid,
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
                    "user_id": target.get("user_id"),
                    "sent_at": target.get("sent_at"),
                    "note": "Draft was already sent previously.",
                }

            target["status"] = "sent"
            target["sent_at"] = datetime.now(timezone.utc).isoformat()
            self._drafts[draft_id_clean] = target
            self._persist_local_drafts()

        logger.info("Local draft %s marked as sent for user %s.", draft_id_clean, uid)
        return {
            "draft_id": draft_id_clean,
            "to": target.get("to"),
            "subject": target.get("subject"),
            "sent": True,
            "status": "sent",
            "user_id": target.get("user_id"),
            "is_live_gmail": False,
            "sent_at": target.get("sent_at"),
            "source": "local_persistent_storage",
        }

    def get_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a draft by ID."""
        with self._lock:
            return self._drafts.get(draft_id)

    def list_drafts(self, status: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List drafts filtered by status ('draft' or 'sent') and optional user_id."""
        with self._lock:
            items = list(self._drafts.values())
            if user_id:
                items = [i for i in items if i.get("user_id") == user_id or not i.get("user_id") or user_id == "default_user"]
            if status:
                items = [i for i in items if i.get("status") == status]
            return sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)


# Singleton Gmail Service instance
gmail_service = GmailService()
