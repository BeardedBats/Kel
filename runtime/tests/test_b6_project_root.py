"""B6: project-root routing for ACP conversations.

A coding request must use an explicitly selected project root (or create a new
project for greenfield), never silently adopt a temp/donor working directory.
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

from kel.service import Service


class FakeModel:
    def execute(self, prompt, **kwargs):
        return {'outcome': 'SUCCESS', 'text': 'chat reply'}


class ProjectRootRoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        saved = dict(os.environ)
        os.environ.pop('ANTHROPIC_API_KEY', None)
        os.environ.pop('KEL_INTERNAL_MODEL', None)
        os.environ['KEL_REVIEWER'] = 'none'
        os.environ['KEL_SKIP_TELEMETRY'] = '1'
        self.addCleanup(lambda: os.environ.update(saved))
        self.service = Service(self.temp.name)
        self.service.model = FakeModel()
        self.service.engine.adapters = {}  # routing checks only; no real CLI runs
        self.addCleanup(self.service.shutdown)

    def plan(self, text, rooted=False):
        base = Path(self.temp.name)
        if rooted:
            proot = base / 'proj'
            proot.mkdir()
            subprocess.run(['git', 'init', str(proot)], capture_output=True, check=False)
            subprocess.run(['git', '-C', str(proot), '-c', 'user.name=Kel', '-c', 'user.email=kel@localhost',
                            'commit', '--allow-empty', '-m', 'init'], capture_output=True, check=False)
            pid = self.service.context.project('proj', str(proot))
            with contextlib.closing(self.service.store.connect()) as db:
                db.execute('INSERT INTO project_tests VALUES(?,?)', (pid, json.dumps(['python', 'smoke_test.py'])))
            cid = self.service.context.conversation(project_id=pid)
        else:
            cid = self.service.context.conversation('default')
        with patch('pathlib.Path.home', return_value=base):
            sid = self.service.submit({'text': text, 'conversation': cid})
        deadline = time.time() + 15
        row = None
        while time.time() < deadline:
            with contextlib.closing(self.service.store.connect()) as db:
                row = db.execute('SELECT state FROM submissions WHERE id=?', (sid,)).fetchone()
            if row and row['state'] in ('DISPATCHED', 'FAILED', 'INTERRUPTED'):
                break
            time.sleep(0.05)
        jobs = [j for j in self.service.store.list_jobs() if j['conversation'] == cid]
        with contextlib.closing(self.service.store.connect()) as db:
            msgs = [m['text'] for m in db.execute(
                "SELECT text FROM messages WHERE conversation_id=? AND role='assistant' ORDER BY seq", (cid,))]
        return row['state'], jobs, msgs

    def test_greenfield_still_creates_a_project(self):
        state, jobs, msgs = self.plan("I want to create a little app that toggles my microphone mute button")
        self.assertEqual(state, 'DISPATCHED')
        self.assertEqual([j['contract'].get('kind') for j in jobs], ['coding'])
        self.assertTrue(all(j['contract'].get('greenfield') for j in jobs))

    def test_plain_chat_does_not_prompt(self):
        state, jobs, msgs = self.plan("hello, what can you do?")
        self.assertEqual(state, 'DISPATCHED')
        self.assertEqual(jobs, [])
        self.assertIn('chat reply', msgs)

    def test_ambiguous_coding_without_root_asks_for_a_project(self):
        state, jobs, msgs = self.plan("fix the login bug in the auth module")
        self.assertEqual(state, 'DISPATCHED')
        self.assertEqual(jobs, [])
        self.assertTrue(any('no project is selected' in m for m in msgs), msgs)

    def test_existing_project_coding_uses_the_selected_root(self):
        state, jobs, msgs = self.plan("fix the login bug in the auth module", rooted=True)
        self.assertEqual(state, 'DISPATCHED')
        self.assertEqual([j['contract'].get('kind') for j in jobs], ['coding'])
        self.assertFalse(jobs[0]['contract'].get('greenfield'))
        self.assertTrue(jobs[0]['contract'].get('root'))


if __name__ == '__main__':
    unittest.main()
