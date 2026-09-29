"""D-70 items 1, 2 and 4: answering "Needs you" inside the card, the in-thread line's state, and
scoping before big work. Fake models and runtimes only; no provider is ever called.
"""
import contextlib
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from kel import needs_answer, office, scoping, staff
from kel.activity import timeline
from kel.coding import compile_coding
from kel.core import PolicyError, encode
from kel.service import Service

sys.path.insert(0, str(Path(__file__).parent))
from test_office import Base, writing  # noqa: E402
from test_role_models_live import FakeCoder, make_project  # noqa: E402
from test_turn_handoff import FakeTurn  # noqa: E402
from test_workforce_e2e import FakeModel  # noqa: E402

PLUMBING = ("Can you build a small website for my brother's plumbing business? "
            'People should be able to book a visit.')
BIG_WORK = {'action': 'start_background_work', 'title': 'Plumbing website',
            'acknowledgement': "On it — I'm starting on that now in the background.", 'related_topic': None}
SMALL_WORK = {'action': 'start_background_work', 'title': 'Garden plan for spring',
              'acknowledgement': "On it — I'm starting on that now in the background.", 'related_topic': None}
QUESTIONS = {'questions': [
    {'question': 'Who is it for?', 'options': ['Just me', 'My team', 'The public'], 'best_guess': 'My team'},
    {'question': 'How long?', 'options': ['One page', 'Two or three pages'], 'best_guess': 'One page'}],
    'summary': 'a one-page spring garden plan for the back yard'}


# ---- item 1: the question a needs-you card asks, and each answer path ----------------------------

