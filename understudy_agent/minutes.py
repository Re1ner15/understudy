import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from google import genai
from google.genai import types

from understudy_agent.config import MODEL_ID
from understudy_agent.schemas import Minutes, TopicNote
from understudy_agent import ledger

# Load environment
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

_client = None

def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client()
    return _client

def get_mock_minutes(
    meeting_id: str,
    meeting_title: str = "Monday Product Sync",
    meeting_date: str = "Aug 27",
) -> Minutes:
    """Returns realistic canned Minutes for testing without calling Gemini."""
    return Minutes(
        title=meeting_title,
        date=meeting_date,
        attendees=["Alex", "Sam"],
        topics=[
            TopicNote(
                heading="Acme Vendor Pricing",
                notes="Discussed unexpected weekend price increases by Acme. Team agreed to inquire regarding bulk discounts and survey competitor analytics pricing.",
            ),
            TopicNote(
                heading="Checkout Endpoints Contract",
                notes="Frontend team is blocked awaiting the API spec contract. Sam will draft a one-page spec this morning, and notify #frontend that endpoints will be ready by Friday.",
            ),
            TopicNote(
                heading="Design Review",
                notes="Booked cross-functional design review session for Thursday at 2:00 PM with the design team.",
            ),
            TopicNote(
                heading="Login Crash Bug",
                notes="Alex reported a reproducible bug where rapid logout/login causes a crash. Filing an immediate tracking ticket.",
            ),
        ],
        decisions=[
            "Seek bulk discount clarity from Acme while evaluating alternative analytics vendors.",
            "Hold cross-team design review for checkout endpoints on Thursday at 2:00 PM.",
            "Defer dashboard UI redesign to next quarter.",
        ],
        materialsShown=[
            "Slide: Architecture Roadmap & Checkout API Spec (Tier 2 milestone)",
            "Doc: Acme Pricing Tier Comparison",
        ],
        actionItems=[
            {
                "id": "ai-1",
                "text": "Email Acme to get clarity on new pricing tiers and ask if we qualify for bulk discount",
                "category": "email",
                "assignee": "Alex",
                "due": "today",
            },
            {
                "id": "ai-2",
                "text": "Research competitor pricing for comparable analytics add-on",
                "category": "research",
                "assignee": "Sam",
                "due": None,
            },
            {
                "id": "ai-3",
                "text": "Write up a one-page API spec doc for checkout endpoints",
                "category": "doc",
                "assignee": "Sam",
                "due": "this morning",
            },
            {
                "id": "ai-4",
                "text": "Book a design review for Thursday at 2pm with design team",
                "category": "calendar",
                "assignee": "Alex",
                "due": "Thursday at 2pm",
            },
            {
                "id": "ai-5",
                "text": "Notify #frontend on Slack that endpoints will be ready Friday",
                "category": "slack",
                "assignee": None,
                "due": "Friday",
            },
        ],
    )

