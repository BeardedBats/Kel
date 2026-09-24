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
            self.service = Service(self.tmp.name)

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

    def test_greenfield_acceptance_request_becomes_a_coding_job(self):
        text = "I want to create a little app that allows me to control my microphone's mute button, to turn it on and off from my keyboard"
        with patch('pathlib.Path.home', return_value=Path(self.tmp.name)):
            # Even when the active project HAS a root (desktop temp workspace),
            # greenfield intent must create a fresh project elsewhere.
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
            self.assertEqual(Path(contract['root']).parent.name, 'Kel Projects')
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