class QuestionTests(Base):
    def _oracle_blocked(self):
        project = make_project(self.tmp.name)
        text = 'Fix the password check in app.txt and deploy it'  # D-85: hard to undo brings the Oracle
        job = self.staffed(compile_coding(text, project, ['python', '-c', 'pass']), text)
        reviews = {'codex': FakeModel('codex', challenges=[{'severity': 'blocker',
                                                            'summary': 'Any password is accepted.'}]),
                   'claude': FakeModel('claude')}
        engine = self.engine({'claude-code': FakeCoder(self.store, reports='claude-opus-5-5')}, reviews)
        try:
            self.drive(engine, job, lambda j: bool(office._published(self.store, job)))
        finally:
            engine.close()
        return job, project

    def test_an_approval_wait_exposes_its_question_and_the_existing_route_answers_it(self):
        from kel.chat_approvals import resolve
        job = self.staffed(writing('Write a haiku about autumn'))
        run = self.store.claim(job, 'document')
        action = {'operation': 'publish', 'target': 'the team page', 'summary': 'publish the team page'}
        approval = self.store.request_approval(job, run['id'], action)
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS approval_actions(approval_id TEXT PRIMARY KEY, action TEXT)')
            db.execute('INSERT INTO approval_actions VALUES(?,?)', (approval, encode(action)))
        view = office.detail(self.store, job)
        self.assertEqual(view['state'], 'needs_you')
        question = view['question']
        self.assertEqual(question['kind'], 'approval')
        self.assertEqual(question['wait'], 'Waiting for your OK')
        self.assertEqual([o['id'] for o in question['options']], ['allow', 'deny'])
        self.assertEqual(question['ref'], {'approval_kind': 'action', 'approval_id': approval})
        self.assertTrue(question['text'])
        # Answered through the in-chat approval's own route: the work continues.
        out = resolve(self.store, question['ref']['approval_kind'], question['ref']['approval_id'], True,
                      conversation=self.store.get(job)['conversation'])
        self.assertEqual(out['state'], 'approved')
        self.assertEqual(self.store.get(job)['state'], 'RUNNING')
        self.assertNotIn('question', office.detail(self.store, job))

    def test_an_oracle_blocker_offers_apply_anyway_and_leave_it_on_the_apply_path(self):
        job, _project = self._oracle_blocked()
        question = office.detail(self.store, job)['question']
        self.assertEqual(question['kind'], 'second_opinion')
        self.assertEqual([o['id'] for o in question['options']], ['apply_anyway', 'leave'])
        self.assertIn('Any password is accepted', question['detail'])
        out = needs_answer.answer_apply(self.store, job, 'leave', actor='user')
        self.assertEqual((out['choice'], out['already']), ('leave', False))
        item = office.items(self.store)['items'][0]
        self.assertEqual((item['state'], item['needs_you']), ('done', False))
        self.assertIn('leave it unapplied', item['status_line'])
        again = needs_answer.answer_apply(self.store, job, 'apply_anyway', actor='user')
        self.assertEqual((again['choice'], again['already']), ('leave', True))  # the first answer stands
        lines = [e for e in timeline(self.store)['entries'] if e['type'] == 'needs_you.answered']
        self.assertEqual([e['what'] for e in lines], ['You chose to leave the checked change unapplied.'])

    def test_apply_anyway_writes_the_change_with_the_user_as_actor(self):
        job, project = self._oracle_blocked()
        out = needs_answer.answer_apply(self.store, job, 'apply_anyway', actor='user')
        self.assertEqual(out['choice'], 'apply_anyway')
        self.assertEqual(out['application']['state'], 'APPLIED')
        item = office.items(self.store)['items'][0]
        self.assertEqual(item['state'], 'done')
        self.assertIn('applied at your request', item['status_line'])
        with self.assertRaisesRegex(PolicyError, 'Only you'):
            needs_answer.answer_apply(self.store, job, 'leave', actor='kel')

    def test_ask_first_holds_a_checked_change_as_a_needs_you_card_with_apply(self):
        from kel import authority
        authority.set_mode(self.store, 'ask')
        project = make_project(self.tmp.name)
        text = 'Change app.txt to say new'
        job = self.staffed(compile_coding(text, project, ['python', '-c', 'pass']), text)
        engine = self.engine({'claude-code': FakeCoder(self.store, reports='claude-opus-5-5')})
        try:
            self.drive(engine, job, lambda j: bool(office._published(self.store, job)))
        finally:
            engine.close()
        self.assertEqual((project / 'app.txt').read_text(), 'old')  # nothing applied on its own
        item = office.items(self.store)['items'][0]
        self.assertEqual((item['state'], item['needs_you'], item['finished']), ('needs_you', True, False))
        self.assertEqual(item['progress']['label'], 'Waiting for you')
        self.assertIn('Ask first is on, so it waits for you to apply it', item['status_line'])
        view = office.detail(self.store, job)
        self.assertEqual(view['application']['waiting_reason'], 'Ask first is on')
        question = view['question']
        self.assertEqual((question['kind'], question['wait']), ('apply', 'Waiting for you to apply it'))
        self.assertEqual([(o['id'], o['label']) for o in question['options']],
                         [('apply_anyway', 'Apply'), ('leave', 'Leave it')])
        self.assertIn('Choose Apply on its work card', view['result'])
        out = needs_answer.answer_apply(self.store, job, 'apply_anyway', actor='user')
        self.assertEqual(out['application']['state'], 'APPLIED')
        self.assertNotEqual((project / 'app.txt').read_text(), 'old')
        item = office.items(self.store)['items'][0]
        self.assertEqual((item['state'], item['needs_you']), ('done', False))
        self.assertIn('applied at your request', item['status_line'])
        self.assertNotIn('question', office.detail(self.store, job))
        lines = [e for e in timeline(self.store)['entries'] if e['type'] == 'needs_you.answered']
        self.assertEqual([e['what'] for e in lines], ['You applied the checked change.'])

    def test_only_a_waiting_change_can_be_answered(self):
        job = self.staffed(writing('Write a haiku about autumn'))
        with self.assertRaisesRegex(PolicyError, 'not waiting'):
            needs_answer.answer_apply(self.store, job, 'leave')
        with self.assertRaisesRegex(PolicyError, 'Apply anyway or Leave it'):
            needs_answer.answer_apply(self.store, job, 'delete')

    def test_paused_blocked_and_clarification_waits(self):
        job = self.staffed(writing('Write a haiku about autumn'))
        with self.store.transaction() as db:
            record = self.store._get(db, job)
            record['state'] = 'PAUSED'
            self.store._save(db, record, 'job.paused')
        question = office.detail(self.store, job)['question']
        self.assertEqual((question['kind'], [o['id'] for o in question['options']]), ('paused', ['resume']))
        with self.store.transaction() as db:
            record = self.store._get(db, job)
            record['state'] = 'BLOCKED'
            self.store._save(db, record, 'test.blocked')
        question = office.detail(self.store, job)['question']
        self.assertEqual((question['kind'], question['options'], question['answer_box']), ('blocked', [], True))
        self.assertEqual(question['conversation_id'], self.store.get(job)['conversation'])


