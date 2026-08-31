import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from dotenv import load_dotenv

# Ensure root directory is on sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

env_file = root_dir / "understudy_agent" / ".env"
load_dotenv(dotenv_path=env_file)
load_dotenv()

os.environ["MOCK_AGENT"] = "1"
os.environ["GOOGLE_CLOUD_PROJECT"] = "demo-understudy"

from understudy_agent.schemas import (
    ActionItem,
    Clarification,
    LiveAction,
    Commitment,
)
from understudy_agent import ledger
from understudy_agent import server
from understudy_agent import slack_app
from fastapi.testclient import TestClient

class InMemoryFirestore:
    """Lightweight in-memory Firestore mock to test ledger & pipeline without emulator."""
    def __init__(self):
        self.store = {}

    def collection(self, col_name):
        return MockCollectionRef(self.store, [col_name])

class MockDocRef:
    def __init__(self, store, path_parts):
        self.store = store
        self.path_parts = path_parts
        self.id = path_parts[-1]

    def set(self, data, merge=False):
        current = self.store
        for p in self.path_parts[:-1]:
            current = current.setdefault(p, {})
        doc_id = self.path_parts[-1]
        if merge and doc_id in current and isinstance(current[doc_id], dict):
            current[doc_id].update(data)
        else:
            current[doc_id] = dict(data)

    def update(self, data):
        current = self.store
        for p in self.path_parts[:-1]:
            current = current.setdefault(p, {})
        doc_id = self.path_parts[-1]
        if doc_id not in current:
            current[doc_id] = {}
        current[doc_id].update(data)

    def get(self):
        current = self.store
        for p in self.path_parts:
            if not isinstance(current, dict) or p not in current:
                return MockDocSnapshot(None, ref=self, exists=False)
            current = current[p]
        return MockDocSnapshot(dict(current), ref=self, exists=True)

    def delete(self):
        current = self.store
        for p in self.path_parts[:-1]:
            if not isinstance(current, dict) or p not in current:
                return
            current = current[p]
        doc_id = self.path_parts[-1]
        if isinstance(current, dict) and doc_id in current:
            del current[doc_id]

    def collection(self, subcol_name):
        return MockCollectionRef(self.store, self.path_parts + [subcol_name])

class MockDocSnapshot:
    def __init__(self, data, ref=None, exists=True):
        self._data = data
        self.reference = ref
        self.exists = exists
        self.id = ref.id if ref else None

    def to_dict(self):
        return dict(self._data) if self._data else {}


class MockCollectionRef:
    def __init__(self, store, path_parts):
        self.store = store
        self.path_parts = path_parts

    def document(self, doc_id=None):
        if doc_id is None:
            import uuid
            doc_id = f"auto-{uuid.uuid4().hex[:8]}"
        return MockDocRef(self.store, self.path_parts + [doc_id])

    def stream(self):
        current = self.store
        for p in self.path_parts:
            if not isinstance(current, dict) or p not in current:
                return []
            current = current[p]
        results = []
        if isinstance(current, dict):
            for k, v in current.items():
                if isinstance(v, dict):
                    results.append(MockDocRef(self.store, self.path_parts + [k]).get())
        return results

    def where(self, filter=None):
        return self


