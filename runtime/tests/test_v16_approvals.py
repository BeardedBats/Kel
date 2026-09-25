"""V1.6 in-chat approvals — engine verification.

The conversation shows a decision card for anything Kel is waiting on, and resolving that card
mutates the SAME durable records the Work surfaces use:

- folder/scope decisions are `boundary_expansion_requests` (resolved through
  `Autonomy.resolve_expansion`; a grant wakes the paused job via `resume_after_grant`),
- step approvals are `approvals` rows (resolved through `Store.resolve_approval`; `remember`
  writes the same project permission cache the Work panel uses).

Chat is a view + action surface only. A second resolution is refused, a denied access is not
re-asked, an expired approval cannot be approved as current, and every announced decision is
linked to the chat message that carries it so history stays readable after a restart.
"""
import contextlib
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from kel import chat_approvals
from kel.authorize import Authorizer, block_job, resume_after_grant
from kel.autonomy import Autonomy
from kel.coding import CodingAdapter, compile_coding, git
from kel.context import Context
from kel.continuation import Continuation
from kel.core import PolicyError, Store, encode
from kel.service import Service


def make_project(base, name):
    root = base / name
    root.mkdir(parents=True)
    git(root, 'init')
    (root / 'app.txt').write_text('old')
    git(root, 'add', '-A')
    git(root, '-c', 'user.name=Kel', '-c', 'user.email=kel@localhost', 'commit', '-m', 'base')
    return root


class ApprovalBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.store = Store(self.base / 'data')
        CodingAdapter(self.store)  # schema only; owns approval_actions (Service does this too)
        Context(self.store).project('General', project_id='default')
        self.project = make_project(self.base, 'proj')
        self.other = make_project(self.base, 'other')
        self.job = self.store.create(compile_coding('Change app.txt.', self.project,
                                                    ['python', '-m', 'unittest']))
        latest = Autonomy(self.store).latest_lease(self.job)
        self.assertIsNotNone(latest)
        self.lease_id = latest['lease_id']
        self.authz = Authorizer(self.store)

    def claim_run(self):
        return self.store.claim(self.job, 'code', provider='codex-code')

    def worker_intent(self, run, **overrides):
        base = {'actor': 'worker', 'worker': run['id'], 'job': self.job, 'milestone': 'code',
                'action_kind': 'repo', 'tool': 'git', 'target': str(self.project)}
        base.update(overrides)
        return base

    def kel_intent(self, **overrides):
        base = {'actor': 'kel', 'job': self.job, 'milestone': 'code', 'action_kind': 'write',
                'target': str(self.project / 'app.txt')}
        base.update(overrides)
        return base

    def ask_for_access(self):
        """The real sequence: a worker reaches outside its leased repository."""
        run = self.claim_run()
        decision = self.authz.decide(self.worker_intent(run, target=str(self.other)))
        self.assertEqual(decision['outcome'], 'REQUIRES_BOUNDARY_EXPANSION')
        with self.store.transaction() as db:
            db.execute("UPDATE runs SET state='RESULT_RECORDED' WHERE id=?", (run['id'],))
            job_row = self.store._get(db, self.job)
            job_row['milestones']['code'].update(state='NEEDS_REPAIR')
            self.store._save(db, job_row, 'test.worker-blocked')
        self.assertTrue(block_job(self.store, self.job, 'code', decision))
        return run, decision['boundary_request_id']

    def ask_for_access_for(self, job):
        """The same real sequence as `ask_for_access`, for a job in any conversation."""
        run = self.store.claim(job, 'code', provider='codex-code')
        decision = self.authz.decide(self.worker_intent(run, job=job, target=str(self.other)))
        self.assertEqual(decision['outcome'], 'REQUIRES_BOUNDARY_EXPANSION')
        with self.store.transaction() as db:
            db.execute("UPDATE runs SET state='RESULT_RECORDED' WHERE id=?", (run['id'],))
            job_row = self.store._get(db, job)
            job_row['milestones']['code'].update(state='NEEDS_REPAIR')
            self.store._save(db, job_row, 'test.worker-blocked')
        self.assertTrue(block_job(self.store, job, 'code', decision))
        return run, decision['boundary_request_id']

    def second_job(self):
        """A second job in the same conversation (one job can only wait on one ask at a time)."""
        return self.store.create(compile_coding('Second task.', self.project,
                                                ['python', '-m', 'unittest']),
                                 conversation='main')

    def ask_for_step(self, command='npm test', job=None):
        """A real run approval through the coding adapter's permission callback."""
        job = job or self.job
        run = self.store.claim(job, 'code', provider='codex-code')
        adapter = CodingAdapter(self.store)
        result = {}
        thread = threading.Thread(
            target=lambda: result.setdefault(
                'ok', adapter.approval(run, 'item/commandExecution/requestApproval',
                                       {'command': command, 'cwd': str(self.project)},
                                       threading.Event())))
        thread.start()
        deadline = time.time() + 10
        while time.time() < deadline:
            with contextlib.closing(self.store.connect()) as db:
                row = db.execute("SELECT id FROM approvals WHERE job_id=? AND status='PENDING'",
                                 (job,)).fetchone()
                announced = row and db.execute(
                    "SELECT 1 FROM approval_announcements WHERE kind='action' AND ref_id=?",
                    (row['id'],)).fetchone()
            if announced:
                return run, row['id'], thread, result
            time.sleep(.05)
        raise AssertionError('the adapter did not request (and announce) an approval')


