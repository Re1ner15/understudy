import os
import uuid
from datetime import datetime
from typing import Optional, Union, Dict, Any
from google.cloud import firestore
from google.cloud.firestore import FieldFilter
from understudy_agent.schemas import (
    TranscriptLine,
    LiveAction,
    Commitment,
    FollowUpInfo,
    MeetingDoc,
    ScreenContext,
    Minutes,
    Clarification,
    GuardrailResult,
)

def get_db() -> firestore.Client:
    """Returns a Firestore client.
    
    When FIRESTORE_EMULATOR_HOST is set (e.g. 127.0.0.1:8080), the client
    automatically connects to the local emulator.
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "demo-understudy")
    return firestore.Client(project=project_id)

def create_meeting(
    meeting_id: str,
    title: str,
    date: str = "Aug 27",
    status: str = "live",
    started_at: str = "02:14",
) -> Dict[str, Any]:
    """Creates or updates a meeting document in meetings/{meetingId}."""
    db = get_db()
    data = {
        "id": meeting_id,
        "title": title,
        "date": date,
        "status": status,
        "startedAt": started_at,
    }
    db.collection("meetings").document(meeting_id).set(data, merge=True)
    return data

def set_attendees(meeting_id: str, attendees: list) -> None:
    """Stores the user-provided attendee names on a meeting (used for minutes)."""
    get_db().collection("meetings").document(meeting_id).set(
        {"attendees": [a for a in attendees if a]}, merge=True
    )

def set_capturing(meeting_id: str, active: bool) -> None:
    """Sets the recording/capture flag on a meeting (listener reads this to mute/unmute)."""
    get_db().collection("meetings").document(meeting_id).set(
        {"capturing": bool(active)}, merge=True
    )

def get_capturing(meeting_id: str) -> bool:
    """Returns the current capture flag (default False = muted)."""
    m = get_meeting(meeting_id) or {}
    return bool(m.get("capturing", False))

def add_transcript_line(
    meeting_id: str,
    line: Union[TranscriptLine, Dict[str, Any]],
) -> Dict[str, Any]:
    """Appends/sets a transcript line in meetings/{meetingId}/transcript/{lineId}."""
    db = get_db()
    data = line.model_dump(exclude_none=True) if isinstance(line, TranscriptLine) else dict(line)
    line_id = data["id"]
    db.collection("meetings").document(meeting_id).collection("transcript").document(line_id).set(data, merge=True)
    return data

def upsert_action(
    meeting_id: str,
    action: Union[LiveAction, Dict[str, Any]],
) -> Dict[str, Any]:
    """Creates or updates an action in meetings/{meetingId}/actions/{actionId}."""
    db = get_db()
    data = action.model_dump(exclude_none=True) if isinstance(action, LiveAction) else dict(action)
    action_id = data["id"]
    db.collection("meetings").document(meeting_id).collection("actions").document(action_id).set(data, merge=True)
    return data

def update_action_status(
    meeting_id: str,
    action_id: str,
    status: str,
    reasoning: Optional[str] = None,
    artifact: Optional[str] = None,
) -> None:
    """Updates status and optional reasoning/artifact for a live action.

    Tolerant of a missing doc: if the card was cleared (e.g. the meeting was
    reset/concluded while a detached handler was still in flight), skip the
    update instead of raising — and do NOT resurrect the cleared card.
    """
    from google.api_core import exceptions as _gexc
    db = get_db()
    updates: Dict[str, Any] = {"status": status}
    if reasoning is not None:
        updates["reasoning"] = reasoning
    if artifact is not None:
        updates["artifact"] = artifact
    try:
        db.collection("meetings").document(meeting_id).collection("actions").document(action_id).update(updates)
    except _gexc.NotFound:
        pass  # card was cleared out from under an in-flight handler — ignore

def upsert_commitment(
    commitment: Union[Commitment, Dict[str, Any]],
) -> Dict[str, Any]:
    """Creates or updates a commitment in commitments/{commitmentId}."""
    db = get_db()
    data = commitment.model_dump(exclude_none=True) if isinstance(commitment, Commitment) else dict(commitment)
    commitment_id = data["id"]
    db.collection("commitments").document(commitment_id).set(data, merge=True)
    return data

def update_commitment_status(commitment_id: str, status: str) -> None:
    """Updates the status of a commitment."""
    db = get_db()
    db.collection("commitments").document(commitment_id).update({"status": status})

def get_commitment(commitment_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single commitment document by ID."""
    db = get_db()
    doc = db.collection("commitments").document(commitment_id).get()
    return doc.to_dict() if doc.exists else None