# ---- items 1 and 2 at the service: routes and the in-thread line ---------------------------------

class ServiceBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ.pop('ANTHROPIC_API_KEY', None)
        os.environ.pop('KEL_INTERNAL_MODEL', None)
        os.environ.pop('KEL_WORKFORCE', None)
        os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none')
        self.service = Service(self.tmp.name)
        self.turn = FakeTurn(SMALL_WORK)
        self.service.turn_mode = ''
        self.service.model = self.turn
        self.service.engine.adapters = {}
        self.service.stop.set()
        self.cid = self.service.context.conversation('default')

    def tearDown(self):
        with contextlib.suppress(Exception):
            self.service.shutdown()
        self.tmp.cleanup()

    def row(self, sid):
        with contextlib.closing(self.service.store.connect()) as db:
            return db.execute('SELECT * FROM submissions WHERE id=?', (sid,)).fetchone()

    def wait(self, sid, states=('DISPATCHED', 'SETTLED', 'FAILED', 'INTERRUPTED'), timeout=20):
        deadline = time.time() + timeout
        while time.time() < deadline:
            row = self.row(sid)
            if row and row['state'] in states:
                return row['state']
            time.sleep(.02)
        raise TimeoutError('submission %s never reached %s' % (sid, states))

    def messages(self):
        with contextlib.closing(self.service.store.connect()) as db:
            return [dict(r) for r in db.execute('SELECT * FROM messages WHERE conversation_id=? ORDER BY seq',
                                                (self.cid,))]

    def scopings(self):
        scoping.ensure_schema(self.service.store)
        with contextlib.closing(self.service.store.connect()) as db:
            return [dict(r) for r in db.execute('SELECT * FROM scopings ORDER BY created')]


