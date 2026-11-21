"""
Google OAuth 2.0 Credential Resolution Helper
Loads, validates, and auto-refreshes Google credentials across:
1. Per-user OAuth tokens in Firestore (users/{user_id}/oauth_tokens/credentials)
2. GOOGLE_TOKEN_JSON or GMAIL_TOKEN_JSON environment variables (for Render / Cloud Run)
3. Render Secret Files (/etc/secrets/token.json, /etc/secrets/google_token.json)
4. Local file paths (token.json)

Guarantees:
- If access_token is expired, automatically refreshes in memory using refresh_token before returning.
- If live Firestore is available, persists the refreshed token back to Firestore.
- Thread-safe in-memory caching of refreshed global credentials.
"""

import os
import json
import logging
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.config import get_settings

logger = logging.getLogger("synaptix.tools.auth_helper")

_global_creds_lock = threading.Lock()
_cached_global_creds: Optional[Credentials] = None
_cached_global_source: Optional[str] = None


def _build_creds_from_dict(token_data: Dict[str, Any], scopes: Optional[List[str]] = None) -> Optional[Credentials]:
    """Constructs a Google OAuth Credentials object from a token dictionary."""
    settings = get_settings()
    data = dict(token_data)

    # Standardize access token field name
    if "access_token" in data and "token" not in data:
        data["token"] = data["access_token"]
    elif "token" in data and "access_token" not in data:
        data["access_token"] = data["token"]

    client_id = data.get("client_id") or settings.effective_client_id
    client_secret = data.get("client_secret") or settings.effective_client_secret
    token_uri = data.get("token_uri") or "https://oauth2.googleapis.com/token"

    # Standardize scopes: handle scope string (space-separated) vs scopes list
    raw_scopes = data.get("scopes") or data.get("scope") or scopes or settings.GOOGLE_OAUTH_SCOPES
    if isinstance(raw_scopes, str):
        token_scopes = raw_scopes.split()
    elif isinstance(raw_scopes, list):
        token_scopes = raw_scopes
    else:
        token_scopes = settings.GOOGLE_OAUTH_SCOPES

    data["client_id"] = client_id
    data["client_secret"] = client_secret
    data["token_uri"] = token_uri
    data["scopes"] = token_scopes

    if not data.get("token") and not data.get("refresh_token"):
        return None

    # First attempt: standard Credentials.from_authorized_user_info which parses expiry correctly
    try:
        creds = Credentials.from_authorized_user_info(data, scopes=token_scopes)
        return creds
    except Exception as exc:
        logger.debug("from_authorized_user_info failed, attempting direct Credentials constructor: %s", exc)

    try:
        creds = Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=token_scopes,
        )
        return creds
    except Exception as exc:
        logger.warning("Failed constructing Credentials object: %s", exc)
        return None


def refresh_credentials_in_memory(creds: Optional[Credentials]) -> Tuple[Optional[Credentials], bool]:
    """
    Checks if Google OAuth credentials have expired or are invalid, and
    automatically refreshes the access token in memory using the refresh_token.
    Returns (credentials, refreshed_bool).
    """
    if creds is None:
        return None, False

    if (not creds.valid or creds.expired) and creds.refresh_token:
        try:
            creds.refresh(Request())
            logger.info("Successfully refreshed Google OAuth credentials in-memory using refresh_token.")
            return creds, True
        except Exception as ref_err:
            logger.error("Failed in-memory Google OAuth token refresh: %s", ref_err)
            return creds, False

    return creds, False