def get_commitments(status_filter: Optional[list[str]] = None) -> list[Dict[str, Any]]:
    """Fetches all commitments, optionally filtered by status list."""
    db = get_db()
    ref = db.collection("commitments")
    if status_filter:
        docs = ref.where(filter=FieldFilter("status", "in", status_filter)).stream()
    else:
        docs = ref.stream()
    return [d.to_dict() for d in docs]

def get_action(meeting_id: str, action_id: str) -> Optional[Dict[str, Any]]:
    """Fetches an action document in meetings/{meetingId}/actions/{actionId}."""
    db = get_db()
    doc = db.collection("meetings").document(meeting_id).collection("actions").document(action_id).get()
    return doc.to_dict() if doc.exists else None

def find_action(action_id: str) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Finds an action document across all meetings. Returns (meeting_id, action_dict)."""
    db = get_db()
    meetings = db.collection("meetings").stream()
    for meeting in meetings:
        act_doc = meeting.reference.collection("actions").document(action_id).get()
        if act_doc.exists:
            return meeting.id, act_doc.to_dict()
    return None, None

def update_commitment_follow_up(
    commitment_id: str,
    follow_up: Dict[str, Any],
    status: Optional[str] = None,
) -> None:
    """Updates the followUp block and optional status of a commitment."""
    db = get_db()
    updates: Dict[str, Any] = {"followUp": follow_up}
    if status is not None:
        updates["status"] = status
    db.collection("commitments").document(commitment_id).update(updates)

def record_nudge(
    commitment_id: str,
    note: str,
    next_nudge: Optional[str] = None,
) -> None:
    """Records a nudge event on a commitment."""
    db = get_db()
    doc_ref = db.collection("commitments").document(commitment_id)
    doc = doc_ref.get()
    
    current_follow_up = {}
    if doc.exists:
        current_follow_up = doc.to_dict().get("followUp", {}) or {}
        
    nudge_count = (current_follow_up.get("nudgeCount") or 0) + 1
    new_follow_up = {
        **current_follow_up,
        "nudgeCount": nudge_count,
        "note": note,
    }
    if next_nudge is not None:
        new_follow_up["nextNudge"] = next_nudge
        
    doc_ref.update({"followUp": new_follow_up})

def clear_meeting_data(meeting_id: str) -> None:
    """Deletes subcollections (transcript, actions, screenContext, minutes, clarifications, audit) of a meeting."""
    db = get_db()
    meeting_ref = db.collection("meetings").document(meeting_id)
    for subcoll in ["transcript", "actions", "screenContext", "minutes", "clarifications", "audit"]:
        docs = meeting_ref.collection(subcoll).stream()
        for d in docs:
            d.reference.delete()

def action_to_commitment(
    action: Union[LiveAction, Dict[str, Any]],
    meeting_title: str,
    meeting_date: str,
) -> Commitment:
    """Maps a live action from a meeting into a durable commitment."""
    data = action.model_dump() if isinstance(action, LiveAction) else dict(action)
    raw_id = data.get("id", "")
    if raw_id.startswith("act-"):
        suffix = raw_id[4:]
        if suffix.startswith("ai-"):
            suffix = suffix[3:]
        commitment_id = f"com-{suffix}"
    elif raw_id.startswith("ai-"):
        commitment_id = f"com-{raw_id[3:]}"
    elif not raw_id.startswith("com-"):
        commitment_id = f"com-{raw_id}"
    else:
        commitment_id = raw_id
    
    status_map = {
        "needs_approval": "needs_approval",
        "running": "in_progress",
        "queued": "open",
        "done": "done",
        "error": "blocked",
    }
    commitment_status = status_map.get(data.get("status", "open"), "open")
    
    return Commitment(
        id=commitment_id,
        title=data.get("title", ""),
        category=data.get("category", "task"),
        assignee=data.get("assignee"),
        sourceMeeting=meeting_title,
        sourceDate=meeting_date,
        due=data.get("due"),
        status=commitment_status,
        artifact=data.get("artifact"),
        followUp=FollowUpInfo(
            note="Promoted from live meeting"
        ),
    )

def add_screen_context(
    meeting_id: str,
    ctx: Union[ScreenContext, Dict[str, Any]],
) -> Dict[str, Any]:
    """Appends a screen context entry in meetings/{meetingId}/screenContext/{autoId}."""
    db = get_db()
    data = ctx.model_dump(exclude_none=True) if isinstance(ctx, ScreenContext) else dict(ctx)
    doc_ref = db.collection("meetings").document(meeting_id).collection("screenContext").document()
    data["id"] = doc_ref.id
    doc_ref.set(data)
    return data

def get_screen_context(meeting_id: str) -> list[Dict[str, Any]]:
    """Fetches all screen context entries for a meeting from meetings/{meetingId}/screenContext."""
    db = get_db()
    docs = db.collection("meetings").document(meeting_id).collection("screenContext").stream()
    return [d.to_dict() for d in docs]

def save_minutes(
    meeting_id: str,
    minutes: Union[Minutes, Dict[str, Any]],
) -> Dict[str, Any]:
    """Saves minutes to meetings/{meetingId}/minutes/latest."""
    db = get_db()
    data = minutes.model_dump(exclude_none=True) if isinstance(minutes, Minutes) else dict(minutes)
    db.collection("meetings").document(meeting_id).collection("minutes").document("latest").set(data)
    return data

def get_minutes(meeting_id: str) -> Optional[Dict[str, Any]]:
    """Fetches the latest minutes from meetings/{meetingId}/minutes/latest."""
    db = get_db()
    doc = db.collection("meetings").document(meeting_id).collection("minutes").document("latest").get()
    return doc.to_dict() if doc.exists else None

def get_transcript(meeting_id: str) -> list[Dict[str, Any]]:
    """Fetches all transcript lines for a meeting from meetings/{meetingId}/transcript."""
    db = get_db()
    docs = db.collection("meetings").document(meeting_id).collection("transcript").stream()
    return [d.to_dict() for d in docs]

def get_actions(meeting_id: str) -> list[Dict[str, Any]]:
    """Fetches all live actions for a meeting from meetings/{meetingId}/actions."""
    db = get_db()
    docs = db.collection("meetings").document(meeting_id).collection("actions").stream()
    return [d.to_dict() for d in docs]

def get_meeting(meeting_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a meeting document from meetings/{meetingId}."""
    db = get_db()
    doc = db.collection("meetings").document(meeting_id).get()
    return doc.to_dict() if doc.exists else None

