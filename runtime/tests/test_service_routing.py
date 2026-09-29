# Deterministic initial routing: Service.submit derives kind via router.classify
# when the client omits it.
import contextlib
import os
import tempfile
import time
import unittest
from unittest.mock import patch

from kel.service import Service
from kel.router import classify
from pathlib import Path


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('ANTHROPIC_API_KEY', None)
            os.environ.pop('KEL_INTERNAL_MODEL', None)
            os.environ['KEL_SKIP_TELEMETRY'] = '1'
            os.environ['KEL_REVIEWER'] = 'none'
            os.environ['KEL_TURN_MODEL'] = 'none'  # D-53: deterministic keyword gate
            # Kel's data folder beside the person's folders, never around them (D-64 protected paths).
            self.service = Service(Path(self.tmp.name) / 'data')

    def tearDown(self):
        self.service.shutdown()
        self.tmp.cleanup()

    def wait_submission(self, sid, terminal=('DISPATCHED', 'SETTLED', 'FAILED', 'INTERRUPTED')):
        deadline = time.time() + 15
        while time.time() < deadline:
            with contextlib.closing(self.service.store.connect()) as db:
                row = db.execute('SELECT state FROM submissions WHERE id=?', (sid,)).fetchone()
            if row and row['state'] in terminal:
                return row['state']
            time.sleep(.05)
        raise TimeoutError('submission did not settle')

    def test_state_exposes_the_chosen_route_for_active_runs(self):
        # D12: the routing decision behind a run must be readable by user surfaces (provider +
        # policy + fallbacks + excluded reasons), straight from the run.claimed event.
        contract = {'request': 'Route transparency', 'milestones': [
            {'id': 'm1', 'objective': 'Work', 'filename': 'out.md', 'depends_on': [],
             'checks': [{'kind': 'min_chars', 'value': 10}]}]}
        job = self.service.store.create(contract, conversation='main')
        job_id = job['id'] if isinstance(job, dict) else job
        route = {'selected': 'fixture', 'fallbacks': ['other'],
                 'excluded': {'alt': ['quota exhausted']}, 'policy': 'eligible-cost-v2',
                 'demoted': [], 'chain': ['fixture', 'other'],
                 'why': 'lowest cost among the models that are healthy and capable here',
                 'unknown_cost': True, 'unknown_quota': True}
        self.service.store.claim(job_id, 'm1', provider='fixture', route=route, model='fixture-1')
        state = self.service.state('main')
        decision = state['routes'][job_id]
        self.assertEqual(decision['provider'], 'fixture')
        self.assertEqual(decision['route']['selected'], 'fixture')
        self.assertEqual(decision['route']['policy'], 'eligible-cost-v2')
        self.assertEqual(decision['route']['excluded'], {'alt': ['quota exhausted']})
        # V2-09: “Why this model?” is read back from the stored decision, in plain words.
        why = self.service.action('/api/model', {'action': 'why', 'conversation': 'main'})
        self.assertEqual(why['job'], job_id)
        self.assertEqual(why['selected'], 'fixture')
        self.assertEqual(why['chain'], ['fixture', 'other'])
        self.assertEqual(why['answer'],
                         'Kel is using fixture: the lowest cost among the models that are '
                         'healthy and capable here.')

    def test_classify_maps_request_kinds(self):
        self.assertEqual(classify('status')['kind'], 'status')
        self.assertEqual(classify('write a plan for the garden')['kind'], 'document')
        self.assertEqual(classify('hello, how are you?')['kind'], 'conversation')
        self.assertEqual(classify("I want to create a little app that allows me to control my microphone's mute button, to turn it on and off from my keyboard")['kind'], 'coding')
        self.assertEqual(classify('write a little app that renames files')['kind'], 'coding')
        self.assertEqual(classify('build me a small tool that converts csv to json')['kind'], 'coding')

    def test_file_action_names_the_file_and_the_folder(self):
        from kel.router import file_action
        self.assertEqual(file_action(r'Create a file named hello.txt containing hi in C:\Users\me\notes'),
                         {'filename': 'hello.txt', 'folder': r'C:\Users\me\notes'})
        self.assertEqual(file_action('save report.csv to /tmp/out'),
                         {'filename': 'report.csv', 'folder': '/tmp/out'})
        self.assertIsNone(file_action('Create a file named hello.txt containing hi'))
        self.assertIsNone(file_action('Write a short plan for a weekend hike'))
        self.assertIsNone(file_action(r'what is in C:\Windows?'))

    def test_named_file_in_a_folder_is_work_that_never_claims_the_file(self):
        # Measured: "Create a file named hello.txt containing hi in <folder>" became a document job,
        # was reported VERIFIED, and no file existed. Outside a saved project it is still work, but
        # its contract records the file request so publication says no file was created.
        # D-81: a folder inside the Memory folder (a folder outside it is refused up front).
        from kel.memory_folder import memory_root
        folder = memory_root(self.service.store.root) / ('target-%s' % Path(self.tmp.name).name)
        folder.mkdir(parents=True)
        self.service.engine.adapters = {}
        sid = self.service.submit({'text': 'Create a file named hello.txt containing hi in ' + str(folder),
                                   'conversation': 'main'})
        self.assertEqual(self.wait_submission(sid), 'DISPATCHED')
        jobs = [j for j in self.service.store.list_jobs() if j['conversation'] == 'main']
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['contract']['file_request'], {'filename': 'hello.txt', 'folder': str(folder)})
        self.assertNotEqual(jobs[0]['contract'].get('kind'), 'coding')

    def _rooted_chat(self, tests=True):
        (Path(self.tmp.name)/'rooted').mkdir(exist_ok=True)
        rooted = self.service.context.project('rooted', str(Path(self.tmp.name)/'rooted'), '')
        import subprocess
        folder = str(Path(self.tmp.name)/'rooted')
        subprocess.run(['git', 'init', folder], capture_output=True, check=False)
        subprocess.run(['git', '-C', folder, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '--allow-empty',
                        '-m', 'init'], capture_output=True, check=False)
        if tests:
            import json
            with self.service.store.transaction() as db:
                db.execute('INSERT OR REPLACE INTO project_tests VALUES(?,?)', (rooted, json.dumps(['python', '-V'])))
        return rooted, self.service.context.conversation(project_id=rooted, title='rooted')

    def test_this_project_means_the_active_project_not_a_new_one(self):
        # LIVE-2 / D-74.2: "in this project" never creates a new project; the work goes to the
        # active project's folder.
        rooted, cid = self._rooted_chat()
        before = set(p['id'] for p in self.service.projects.list()) if hasattr(self.service.projects, 'list') else None
        for text in ('In this project, create a tool that adds two numbers in calc.py',
                     'I want to create a little app that shows the weather'):
            sid = self.service.submit({'text': text, 'conversation': cid})
            self.assertEqual(self.wait_submission(sid), 'DISPATCHED')
        jobs = [j for j in self.service.store.list_jobs() if j['conversation'] == cid]
        self.assertEqual(len(jobs), 2)
        for job in jobs:
            self.assertFalse(job['contract'].get('greenfield'))
            self.assertEqual(Path(job['contract']['root']), Path(self.tmp.name)/'rooted')
        if before is not None:
            self.assertEqual(set(p['id'] for p in self.service.projects.list()), before)

    def test_greenfield_acceptance_request_becomes_a_coding_job(self):
        text = ("I want to create a new separate project: a little app that allows me to control my microphone's "
                "mute button, to turn it on and off from my keyboard")
        with patch('pathlib.Path.home', return_value=Path(self.tmp.name)):
            # D-74.2: with a project that has a folder active, only an explicit request for a new or
            # separate project creates one — under the Kel Projects root, never in the folder.
            (Path(self.tmp.name)/'rooted').mkdir(exist_ok=True)
            rooted = self.service.context.project('rooted', str(Path(self.tmp.name)/'rooted'), '')
            cid = self.service.context.conversation(project_id=rooted, title='green')
            sid = self.service.submit({'text': text, 'conversation': cid})
            self.assertEqual(self.wait_submission(sid), 'DISPATCHED')
            with contextlib.closing(self.service.store.connect()) as db:
                kind = db.execute('SELECT kind FROM submission_packets WHERE id=?', (sid,)).fetchone()['kind']
            self.assertEqual(kind, 'coding')
            jobs = [j for j in self.service.store.list_jobs() if j['conversation'] == cid]
            self.assertEqual(len(jobs), 1)
            contract = jobs[0]['contract']
            self.assertEqual(contract['kind'], 'coding')
            self.assertTrue(contract.get('greenfield'))
            self.assertEqual(contract['test_command'], ['python', 'smoke_test.py'])
            self.assertEqual(Path(contract['root']).parent, Path(os.environ['KEL_PROJECTS_ROOT']))
            # VIS-16: a short human project name and a tidy folder, not a slug of the whole request.
            project = self.service.projects.row(contract['project_id'])
            self.assertLessEqual(len(project['name']), 40)
            self.assertNotIn('i-want-to', project['name'].lower())
            self.assertNotIn('i want to', project['name'].lower())
            self.assertRegex(Path(contract['root']).name, r'^[a-z0-9]+(-[a-z0-9]+)*$')
            self.assertNotIn('i-want-to', Path(contract['root']).name)
            self.assertNotEqual(str(Path(contract['root'])), str(Path(self.tmp.name)/'rooted'))
            self.assertTrue(Path(contract['root']).is_dir())
            self.assertTrue((Path(contract['root'])/'.git').is_dir())
            import subprocess
            head = subprocess.run(['git','-C',str(contract['root']),'rev-parse','HEAD'],capture_output=True,text=True)
            self.assertEqual(head.returncode, 0, 'greenfield repo needs an initial HEAD commit')

    def test_status_query_answers_without_a_model(self):
        sid = self.service.submit({'text': 'status', 'conversation': 'main'})
        self.assertEqual(self.wait_submission(sid), 'SETTLED')
        state = self.service.state('main')
        self.assertTrue(any(m['role'] == 'assistant' and 'No work is running' in m['text'] for m in state['messages']))
        self.assertEqual(state['jobs'], [])
        submission = next(item for item in state['submissions'] if item['id'] == sid)
        self.assertIsNone(submission['job_id'])

    def test_missing_recipe_answer_settles_without_a_job(self):
        sid = self.service.submit({'text': 'Run a missing recipe', 'conversation': 'main',
                                   'kind': 'recipe'})
        self.assertEqual(self.wait_submission(sid), 'SETTLED')
        state = self.service.state('main')
        submission = next(item for item in state['submissions'] if item['id'] == sid)
        self.assertIsNone(submission['job_id'])
        self.assertTrue(any(message['role'] == 'assistant' and
                            'could not find that recipe' in message['text']
                            for message in state['messages']))

    def test_old_no_job_dispatch_is_read_as_settled_without_rewriting_data(self):
        with self.service.store.transaction() as db:
            db.execute('INSERT INTO submissions VALUES(?,?,?,?,?,?,?)',
                       ('old-answer', 'main', 'status', 'DISPATCHED', None, None, 1.0))
        submission = next(item for item in self.service.state('main')['submissions']
                          if item['id'] == 'old-answer')
        self.assertEqual(submission['state'], 'SETTLED')
        with contextlib.closing(self.service.store.connect()) as db:
            raw = db.execute('SELECT state FROM submissions WHERE id=?',
                             ('old-answer',)).fetchone()['state']
        self.assertEqual(raw, 'DISPATCHED')

    def test_untyped_request_is_classified_and_compiled_deterministically(self):
        sid = self.service.submit({'text': 'Write a short plan for a weekend hike', 'conversation': 'main'})
        self.assertEqual(self.wait_submission(sid), 'DISPATCHED')
        with contextlib.closing(self.service.store.connect()) as db:
            kind = db.execute('SELECT kind FROM submission_packets WHERE id=?', (sid,)).fetchone()['kind']
        self.assertEqual(kind, 'document')
        jobs = [j for j in self.service.store.list_jobs() if j['conversation'] == 'main']
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['contract']['compiler'], 'document-template-v1')

    def test_explicit_client_kind_still_wins(self):
        # No adapters: kind='chat' must attempt the direct chat path and fail
        # planning with the explicit model error, proving the client kind won.
        self.service.engine.adapters.clear()
        sid = self.service.submit({'text': 'hello there', 'conversation': 'main', 'kind': 'chat'})
        state = self.wait_submission(sid)
        self.assertEqual(state, 'FAILED')
        with contextlib.closing(self.service.store.connect()) as db:
            row = db.execute("SELECT kind, error FROM submission_packets JOIN submissions "
                             "ON submissions.id=submission_packets.id WHERE submission_packets.id=?", (sid,)).fetchone()
        self.assertEqual(row['kind'], 'chat')
        self.assertIn('Connect a model', row['error'])


if __name__ == '__main__':
    unittest.main()