class RouteTests(ServiceBase):
    def test_leave_it_on_the_apply_route_and_unknown_actions_refused(self):
        with self.assertRaisesRegex(PolicyError, 'could not find'):
            self.service.action('/api/apply', {'job': 'nope', 'action': 'leave'})
        with self.assertRaisesRegex(PolicyError, 'Choose Apply or Undo'):
            self.service.action('/api/apply', {'job': 'nope', 'action': 'remove'})
        with self.assertRaisesRegex(PolicyError, 'Actor identity'):
            self.service.action('/api/apply', {'job': 'nope', 'action': 'leave', 'actor': 'kel'})

    def test_the_handoff_view_names_the_top_card_state_for_staffed_work(self):
        sid = self.service.submit({'text': 'Write me a spring garden plan for the back yard', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'DISPATCHED')
        view = self.service.handoff_view(self.cid, sid)
        self.assertTrue(view['staffed'])
        self.assertEqual(view['office_state'], 'working')
        # Old work without a card keeps today's card: no `staffed` flag.
        contract = writing('Write a haiku')
        job = self.service.store.create(contract, conversation=self.cid)
        with self.service.store.transaction() as db:
            db.execute("UPDATE submissions SET job_id=? WHERE id=?", (job, sid))
        self.assertNotIn('staffed', self.service.handoff_view(self.cid, sid))


# ---- item 4: scoping before big work ----------------------------------------------------------------

class ScopingTests(ServiceBase):
    def test_big_work_is_scoped_first_and_nothing_starts(self):
        self.turn.answer = BIG_WORK
        before = set(Path.home().glob('Documents/Kel Projects/*'))
        sid = self.service.submit({'text': PLUMBING, 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'SETTLED')
        self.assertEqual([j for j in self.service.store.list_jobs() if j['conversation'] == self.cid], [])
        self.assertEqual(set(Path.home().glob('Documents/Kel Projects/*')), before, 'no folder before Start')
        rows = self.scopings()
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['state'], rows[0]['why']), ('open', 'size'))
        said = self.messages()[-1]
        self.assertEqual(said['text'], "Happy to. It's a bigger job, so three quick questions first; I'll decide the rest.")
        self.assertEqual(json.loads(said['meta'])['kind'], 'scoping')
        view = scoping.view(self.service.store, rows[0]['id'], self.cid)
        self.assertEqual(len(view['questions']), 3)
        self.assertTrue(view['summary'].startswith("I'll build: "))
        # The top card says "Scoping" with its question count and no progress bar.
        items = self.service.office({'conversation': [self.cid]})['items']
        self.assertEqual([(i['state'], i['questions'], i['progress']) for i in items], [('scoping', 3, None)])
        # One Activity line: Kel asked; nothing ran.
        lines = [e for e in timeline(self.service.store)['entries'] if e['type'] == 'scoping.asked']
        self.assertEqual(len(lines), 1)
        self.assertIn('nothing ran yet', lines[0]['what'])
        # Handing the scoping to no one: the submission never got an acknowledgement or a job.
        self.assertIsNone(self.row(sid)['job_id'])

    def test_small_work_below_the_threshold_starts_straight_away(self):
        sid = self.service.submit({'text': 'Write me a spring garden plan for the back yard', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'DISPATCHED')
        self.assertEqual(self.scopings(), [])

    def test_the_threshold_is_one_setting(self):
        self.assertEqual(scoping.threshold(self.service.store), 'D2')
        scoping.set_threshold(self.service.store, 'off')
        self.turn.answer = BIG_WORK
        sid = self.service.submit({'text': 'Summarize my week in a short note', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'DISPATCHED')
        self.assertEqual(self.scopings(), [])
        with self.assertRaisesRegex(PolicyError, 'D1, D2'):
            scoping.set_threshold(self.service.store, 'huge')

    def test_open_questions_scope_small_work_and_start_carries_the_answers(self):
        self.turn.answer = dict(SMALL_WORK, scoping=QUESTIONS)
        sid = self.service.submit({'text': 'Write me a spring garden plan for the back yard', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'SETTLED')
        row = self.scopings()[0]
        self.assertEqual(row['why'], 'open_questions')
        view = scoping.view(self.service.store, row['id'])
        self.assertEqual([q['question'] for q in view['questions']], ['Who is it for?', 'How long?'])
        self.assertEqual(view['summary'], "I'll write: a one-page spring garden plan for the back yard")
        # Q1 picked; Q2 typed ("Something else…"), understood by the vetting ingestion as typed.
        out = self.service.action('/api/scoping', {'action': 'start', 'id': row['id'], 'conversation': self.cid,
                                                   'answers': {'Q1': {'option': 'C'},
                                                               'Q2': {'text': 'a single index card'}}})
        self.assertEqual(out['state'], 'started')
        self.assertEqual(out['answer_line'], 'The public · a single index card')
        new_sid = out['submission_id']
        self.assertEqual(self.wait(new_sid), 'DISPATCHED')
        job = self.service.store.get(self.row(new_sid)['job_id'])
        self.assertIn('Details agreed before starting:', job['contract']['request'])
        self.assertIn('Who is it for? The public', job['contract']['request'])
        answers = job['contract']['context']['scoping']['answers']
        self.assertEqual([(a['answer'], a['assumed']) for a in answers],
                         [('The public', False), ('a single index card', False)])
        # The vetting ingestion recorded both answers (one path for every source).
        with contextlib.closing(self.service.store.connect()) as db:
            recorded = {r['question_id']: (json.loads(r['selected']), r['custom']) for r in db.execute(
                'SELECT * FROM vetting_answers WHERE session_id=?', (row['session_id'],))}
        self.assertEqual(recorded, {'Q1': (['C'], ''), 'Q2': ([], 'a single index card')})
        # The card turned into work: a hand-off with its own acknowledgement, and no Scoping card left.
        self.assertTrue(self.service.handoff_view(self.cid, new_sid)['staffed'])
        states = [i['state'] for i in self.service.office({'conversation': [self.cid]})['items']]
        self.assertEqual(states, ['working'])
        # Start is idempotent.
        again = self.service.action('/api/scoping', {'action': 'start', 'id': row['id'], 'conversation': self.cid})
        self.assertTrue(again['already'])
        self.assertEqual(len([j for j in self.service.store.list_jobs() if j['conversation'] == self.cid]), 1)
        whats = [e['what'] for e in timeline(self.service.store)['entries'] if e['type'].startswith('scoping.')]
        self.assertEqual(len(whats), 2)

    def test_best_guess_starts_at_once_with_the_assumptions_recorded(self):
        self.turn.answer = dict(SMALL_WORK, scoping=QUESTIONS)
        sid = self.service.submit({'text': 'Write me a spring garden plan for the back yard', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'SETTLED')
        row = self.scopings()[0]
        out = self.service.action('/api/scoping', {'action': 'best_guess', 'id': row['id'], 'conversation': self.cid})
        self.assertEqual(out['state'], 'best_guess')
        self.assertEqual(self.wait(out['submission_id']), 'DISPATCHED')
        job = self.service.store.get(self.row(out['submission_id'])['job_id'])
        answers = job['contract']['context']['scoping']
        self.assertTrue(answers['best_guess'])
        self.assertEqual([(a['answer'], a['assumed']) for a in answers['answers']],
                         [('My team', True), ('One page', True)])
        self.assertIn("(Kel's best guess)", job['contract']['request'])
        ack = [m for m in self.messages() if 'best guess' in m['text']][-1]
        self.assertIn('my team; one page', ack['text'])
        lines = [e for e in timeline(self.service.store)['entries'] if e['type'] == 'scoping.best_guess']
        self.assertEqual(len(lines), 1)

    def test_scoping_is_scoped_to_its_conversation_and_the_route_is_plain(self):
        self.turn.answer = dict(SMALL_WORK, scoping=QUESTIONS)
        sid = self.service.submit({'text': 'Write me a spring garden plan for the back yard', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'SETTLED')
        row = self.scopings()[0]
        with self.assertRaisesRegex(PolicyError, 'could not find'):
            self.service.action('/api/scoping', {'action': 'start', 'id': row['id'], 'conversation': 'other'})
        with self.assertRaisesRegex(PolicyError, 'Choose Start'):
            self.service.action('/api/scoping', {'action': 'delete', 'id': row['id']})
        with self.assertRaisesRegex(PolicyError, 'Actor identity'):
            self.service.action('/api/scoping', {'action': 'start', 'id': row['id'], 'actor': 'kel'})

    def test_bad_model_questions_fall_back_to_kels_own(self):
        cleaned = scoping.clean_questions([{'question': 'Pick', 'options': ['Only one']},
                                           {'question': '## heading', 'options': ['a', 'b']},
                                           {'question': 'Which colour?', 'options': ['Red', 'red', 'Blue'],
                                            'best_guess': 'Blue'}])
        self.assertEqual(cleaned, [{'prompt': 'Which colour?', 'options': ['Red', 'Blue'], 'best': 1}])
        self.turn.answer = dict(BIG_WORK, scoping={'questions': 'nonsense'})
        sid = self.service.submit({'text': PLUMBING, 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'SETTLED')
        view = scoping.view(self.service.store, self.scopings()[0]['id'])
        self.assertEqual(view['questions'][0]['question'], 'How finished should the first version be?')

    def test_the_keyword_gate_never_scopes(self):
        self.service.model = None  # no turn model: the old gate and a template acknowledgement
        handed = []
        self.service._handoff = lambda *args, **kwargs: handed.append(args[2])  # nothing really starts
        self.service.submit({'text': PLUMBING, 'conversation': self.cid})
        deadline = time.time() + 20
        while not handed and time.time() < deadline:
            time.sleep(.02)
        self.assertEqual(handed, [PLUMBING])
        self.assertEqual(self.scopings(), [])


if __name__ == '__main__':
    unittest.main()
