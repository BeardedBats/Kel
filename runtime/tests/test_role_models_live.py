"""D-67 on the everyday path: the engine asks for each role's model, the runtimes get the real flags,
the reviewer runs on the Verifier's model, and only what a runtime reported is recorded as run.

Every runtime here is a fake; no provider is called.
"""
import contextlib
import json
import os
import queue
import tempfile
import time
import unittest
from pathlib import Path

from kel import role_models, staff
from kel.coding import CodingAdapter, compile_coding, file_manifest, git, snapshot
from kel.core import Store, digest, encode
from kel.engine import FIXED_WAIT, Engine
from kel.native import NativeAdapter


def make_project(base):
    root = Path(base) / 'proj'
    root.mkdir()
    git(root, 'init')
    (root / 'app.txt').write_text('old')
    git(root, 'add', '-A')
    git(root, '-c', 'user.name=Kel', '-c', 'user.email=kel@localhost', 'commit', '-m', 'base')
    return root


class FakeCoder:
    """A coding runtime that really changes an isolated copy and records test evidence the way the
    coding bridge does, and reports the model it ran as `model_used` (or refuses a model)."""
    capabilities = {'text', 'repository_edit'}

    def __init__(self, store, reports=None, refuse=False, files=1):
        self.store, self.reports, self.refuse, self.files = store, reports, refuse, files
        self.calls = []

    def execute(self, prompt, run_id=None, session_id=None, cancel=None):
        from kel.staff import binding_for_run
        self.calls.append(binding_for_run(self.store, run_id))
        if self.refuse:
            return {'outcome': 'FAILED', 'error': 'model claude-opus-5-5 not found'}
        with contextlib.closing(self.store.connect()) as db:
            run = db.execute('SELECT job_id FROM runs WHERE id=?', (run_id,)).fetchone()
            existing = db.execute('SELECT * FROM code_workspaces WHERE job_id=?', (run['job_id'],)).fetchone()
        job = self.store.get(run['job_id'])
        if existing:
            workspace, revision = Path(existing['path']), existing['base']
        else:
            workspace = self.store.root / 'repositories' / run['job_id']
            workspace.parent.mkdir(exist_ok=True)
            revision = snapshot(job['contract']['root'], workspace)
            baseline = file_manifest(workspace)
            with self.store.transaction() as db:
                db.execute('INSERT INTO code_workspaces VALUES(?,?,?,?)',
                           (run['job_id'], str(workspace), revision, encode(baseline)))
        (workspace / 'app.txt').write_text('new')
        for index in range(1, self.files):
            (workspace / ('extra%d.txt' % index)).write_text('extra')
        git(workspace, 'add', '-A')
        diff = git(workspace, 'diff', '--cached', '--binary', revision).decode()
        tests = {'exit_code': 0, 'existing_tests_preserved': True, 'source_stable_during_tests': True}
        with self.store.transaction() as db:
            db.execute('INSERT OR REPLACE INTO code_evidence VALUES(?,?,?,?,?,?,?,?)',
                       (run_id, str(workspace), encode(file_manifest(workspace)), diff,
                        digest(diff.encode()), encode(tests), '{}', time.time()))
        result = {'outcome': 'SUCCESS', 'text': '# Repository change\n\nChanged app.txt to the new text.'}
        if self.reports:
            result['model_used'] = self.reports
        return result


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ.pop('KEL_WORKFORCE', None)
        self.store = Store(Path(self.tmp.name) / 'data')
        staff.ensure_schema(self.store)
        CodingAdapter(self.store)  # the coding bridge's tables


