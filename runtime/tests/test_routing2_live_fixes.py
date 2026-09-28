"""Routing 2 §5.0 — the failures a live off-screen check of the packaged build found, each pinned.

The check (main@61c73ff, a copy of Nick's data, Full access): "In this project, add a multiply(a, b)
function to calc.py and a pytest test for it in test_calc.py." became a writing job with no change.
Codex refused GPT-6 Luna ("not supported when using Codex with a ChatGPT account") and GPT-6 Astra
("requires a newer version of Codex"); Kel tried Luna again, said Codex was "not set up", planned
from the template, and the Verifier's failure left the result unverified. No provider is called here.
"""
import contextlib
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from kel import native, role_models, staff
from kel.core import Store

LUNA_REFUSAL = ("The 'gpt-6-luna' model is not supported when using Codex with a ChatGPT account.")
ASTRA_REFUSAL = ("The 'gpt-6-astra' model requires a newer version of Codex. Please upgrade to the "
                 "latest app or CLI.")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ.pop('KEL_WORKFORCE', None)
        # Codex's own model list lives in CODEX_HOME; an empty one says nothing (no cache).
        os.environ['CODEX_HOME'] = str(Path(self.tmp.name) / 'codex-home')
        self.store = Store(Path(self.tmp.name) / 'data')
        staff.ensure_schema(self.store)


class CodexStreamTests(unittest.TestCase):
    def adapter(self, tmp):
        return native.NativeAdapter('codex', Path(tmp) / 'w', Path(tmp) / 'l')

    def test_a_refusal_in_turn_failed_keeps_the_runtimes_words(self):
        # Codex exec reports a failed turn as {"type":"turn.failed","error":{"message":...}}; the old
        # parser read only a top-level message, so every refusal read "Native turn failed".
        output = '\n'.join(json.dumps(x) for x in [
            {'type': 'thread.started', 'thread_id': 't1'},
            {'type': 'turn.started'},
            {'type': 'error', 'message': LUNA_REFUSAL},
            {'type': 'turn.failed', 'error': {'message': LUNA_REFUSAL}}])
        with tempfile.TemporaryDirectory() as tmp:
            parsed = self.adapter(tmp).parse(output)
        self.assertEqual(parsed['outcome'], 'FAILED')
        self.assertIn('not supported when using Codex with a ChatGPT account', parsed['error'])
        self.assertEqual(parsed['error'].count('not supported'), 1, 'the same words are not repeated')

    def test_codex_usage_is_kept_from_turn_completed(self):
        output = '\n'.join(json.dumps(x) for x in [
            {'type': 'thread.started', 'thread_id': 't1'},
            {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'Done.'}},
            {'type': 'turn.completed', 'usage': {'input_tokens': 1200, 'cached_input_tokens': 800,
                                                 'output_tokens': 90, 'reasoning_output_tokens': 40}}])
        with tempfile.TemporaryDirectory() as tmp:
            parsed = self.adapter(tmp).parse(output)
        self.assertEqual(parsed['outcome'], 'SUCCESS')
        self.assertEqual(parsed['usage']['cached_input_tokens'], 800)

    def test_a_failed_run_on_an_explicit_model_reports_the_refusal_once(self):
        # A fake Codex that refuses the model on its JSON stream and exits 1 (as Codex does).
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / 'fake_codex.py'
            script.write_text('import sys, json\nsys.stdin.read()\n'
                              'print(json.dumps({"type":"turn.failed","error":{"message":%r}}))\n'
                              'sys.exit(1)\n' % LUNA_REFUSAL, encoding='utf-8')
            saved = native.executable
            native.executable = lambda provider: [sys.executable, str(script)]
            try:
                adapter = native.NativeAdapter('codex', Path(tmp) / 'w', Path(tmp) / 'l', model='gpt-6-luna')
                seen = []
                adapter.on_refusal = lambda error, version: seen.append(error)
                result = adapter.execute('hello')
            finally:
                native.executable = saved
        self.assertEqual(result['outcome'], 'FAILED')
        self.assertIn('not supported when using Codex with a ChatGPT account', result['error'])
        self.assertEqual(len(seen), 1)
        self.assertEqual(role_models.classify_refusal(seen[0], 'gpt-6-luna')[0], 'account')


