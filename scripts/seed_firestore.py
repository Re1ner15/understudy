import os
import sys
from understudy_agent.ledger import (
    get_db,
    create_meeting,
    add_transcript_line,
    upsert_action,
    upsert_commitment,
)
from understudy_agent.schemas import (
    TranscriptLine,
    LiveAction,
    Commitment,
    FollowUpInfo,
)

MEETING_ID = "demo-meeting"

transcript_seed = [
    TranscriptLine(
        id="tl-1",
        speaker="Alex",
        text="Yeah. I'll email Acme today to get clarity on the new tiers and ask if we qualify for a bulk discount.",
        ts="02:06",
    ),
    TranscriptLine(
        id="tl-2",
        speaker="Sam",
        text="Good. And can you research what two or three competitors charge for a comparable analytics add-on?",
        ts="02:09",
    ),
    TranscriptLine(
        id="tl-3",
        speaker="Alex",
        text="Right. Can you write up a one-page API spec doc for the checkout endpoints?",
        ts="02:12",
    ),
    TranscriptLine(
        id="tl-4",
        speaker="Sam",
        text="I'll draft it this morning. And let's book a design review for Thursday at 2pm",
        ts="now",
        isLive=True,
    ),
]

actions_seed = [
    LiveAction(
        id="act-1",
        itemId="ai-1",
        category="email",
        title="Email Acme about new pricing tiers & bulk discount",
        assignee="Alex",
        status="needs_approval",
        reasoning="Alex committed to email the vendor. Sending is irreversible, so I drafted it and I'm holding for your OK.",
        requiresApproval=True,
        artifact="Subject: Inquiry Regarding New Pricing Tiers and Bulk Discounts\n\nHi Acme Team,\n\nI hope you are doing well...",
    ),
    LiveAction(
        id="act-2",
        itemId="ai-3",
        category="doc",
        title="Write API spec doc — checkout endpoints",
        assignee="Sam",
        status="running",
        reasoning='Heard "write up a one-page API spec for the checkout endpoints" → categorized doc, generating outline now.',
        requiresApproval=False,
    ),
    LiveAction(
        id="act-3",
        itemId="ai-4",
        category="calendar",
        title="Book design review — Thursday 2:00 PM",
        assignee="Alex",
        status="done",
        reasoning='Extracted time and attendees from "book a design review for Thursday at 2pm" → invited the design team.',
        requiresApproval=False,
        artifact="Event: Design Review\nTime: Thursday 2:00 PM\nAttendees: Sam, Design Team",
    ),
    LiveAction(
        id="act-4",
        itemId="ai-2",
        category="research",
        title="Research competitor analytics pricing",
        assignee="Sam",
        status="done",
        reasoning="3 comparables, $12–29/seat range with feature notes.",
        requiresApproval=False,
        artifact="Brief ready: 3 comparables, $12-29/seat range with feature notes.",
    ),
    LiveAction(
        id="act-5",
        itemId="ai-5",
        category="slack",
        title="Notify #frontend: endpoints ready Friday",
        assignee=None,
        status="queued",
        reasoning="Queued message for the #frontend channel regarding endpoint delivery.",
        requiresApproval=False,
    ),
]

commitments_seed = [
    # Needs attention
    Commitment(
        id="com-1",
        title="Send Q3 pricing summary to finance",
        category="email",
        assignee="Sam",
        sourceMeeting="Vendor call · Acme",
        sourceDate="Aug 24",
        due="2 days overdue",
        status="overdue",
        followUp=FollowUpInfo(
            nudgeCount=2,
            note="Chased 2×",
            actionType="escalate",
        ),
    ),
    Commitment(
        id="com-2",
        title="Finalize checkout API spec",
        category="doc",
        assignee="Sam",
        sourceMeeting="Monday Product Sync",
        sourceDate="Aug 27",
        due="no due date",
        status="blocked",
        followUp=FollowUpInfo(
            note="Sam replied: blocked",
            actionType="unblock",
        ),
    ),
    Commitment(
        id="com-3",
        title="Email Acme — pricing & bulk discount",
        category="email",
        assignee="Alex",
        sourceMeeting="Monday Product Sync",
        sourceDate="Aug 27",
        due="today",
        status="needs_approval",
        followUp=FollowUpInfo(
            note="Needs your OK",
            actionType="review",
        ),
    ),
    # In progress
    Commitment(
        id="com-4",
        title="Write checkout API spec doc",
        category="doc",
        assignee="Sam",
        sourceMeeting="Monday Product Sync",
        sourceDate="Aug 27",
        due="this morning",
        status="in_progress",
        followUp=FollowUpInfo(
            note="On track",
        ),
    ),
    Commitment(
        id="com-5",
        title="Prep slides for design review",
        category="task",
        assignee="Alex",
        sourceMeeting="Design weekly",
        sourceDate="Aug 25",
        due="due Thu",
        status="in_progress",
        followUp=FollowUpInfo(
            nextNudge="Wed",
            note="Nudge scheduled Wed",
        ),
    ),
    Commitment(
        id="com-6",
        title="Notify #frontend: endpoints ready Friday",
        category="slack",
        assignee=None,
        sourceMeeting="Monday Product Sync",
        sourceDate="Aug 27",
        due="Fri",
        status="in_progress",
        followUp=FollowUpInfo(
            note="Queued to post",
        ),
    ),
    # Recently done
    Commitment(
        id="com-7",
        title="Booked design review · Thu 2:00 PM",
        category="calendar",
        assignee="Alex",
        sourceMeeting="Monday Product Sync",
        sourceDate="Aug 27",
        due="completed",
        status="done",
        followUp=FollowUpInfo(
            note="Invite sent · 2m ago",
        ),
    ),
    Commitment(
        id="com-8",
        title="Filed bug #PROD-482 · login crash",
        category="task",
        assignee="Alex",
        sourceMeeting="Monday Product Sync",
        sourceDate="Aug 27",
        due="completed",
        status="done",
        followUp=FollowUpInfo(
            note="Auto-closed · Sam confirmed",
        ),
    ),
    Commitment(
        id="com-9",
        title="Shared competitor pricing brief",
        category="research",
        assignee="Sam",
        sourceMeeting="Monday Product Sync",
        sourceDate="Aug 27",
        due="completed",
        status="done",
        followUp=FollowUpInfo(
            note="Posted to #product",
        ),
    ),
]

def seed():
    emulator_host = os.getenv("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")
    os.environ["FIRESTORE_EMULATOR_HOST"] = emulator_host
    print(f"Connecting to Firestore (FIRESTORE_EMULATOR_HOST={emulator_host})...")
    
    # 1. Create meeting
    print(f"Seeding meeting '{MEETING_ID}'...")
    create_meeting(
        meeting_id=MEETING_ID,
        title="Monday Product Sync",
        date="Aug 27",
        status="live",
        started_at="02:14",
    )
    
    # 2. Seed transcript lines
    print(f"Seeding {len(transcript_seed)} transcript lines...")
    for line in transcript_seed:
        add_transcript_line(MEETING_ID, line)
        
    # 3. Seed live actions
    print(f"Seeding {len(actions_seed)} live actions...")
    for action in actions_seed:
        upsert_action(MEETING_ID, action)
        
    # 4. Seed commitments
    print(f"Seeding {len(commitments_seed)} commitments...")
    for commitment in commitments_seed:
        upsert_commitment(commitment)
        
    print("✅ Firestore emulator seeding complete!")

if __name__ == "__main__":
    seed()