class EngineBindingTests(Base):
    def setUp(self):
        super().setUp()
        self.project = make_project(self.tmp.name)

    def job(self, text='Fix the typo in app.txt'):
        contract = compile_coding(text, self.project, ['python', '-c', 'pass'])
        contract['staffing'] = staff.plan_job(self.store, contract, text)
        return self.store.create(contract)

    def tick_until(self, adapters, job, until, timeout=20):
        engine = Engine(self.store, adapters)
        try:
            deadline = time.time() + timeout
            while time.time() < deadline:
                engine.tick()
                current = self.store.get(job)
                if until(current):
                    return current
                time.sleep(.02)
            raise TimeoutError(self.store.get(job)['state'])
        finally:
            engine.close()

    def test_the_builder_runs_on_its_role_model_and_the_runtime_confirms_it(self):
        job = self.job()
        claude = FakeCoder(self.store, reports='claude-opus-5-5')
        codex = FakeCoder(self.store, reports='gpt-6-astra')
        final = self.tick_until({'claude-code': claude, 'codex-code': codex}, job,
                                lambda j: j['milestones']['code']['state'] not in ('READY', 'RUNNING'))
        self.assertEqual(len(claude.calls), 1)
        self.assertEqual(codex.calls, [])
        self.assertEqual((claude.calls[0]['model_arg'], claude.calls[0]['effort_arg']), ('claude-opus-5-5', None))
        call = staff.calls(self.store, job)[0]
        self.assertEqual(call['asked']['model'], 'claude-opus-5-5')
        self.assertEqual((call['ran']['adapter'], call['ran']['model'], call['ran']['model_confirmed']),
                         ('claude-code', 'claude-opus-5-5', True))
        self.assertIsNone(call['why'])
        self.assertEqual(final['milestones']['code']['model'], 'claude-opus-5-5')

    def test_without_claude_code_the_builder_falls_back_to_codex_and_says_why(self):
        job = self.job()
        codex = FakeCoder(self.store)
        self.tick_until({'codex-code': codex}, job,
                        lambda j: j['milestones']['code']['state'] not in ('READY', 'RUNNING'))
        call = staff.calls(self.store, job)[0]
        self.assertEqual((call['asked']['model'], call['ran']['adapter']), ('claude-opus-5-5', 'codex-code'))
        self.assertIn('Claude Opus 5.5', call['why'])
        self.assertFalse(call['ran'].get('model_confirmed'), 'no model is shown until the runtime says')

    def test_a_refused_model_is_recorded_and_the_next_step_falls_back(self):
        job = self.job()
        claude = FakeCoder(self.store, refuse=True)
        codex = FakeCoder(self.store)
        self.tick_until({'claude-code': claude, 'codex-code': codex}, job,
                        lambda j: j['milestones']['code']['attempts'] >= 2
                        and j['milestones']['code']['state'] not in ('READY', 'RUNNING'))
        self.assertIn('refused', role_models.rejected(self.store, 'claude-opus-5-5'))
        calls = staff.calls(self.store, job)
        self.assertEqual(calls[0]['state'], 'failed')
        self.assertEqual(calls[1]['ran']['adapter'], 'codex-code')

    def test_a_fixed_model_that_cannot_run_waits_in_plain_words_then_resumes(self):
        role_models.set_role(self.store, 'builder', 'fixed', 'claude-opus-5-5')
        job = self.job()
        codex = FakeCoder(self.store)
        waiting = self.tick_until({'codex-code': codex}, job, lambda j: j['state'] == 'WAITING_RESOURCE')
        self.assertTrue(waiting['route_block'].startswith(FIXED_WAIT))
        self.assertIn('Builder is set to Claude Opus 5.5 only', waiting['route_block'])
        self.assertEqual(codex.calls, [])
        claude = FakeCoder(self.store, reports='claude-opus-5-5')
        self.tick_until({'codex-code': codex, 'claude-code': claude}, job,
                        lambda j: j['milestones']['code']['attempts'] >= 1)
        self.assertEqual(len(claude.calls), 1)

    def test_a_model_picked_for_the_chat_never_steers_staff(self):
        # D-69: a chat's model is Kel's own (replies and turns); staff always use their role model.
        from kel.model_prefs import ModelPrefs
        job = self.job()
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS submissions(id TEXT PRIMARY KEY,conversation_id TEXT,'
                       'text TEXT,state TEXT,error TEXT,job_id TEXT,created REAL)')
            db.execute("INSERT INTO submissions VALUES('s1','chat-1','x','DISPATCHED',NULL,?,0)", (job,))
        prefs = ModelPrefs(self.store)
        prefs.set_conversation('chat-1', 'codex', None)
        prefs.set_default('codex', None)
        claude = FakeCoder(self.store, reports='claude-opus-5-5')
        codex = FakeCoder(self.store)
        self.tick_until({'claude-code': claude, 'codex-code': codex}, job,
                        lambda j: j['milestones']['code']['attempts'] >= 1)
        self.assertEqual((len(claude.calls), len(codex.calls)), (1, 0))
        self.assertIsNone(staff.calls(self.store, job)[0]['why'])

    def test_an_unstaffed_job_still_follows_the_chat_choice(self):
        from kel.model_prefs import ModelPrefs
        contract = compile_coding('Fix the typo', self.project, ['python', '-c', 'pass'])
        job = self.store.create(contract)
        ModelPrefs(self.store).set_default('codex', None)
        claude = FakeCoder(self.store)
        codex = FakeCoder(self.store)
        self.tick_until({'claude-code': claude, 'codex-code': codex}, job,
                        lambda j: j['milestones']['code']['attempts'] >= 1)
        self.assertEqual((len(codex.calls), len(claude.calls)), (1, 0))


