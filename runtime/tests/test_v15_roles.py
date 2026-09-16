"""V1.5 G3: role snapshots attached to every run, enforced at the coding effect point.

Kel attaches a frozen role snapshot at claim time (one assignment per milestone). Enforcement
reads the frozen copy, so later role edits never rewrite a run's policy; ad-hoc intents that pass
a role directly still resolve live. Roles only narrow — lease and guardrails always apply — so
attachment failures never block work.
"""
import contextlib
import json
import tempfile
import unittest
from pathlib import Path

from kel.authorize import Authorizer, role_for
from kel.coding import CodingAdapter, compile_coding, git
from kel.core import Store
from kel.engine import Engine, compile_document
from kel.native import FixtureAdapter
from kel.team import Team


def make_project(base, name):
    root = base / name
    root.mkdir(parents=True)
    git(root, 'init')
    (root / 'app.txt').write_text('old')
    git(root, 'add', '-A')
    git(root, '-c', 'user.name=Kel', '-c', 'user.email=kel@localhost', 'commit', '-m', 'base')
    return root


class CodingProbe:
    capabilities = {'text', 'repository_edit'}

    def execute(self, prompt, run_id=None, session_id=None, cancel=None):
        return {'outcome': 'FAILED', 'error': 'probe'}


class RoleAttachmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.base = base
        self.store = Store(base / 'data')
        self.project = make_project(base, 'proj')
        self.job = self.store.create(compile_coding('Change app.txt.', self.project,
                                                    ['python', '-m', 'unittest']))

    def tearDown(self):
        self.tmp.cleanup()

    def run_engine_once(self, adapters=None):
        engine = Engine(self.store, adapters or {'codex-code': CodingProbe()})
        try:
            engine.tick()
        finally:
            engine.close()

    def test_engine_attaches_a_frozen_role_snapshot_to_every_run(self):
        self.run_engine_once()
        with contextlib.closing(self.store.connect()) as db:
            rows = [dict(r) for r in db.execute(
                'SELECT template_id, run_id, snapshot FROM team_assignments')]
            runs = [r['id'] for r in db.execute('SELECT id FROM runs')]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['template_id'], 'implementation-engineer')
        self.assertEqual(rows[0]['run_id'], runs[0])
        snapshot = json.loads(rows[0]['snapshot'])
        self.assertIn('tool_policy', snapshot)
        self.assertIn('git', snapshot['tool_policy'].get('allow', []))

    def test_frozen_snapshot_governs_even_after_a_role_edit(self):
        self.run_engine_once()
        team = Team(self.store)
        team.edit_role('implementation-engineer',
                       {'tool_policy': {'allow': ['read'], 'deny': ['git', 'run_tests', 'write']}})
        info = role_for(self.store, self.job, 'code')
        self.assertEqual(info['template_id'], 'implementation-engineer')
        decision = Authorizer(self.store).decide({
            'actor': 'kel', 'job': self.job, 'milestone': 'code',
            'role': info['template_id'], 'role_tool_policy': info['tool_policy'],
            'action_kind': 'repo', 'tool': 'git', 'target': str(self.project)})
        self.assertEqual(decision['outcome'], 'ALLOW',
                         'the frozen snapshot governs; the live edit does not rewrite it')

    def test_a_strict_snapshot_blocks_the_coding_dispatcher(self):
        team = Team(self.store)
        team.seed_defaults()
        team.define_role('strict-impl', 'Strict Impl', 'Engineering',
                         {'goal': 'Inspect only.', 'outputs': 'notes', 'quality_bar': 'exact',
                          'tool_policy': {'allow': ['read'],
                                          'deny': ['git', 'run_tests', 'write']},
                          'budget': 4})
        run = self.store.claim(self.job, 'code', provider='codex-code')
        team.create_assignment(self.job, 'code', 'strict-impl', run_id=run['id'],
                               provider='codex-code')
        result = CodingAdapter(self.store).execute('Change app.txt.', run_id=run['id'],
                                                   session_id=None, cancel=None)
        self.assertEqual(result['outcome'], 'BLOCKED')
        self.assertIn('role', (result['error'] or '').lower())
        with contextlib.closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM code_workspaces').fetchone()[0], 0,
                             'a denied role blocks before any workspace is created')

    def test_retries_reuse_the_same_frozen_assignment(self):
        self.run_engine_once()
        with contextlib.closing(self.store.connect()) as db:
            first = [r['assignment_id'] for r in db.execute(
                'SELECT assignment_id FROM team_assignments')]
        with self.store.transaction() as db:
            job = self.store._get(db, self.job)
            job['milestones']['code'].update(state='NEEDS_REPAIR')
            job.update(state='READY')
            self.store._save(db, job, 'test.retry')
        self.run_engine_once()
        with contextlib.closing(self.store.connect()) as db:
            rows = [r['assignment_id'] for r in db.execute(
                'SELECT assignment_id FROM team_assignments')]
        self.assertEqual(rows, first, 'one frozen assignment per milestone, not one per attempt')

    def test_text_jobs_attach_the_documentation_role(self):
        job = self.store.create(compile_document('Write a short plan for the weekend.'))
        self.run_engine_once({'fixture': FixtureAdapter()})
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT template_id FROM team_assignments WHERE job_id=?',
                             (job,)).fetchone()
        self.assertEqual(row['template_id'], 'documentation-specialist')


if __name__ == '__main__':
    unittest.main()