class RefusalTests(Base):
    def test_refusals_are_classified_in_plain_words(self):
        self.assertEqual(role_models.classify_refusal(LUNA_REFUSAL, 'gpt-6-luna'),
                         ('account', "your ChatGPT account doesn't offer it in Codex"))
        self.assertEqual(role_models.classify_refusal(ASTRA_REFUSAL, 'gpt-6-astra'),
                         ('runtime_old', 'the Codex on this computer is too old for it (update Codex)'))
        self.assertEqual(role_models.classify_refusal('model claude-opus-5-5 not found', 'claude-opus-5-5')[0],
                         'not_found')
        self.assertIsNone(role_models.classify_refusal('Native CLI exited 1', 'gpt-6-luna'))
        self.assertIsNone(role_models.classify_refusal('TimeoutError', 'gpt-6-luna'))

    def test_a_refused_model_is_unavailable_in_settings_with_the_reason(self):
        adapters = {'codex', 'codex-code', 'claude', 'claude-code'}
        rows = {row['role']: row for row in role_models.listing(self.store, adapters)['roles']}
        self.assertTrue(rows['kel']['available'])
        self.assertTrue(role_models.note_refusal(self.store, 'gpt-6-luna', LUNA_REFUSAL, 'Codex CLI 0.142.5'))
        listing = role_models.listing(self.store, adapters)
        rows = {row['role']: row for row in listing['roles']}
        self.assertFalse(rows['kel']['available'])
        self.assertEqual(rows['kel']['note'],
                         "ChatGPT Luna can't run here: your ChatGPT account doesn't offer it in Codex")
        model = next(m for m in listing['models'] if m['id'] == 'gpt-6-luna')
        self.assertFalse(model['available'])
        # ...and Kel does not ask for it again: its turns and plans go to the next model.
        binding = role_models.resolve(self.store, 'kel', adapters={'codex', 'claude'})
        self.assertIsNone(binding['adapter'])
        self.assertIn("ChatGPT Luna can't run here: your ChatGPT account", binding['why'])
        self.assertNotIn('not set up', binding['why'])

    def test_a_too_old_runtime_refusal_lasts_until_the_runtime_changes(self):
        saved = role_models._current_runtime_version
        try:
            role_models._current_runtime_version = lambda model_id: 'Codex CLI 0.142.5'
            role_models.note_refusal(self.store, 'gpt-6-astra', ASTRA_REFUSAL, 'Codex CLI 0.142.5')
            later = time.time() + 3 * 86400  # older than a day: still true while Codex is unchanged
            self.assertIn('too old', role_models.rejected(self.store, 'gpt-6-astra', now=later))
            role_models._current_runtime_version = lambda model_id: 'Codex CLI 0.157.1'
            self.assertIsNone(role_models.rejected(self.store, 'gpt-6-astra', now=later),
                              'a newer Codex gets to try the model again')
        finally:
            role_models._current_runtime_version = saved

    def test_an_account_refusal_lasts_a_day(self):
        role_models.note_refusal(self.store, 'gpt-6-luna', LUNA_REFUSAL)
        self.assertIsNotNone(role_models.rejected(self.store, 'gpt-6-luna'))
        self.assertIsNone(role_models.rejected(self.store, 'gpt-6-luna', now=time.time() + 25 * 3600))

    def test_a_staff_step_refusal_is_recorded_with_its_plain_summary(self):
        with self.store.transaction() as db:
            staff.insert_call(db, call_id='run-1', job_id='job-1', milestone_id='m', role='kel', kind='work',
                              asked={'role': 'kel', 'model': 'gpt-6-luna', 'model_arg': 'gpt-6-luna',
                                     'resolved': 'gpt-6-luna'},
                              ran={'adapter': 'codex', 'runtime_version': 'Codex CLI 0.142.5'})
        from kel.core import Store as _Store
        with self.store.transaction() as db:
            _Store._settle_staff_call(db, 'run-1', 'failed',
                                      {'outcome': 'FAILED', 'error': 'Native CLI exited 1 — ' + LUNA_REFUSAL})
        call = staff.calls(self.store, 'job-1')[0]
        self.assertEqual(call['summary'],
                         "ChatGPT Luna can't run here: your ChatGPT account doesn't offer it in Codex")
        self.assertIsNotNone(role_models.rejected(self.store, 'gpt-6-luna'))

    def test_codex_model_list_counts_only_when_our_codex_fetched_it(self):
        home = Path(os.environ['CODEX_HOME'])
        home.mkdir(parents=True)
        (home / 'models_cache.json').write_text(json.dumps(
            {'client_version': '0.142.5', 'models': [{'slug': 'gpt-5.5'}]}), encoding='utf-8')
        saved = native.codex_executable
        try:
            native.codex_executable = lambda refresh=False, env=None: {'path': 'x', 'version': 'codex-cli 0.142.5'}
            self.assertFalse(role_models.codex_offers('gpt-6-luna'))
            self.assertIn("doesn't list it", role_models.rejected(self.store, 'gpt-6-luna'))
            native.codex_executable = lambda refresh=False, env=None: {'path': 'x', 'version': 'codex-cli 0.144.5'}
            self.assertIsNone(role_models.codex_offers('gpt-6-luna'),
                              "another Codex's list says nothing about the one Kel runs")
        finally:
            native.codex_executable = saved


