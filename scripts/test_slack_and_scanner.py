import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Ensure understudy_agent package is discoverable
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

env_file = root_dir / "understudy_agent" / ".env"
load_dotenv(dotenv_path=env_file)
load_dotenv()

if "FIRESTORE_EMULATOR_HOST" not in os.environ:
    os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"

from understudy_agent.ledger import (
    get_commitment,
    get_action,
    update_action_status,
    update_commitment_status,
)
from understudy_agent.scanner import scan_and_nudge
from understudy_agent.slack_app import get_app
from scripts.seed_firestore import seed

class MockRespond:
    def __init__(self):
        self.calls = []
    def __call__(self, **kwargs):
        self.calls.append(kwargs)

def test_full_flow():
    print("--- 1. Seeding Firestore Emulator ---")
    seed()

    print("\n--- 2. Testing scan_and_nudge() ---")
    nudged = scan_and_nudge()
    assert len(nudged) >= 1, f"Expected at least 1 nudged item, got {len(nudged)}"
    
    com1 = get_commitment("com-1")
    assert com1 is not None, "com-1 not found"
    assert com1["followUp"]["nudgeCount"] == 3, f"Expected nudgeCount=3, got {com1['followUp']['nudgeCount']}"
    assert com1["followUp"]["note"] == "Escalated", f"Expected note='Escalated', got {com1['followUp']['note']}"
    assert com1["followUp"]["actionType"] == "escalate", "Expected actionType='escalate'"
    print("✅ scan_and_nudge verified com-1 escalated in Firestore!")

    print("\n--- 3. Testing Action Handlers on App ---")
    app = get_app()
    ack_called = []
    def mock_ack():
        ack_called.append(True)

    # 3. Test Bolt Dispatch for interactive actions
    import time
    from slack_bolt.request import BoltRequest

    def dispatch_action(action_id: str, value: str):
        body = {
            "type": "block_actions",
            "user": {"id": "U12345", "name": "ranjit"},
            "api_app_id": "A123",
            "container": {"type": "message"},
            "trigger_id": "trig123",
            "channel": {"id": "C123", "name": "under-study"},
            "message": {
                "ts": "1234567890.123456",
                "blocks": [
                    {
                        "type": "actions",
                        "block_id": "test_actions",
                        "elements": [{"type": "button", "action_id": action_id, "value": value}]
                    }
                ]
            },
            "response_url": "https://hooks.slack.com/actions/mock/response",
            "actions": [
                {
                    "action_id": action_id,
                    "block_id": "test_actions",
                    "text": {"type": "plain_text", "text": "Click"},
                    "value": value,
                    "type": "button",
                    "action_ts": "1234567890.123456"
                }
            ]
        }
        req = BoltRequest(body=body, mode="socket_mode")
        resp = app.dispatch(req)
        time.sleep(0.5)
        return resp

    print("Testing Bolt dispatch for 'commitment_done' on com-1...")
    resp = dispatch_action("commitment_done", json.dumps({"commitment_id": "com-1", "title": "Send Q3 pricing"}))
    assert resp.status == 200, f"Bolt returned status {resp.status}"
    com1_after = get_commitment("com-1")
    assert com1_after["status"] == "done", f"Expected done, got {com1_after['status']}"
    print("✅ Bolt dispatch commitment_done updated Firestore com-1 status to 'done'!")

    print("Testing Bolt dispatch for 'commitment_snooze' on com-4...")
    resp = dispatch_action("commitment_snooze", json.dumps({"commitment_id": "com-4", "title": "Write checkout API spec"}))
    assert resp.status == 200
    com4_after = get_commitment("com-4")
    assert com4_after["followUp"]["nextNudge"] == "Tomorrow 9:00 AM"
    print("✅ Bolt dispatch commitment_snooze updated Firestore com-4 nextNudge!")

    print("Testing Bolt dispatch for 'commitment_blocked' on com-5...")
    resp = dispatch_action("commitment_blocked", json.dumps({"commitment_id": "com-5", "title": "Prep slides"}))
    assert resp.status == 200
    com5_after = get_commitment("com-5")
    assert com5_after["status"] == "blocked"
    assert com5_after["followUp"]["actionType"] == "unblock"
    print("✅ Bolt dispatch commitment_blocked updated Firestore com-5 status to 'blocked'!")

    print("Testing Bolt dispatch for 'action_approve' on act-1...")
    resp = dispatch_action("action_approve", json.dumps({"meeting_id": "demo-meeting", "action_id": "act-1", "title": "Email Acme"}))
    assert resp.status == 200
    act1_after = get_action("demo-meeting", "act-1")
    assert act1_after["status"] == "done"
    print("✅ Bolt dispatch action_approve updated Firestore act-1 status to 'done'!")

    print("Testing Bolt dispatch for 'action_skip' on act-2...")
    resp = dispatch_action("action_skip", json.dumps({"meeting_id": "demo-meeting", "action_id": "act-2", "title": "Write API spec"}))
    assert resp.status == 200
    act2_after = get_action("demo-meeting", "act-2")
    assert act2_after["status"] == "error"
    print("✅ Bolt dispatch action_skip updated Firestore act-2 status to 'error'!")

    print("\n🎉 ALL TESTS AND DISPATCHES PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_full_flow()
