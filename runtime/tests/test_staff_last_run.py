"""Settings → Staff & models: "fell back to X last time" per role, from what the last run asked for and
what actually ran (`/api/model {action:'roles'}` rows carry `last_run`). No provider is called.
"""
import os
import tempfile
import time
import unittest
from pathlib import Path

from kel import role_models, staff, usage
from kel.core import Store

ALL = {'codex', 'codex-code', 'claude', 'claude-code'}


class LastRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ['CODEX_HOME'] = str(Path(self.tmp.name) / 'codex-home')
        self.store = Store(Path(self.tmp.name) / 'data')
        staff.ensure_schema(self.store)

    def rows(self):
        return {row['role']: row for row in role_models.listing(self.store, ALL)['roles']}

    def test_no_runs_yet_says_nothing(self):
        self.assertIsNone(self.rows()['builder']['last_run'])

    def test_a_builder_that_fell_back_says_so_with_the_reason(self):
        staff.start_call(self.store, job_id='j1', milestone_id='m', role='builder', kind='work',
                         asked={'model': 'claude-opus-5-5', 'resolved': 'codex'},
                         ran={'adapter': 'codex-code', 'model': None, 'model_confirmed': False},
                         why="Claude Opus 5.5 can't run here: your account doesn't offer it in Claude Code",
                         started=time.time() - 60)
        last = self.rows()['builder']['last_run']
        self.assertTrue(last['fell_back'])
        self.assertEqual((last['asked_label'], last['ran_label'], last['confirmed']), ('Claude Opus 5.5', 'Codex', False))
        self.assertIn("can't run here", last['why'])
        # A newer run on the chosen model replaces it: no fall-back to report.
        staff.start_call(self.store, job_id='j2', milestone_id='m', role='builder', kind='work',
                         asked={'model': 'claude-opus-5-5', 'resolved': 'claude-opus-5-5'},
                         ran={'adapter': 'claude-code', 'model': 'claude-opus-5-5', 'model_confirmed': True})
        last = self.rows()['builder']['last_run']
        self.assertFalse(last['fell_back'])
        self.assertIsNone(last['why'])
        self.assertEqual(last['ran_label'], 'Claude Opus 5.5')

    def test_kel_reads_its_own_calls(self):
        usage.record(self.store, 'turn:1', kind='turn', adapter='claude', model='claude-sonnet',
                     result={'model_used': 'sonnet'},
                     extra={'role': 'kel', 'asked_model': 'gpt-6-luna', 'why': "ChatGPT Luna can't run here"})
        last = self.rows()['kel']['last_run']
        self.assertEqual((last['asked_label'], last['ran_label'], last['fell_back']), ('ChatGPT Luna', 'Claude Sonnet', True))


if __name__ == '__main__':
    unittest.main()
