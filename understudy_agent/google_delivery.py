"""Google Workspace Delivery Module for Understudy.

Provides live integration with Google Workspace APIs:
- Gmail: Create draft and send draft
- Google Calendar: Create calendar events
- Google Docs: Create documents with content

Gated by the environment variable: GOOGLE_WORKSPACE_ENABLED=true
"""

import os
import re
import base64
import logging
from datetime import datetime, timedelta, time
from email.message import EmailMessage
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger("understudy.google_delivery")

# Root workspace directory & credentials paths
ROOT_DIR = Path(__file__).resolve().parent.parent
TOKEN_FILE = ROOT_DIR / "understudy_agent" / "token.json"
CLIENT_SECRET_FILE = ROOT_DIR / "understudy_agent" / "client_secret.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]

def is_google_workspace_enabled() -> bool:
    """Returns True if Google Workspace real delivery is enabled via env flag."""
    return os.getenv("GOOGLE_WORKSPACE_ENABLED", "").lower() in ("1", "true", "yes")

def _get_credentials():
    """Loads cached OAuth credentials from token.json, refreshing if expired.

    Raises:
        FileNotFoundError: If token.json is not found.
        ValueError: If credentials cannot be loaded or refreshed.
    """
    if not TOKEN_FILE.exists():
        # Also check root level as fallback
        root_token = ROOT_DIR / "token.json"
        if root_token.exists():
            target_token_file = root_token
        else:
            raise FileNotFoundError(
                f"Google Workspace credentials not found at '{TOKEN_FILE}'. "
                "Please run 'python scripts/google_auth.py' to authenticate."
            )
    else:
        target_token_file = TOKEN_FILE

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError as exc:
        raise ImportError(
            "Google client libraries not installed. Please run 'pip install -r requirements.txt'."
        ) from exc

    try:
        creds = Credentials.from_authorized_user_file(str(target_token_file), SCOPES)
    except Exception as e:
        raise ValueError(f"Failed to read credentials from {target_token_file}: {e}") from e

    if not creds:
        raise ValueError(f"No valid credentials found in {target_token_file}.")

    if creds.expired and creds.refresh_token:
        try:
            logger.info("Google Workspace credentials expired. Refreshing token...")
            creds.refresh(Request())
            with open(target_token_file, "w") as f:
                f.write(creds.to_json())
            logger.info("Google Workspace credentials refreshed successfully.")
        except Exception as e:
            raise ValueError(f"Failed to refresh Google Workspace credentials: {e}") from e

    if not creds.valid:
        raise ValueError("Google Workspace credentials are not valid.")

    return creds

def get_next_thursday_iso(hour: int = 14, minute: int = 0) -> str:
    """Returns ISO 8601 string for next Thursday at the specified hour (default 2:00 PM)."""
    now = datetime.now()
    # weekday: Monday=0, Tuesday=1, Wednesday=2, Thursday=3, ...
    days_ahead = (3 - now.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    target_date = now + timedelta(days=days_ahead)
    target_dt = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    # Return formatted ISO string with local offset or standard ISO format
    local_tz = datetime.now().astimezone().tzinfo
    target_dt_with_tz = target_dt.replace(tzinfo=local_tz)
    return target_dt_with_tz.isoformat()

def parse_proposed_time_to_iso(time_str: Optional[str]) -> str:
    """Parses a natural language or ISO time string into an ISO 8601 string.

    If unparseable or empty, falls back to tentative next-Thursday slot at 2:00 PM.
    """
    if not time_str or not time_str.strip():
        return get_next_thursday_iso(hour=14, minute=0)

    raw = time_str.strip()

    # 1. Try standard ISO parsing
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            local_tz = datetime.now().astimezone().tzinfo
            dt = dt.replace(tzinfo=local_tz)
        return dt.isoformat()
    except Exception:
        pass

    # 2. Parse natural language strings (e.g., "Thursday at 2pm", "Friday 10:00 AM", "today at 3pm")
    lower = raw.lower()
    now = datetime.now()
    local_tz = now.astimezone().tzinfo

    # Extract time of day (hour, minute)
    time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", lower)
    hour = 14
    minute = 0
    if time_match:
        h = int(time_match.group(1))
        m = int(time_match.group(2)) if time_match.group(2) else 0
        ampm = time_match.group(3)
        if ampm == "pm" and h < 12:
            h += 12
        elif ampm == "am" and h == 12:
            h = 0
        hour, minute = h, m

    # Extract day
    day_offset = None
    weekdays = {
        "monday": 0, "mon": 0,
        "tuesday": 1, "tue": 1, "tues": 1,
        "wednesday": 2, "wed": 2,
        "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
        "friday": 4, "fri": 4,
        "saturday": 5, "sat": 5,
        "sunday": 6, "sun": 6,
    }

    for day_name, day_num in weekdays.items():
        if day_name in lower:
            days_ahead = (day_num - now.weekday()) % 7
            if days_ahead == 0 and "next" in lower:
                days_ahead = 7
            elif days_ahead == 0 and (now.hour > hour or (now.hour == hour and now.minute >= minute)):
                days_ahead = 7
            day_offset = days_ahead
            break

    if day_offset is None:
        if "tomorrow" in lower:
            day_offset = 1
        elif "today" in lower or "tonight" in lower:
            day_offset = 0

    if day_offset is not None:
        target_date = now + timedelta(days=day_offset)
        target_dt = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0, tzinfo=local_tz)
        return target_dt.isoformat()

    # Fallback to tentative next-Thursday slot at 2:00 PM
    return get_next_thursday_iso(hour=14, minute=0)

