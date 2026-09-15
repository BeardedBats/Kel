"""B3: provenance recording for planner, executor, and reviewer.

Each job/run records who planned it (compiler and/or provider+model), who
executed it (provider+model), and who reviewed it (provider+model). None of
this changes routing, executor!=reviewer separation, or final job state.
"""
import contextlib
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from kel.commander import Commander
from kel.core import Store, PolicyError
from kel.engine import compile_document
from kel.service import Service


def _poll(service, sid):
    deadline = time.time() + 15
    row = None
    while time.time() < deadline:
        with contextlib.closing(service.store.connect()) as db:
            row = db.execute('SELECT state FROM submissions WHERE id=?', (sid,)).fetchone()
        if row and row['state'] in ('DISPATCHED', 'FAILED', 'INTERRUPTED'):
            return row['state']
        time.sleep(0.05)
    return row['state'] if row else 'TIMEOUT'


class PlannerModel:
    """A commander model that proposes a valid single-milestone plan."""
    provider = 'planner-provider'
    model = 'planner-model'

    def execute(self, prompt, **kwargs):
        return {'outcome': 'SUCCESS', 'text': json.dumps({'milestones': [{
            'id': 'doc', 'objective': 'x', 'filename': 'doc.md', 'depends_on': [],
            'checks': [{'kind': 'manual_review', 'rubric': 'meets request'}]}]})}


class PlannerProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        saved = dict(os.environ)
        os.environ.pop('ANTHROPIC_API_KEY', None)
        os.environ.pop('KEL_INTERNAL_MODEL', None)
        os.environ['KEL_REVIEWER'] = 'none'
        os.environ['KEL_SKIP_TELEMETRY'] = '1'
        self.addCleanup(lambda: os.environ.update(saved))
        base = Path(self.temp.name)
        self.service = Service(self.temp.name)
        self.service.engine.adapters = {}
        self.addCleanup(self.service.shutdown)
        self.base = base

    def _conversation(self):
        return self.service.context.conversation('default')

    def _job(self, cid):
        jobs = [j for j in self.service.store.list_jobs() if j['conversation'] == cid]
        return jobs[0]

    def test_document_without_commander_records_template_compiler(self):
        cid = self._conversation()
        with patch('pathlib.Path.home', return_value=self.base):
            sid = self.service.submit({'text': 'Write a plain guide.', 'conversation': cid, 'kind': 'document'})
        self.assertEqual(_poll(self.service, sid), 'DISPATCHED')
        contract = self._job(cid)['contract']
        self.assertEqual(contract['planner'],
                         {'provider': None, 'model': None, 'compiler': 'document-template-v1'})

    def test_document_with_commander_records_provider_model(self):
        self.service.commander = Commander(PlannerModel())
        cid = self._conversation()
        with patch('pathlib.Path.home', return_value=self.base):
            sid = self.service.submit({'text': 'Write a plain guide.', 'conversation': cid, 'kind': 'document'})
        self.assertEqual(_poll(self.service, sid), 'DISPATCHED')
        contract = self._job(cid)['contract']
        self.assertEqual(contract['planner'], {
            'provider': 'planner-provider', 'model': 'planner-model',
            'compiler': 'commander-proposal-v1'})

    def test_coding_planner_records_coding_compiler(self):
        cid = self._conversation()
        with patch('pathlib.Path.home', return_value=self.base):
            sid = self.service.submit({
                'text': 'I want to create a little app that toggles my microphone mute button',
                'conversation': cid, 'kind': 'coding'})
        self.assertEqual(_poll(self.service, sid), 'DISPATCHED')
        contract = self._job(cid)['contract']
        self.assertEqual(contract['kind'], 'coding')
        self.assertEqual(contract['planner']['compiler'], 'coding-contract-v2')


class ExecutionProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.job = self.store.create(compile_document('Write a plain guide.'))

    def test_executor_and_reviewer_provenance_and_separation(self):
        run = self.store.claim(self.job, 'document', provider='codex', model='codex-v2')
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT provider, model FROM runs WHERE id=?', (run['id'],)).fetchone()
        self.assertEqual((row['provider'], row['model']), ('codex', 'codex-v2'))
        self.store.enqueue_result('receipt', run['id'], run['epoch'],
                                  {'outcome': 'SUCCESS', 'text': 'A completed artifact ready for independent review.'})
        self.store.consume()
        self.store.verify(self.job, 'document')
        subject = self.store.get(self.job)['milestones']['document']['artifact']['sha256']
        version = self.store.get(self.job)['contract_version']
        # Executor cannot review its own run.
        with self.assertRaises(PolicyError):
            self.store.record_review(self.job, 'document', subject, run['id'], 'VERIFIED', ['ok'], version)
        # Independent reviewer provenance is recorded.
        self.store.record_review(self.job, 'document', subject, 'reviewer-1', 'VERIFIED', ['Meets request.'],
                                 version, reviewer_provider='claude', reviewer_model='claude-v1')
        check = next(c for c in self.store.get(self.job)['milestones']['document']['checks']
                     if c['kind'] == 'manual_review')
        self.assertEqual(check['reviewer_provider'], 'claude')
        self.assertEqual(check['reviewer_model'], 'claude-v1')

    def test_provenance_survives_reload(self):
        contract = compile_document('Write a plain guide.')
        contract['planner'] = {'provider': 'pp', 'model': 'pm', 'compiler': 'document-template-v1'}
        jid = self.store.create(contract)
        run = self.store.claim(jid, 'document', provider='codex', model='codex-v2')
        self.store.enqueue_result('receipt', run['id'], run['epoch'],
                                  {'outcome': 'SUCCESS', 'text': 'A completed artifact ready for independent review.'})
        self.store.consume()
        self.store.verify(jid, 'document')
        subject = self.store.get(jid)['milestones']['document']['artifact']['sha256']
        self.store.record_review(jid, 'document', subject, 'reviewer-1', 'VERIFIED', ['Meets request.'],
                                 self.store.get(jid)['contract_version'],
                                 reviewer_provider='claude', reviewer_model='claude-v1')
        # Reopen the store on the same data dir and confirm everything persists.
        reopened = Store(self.temp.name)
        job = reopened.get(jid)
        self.assertEqual(job['contract']['planner'],
                         {'provider': 'pp', 'model': 'pm', 'compiler': 'document-template-v1'})
        self.assertEqual(job['milestones']['document']['provider'], 'codex')
        self.assertEqual(job['milestones']['document']['model'], 'codex-v2')
        check = next(c for c in job['milestones']['document']['checks'] if c['kind'] == 'manual_review')
        self.assertEqual((check['reviewer_provider'], check['reviewer_model']), ('claude', 'claude-v1'))


if __name__ == '__main__':
    unittest.main()
