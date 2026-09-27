"""D-64 — Full access by default: Kel acts without asking, and everything is still recorded.

The Ask first path is pinned by the V1.5/V1.6/V2 suites (they set mode 'ask'); this file pins the
default: no prompt, the grant recorded (approval rows with actor `full-access`, granted boundary
requests, guardrail decisions, Activity lines), a person's explicit "no" still standing, and the
constitution rules — Kel's own app/Data root and credential folders — refused in every mode.
"""
import contextlib
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kel import authority, network_policy  # noqa: E402
from kel.activity import sentence_for, timeline  # noqa: E402
from kel.authorize import Authorizer, decisions  # noqa: E402
from kel.autonomy import Autonomy  # noqa: E402
from kel.coding import CodingAdapter, compile_coding, git  # noqa: E402
from kel.connections import Connections  # noqa: E402
from kel.context import Context  # noqa: E402
from kel.core import PolicyError, Store  # noqa: E402
from kel.service import Service  # noqa: E402
from test_v2_connections import LocalService  # noqa: E402


def make_project(base, name):
    root = base / name
    root.mkdir(parents=True)
    git(root, 'init')
    (root / 'app.txt').write_text('old')
    git(root, 'add', '-A')
    git(root, '-c', 'user.name=Kel', '-c', 'user.email=kel@localhost', 'commit', '-m', 'base')
    return root


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.base = Path(self.tmp.name)
        self.store = Store(self.base / 'data')
        Context(self.store)  # projects/conversations, as the service creates them

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass


class ModeTests(Base):
    def test_a_fresh_store_is_full_access_and_the_migration_is_recorded(self):
        self.assertEqual(authority.mode(self.store), 'full')
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT name FROM schema_migrations WHERE version=34').fetchone()
        self.assertEqual(row['name'], 'v2-full-access')
        info = authority.describe(self.store)
        self.assertEqual((info['mode'], info['authority_mode'], info['label'], info['default']),
                         ('full', 'full', 'Full access', 'full'))
        self.assertEqual([m['mode'] for m in info['modes']], ['full', 'ask'])

    def test_an_existing_install_gets_full_access_once_and_a_later_choice_is_kept(self):
        authority.ensure_schema(self.store)
        with self.store.transaction() as db:  # an install from before D-64
            db.execute('DROP TABLE authority_prefs')
            db.execute('DELETE FROM schema_migrations WHERE version=34')
        self.assertTrue(authority.ensure_schema(self.store))
        self.assertEqual(authority.mode(self.store), 'full')
        authority.set_mode(self.store, 'ask')
        with self.store.transaction() as db:
            db.execute('DELETE FROM schema_migrations WHERE version=34')
        authority.ensure_schema(self.store)  # re-running the migration never overrides a choice
        self.assertEqual(authority.mode(self.store), 'ask')

    def test_only_the_person_changes_the_mode_and_the_switch_is_in_activity(self):
        with self.assertRaises(PolicyError):
            authority.set_mode(self.store, 'ask', actor='kel')
        with self.assertRaises(PolicyError):
            authority.set_mode(self.store, 'sometimes')
        answer = authority.set_mode(self.store, 'ask')
        self.assertEqual((answer['mode'], answer['label'], answer['changed_by_you']),
                         ('ask', 'Ask first', True))
        authority.set_mode(self.store, 'ask')  # unchanged: no second line
        authority.set_mode(self.store, 'full')
        rows = [e for e in timeline(self.store)['entries'] if e['type'] == 'authority.changed']
        self.assertEqual([r['what'] for r in rows],
                         ['Full access is on: Kel acts without asking.',
                          'Ask first is on: Kel asks before it acts.'])

    def test_the_service_route_reads_and_sets_the_mode_as_the_person(self):
        with patch.dict(os.environ, {'KEL_SKIP_TELEMETRY': '1', 'KEL_REVIEWER': 'none'}):
            os.environ.pop('ANTHROPIC_API_KEY', None)
            service = Service(self.base / 'svc')
        service.stop.set()
        self.addCleanup(service.shutdown)
        self.assertEqual(service.action('/api/autonomy', {'action': 'mode'})['mode'], 'full')
        self.assertEqual(service.action('/api/autonomy', {'action': 'set_mode', 'mode': 'ask'})['mode'],
                         'ask')
        self.assertEqual(authority.mode(service.store), 'ask')
        with self.assertRaises(PolicyError):  # a payload identity is never accepted
            service.action('/api/autonomy', {'action': 'set_mode', 'mode': 'full', 'actor': 'kel'})
        self.assertEqual(authority.mode(service.store), 'ask')


