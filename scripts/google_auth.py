#!/usr/bin/env python3
"""One-time OAuth installed-app authorization flow for Google Workspace.

Reads `understudy_agent/client_secret.json`, prompts the user via local web server,
and caches the access & refresh tokens to `understudy_agent/token.json`.
"""

import os
import sys
from pathlib import Path

# Resolve root workspace and file paths
ROOT_DIR = Path(__file__).resolve().parent.parent
CLIENT_SECRET_FILE = ROOT_DIR / "understudy_agent" / "client_secret.json"
TOKEN_FILE = ROOT_DIR / "understudy_agent" / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]

def run_auth_flow():
    print("=" * 70)
    print("🔐 Understudy Google Workspace OAuth Authorization")
    print("=" * 70)

    if not CLIENT_SECRET_FILE.exists():
        print(f"❌ Error: Client secret file not found at:\n   {CLIENT_SECRET_FILE}")
        print("\nTo set up Google Workspace integration:")
        print("1. Go to Google Cloud Console (https://console.cloud.google.com/).")
        print("2. Enable APIs: Gmail API, Google Calendar API, Google Docs API, Google Drive API.")
        print("3. Configure OAuth consent screen (Internal or External with your email as test user).")
        print("4. Create OAuth Client ID credentials (Application type: 'Desktop App').")
        print("5. Download the JSON credentials file and save it to:")
        print(f"   {CLIENT_SECRET_FILE}")
        print("6. Re-run: python scripts/google_auth.py")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("❌ Error: 'google-auth-oauthlib' is not installed.")
        print("   Please install requirements: pip install -r requirements.txt")
        sys.exit(1)

    print(f"Reading OAuth credentials from: {CLIENT_SECRET_FILE}")
    print(f"Requested Scopes:")
    for scope in SCOPES:
        print(f"  • {scope}")

    print("\nStarting local authentication server. Your browser will open shortly...")
    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRET_FILE),
        scopes=SCOPES,
    )

    creds = flow.run_local_server(port=0)

    # Save credentials token for future invocations
    with open(TOKEN_FILE, "w") as token_out:
        token_out.write(creds.to_json())

    print("\n" + "=" * 70)
    print(f"✅ Success! Google Workspace token cached to:\n   {TOKEN_FILE}")
    print("You can now enable real delivery with GOOGLE_WORKSPACE_ENABLED=true.")
    print("=" * 70)

if __name__ == "__main__":
    run_auth_flow()
