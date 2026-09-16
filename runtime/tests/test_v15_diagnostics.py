"""V1.5 G8 / WS22: the diagnostics snapshot carries the shipped authorization truth.

The snapshot is the read-only surface a user or a release audit consults. It must report the
active policy version, a decision roll-up with a bounded recent tail, live lease states, and the
applied schema history — on a fresh database, and without ever requiring credential values.
"""
import json
import tempfile
import unittest
from pathlib import Path

from kel.authorize import POLICY_VERSION, Authorizer
from kel.autonomy import Autonomy
from kel.coding import compile_coding, git
from kel.core import Store
from kel.diagnostics import Diagnostics


def make_project(base, name):
    root = base / name
    root.mkdir(parents=True)
    git(root, 'init')
    (root / 'app.txt').write_text('old')
    git(root, 'add', '-A')
    git(root, '-c', 'user.name=Kel', '-c', 'user.email=kel@localhost', 'commit', '-m', 'base')
    return root


class DiagnosticsSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.store = Store(base / 'data')
        self.project = make_project(base, 'proj')
        self.other = make_project(base, 'other')
        self.job = self.store.create(compile_coding('Touch app.txt.', self.project,
                                                    ['python', '-m', 'unittest']))
        self.authz = Authorizer(self.store)
        self.diag = Diagnostics(self.store, '1.5.0-test')

    def intent(self, **overrides):
        base = {'actor': 'kel', 'job': self.job, 'milestone': 'code',
                'action_kind': 'write', 'target': str(self.project / 'app.txt')}
        base.update(overrides)
        return base

    def test_snapshot_reports_policy_rollup(self):
        before = self.diag.snapshot()['policy']['by_decision'].get('ALLOW', 0)
        allowed = self.authz.decide(self.intent())
        denied = self.authz.decide(self.intent(target=str(self.other / 'app.txt')))
        self.assertEqual(allowed['outcome'], 'ALLOW')
        self.assertIn(denied['outcome'], ('DENY', 'REQUIRES_BOUNDARY_EXPANSION'))
        policy = self.diag.snapshot()['policy']
        self.assertEqual(policy['version'], POLICY_VERSION)
        self.assertEqual(policy['by_decision'].get('ALLOW'), before + 1)
        self.assertGreaterEqual(sum(policy['by_decision'].values()), before + 2)
        self.assertEqual(policy['recent'][0]['job_id'], self.job)
        self.assertEqual(policy['recent'][0]['policy_version'], POLICY_VERSION)
        self.assertEqual(policy['recent'][0]['decision'], denied['outcome'])

    def test_snapshot_reports_lease_states(self):
        lease = Autonomy(self.store).latest_lease(self.job)
        self.assertIsNotNone(lease)
        before = self.diag.snapshot()['leases']
        self.assertGreaterEqual(before.get('ACTIVE', 0), 1)
        Autonomy(self.store).revoke(lease['lease_id'], 'diagnostics probe')
        after = self.diag.snapshot()['leases']
        self.assertGreaterEqual(after.get('REVOKED', 0), 1)
        self.assertEqual(after.get('ACTIVE', 0), before.get('ACTIVE', 0) - 1)

    def test_snapshot_reports_migrations_and_is_serializable(self):
        snapshot = self.diag.snapshot()
        names = {m['name'] for m in snapshot['migrations']}
        self.assertIn('v15-authorization', names)
        self.assertIn('v14-diagnostics', names)
        json.dumps(snapshot)  # the export/report paths JSON-encode this payload


if __name__ == '__main__':
    unittest.main()
