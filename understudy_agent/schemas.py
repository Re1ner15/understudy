from typing import Literal, Optional
from pydantic import BaseModel, Field

# --- Live Extraction & Orchestration Schemas ---

class ActionItem(BaseModel):
    id: str = Field(description="A stable short id like 'ai-1', 'ai-2'")
    text: str = Field(description="The imperative to-do action")
    category: Literal["email", "calendar", "doc", "research", "task", "slack", "code"] = Field(
        description="The category of the action item"
    )
    assignee: Optional[str] = Field(
        default=None, description="The assignee if a person is named, else null"
    )
    due: Optional[str] = Field(
        default=None, description="A due date if mentioned (natural language ok), else null"
    )
    source_quote: str = Field(description="The sentence from the transcript that the item came from")
    confidence: float = Field(description="Confidence score 0-1", ge=0, le=1)

class ActionItemBatch(BaseModel):
    items: list[ActionItem]

class GuardrailResult(BaseModel):
    safe: bool = Field(description="True if the action passed all safety checks, False otherwise")
    reasons: list[str] = Field(default_factory=list, description="List of reasons if flagged or audited")

class ToolResult(BaseModel):
    item_id: str
    category: str
    status: Literal["done", "needs_approval", "error"]
    summary: str
    artifact: Optional[str] = None
    requires_approval: bool
    draftId: Optional[str] = None

class EmailDraft(BaseModel):
    subject: str
    body: str

class CalendarEvent(BaseModel):
    title: str
    proposed_time: str
    attendees: list[str]

class DocDraft(BaseModel):
    title: str
    content: str

class ResearchBrief(BaseModel):
    findings: str

class TaskTicket(BaseModel):
    title: str
    body: str
    labels: list[str]

class SlackMessage(BaseModel):
    target: str = Field(description="The recipient or channel, e.g. '#frontend' or a person")
    message: str = Field(description="The Slack message content")

class CodeEdit(BaseModel):
    old_string: str = Field(
        description="An EXACT substring copied verbatim from the current file to replace. "
        "Include enough surrounding context to be unique within the file."
    )
    new_string: str = Field(description="The replacement text for old_string")

class CodeChange(BaseModel):
    issue_title: str = Field(description="A concise GitHub issue title for the change")
    issue_body: str = Field(description="A clear issue body: what to change and why, in markdown")
    pr_title: str = Field(description="A concise pull request title")
    pr_body: str = Field(description="A PR description in markdown summarizing the change")
    commit_message: str = Field(description="A conventional commit message for the edit")
    edits: list[CodeEdit] = Field(
        description="The minimal set of exact find/replace edits to apply to the file. "
        "Each old_string must appear verbatim in the current file. Do not rewrite the whole file."
    )

# --- Firestore Document Models (camelCase matching web/src/data/types.ts) ---

class TranscriptLine(BaseModel):
    id: str
    speaker: str
    text: str
    ts: str
    isLive: Optional[bool] = None

class LiveAction(BaseModel):
    id: str
    itemId: str
    category: Literal["email", "calendar", "doc", "research", "task", "slack", "code"]
    title: str
    assignee: Optional[str] = None
    status: Literal["queued", "running", "done", "needs_approval", "error"]
    reasoning: str
    artifact: Optional[str] = None
    requiresApproval: bool = False
    guardrail: Optional[GuardrailResult] = None
    draftId: Optional[str] = None
    messageId: Optional[str] = None
    relatedMemory: Optional[list] = None

class FollowUpInfo(BaseModel):
    nudgeCount: Optional[int] = None
    lastNudge: Optional[str] = None
    nextNudge: Optional[str] = None
    note: Optional[str] = None
    actionType: Optional[Literal["escalate", "unblock", "review"]] = None

class Commitment(BaseModel):
    id: str
    title: str
    category: Literal["email", "calendar", "doc", "research", "task", "slack", "code"]
    assignee: Optional[str] = None
    sourceMeeting: str
    sourceDate: str
    due: Optional[str] = None
    status: Literal["open", "in_progress", "blocked", "done", "needs_approval", "overdue"]
    followUp: Optional[FollowUpInfo] = None
    artifact: Optional[str] = None

class MeetingDoc(BaseModel):
    id: str
    title: str
    date: str
    status: str = "live"
    startedAt: str = "02:14"

class ScreenContext(BaseModel):
    kind: Literal["slide", "website", "doc", "code", "app", "other"]
    summary: str
    keyPoints: list[str]
    ts: str

class TopicNote(BaseModel):
    heading: str
    notes: str

class Minutes(BaseModel):
    title: str
    date: str
    attendees: list[str]
    topics: list[TopicNote]
    decisions: list[str]
    materialsShown: list[str]
    actionItems: list[dict]

class Clarification(BaseModel):
    id: str = Field(description="Unique identifier for the clarification, e.g. clar-ai-1")
    meetingId: str = Field(description="ID of the meeting where this clarification arose")
    question: str = Field(description="The clarifying question asked")
    relatedText: str = Field(description="The ambiguous action item text or transcript quote")
    status: Literal["open", "answered", "dismissed"] = Field(
        default="open", description="Status of the clarification: open, answered, or dismissed"
    )
    answer: Optional[str] = Field(
        default=None, description="The provided answer/clarification response"
    )
    actionItem: Optional[ActionItem] = Field(
        default=None, description="The underlying ActionItem to resume execution once clarified"
    )

