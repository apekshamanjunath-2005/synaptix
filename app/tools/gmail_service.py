"""
Gmail Service & Adapter for Synaptix Personal Productivity Assistant
Provides draft creation and sending with Human-in-the-Loop review gates.
Supports multi-user OAuth token loading dynamically from Firestore,
Render environment variables (GOOGLE_TOKEN_JSON / GMAIL_TOKEN_JSON),
and Render Secret Files (/etc/secrets/token.json) with automatic in-memory token refresh.

Features:
- Live Google Gmail API v1 integration (using https://www.googleapis.com/auth/gmail.compose)
- Multi-user support: dynamically resolves credentials from Firestore for active user
- Production Render support: loads GOOGLE_TOKEN_JSON or /etc/secrets/token.json with in-memory refresh
- Dual-mode architecture: seamlessly falls back to local storage in MOCK_MODE for tests
- Explicit error reporting: never falsely claims an email was sent if Gmail API is disconnected
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
from app.tools.google_auth_helper import get_live_google_credentials, refresh_credentials_in_memory

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
    Supports live Gmail API v1 with per-user dynamic OAuth from Firestore,
    production environment variable / secret file credentials, and local fallback storage.
    """

    def __init__(self, token_path: Optional[str] = None):
        self.settings = get_settings()
        self._lock = threading.Lock()
        self.token_path = Path(token_path) if token_path else DEFAULT_TOKEN_FILE
        self._drafts: Dict[str, Dict[str, Any]] = {}

        self._load_local_drafts()

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

    def get_user_gmail_client(self, user_id: Optional[str] = None):
        """
        Dynamically loads Google OAuth credentials with in-memory token refresh.
        Checks active user's Firestore tokens, GOOGLE_TOKEN_JSON env, Render Secret Files, or local token.json.
        Returns active googleapiclient Gmail v1 Resource if available, else None.
        """
        if self.settings.MOCK_MODE or os.getenv("MOCK_MODE", "").lower() == "true":
            return None

        target_uid = user_id or current_user_id.get("default_user")
        creds, source = get_live_google_credentials(target_uid, GMAIL_SCOPES)
        if creds and creds.valid:
            try:
                from googleapiclient.discovery import build
                client = build("gmail", "v1", credentials=creds)
                return client
            except Exception as exc:
                logger.error("Failed to construct Gmail API client from %s: %s", source, exc)
        return None

    @property
    def is_live_gmail(self) -> bool:
        """Returns True if live Gmail credentials can be resolved."""
        if self.settings.MOCK_MODE or os.getenv("MOCK_MODE", "").lower() == "true":
            return False
        client = self.get_user_gmail_client()
        return client is not None

    @property
    def is_configured(self) -> bool:
        """Returns True if Google OAuth credentials exist in any layer."""
        return self.is_live_gmail or bool(self.settings.effective_client_id)

    def get_connection_status(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Diagnostic helper returning detailed connection state for the active user."""
        target_uid = user_id or current_user_id.get("default_user")
        creds, source = get_live_google_credentials(target_uid, GMAIL_SCOPES)
        if creds and creds.valid:
            email_addr = None
            try:
                from googleapiclient.discovery import build
                srv = build("gmail", "v1", credentials=creds)
                profile = srv.users().getProfile(userId="me").execute()
                email_addr = profile.get("emailAddress")
            except Exception as exc:
                logger.debug("Could not fetch Gmail profile: %s", exc)

            granted = creds.scopes or []
            has_compose = any("gmail.compose" in s for s in granted)
            return {
                "is_live_gmail": True,
                "can_send": has_compose,
                "email": email_addr,
                "source": source,
                "user_id": target_uid,
                "scopes": granted,
                "message": f"Connected to Live Gmail as {email_addr}" if email_addr else "Connected to Live Google Gmail API.",
            }

        return {
            "is_live_gmail": False,
            "can_send": False,
            "email": None,
            "source": "offline_simulator",
            "user_id": target_uid,
            "message": "Live Gmail is not connected. Sign in with Google or configure GOOGLE_TOKEN_JSON on Render.",
        }

    def create_email_draft(
        self,
        to: str,
        subject: str,
        body: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates an email draft.
        If in live production with credentials, creates a real draft in the user's Gmail mailbox.
        Otherwise (or in MOCK_MODE), stores safely in fallback storage for testing.
        """
        usage_tracker.record_tool_call("gmail")
        uid = user_id or current_user_id.get("default_user")
        to_clean = to.strip()
        subject_clean = subject.strip()
        body_clean = body.strip()

        # In MOCK_MODE or test environment, bypass live external API
        if not (self.settings.MOCK_MODE or os.getenv("MOCK_MODE", "").lower() == "true"):
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
        If MOCK_MODE: simulates dispatch in local store for tests.
        If live Gmail is available:
          - If created in Gmail (starts with 'r'), sends via drafts().send().
          - If created as a local draft (starts with 'draft-'), delivers real email via messages().send().
          - Automatically refreshes token in memory and retries if 401 occurs.
        If live Gmail is NOT available:
          - In Production: returns sent: False with clear actionable error.
        """
        usage_tracker.record_tool_call("gmail")
        uid = user_id or current_user_id.get("default_user")
        draft_id_clean = draft_id.strip()

        # 1. LOCAL SIMULATOR (ONLY allowed in MOCK_MODE / automated tests)
        if self.settings.MOCK_MODE or os.getenv("MOCK_MODE", "").lower() == "true":
            with self._lock:
                target = self._drafts.get(draft_id_clean)
                if not target:
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

            logger.info("MOCK_MODE: Local draft %s marked as sent for user %s.", draft_id_clean, uid)
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

        # 2. LIVE GMAIL DISPATCH (Production)
        creds, source = get_live_google_credentials(uid, GMAIL_SCOPES)
        client = None
        if creds and creds.valid:
            try:
                from googleapiclient.discovery import build
                client = build("gmail", "v1", credentials=creds)
            except Exception as b_err:
                logger.error("Failed building Gmail API client: %s", b_err)

        if client and creds:
            # Helper to execute with automatic in-memory 401 token refresh retry
            def _execute_with_refresh(build_request_fn):
                nonlocal client, creds
                try:
                    return build_request_fn(client).execute()
                except Exception as exc:
                    err_msg = str(exc)
                    if ("401" in err_msg or "invalid_grant" in err_msg or "expired" in err_msg.lower()) and creds.refresh_token:
                        logger.warning("Gmail API returned auth error (%s). Refreshing token in memory and retrying...", exc)
                        from google.auth.transport.requests import Request
                        creds.refresh(Request())
                        from googleapiclient.discovery import build
                        client = build("gmail", "v1", credentials=creds)
                        return build_request_fn(client).execute()
                    raise

            # Attempt A: Live draft in Gmail mailbox
            if not draft_id_clean.startswith("draft-"):
                try:
                    sent_msg = _execute_with_refresh(
                        lambda c: c.users().drafts().send(userId="me", body={"id": draft_id_clean})
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
                    logger.warning("drafts.send failed for draft %s: %s. Attempting fallback direct message dispatch.", draft_id_clean, exc)

            # Attempt B: Dispatch local draft content via live Gmail messages().send()
            with self._lock:
                target = self._drafts.get(draft_id_clean)
                if not target:
                    for did, d in self._drafts.items():
                        if draft_id_clean.lower() in did.lower():
                            target = d
                            draft_id_clean = did
                            break

            if target and target.get("to") and target.get("body"):
                try:
                    mime_msg = MIMEText(target["body"])
                    mime_msg["to"] = target["to"]
                    mime_msg["subject"] = target.get("subject", "No Subject")
                    raw_bytes = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("utf-8")
                    sent_msg = _execute_with_refresh(
                        lambda c: c.users().messages().send(userId="me", body={"raw": raw_bytes})
                    )
                    with self._lock:
                        target["status"] = "sent"
                        target["sent_at"] = datetime.now(timezone.utc).isoformat()
                        target["message_id"] = sent_msg.get("id")
                        target["is_live_gmail"] = True
                        self._persist_local_drafts()
                    logger.info("Successfully dispatched real email via messages.send for draft %s to %s. Message ID: %s",
                                draft_id_clean, target["to"], sent_msg.get("id"))
                    return {
                        "draft_id": draft_id_clean,
                        "message_id": sent_msg.get("id"),
                        "to": target["to"],
                        "subject": target.get("subject"),
                        "sent": True,
                        "status": "sent",
                        "user_id": uid,
                        "is_live_gmail": True,
                        "sent_at": target["sent_at"],
                        "source": "google_gmail_api",
                    }
                except Exception as send_err:
                    logger.error("messages.send failed for draft %s: %s", draft_id_clean, send_err)
                    return {
                        "draft_id": draft_id_clean,
                        "sent": False,
                        "status": "failed",
                        "error": f"Google Gmail API error while sending: {str(send_err)}",
                        "is_live_gmail": True,
                    }

        # 3. PRODUCTION FAILURE SURFACING: Refuse silent offline fake sends
        logger.error("Cannot send email draft %s: Live Gmail is not connected for user %s.", draft_id_clean, uid)
        return {
            "draft_id": draft_id_clean,
            "sent": False,
            "status": "failed",
            "error": "Live Gmail is not connected. Please connect Google OAuth or configure GOOGLE_TOKEN_JSON in Render environment variables.",
            "is_live_gmail": False,
        }

    def get_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a draft by ID."""
        with self._lock:
            return self._drafts.get(draft_id)

    def list_drafts(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List drafts filtered by user."""
        uid = user_id or current_user_id.get("default_user")
        with self._lock:
            items = []
            for did, d in self._drafts.items():
                if d.get("user_id") == uid or uid == "default_user":
                    items.append(d.copy())
            return sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)


gmail_service = GmailService()
