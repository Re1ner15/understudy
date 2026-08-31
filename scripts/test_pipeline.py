import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# Ensure root directory is on sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

env_file = root_dir / "understudy_agent" / ".env"
load_dotenv(dotenv_path=env_file)
load_dotenv()

# Configure environment for emulator & mock mode
if "FIRESTORE_EMULATOR_HOST" not in os.environ:
    os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
if "GOOGLE_CLOUD_PROJECT" not in os.environ:
    os.environ["GOOGLE_CLOUD_PROJECT"] = "demo-understudy"

from understudy_agent import ledger

SERVER_URL = os.getenv("AGENT_SERVER_URL", "http://localhost:8000").rstrip("/")
MEETING_ID = "demo-meeting"

def test_pipeline():
    print("=" * 70)
    print("🚀 Running Understudy End-to-End Live Pipeline Integration Test")
    print(f"Server URL:         {SERVER_URL}")
    print(f"Firestore Emulator: {os.getenv('FIRESTORE_EMULATOR_HOST')}")
    print(f"Mock Agent Mode:    {os.getenv('MOCK_AGENT', '1')}")
    print("=" * 70)

    # 1. Health Check
    print("\n[Step 1] Checking Agent Server health...")
    try:
        resp = requests.get(f"{SERVER_URL}/health", timeout=5.0)
        assert resp.status_code == 200, f"Health check failed with code {resp.status_code}: {resp.text}"
        health_data = resp.json()
        assert health_data.get("status") == "ok", f"Unexpected health response: {health_data}"
        print(f"✅ Server is healthy! (Response: {health_data})")
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to server at {SERVER_URL}.")
        print("   Make sure to start the server in another terminal:")
        print("   MOCK_AGENT=1 FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 PYTHONPATH=. python scripts/run_server.py")
        sys.exit(1)

    # 2. Start Meeting
    print(f"\n[Step 2] Starting meeting '{MEETING_ID}'...")
    resp = requests.post(
        f"{SERVER_URL}/meetings/{MEETING_ID}/start",
        json={
            "title": "Monday Product Sync",
            "date": "Aug 27",
            "status": "live",
            "startedAt": "02:14",
            "reset": True,
        },
        timeout=5.0,
    )
    assert resp.status_code == 200, f"Failed to start meeting: {resp.text}"
    print(f"✅ Meeting '{MEETING_ID}' started successfully in Firestore.")

    # 3. Read demo fixture & stream utterances
    fixture_path = root_dir / "understudy_agent" / "fixtures" / "demo_meeting.txt"
    with open(fixture_path, "r") as f:
        raw_lines = [line.strip() for line in f if line.strip()]

    print(f"\n[Step 3] Streaming {len(raw_lines)} utterances to POST /meetings/{MEETING_ID}/utterance...")
    for idx, raw_line in enumerate(raw_lines):
        if ":" in raw_line:
            speaker, text = raw_line.split(":", 1)
            speaker = speaker.strip()
            text = text.strip()
        else:
            speaker = "Speaker"
            text = raw_line

        minute_offset = 6 + idx
        ts = f"02:{minute_offset:02d}"

        resp = requests.post(
            f"{SERVER_URL}/meetings/{MEETING_ID}/utterance",
            json={
                "speaker": speaker,
                "text": text,
                "ts": ts,
            },
            timeout=5.0,
        )
        assert resp.status_code == 200, f"Failed to post utterance: {resp.text}"
        print(f"  [{ts}] {speaker}: {text[:60]}...")
        time.sleep(0.05)

    # 4. Post screen context
    print(f"\n[Step 4] Posting screen context to POST /meetings/{MEETING_ID}/screen-context...")
    resp = requests.post(
        f"{SERVER_URL}/meetings/{MEETING_ID}/screen-context",
        json={
            "kind": "slide",
            "summary": "Architecture Roadmap & Checkout API Spec (Tier 2 milestone)",
            "keyPoints": [
                "Acme Pricing Tier comparison doc open",
                "Checkout Endpoints contract blocked awaiting SAM spec",
            ],
            "ts": "02:12",
        },
        timeout=5.0,
    )
    assert resp.status_code == 200, f"Failed to post screen context: {resp.text}"
    print("✅ Screen context posted.")

    # 5. Wait for debounced watcher and tool execution
    print("\n[Step 5] Waiting for debounced pipeline worker to process action items...")
    max_wait_seconds = 15
    start_wait = time.time()
    actions = []
    commitments = []

    while time.time() - start_wait < max_wait_seconds:
        actions = ledger.get_actions(MEETING_ID)
        commitments = ledger.get_commitments()
        if len(actions) >= 6 and all(a.get("status") in ["done", "needs_approval", "error"] for a in actions):
            break
        time.sleep(0.5)

    print(f"Found {len(actions)} actions and {len(commitments)} commitments in Firestore.")
    assert len(actions) >= 6, f"Expected at least 6 actions in Firestore, got {len(actions)}"
    assert len(commitments) >= 6, f"Expected at least 6 commitments in Firestore, got {len(commitments)}"

    # 6. Verify Action Details & Commitments Mirroring
    print("\n[Step 6] Verifying action items and commitments in Firestore:")
    print("-" * 80)
    print(f"{'ID':<12} | {'Category':<10} | {'Status':<15} | {'Assignee':<8} | {'Title'}")
    print("-" * 80)

    categories_found = set()
    for act in sorted(actions, key=lambda a: a.get("id", "")):
        aid = act.get("id", "")
        cat = act.get("category", "")
        st = act.get("status", "")
        assignee = act.get("assignee") or "-"
        title = act.get("title", "")
        artifact = act.get("artifact")

        categories_found.add(cat)
        print(f"{aid:<12} | {cat:<10} | {st:<15} | {assignee:<8} | {title[:35]}")
        assert artifact is not None and len(artifact) > 0, f"Action {aid} missing artifact"

        # Check corresponding commitment
        comm_obj = ledger.action_to_commitment(act, "Monday Product Sync", "Aug 27")
        comm_id = comm_obj.id
        comm = ledger.get_commitment(comm_id)
        assert comm is not None, f"Commitment {comm_id} not mirrored in Firestore!"
        assert comm.get("title") == title, f"Commitment title mismatch for {comm_id}"

    # Verify all expected categories are present
    expected_categories = {"email", "research", "doc", "calendar", "slack", "task"}
    missing_cats = expected_categories - categories_found
    assert not missing_cats, f"Missing action categories in Firestore: {missing_cats}"

    # Verify email action requires approval
    email_actions = [a for a in actions if a.get("category") == "email"]
    assert len(email_actions) > 0, "No email action found"
    assert email_actions[0].get("status") == "needs_approval", f"Email action status should be 'needs_approval', got {email_actions[0].get('status')}"
    assert email_actions[0].get("requiresApproval") is True, "Email action requiresApproval should be True"

    print("-" * 80)
    print("✅ All 6 action items & mirrored commitments verified with correct statuses and artifacts!")

    # 7. End Meeting & Generate Minutes
    print(f"\n[Step 7] Ending meeting via POST /meetings/{MEETING_ID}/end...")
    resp = requests.post(f"{SERVER_URL}/meetings/{MEETING_ID}/end", json={"mock": True}, timeout=10.0)
    assert resp.status_code == 200, f"Failed to end meeting: {resp.text}"
    end_data = resp.json()
    minutes = end_data.get("minutes")
    assert minutes is not None, "Minutes missing from end meeting response"
    assert len(minutes.get("topics", [])) > 0, "Minutes topics should not be empty"

    saved_minutes = ledger.get_minutes(MEETING_ID)
    assert saved_minutes is not None, "Minutes not saved to Firestore!"
    print(f"✅ Meeting ended and minutes saved to Firestore! (Title: '{saved_minutes.get('title')}')")

    # 8. Trigger Scanner
    print("\n[Step 8] Triggering scanner via POST /scan...")
    resp = requests.post(f"{SERVER_URL}/scan", timeout=5.0)
    assert resp.status_code == 200, f"Failed to trigger scan: {resp.text}"
    scan_data = resp.json()
    assert scan_data.get("status") == "ok", f"Scanner endpoint returned error: {scan_data}"
    print(f"✅ Scanner endpoint triggered successfully! (Nudged count: {len(scan_data.get('nudged', []))})")

    print("\n" + "=" * 70)
    print("🎉 ALL PIPELINE INTEGRATION TESTS PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == "__main__":
    test_pipeline()