class ChatApprovalViewTests(ApprovalBase):
    def test_pending_access_item_is_plain_and_scoped_to_the_conversation(self):
        _, request_id = self.ask_for_access()
        items = chat_approvals.items(self.store, 'main')
        self.assertEqual([i['id'] for i in items], [request_id])
        item = items[0]
        self.assertEqual((item['kind'], item['state']), ('access', 'pending'))
        self.assertEqual(item['job_id'], self.job)
        self.assertIn('access', item['title'].lower())
        self.assertEqual(item['target'], str(self.other))
        self.assertTrue(item['what'] and item['why'])
        self.assertTrue(item['message_seq'], 'the card must be anchored to its chat message')
        # A different conversation sees nothing.
        self.assertEqual(chat_approvals.items(self.store, 'not-this-conversation'), [])

    def test_pending_step_item_uses_plain_summary(self):
        _, approval_id, thread, result = self.ask_for_step()
        with self.store.transaction() as db:
            db.execute("INSERT OR IGNORE INTO conversations(id,project_id,title,created) VALUES(?,?,?,?)",
                       ('main', 'default', 'Website Redesign', time.time()))
            db.execute("UPDATE conversations SET title=? WHERE id=?", ('Website Redesign', 'main'))
        items = chat_approvals.items(self.store, 'main')
        self.assertEqual([i['id'] for i in items], [approval_id])
        item = items[0]
        self.assertEqual((item['kind'], item['state']), ('action', 'pending'))
        self.assertIn('npm test', item['summary'])
        self.assertEqual(item['target'], 'npm test')
        self.assertEqual(item['context_title'], 'Website Redesign')
        self.assertTrue(item['repeatable'])
        self.assertGreater(item['seconds_left'], 0)
        self.assertTrue(item['message_seq'])
        # Clean up the polling thread.
        chat_approvals.resolve(self.store, 'action', approval_id, False)
        thread.join(timeout=5)
        self.assertFalse(result.get('ok'))

    def test_unrepeatable_request_has_no_reusable_grant(self):
        run = self.claim_run()
        adapter = CodingAdapter(self.store)
        result = {}
        thread = threading.Thread(
            target=lambda: result.setdefault(
                'ok', adapter.approval(run, 'item/fileChange/requestApproval',
                                       {'itemId': 'patch-1', 'cwd': str(self.project)},
                                       threading.Event())))
        thread.start()
        deadline = time.time() + 10
        approval_id = None
        while time.time() < deadline and not approval_id:
            with contextlib.closing(self.store.connect()) as db:
                row = db.execute("SELECT id FROM approvals WHERE job_id=? AND status='PENDING'",
                                 (self.job,)).fetchone()
            approval_id = row and row['id']
            time.sleep(.05)
        self.assertTrue(approval_id, 'missing patch details cannot form a reusable grant')
        item = chat_approvals.items(self.store, 'main')[0]
        self.assertFalse(item['repeatable'])
        chat_approvals.resolve(self.store, 'action', approval_id, False)
        thread.join(timeout=5)

    def test_continuation_conversation_sees_the_same_item(self):
        _, request_id = self.ask_for_access()
        follow = Context(self.store).conversation(project_id='default', title='Follow-up work')
        Continuation(self.store).attach(self.job, follow, kind='continuation',
                                        reason='test hand-off')
        items = chat_approvals.items(self.store, follow)
        self.assertEqual([i['id'] for i in items], [request_id])
        # ... and it is still the same single durable record.
        self.assertEqual(len(Autonomy(self.store).requests(self.lease_id)), 1)

    def test_user_copy_contains_no_machinery(self):
        _, request_id = self.ask_for_access()
        _, approval_id, thread, _ = self.ask_for_step(job=self.second_job())
        items = chat_approvals.items(self.store, 'main')
        self.assertEqual({i['kind'] for i in items}, {'access', 'action'})
        banned = ('lease', 'scope', 'digest', 'runtime', 'worker', 'request_id', 'approval_id')
        for item in items:
            copy = ' '.join(str(item.get(f) or '') for f in
                            ('title', 'what', 'why', 'benefit', 'fallback', 'summary')).lower()
            for word in banned:
                self.assertNotIn(word, copy, word)
            self.assertNotIn(request_id, copy)
            self.assertNotIn(approval_id, copy)
        chat_approvals.resolve(self.store, 'action', approval_id, False)
        thread.join(timeout=5)


