import os
import sys
import json
import time
import unittest
from unittest.mock import patch, MagicMock
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
    LiveAction,
    GuardrailResult,
    Clarification,
    Commitment,
)
from understudy_agent.tracing import (
    span,
    Span,
    get_current_trace_id,
    get_current_span_id,
    get_current_meeting_id,
)
from understudy_agent import ledger
from understudy_agent import server
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
        if not doc_id:
            import uuid
            doc_id = f"auto-{uuid.uuid4().hex[:8]}"
        return MockDocRef(self.store, self.path_parts + [doc_id])

    def where(self, filter=None):
        return self

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
                snapshots.append(MockDocSnapshot(data, ref=ref, exists=True))
        return snapshots


class TestAgentObservabilityAndTracing(unittest.TestCase):
    def setUp(self):
        self.mock_db = InMemoryFirestore()
        self.patcher = patch("understudy_agent.ledger.get_db", return_value=self.mock_db)
        self.patcher.start()
        self.client = TestClient(server.app)

    def tearDown(self):
        self.patcher.stop()

    def test_span_context_manager_unit(self):
        """Tests span creation, attribute recording, latency computation, and parent-child linkage."""
        meeting_id = "test-unit-meeting"

        with span("root.operation", meeting_id=meeting_id, initial_attr="value1") as root:
            root_trace = get_current_trace_id()
            root_span_id = get_current_span_id()
            self.assertIsNotNone(root_trace)
            self.assertIsNotNone(root_span_id)
            self.assertEqual(root.trace_id, root_trace)
            self.assertEqual(root.span_id, root_span_id)
            self.assertIsNone(root.parent_id)

            time.sleep(0.01)

            with span("child.operation", category="doc") as child:
                self.assertEqual(child.trace_id, root_trace)
                self.assertEqual(child.parent_id, root_span_id)
                self.assertEqual(get_current_span_id(), child.span_id)
                child.set_attribute("doc_title", "API Spec")
                child.set_status("ok")

            # After child exit, current span should revert to root
            self.assertEqual(get_current_span_id(), root_span_id)

        # Verify audit logs in ledger
        audit_logs = ledger.get_audit_logs(meeting_id)
        self.assertEqual(len(audit_logs), 2)

        child_log = next(s for s in audit_logs if s["name"] == "child.operation")
        root_log = next(s for s in audit_logs if s["name"] == "root.operation")

        self.assertEqual(child_log["traceId"], root_log["traceId"])
        self.assertEqual(child_log["parentId"], root_log["spanId"])
        self.assertIsNone(root_log["parentId"])
        self.assertTrue(child_log["latencyMs"] >= 0)
        self.assertTrue(root_log["latencyMs"] >= 10)
        self.assertEqual(child_log["attributes"]["doc_title"], "API Spec")
        self.assertEqual(child_log["status"], "ok")

    def test_span_exception_handling(self):
        """Tests that exceptions inside a span are captured as status='error'."""
        meeting_id = "test-error-meeting"

        with self.assertRaises(ValueError):
            with span("failing.operation", meeting_id=meeting_id) as s:
                raise ValueError("Simulated failure")

        logs = ledger.get_audit_logs(meeting_id)
        self.assertEqual(len(logs), 1)
        err_span = logs[0]
        self.assertEqual(err_span["status"], "error")
        self.assertEqual(err_span["attributes"]["error"], "Simulated failure")
        self.assertEqual(err_span["attributes"]["errorType"], "ValueError")

    def test_mock_pipeline_reasoning_chain_trace(self):
        """End-to-end acceptance test: runs a mock pipeline and verifies

        linked reasoning-chain traces with OpenTelemetry schema in GET /meetings/{id}/audit.
        """
        meeting_id = "trace-e2e-meeting"

        # 1. Start meeting
        start_resp = self.client.post(
            f"/meetings/{meeting_id}/start",
            json={"title": "Observability Sync", "date": "Aug 28", "status": "live", "reset": True},
        )
        self.assertEqual(start_resp.status_code, 200)

        # 2. Add an utterance that triggers an action item (e.g. Email Acme)
        utter_resp = self.client.post(
            f"/meetings/{meeting_id}/utterance?sync=true",
            json={
                "speaker": "Alex",
                "text": "I'll email Acme today to get clarity on the new tiers and ask if we qualify for a bulk discount.",
                "ts": "02:15",
            },
        )
        self.assertEqual(utter_resp.status_code, 200)

        # 3. Retrieve audit spans via GET /meetings/{id}/audit
        audit_resp = self.client.get(f"/meetings/{meeting_id}/audit")
        self.assertEqual(audit_resp.status_code, 200)
        resp_data = audit_resp.json()
        self.assertEqual(resp_data["status"], "ok")
        spans = resp_data.get("audit", [])
        self.assertTrue(len(spans) > 0, "No audit spans returned by GET /meetings/{id}/audit")

        # 4. Verify OpenTelemetry fields on all spans
        span_names = set()
        trace_ids = set()
        span_by_name = {}

        for sp in spans:
            self.assertIn("traceId", sp)
            self.assertIn("spanId", sp)
            self.assertIn("name", sp)
            self.assertIn("startTs", sp)
            self.assertIn("endTs", sp)
            self.assertIn("status", sp)
            self.assertIn("attributes", sp)
            span_names.add(sp["name"])
            trace_ids.add(sp["traceId"])
            span_by_name[sp["name"]] = sp

        print(f"\n[Observability] Discovered spans for meeting '{meeting_id}': {span_names}")

        # 5. Assert expected reasoning chain steps are present
        self.assertIn("pipeline.reasoning_chain", span_names, "Missing root reasoning chain span")
        self.assertIn("watcher.extraction", span_names, "Missing watcher extraction span")
        self.assertIn("tool.email", span_names, "Missing tool execution span")
        self.assertIn("guardrail.evaluate", span_names, "Missing guardrail evaluation span")
        self.assertIn("slack.post_notification", span_names, "Missing Slack post span")

        # 6. Verify parent-child linkage in the reasoning chain
        root_span = span_by_name["pipeline.reasoning_chain"]
        self.assertIsNone(root_span["parentId"])
        root_trace_id = root_span["traceId"]
        root_span_id = root_span["spanId"]

        watcher_span = span_by_name["watcher.extraction"]
        self.assertEqual(watcher_span["traceId"], root_trace_id)
        self.assertEqual(watcher_span["parentId"], root_span_id)
        self.assertIn("model", watcher_span["attributes"])
        self.assertTrue(watcher_span["attributes"]["extractedCount"] >= 1)

        tool_span = span_by_name["tool.email"]
        self.assertEqual(tool_span["traceId"], root_trace_id)
        self.assertEqual(tool_span["parentId"], root_span_id)
        self.assertEqual(tool_span["attributes"]["category"], "email")
        self.assertEqual(tool_span["attributes"]["status"], "needs_approval")

        guard_span = span_by_name["guardrail.evaluate"]
        self.assertEqual(guard_span["traceId"], root_trace_id)
        self.assertEqual(guard_span["parentId"], root_span_id)
        self.assertTrue(guard_span["attributes"]["safe"])

        slack_span = span_by_name["slack.post_notification"]
        self.assertEqual(slack_span["traceId"], root_trace_id)
        self.assertEqual(slack_span["parentId"], root_span_id)

    def test_ambiguous_clarification_and_resume_tracing(self):
        """Tests that ambiguous items produce clarification spans and resumed execution links traces."""
        meeting_id = "trace-clar-meeting"

        # 1. Start meeting & post ambiguous utterance
        self.client.post(f"/meetings/{meeting_id}/start", json={"reset": True})
        self.client.post(
            f"/meetings/{meeting_id}/utterance?sync=true",
            json={"speaker": "Alex", "text": "someone should follow up with the vendor"},
        )

        # Verify clarification creation spans
        audit_resp = self.client.get(f"/meetings/{meeting_id}/audit")
        spans = audit_resp.json().get("audit", [])
        span_names = {s["name"] for s in spans}
        self.assertIn("clarification.create", span_names)
        self.assertIn("slack.post_clarification", span_names)

        # 2. Answer clarification
        answer_resp = self.client.post(
            f"/meetings/{meeting_id}/clarifications/clar-ai-vendor-ambig/answer",
            json={"answer": "Sam"},
        )
        self.assertEqual(answer_resp.status_code, 200)

        # Verify resumed execution spans
        audit_resp2 = self.client.get(f"/meetings/{meeting_id}/audit")
        spans2 = audit_resp2.json().get("audit", [])
        span_names2 = {s["name"] for s in spans2}
        self.assertIn("clarification.resume", span_names2)

        resume_span = next(s for s in spans2 if s["name"] == "clarification.resume")
        self.assertEqual(resume_span["attributes"]["answer"], "Sam")

    def test_scanner_nudge_tracing(self):
        """Tests that scanner execution emits scanner.scan_and_nudge and child nudge spans."""
        # Seed an overdue commitment
        overdue_comm = Commitment(
            id="com-overdue-1",
            title="Update pricing spreadsheet",
            category="task",
            assignee="Alex",
            sourceMeeting="Monday Product Sync",
            sourceDate="Aug 24",
            due="yesterday",
            status="open",
        )
        ledger.upsert_commitment(overdue_comm)

        # Trigger scan
        resp = self.client.post("/scan")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")


def run_tests():
    print("=" * 70)
    print("🔬 Running OpenTelemetry Agent Observability & Tracing Test Suite")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAgentObservabilityAndTracing)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        print("❌ Tracing tests failed!")
        sys.exit(1)
    print("\n" + "=" * 70)
    print("🎉 ALL OPENTELEMETRY TRACING TESTS PASSED PERFECTLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
