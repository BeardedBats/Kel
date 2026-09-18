"""V1.4.1 hardening tests: the real runtime boundaries added after the post-release audit.

Covers: guardrail tamper refusal (engine refuses new work), protected-path denial on the
engine's apply path, emergency-stop scope (leases + active/queued work), actor-identity
spoofing at the service and engine boundaries, and credential custody assertions.
"""
import contextlib
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import patch

from kel.core import PolicyError, Store, encode, digest
from kel.autonomy import Autonomy
from kel import guardrails
from kel.engine import Engine, compile_document
from kel.native import FixtureAdapter
from kel.service import Service
from kel.providers import Providers
from kel.diagnostics import Diagnostics


class GuardrailTamperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / 'data')

    def tearDown(self):
        self.tmp.cleanup()

    def test_guardrails_detect_runtime_modification(self):
        weakened = (('weakened', 'Rule removed.', 'AUTO-X'),)
        self.assertTrue(guardrails.assert_intact())
        with mock.patch('kel.guardrails.RULES', weakened):
            with self.assertRaises(PolicyError):
                guardrails.assert_intact()
        with mock.patch('kel.autonomy.RULES', weakened):
            with self.assertRaises(PolicyError):
                Autonomy(self.store).assert_intact()
        self.assertTrue(guardrails.assert_intact())
        self.assertTrue(Autonomy(self.store).assert_intact())

    def test_engine_refuses_new_work_while_rules_are_modified(self):
        engine = Engine(self.store, {'fixture': FixtureAdapter()}, concurrency=2)
        try:
            job = self.store.create(compile_document('Write a short plan for the weekend.'))
            weakened = (('weakened', 'Rule removed.', 'AUTO-X'),)
            with mock.patch('kel.guardrails.RULES', weakened):
                engine.tick()
                self.assertIsNotNone(engine.tampered)
                with contextlib.closing(self.store.connect()) as db:
                    runs = db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]
                self.assertEqual(runs, 0, 'no worker run may be claimed while tampered')
                self.assertEqual(self.store.get(job)['state'], 'READY')
            engine.tick()
            self.assertIsNone(engine.tampered)
            deadline = time.time() + 5
            claimed = False
            while time.time() < deadline and not claimed:
                engine.tick()
                with contextlib.closing(self.store.connect()) as db:
                    claimed = db.execute('SELECT COUNT(*) FROM runs').fetchone()[0] > 0
                time.sleep(.05)
            self.assertTrue(claimed, 'work must resume after the rule set verifies again')
        finally:
            engine.close()


class ProtectedPathTests(unittest.TestCase):
    @staticmethod
    def _verified_coding_job(store, base, root):
        from kel.coding import CodingAdapter, compile_coding, snapshot, file_manifest, git
        CodingAdapter(store)
        repo = base / root
        repo.mkdir(parents=True)
        git(repo, 'init')
        (repo / 'app.txt').write_text('old')
        git(repo, 'add', '-A')
        git(repo, '-c', 'user.name=Kel', '-c', 'user.email=kel@localhost', 'commit', '-m', 'base')
        job = store.create(compile_coding('Change app.txt.', repo, ['python', '-m', 'unittest']))
        workspace = base / 'copy'
        revision = snapshot(repo, workspace)
        baseline = file_manifest(workspace)
        (workspace / 'app.txt').write_text('new')
        git(workspace, 'add', '-A')
        diff = git(workspace, 'diff', '--cached', '--binary', revision).decode()
        run = store.claim(job, 'code', provider='codex-code')
        tests = {'exit_code': 0, 'existing_tests_preserved': True, 'source_stable_during_tests': True}
        with store.transaction() as db:
            db.execute('INSERT INTO code_workspaces VALUES(?,?,?,?)',
                       (job, str(workspace), revision, encode(baseline)))
            db.execute('INSERT INTO code_evidence VALUES(?,?,?,?,?,?,?,?)',
                       (run['id'], str(workspace), encode(file_manifest(workspace)), diff,
                        digest(diff.encode()), encode(tests), '{}', time.time()))
        store.enqueue_result('result', run['id'], run['epoch'],
                             {'outcome': 'SUCCESS',
                              'text': 'Fixture change with trusted evidence, ready for review.'})
        store.consume()
        store.verify(job, 'code')
        artifact = store.get(job)['milestones']['code']['artifact']
        store.record_review(job, 'code', artifact['sha256'], 'reviewer', 'VERIFIED',
                            ['Fixture output meets the requested diff.'])
        assert store.assess(job) == 'VERIFIED'
        return job, repo

    def test_predicates_and_apply_refusal(self):
        self.assertIsNotNone(guardrails.protected_reason('C:\\Kel Releases\\Kel-V1.4-Frozen\\x'))
        self.assertIsNotNone(guardrails.protected_reason('C:\\Windows\\System32\\x'))
        self.assertIsNone(guardrails.protected_reason('C:\\Users\\someone\\Documents\\proj'))
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            store = Store(base / 'data')
            job, repo = self._verified_coding_job(
                store, base, Path('Kel Releases') / 'Kel-V1.6-Frozen' / 'proj')
            from kel.apply_changes import apply_checked
            with self.assertRaises(PolicyError) as caught:
                apply_checked(store, job)
            self.assertIn('protected location', str(caught.exception))
            self.assertEqual((repo / 'app.txt').read_text(), 'old',
                             'the protected project must be left untouched')


class EmergencyStopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / 'data')
        self.autonomy = Autonomy(self.store)
        self.workspace = self.root / 'proj'
        self.workspace.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_scope_covers_leases_and_active_and_queued_work(self):
        lease = self.autonomy.issue('job-active', review_ref='brief:approved',
                                    roots=[str(self.workspace)])
        running = self.store.create(compile_document('Write a short plan for the weekend.'))
        run = self.store.claim(running, 'document', provider='fixture')
        queued = self.store.create(compile_document('Write another short plan.'))
        cancelled = self.store.create(compile_document('Write a third short plan.'))
        self.store.control(cancelled, 'cancel')
        result = self.autonomy.emergency_stop()
        self.assertIn(lease['lease_id'], result['stopped'])
        self.assertIn(running, result['paused_jobs'])
        self.assertIn(queued, result['paused_jobs'])
        self.assertNotIn(cancelled, result['paused_jobs'])
        denied = self.autonomy.check(lease['lease_id'], 'write',
                                     target=str(self.workspace / 'x.txt'))
        self.assertFalse(denied['allowed'])
        self.assertEqual(self.store.get(running)['state'], 'PAUSING')
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT state FROM runs WHERE id=?', (run['id'],)).fetchone()
        self.assertEqual(row['state'], 'CANCEL_REQUESTED')
        self.assertEqual(self.store.get(queued)['state'], 'PAUSED')
        self.assertEqual(self.store.get(cancelled)['state'], 'CANCELLED')
        self.store.control(queued, 'resume')
        self.assertEqual(self.store.get(queued)['state'], 'READY')

    def test_only_the_user_can_trigger_it(self):
        for actor in ('worker', 'system', 'reviewer', 'kel', 'admin'):
            with self.assertRaises(PolicyError):
                self.autonomy.emergency_stop(actor=actor)


class ActorBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('ANTHROPIC_API_KEY', None)
            os.environ.pop('KEL_INTERNAL_MODEL', None)
            os.environ['KEL_SKIP_TELEMETRY'] = '1'
            os.environ['KEL_REVIEWER'] = 'none'
            self.service = Service(self.root / 'data')
        self.service.stop.set()  # freeze the supervisor tick for deterministic seeding

    def tearDown(self):
        self.service.shutdown()
        self.tmp.cleanup()

    def test_service_rejects_caller_supplied_actor_identity(self):
        for payload in (
            {'action': 'emergency_stop', 'actor': 'worker'},
            {'action': 'emergency_stop', 'actor': 'system'},
            {'action': 'resolve', 'request_id': 'x', 'allow': True, 'actor': 'reviewer'},
            {'action': 'resolve', 'request_id': 'x', 'allow': True, 'actor': 'user'},
        ):
            with self.assertRaises(PolicyError):
                self.service.action('/api/autonomy', payload)
        with self.assertRaises(PolicyError):
            self.service.action('/api/approval', {'id': 'x', 'allow': True, 'actor': 'user'})

    def test_emergency_stop_through_the_service_pauses_work(self):
        autonomy = Autonomy(self.service.store)
        (self.root / 'proj').mkdir(exist_ok=True)
        lease = autonomy.issue('job-1', review_ref='brief:approved', roots=[str(self.root / 'proj')])
        job = self.service.store.create(compile_document('Write a short status plan.'))
        self.service.store.claim(job, 'document', provider='fixture')
        result = self.service.action('/api/autonomy', {'action': 'emergency_stop'})
        self.assertIn(lease['lease_id'], result['stopped'])
        self.assertIn(job, result['paused_jobs'])
        self.assertEqual(self.service.store.get(job)['state'], 'PAUSING')

    def test_state_reports_engine_version_and_guardrails(self):
        state = self.service.state('main')
        # The engine's identity comes from its single source (`kel.__version__`); R8.B made the
        # desktop's reuse guard compare exactly this value against `app.getVersion()`.
        from kel.service import ENGINE_VERSION
        self.assertEqual(state['engine_version'], ENGINE_VERSION)
        self.assertTrue(state['guardrails_ok'])


class CredentialCustodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / 'data')
        self.providers = Providers(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def test_engine_stores_a_reference_not_a_value(self):
        with self.assertRaises(PolicyError):
            self.providers.set_credential_metadata('deepseek', ['api_key'], '')
        self.providers.set_credential_metadata('deepseek', ['api_key'],
                                               'kel:provider:deepseek:api_key')
        rows = self.providers.credential_metadata('deepseek')
        self.assertEqual(rows[0]['credential_ref'], 'kel:provider:deepseek:api_key')
        raw = (self.root / 'data' / 'kel.sqlite3').read_bytes()
        self.assertIn(b'kel:provider:deepseek:api_key', raw)
        self.assertNotIn(b'sk-live-secret-value', raw)

    def test_export_refuses_secret_shaped_provider_values(self):
        with self.store.transaction() as db:
            db.execute('INSERT INTO providers VALUES(?,?)',
                       ('deepseek', encode({'failures': 0, 'quota_source': 'sk-live-abc123'})))
        with self.assertRaises(PolicyError):
            Diagnostics(self.store, '1.5.0').export()