class BoundaryTests(Base):
    def setUp(self):
        super().setUp()
        self.project = make_project(self.base, 'proj')
        self.other = make_project(self.base, 'other')
        self.job = self.store.create(compile_coding('Change app.txt.', self.project,
                                                    ['python', '-m', 'unittest']))
        self.lease_id = Autonomy(self.store).latest_lease(self.job)['lease_id']
        self.authz = Authorizer(self.store)
        self.run = self.store.claim(self.job, 'code', provider='codex-code')

    def intent(self, **over):
        base = {'actor': 'worker', 'worker': self.run['id'], 'job': self.job, 'milestone': 'code',
                'action_kind': 'repo', 'tool': 'git', 'target': str(self.other)}
        base.update(over)
        return base

    def test_outside_the_project_goes_ahead_without_asking_and_is_recorded(self):
        decision = self.authz.decide(self.intent())
        self.assertEqual((decision['outcome'], decision['rule']), ('ALLOW', 'full-access'))
        requests = Autonomy(self.store).requests(self.lease_id)
        self.assertEqual([(r['status'], r['grant_kind'], r['actor']) for r in requests],
                         [('GRANTED', 'project', 'full-access')])
        self.assertNotEqual(self.store.get(self.job)['state'], 'AWAITING_USER')
        self.assertTrue(any(row['decision'] == 'ALLOW' and row['rule'] == 'full-access'
                            for row in decisions(self.store, job_id=self.job)))
        whats = [e['what'] for e in timeline(self.store)['entries']
                 if e['type'] == 'authorization.auto_granted']
        self.assertEqual(whats, ['Full access: Kel went ahead to work in another repository.'])
        # The grant is reused: a second step is allowed by the lease, with no second request.
        self.assertEqual(self.authz.decide(self.intent())['outcome'], 'ALLOW')
        self.assertEqual(len(Autonomy(self.store).requests(self.lease_id)), 1)

    def test_a_pending_ask_is_settled_instead_of_asked_again(self):
        authority.set_mode(self.store, 'ask')
        asked = self.authz.decide(self.intent())
        self.assertEqual(asked['outcome'], 'REQUIRES_BOUNDARY_EXPANSION')
        authority.set_mode(self.store, 'full')
        decision = self.authz.decide(self.intent())
        self.assertEqual(decision['outcome'], 'ALLOW')
        self.assertEqual(decision['boundary_request_id'], asked['boundary_request_id'])
        self.assertEqual([r['status'] for r in Autonomy(self.store).requests(self.lease_id)],
                         ['GRANTED'])

    def test_a_persons_earlier_no_still_stands(self):
        authority.set_mode(self.store, 'ask')
        asked = self.authz.decide(self.intent())
        Autonomy(self.store).resolve_expansion(asked['boundary_request_id'], allow=False)
        authority.set_mode(self.store, 'full')
        decision = self.authz.decide(self.intent())
        self.assertEqual((decision['outcome'], decision['rule']), ('DENY', 'boundary-denied'))

    def test_kels_own_data_is_refused_in_every_mode(self):
        own = self.store.root / 'repositories'
        own.mkdir(exist_ok=True)
        for mode in ('full', 'ask'):
            authority.set_mode(self.store, mode)
            decision = self.authz.decide(self.intent(target=str(own)))
            self.assertEqual((decision['outcome'], decision['rule']), ('DENY', 'protected-path'), mode)
        self.assertEqual(Autonomy(self.store).requests(self.lease_id), [])

    def test_the_whole_installed_data_tree_and_protected_app_folders_are_refused(self):
        data = self.base / 'Data'
        for name in ('engine', 'store', 'host'):
            (data / name).mkdir(parents=True)
        store = Store(data / 'engine')
        app = self.base / 'App'
        app.mkdir()
        job = store.create(compile_coding('Change app.txt.', self.project, ['python', '-m', 'unittest']))
        run = store.claim(job, 'code', provider='codex-code')
        authz = Authorizer(store)
        with patch.dict(os.environ, {'KEL_PROTECTED_PATHS': str(app)}):
            for target in (data / 'store', data / 'host' / 'config', data, app / 'resources'):
                decision = authz.decide({'actor': 'worker', 'worker': run['id'], 'job': job,
                                         'milestone': 'code', 'action_kind': 'write',
                                         'target': str(target)})
                self.assertEqual((decision['outcome'], decision['rule']),
                                 ('DENY', 'protected-path'), str(target))
            inside = authz.decide({'actor': 'worker', 'worker': run['id'], 'job': job,
                                   'milestone': 'code', 'action_kind': 'write',
                                   'target': str(self.project / 'app.txt')})
            self.assertEqual(inside['outcome'], 'ALLOW')