def get_live_google_credentials(
    user_id: Optional[str] = None,
    required_scopes: Optional[List[str]] = None
) -> Tuple[Optional[Credentials], str]:
    """
    Resolves live Google OAuth credentials with automatic in-memory token refresh.
    
    Priority:
    1. Active user's OAuth tokens from Firestore
    2. GOOGLE_TOKEN_JSON or GMAIL_TOKEN_JSON environment variable
    3. Render Secret File at /etc/secrets/token.json
    4. Local token.json file in project root
    
    Returns (credentials, source_name).
    """
    settings = get_settings()
    req_scopes = required_scopes or settings.GOOGLE_OAUTH_SCOPES

    # 1. User-specific tokens in Firestore
    target_uid = user_id
    if target_uid and target_uid not in ("default_user", "guest_user"):
        try:
            from app.database.firestore import firestore_service
            tokens = firestore_service.get_user_tokens(target_uid)
            if tokens and isinstance(tokens, dict):
                creds = _build_creds_from_dict(tokens, req_scopes)
                if creds:
                    creds, refreshed = refresh_credentials_in_memory(creds)
                    if refreshed:
                        try:
                            updated = dict(tokens)
                            updated["access_token"] = creds.token
                            if creds.expiry:
                                updated["expires_at"] = creds.expiry.isoformat()
                            firestore_service.save_user_tokens(target_uid, updated)
                            logger.info("Persisted refreshed OAuth token back to Firestore for user %s", target_uid)
                        except Exception as save_err:
                            logger.warning("Could not persist refreshed token to Firestore: %s", save_err)

                    if creds.valid:
                        return creds, f"firestore_user_tokens ({target_uid})"
        except Exception as exc:
            logger.warning("Error resolving Firestore tokens for user %s: %s", target_uid, exc)

    # 2. Global fallback credentials (Render environment variable, Secret File, or local token.json)
    global _cached_global_creds, _cached_global_source

    with _global_creds_lock:
        # Check if already cached and auto-refresh in memory if expired
        if _cached_global_creds and _cached_global_source:
            _cached_global_creds, _ = refresh_credentials_in_memory(_cached_global_creds)
            if _cached_global_creds.valid:
                return _cached_global_creds, _cached_global_source

        # Source A: Environment Variable GOOGLE_TOKEN_JSON or GMAIL_TOKEN_JSON
        for env_key in ("GOOGLE_TOKEN_JSON", "GMAIL_TOKEN_JSON"):
            raw_env = os.getenv(env_key) or getattr(settings, env_key, None)
            if raw_env and raw_env.strip():
                try:
                    token_dict = json.loads(raw_env.strip())
                    creds = _build_creds_from_dict(token_dict, req_scopes)
                    if creds:
                        creds, _ = refresh_credentials_in_memory(creds)
                        if creds.valid:
                            _cached_global_creds = creds
                            _cached_global_source = env_key
                            logger.info("Loaded live Google credentials from %s environment variable.", env_key)
                            return creds, env_key
                except Exception as env_err:
                    logger.error("Failed parsing %s environment variable as JSON: %s", env_key, env_err)

        # Source B: Render Secret Files
        for secret_path in (
            Path("/etc/secrets/token.json"),
            Path("/etc/secrets/google_token.json"),
            Path("/etc/secrets/credentials.json"),
        ):
            if secret_path.is_file():
                try:
                    token_dict = json.loads(secret_path.read_text(encoding="utf-8"))
                    creds = _build_creds_from_dict(token_dict, req_scopes)
                    if creds:
                        creds, _ = refresh_credentials_in_memory(creds)
                        if creds.valid:
                            _cached_global_creds = creds
                            _cached_global_source = str(secret_path)
                            logger.info("Loaded live Google credentials from secret file: %s", secret_path)
                            return creds, str(secret_path)
                except Exception as sec_err:
                    logger.warning("Failed reading secret file %s: %s", secret_path, sec_err)

        # Source C: Local token.json on disk
        local_token_file = Path(__file__).resolve().parent.parent.parent / "token.json"
        if local_token_file.is_file():
            try:
                token_dict = json.loads(local_token_file.read_text(encoding="utf-8"))
                creds = _build_creds_from_dict(token_dict, req_scopes)
                if creds:
                    creds, refreshed = refresh_credentials_in_memory(creds)
                    if refreshed:
                        try:
                            local_token_file.write_text(creds.to_json(), encoding="utf-8")
                        except Exception:
                            pass
                    if creds.valid:
                        _cached_global_creds = creds
                        _cached_global_source = "token.json"
                        return creds, "token.json"
            except Exception as loc_err:
                logger.warning("Failed reading local token.json: %s", loc_err)

    return None, "offline_simulator"
