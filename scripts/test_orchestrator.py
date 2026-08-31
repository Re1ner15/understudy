import os
import sys
import argparse
import asyncio
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from understudy_agent.watcher import watcher
from understudy_agent.orchestrator import orchestrate
from understudy_agent.schemas import ActionItemBatch, ActionItem

def get_mock_batch() -> ActionItemBatch:
    return ActionItemBatch(items=[
        ActionItem(
            id="ai-1",
            text="Email Acme to get clarity on new pricing tiers and ask if we qualify for bulk discount",
            category="email",
            assignee="Alex",
            due="today",
            source_quote="I'll email Acme today to get clarity on the new tiers and ask if we qualify for a bulk discount.",
            confidence=0.95,
        ),
        ActionItem(
            id="ai-2",
            text="Research competitor pricing for comparable analytics add-on",
            category="research",
            assignee="Alex",
            due=None,
            source_quote="can you research what two or three competitors charge for a comparable analytics add-on?",
            confidence=0.95,
        ),
        ActionItem(
            id="ai-3",
            text="Write up a one-page API spec doc for checkout endpoints",
            category="doc",
            assignee="Sam",
            due="this morning",
            source_quote="Can you write up a one-page API spec doc for the checkout endpoints so they can start?",
            confidence=0.95,
        ),
        ActionItem(
            id="ai-4",
            text="Book a design review with the design team",
            category="calendar",
            assignee="Sam",
            due="Thursday at 2pm",
            source_quote="book a design review for Thursday at 2pm with the design team.",
            confidence=0.95,
        ),
        ActionItem(
            id="ai-5",
            text="Ping frontend team that endpoints will be ready by Friday",
            category="slack",
            assignee="Alex",
            due="Friday",
            source_quote="ping the frontend team on Slack that the endpoints will be ready by Friday.",
            confidence=0.95,
        ),
        ActionItem(
            id="ai-6",
            text="File a bug for the login crash on quick logout/login",
            category="task",
            assignee="Alex",
            due=None,
            source_quote="Let's file a bug for the login crash so it doesn't slip.",
            confidence=0.95,
        ),
    ])

async def get_watcher_batch(fixture_filename: str = "demo_meeting.txt") -> ActionItemBatch:
    fixture_path = os.path.join(
        os.path.dirname(__file__), "..", "understudy_agent", "fixtures", fixture_filename
    )
    with open(fixture_path, "r") as f:
        transcript = f.read()

    print(f"Running watcher agent on {fixture_filename}...")
    runner = InMemoryRunner(agent=watcher)
    
    retries = [2, 5, 10]
    for attempt in range(len(retries) + 1):
        try:
            events = await runner.run_debug(transcript)
            for event in events:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            try:
                                return ActionItemBatch.model_validate_json(part.text)
                            except Exception:
                                pass
                if hasattr(event, "output") and event.output is not None:
                    if isinstance(event.output, ActionItemBatch):
                        return event.output
                    elif isinstance(event.output, str):
                        try:
                            return ActionItemBatch.model_validate_json(event.output)
                        except Exception:
                            pass
        except Exception as e:
            err_str = str(e)
            if attempt < len(retries) and (
                "503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str or "RESOURCE_EXHAUSTED" in err_str
            ):
                print(f"Watcher hit {e}, retrying in {retries[attempt]}s...")
                await asyncio.sleep(retries[attempt])
            else:
                raise e

    raise RuntimeError("Failed to extract ActionItemBatch from watcher agent events")

async def main():
    parser = argparse.ArgumentParser(description="Test Understudy orchestrator")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use hardcoded mock batch instead of calling watcher agent",
    )
    args = parser.parse_args()

    load_dotenv("understudy_agent/.env")
    load_dotenv()

    if args.mock:
        print("Using mock ActionItemBatch...")
        batch = get_mock_batch()
    else:
        batch = await get_watcher_batch("demo_meeting.txt")

    print(f"\nExtracted {len(batch.items)} action items:")
    for item in batch.items:
        assignee = item.assignee or "unassigned"
        due = item.due or "no due date"
        print(f" - [{item.id}] ({item.category}) {item.text} [Assignee: {assignee}, Due: {due}]")

    print("\n--- Starting Orchestrator ---")
    results = await orchestrate(batch)

    print("\n--- Summary Table ---")
    print(f"{'ID':<6} | {'Category':<10} | {'Status':<15} | {'Summary'}")
    print("-" * 80)
    for res in results:
        print(f"{res.item_id:<6} | {res.category:<10} | {res.status:<15} | {res.summary}")

    print("\n--- Artifacts ---")
    for res in results:
        print(f"\n[{res.item_id} - {res.category.upper()}]")
        if res.artifact:
            print(res.artifact)
        else:
            print("No artifact generated.")

if __name__ == "__main__":
    asyncio.run(main())
