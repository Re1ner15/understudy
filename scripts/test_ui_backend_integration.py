import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

os.environ['MOCK_AGENT'] = '1'
os.environ['GOOGLE_CLOUD_PROJECT'] = 'demo-understudy'

from understudy_agent.schemas import LiveAction, Commitment
from understudy_agent import ledger
from understudy_agent import server
from fastapi.testclient import TestClient

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
            doc_id = f'auto-{uuid.uuid4().hex[:8]}'
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

class InMemoryFirestore:
    def __init__(self):
        self.store = {}

    def collection(self, col_name):
        return MockCollectionRef(self.store, [col_name])

class TestUIBackendIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_db = InMemoryFirestore()
        self.patcher = patch('understudy_agent.ledger.get_db', return_value=self.mock_db)
        self.patcher.start()
        self.client = TestClient(server.app)

    def tearDown(self):
        self.patcher.stop()

    def test_cors_middleware_headers(self):
        resp = self.client.options(
            '/health',
            headers={
                'Origin': 'http://localhost:5173',
                'Access-Control-Request-Method': 'GET',
            },
        )
        self.assertIn(resp.status_code, [200, 204])
        self.assertEqual(resp.headers.get('access-control-allow-origin'), 'http://localhost:5173')

    def test_skip_action_endpoint(self):
        meeting_id = 'test-skip-meeting'
        action_id = 'act-test-skip'
        action = LiveAction(
            id=action_id,
            itemId='ai-skip-1',
            category='email',
            title='Email Acme about pricing',
            status='needs_approval',
            reasoning='Waiting for user review.',
            requiresApproval=True,
        )
        ledger.upsert_action(meeting_id, action)
        comm = ledger.action_to_commitment(action, 'Test Meeting', 'Aug 28')
        ledger.upsert_commitment(comm)

        resp = self.client.post(f'/meetings/{meeting_id}/actions/{action_id}/skip')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'ok')

        updated_act = ledger.get_action(meeting_id, action_id)
        self.assertIsNotNone(updated_act)
        self.assertEqual(updated_act.get('status'), 'error')
        self.assertIn('Skipped', updated_act.get('reasoning', ''))

        updated_comm = ledger.get_commitment(comm.id)
        self.assertIsNotNone(updated_comm)
        self.assertEqual(updated_comm.get('status'), 'blocked')

    def test_approve_action_endpoint(self):
        meeting_id = 'test-approve-meeting'
        action_id = 'act-test-approve'
        action = LiveAction(
            id=action_id,
            itemId='ai-app-1',
            category='email',
            title='Email Acme about pricing',
            status='needs_approval',
            reasoning='Waiting for approval.',
            requiresApproval=True,
        )
        ledger.upsert_action(meeting_id, action)
        comm = ledger.action_to_commitment(action, 'Test Meeting', 'Aug 28')
        ledger.upsert_commitment(comm)

        resp = self.client.post(f'/meetings/{meeting_id}/actions/{action_id}/approve')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'ok')

        updated_act = ledger.get_action(meeting_id, action_id)
        self.assertEqual(updated_act.get('status'), 'done')
        updated_comm = ledger.get_commitment(comm.id)
        self.assertEqual(updated_comm.get('status'), 'done')

    def test_gemma_prefilter_in_live_mode_span(self):
        meeting_id = 'test-live-gemma-meeting'
        self.client.post(f'/meetings/{meeting_id}/start', json={'reset': True})

        with patch('understudy_agent.server.is_mock_agent', return_value=False),              patch('understudy_agent.server.is_actionable') as mock_filter,              patch('understudy_agent.server.extract_action_items', return_value=[]):
            mock_filter.side_effect = lambda txt: {'actionable': True, 'confidence': 0.95} if 'email' in txt.lower() else {'actionable': False, 'confidence': 0.05}

            self.client.post(
                f'/meetings/{meeting_id}/utterance?sync=true',
                json={'speaker': 'Alex', 'text': 'How was your weekend everyone?'},
            )
            audit_logs = ledger.get_audit_logs(meeting_id)
            span_names = [s['name'] for s in audit_logs]
            self.assertIn('gemma.prefilter', span_names)

            gemma_span = next(s for s in audit_logs if s['name'] == 'gemma.prefilter')
            self.assertEqual(gemma_span['attributes']['countIn'], 1)
            self.assertEqual(gemma_span['attributes']['countOut'], 0)

    def test_gemma_prefilter_bypassed_in_mock_mode(self):
        meeting_id = 'test-mock-bypass-meeting'
        self.client.post(f'/meetings/{meeting_id}/start', json={'reset': True})

        with patch('understudy_agent.server.is_mock_agent', return_value=True):
            self.client.post(
                f'/meetings/{meeting_id}/utterance?sync=true',
                json={'speaker': 'Alex', 'text': 'How was your weekend everyone?'},
            )
            audit_logs = ledger.get_audit_logs(meeting_id)
            span_names = [s['name'] for s in audit_logs]
            self.assertNotIn('gemma.prefilter', span_names)

if __name__ == '__main__':
    unittest.main()
