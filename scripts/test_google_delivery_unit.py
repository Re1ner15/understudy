#!/usr/bin/env python3
"""Comprehensive Unit Tests for Google Workspace Delivery Module & Wiring."""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Ensure root workspace is on path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ["MOCK_AGENT"] = "1"
os.environ["GOOGLE_CLOUD_PROJECT"] = "demo-understudy"

from understudy_agent import google_delivery
from understudy_agent.schemas import ActionItem, ToolResult, LiveAction, EmailDraft, CalendarEvent, DocDraft
from understudy_agent.tools import handlers as tool_handlers
from understudy_agent import server
from understudy_agent import slack_app
from understudy_agent import ledger

# In-memory Firestore mocks
class InMemoryFirestore:
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

    def to_dict(self):
        return dict(self._data) if self._data else {}

class MockCollectionRef:
    def __init__(self, store, path_parts):
        self.store = store
        self.path_parts = path_parts

    def document(self, doc_id):
        return MockDocRef(self.store, self.path_parts + [doc_id])

    def stream(self):
        current = self.store
        for p in self.path_parts:
            if not isinstance(current, dict) or p not in current:
                return []
            current = current[p]
        if not isinstance(current, dict):
            return []
        snapshots = []
        for doc_id, data in current.items():
            if isinstance(data, dict):
                ref = MockDocRef(self.store, self.path_parts + [doc_id])
                snapshots.append(MockDocSnapshot(dict(data), ref=ref, exists=True))
        return snapshots