def add_clarification(
    meeting_id: str,
    clarification: Union[Clarification, Dict[str, Any]],
) -> Dict[str, Any]:
    """Appends/sets a clarification in meetings/{meetingId}/clarifications/{clarificationId}."""
    db = get_db()
    data = clarification.model_dump(exclude_none=True) if isinstance(clarification, Clarification) else dict(clarification)
    clar_id = data["id"]
    db.collection("meetings").document(meeting_id).collection("clarifications").document(clar_id).set(data, merge=True)
    return data

def answer_clarification(
    meeting_id: str,
    clarification_id: str,
    answer: str,
    status: str = "answered",
) -> Optional[Dict[str, Any]]:
    """Updates status and answer for a clarification in meetings/{meetingId}/clarifications/{clarificationId}."""
    db = get_db()
    doc_ref = db.collection("meetings").document(meeting_id).collection("clarifications").document(clarification_id)
    doc_ref.update({"status": status, "answer": answer})
    updated_doc = doc_ref.get()
    return updated_doc.to_dict() if updated_doc.exists else None

def get_clarifications(
    meeting_id: str,
    status_filter: Optional[list[str]] = None,
) -> list[Dict[str, Any]]:
    """Fetches all clarifications for a meeting, optionally filtered by status list."""
    db = get_db()
    ref = db.collection("meetings").document(meeting_id).collection("clarifications")
    if status_filter:
        docs = ref.where(filter=FieldFilter("status", "in", status_filter)).stream()
    else:
        docs = ref.stream()
    return [d.to_dict() for d in docs]

