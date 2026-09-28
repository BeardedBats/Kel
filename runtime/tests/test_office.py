"""D-66/D-68: the live work view — cards for staffed work, the detail of one piece of work, and
removing a finished card. Read-only engine truth; fake runtimes only.
"""
import contextlib
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from kel import office, staff
from kel.activity import timeline
from kel.coding import CodingAdapter, compile_coding
from kel.commander import Commander
from kel.core import PolicyError, Store
from kel.engine import Engine

sys.path.insert(0, str(Path(__file__).parent))
from test_role_models_live import FakeCoder, make_project  # noqa: E402
from test_workforce_e2e import FakeModel, FakeText, StaffStub  # noqa: E402

PLAIN_FORBIDDEN = ('D0', 'D1', 'D2', 'D3', 'D4', 'lease', 'run_id', 'staff_calls', 'tsk_', 'epoch')


def writing(request):
    return {'request': request, 'compiler': 'test', 'handoff': {'submission_id': 'sub-1', 'ack_seq': 7,
                                                                'title': 'Autumn haiku'},
            'milestones': [{'id': 'document', 'objective': request, 'filename': 'result.md', 'depends_on': [],
                            'checks': [{'kind': 'min_chars', 'value': 5},
                                       {'kind': 'manual_review', 'rubric': 'Satisfies the request.'}]}]}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ.pop('KEL_WORKFORCE', None)
        self.store = Store(Path(self.tmp.name) / 'data')
        staff.ensure_schema(self.store)
        CodingAdapter(self.store)

    def staffed(self, contract, text=None):
        contract['staffing'] = staff.plan_job(self.store, contract, text)
        return self.store.create(contract)

    def engine(self, adapters, reviews=None, stub_adapters=('codex', 'claude')):
        commander = Commander(FakeModel('claude'))
        commander.staff = StaffStub(set(stub_adapters), reviews or {'codex': FakeModel('codex'),
                                                                     'claude': FakeModel('claude')})
        return Engine(self.store, adapters, reviewer=commander)

    def drive(self, engine, job, until, timeout=40):
        deadline = time.time() + timeout
        while time.time() < deadline:
            engine.tick()
            if until(self.store.get(job)):
                return self.store.get(job)
            time.sleep(.03)
        raise TimeoutError(self.store.get(job)['state'])

    def assert_plain(self, value):
        text = json.dumps(value)
        for word in PLAIN_FORBIDDEN:
            self.assertNotIn('"%s' % word, text)