def generate_minutes(meeting_id: str, mock: bool = False) -> Minutes:
    """Generates structured meeting minutes from Firestore transcripts, screen context,

    and commitments, saves them to Firestore under meetings/{meeting_id}/minutes/latest,
    and returns the Minutes object.
    
    Args:
        meeting_id: The ID of the meeting in Firestore.
        mock: If True, returns and persists mock Minutes without Gemini calls.
    """
    # 1. Fetch meeting metadata & context from ledger
    meeting_data = ledger.get_meeting(meeting_id) or {}
    meeting_title = meeting_data.get("title", "Meeting Sync")
    meeting_date = meeting_data.get("date", datetime.now().strftime("%b %d"))
    # User-supplied attendees take priority over transcript-derived / generic names.
    explicit_attendees = [a for a in (meeting_data.get("attendees") or []) if a]

    if mock or os.getenv("MOCK_GEMINI", "").lower() in ("true", "1", "yes"):
        minutes = get_mock_minutes(meeting_id, meeting_title=meeting_title, meeting_date=meeting_date)
        ledger.save_minutes(meeting_id, minutes)
        return minutes

    # 2. Gather full context from Firestore
    transcript_lines = ledger.get_transcript(meeting_id)
    screen_contexts = ledger.get_screen_context(meeting_id)
    actions = ledger.get_actions(meeting_id)
    commitments = ledger.get_commitments()

    # Format transcript
    transcript_formatted = []
    attendees_set = set()
    for line in transcript_lines:
        speaker = line.get("speaker", "Speaker")
        text = line.get("text", "")
        ts = line.get("ts", "")
        if speaker and speaker != "Speaker":
            attendees_set.add(speaker)
        transcript_formatted.append(f"[{ts}] {speaker}: {text}")
    transcript_text = "\n".join(transcript_formatted) if transcript_formatted else "No transcript lines recorded."

    # Format screen context
    screen_formatted = []
    for ctx in screen_contexts:
        ts = ctx.get("ts", "")
        kind = ctx.get("kind", "other")
        summary = ctx.get("summary", "")
        kp = ", ".join(ctx.get("keyPoints", []))
        screen_formatted.append(f"[{ts}] ({kind}) {summary} | Details: {kp}")
    screen_text = "\n".join(screen_formatted) if screen_formatted else "No screen context recorded."

    # Format actions / commitments
    actions_formatted = []
    for act in actions:
        aid = act.get("id", "")
        title = act.get("title", "")
        cat = act.get("category", "")
        assignee = act.get("assignee") or "unassigned"
        actions_formatted.append(f"- [{aid}] ({cat}) {title} (Assignee: {assignee})")
    actions_text = "\n".join(actions_formatted) if actions_formatted else "No actions recorded."

    prompt = f"""You are an executive meeting assistant generating structured meeting minutes.

Meeting Information:
- Meeting ID: {meeting_id}
- Title: {meeting_title}
- Date: {meeting_date}
- Attendees (use EXACTLY these names, do not invent others): {', '.join(explicit_attendees) if explicit_attendees else (', '.join(attendees_set) if attendees_set else 'the meeting participants')}

=== Transcript ===
{transcript_text}

=== Screen Content / Visual Context ===
{screen_text}

=== Live Actions & Commitments ===
{actions_text}

Generate formal and concise meeting minutes structured according to the schema:
- title: string
- date: string
- attendees: list of attendee names
- topics: list of topic objects (heading: string, notes: string summary of discussion)
- decisions: list of concrete decisions reached
- materialsShown: list of documents, presentations, or tools presented on screen or referenced
- actionItems: list of action item objects with id, text, category, assignee (or null), due (or null)
"""

    client = get_client()
    retries = [2, 5, 15, 30]

    for attempt in range(len(retries) + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=Minutes,
                ),
            )
            minutes = Minutes.model_validate_json(response.text)
            if explicit_attendees:
                minutes.attendees = explicit_attendees  # honor user-provided names exactly
            # Populate action items from the REAL extracted actions (accurate title +
            # assignee) rather than the LLM's freeform list, which can come back blank.
            # Exclude guardrail-held items (e.g. "post the API key", "email everyone
            # the roadmap") — those were caught and held for review, so they are NOT
            # real commitments and must not appear as clean assigned action items.
            real_actions = ledger.get_actions(meeting_id)
            if real_actions:
                committed = [
                    a for a in real_actions
                    if (a.get("guardrail") or {}).get("safe", True)
                ]
                minutes.actionItems = [
                    {
                        "id": a.get("id"),
                        "text": a.get("title", ""),
                        "category": a.get("category", "task"),
                        "assignee": a.get("assignee"),
                        "due": a.get("due"),
                    }
                    for a in committed
                ]
            ledger.save_minutes(meeting_id, minutes)
            return minutes
        except Exception as e:
            err_str = str(e)
            if attempt < len(retries) and (
                "503" in err_str
                or "429" in err_str
                or "UNAVAILABLE" in err_str
                or "Too Many Requests" in err_str
                or "RESOURCE_EXHAUSTED" in err_str
            ):
                print(f"Gemini API rate limit/transient error ({err_str}), retrying in {retries[attempt]}s...")
                time.sleep(retries[attempt])
            else:
                raise e

    raise RuntimeError("generate_minutes: exhausted retries")