class HonestNoteTests(Base):
    def test_a_runtime_set_aside_for_this_step_is_not_called_missing(self):
        binding = role_models.resolve(self.store, 'kel', adapters={'claude'},
                                      set_aside={'codex': "didn't finish this step on its earlier tries"})
        self.assertIn("ChatGPT Luna runs on Codex, which didn't finish this step on its earlier tries",
                      binding['why'])
        self.assertNotIn('not set up', binding['why'])


class CodexChoiceTests(unittest.TestCase):
    def test_the_newest_installed_codex_is_chosen_and_config_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            app_bin = Path(tmp) / 'app' / 'bin'
            npm_bin = Path(tmp) / 'npm' / 'node_modules' / '@openai' / 'codex' / 'node_modules' / '@openai' / \
                'codex-win32-x64' / 'vendor' / 'x86_64-pc-windows-msvc' / 'bin'
            for folder in (app_bin, npm_bin):
                folder.mkdir(parents=True)
                (folder / 'codex.exe').write_bytes(b'')
            old_app, new_npm = str((app_bin / 'codex.exe').resolve()), str((npm_bin / 'codex.exe').resolve())
            saved = dict(native._VERSIONS)
            native._VERSIONS[old_app] = 'codex-cli 0.142.5'
            native._VERSIONS[new_npm] = 'codex-cli 0.144.5'
            try:
                env = {'PATH': str(app_bin), 'APPDATA': str(Path(tmp) / ''), 'LOCALAPPDATA': ''}
                # APPDATA/npm/node_modules/... is where the npm-global package lives.
                env['APPDATA'] = str(Path(tmp))
                chosen = native.codex_executable(refresh=True, env=env)
                if os.name == 'nt':
                    self.assertEqual(chosen['path'], new_npm, 'the first on PATH is an old bundled copy')
                    self.assertEqual(chosen['version'], 'codex-cli 0.144.5')
                env['KEL_CODEX_PATH'] = old_app
                self.assertEqual(native.codex_executable(refresh=True, env=env)['path'], old_app,
                                 'a configured Codex always wins')
            finally:
                native._VERSIONS.clear()
                native._VERSIONS.update(saved)

    def test_versions_order_prereleases_below_releases(self):
        self.assertLess(native.parse_version('codex-cli 0.130.0-alpha.5'), native.parse_version('0.130.0'))
        self.assertLess(native.parse_version('codex-cli 0.142.5'), native.parse_version('codex-cli 0.144.5'))
        self.assertIsNone(native.parse_version('no version here'))


def reviewed_job(store):
    contract = {'request': 'Write a haiku', 'milestones': [{'id': 'd', 'objective': 'Write a haiku',
                'filename': 'd.md', 'depends_on': [], 'checks': [
                    {'kind': 'min_chars', 'value': 3}, {'kind': 'manual_review', 'rubric': 'Good.'}]}]}
    contract['staffing'] = staff.plan_job(store, contract)
    job = store.create(contract)
    run = store.claim(job, 'd', provider='claude')
    store.enqueue_result('r', run['id'], run['epoch'], {'outcome': 'SUCCESS', 'text': 'Leaves fall.'})
    store.consume()
    store.verify(job, 'd')
    return job


class Reviewer:
    def __init__(self, provider, model, refuse=None):
        self.provider, self.model, self.refuse = provider, model, refuse
        self.calls = 0
        self.on_refusal = None

    def execute(self, prompt, run_id=None, **kwargs):
        self.calls += 1
        if self.refuse:
            if self.on_refusal:
                self.on_refusal(self.refuse, 'Codex CLI 0.142.5')
            return {'outcome': 'FAILED', 'error': 'Native CLI exited 1 — ' + self.refuse}
        return {'outcome': 'SUCCESS', 'model_used': self.model or 'default', 'reasoning_used': 'auto',
                'text': json.dumps({'verdict': 'VERIFIED', 'findings': ['Meets the request.'],
                                    'challenges': [], 'coverage': 'the result'})}