class ListTests(Base):
    def test_only_staffed_work_becomes_a_card(self):
        self.store.create(writing('Write a haiku'))  # workforce off / older work: no card
        job = self.staffed(writing('Write a haiku about autumn'))
        listing = office.items(self.store)
        self.assertEqual([item['job_id'] for item in listing['items']], [job])
        item = listing['items'][0]
        self.assertEqual((item['title'], item['kind'], item['state'], item['finished']),
                         ('Autumn haiku', 'writing', 'working', False))
        self.assertEqual(item['progress'], {'done': 0, 'total': 1, 'label': 'Working on it'})
        self.assertEqual(item['team'][0]['role'], 'kel')
        self.assert_plain(listing)

    def test_a_finished_card_stays_until_removed_and_removal_is_durable_and_idempotent(self):
        job = self.staffed(writing('Write a haiku about autumn'))
        engine = self.engine({'codex': FakeText('gpt-6-luna'), 'claude': FakeText('claude-sonnet-4-6')})
        try:
            self.drive(engine, job, lambda j: j['state'] == 'CLOSED')
            self.drive(engine, job, lambda j: bool(office._published(self.store, job)))
        finally:
            engine.close()
        item = office.items(self.store)['items'][0]
        self.assertEqual((item['state'], item['finished'], item['status_line']), ('done', True, 'Done and checked.'))
        self.assertEqual(item['progress']['label'], 'Done')
        # Never trimmed by age: a card finished long ago is still there.
        with self.store.transaction() as db:
            db.execute('UPDATE events SET at=at-864000 WHERE aggregate_id=?', (job,))
        self.assertEqual([i['job_id'] for i in office.items(self.store)['items']], [job])
        first = office.dismiss(self.store, job)
        self.assertEqual((first['dismissed'], first['already']), (True, False))
        second = office.dismiss(self.store, job)
        self.assertEqual((second['dismissed'], second['already']), (True, True))
        self.assertEqual(office.items(self.store)['items'], [])
        # Survives a restart (a fresh store object on the same data) and deletes nothing.
        again = Store(self.store.root)
        self.assertEqual(office.items(again)['items'], [])
        self.assertEqual(again.get(job)['verdict'], 'VERIFIED')
        with contextlib.closing(again.connect()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM publications WHERE job_id=?', (job,)).fetchone()[0], 1)
        lines = [e for e in timeline(again)['entries'] if e['type'] == 'office.dismissed']
        self.assertEqual(len(lines), 1, 'one Activity line, even after a second remove')
        self.assertEqual(lines[0]['what'], 'You removed finished work from the top of the chat.')

    def test_open_work_cannot_be_removed(self):
        job = self.staffed(writing('Write a haiku about autumn'))
        with self.assertRaisesRegex(PolicyError, 'Stop it first'):
            office.dismiss(self.store, job)
        with self.assertRaisesRegex(PolicyError, 'could not find'):
            office.dismiss(self.store, 'no-such-job')

    def test_stable_order_needs_you_then_working_then_finished_newest_first(self):
        done_old = self.staffed(writing('Write the first note'))
        done_new = self.staffed(writing('Write the second note'))
        working = self.staffed(writing('Write the third note'))
        waiting = self.staffed(writing('Write the fourth note'))
        stamp = time.time()
        with self.store.transaction() as db:
            for job, when in ((done_old, stamp - 50), (done_new, stamp - 10)):
                record = self.store._get(db, job)
                record.update(state='CANCELLED')
                self.store._save(db, record, 'job.cancel')
                db.execute('UPDATE events SET at=? WHERE aggregate_id=?', (when, job))
            record = self.store._get(db, waiting)
            record.update(state='AWAITING_USER')
            self.store._save(db, record, 'test.waiting')
        order = [item['job_id'] for item in office.items(self.store)['items']]
        self.assertEqual(order, [waiting, working, done_new, done_old])
        self.assertEqual([item['order'] for item in office.items(self.store)['items']], [0, 1, 2, 3])
        states = {item['job_id']: item['state'] for item in office.items(self.store)['items']}
        self.assertEqual((states[waiting], states[working], states[done_new]), ('needs_you', 'working', 'stopped'))

    def test_scope_by_conversation(self):
        mine = writing('Write a haiku about autumn')
        job = self.store.create(dict(mine, staffing=staff.plan_job(self.store, mine)), conversation='chat-a')
        other = writing('Write a limerick')
        self.store.create(dict(other, staffing=staff.plan_job(self.store, other)), conversation='chat-b')
        self.assertEqual([i['job_id'] for i in office.items(self.store, conversation='chat-a')['items']], [job])


class DetailTests(Base):
    def test_the_detail_names_every_staff_member_and_only_models_that_ran(self):
        project = make_project(self.tmp.name)
        text = 'Fix the password check in app.txt'
        job = self.staffed(compile_coding(text, project, ['python', '-c', 'pass']), text)
        claude = FakeCoder(self.store, reports='claude-opus-5-5')
        engine = self.engine({'claude-code': claude})
        try:
            self.drive(engine, job, lambda j: (project / 'app.txt').read_text() == 'new')
            self.drive(engine, job, lambda j: bool(office._published(self.store, job)))
        finally:
            engine.close()
        view = office.detail(self.store, job)
        self.assert_plain(view)
        roles = [(m['role'], m['state']) for m in view['staff']]
        self.assertEqual(roles, [('kel', 'done'), ('builder', 'done'), ('verifier', 'done'), ('sentinel', 'done'),
                                 ('oracle', 'done')])
        sentinel = view['staff'][3]
        self.assertEqual((sentinel['role_label'], sentinel['doing']),
                         ('Sentinel', 'Security check: found nothing that should stop this'))
        # The detail carries Sentinel and the Red Team in the Oracle's shape.
        shape = {'state', 'why', 'conclusion', 'coverage', 'independence', 'independence_label', 'model_label',
                 'reasoning', 'findings'}
        self.assertEqual(set(view['sentinel']), shape)
        self.assertEqual(set(view['red_team']), shape)
        self.assertEqual((view['sentinel']['state'], view['sentinel']['conclusion']),
                         ('done', 'It found nothing that should stop this.'))
        self.assertEqual(view['sentinel']['independence_label'],
                         'A different model family from the one that did the work')
        self.assertEqual(view['red_team']['state'], 'not_needed', 'a one-file change is below the Red Team size')
        builder = view['staff'][1]
        self.assertEqual((builder['model_label'], builder['version'], builder['model_confirmed'], builder['runtime'],
                          builder['provider']), ('Claude Opus 5.5', 'Opus 5.5', True, 'Claude Code', 'Anthropic'))
        self.assertIsNone(builder['asked'])
        verifier = view['staff'][2]
        self.assertEqual((verifier['model_label'], verifier['independence']), ('GPT-6 Astra', 'different'))
        # Routing 2: review is assurance-tier, so a Verifier left on Auto reasons at High.
        self.assertEqual(verifier['reasoning'], 'High')
        self.assertEqual(view['state'], 'done')
        self.assertEqual(view['status_line'], 'Done and checked — applied to your project.')
        self.assertEqual(view['files_changed'], ['app.txt'])
        self.assertEqual(view['verification']['result'], 'passed')
        self.assertEqual(view['oracle']['state'], 'done')
        self.assertEqual(view['oracle']['model_label'], 'GPT-6 Astra')
        self.assertEqual(view['review']['verdict'], 'verified')
        self.assertEqual([s['state'] for s in view['steps']], ['done'])
        self.assertEqual(view['application']['state'], 'APPLIED')
        self.assertEqual(view['kind'], 'code')

    def test_a_model_that_did_not_report_is_not_shown_as_having_run(self):
        project = make_project(self.tmp.name)
        text = 'Fix the typo in app.txt'
        job = self.staffed(compile_coding(text, project, ['python', '-c', 'pass']), text)
        codex = FakeCoder(self.store)  # Claude Code missing; Codex ran but reported no model
        engine = self.engine({'codex-code': codex}, stub_adapters=('codex',))
        try:
            self.drive(engine, job, lambda j: j['milestones']['code']['attempts'] >= 1
                       and j['milestones']['code']['state'] != 'RUNNING')
        finally:
            engine.close()
        builder = next(m for m in office.detail(self.store, job)['staff'] if m['role'] == 'builder')
        self.assertIsNone(builder['model'])
        self.assertIsNone(builder['model_label'])
        self.assertFalse(builder['model_confirmed'])
        self.assertEqual(builder['asked']['model_label'], 'Claude Opus 5.5')
        self.assertIn('Claude Opus 5.5', builder['note'])
        self.assertEqual(builder['runtime'], 'Codex')

    def test_an_oracle_blocker_shows_as_needs_you_with_its_finding(self):
        project = make_project(self.tmp.name)
        text = 'Fix the password check in app.txt'
        job = self.staffed(compile_coding(text, project, ['python', '-c', 'pass']), text)
        reviews = {'codex': FakeModel('codex', challenges=[{'severity': 'blocker',
                                                            'summary': 'Any password is accepted.'}]),
                   'claude': FakeModel('claude')}
        engine = self.engine({'claude-code': FakeCoder(self.store, reports='claude-opus-5-5')}, reviews)
        try:
            self.drive(engine, job, lambda j: bool(office._published(self.store, job)))
        finally:
            engine.close()
        item = office.items(self.store)['items'][0]
        self.assertEqual((item['state'], item['needs_you'], item['finished']), ('needs_you', True, False))
        self.assertIn('Any password is accepted', item['status_line'])
        view = office.detail(self.store, job)
        self.assertEqual(view['oracle']['findings'], [{'severity': 'blocker', 'area': 'Second opinion',
                                                       'summary': 'Any password is accepted.', 'where': None,
                                                       'status': 'open'}])
        with self.assertRaisesRegex(PolicyError, 'Stop it first'):
            office.dismiss(self.store, job)

    def test_unknown_or_unstaffed_work_is_refused_plainly(self):
        with self.assertRaisesRegex(PolicyError, 'could not find'):
            office.detail(self.store, 'nope')
        job = self.store.create(writing('Write a haiku'))
        with self.assertRaisesRegex(PolicyError, 'no live team'):
            office.detail(self.store, job)


class RouteTests(unittest.TestCase):
    def test_the_engine_routes(self):
        from kel.service import Service
        with tempfile.TemporaryDirectory() as tmp:
            saved = dict(os.environ)
            try:
                os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none')
                os.environ.pop('ANTHROPIC_API_KEY', None)
                os.environ.pop('KEL_WORKFORCE', None)
                service = Service(tmp)
                try:
                    service.stop.set()
                    contract = writing('Write a haiku about autumn')
                    contract['staffing'] = staff.plan_job(service.store, contract)
                    job = service.store.create(contract)
                    listing = service.office({'project': ['*']})
                    self.assertEqual([i['job_id'] for i in listing['items']], [job])
                    self.assertEqual(service.office_item(job)['job_id'], job)
                    with self.assertRaisesRegex(PolicyError, 'Stop it first'):
                        service.action('/api/office', {'action': 'dismiss', 'id': job})
                    with self.assertRaisesRegex(PolicyError, 'only remove'):
                        service.action('/api/office', {'action': 'restore', 'id': job})
                finally:
                    service.shutdown()
            finally:
                os.environ.clear()
                os.environ.update(saved)


if __name__ == '__main__':
    unittest.main()