class RuntimeFlagTests(unittest.TestCase):
    def test_codex_text_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            default = NativeAdapter('codex', Path(tmp) / 'w', Path(tmp) / 'l').argv()
            self.assertIn('model_reasoning_effort="low"', default)
            self.assertNotIn('-m', default)
            staffed = NativeAdapter('codex', Path(tmp) / 'w', Path(tmp) / 'l', model='gpt-6-astra',
                                    effort='high').argv()
            self.assertEqual(staffed[staffed.index('-m') + 1], 'gpt-6-astra')
            self.assertIn('model_reasoning_effort="high"', staffed)
            auto = NativeAdapter('codex', Path(tmp) / 'w', Path(tmp) / 'l', model='gpt-6-astra',
                                 effort=None).argv()
            self.assertFalse(any('model_reasoning_effort' in part for part in auto))

    def test_claude_text_flags_and_the_model_it_reports(self):
        import kel.native as native
        with tempfile.TemporaryDirectory() as tmp:
            saved = native.executable
            native.executable = lambda provider: ['claude']
            try:
                adapter = NativeAdapter('claude', Path(tmp) / 'w', Path(tmp) / 'l', model='claude-fable-5-1',
                                        fallback_model='fable', effort='max')
                argv = adapter.argv()
            finally:
                native.executable = saved
            self.assertEqual(argv[argv.index('--model') + 1], 'claude-fable-5-1')
            self.assertEqual(argv[argv.index('--fallback-model') + 1], 'fable')
            self.assertEqual(argv[argv.index('--effort') + 1], 'max')
            parsed = adapter.parse(json.dumps({'result': 'ok', 'session_id': 's', 'modelUsage': {
                'claude-haiku-4-5': {'outputTokens': 3}, 'claude-fable-5': {'outputTokens': 900}}}))
            self.assertEqual(parsed['model_used'], 'claude-fable-5',
                             'the model that ran (Claude Code fell back), not the one asked for')

    def test_the_coding_connection_sends_model_and_effort_and_reports_the_thread(self):
        from kel.appserver import CodexConnection

        class Wire(CodexConnection):
            def __init__(self, thread=None):
                self.workspace = 'w'
                self.sent = []
                self.events = queue.Queue()
                self.thread = thread if thread is not None else {'thread': {'id': 't'}}

            def call(self, method, params, timeout=25):
                self.sent.append((method, params))
                if method == 'model/list':
                    return {'data': [{'model': 'default-model', 'isDefault': True}]}
                if method == 'thread/start':
                    return self.thread
                if method == 'turn/start':
                    self.events.put({'method': 'turn/completed',
                                     'params': {'threadId': 't', 'turn': {'id': 'u', 'status': 'completed'}}})
                    return {'turn': {'id': 'u'}}
                return {}

        seen = []
        wire = Wire({'thread': {'id': 't'}, 'model': 'gpt-6-astra', 'reasoningEffort': 'high'})
        wire.run('do it', model='gpt-6-astra', effort='high', on_event=seen.append)
        sent = dict(wire.sent)
        self.assertEqual(sent['thread/start']['model'], 'gpt-6-astra')
        self.assertEqual(sent['turn/start']['effort'], 'high')
        self.assertNotIn('model/list', sent)
        self.assertIn({'method': 'kel/thread', 'params': {'threadId': 't', 'model': 'gpt-6-astra',
                                                          'reasoningEffort': 'high'}}, seen)
        claude = Wire()
        claude.run('do it', model='claude-opus-5-5', fallback_model='opus', thread_effort='xhigh')
        sent = dict(claude.sent)
        self.assertEqual((sent['thread/start']['model'], sent['thread/start']['fallbackModel'],
                          sent['thread/start']['effort']), ('claude-opus-5-5', 'opus', 'xhigh'))
        unstaffed = Wire()
        unstaffed.run('do it')
        sent = dict(unstaffed.sent)
        self.assertEqual((sent['thread/start']['model'], sent['turn/start']['effort']), ('default-model', 'low'),
                         'an unstaffed run is unchanged')
        self.assertNotIn('effort', sent['thread/start'])