class HandOverTests(Base):
    def setUp(self):
        super().setUp()
        saved = role_models._current_runtime_version
        role_models._current_runtime_version = lambda model_id: 'Codex CLI 0.142.5'
        self.addCleanup(lambda: setattr(role_models, '_current_runtime_version', saved))

    def staff_stub(self, refusals, built):
        store = self.store

        class Staff:
            def staff_adapters(self):
                return {'codex', 'claude'}

            def staff_model(self, binding, timeout=100, turn=False):
                if not binding.get('adapter'):
                    return None
                built.append(binding['model'])
                reviewer = Reviewer(binding['adapter'], binding['model_arg'], refusals.get(binding['model']))
                model_id = binding['model']
                reviewer.on_refusal = lambda error, version: role_models.note_refusal(store, model_id, error, version)
                return reviewer
        return Staff()

    def test_the_verifier_hands_over_when_its_model_cannot_run(self):
        from kel.commander import Commander
        job = reviewed_job(self.store)
        built = []
        commander = Commander(Reviewer('claude', None))
        commander.staff = self.staff_stub({'gpt-6-astra': ASTRA_REFUSAL}, built)
        self.assertEqual(commander.review(self.store, job, 'd'), 'VERIFIED')
        self.assertEqual(built[0], 'gpt-6-astra')
        self.assertNotEqual(built[1], 'gpt-6-astra', 'the next reviewer is another model')
        checks = [c for c in staff.calls(self.store, job) if c['kind'] == 'check']
        self.assertEqual([c['state'] for c in checks], ['failed', 'done'])
        self.assertIn('too old', checks[0]['summary'])
        self.assertIn('first reviewer could not run', checks[1]['why'])
        self.assertIn('too old', role_models.rejected(self.store, 'gpt-6-astra'))

    def test_only_when_no_model_can_review_is_the_result_unverified(self):
        from kel.commander import Commander
        job = reviewed_job(self.store)
        built = []
        everyone = {model: LUNA_REFUSAL for model in role_models.MODELS}
        broken = Reviewer('claude', None, refuse=LUNA_REFUSAL)
        commander = Commander(broken)
        commander.staff = self.staff_stub(everyone, built)
        self.assertEqual(commander.review(self.store, job, 'd'), 'UNCERTAIN')
        self.assertLessEqual(len([c for c in staff.calls(self.store, job) if c['kind'] == 'check']),
                             Commander.REVIEW_HANDOVERS)

    def test_the_oracle_hands_over_too(self):
        from kel import oracle
        job = reviewed_job(self.store)
        built = []
        subject = self.store.get(job)['milestones']['d']['artifact']['sha256']
        oracle._start(self.store, job, subject, ['test'])
        oracle._review(self.store, self.store.get(job), 'd', subject,
                       self.staff_stub({'gpt-6-astra': ASTRA_REFUSAL}, built))
        calls = [c for c in staff.calls(self.store, job) if c['kind'] == 'oracle']
        self.assertEqual([c['state'] for c in calls], ['failed', 'done'])
        self.assertEqual(built[0], 'gpt-6-astra')


class PlannerTests(unittest.TestCase):
    class Planner:
        def __init__(self, provider, model, ok):
            self.provider, self.model, self.ok = provider, model, ok
            self.calls = 0

        def execute(self, prompt, **kwargs):
            self.calls += 1
            if not self.ok:
                return {'outcome': 'FAILED', 'error': LUNA_REFUSAL}
            return {'outcome': 'SUCCESS', 'text': json.dumps({'milestones': [
                {'id': 'doc', 'objective': 'x', 'filename': 'doc.md', 'depends_on': [],
                 'checks': [{'kind': 'min_chars', 'value': 40}]}]})}

    def test_planning_tries_every_planner_before_the_template(self):
        from kel.commander import Commander
        kel = self.Planner('codex', 'gpt-6-luna', False)
        default = self.Planner('claude', None, False)
        alternate = self.Planner('codex', None, True)
        contract, meta = Commander(default, [alternate]).plan('Write a note about tea', model=kel)
        self.assertEqual(meta['mode'], 'model_proposal')
        self.assertEqual((kel.calls, default.calls, alternate.calls), (1, 1, 1))
        self.assertEqual(meta['provider'], 'codex')