class ChatApprovalResolutionTests(ApprovalBase):
    def test_allow_once_is_durable_single_and_wakes_the_job(self):
        _, request_id = self.ask_for_access()
        out = chat_approvals.resolve(self.store, 'access', request_id, True, grant_kind='once')
        self.assertEqual(out['state'], 'allowed_once')
        request = [r for r in Autonomy(self.store).requests(self.lease_id)][0]
        self.assertEqual((request['status'], request['grant_kind']), ('GRANTED', 'once'))
        job = self.store.get(self.job)
        self.assertEqual(job['state'], 'READY')  # the same wake-up the Autonomy page triggers
        with contextlib.closing(self.store.connect()) as db:
            texts = [r['text'] for r in db.execute(
                "SELECT text FROM messages WHERE job_id=? ORDER BY seq", (self.job,))]
        self.assertTrue(any('continuing' in t.lower() for t in texts))
        # A second resolution is refused and changes nothing.
        with self.assertRaises(PolicyError):
            chat_approvals.resolve(self.store, 'access', request_id, True, grant_kind='once')
        request = [r for r in Autonomy(self.store).requests(self.lease_id)][0]
        self.assertEqual(request['status'], 'GRANTED')

    def test_allow_once_grant_cannot_be_spent_twice(self):
        _, request_id = self.ask_for_access()
        chat_approvals.resolve(self.store, 'access', request_id, True, grant_kind='once')
        run = self.claim_run()
        first = self.authz.decide(self.worker_intent(run, target=str(self.other)))
        self.assertEqual(first['outcome'], 'ALLOW')
        # A spent one-time grant fails closed; it is never silently re-allowed.
        second = self.authz.decide(self.worker_intent(run, target=str(self.other)))
        self.assertEqual((second['outcome'], second['rule']), ('DENY', 'grant-used'))

    def test_allow_project_is_reusable_and_not_asked_again(self):
        _, request_id = self.ask_for_access()
        out = chat_approvals.resolve(self.store, 'access', request_id, True, grant_kind='project')
        self.assertEqual(out['state'], 'allowed_project')
        run = self.claim_run()
        first = self.authz.decide(self.worker_intent(run, target=str(self.other)))
        second = self.authz.decide(self.worker_intent(run, target=str(self.other)))
        self.assertEqual((first['outcome'], second['outcome']), ('ALLOW', 'ALLOW'))

    def test_deny_resolves_durably_and_is_not_asked_again(self):
        _, request_id = self.ask_for_access()
        out = chat_approvals.resolve(self.store, 'access', request_id, False)
        self.assertEqual(out['state'], 'denied')
        item = chat_approvals.items(self.store, 'main')[0]
        self.assertEqual(item['state'], 'denied')
        # The next identical attempt is refused outright - never a second ask.
        again = self.authz.decide(self.kel_intent(action_kind='repo', tool='git',
                                                  target=str(self.other)))
        self.assertEqual((again['outcome'], again['rule']), ('DENY', 'boundary-denied'))
        self.assertEqual(len(Autonomy(self.store).requests(self.lease_id)), 1)
        # The consequence is explained once, in plain words, inside the conversation.
        with contextlib.closing(self.store.connect()) as db:
            denied_texts = [r['text'] for r in db.execute(
                'SELECT text FROM messages WHERE job_id=? ORDER BY seq', (self.job,))
                if 'You denied this request' in r['text']]
        self.assertEqual(len(denied_texts), 1)
        self.assertIn('nothing was changed', denied_texts[0])
        # ... and the sentence never repeats, from any surface.
        self.assertIsNone(chat_approvals.announce_denial(self.store, request_id))

    def test_approve_step_is_durable_and_completes_the_wait(self):
        _, approval_id, thread, result = self.ask_for_step()
        out = chat_approvals.resolve(self.store, 'action', approval_id, True)
        self.assertEqual(out['state'], 'approved')
        thread.join(timeout=5)
        self.assertTrue(result.get('ok'), 'the waiting adapter must see the approval')
        with contextlib.closing(self.store.connect()) as db:
            run = db.execute("SELECT state FROM runs WHERE job_id=?", (self.job,)).fetchone()
        self.assertEqual(run['state'], 'RUNNING')
        with self.assertRaises(PolicyError):
            chat_approvals.resolve(self.store, 'action', approval_id, True)

    def test_approve_with_remember_writes_the_project_permission(self):
        _, approval_id, thread, _ = self.ask_for_step()
        action = {'method': 'item/commandExecution/requestApproval', 'workspace': str(self.project),
                  'command': 'npm test', 'permissions': None, 'grantRoot': None, 'network': None}
        chat_approvals.resolve(self.store, 'action', approval_id, True, remember=True)
        self.assertTrue(Context(self.store).allowed('default', action))
        thread.join(timeout=5)

    def test_deny_step_cancels_the_run(self):
        _, approval_id, thread, result = self.ask_for_step()
        out = chat_approvals.resolve(self.store, 'action', approval_id, False)
        self.assertEqual(out['state'], 'denied')
        thread.join(timeout=5)
        self.assertFalse(result.get('ok'))
        with contextlib.closing(self.store.connect()) as db:
            run = db.execute("SELECT state FROM runs WHERE job_id=?", (self.job,)).fetchone()
        self.assertEqual(run['state'], 'CANCEL_REQUESTED')

    def test_expired_approval_cannot_be_approved_as_current(self):
        run = self.claim_run()
        action = {'kind': 'command', 'command': 'npm test'}
        approval_id = self.store.request_approval(self.job, run['id'], action, seconds=-1)
        with self.store.transaction() as db:
            db.execute('INSERT INTO approval_actions VALUES(?,?)', (approval_id, encode(action)))
        chat_approvals.announce_approval(self.store, approval_id, self.store.get(self.job), action)
        item = [i for i in chat_approvals.items(self.store, 'main') if i['kind'] == 'action'][0]
        self.assertEqual(item['state'], 'expired')
        self.assertEqual(chat_approvals.resolve(self.store, 'action', approval_id, True)['state'],
                         'expired')
        # The durable row also settled as expired - not approved.
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT status FROM approvals WHERE id=?', (approval_id,)).fetchone()
        self.assertEqual(row['status'], 'EXPIRED')

    def test_cancelled_approval_reads_as_no_longer_active(self):
        run = self.claim_run()
        action = {'kind': 'command', 'command': 'npm test'}
        approval_id = self.store.request_approval(self.job, run['id'], action, seconds=300)
        with self.store.transaction() as db:
            db.execute('INSERT INTO approval_actions VALUES(?,?)', (approval_id, encode(action)))
            db.execute("UPDATE approvals SET status='CANCELLED' WHERE id=?", (approval_id,))
        item = [i for i in chat_approvals.items(self.store, 'main') if i['kind'] == 'action'][0]
        self.assertEqual(item['state'], 'expired')


