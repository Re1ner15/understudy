import os
import sys
import argparse
from datetime import datetime

from understudy_agent import ledger
from understudy_agent.schemas import ScreenContext
from understudy_agent.minutes import generate_minutes
from scripts.seed_firestore import seed, MEETING_ID

def main():
    parser = argparse.ArgumentParser(description="Test meeting minutes generation and persistence")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode without invoking Gemini API",
    )
    args = parser.parse_args()

    emulator_host = os.getenv("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")
    os.environ["FIRESTORE_EMULATOR_HOST"] = emulator_host
    print(f"Connecting to Firestore emulator at {emulator_host}...")

    # 1. Seed the emulator with standard demo meeting data
    print("\n--- Step 1: Seeding Firestore Emulator ---")
    seed()

    # 2. Add sample screen context for the meeting
    print("\n--- Step 2: Adding sample ScreenContext to meeting ---")
    sample_ctx = ScreenContext(
        kind="slide",
        summary="Architecture roadmap and checkout API specification overview slide",
        keyPoints=[
            "Tier 2 milestone: Screen awareness & meeting minutes generation",
            "Checkout endpoints contract delivery expected by Friday",
            "Design review sync booked for Thursday at 2:00 PM",
        ],
        ts="02:10",
    )
    ledger.add_screen_context(MEETING_ID, sample_ctx)
    print(f"Added screen context ({sample_ctx.kind}): '{sample_ctx.summary}'")

    # 3. Generate meeting minutes
    print(f"\n--- Step 3: Generating Minutes (mock={args.mock}) ---")
    minutes = generate_minutes(MEETING_ID, mock=args.mock)

    # 4. Display generated minutes
    print("\n" + "=" * 70)
    print("GENERATED MEETING MINUTES")
    print("=" * 70)
    print(f"Title:     {minutes.title}")
    print(f"Date:      {minutes.date}")
    print(f"Attendees: {', '.join(minutes.attendees)}")

    print("\n[Topics Discussed]")
    for topic in minutes.topics:
        print(f"• {topic.heading}:")
        print(f"  {topic.notes}")

    print("\n[Key Decisions]")
    for dec in minutes.decisions:
        print(f"• {dec}")

    print("\n[Materials Shown / Referenced]")
    for mat in minutes.materialsShown:
        print(f"• {mat}")

    print("\n[Action Items]")
    for item in minutes.actionItems:
        assignee = item.get("assignee") or "unassigned"
        due = item.get("due") or "no due date"
        print(f"• [{item.get('id', 'item')}] ({item.get('category', 'task')}) {item.get('text', '')} (Assignee: {assignee}, Due: {due})")
    print("=" * 70)

    # 5. Verify Firestore persistence
    print("\n--- Step 4: Verifying Firestore Persistence ---")
    saved_doc = ledger.get_minutes(MEETING_ID)
    if saved_doc is None:
        print("❌ FAILED: Minutes document was not found in Firestore!")
        sys.exit(1)

    print(f"✅ CONFIRMED: Minutes successfully saved to meetings/{MEETING_ID}/minutes/latest in Firestore.")
    print(f"Saved document title: '{saved_doc.get('title')}', topics count: {len(saved_doc.get('topics', []))}")

if __name__ == "__main__":
    main()
