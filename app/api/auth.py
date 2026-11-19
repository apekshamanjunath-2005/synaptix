"""
Authentication Router for Synaptix (Multi-User Google OAuth 2.0)
Provides web-based OAuth login, callback token exchange, userinfo loading,
session management with HTTP-only signed JWT cookies, and user isolation.
"""

import logging
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.config import get_settings
from app.database.firestore import firestore_service

logger = logging.getLogger("synaptix.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()

COOKIE_NAME = "synaptix_session"
JWT_ALGORITHM = "HS256"


# ────────────────────────────────────────────────────────────────────────────
# JWT SESSION TOKEN HELPERS
# ────────────────────────────────────────────────────────────────────────────

def create_session_token(
    user_id: str,
    email: str,
    name: Optional[str] = None,
    picture: Optional[str] = None
) -> str:
    """Create a signed JWT session token valid for 30 days."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=30)).timestamp()),
    }
    return jwt.encode(payload, settings.SESSION_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a signed JWT session token."""
    try:
        payload = jwt.decode(token, settings.SESSION_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception as exc:
        logger.debug("Session token decode failed: %s", exc)
        return None


def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Extract user from Bearer header or HTTP-only session cookie if present.
    Returns None if not authenticated.
    """
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()

    if not token:
        token = request.cookies.get(COOKIE_NAME)

    if not token:
        return None

    payload = decode_session_token(token)
    if not payload:
        return None

    return {
        "authenticated": True,
        "user_id": payload.get("sub"),
        "email": payload.get("email"),
        "name": payload.get("name"),
        "picture": payload.get("picture"),
    }


def get_current_user(request: Request) -> Dict[str, Any]:
    """
    FastAPI dependency for endpoints.
    Returns authenticated user if session exists; otherwise returns default_user
    for backward compatibility with existing tests and CLI tools.
    """
    user = get_optional_user(request)
    if user:
        return user

    # Graceful fallback for unauthenticated calls / unit tests
    return {
        "authenticated": False,
        "user_id": "default_user",
        "email": "user@example.com",
        "name": "Default User",
        "picture": None,
    }


# ────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ────────────────────────────────────────────────────────────────────────────

@router.get("/login")
async def login():
    """
    Redirects user to Google OAuth 2.0 consent screen with requested scopes
    including openid, email, profile, Calendar, and Gmail compose.
    """
    client_id = settings.effective_client_id
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth Client ID is not configured. Set GOOGLE_CLIENT_ID or GOOGLE_CALENDAR_CLIENT_ID in .env."
        )

    scope_str = " ".join(settings.GOOGLE_OAUTH_SCOPES)
    params = {
        "client_id": client_id,
        "redirect_uri": settings.OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": scope_str,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    logger.info("Redirecting to Google OAuth login screen with scopes: %s", scope_str)
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/google/callback")
async def google_callback(
    code: Optional[str] = None,
    error: Optional[str] = None,
    state: Optional[str] = None
):
    """
    OAuth 2.0 callback handler.
    Exchanges auth code for tokens, retrieves profile userinfo,
    persists tokens into Firestore, and sets signed session cookie.
    """
    if error:
        logger.warning("Google OAuth error in callback: %s", error)
        return RedirectResponse(url=f"/?auth_error={urllib.parse.quote(error)}", status_code=302)

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code from Google.")

    client_id = settings.effective_client_id
    client_secret = settings.effective_client_secret

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth Client ID or Client Secret missing in configuration."
        )

    # 1. Exchange authorization code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    token_payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": settings.OAUTH_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(token_url, data=token_payload)
            if token_resp.status_code != 200:
                logger.error("Token exchange failed (%d): %s", token_resp.status_code, token_resp.text)
                return RedirectResponse(
                    url=f"/?auth_error={urllib.parse.quote('Token exchange failed: ' + token_resp.text)}",
                    status_code=302
                )
            tokens = token_resp.json()

            # 2. Fetch userinfo from Google
            access_token = tokens.get("access_token")
            userinfo_resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if userinfo_resp.status_code != 200:
                logger.error("Userinfo fetch failed: %s", userinfo_resp.text)
                return RedirectResponse(url="/?auth_error=Failed+to+fetch+user+profile", status_code=302)

            user_info = userinfo_resp.json()

    except Exception as exc:
        logger.error("Error communicating with Google OAuth: %s", exc)
        return RedirectResponse(url=f"/?auth_error={urllib.parse.quote(str(exc))}", status_code=302)

    # 3. Derive unique user ID
    raw_uid = user_info.get("id") or user_info.get("email", "").replace("@", "_").replace(".", "_")
    user_id = f"user_{raw_uid}"
    email = user_info.get("email", "")
    name = user_info.get("name") or email.split("@")[0].title()
    picture = user_info.get("picture")

    # 4. Save OAuth tokens and user profile to Firestore
    # Add client_id and client_secret to tokens dictionary for easy refresh
    tokens_to_save = dict(tokens)
    tokens_to_save["client_id"] = client_id
    tokens_to_save["client_secret"] = client_secret
    firestore_service.save_user_tokens(user_id=user_id, tokens=tokens_to_save)

    profile_data = {
        "email": email,
        "name": name,
        "picture": picture,
        "google_id": user_info.get("id"),
    }
    firestore_service.save_user_profile(user_id=user_id, profile=profile_data)

    # 5. Issue signed session JWT
    session_jwt = create_session_token(
        user_id=user_id,
        email=email,
        name=name,
        picture=picture
    )

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_jwt,
        httponly=True,
        samesite="lax",
        max_age=86400 * 30,  # 30 days
        secure=False  # Allow local HTTP development
    )
    logger.info("User logged in successfully: %s (%s)", name, email)
    return response


@router.get("/me")
async def get_current_user_profile(request: Request):
    """
    Returns profile information for currently authenticated user.
    Returns 401 if unauthenticated.
    """
    user = get_optional_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please sign in with Google."
        )

    # Enrich with stored profile if present
    profile = firestore_service.get_user_profile(user["user_id"])
    return {
        "authenticated": True,
        "user_id": user["user_id"],
        "email": profile.get("email") if profile else user.get("email"),
        "name": profile.get("name") if profile else user.get("name"),
        "picture": profile.get("picture") if profile else user.get("picture"),
    }


@router.post("/logout")
@router.get("/logout")
async def logout():
    """Clears the session cookie and redirects to home."""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key=COOKIE_NAME)
    logger.info("User logged out successfully.")
    return response


@router.post("/guest")
@router.get("/guest")
async def guest_login():
    """
    Instant zero-cost guest login for offline development and testing.
    Creates a guest profile and issues a session cookie.
    """
    guest_id = "guest_user"
    profile = {
        "email": "guest@synaptix.local",
        "name": "Guest User",
        "picture": None,
    }
    firestore_service.save_user_profile(guest_id, profile)
    session_jwt = create_session_token(
        user_id=guest_id,
        email=profile["email"],
        name=profile["name"]
    )
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_jwt,
        httponly=True,
        samesite="lax",
        max_age=86400 * 30,
        secure=False
    )
    logger.info("Guest session activated.")
    return response