class TestGoogleDeliveryUnit(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.mock_db = InMemoryFirestore()
        self.db_patcher = patch.object(ledger, "get_db", return_value=self.mock_db)
        self.db_patcher.start()

    def tearDown(self):
        self.db_patcher.stop()

    def test_missing_credentials_raises_cleanly(self):
        """Tests that _get_credentials raises FileNotFoundError when token file is absent."""
        with patch.object(google_delivery, "TOKEN_FILE", Path("/tmp/non_existent_token_file.json")):
            with patch.object(google_delivery, "ROOT_DIR", Path("/tmp")):
                with self.assertRaises(FileNotFoundError) as ctx:
                    google_delivery._get_credentials()
                self.assertIn("Google Workspace credentials not found", str(ctx.exception))

    def test_parse_proposed_time_to_iso(self):
        """Tests natural language and ISO parsing for calendar events."""
        # 1. ISO string input
        iso_input = "2026-09-10T14:30:00+00:00"
        parsed = google_delivery.parse_proposed_time_to_iso(iso_input)
        self.assertEqual(parsed, iso_input)

        # 2. Natural language string (Thursday at 2pm)
        thu_parsed = google_delivery.parse_proposed_time_to_iso("Thursday at 2pm")
        self.assertIn("T14:00:00", thu_parsed)

        # 3. Empty or unparseable input falls back to Thursday 14:00
        fallback = google_delivery.parse_proposed_time_to_iso(None)
        self.assertIn("T14:00:00", fallback)

    @patch("understudy_agent.google_delivery._get_credentials")
    @patch("googleapiclient.discovery.build")
    def test_create_gmail_draft(self, mock_build, mock_get_creds):
        """Tests Gmail draft creation returns draftId and draft URL."""
        mock_get_creds.return_value = MagicMock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_drafts = MagicMock()
        mock_service.users().drafts.return_value = mock_drafts
        mock_drafts.create().execute.return_value = {"id": "draft_12345"}

        res = google_delivery.create_gmail_draft(
            to="test@example.com",
            subject="Test Subject",
            body="Test Body",
        )

        self.assertEqual(res["draftId"], "draft_12345")
        self.assertEqual(res["url"], "https://mail.google.com/mail/u/0/#drafts/draft_12345")

    @patch("understudy_agent.google_delivery._get_credentials")
    @patch("googleapiclient.discovery.build")
    def test_send_gmail_draft(self, mock_build, mock_get_creds):
        """Tests sending a Gmail draft returns messageId."""
        mock_get_creds.return_value = MagicMock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_drafts = MagicMock()
        mock_service.users().drafts.return_value = mock_drafts
        mock_drafts.send().execute.return_value = {"id": "msg_98765"}

        res = google_delivery.send_gmail_draft("draft_12345")
        self.assertEqual(res["messageId"], "msg_98765")

    @patch("understudy_agent.google_delivery._get_credentials")
    @patch("googleapiclient.discovery.build")
    def test_create_calendar_event(self, mock_build, mock_get_creds):
        """Tests Google Calendar event creation."""
        mock_get_creds.return_value = MagicMock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_events = MagicMock()
        mock_service.events.return_value = mock_events
        mock_events.insert().execute.return_value = {
            "id": "cal_evt_111",
            "htmlLink": "https://calendar.google.com/calendar/event?eid=cal_evt_111",
        }

        res = google_delivery.create_calendar_event(
            title="Sprint Planning",
            start_iso="2026-09-03T14:00:00",
            attendees=["alex@example.com", "Sam"],
        )

        self.assertEqual(res["eventId"], "cal_evt_111")
        self.assertEqual(res["htmlLink"], "https://calendar.google.com/calendar/event?eid=cal_evt_111")

    @patch("understudy_agent.google_delivery._get_credentials")
    @patch("googleapiclient.discovery.build")
    def test_create_google_doc(self, mock_build, mock_get_creds):
        """Tests Google Doc creation."""
        mock_get_creds.return_value = MagicMock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_docs = MagicMock()
        mock_service.documents.return_value = mock_docs
        mock_docs.create().execute.return_value = {"documentId": "doc_xyz789"}
        mock_docs.batchUpdate().execute.return_value = {}

        res = google_delivery.create_google_doc(
            title="Tech Spec",
            content="Architecture details",
        )

        self.assertEqual(res["docId"], "doc_xyz789")
        self.assertEqual(res["url"], "https://docs.google.com/document/d/doc_xyz789/edit")

    @patch.dict(os.environ, {"GOOGLE_WORKSPACE_ENABLED": "false"})
    @patch("understudy_agent.tools.handlers.gemini_json")
    async def test_handlers_mock_path_when_disabled(self, mock_gemini):
        """Verifies handlers use mock branch when GOOGLE_WORKSPACE_ENABLED is unset/false."""
        mock_gemini.side_effect = [
            EmailDraft(subject="Pricing Tiers", body="Hello Acme"),
            CalendarEvent(title="Design Review", proposed_time="Thursday at 2pm", attendees=["Alex", "Sam"]),
            DocDraft(title="API Spec", content="API Details"),
        ]

        # 1. draft_email
        email_item = ActionItem(
            id="ai-email-test",
            text="Email Acme about pricing tiers",
            category="email",
            assignee="Alex",
            due="today",
            source_quote="I'll email Acme today",
            confidence=0.95,
        )
        res = await tool_handlers.draft_email(email_item)
        self.assertEqual(res.status, "needs_approval")
        self.assertTrue(res.requires_approval)
        self.assertIsNone(res.draftId)
        self.assertNotIn("Draft ID:", res.artifact or "")

        # 2. create_calendar
        cal_item = ActionItem(
            id="ai-cal-test",
            text="Schedule design review",
            category="calendar",
            assignee="Sam",
            due="Thursday at 2pm",
            source_quote="book a design review",
            confidence=0.95,
        )
        cal_res = await tool_handlers.create_calendar(cal_item)
        self.assertEqual(cal_res.status, "done")
        self.assertIn("https://calendar.google.com/mock/", cal_res.artifact or "")

        # 3. create_doc
        doc_item = ActionItem(
            id="ai-doc-test",
            text="Write API spec",
            category="doc",
            assignee="Sam",
            due="today",
            source_quote="write spec",
            confidence=0.95,
        )
        doc_res = await tool_handlers.create_doc(doc_item)
        self.assertEqual(doc_res.status, "done")
        self.assertIn("https://docs.google.com/mock/", doc_res.artifact or "")

    @patch.dict(os.environ, {"GOOGLE_WORKSPACE_ENABLED": "true"})
    @patch("understudy_agent.tools.handlers.gemini_json")
    @patch("understudy_agent.google_delivery.create_gmail_draft")
    @patch("understudy_agent.google_delivery.create_calendar_event")
    @patch("understudy_agent.google_delivery.create_google_doc")
    async def test_handlers_google_workspace_enabled(self, mock_doc, mock_cal, mock_draft, mock_gemini):
        """Verifies handlers call real Google Workspace delivery when enabled."""
        mock_gemini.side_effect = [
            EmailDraft(subject="Pricing Tiers", body="Hello Acme"),
            CalendarEvent(title="Design Review", proposed_time="Thursday at 2pm", attendees=["Alex", "Sam"]),
            DocDraft(title="API Spec", content="API Details"),
        ]
        mock_draft.return_value = {"draftId": "live_draft_42", "url": "https://mail.google.com/mail/u/0/#drafts/live_draft_42"}
        mock_cal.return_value = {"eventId": "cal_live_99", "htmlLink": "https://calendar.google.com/calendar/event?eid=cal_live_99"}
        mock_doc.return_value = {"docId": "doc_live_88", "url": "https://docs.google.com/document/d/doc_live_88/edit"}

        # 1. draft_email
        email_item = ActionItem(
            id="ai-email-live",
            text="Email Acme about pricing tiers",
            category="email",
            assignee="alex@acme.com",
            due="today",
            source_quote="I'll email Acme today",
            confidence=0.95,
        )
        res = await tool_handlers.draft_email(email_item)
        self.assertEqual(res.status, "needs_approval")
        self.assertEqual(res.draftId, "live_draft_42")
        self.assertIn("https://mail.google.com/mail/u/0/#drafts/live_draft_42", res.artifact)
        mock_draft.assert_called_once_with(to="alex@acme.com", subject="Pricing Tiers", body="Hello Acme")

        # 2. create_calendar
        cal_item = ActionItem(
            id="ai-cal-live",
            text="Schedule design review",
            category="calendar",
            assignee="Sam",
            due="Thursday at 2pm",
            source_quote="book a design review",
            confidence=0.95,
        )
        cal_res = await tool_handlers.create_calendar(cal_item)
        self.assertEqual(cal_res.status, "done")
        self.assertIn("https://calendar.google.com/calendar/event?eid=cal_live_99", cal_res.artifact)

        # 3. create_doc
        doc_item = ActionItem(
            id="ai-doc-live",
            text="Write API spec",
            category="doc",
            assignee="Sam",
            due="today",
            source_quote="write spec",
            confidence=0.95,
        )
        doc_res = await tool_handlers.create_doc(doc_item)
        self.assertEqual(doc_res.status, "done")
        self.assertIn("https://docs.google.com/document/d/doc_live_88/edit", doc_res.artifact)

    @patch.dict(os.environ, {"GOOGLE_WORKSPACE_ENABLED": "true"})
    @patch("understudy_agent.google_delivery.send_gmail_draft")
    def test_send_on_approve_server(self, mock_send):
        """Verifies server.approve_action triggers send_gmail_draft when enabled."""
        mock_send.return_value = {"messageId": "live_msg_777"}

        meeting_id = "test-approve-meeting"
        action_id = "act-email-approve"

        # Create action in ledger
        action = LiveAction(
            id=action_id,
            itemId="ai-100",
            category="email",
            title="Email Acme",
            status="needs_approval",
            reasoning="Drafted email",
            artifact="Draft URL: https://mail.google.com/mail/u/0/#drafts/draft_live_100\nDraft ID: draft_live_100",
            draftId="draft_live_100",
            requiresApproval=True,
        )
        ledger.upsert_action(meeting_id, action)

        # Call approve_action
        resp = server.approve_action(meeting_id, action_id, approved_by="ranjit")
        self.assertEqual(resp["status"], "ok")
        self.assertEqual(resp["messageId"], "live_msg_777")
        mock_send.assert_called_once_with("draft_live_100")

        # Verify Firestore updated to done
        saved_action = ledger.get_action(meeting_id, action_id)
        self.assertEqual(saved_action["status"], "done")
        self.assertIn("Message ID: live_msg_777", saved_action["reasoning"])

    @patch.dict(os.environ, {"GOOGLE_WORKSPACE_ENABLED": "true"})
    @patch("understudy_agent.google_delivery.send_gmail_draft")
    @patch("slack_sdk.webhook.WebhookClient.send")
    @patch("slack_sdk.webhook.WebhookClient.send_dict")
    @patch("understudy_agent.slack_app.get_slack_client")
    def test_send_on_approve_slack_bolt(
        self,
        mock_slack_client,
        mock_send_dict,
        mock_send_webhook,
        mock_send,
    ):
        """Verifies Slack Bolt action_approve handler sends Gmail draft when enabled with zero network calls."""
        from slack_sdk import WebClient
        from slack_sdk.web.slack_response import SlackResponse
        mock_send.return_value = {"messageId": "slack_sent_msg_999"}
        mock_client_instance = WebClient(token="xoxb-mock-token")
        auth_resp = SlackResponse(
            client=mock_client_instance,
            http_verb="POST",
            api_url="https://slack.com/api/auth.test",
            req_args={},
            data={"ok": True, "bot_id": "B123", "user_id": "U123"},
            headers={"x-oauth-scopes": "chat:write,commands"},
            status_code=200,
        )
        mock_client_instance.auth_test = MagicMock(return_value=auth_resp)
        mock_client_instance.chat_update = MagicMock(return_value={"ok": True})
        mock_slack_client.return_value = mock_client_instance

        mock_webhook_resp = MagicMock(status_code=200, body="ok")
        mock_send_dict.return_value = mock_webhook_resp
        mock_send_webhook.return_value = mock_webhook_resp

        slack_app._app_instance = None

        meeting_id = "test-slack-meeting"
        action_id = "act-slack-email"

        action = LiveAction(
            id=action_id,
            itemId="ai-slack-1",
            category="email",
            title="Email Acme",
            status="needs_approval",
            reasoning="Drafted email",
            artifact="Draft URL: https://mail.google.com/mail/u/0/#drafts/draft_slack_55\nDraft ID: draft_slack_55",
            draftId="draft_slack_55",
            requiresApproval=True,
        )
        ledger.upsert_action(meeting_id, action)

        app = slack_app.create_app()
        from slack_bolt.request import BoltRequest
        body = {
            "type": "block_actions",
            "user": {"id": "U12345", "name": "alex"},
            "api_app_id": "A123",
            "container": {"type": "message"},
            "trigger_id": "trig123",
            "channel": {"id": "C123", "name": "under-study"},
            "message": {
                "ts": "1234567890.123456",
                "blocks": []
            },
            "response_url": "https://hooks.slack.com/actions/mock/response",
            "actions": [
                {
                    "action_id": "action_approve",
                    "block_id": "test_actions",
                    "text": {"type": "plain_text", "text": "Approve"},
                    "value": json.dumps({"meeting_id": meeting_id, "action_id": action_id, "title": "Email Acme"}),
                    "type": "button",
                    "action_ts": "1234567890.123456"
                }
            ]
        }
        req = BoltRequest(body=body, mode="socket_mode")
        resp = app.dispatch(req)

        self.assertEqual(resp.status, 200)
        mock_send.assert_called_once_with("draft_slack_55")

        saved_action = ledger.get_action(meeting_id, action_id)
        self.assertEqual(saved_action["status"], "done")
        self.assertIn("Message ID: slack_sent_msg_999", saved_action["reasoning"])


if __name__ == "__main__":
    unittest.main()