class TestClarificationPipeline(unittest.TestCase):
    def setUp(self):
        self.mock_db = InMemoryFirestore()
        self.db_patcher = patch("understudy_agent.ledger.get_db", return_value=self.mock_db)
        self.db_patcher.start()
        self.client = TestClient(server.app)

    def tearDown(self):
        self.db_patcher.stop()

    def test_schema_clarification(self):
        """Test Clarification schema creation, validation, and JSON roundtrip."""
        item = ActionItem(
            id="ai-1",
            text="Follow up with the vendor",
            category="email",
            assignee=None,
            due=None,
            source_quote="someone should follow up with the vendor",
            confidence=0.5,
        )
        clar = Clarification(
            id="clar-ai-1",
            meetingId="demo-meeting",
            question="Who should follow up with the vendor regarding the pricing tiers?",
            relatedText=item.text,
            status="open",
            actionItem=item,
        )
        self.assertEqual(clar.id, "clar-ai-1")
        self.assertEqual(clar.status, "open")
        self.assertIsNone(clar.answer)
        self.assertEqual(clar.actionItem.confidence, 0.5)

        data = clar.model_dump()
        self.assertEqual(data["question"], "Who should follow up with the vendor regarding the pricing tiers?")
        
        # Validation
        restored = Clarification.model_validate(data)
        self.assertEqual(restored.id, "clar-ai-1")
        self.assertEqual(restored.status, "open")

    def test_ledger_clarification_crud(self):
        """Test ledger add_clarification, get_clarification, answer_clarification, find_clarification."""
        meeting_id = "test-meeting-1"
        clar = Clarification(
            id="clar-vendor-1",
            meetingId=meeting_id,
            question="Who should contact Acme?",
            relatedText="Follow up with Acme",
            status="open",
        )
        
        # 1. Add
        saved = ledger.add_clarification(meeting_id, clar)
        self.assertEqual(saved["id"], "clar-vendor-1")
        self.assertEqual(saved["status"], "open")

        # 2. Get single
        retrieved = ledger.get_clarification(meeting_id, "clar-vendor-1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["question"], "Who should contact Acme?")

        # 3. Get list
        all_clars = ledger.get_clarifications(meeting_id)
        self.assertEqual(len(all_clars), 1)

        # 4. Find across meetings
        found_mid, found_doc = ledger.find_clarification("clar-vendor-1")
        self.assertEqual(found_mid, meeting_id)
        self.assertEqual(found_doc["id"], "clar-vendor-1")

        # 5. Answer
        updated = ledger.answer_clarification(meeting_id, "clar-vendor-1", answer="Alex", status="answered")
        self.assertEqual(updated["status"], "answered")
        self.assertEqual(updated["answer"], "Alex")

        # 6. Clear meeting data
        ledger.clear_meeting_data(meeting_id)
        self.assertEqual(len(ledger.get_clarifications(meeting_id)), 0)

    def test_ambiguity_detection(self):
        """Test is_ambiguous_item logic for low confidence and missing assignees."""
        # Ambiguous: confidence < 0.6
        item_low_conf = ActionItem(
            id="ai-1",
            text="Check pricing",
            category="research",
            assignee="Alex",
            source_quote="Alex might check pricing",
            confidence=0.55,
        )
        self.assertTrue(server.is_ambiguous_item(item_low_conf))

        # Ambiguous: no assignee
        item_no_assignee = ActionItem(
            id="ai-2",
            text="Follow up with the vendor",
            category="email",
            assignee=None,
            source_quote="Someone should email vendor",
            confidence=0.9,
        )
        self.assertTrue(server.is_ambiguous_item(item_no_assignee))

        # Ambiguous: placeholder assignee
        item_placeholder_assignee = ActionItem(
            id="ai-3",
            text="File bug",
            category="task",
            assignee="someone",
            source_quote="someone file bug",
            confidence=0.9,
        )
        self.assertTrue(server.is_ambiguous_item(item_placeholder_assignee))

        # Non-ambiguous: confident & named assignee
        item_clear = ActionItem(
            id="ai-4",
            text="Write API spec",
            category="doc",
            assignee="Sam",
            source_quote="Sam write doc",
            confidence=0.95,
        )
        self.assertFalse(server.is_ambiguous_item(item_clear))

    def test_generate_clarifying_question(self):
        """Test generate_clarifying_question in mock mode."""
        item = ActionItem(
            id="ai-vendor",
            text="Follow up with the vendor regarding pricing tiers",
            category="email",
            assignee=None,
            source_quote="someone should follow up with the vendor",
            confidence=0.5,
        )
        import asyncio
        question = asyncio.run(server.generate_clarifying_question(item))
        self.assertIn("vendor", question.lower())
        self.assertIn("Who should", question)

    @patch("understudy_agent.slack_app.get_app")
    def test_pipeline_confidence_gating_acceptance(self, mock_get_slack_app):
        """Acceptance test: Posting transcript containing 'someone should follow up with the vendor'
        creates an open Clarification in Firestore and posts to Slack, instead of blindly executing.
        """
        mock_slack_client = MagicMock()
        mock_slack_app_instance = MagicMock()
        mock_slack_app_instance.client = mock_slack_client
        mock_get_slack_app.return_value = mock_slack_app_instance

        meeting_id = "test-gating-meeting"
        ledger.create_meeting(meeting_id, title="Product Sync", date="Aug 27")

        # 1. Add ambiguous transcript utterance
        resp = self.client.post(
            f"/meetings/{meeting_id}/utterance?sync=true",
            json={
                "speaker": "ALEX",
                "text": "Yeah, someone should follow up with the vendor on pricing tiers.",
                "ts": "02:05",
            },
        )
        self.assertEqual(resp.status_code, 200)

        # 2. Check Firestore clarifications
        clarifications = ledger.get_clarifications(meeting_id)
        self.assertEqual(len(clarifications), 1, "Expected 1 clarification created in Firestore")
        
        clar = clarifications[0]
        self.assertEqual(clar["status"], "open")
        self.assertIn("vendor", clar["question"].lower())
        self.assertEqual(clar["relatedText"], "Follow up with the vendor regarding pricing tiers")
        self.assertIsNone(clar.get("answer"))

        # 3. Check that NO LiveAction was created/auto-executed prematurely
        actions = ledger.get_actions(meeting_id)
        self.assertEqual(len(actions), 0, "No action should be auto-executed for ambiguous item")

        # 4. Check that Slack post_clarification was called
        self.assertTrue(mock_slack_client.chat_postMessage.called)
        call_kwargs = mock_slack_client.chat_postMessage.call_args[1]
        blocks = call_kwargs.get("blocks", [])
        self.assertTrue(any("Clarification Needed" in str(b) for b in blocks))
        self.assertTrue(any("clarification_quick_reply" in str(b) for b in blocks))
        print("✅ Acceptance test verified: Clarification created & posted to Slack without auto-executing!")

    @patch("understudy_agent.slack_app.get_app")
    def test_resume_clarification_execution(self, mock_get_slack_app):
        """Test answering a clarification via API / Slack and resuming execution."""
        mock_slack_client = MagicMock()
        mock_slack_app_instance = MagicMock()
        mock_slack_app_instance.client = mock_slack_client
        mock_get_slack_app.return_value = mock_slack_app_instance

        meeting_id = "test-resume-meeting"
        ledger.create_meeting(meeting_id, title="Product Sync", date="Aug 27")

        # 1. Post utterance to create clarification
        self.client.post(
            f"/meetings/{meeting_id}/utterance?sync=true",
            json={
                "speaker": "ALEX",
                "text": "someone should follow up with the vendor",
                "ts": "02:05",
            },
        )
        clarifications = ledger.get_clarifications(meeting_id)
        self.assertEqual(len(clarifications), 1)
        clar_id = clarifications[0]["id"]

        # 2. Answer clarification via API endpoint
        resp = self.client.post(
            f"/meetings/{meeting_id}/clarifications/{clar_id}/answer",
            json={"answer": "Alex"},
        )
        self.assertEqual(resp.status_code, 200)
        res_data = resp.json()
        self.assertEqual(res_data["status"], "ok")

        # 3. Verify clarification is marked 'answered'
        updated_clar = ledger.get_clarification(meeting_id, clar_id)
        self.assertEqual(updated_clar["status"], "answered")
        self.assertEqual(updated_clar["answer"], "Alex")

        # 4. Verify action was executed and created
        actions = ledger.get_actions(meeting_id)
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action["assignee"], "Alex")
        self.assertEqual(action["category"], "email")
        self.assertEqual(action["status"], "needs_approval") # email drafts require approval
        self.assertIsNotNone(action.get("artifact"))

        # 5. Verify commitment was mirrored
        commitments = ledger.get_commitments()
        self.assertTrue(len(commitments) >= 1)
        self.assertTrue(any(c.get("assignee") == "Alex" for c in commitments))
        print("✅ Resume execution verified: answering clarification completed pipeline!")

    @patch("slack_sdk.webhook.client.WebhookClient.send_dict", return_value=MagicMock(status_code=200, body="ok"))
    @patch("slack_sdk.web.client.WebClient.auth_test")
    def test_slack_bolt_clarification_dispatch(self, mock_auth_test, mock_webhook_send):
        """Test Slack Bolt interactive action handlers for quick-reply and dismiss."""
        mock_resp = MagicMock()
        mock_resp.headers = {"x-oauth-scopes": "chat:write,commands"}
        mock_resp.data = {"ok": True, "user_id": "BOT123", "bot_id": "B123"}
        mock_resp.get.side_effect = lambda k, d=None: mock_resp.data.get(k, d)
        mock_resp.__getitem__.side_effect = lambda k: mock_resp.data[k]
        mock_auth_test.return_value = mock_resp

        app = slack_app.create_app()
        from slack_bolt.request import BoltRequest

        meeting_id = "test-bolt-meeting"
        ledger.create_meeting(meeting_id, title="Product Sync", date="Aug 27")


        item = ActionItem(
            id="ai-vendor-test",
            text="Follow up with the vendor",
            category="email",
            assignee=None,
            source_quote="someone should follow up",
            confidence=0.5,
        )
        clar = Clarification(
            id="clar-test-1",
            meetingId=meeting_id,
            question="Who should follow up?",
            relatedText="Follow up with the vendor",
            status="open",
            actionItem=item,
        )
        ledger.add_clarification(meeting_id, clar)

        # Dispatch quick reply "Assign to Sam"
        body = {
            "type": "block_actions",
            "user": {"id": "U999", "name": "ranjit"},
            "channel": {"id": "C123", "name": "under-study"},
            "message": {"ts": "1234567890.000100", "blocks": []},
            "response_url": "https://hooks.slack.com/actions/mock",
            "actions": [
                {
                    "action_id": "clarification_quick_reply",
                    "value": json.dumps({
                        "meeting_id": meeting_id,
                        "clarification_id": "clar-test-1",
                        "answer": "Sam",
                    })
                }
            ]
        }
        req = BoltRequest(body=body, mode="socket_mode")
        resp = app.dispatch(req)
        self.assertEqual(resp.status, 200)

        updated_clar = ledger.get_clarification(meeting_id, "clar-test-1")
        self.assertEqual(updated_clar["status"], "answered")
        self.assertEqual(updated_clar["answer"], "Sam")

        # Test dismiss
        clar_dismiss = Clarification(
            id="clar-test-2",
            meetingId=meeting_id,
            question="Who should follow up?",
            relatedText="Follow up with the vendor",
            status="open",
        )
        ledger.add_clarification(meeting_id, clar_dismiss)

        body_dismiss = {
            "type": "block_actions",
            "user": {"id": "U999", "name": "ranjit"},
            "channel": {"id": "C123", "name": "under-study"},
            "message": {"ts": "1234567890.000100", "blocks": []},
            "response_url": "https://hooks.slack.com/actions/mock",
            "actions": [
                {
                    "action_id": "clarification_dismiss",
                    "value": json.dumps({
                        "meeting_id": meeting_id,
                        "clarification_id": "clar-test-2",
                    })
                }
            ]
        }
        req_dismiss = BoltRequest(body=body_dismiss, mode="socket_mode")
        resp_dismiss = app.dispatch(req_dismiss)
        self.assertEqual(resp_dismiss.status, 200)

        updated_dismiss = ledger.get_clarification(meeting_id, "clar-test-2")
        self.assertEqual(updated_dismiss["status"], "dismissed")
        print("✅ Slack Bolt interactive handlers verified for quick reply & dismiss!")

if __name__ == "__main__":
    unittest.main()
