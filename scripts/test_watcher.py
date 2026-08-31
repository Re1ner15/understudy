import os
import asyncio
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from understudy_agent.watcher import watcher

def main():
    # Load environment variables
    load_dotenv("understudy_agent/.env")
    
    # Read the fixture
    fixture_path = os.path.join(os.path.dirname(__file__), "..", "understudy_agent", "fixtures", "sample_meeting.txt")
    with open(fixture_path, "r") as f:
        transcript = f.read()

    # Run the watcher agent
    print("Running watcher agent on transcript...")
    
    async def run():
        runner = InMemoryRunner(agent=watcher)
        events = await runner.run_debug(transcript)
        
        batch = None
        for event in events:
            if event.content and event.content.parts:
                text = event.content.parts[0].text
                try:
                    from understudy_agent.schemas import ActionItemBatch
                    batch = ActionItemBatch.model_validate_json(text)
                except Exception:
                    pass
        return batch

    batch = asyncio.run(run())
    
    # Print the table header
    print(f"{'ID':<6} | {'Category':<10} | {'Assignee':<10} | {'Due':<12} | {'Text'}")
    print("-" * 80)
    
    # Print the table rows
    if batch and hasattr(batch, 'items'):
        for item in batch.items:
            # Handle Optional fields
            assignee = item.assignee if item.assignee else "N/A"
            due = item.due if item.due else "N/A"
            print(f"{item.id:<6} | {item.category:<10} | {assignee:<10} | {due:<12} | {item.text}")
    else:
        print("No items extracted or invalid format.")

if __name__ == "__main__":
    main()