def get_clarification(meeting_id: str, clarification_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single clarification document from meetings/{meetingId}/clarifications/{clarificationId}."""
    db = get_db()
    doc = db.collection("meetings").document(meeting_id).collection("clarifications").document(clarification_id).get()
    return doc.to_dict() if doc.exists else None

def find_clarification(clarification_id: str) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Finds a clarification document across all meetings. Returns (meeting_id, clarification_dict)."""
    db = get_db()
    meetings = db.collection("meetings").stream()
    for meeting in meetings:
        clar_doc = meeting.reference.collection("clarifications").document(clarification_id).get()
        if clar_doc.exists:
            return meeting.id, clar_doc.to_dict()
    return None, None

def log_span(
    meeting_id: str,
    span_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Persists an OpenTelemetry-style span into meetings/{meetingId}/audit/{spanId}."""
    db = get_db()
    data = dict(span_data)
    span_id = data.get("spanId") or data.get("id") or f"span-{uuid.uuid4().hex[:12]}"
    data["id"] = span_id
    data["spanId"] = span_id
    data["meetingId"] = meeting_id
    if "ts" not in data:
        data["ts"] = data.get("startTs") or datetime.now().isoformat()
    db.collection("meetings").document(meeting_id).collection("audit").document(span_id).set(data, merge=True)
    return data

def log_guardrail_decision(
    meeting_id: str,
    action_id: str,
    result: Union[GuardrailResult, Dict[str, Any]],
    action_data: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    parent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Logs a guardrail decision to the audit subcollection at meetings/{meetingId}/audit/{auditId}."""
    db = get_db()
    audit_id = f"audit-{uuid.uuid4().hex[:8]}"
    ts = datetime.now().isoformat()

    safe = result.safe if isinstance(result, GuardrailResult) else result.get("safe", True)
    reasons = result.reasons if isinstance(result, GuardrailResult) else result.get("reasons", [])

    act_dict = action_data or {}
    action_title = act_dict.get("title") or act_dict.get("text", "")
    category = act_dict.get("category", "")

    # Retrieve active tracing context if present
    try:
        from understudy_agent.tracing import get_current_trace_id, get_current_span_id
        resolved_trace_id = trace_id or get_current_trace_id() or f"trace-{uuid.uuid4().hex[:16]}"
        resolved_parent_id = parent_id or get_current_span_id()
    except Exception:
        resolved_trace_id = trace_id or f"trace-{uuid.uuid4().hex[:16]}"
        resolved_parent_id = parent_id

    audit_entry = {
        "id": audit_id,
        "spanId": audit_id,
        "traceId": resolved_trace_id,
        "parentId": resolved_parent_id,
        "name": "guardrail.evaluate",
        "actionId": action_id,
        "meetingId": meeting_id,
        "safe": safe,
        "reasons": reasons,
        "actionTitle": action_title,
        "category": category,
        "status": "approved" if safe else "flagged_needs_approval",
        "startTs": ts,
        "endTs": ts,
        "ts": ts,
        "attributes": {
            "safe": safe,
            "reasons": reasons,
            "actionId": action_id,
            "actionTitle": action_title,
            "category": category,
        },
    }

    db.collection("meetings").document(meeting_id).collection("audit").document(audit_id).set(audit_entry, merge=True)
    return audit_entry

def get_audit_logs(meeting_id: str) -> list[Dict[str, Any]]:
    """Fetches all guardrail audit logs and tracing spans for a meeting from meetings/{meetingId}/audit."""
    db = get_db()
    docs = db.collection("meetings").document(meeting_id).collection("audit").stream()
    logs = [d.to_dict() for d in docs]
    # Sort by timestamp chronologically
    logs.sort(key=lambda x: x.get("startTs") or x.get("ts", ""))
    return logs