class ChatApprovalAnnouncementTests(ApprovalBase):
    def test_access_announcement_links_the_pause_message(self):
        _, request_id = self.ask_for_access()
        with contextlib.closing(self.store.connect()) as db:
            ann = db.execute("SELECT * FROM approval_announcements WHERE kind='access' AND ref_id=?",
                             (request_id,)).fetchone()
            message = db.execute('SELECT * FROM messages WHERE seq=?',
                                 (ann['message_seq'],)).fetchone()
        self.assertEqual(message['job_id'], self.job)
        self.assertIn('decide right in this chat', message['text'])
        self.assertNotIn(request_id, message['text'])
        item = chat_approvals.items(self.store, 'main')[0]
        self.assertEqual(item['message_seq'], ann['message_seq'])
        self.assertAlmostEqual(item['message_at'], message['at'], places=3)

    def test_step_announcement_is_written_once_per_ask(self):
        _, approval_id, thread, _ = self.ask_for_step()
        again = chat_approvals.announce_approval(
            self.store, approval_id, self.store.get(self.job), {'kind': 'command'})
        self.assertIsNone(again, 're-announcing the same ask must not add a second message')
        with contextlib.closing(self.store.connect()) as db:
            count = db.execute("SELECT COUNT(*) AS n FROM messages WHERE job_id=? AND text LIKE "
                               "'Kel needs your OK%'", (self.job,)).fetchone()['n']
        self.assertEqual(count, 1)
        chat_approvals.resolve(self.store, 'action', approval_id, False)
        thread.join(timeout=5)