class ReviewerBindingTests(Base):
    class Reviewer:
        def __init__(self, provider, model, used):
            self.provider, self.model, self.used = provider, model, used

        def execute(self, prompt, run_id=None, **kwargs):
            return {'outcome': 'SUCCESS', 'model_used': self.used, 'reasoning_used': 'auto',
                    'text': json.dumps({'verdict': 'VERIFIED', 'findings': ['Meets the request.']})}

    def test_a_staffed_review_runs_on_the_verifier_model_in_another_family(self):
        from kel.commander import Commander
        contract = {'request': 'Write a haiku', 'milestones': [{'id': 'd', 'objective': 'Write a haiku',
                    'filename': 'd.md', 'depends_on': [], 'checks': [
                        {'kind': 'min_chars', 'value': 3}, {'kind': 'manual_review', 'rubric': 'Good.'}]}]}
        contract['staffing'] = staff.plan_job(self.store, contract)
        job = self.store.create(contract)
        run = self.store.claim(job, 'd', provider='claude')
        self.store.enqueue_result('r', run['id'], run['epoch'], {'outcome': 'SUCCESS', 'text': 'Leaves fall.'})
        self.store.consume()
        self.store.verify(job, 'd')
        built = []
        test = self

        class Staff:
            def staff_adapters(self):
                return {'codex', 'claude'}

            def staff_model(self, binding, timeout=100, turn=False):
                built.append(binding)
                return test.Reviewer(binding['adapter'], binding['model_arg'], binding['model_arg'])

        commander = Commander(self.Reviewer('claude', None, None))
        commander.staff = Staff()
        self.assertEqual(commander.review(self.store, job, 'd'), 'VERIFIED')
        self.assertEqual((built[0]['adapter'], built[0]['model_arg']), ('codex', 'gpt-6-astra'))
        check = next(c for c in self.store.get(job)['milestones']['d']['checks'] if c['kind'] == 'manual_review')
        self.assertEqual((check['reviewer_provider'], check['reviewer_model']), ('codex', 'gpt-6-astra'))
        call = next(c for c in staff.calls(self.store, job) if c['kind'] == 'check')
        self.assertEqual((call['role'], call['state'], call['ran']['independence'], call['ran']['model']),
                         ('verifier', 'done', 'different', 'gpt-6-astra'))

    def test_an_unstaffed_review_is_unchanged(self):
        from kel.commander import Commander
        contract = {'request': 'Write a haiku', 'milestones': [{'id': 'd', 'objective': 'Write a haiku',
                    'filename': 'd.md', 'depends_on': [], 'checks': [
                        {'kind': 'min_chars', 'value': 3}, {'kind': 'manual_review', 'rubric': 'Good.'}]}]}
        job = self.store.create(contract)
        run = self.store.claim(job, 'd', provider='claude')
        self.store.enqueue_result('r', run['id'], run['epoch'], {'outcome': 'SUCCESS', 'text': 'Leaves fall.'})
        self.store.consume()
        self.store.verify(job, 'd')
        commander = Commander(self.Reviewer('codex', None, None))
        self.assertEqual(commander.review(self.store, job, 'd'), 'VERIFIED')
        self.assertEqual(staff.calls(self.store, job), [])


class SettingsRouteTests(unittest.TestCase):
    def test_role_models_through_the_engine_api(self):
        from kel.service import Service
        with tempfile.TemporaryDirectory() as tmp:
            saved = dict(os.environ)
            try:
                os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none')
                os.environ.pop('ANTHROPIC_API_KEY', None)
                service = Service(tmp)
                try:
                    service.engine.adapters = {'codex': object(), 'codex-code': object()}
                    listing = service.action('/api/model', {'action': 'roles'})
                    rows = {row['role']: row for row in listing['roles']}
                    self.assertEqual(rows['builder']['model_label'], 'Claude Opus 5.5')
                    self.assertFalse(rows['builder']['available'])
                    self.assertTrue(rows['verifier']['available'])
                    changed = service.action('/api/model', {'action': 'set_role', 'role': 'builder',
                                                             'mode': 'preferred', 'model': 'codex',
                                                             'reasoning': 'high'})
                    rows = {row['role']: row for row in changed['roles']}
                    self.assertEqual((rows['builder']['model'], rows['builder']['reasoning']), ('codex', 'high'))
                    self.assertTrue(rows['builder']['available'])
                    reset = service.action('/api/model', {'action': 'reset_role', 'role': 'builder'})
                    self.assertTrue({row['role']: row for row in reset['roles']}['builder']['is_default'])
                    with self.assertRaises(Exception):
                        service.action('/api/model', {'action': 'set_role', 'role': 'builder', 'mode': 'x'})
                finally:
                    service.shutdown()
            finally:
                os.environ.clear()
                os.environ.update(saved)


if __name__ == '__main__':
    unittest.main()
