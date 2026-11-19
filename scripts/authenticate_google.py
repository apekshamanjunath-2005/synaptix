"""
Google OAuth 2.0 Authorization Script for Synaptix
Authorizes both Google Calendar and Google Gmail (compose) scopes:
- https://www.googleapis.com/auth/calendar
- https://www.googleapis.com/auth/gmail.compose

Reuses existing GOOGLE_CALENDAR_CLIENT_ID and GOOGLE_CALENDAR_CLIENT_SECRET from .env.
"""

import sys
import os
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.compose",
]

TOKEN_FILE = PROJECT_ROOT / "token.json"


def authenticate():
    settings = get_settings()
    client_id = settings.GOOGLE_CALENDAR_CLIENT_ID
    client_secret = settings.GOOGLE_CALENDAR_CLIENT_SECRET

    if not client_id or not client_secret:
        print("\n❌ ERROR: Google OAuth credentials not found in .env!")
        print("Please ensure GOOGLE_CALENDAR_CLIENT_ID and GOOGLE_CALENDAR_CLIENT_SECRET are set.")
        sys.exit(1)

    print("\n" + "=" * 65)
    print(" 🔐 SYNAPTIX GOOGLE OAUTH AUTHORIZATION")
    print(" Scopes:")
    for scope in SCOPES:
        print(f"  • {scope}")
    print("=" * 65)

    # Check existing token.json
    if TOKEN_FILE.exists():
        try:
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
            granted = creds.scopes or []
            has_compose = any("gmail.compose" in s for s in granted)
            has_cal = any("calendar" in s for s in granted)
            if has_compose and has_cal and creds.valid:
                print("\n✅ Existing token.json already has valid permissions for Calendar and Gmail compose!")
                print(f"Token file: {TOKEN_FILE}")
                return
            else:
                print("\n⚠️ Existing token.json lacks Gmail compose or is expired. Refreshing authorization...")
                TOKEN_FILE.unlink(missing_ok=True)
        except Exception as e:
            print(f"⚠️ Could not read existing token ({e}). Re-authorizing...")
            TOKEN_FILE.unlink(missing_ok=True)

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                "http://localhost:8088/",
                "http://127.0.0.1:8088/",
                "urn:ietf:wg:oauth:2.0:oob",
            ],
        }
    }

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow

        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        print("\n🌐 Opening local browser for Google authorization on port 8088...")
        print("Please sign in and click 'Allow' to grant Calendar & Gmail compose permissions.")
        
        creds = flow.run_local_server(port=8088, prompt="consent")
        
        # Save token
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        print(f"\n🎉 Authorization successful! Credentials saved to: {TOKEN_FILE.name}")
        print("Gmail and Calendar integrations are now fully live in Synaptix!")

    except Exception as exc:
        print(f"\n❌ OAuth flow error: {exc}")
        print("\nNote: Make sure http://localhost:8088/ is in your Authorized Redirect URIs in Google Cloud Console.")
        sys.exit(1)


if __name__ == "__main__":
    authenticate()