class RestartCoherenceTests(ApprovalBase):
    def test_pending_decisions_survive_a_restart_and_resolve_after(self):
        _, request_id = self.ask_for_access()
        job2 = self.second_job()
        _, approval_id, thread, result = self.ask_for_step(job=job2)
        # "Restart": everything durable is re-opened from the same database file.
        reopened = Store(self.base / 'data')
        items = chat_approvals.items(reopened, 'main')
        self.assertEqual(sorted(i['id'] for i in items), sorted([request_id, approval_id]))
        self.assertEqual({i['state'] for i in items}, {'pending'})
        chat_approvals.resolve(reopened, 'access', request_id, True, grant_kind='once')
        chat_approvals.resolve(reopened, 'action', approval_id, True)
        self.assertTrue(resume_after_grant(reopened, request_id) is False)  # already resumed once
        item = [i for i in chat_approvals.items(reopened, 'main') if i['kind'] == 'access'][0]
        self.assertEqual(item['state'], 'allowed_once')
        thread.join(timeout=5)
        self.assertTrue(result.get('ok'))


class ServiceRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('ANTHROPIC_API_KEY', None)
            os.environ['KEL_SKIP_TELEMETRY'] = '1'
            os.environ['KEL_REVIEWER'] = 'none'
            self.service = Service(self.tmp.name)
        self.addCleanup(self.service.shutdown)
        contract = {'request': 'Prepare a note', 'milestones': [
            {'id': 'code', 'objective': 'Do the thing', 'filename': 'result.md',
             'checks': [{'kind': 'min_chars', 'value': 2}], 'depends_on': []}]}
        self.job = self.service.store.create(contract, conversation='main')
        run = self.service.store.claim(self.job, 'code')
        action = {'kind': 'command', 'command': 'npm test'}
        self.action = action
        self.approval_id = self.service.store.request_approval(self.job, run['id'], action)
        with self.service.store.transaction() as db:
            db.execute('INSERT INTO approval_actions VALUES(?,?)', (self.approval_id, encode(action)))

    def test_list_and_resolve_through_the_service_route(self):
        listed = self.service._approvals_list('main')
        self.assertEqual([i['id'] for i in listed['items']], [self.approval_id])
        out = self.service.action('/api/approvals', {'kind': 'action', 'id': self.approval_id,
                                                     'allow': True})
        self.assertEqual(out['state'], 'approved')
        listed = self.service._approvals_list('main')
        self.assertEqual(listed['items'][0]['state'], 'approved')
        with self.assertRaises(PolicyError):
            self.service.action('/api/approvals', {'kind': 'action', 'id': self.approval_id,
                                                   'allow': True, 'actor': 'user'})
        with self.assertRaises(PolicyError):
            self.service.action('/api/approvals', {'action': 'take-over'})