def create_gmail_draft(
    to: Optional[str] = None,
    subject: str = "",
    body: str = "",
) -> Dict[str, str]:
    """Creates a real Gmail DRAFT without sending.

    Returns:
        {"draftId": str, "url": str}
    """
    creds = _get_credentials()
    from googleapiclient.discovery import build

    service = build("gmail", "v1", credentials=creds)

    message = EmailMessage()
    message.set_content(body or "")
    if to and to.strip():
        message["To"] = to.strip()
    message["Subject"] = subject or "(No Subject)"

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_body = {"message": {"raw": encoded_message}}

    draft = service.users().drafts().create(userId="me", body=create_body).execute()
    draft_id = draft.get("id", "")
    url = f"https://mail.google.com/mail/u/0/#drafts/{draft_id}"

    logger.info(f"Created Gmail draft '{draft_id}' -> {url}")
    return {"draftId": draft_id, "url": url}

def send_gmail_draft(draft_id: str) -> Dict[str, str]:
    """Sends an existing Gmail draft.

    Returns:
        {"messageId": str}
    """
    if not draft_id:
        raise ValueError("draft_id is required to send a Gmail draft.")

    creds = _get_credentials()
    from googleapiclient.discovery import build

    service = build("gmail", "v1", credentials=creds)

    send_body = {"id": draft_id}
    sent = service.users().drafts().send(userId="me", body=send_body).execute()
    message_id = sent.get("id", "")

    logger.info(f"Sent Gmail draft '{draft_id}' -> messageId: '{message_id}'")
    return {"messageId": message_id}

def create_calendar_event(
    title: str,
    start_iso: str,
    attendees: Optional[List[str]] = None,
    end_iso: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, str]:
    """Creates a real Google Calendar event.

    Returns:
        {"eventId": str, "htmlLink": str}
    """
    creds = _get_credentials()
    from googleapiclient.discovery import build

    service = build("calendar", "v3", credentials=creds)

    # Parse and compute start / end datetimes
    try:
        start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    except Exception:
        start_dt = datetime.fromisoformat(get_next_thursday_iso())

    if end_iso:
        try:
            end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
        except Exception:
            end_dt = start_dt + timedelta(hours=1)
    else:
        end_dt = start_dt + timedelta(hours=1)

    start_iso_clean = start_dt.isoformat()
    end_iso_clean = end_dt.isoformat()

    # Format attendees: only include email field if formatted as valid email
    attendee_entries = []
    attendee_names = []
    for att in (attendees or []):
        if not att or not str(att).strip():
            continue
        att_str = str(att).strip()
        attendee_names.append(att_str)
        if "@" in att_str:
            attendee_entries.append({"email": att_str})

    desc = description or ""
    if attendee_names:
        desc_line = f"Attendees: {', '.join(attendee_names)}"
        desc = f"{desc}\n\n{desc_line}".strip() if desc else desc_line

    event_body: Dict[str, Any] = {
        "summary": title or "Understudy Scheduled Event",
        "description": desc,
        "start": {
            "dateTime": start_iso_clean,
        },
        "end": {
            "dateTime": end_iso_clean,
        },
    }

    if attendee_entries:
        event_body["attendees"] = attendee_entries

    event = service.events().insert(calendarId="primary", body=event_body).execute()
    event_id = event.get("id", "")
    html_link = event.get("htmlLink", "") or f"https://calendar.google.com/calendar/event?eid={event_id}"

    logger.info(f"Created Calendar event '{event_id}' -> {html_link}")
    return {"eventId": event_id, "htmlLink": html_link}

def create_google_doc(
    title: str,
    content: str = "",
) -> Dict[str, str]:
    """Creates a real Google Doc with the specified title and content.

    Returns:
        {"docId": str, "url": str}
    """
    creds = _get_credentials()
    from googleapiclient.discovery import build

    docs_service = build("docs", "v1", credentials=creds)

    doc = docs_service.documents().create(body={"title": title or "Untitled Document"}).execute()
    doc_id = doc.get("documentId", "")
    url = f"https://docs.google.com/document/d/{doc_id}/edit"

    if content and content.strip():
        requests = [
            {
                "insertText": {
                    "location": {
                        "index": 1,
                    },
                    "text": content,
                }
            }
        ]
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": requests},
        ).execute()

    logger.info(f"Created Google Doc '{doc_id}' -> {url}")
    return {"docId": doc_id, "url": url}