class CodingFloorTests(unittest.TestCase):
    MEASURED = ('In this project, add a multiply(a, b) function to calc.py and a pytest test for it in '
                'test_calc.py.')

    def test_the_measured_request_is_coding_intent(self):
        from kel.router import coding_intent
        self.assertTrue(coding_intent(self.MEASURED))
        self.assertTrue(coding_intent('please fix the bug in the parser'))
        self.assertTrue(coding_intent('Can you refactor the login module?'))
        self.assertFalse(coding_intent('write a blog post about unit tests'))
        self.assertFalse(coding_intent('What does calc.py do?'))
        self.assertFalse(coding_intent('add a paragraph to my notes'))

    def test_it_compiles_as_coding_in_a_project_with_a_folder_and_tests(self):
        from kel.service import Service
        with tempfile.TemporaryDirectory() as tmp:
            saved = dict(os.environ)
            try:
                os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none')
                os.environ.pop('ANTHROPIC_API_KEY', None)
                project_root = Path(tmp) / 'proj'
                project_root.mkdir()
                (project_root / 'calc.py').write_text('def add(a, b):\n    return a + b\n')
                from kel.coding import git
                git(project_root, 'init')
                git(project_root, 'add', '-A')
                git(project_root, '-c', 'user.name=Kel', '-c', 'user.email=kel@localhost', 'commit', '-m', 'base')
                service = Service(Path(tmp) / 'data')
                try:
                    created = service.projects.create('Calc', root=str(project_root),
                                                      test_command=['python', '-m', 'pytest', '-q'])
                    packet = {'project': {'id': created['id'], 'root': str(project_root)}, 'files': []}
                    self.assertTrue(service._code_in_project(self.MEASURED, packet))
                    self.assertFalse(service._code_in_project('write a blog post about unit tests', packet))
                    contract = service._compile_work('s1', 'main', self.MEASURED, dict(packet, kind_source='router'),
                                                     'conversation', False)
                    self.assertEqual(contract['kind'], 'coding')
                    without_tests = service.projects.create('Loose', root=str(project_root))
                    self.assertFalse(service._code_in_project(
                        self.MEASURED, {'project': {'id': without_tests['id'], 'root': str(project_root)}}),
                        'the broadened floor only fires where Kel can run tests')
                finally:
                    service.shutdown()
            finally:
                os.environ.clear()
                os.environ.update(saved)


class BackslashPathTests(unittest.TestCase):
    def test_project_create_accepts_backslash_paths_over_http(self):
        """The renderer's folder picker gives backslash paths; JSON over the engine's HTTP handler keeps
        them (the live report came from a path typed in a JavaScript string literal)."""
        import urllib.request
        from kel.service import serve
        import threading
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'R6Proj'
            folder.mkdir()
            saved = dict(os.environ)
            os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none')
            os.environ.pop('ANTHROPIC_API_KEY', None)
            data = Path(tmp) / 'data'
            thread = threading.Thread(target=serve, args=(str(data), 0), daemon=True)
            thread.start()
            try:
                descriptor = data / 'desktop-session.json'
                deadline = time.time() + 30
                while not descriptor.exists() and time.time() < deadline:
                    time.sleep(.1)
                session = json.loads(descriptor.read_text(encoding='utf-8'))
                path = str(folder.resolve())
                if os.name == 'nt':
                    self.assertIn('\\', path)
                body = json.dumps({'action': 'create', 'name': 'R6', 'root': path}).encode()
                request = urllib.request.Request(session['url'] + 'api/project', data=body, method='POST',
                                                 headers={'Authorization': 'Bearer ' + session['token'],
                                                          'Content-Type': 'application/json'})
                with urllib.request.urlopen(request, timeout=20) as response:
                    created = json.loads(response.read())
                self.assertEqual(Path(created['root']), folder.resolve())
                shutdown = urllib.request.Request(session['url'] + 'api/shutdown-idle', data=b'{}', method='POST',
                                                  headers={'Authorization': 'Bearer ' + session['token'],
                                                           'Content-Type': 'application/json'})
                try:
                    urllib.request.urlopen(shutdown, timeout=20).read()
                except Exception:
                    pass
                thread.join(timeout=20)
            finally:
                os.environ.clear()
                os.environ.update(saved)


if __name__ == '__main__':
    unittest.main()