class CrossScopeResolutionTests(ApprovalBase):
    """APR-02 / Round 2.5 APPROVAL-EXACT: the resolve path is scoped like the read path.

    The list is conversation-scoped; before this increment the resolution was not, so an id from
    another conversation could settle work the caller was not looking at.
    """

    def test_a_step_approval_cannot_be_resolved_from_another_conversation(self):
        run, approval_id, thread, result = self.ask_for_step()
        with self.assertRaises(PolicyError) as caught:
            chat_approvals.resolve(self.store, 'action', approval_id, True,
                                   conversation='somewhere-else')
        self.assertIn('another conversation', str(caught.exception))
        # Untouched by the refused attempt, and still resolvable from its own conversation.
        resolved = chat_approvals.resolve(self.store, 'action', approval_id, True,
                                          conversation='main')
        self.assertEqual(resolved['state'], 'approved')
        thread.join(timeout=5)
        self.assertTrue(result.get('ok'))

    def test_a_job_in_another_conversation_is_not_resolvable_from_main(self):
        other = self.store.create(compile_coding('Elsewhere.', self.project,
                                                 ['python', '-m', 'unittest']),
                                  conversation='elsewhere')
        run, approval_id, thread, result = self.ask_for_step(job=other)
        with self.assertRaises(PolicyError) as caught:
            chat_approvals.resolve(self.store, 'action', approval_id, True, conversation='main')
        self.assertIn('another conversation', str(caught.exception))
        resolved = chat_approvals.resolve(self.store, 'action', approval_id, True,
                                          conversation='elsewhere')
        self.assertEqual(resolved['state'], 'approved')
        thread.join(timeout=5)
        self.assertTrue(result.get('ok'))

    def test_a_boundary_grant_cannot_be_resolved_from_another_conversation(self):
        _, request_id = self.ask_for_access()
        with self.assertRaises(PolicyError) as caught:
            chat_approvals.resolve(self.store, 'access', request_id, True,
                                   conversation='somewhere-else')
        self.assertIn('another conversation', str(caught.exception))
        resolved = chat_approvals.resolve(self.store, 'access', request_id, True,
                                          conversation='main')
        self.assertEqual(resolved['state'], 'allowed_once')

    def test_an_unknown_id_is_refused_even_with_a_declared_conversation(self):
        with self.assertRaises(PolicyError) as caught:
            chat_approvals.resolve(self.store, 'action', 'apr_missing', True, conversation='main')
        self.assertIn('missing', str(caught.exception))

    def test_without_a_declared_conversation_acts_as_main(self):
        # Read-path parity (Campaign C AUD-MAJOR-001): omission acts as the `main` conversation
        # and can never reach another conversation - the refusal tests below pin that half.
        run, approval_id, thread, result = self.ask_for_step()
        resolved = chat_approvals.resolve(self.store, 'action', approval_id, True)
        self.assertEqual(resolved['state'], 'approved')
        thread.join(timeout=5)
        self.assertTrue(result.get('ok'))

    def test_no_conversation_cannot_settle_a_foreign_step_approval(self):
        other = self.store.create(compile_coding('Elsewhere.', self.project,
                                                 ['python', '-m', 'unittest']),
                                  conversation='elsewhere')
        run, approval_id, thread, result = self.ask_for_step(job=other)
        with self.assertRaises(PolicyError) as caught:
            chat_approvals.resolve(self.store, 'action', approval_id, True)
        self.assertIn('another conversation', str(caught.exception))
        resolved = chat_approvals.resolve(self.store, 'action', approval_id, True,
                                          conversation='elsewhere')
        self.assertEqual(resolved['state'], 'approved')
        thread.join(timeout=5)
        self.assertTrue(result.get('ok'))

    def test_no_conversation_cannot_settle_a_foreign_boundary_grant(self):
        other = self.store.create(compile_coding('Elsewhere.', self.project,
                                                 ['python', '-m', 'unittest']),
                                  conversation='elsewhere')
        _, request_id = self.ask_for_access_for(other)
        with self.assertRaises(PolicyError) as caught:
            chat_approvals.resolve(self.store, 'access', request_id, True)
        self.assertIn('another conversation', str(caught.exception))
        resolved = chat_approvals.resolve(self.store, 'access', request_id, True,
                                          conversation='elsewhere')
        self.assertEqual(resolved['state'], 'allowed_once')

    def test_the_service_route_refuses_omission_on_a_foreign_step_approval(self):
        other = self.store.create(compile_coding('Elsewhere.', self.project,
                                                 ['python', '-m', 'unittest']),
                                  conversation='elsewhere')
        run, approval_id, thread, result = self.ask_for_step(job=other)
        service = Service(str(self.base / 'data'))
        self.addCleanup(service.shutdown)
        with self.assertRaises(PolicyError) as caught:
            service.action('/api/approvals', {'kind': 'action', 'id': approval_id,
                                              'allow': True})
        self.assertIn('another conversation', str(caught.exception))
        out = service.action('/api/approvals', {'kind': 'action', 'id': approval_id,
                                                'allow': True, 'conversation': 'elsewhere'})
        self.assertEqual(out['state'], 'approved')
        thread.join(timeout=5)
        self.assertTrue(result.get('ok'))

    def test_the_legacy_singular_route_is_scoped_too(self):
        other = self.store.create(compile_coding('Elsewhere.', self.project,
                                                 ['python', '-m', 'unittest']),
                                  conversation='elsewhere')
        run, approval_id, thread, result = self.ask_for_step(job=other)
        service = Service(str(self.base / 'data'))
        self.addCleanup(service.shutdown)
        with self.assertRaises(PolicyError) as caught:
            service.action('/api/approval', {'id': approval_id, 'allow': True})
        self.assertIn('another conversation', str(caught.exception))
        with self.assertRaises(PolicyError):
            service.action('/api/approval', {'id': approval_id, 'allow': True,
                                             'conversation': 'main'})
        out = service.action('/api/approval', {'id': approval_id, 'allow': True,
                                               'conversation': 'elsewhere'})
        self.assertEqual(out['status'], 'APPROVED')
        thread.join(timeout=5)
        self.assertTrue(result.get('ok'))

    def test_the_service_route_honours_the_declared_conversation(self):
        run, approval_id, thread, result = self.ask_for_step()
        service = Service(str(self.base / 'data'))
        self.addCleanup(service.shutdown)
        with self.assertRaises(PolicyError):
            service.action('/api/approvals', {'kind': 'action', 'id': approval_id,
                                              'allow': True, 'conversation': 'somewhere-else'})
        out = service.action('/api/approvals', {'kind': 'action', 'id': approval_id,
                                                'allow': True, 'conversation': 'main'})
        self.assertEqual(out['state'], 'approved')
        thread.join(timeout=5)
        self.assertTrue(result.get('ok'))


if __name__ == '__main__':
    unittest.main()
