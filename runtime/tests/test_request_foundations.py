"""Durable context fallback and bounded pre-job planning without provider calls."""
import contextlib
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from kel.commander import Commander
from kel.context import Context
from kel.core import PolicyError
from kel.service import Service


class FakePlanner:
    provider = 'fixture'
    model = 'fixture-plan'

    def execute(self, prompt, cancel=None):
        return {'outcome': 'SUCCESS', 'text': json.dumps({'milestones': [{
            'id': 'doc', 'objective': 'write guide', 'filename': 'guide.md', 'depends_on': [],
            'checks': [{'kind': 'manual_review', 'rubric': 'meets request'}]}]})}


class RequestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.service = Service(self.tmp.name)
        self.service.engine.adapters = {}
        self.addCleanup(self.service.shutdown)

    def intake(self):
        with patch.object(self.service.requests, 'submit'):
            sid = self.service.submit({'conversation': 'main', 'text': 'Write a guide.', 'kind': 'document'})
        with contextlib.closing(self.service.store.connect()) as db:
            packet = json.loads(db.execute('SELECT packet FROM submission_packets WHERE id=?', (sid,)).fetchone()['packet'])
        return sid, packet

    def test_context_failure_persists_without_error_payload(self):
        with patch('kel.composer.Composer.build', side_effect=RuntimeError('SECRET error payload')):
            sid, packet = self.intake()
        status = Context(self.service.store).context_status(sid)
        self.assertEqual(status['state'], 'degraded')
        self.assertEqual(status['error_code'], 'RuntimeError')
        self.assertNotIn('SECRET', json.dumps(status))
        self.assertEqual(packet['context_status'], status)
        public = next(s for s in self.service.state('main')['submissions'] if s['id'] == sid)
        self.assertEqual(public['context_status'], status)

    def test_admission_precedes_calls_and_unknown_cost_is_not_zero(self):
        sid, _packet = self.intake()
        model = FakePlanner()
        first = self.service._admit_planning_call(sid, model, True)
        reserved = self.service.context.request_calls(sid)[0]
        self.assertEqual(reserved['state'], 'reserved')
        self.assertGreater(reserved['estimate']['cost'], 0)
        self.service._settle_planning_call(first, model, {'outcome': 'SUCCESS'}, 10)
        settled = self.service.context.request_calls(sid)[0]
        self.assertIsNone(settled['usage']['cost_usd'])
        self.service._admit_planning_call(sid, model, False)
        self.service._admit_planning_call(sid, model, True)
        with self.assertRaisesRegex(PolicyError, 'three planning attempts'):
            self.service._admit_planning_call(sid, model, True)
        self.assertEqual(len(self.service.context.request_calls(sid)), 3)

    def test_cancelled_planner_late_result_creates_no_job_or_failure(self):
        sid, packet = self.intake()
        entered, release = threading.Event(), threading.Event()
        service = self.service
        class Blocking(FakePlanner):
            def execute(self, prompt, cancel=None):
                entered.set()
                release.wait(5)
                self.cancelled = cancel.is_set()
                return super().execute(prompt, cancel)
        planner = Blocking()
        service.commander = Commander(planner)
        worker = threading.Thread(target=service._start_work, args=(sid, 'main', 'Write a guide.', packet, 'document'))
        worker.start()
        try:
            self.assertTrue(entered.wait(5))
            self.assertTrue(service.cancel_submission('main', sid)['cancelled'])
        finally:
            release.set()
            worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertTrue(planner.cancelled)
        with contextlib.closing(service.store.connect()) as db:
            self.assertEqual(db.execute('SELECT state FROM submissions WHERE id=?', (sid,)).fetchone()['state'], 'CANCELLED')
        self.assertEqual(service.store.list_jobs(), [])
        self.assertEqual(service.context.request_calls(sid)[0]['state'], 'settled')
        with contextlib.closing(service.store.connect()) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM provider_usage WHERE json_extract(data,'$.submission_id')=?", (sid,)).fetchone()[0], 1)

    def test_cancellation_during_admission_settles_without_adapter_call(self):
        sid, _packet = self.intake()
        cancel = threading.Event()
        executed = []
        class Unsupported(FakePlanner):
            def execute(self, prompt):
                executed.append(prompt)
                return super().execute(prompt)
        model = Unsupported()
        commander = Commander(model)
        def admit(candidate, supported):
            call_id = self.service._admit_planning_call(sid, candidate, supported)
            cancel.set()
            return call_id
        with commander.planning_scope(cancel, admit, self.service._settle_planning_call):
            with self.assertRaisesRegex(PolicyError, 'stopped'):
                commander.plan('Write a guide')
        self.assertEqual(executed, [])
        call = self.service.context.request_calls(sid)[0]
        self.assertEqual(call['state'], 'settled')
        self.assertEqual(call['usage']['execution_state'], 'not_started')
        self.assertEqual(call['usage']['processed'], 0)
        self.assertEqual(call['usage']['cost_usd'], 0)
        with contextlib.closing(self.service.store.connect()) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM provider_usage WHERE json_extract(data,'$.submission_id')=?", (sid,)).fetchone()[0], 0)

    def test_usage_settlement_is_idempotent(self):
        sid, _packet = self.intake()
        model = FakePlanner()
        call_id = self.service._admit_planning_call(sid, model, True)
        result = {'outcome': 'SUCCESS', 'usage': {'input_tokens': 20, 'output_tokens': 4}}
        self.service._settle_planning_call(call_id, model, result, 12)
        self.service._kel_usage('plan', sid, 'main', model, result, 12)
        self.service._kel_usage('plan', sid, 'main', model, result, 12)
        with contextlib.closing(self.service.store.connect()) as db:
            count = db.execute("SELECT COUNT(*) FROM provider_usage WHERE json_extract(data,'$.call_id')=?", (call_id,)).fetchone()[0]
        self.assertEqual(count, 1)

    def test_attention_context_blocks_work(self):
        sid, packet = self.intake()
        packet['context_status']['requires_attention'] = True
        with self.assertRaisesRegex(PolicyError, 'context needs attention'):
            self.service._compile_work(sid, 'main', 'Write a guide.', packet, 'document', False)

    def test_saved_transcript_origin_uses_stored_identity(self):
        from kel.transcription import Transcription
        Transcription(self.service.store)
        with self.service.store.transaction() as db:
            db.execute('INSERT INTO transcripts(id,name,text,created,updated) VALUES(?,?,?,?,?)',
                       ('saved-input', 'Recorded notes', 'Original words', time.time(), time.time()))
        with patch.object(self.service.requests, 'submit'):
            sid = self.service.submit({'text': 'Edited words', 'conversation': 'main',
                                       'transcriptOrigin': {'id': 'saved-input', 'name': 'Forged label'}})
        with contextlib.closing(self.service.store.connect()) as db:
            packet = json.loads(db.execute('SELECT packet FROM submission_packets WHERE id=?', (sid,)).fetchone()['packet'])
            message = db.execute("SELECT meta FROM messages WHERE conversation_id='main' AND role='user' ORDER BY seq DESC LIMIT 1").fetchone()
        self.assertEqual(packet['transcript_origin']['name'], 'Recorded notes')
        self.assertTrue(packet['transcript_origin']['edited'])
        self.assertEqual(json.loads(message['meta'])['transcript_origin'], packet['transcript_origin'])
        with self.assertRaisesRegex(PolicyError, 'no longer exists'):
            self.service.submit({'text': 'Words', 'transcriptOrigin': {'id': 'missing'}})

    def test_restart_marks_unsettled_planning_call_interrupted(self):
        sid, _packet = self.intake()
        self.service._admit_planning_call(sid, FakePlanner(), False)
        self.service.shutdown()
        restarted = Service(self.tmp.name)
        self.addCleanup(restarted.shutdown)
        self.assertEqual(restarted.context.request_calls(sid)[0]['state'], 'interrupted')

    def test_donor_send_claims_matching_origin_once(self):
        import uuid
        from kel.transcription import Transcription
        from kel.input_origins import InputOrigins
        Transcription(self.service.store)
        with self.service.store.transaction() as db:
            db.execute('INSERT INTO transcripts(id,name,text,created,updated) VALUES(?,?,?,?,?)',
                       ('ramble-input', 'Ramble source', 'Recorded words', time.time(), time.time()))
        donor = str(uuid.uuid4())
        origins = InputOrigins(self.service.store)
        origins.queue(donor, 'default', 'ramble-input', 'Edited request')
        self.assertIsNone(origins.claim(donor, 'other-project', 'Edited request'))
        with patch.object(self.service.requests, 'submit'):
            sid = self.service.submit({'text': 'Edited request', 'conversation': 'main', 'donor_id': donor})
        with contextlib.closing(self.service.store.connect()) as db:
            packet = json.loads(db.execute('SELECT packet FROM submission_packets WHERE id=?', (sid,)).fetchone()['packet'])
        self.assertEqual(packet['transcript_origin']['id'], 'ramble-input')
        self.assertEqual(packet['transcript_origin']['name'], 'Ramble source')
        self.assertIsNone(origins.claim(donor, 'default', 'Edited request'))

    def test_estimated_admission_blocks_before_adapter_call(self):
        sid, _packet = self.intake()
        with patch('kel.budget.estimate', return_value={'tokens': 4_000_000, 'ms': 10, 'cost': 0.1, 'measured': False}):
            with self.assertRaisesRegex(PolicyError, 'planning budget'):
                self.service._admit_planning_call(sid, FakePlanner(), True)
        self.assertEqual(self.service.context.request_calls(sid), [])


class PlannerScopeTests(unittest.TestCase):
    def test_uninterruptible_adapter_reports_limit_and_fences_result(self):
        cancel = threading.Event()
        calls = []
        class Unsupported:
            def execute(self, prompt):
                cancel.set()
                return {'outcome': 'SUCCESS', 'text': '{}'}
        model = Unsupported()
        commander = Commander(model)
        with commander.planning_scope(cancel, lambda model, supported: calls.append(supported) or 'call',
                                      lambda *args: calls.append('settled')):
            with self.assertRaisesRegex(PolicyError, 'stopped'):
                commander.plan('Write a guide')
        self.assertEqual(calls, [False, 'settled'])