class StepApprovalTests(Base):
    def setUp(self):
        super().setUp()
        CodingAdapter(self.store)
        self.project = make_project(self.base, 'proj')
        self.job = self.store.create(compile_coding('Change app.txt.', self.project,
                                                    ['python', '-m', 'unittest']))
        self.run = self.store.claim(self.job, 'code', provider='codex-code')
        self.workspace = self.store.root / 'repositories' / self.job
        self.workspace.mkdir(parents=True)
        with self.store.transaction() as db:
            db.execute('INSERT INTO code_workspaces VALUES(?,?,?,?)',
                       (self.job, str(self.workspace), 'base', '{}'))

    def ask(self, command):
        result = {}
        thread = threading.Thread(target=lambda: result.setdefault('ok', CodingAdapter(self.store).approval(
            self.run, 'item/commandExecution/requestApproval',
            {'command': command, 'cwd': str(self.workspace)}, threading.Event())))
        thread.start()
        thread.join(5)
        self.assertFalse(thread.is_alive(), 'Full access must not wait for a person')
        return result['ok']

    def rows(self):
        with contextlib.closing(self.store.connect()) as db:
            return [dict(r) for r in db.execute('SELECT status, actor FROM approvals WHERE job_id=?',
                                                (self.job,))]

    def test_a_command_runs_without_a_prompt_and_is_recorded(self):
        self.assertTrue(self.ask('npm test'))
        self.assertEqual(self.rows(), [{'status': 'APPROVED', 'actor': 'full-access'}])
        with contextlib.closing(self.store.connect()) as db:
            run_state = db.execute('SELECT state FROM runs WHERE id=?', (self.run['id'],)).fetchone()[0]
            announced = db.execute('SELECT COUNT(*) FROM approval_announcements').fetchone()[0] \
                if db.execute("SELECT 1 FROM sqlite_master WHERE name='approval_announcements'").fetchone() else 0
        self.assertEqual(run_state, 'RUNNING')
        self.assertEqual(announced, 0, 'no approval card is posted in the chat')
        whats = [e['what'] for e in timeline(self.store)['entries'] if e['type'] == 'approval.auto_granted']
        self.assertEqual(whats, ['Full access: Kel went ahead to run npm test.'])

    def test_a_command_aimed_at_kels_own_data_is_refused_and_recorded(self):
        self.assertFalse(self.ask('del /s /q "%s"' % (self.store.root / 'kel.sqlite3')))
        self.assertEqual(self.rows(), [{'status': 'DENIED', 'actor': 'full-access'}])
        refused = [e for e in timeline(self.store)['entries'] if e['type'] == 'approval.refused']
        self.assertEqual(len(refused), 1)
        self.assertIn("Kel's own app or data folder", refused[0]['what'])

    def test_ask_first_still_waits_for_the_person(self):
        authority.set_mode(self.store, 'ask')
        result = {}
        thread = threading.Thread(target=lambda: result.setdefault('ok', CodingAdapter(self.store).approval(
            self.run, 'item/commandExecution/requestApproval',
            {'command': 'npm test', 'cwd': str(self.workspace)}, threading.Event())))
        thread.start()
        deadline = time.time() + 5
        while time.time() < deadline and not any(r['status'] == 'PENDING' for r in self.rows()):
            time.sleep(.05)
        self.assertEqual(self.rows(), [{'status': 'PENDING', 'actor': None}])
        with self.store.transaction() as db:  # settle it so the thread ends
            db.execute("UPDATE approvals SET status='DENIED' WHERE job_id=?", (self.job,))
        thread.join(5)
        self.assertFalse(result['ok'])


class NetworkTests(Base):
    def test_an_approved_scope_reaches_a_new_host_without_asking_and_records_it(self):
        network_policy.set_mode(self.store, 'approved', domains=['github.com'])
        decision = network_policy.decide(self.store, 'example.org')
        self.assertTrue(decision['allowed'])
        self.assertEqual(network_policy.requests(self.store)['requests'], [])
        event = network_policy.history(self.store)['events'][0]
        self.assertEqual((event['host'], event['decision']), ('example.org', 'allowed'))
        self.assertIn('full access', event['reason'])
        # The person's approved list is never changed on their behalf.
        self.assertEqual(network_policy.get_policy(self.store)['default']['domains'], ['github.com'])

    def test_no_internet_is_the_persons_block_and_still_holds(self):
        network_policy.set_mode(self.store, 'none')
        self.assertFalse(network_policy.decide(self.store, 'example.org')['allowed'])


class ConnectionWriteTests(Base):
    def test_a_change_in_a_connected_service_goes_ahead_and_is_in_the_access_history(self):
        service = LocalService()
        self.addCleanup(service.stop)
        connections = Connections(self.store, attempts=1, sleep=lambda _s: None)
        connections.save('Local Service', base_url=service.base)
        row = {'id': 'local-change', 'service': '', 'name': 'Change something', 'description': 'd',
               'method': 'POST', 'path': '/something', 'params': (), 'returns': 'r',
               'mutating': True, 'source': 'documented'}
        with patch('kel.connection_actions.ACTIONS', (row,)):
            done = connections.run('local-service', 'local-change')
            self.assertEqual(done['state'], 'ok')
            self.assertEqual(service.seen[0]['method'], 'POST')
            authority.set_mode(self.store, 'ask')
            with self.assertRaises(PolicyError):
                connections.run('local-service', 'local-change')
        self.assertEqual(len(service.seen), 1)
        self.assertTrue(connections.events('local-service'))


class SentenceTests(unittest.TestCase):
    def test_activity_lines_are_plain(self):
        self.assertEqual(sentence_for('approval.auto_granted', {'detail': {'summary': 'apply these file changes'}}),
                         'Full access: Kel went ahead to apply these file changes.')
        self.assertEqual(sentence_for('authority.changed', {'detail': {'mode': 'ask'}}),
                         'Ask first is on: Kel asks before it acts.')


if __name__ == '__main__':
    unittest.main()
