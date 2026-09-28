"""D-53: the conversational background hand-off.

A real-work message gets a warm acknowledgement at once, the work starts durably in the
background, the chat stays usable, and the checked result is posted into the same conversation.
Plain questions are still answered directly. No real model provider is ever called here: the turn
model is a fake that returns fixed JSON.
"""
import contextlib
import json
import os
import tempfile
import threading
import time
import unittest

from kel.core import PolicyError, Store
from kel.service import Service
from kel import handoff
from kel.turn import (CHANGE_CLAIM, COMPLETION_CLAIM, FORCED_SUFFIX, NO_CHANGE, NO_CHANGE_WITH_WORK,
                      decide, guard_ack, guard_reply, template_ack, title_for)


class FakeTurn:
    """A turn model that answers from a script; records what it was asked."""

    def __init__(self, answer=None, outcome='SUCCESS'):
        self.answer = answer
        self.outcome = outcome
        self.calls = []

    def execute(self, prompt, system=None, images=None, **kwargs):
        self.calls.append({'prompt': prompt, 'system': system})
        answer = self.answer(prompt, system) if callable(self.answer) else self.answer
        if self.outcome != 'SUCCESS':
            return {'outcome': self.outcome, 'error': 'fake failure'}
        return {'outcome': 'SUCCESS', 'text': answer if isinstance(answer, str) else json.dumps(answer)}


WORK = {'action': 'start_background_work', 'title': 'Garden plan for spring',
        'acknowledgement': "Great — that's getting taken care of; I'll post it here once it's been "
                           'checked. While that runs, want to talk through which beds get the most sun?',
        'related_topic': 'which beds get the most sun'}
REPLY = {'action': 'reply', 'text': 'Tomatoes like six to eight hours of sun.'}


class DecideTests(unittest.TestCase):
    packet = {'project': {'name': 'Home', 'decisions': ''}, 'history': [], 'files': []}

    def test_reply_and_work_are_parsed(self):
        self.assertEqual(decide(FakeTurn(REPLY), self.packet, 'how much sun?', []),
                         {'action': 'reply', 'text': 'Tomatoes like six to eight hours of sun.'})
        work = decide(FakeTurn(WORK), self.packet, 'write me a garden plan', [])
        self.assertEqual(work['action'], 'start_background_work')
        self.assertEqual(work['title'], 'Garden plan for spring')
        self.assertEqual(work['acknowledgement'], WORK['acknowledgement'])
        self.assertEqual(work['related_topic'], 'which beds get the most sun')

    def test_fenced_json_and_the_system_prompt(self):
        model = FakeTurn('```json\n' + json.dumps(REPLY) + '\n```')
        self.assertEqual(decide(model, self.packet, 'q', [])['action'], 'reply')
        self.assertIn('You are Kel, one helpful assistant', model.calls[0]['system'])
        self.assertNotIn(FORCED_SUFFIX, model.calls[0]['system'])
        self.assertIn("The person's latest message:\nq", model.calls[0]['prompt'])

    def test_unparseable_answer_is_a_reply_and_forced_mode_uses_the_template(self):
        self.assertEqual(decide(FakeTurn('Sure, happy to help.'), self.packet, 'hi', []),
                         {'action': 'reply', 'text': 'Sure, happy to help.'})
        forced = FakeTurn('Sure, happy to help.')
        out = decide(forced, self.packet, 'run `git status`', [], forced=True)
        self.assertEqual(out['action'], 'start_background_work')
        self.assertEqual(out['acknowledgement'], template_ack())
        self.assertIn(FORCED_SUFFIX, forced.calls[0]['system'])

    def test_forced_mode_overrides_a_reply(self):
        out = decide(FakeTurn(REPLY), self.packet, 'run `git status`', [], forced=True)
        self.assertEqual(out['action'], 'start_background_work')

    def test_no_model_or_a_failed_call_falls_back(self):
        self.assertIsNone(decide(None, self.packet, 'hi', []))
        self.assertIsNone(decide(FakeTurn(REPLY, outcome='FAILED'), self.packet, 'hi', []))
        forced = decide(FakeTurn(REPLY, outcome='FAILED'), self.packet, 'run `git status`', [], forced=True)
        self.assertEqual(forced['acknowledgement'], template_ack())

    def test_running_work_reaches_the_model(self):
        model = FakeTurn(REPLY)
        decide(model, self.packet, "how's it going?", [{'title': 'Garden plan', 'state': 'RUNNING',
                                                        'summary': 'still running, not finished yet'}])
        self.assertIn('still running, not finished yet', model.calls[0]['prompt'])

    RUNNING = [{'work_id': 'sub-1', 'title': 'Garden plan', 'state': 'RUNNING', 'can_amend': True,
                'request': 'Write a garden plan'},
               {'work_id': 'sub-0', 'title': 'Old list', 'state': 'CLOSED', 'can_amend': False,
                'request': 'Write a list'}]

    def test_an_amendment_names_changeable_work_and_carries_the_whole_request(self):
        answer = {'action': 'amend_background_work', 'work_id': 'sub-1',
                  'amended_request': 'Write a garden plan that includes herbs', 'title': 'Garden plan with herbs'}
        out = decide(FakeTurn(answer), self.packet, 'also include herbs', self.RUNNING)
        self.assertEqual(out, {'action': 'amend_background_work', 'work_id': 'sub-1',
                               'amended_request': 'Write a garden plan that includes herbs',
                               'title': 'Garden plan with herbs'})
        # A wrong or missing id falls to the only changeable work; a missing request is rebuilt.
        out = decide(FakeTurn({'action': 'amend_background_work', 'work_id': 'nope'}), self.packet,
                     'also include herbs', self.RUNNING)
        self.assertEqual((out['work_id'], out['amended_request']),
                         ('sub-1', 'Write a garden plan\n\nChange: also include herbs'))
        # Work that can no longer change is never amended: the amended request is new work.
        out = decide(FakeTurn(dict(answer, work_id='sub-0')), self.packet, 'also include herbs',
                     [self.RUNNING[1]])
        self.assertEqual(out['action'], 'start_background_work')
        self.assertEqual(out['acknowledgement'], template_ack())
        # Forced messages may still be amendments.
        out = decide(FakeTurn(answer), self.packet, 'also run `git status`', self.RUNNING, forced=True)
        self.assertEqual(out['action'], 'amend_background_work')

    def test_a_reply_claiming_a_change_is_rejected(self):
        claim = {'action': 'reply', 'text': "Got it — I've folded the herbs into the plan."}
        out = decide(FakeTurn(claim), self.packet, 'also include herbs', self.RUNNING)
        self.assertEqual(out, {'action': 'reply', 'text': NO_CHANGE_WITH_WORK})
        out = decide(FakeTurn("Sure, I've added that."), self.packet, 'add herbs', [])
        self.assertEqual(out, {'action': 'reply', 'text': NO_CHANGE})

    def test_the_system_prompt_asks_before_starting_and_offers_only_next_steps(self):
        model = FakeTurn(REPLY)
        decide(model, self.packet, 'q', [])
        system = model.calls[0]['system']
        self.assertIn('Ask before you start, never after', system)
        self.assertIn('amend_background_work', system)
        self.assertNotIn('a detail that would improve the result', system)


class GuardTests(unittest.TestCase):
    def test_completion_claims_and_markdown_are_rejected(self):
        for bad in ("It's done! Anything else?", 'Here is the plan you asked for.',
                    "I've written the document.", 'The result is verified.', 'All tests passed.',
                    'Now ready for you.', '# Plan\nOn it.', '- step one\n- step two', 'x' * 601):
            self.assertEqual(guard_ack(bad, 'soil'), template_ack('soil'), bad)
        good = "On it — I'm starting on that in the background. Want to talk about soil meanwhile?"
        self.assertEqual(guard_ack(good, 'soil'), good)
        self.assertEqual(guard_ack(None), template_ack())

    def test_acks_never_claim_a_change_ask_for_a_detail_or_say_it_already_runs(self):
        # D-55: a hand-off offers a next step; it never asks for a detail that would change the
        # work it just started, and nothing claims a change was folded in without a restart.
        for bad in ("On it! I've added the herbs you mentioned.", "Got it — I'll fold that in.",
                    'Sure, that has been incorporated into the plan.',
                    'Starting now. Should I include a watering schedule too?',
                    'Starting now. Let me know which beds you want covered.',
                    "Starting now. Do you want me to focus on vegetables?",
                    "It's already running in the background.", "I've started on it."):
            self.assertEqual(guard_ack(bad, 'soil'), template_ack('soil'), bad)
        self.assertIsNone(CHANGE_CLAIM.search(template_ack('soil')))

    def test_a_reply_never_claims_a_change_it_did_not_make(self):
        running = [{'work_id': 's1', 'title': 'Garden plan', 'can_amend': True}]
        self.assertEqual(guard_reply("Done — I've added herbs to the plan.", running), NO_CHANGE_WITH_WORK)
        self.assertEqual(guard_reply("I've updated it to include herbs.", []), NO_CHANGE)
        for fine in ("It's still running — I'll update you when it's checked.",
                     "I'm working on it; two of three parts are checked.",
                     'Tomatoes need six to eight hours of sun, including morning light.'):
            self.assertEqual(guard_reply(fine, running), fine)

    def test_template_offers_the_topic_or_an_open_question(self):
        self.assertTrue(template_ack('who the plan is for').endswith(
            'Want to talk about who the plan is for while it runs?'))
        self.assertTrue(template_ack().endswith("Anything you'd like to talk through meanwhile?"))
        self.assertTrue(template_ack('- a list').endswith('meanwhile?'))
        self.assertIsNone(COMPLETION_CLAIM.search(template_ack('soil')))

    def test_title_prefers_a_plain_model_title(self):
        self.assertEqual(title_for('write a plan', 'Spring garden plan'), 'Spring garden plan')
        self.assertEqual(title_for('write a plan', '# x'), 'write a plan')
        long = 'please write a very detailed plan for my vegetable garden with raised beds and drip lines'
        self.assertTrue(title_for(long).endswith('…'))
        self.assertLessEqual(len(title_for(long)), 61)


class HandoffServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ.pop('ANTHROPIC_API_KEY', None)
        os.environ.pop('KEL_INTERNAL_MODEL', None)
        os.environ['KEL_REVIEWER'] = 'none'
        os.environ['KEL_SKIP_TELEMETRY'] = '1'
        os.environ['KEL_TURN_MODEL'] = 'none'
        self.services = []
        self.service = self.start()
        # The turn model is a fake; no worker may run for real.
        self.turn = FakeTurn(lambda prompt, system: REPLY if 'how much sun' in
                             prompt.split('latest message:')[-1].lower() else WORK)
        self.service.turn_mode = ''
        self.service.model = self.turn
        self.service.engine.adapters = {}
        self.service.stop.set()  # no supervision: jobs stay where the test puts them
        self.cid = self.service.context.conversation('default')

    def start(self):
        service = Service(self.tmp.name)
        self.services.append(service)
        return service

    def tearDown(self):
        for service in self.services:
            with contextlib.suppress(Exception):
                service.shutdown()
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
        raise TimeoutError('submission %s never reached %s (now %s)' % (sid, states, self.row(sid)['state']))

    def wait_for_ack(self, sid, timeout=20):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with contextlib.closing(self.service.store.connect()) as db:
                ack = db.execute('SELECT * FROM submission_acks WHERE submission_id=?', (sid,)).fetchone()
            if ack:
                return ack
            time.sleep(.02)
        raise TimeoutError('no acknowledgement')

    def messages(self):
        with contextlib.closing(self.service.store.connect()) as db:
            return [dict(r) for r in db.execute(
                'SELECT * FROM messages WHERE conversation_id=? ORDER BY seq', (self.cid,))]

    def block_planning(self):
        gate = threading.Event()
        original = self.service._compile_work

        def slow(*args, **kwargs):
            gate.wait(20)
            return original(*args, **kwargs)
        self.service._compile_work = slow
        self.addCleanup(gate.set)
        return gate

    def test_a_question_is_answered_directly_without_a_job(self):
        sid = self.service.submit({'text': 'How much sun do tomatoes need?', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'SETTLED')
        self.assertEqual([j for j in self.service.store.list_jobs() if j['conversation'] == self.cid], [])
        self.assertEqual(self.messages()[-1]['text'], REPLY['text'])
        submission = next(s for s in self.service.state(self.cid)['submissions'] if s['id'] == sid)
        self.assertIsNone(submission['ack_seq'])

    def test_work_is_acknowledged_while_planning_then_dispatched_with_its_handoff(self):
        gate = self.block_planning()
        text = 'Write me a spring garden plan for the back yard'
        sid = self.service.submit({'text': text, 'conversation': self.cid})
        ack = self.wait_for_ack(sid)
        self.assertEqual(self.row(sid)['state'], 'PLANNING')
        state = self.service.state(self.cid)
        submission = next(s for s in state['submissions'] if s['id'] == sid)
        self.assertEqual(submission['ack_seq'], ack['message_seq'])
        self.assertEqual(submission['title'], 'Garden plan for spring')
        ack_message = next(m for m in state['messages'] if m['seq'] == ack['message_seq'])
        self.assertEqual(ack_message['role'], 'assistant')
        self.assertEqual(ack_message['text'], WORK['acknowledgement'])
        gate.set()
        self.assertEqual(self.wait(sid), 'DISPATCHED')
        job_id = self.row(sid)['job_id']
        job = self.service.store.get(job_id)
        self.assertEqual(job['contract']['handoff'],
                         {'submission_id': sid, 'ack_seq': ack['message_seq'], 'title': 'Garden plan for spring'})
        users = [m for m in self.messages() if m['role'] == 'user']
        self.assertEqual(len(users), 1, users)
        self.assertEqual(users[0]['text'], text)
        self.assertEqual(users[0]['job_id'], job_id)
        self.assertLess(users[0]['seq'], ack['message_seq'])

    def test_a_tool_request_is_work_even_when_the_model_says_reply(self):
        self.turn.answer = REPLY
        sid = self.service.submit({'text': 'Please run `git status` in the repo and tell me', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'DISPATCHED')
        self.assertIn(FORCED_SUFFIX, self.turn.calls[-1]['system'])
        self.assertTrue(self.row(sid)['job_id'])
        ack = self.wait_for_ack(sid)
        text = next(m['text'] for m in self.messages() if m['seq'] == ack['message_seq'])
        self.assertEqual(text, template_ack())

    def test_a_start_failure_is_said_once_and_retry_does_not_ack_twice(self):
        original = self.service._compile_work

        def broken(*args, **kwargs):
            raise PolicyError('No planner is available right now')
        self.service._compile_work = broken
        sid = self.service.submit({'text': 'Draft a letter to my landlord', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'FAILED')
        texts = [m['text'] for m in self.messages()]
        self.assertIn("I wasn't able to get that started — No planner is available right now. "
                      'You can retry it from the card above.', texts)
        view = self.service.handoff_view(self.cid, sid)
        self.assertEqual((view['phase'], view['can_retry'], view['can_stop']), ('failed_to_start', True, False))
        calls = len(self.turn.calls)
        self.service._compile_work = original
        self.service.action('/api/retry', {'id': sid})
        self.assertEqual(self.wait(sid, ('DISPATCHED', 'FAILED')), 'DISPATCHED')
        self.assertEqual(len(self.turn.calls), calls, 'retry must not decide the turn again')
        acks = [m for m in self.messages() if m['text'] == WORK['acknowledgement']]
        self.assertEqual(len(acks), 1)
        with contextlib.closing(self.service.store.connect()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM submission_acks').fetchone()[0], 1)

    def test_boot_recovery_reports_an_unstarted_handoff_once(self):
        store = self.service.store
        with store.transaction() as db:
            db.execute('INSERT INTO submissions VALUES(?,?,?,?,?,?,?)',
                       ('boot-sid', self.cid, 'Write a plan', 'PLANNING', None, None, time.time()))
            seq = db.execute('INSERT INTO messages(conversation_id,role,text,at) VALUES(?,?,?,?)',
                             (self.cid, 'assistant', 'On it.', time.time())).lastrowid
            db.execute('INSERT INTO submission_acks VALUES(?,?,?,?)', ('boot-sid', seq, 'Spring plan', time.time()))
        self.service.shutdown()
        self.services.remove(self.service)
        first = self.start()
        first.shutdown()
        self.services.remove(first)
        self.service = self.start()
        notices = [m for m in self.messages()
                   if m['text'] == "Kel closed before it could start 'Spring plan'. Use Retry on its card."]
        self.assertEqual(len(notices), 1)
        self.assertEqual(self.row('boot-sid')['state'], 'INTERRUPTED')

    def test_chat_settles_while_two_plannings_are_blocked(self):
        gate = self.block_planning()
        first = self.service.submit({'text': 'Write a garden plan', 'conversation': self.cid})
        second = self.service.submit({'text': 'Draft a watering schedule', 'conversation': self.cid})
        self.wait_for_ack(first)
        self.wait_for_ack(second)
        question = self.service.submit({'text': 'How much sun do tomatoes need?', 'conversation': self.cid})
        self.assertEqual(self.wait(question, timeout=10), 'SETTLED')
        self.assertEqual(self.row(first)['state'], 'PLANNING')
        self.assertEqual(self.row(second)['state'], 'PLANNING')
        gate.set()
        self.assertEqual(self.wait(first), 'DISPATCHED')
        self.assertEqual(self.wait(second), 'DISPATCHED')

    def set_job(self, job_id, **fields):
        with self.service.store.transaction() as db:
            data = json.loads(db.execute('SELECT data FROM jobs WHERE id=?', (job_id,)).fetchone()['data'])
            data.update(fields)
            db.execute('UPDATE jobs SET data=? WHERE id=?', (json.dumps(data), job_id))

    def test_handoff_view_phases_and_conversation_scope(self):
        gate = self.block_planning()
        sid = self.service.submit({'text': 'Write a garden plan', 'conversation': self.cid})
        self.wait_for_ack(sid)
        view = self.service.handoff_view(self.cid, sid)
        self.assertEqual((view['phase'], view['title'], view['job_id']), ('starting', 'Garden plan for spring', None))
        gate.set()
        self.wait(sid)
        job_id = self.row(sid)['job_id']
        view = self.service.handoff_view(self.cid, sid)
        self.assertEqual((view['phase'], view['can_stop'], view['total']), ('running', True, 1))
        self.set_job(job_id, state='AWAITING_USER')
        self.assertEqual(self.service.handoff_view(self.cid, sid)['phase'], 'needs_you')
        self.set_job(job_id, state='WAITING_RESOURCE')
        self.assertEqual(self.service.handoff_view(self.cid, sid)['phase'], 'waiting')
        self.set_job(job_id, state='CLOSED', verdict='UNCERTAIN')
        view = self.service.handoff_view(self.cid, sid)
        self.assertEqual((view['phase'], view['can_stop']), ('needs_look', False))
        self.set_job(job_id, state='CLOSED', verdict='VERIFIED')
        self.assertEqual(self.service.handoff_view(self.cid, sid)['phase'], 'done')
        self.set_job(job_id, state='CANCELLED', verdict='UNCERTAIN')
        self.assertEqual(self.service.handoff_view(self.cid, sid)['phase'], 'stopped')
        other = self.service.context.conversation('default')
        with self.assertRaises(PolicyError):
            self.service.handoff_view(other, sid)

    def test_turn_and_reply_models_follow_the_saved_model_preference(self):
        from kel.internal import InternalAdapter
        from kel.model_prefs import ModelPrefs
        from kel.native import NativeAdapter
        prefs = ModelPrefs(self.service.store)
        self.service.engine.adapters = {'codex': object(), 'claude': object()}
        # No preference (D-67): Kel answers on its own role model — ChatGPT Luna through Codex, at
        # low effort for the quick turn decision and the model's default level for a full reply.
        model = self.service._turn_model(self.cid)
        self.assertIsInstance(model, NativeAdapter)
        self.assertEqual((model.provider, model.model, model.timeout, model.effort),
                         ('codex', 'gpt-6-luna', 30, 'low'))
        direct = self.service._chat_model(self.cid)
        self.assertEqual((direct.provider, direct.model, direct.effort), ('codex', 'gpt-6-luna', None))
        argv = model.argv()
        self.assertEqual(argv[argv.index('-m') + 1], 'gpt-6-luna')
        self.assertIn('model_reasoning_effort="low"', argv)
        # Without Codex, the Kel role falls to the next model in its quick-answer ranking (Routing 2):
        # the closest fit for fast work that can run here — Claude Sonnet on Claude Code.
        self.service.engine.adapters = {'claude': object()}
        fallback = self.service._turn_model(self.cid)
        self.assertEqual((fallback.provider, fallback.model), ('claude', 'sonnet'))
        # With nothing ranked able to run, Kel's usual order decides (here, the connected fake).
        self.service.engine.adapters = {}
        self.assertIs(self.service._turn_model(self.cid), self.turn)
        self.service.engine.adapters = {'codex': object(), 'claude': object()}
        # D-73.3 / FN-06: the older engine default is retired; a chat's own pick is the override.
        prefs.set_conversation(self.cid, 'claude-code', None)
        model = self.service._turn_model(self.cid)
        self.assertIsInstance(model, NativeAdapter)
        self.assertEqual((model.provider, model.timeout), ('claude', 30))
        prefs.set_conversation(self.cid, 'codex', None)
        model = self.service._turn_model(self.cid)
        self.assertEqual((model.provider, model.timeout), ('codex', 30))
        direct = self.service._chat_model(self.cid)
        self.assertEqual((direct.provider, direct.timeout), ('codex', 100))
        # A preference that is not available here falls through to the next one, then the fallback.
        self.service.engine.adapters = {'claude': object()}
        self.assertEqual(self.service._turn_model(self.cid).provider, 'claude')
        self.service.engine.adapters = {}
        self.assertIs(self.service._turn_model(self.cid), self.turn)
        # The API worker, when it is the conversation's choice and connected.
        self.service.model = InternalAdapter(model='claude-sonnet-4-6', transport=lambda body, timeout: {})
        prefs.set_conversation(self.cid, 'internal', 'claude-sonnet-4-6')
        model = self.service._turn_model(self.cid)
        self.assertIsInstance(model, InternalAdapter)
        self.assertEqual((model.model, model.timeout), ('claude-sonnet-4-6', 20))
        self.assertIs(self.service._chat_model(self.cid), self.service.model)
        self.service.turn_mode = 'none'
        self.assertIsNone(self.service._turn_model(self.cid))

    def test_state_can_read_every_conversation(self):
        other = self.service.context.conversation('default')
        first = self.service.submit({'text': 'Write a garden plan', 'conversation': self.cid})
        second = self.service.submit({'text': 'Draft a watering schedule', 'conversation': other})
        self.assertEqual(self.wait(first), 'DISPATCHED')
        self.assertEqual(self.wait(second), 'DISPATCHED')
        everywhere = self.service.state('*')
        self.assertEqual(everywhere['scope'], 'all')
        self.assertEqual({j['conversation'] for j in everywhere['jobs']}, {self.cid, other})
        self.assertEqual((everywhere['messages'], everywhere['submissions']), ([], []))
        one = self.service.state(self.cid)
        self.assertEqual(one['scope'], 'conversation')
        self.assertEqual({j['conversation'] for j in one['jobs']}, {self.cid})

    def test_a_named_file_in_a_folder_is_never_a_plain_document_result(self):
        import subprocess
        from pathlib import Path
        # Outside Kel's own data folder (the service's root here): Kel refuses work in there (FN-01).
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        base = Path(folder.name)
        outside = base / 'outside'
        outside.mkdir()
        sid = self.service.submit({'text': 'Create a file named hello.txt containing hi in ' + str(outside),
                                   'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'DISPATCHED')
        contract = self.service.store.get(self.row(sid)['job_id'])['contract']
        self.assertNotEqual(contract.get('kind'), 'coding')
        self.assertEqual(contract['file_request'], {'filename': 'hello.txt', 'folder': str(outside)})
        # Inside a saved project (with a test command) the same request is real file work there.
        project = base / 'proj'
        (project / 'sub').mkdir(parents=True)
        subprocess.run(['git', 'init', str(project)], capture_output=True, check=False)
        pid = self.service.context.project('proj', str(project))
        with self.service.store.transaction() as db:
            db.execute('INSERT INTO project_tests VALUES(?,?)', (pid, json.dumps(['python', 'smoke_test.py'])))
        sid = self.service.submit({'text': 'Create a file named hello.txt containing hi in ' + str(project / 'sub'),
                                   'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'DISPATCHED')
        contract = self.service.store.get(self.row(sid)['job_id'])['contract']
        self.assertEqual(contract['kind'], 'coding')
        self.assertEqual(contract['root'], str(project.resolve()))
        self.assertNotIn('file_request', contract)

    # -- D-55: a change for running work restarts that work; it never becomes a second job ------
    AMENDED = 'Write a spring garden plan for the back yard that includes an herb bed'

    def amend_turn(self, amended=None):
        """The fake turn model: the first message is work, later "also …" messages amend it."""
        import re

        def answer(prompt, system):
            latest = prompt.split('latest message:')[-1].strip().lower()
            if latest.startswith('also'):
                found = re.findall(r'"work_id": "([^"]+)"', prompt)
                return {'action': 'amend_background_work', 'work_id': found[0] if found else None,
                        'amended_request': amended or self.AMENDED, 'title': 'Garden plan with herbs'}
            if latest.startswith('did you'):
                return {'action': 'reply', 'text': "Yes — I've added the herb bed to the plan."}
            return WORK
        self.turn.answer = answer

    def live_jobs(self):
        return [j for j in self.service.store.list_jobs()
                if j['conversation'] == self.cid and j['state'] not in ('CANCELLED', 'CANCELLING')]

    def test_a_change_for_running_work_restarts_it_instead_of_starting_a_second_job(self):
        self.amend_turn()
        first = self.service.submit({'text': 'Write me a spring garden plan for the back yard',
                                     'conversation': self.cid})
        self.assertEqual(self.wait(first), 'DISPATCHED')
        old_job = self.row(first)['job_id']
        change = self.service.submit({'text': 'also add an herb bed', 'conversation': self.cid})
        self.assertEqual(self.wait(change, ('SETTLED', 'FAILED')), 'SETTLED')
        self.assertIsNone(self.row(change)['job_id'])
        self.assertEqual(self.wait(first), 'DISPATCHED')
        deadline = time.time() + 20
        while self.row(first)['job_id'] == old_job and time.time() < deadline:
            time.sleep(.02)
        new_job = self.row(first)['job_id']
        self.assertNotEqual(new_job, old_job)
        self.assertEqual(self.service.store.get(old_job)['state'], 'CANCELLED')
        # Exactly one live job, carrying the amended request, behind the one original card.
        self.assertEqual([j['id'] for j in self.live_jobs()], [new_job])
        self.assertEqual(self.service.store.get(new_job)['contract']['request'], self.AMENDED)
        self.assertEqual(self.row(first)['text'], self.AMENDED)
        with contextlib.closing(self.service.store.connect()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM submission_acks').fetchone()[0], 1)
        restart = [m['text'] for m in self.messages() if m['text'].startswith('Restarting')]
        self.assertEqual(restart, ["Restarting “Garden plan with herbs” with that change — I stopped the "
                                   "earlier run, and I'll post the result here once it's been checked."])
        view = self.service.handoff_view(self.cid, first)
        self.assertEqual((view['job_id'], view['title']), (new_job, 'Garden plan with herbs'))
        # The replaced job is not separate work anywhere the person or the turn model looks.
        self.assertNotIn(old_job, [j['id'] for j in self.service.state(self.cid)['jobs']])
        running = handoff.running_work(self.service.store, self.cid)
        self.assertEqual([r['work_id'] for r in running], [first])
        # The person's first message is the restarted job's source message; nothing was duplicated.
        users = [m for m in self.messages() if m['role'] == 'user']
        self.assertEqual([u['job_id'] for u in users], [new_job, None])

    def test_a_change_while_the_work_is_still_starting_is_planned_in_before_any_job_exists(self):
        self.amend_turn()
        gate = self.block_planning()
        first = self.service.submit({'text': 'Write me a spring garden plan for the back yard',
                                     'conversation': self.cid})
        self.wait_for_ack(first)
        change = self.service.submit({'text': 'also add an herb bed', 'conversation': self.cid})
        self.assertEqual(self.wait(change, ('SETTLED', 'FAILED')), 'SETTLED')
        self.assertIn("Restarting “Garden plan with herbs” with that change before it gets going. "
                      "I'll post the result here once it's been checked.", [m['text'] for m in self.messages()])
        gate.set()
        self.assertEqual(self.wait(first), 'DISPATCHED')
        jobs = [j for j in self.service.store.list_jobs() if j['conversation'] == self.cid]
        self.assertEqual(len(jobs), 1, 'an amendment must never create a second job')
        self.assertEqual(jobs[0]['contract']['request'], self.AMENDED)

    def test_a_change_for_finished_work_is_new_work_with_the_whole_request(self):
        self.amend_turn()
        first = self.service.submit({'text': 'Write me a spring garden plan for the back yard',
                                     'conversation': self.cid})
        self.assertEqual(self.wait(first), 'DISPATCHED')
        old_job = self.row(first)['job_id']
        self.set_job(old_job, state='CLOSED', verdict='VERIFIED')
        change = self.service.submit({'text': 'also add an herb bed', 'conversation': self.cid})
        self.assertEqual(self.wait(change), 'DISPATCHED')
        self.assertEqual(self.service.store.get(old_job)['state'], 'CLOSED')
        new_job = self.row(change)['job_id']
        self.assertEqual(self.service.store.get(new_job)['contract']['request'], self.AMENDED)
        self.assertFalse(any(m['text'].startswith('Restarting') for m in self.messages()))

    def test_a_reply_that_claims_a_change_says_nothing_changed(self):
        self.amend_turn()
        first = self.service.submit({'text': 'Write me a spring garden plan for the back yard',
                                     'conversation': self.cid})
        self.assertEqual(self.wait(first), 'DISPATCHED')
        job = self.row(first)['job_id']
        question = self.service.submit({'text': 'did you add the herb bed?', 'conversation': self.cid})
        self.assertEqual(self.wait(question), 'SETTLED')
        self.assertEqual(self.messages()[-1]['text'], NO_CHANGE_WITH_WORK)
        self.assertEqual(self.row(first)['job_id'], job)
        self.assertEqual(len(self.live_jobs()), 1)

    # -- CH-3: the composer's Stop really stops a reply that is still being answered -----------
    def blocking_turn(self, answer):
        """A turn model that holds its answer until released and reports the Stop it was given."""
        release, entered, seen = threading.Event(), threading.Event(), {}

        class Blocking:
            def execute(inner, prompt, system=None, images=None, cancel=None):
                seen['cancel'] = cancel
                entered.set()
                release.wait(20)
                return {'outcome': 'SUCCESS', 'text': json.dumps(answer)}
        self.service.model = Blocking()
        self.addCleanup(release.set)
        return release, entered, seen

    def test_stop_drops_a_reply_still_being_written_and_says_so_once(self):
        release, entered, seen = self.blocking_turn(REPLY)
        sid = self.service.submit({'text': 'How much sun do tomatoes need?', 'conversation': self.cid})
        self.assertTrue(entered.wait(10))
        out = self.service.action('/api/cancel', {'id': sid, 'conversation': self.cid})
        self.assertTrue(out['cancelled'])
        self.assertTrue(seen['cancel'].is_set(), 'the in-flight model call is told to stop')
        release.set()
        time.sleep(.3)  # let the stopped planner finish and (not) write its answer
        self.assertEqual(self.row(sid)['state'], 'CANCELLED')
        texts = [m['text'] for m in self.messages()]
        self.assertNotIn(REPLY['text'], texts, 'a stopped reply must never be posted later')
        self.assertEqual(texts.count('You stopped this reply.'), 1)
        self.assertEqual(texts[-1], 'You stopped this reply.')
        # A second Stop, or a Stop for a settled reply, changes nothing.
        self.assertFalse(self.service.action('/api/cancel', {'id': sid, 'conversation': self.cid})['cancelled'])
        with self.assertRaises(PolicyError):
            self.service.action('/api/cancel', {'id': sid, 'conversation': 'another'})

    def test_stop_while_deciding_starts_no_work(self):
        release, entered, _ = self.blocking_turn(WORK)
        sid = self.service.submit({'text': 'Write me a garden plan', 'conversation': self.cid})
        self.assertTrue(entered.wait(10))
        self.assertTrue(self.service.action('/api/cancel', {'id': sid, 'conversation': self.cid})['cancelled'])
        release.set()
        time.sleep(.3)
        self.assertEqual(self.row(sid)['state'], 'CANCELLED')
        self.assertEqual([j for j in self.service.store.list_jobs() if j['conversation'] == self.cid], [])
        with contextlib.closing(self.service.store.connect()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM submission_acks').fetchone()[0], 0)
        self.assertNotIn(WORK['acknowledgement'], [m['text'] for m in self.messages()])

    def test_stop_never_cancels_handed_off_work(self):
        sid = self.service.submit({'text': 'Write me a garden plan', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'DISPATCHED')
        out = self.service.action('/api/cancel', {'id': sid, 'conversation': self.cid})
        self.assertEqual((out['cancelled'], out['handed_off']), (False, True))
        job = self.service.store.get(self.row(sid)['job_id'])
        self.assertNotIn(job['state'], ('CANCELLED', 'CANCELLING'))
        self.assertNotIn('You stopped this reply.', [m['text'] for m in self.messages()])

    # -- CH-2: model truth ------------------------------------------------------------------------
    def test_a_reply_says_once_when_it_did_not_come_from_the_chosen_model(self):
        from kel.model_prefs import ModelPrefs
        self.turn.label, self.turn.provider = 'Claude', 'claude-code'
        ModelPrefs(self.service.store).set_conversation(self.cid, 'deepseek', 'deepseek-flash')
        first = self.service.submit({'text': 'How much sun do tomatoes need?', 'conversation': self.cid})
        self.assertEqual(self.wait(first), 'SETTLED')
        reply = self.service.state(self.cid)['messages'][-1]
        self.assertEqual(reply['text'], REPLY['text'] + "\n\nUsed Claude — DeepSeek isn't available right now.")  # Routing 2 §5.6: no DeepSeek key here
        self.assertEqual(reply['meta']['answered_by']['label'], 'Claude')
        self.assertEqual(reply['meta']['fallback_from']['provider'], 'deepseek')
        second = self.service.submit({'text': 'And how much sun do peppers need?', 'conversation': self.cid})
        self.assertEqual(self.wait(second), 'SETTLED')
        again = self.service.state(self.cid)['messages'][-1]
        self.assertEqual(again['text'], REPLY['text'], 'the line is said once per conversation')
        self.assertEqual(again['meta']['fallback_from']['provider'], 'deepseek')

    def test_every_answer_records_who_answered_it(self):
        self.turn.label = 'Claude'
        sid = self.service.submit({'text': 'Write me a garden plan', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'DISPATCHED')
        ack = next(m for m in self.service.state(self.cid)['messages'] if m['text'] == WORK['acknowledgement'])
        self.assertEqual(ack['meta'], {'answered_by': {'label': 'Claude', 'model': None, 'provider': None}})

    def test_the_model_list_says_what_kel_can_actually_answer_with(self):
        self.service.engine.adapters = {'claude': object()}
        listing = {row['id']: row for row in self.service._model_action({'action': 'get'})['providers']}
        self.assertFalse(listing['deepseek']['available'])
        self.assertEqual(listing['deepseek']['note'], 'API key needed')  # Routing 2 §5.6: honest key state
        self.assertFalse(any(option['available'] for option in listing['deepseek']['options']))
        self.assertFalse(listing['codex']['available'], 'no Codex adapter is registered here')
        providers = {row['provider']: row for row in
                     self.service.action('/api/providers', {'action': 'list'})['providers']}
        self.assertFalse(providers['deepseek']['available'])
        self.assertEqual(providers['deepseek']['available_note'], 'API key needed')

    # -- ST-04 / ST-23 / CH-10: start-up and idle cost ---------------------------------------------
    def test_a_reserved_chat_is_created_on_its_first_message_only_once(self):
        import uuid
        reserved = str(uuid.uuid4())
        self.assertEqual(self.service._project_of(reserved), 'default', 'a reserved chat is not an error')
        with self.assertRaises(PolicyError):
            self.service._project_of('not-a-conversation')
        for _ in range(2):
            self.assertEqual(self.service.action('/api/conversation', {'project': 'default', 'id': reserved}),
                             {'id': reserved, 'project_id': 'default'})
        rows = [c for c in self.service.state(reserved)['conversations'] if c['id'] == reserved]
        self.assertEqual(len(rows), 1)
        with self.assertRaises(PolicyError):
            self.service.action('/api/conversation', {'project': 'default', 'id': 'x; drop table'})

    def test_conversation_counts_come_from_one_grouped_read(self):
        empty = self.service.context.conversation('default')
        sid = self.service.submit({'text': 'Write me a garden plan', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'DISPATCHED')
        counts = {row['id']: row for row in self.service.conversations()['conversations']}
        self.assertEqual((counts[empty]['message_count'], counts[empty]['job_count']), (0, 0))
        self.assertGreaterEqual(counts[self.cid]['message_count'], 2)
        self.assertEqual(counts[self.cid]['job_count'], 1)

    def test_an_idle_engine_says_so_and_does_not_renew_its_lease_every_pass(self):
        calls = []
        original = self.service.store.controller_lease
        self.service.store.controller_lease = lambda *a, **k: (calls.append(a), original(*a, **k))[1]
        self.addCleanup(setattr, self.service.store, 'controller_lease', original)
        for _ in range(10):
            self.assertFalse(self.service.engine.tick())
        self.assertEqual(calls, [], 'the 120 s lease is renewed about every 30 s, not every pass')
        self.service.engine._lease_renewed -= 31
        self.service.engine.tick()
        self.assertEqual(len(calls), 1)
        sid = self.service.submit({'text': 'Write me a garden plan', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'DISPATCHED')
        self.assertTrue(self.service.engine.tick(), 'a READY job keeps supervision at full pace')

    # -- CP-2: polls read only what they show -----------------------------------------------------
    def test_state_and_why_never_read_the_whole_event_log(self):
        sid = self.service.submit({'text': 'Write me a garden plan', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'DISPATCHED')
        job = self.row(sid)['job_id']
        route = {'selected': 'codex', 'why': 'your chosen model', 'chain': ['codex']}
        self.service.store.claim(job, 'document', provider='codex', route=route)

        def whole_log(*args, **kwargs):
            raise AssertionError('the whole event log was read')
        self.service.store.events = whole_log
        self.addCleanup(vars(self.service.store).pop, 'events', None)
        state = self.service.state(self.cid)
        self.assertEqual(state['routes'][job]['route'], route)
        self.assertEqual(self.service.state('*')['routes'][job]['provider'], 'codex')
        why = self.service._model_action({'action': 'why', 'conversation': self.cid})
        self.assertEqual((why['job'], why['selected']), (job, 'codex'))
        self.assertTrue(self.service._work(self.cid)['work']['jobs'][0]['last_at'])

    def test_the_card_poll_does_not_fingerprint_the_project(self):
        from kel.continuation import Continuation
        sid = self.service.submit({'text': 'Write me a garden plan', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'DISPATCHED')
        original = Continuation.plan_resume

        def refuse(*args, **kwargs):
            raise AssertionError('plan_resume (fingerprint + evidence) ran on a poll')
        Continuation.plan_resume = refuse
        self.addCleanup(setattr, Continuation, 'plan_resume', original)
        self.assertEqual(self.service.handoff_view(self.cid, sid)['phase'], 'running')
        self.assertEqual(len(self.service._work(self.cid)['work']['jobs']), 1)

    def test_the_handoff_tables_and_hot_path_indexes_are_one_ledger_migration(self):
        with contextlib.closing(self.service.store.connect()) as db:
            names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type IN ('index','table')")}
            ledger = db.execute('SELECT name FROM schema_migrations WHERE version=31').fetchone()
        for name in ('submission_acks', 'handoff_notices', 'handoff_restarts', 'messages_by_conversation',
                     'submissions_by_conversation', 'submissions_by_job', 'approvals_by_status', 'runs_by_job'):
            self.assertIn(name, names)
        self.assertEqual(ledger['name'], 'v2-handoff-and-conversation-indexes')
        self.assertFalse(handoff.ensure_schema(self.service.store), 'applied once')

    # -- CH-9: a rename reaches the engine -----------------------------------------------------------
    def test_a_rename_is_kept_by_the_engine_and_survives_the_first_message(self):
        import uuid
        out = self.service.action('/api/conversation-title', {'conversation': self.cid, 'title': '  Spring   garden '})
        self.assertEqual(out, {'id': self.cid, 'title': 'Spring garden'})
        sid = self.service.submit({'text': 'How much sun do tomatoes need?', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'SETTLED')
        title = next(c['title'] for c in self.service.state(self.cid)['conversations'] if c['id'] == self.cid)
        self.assertEqual(title, 'Spring garden')
        reserved = str(uuid.uuid4())
        self.service.action('/api/conversation-title', {'conversation': reserved, 'title': 'Taxes'})
        self.assertIn((reserved, 'Taxes'), [(c['id'], c['title']) for c in self.service.state(reserved)['conversations']])
        for bad in ('', '   ', 'x' * 121, None):
            with self.assertRaises(PolicyError):
                self.service.action('/api/conversation-title', {'conversation': self.cid, 'title': bad})
        with self.assertRaises(PolicyError):
            self.service.action('/api/conversation-title', {'conversation': 'not-a-chat', 'title': 'x'})

    def test_follow_up_posts_one_notice_per_stalled_state(self):
        sid = self.service.submit({'text': 'Write a garden plan', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'DISPATCHED')
        job_id = self.row(sid)['job_id']
        self.assertEqual(handoff.follow_up(self.service.store), 0)
        self.set_job(job_id, state='WAITING_RESOURCE')
        self.assertEqual(handoff.follow_up(self.service.store), 1)
        self.assertEqual(handoff.follow_up(self.service.store), 0)
        notices = [m['text'] for m in self.messages() if m['text'].startswith('An update on')]
        self.assertEqual(len(notices), 1)
        self.assertIn('Garden plan for spring', notices[0])
        running = handoff.running_work(self.service.store, self.cid)
        self.assertEqual(running[0]['title'], 'Garden plan for spring')
        self.assertEqual(running[0]['state'], 'WAITING_RESOURCE')


class PublishLeadInTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def job(self):
        checks = [{'kind': 'contains', 'value': 'ACCEPT'}, {'kind': 'min_chars', 'value': 6}]
        return self.store.create({'request': 'Write ACCEPT', 'handoff': {'submission_id': 's1', 'ack_seq': 1,
                                                                          'title': 'The ACCEPT note'},
                                  'milestones': [{'id': 'a', 'objective': 'Write ACCEPT', 'filename': 'a.md',
                                                  'checks': checks}]})

    def result(self, job, text, event):
        run = self.store.claim(job, 'a')
        self.store.enqueue_result(event, run['id'], run['epoch'], {'outcome': 'SUCCESS', 'text': text})
        self.store.consume()

    def test_verified_handoff_result_names_the_work(self):
        job = self.job()
        self.result(job, 'ACCEPT valid artifact', 'e1')
        self.store.verify(job, 'a')
        text, created = self.store.publish(job)
        self.assertTrue(created)
        self.assertTrue(text.startswith("Here's the ACCEPT note — it passed its checks.\n\nACCEPT valid artifact"))

    def test_a_document_result_never_reads_as_a_created_file(self):
        checks = [{'kind': 'contains', 'value': 'ACCEPT'}, {'kind': 'min_chars', 'value': 6}]
        job = self.store.create({'request': 'Create a file named hello.txt containing ACCEPT in C:\\notes',
                                 'handoff': {'submission_id': 's2', 'ack_seq': 1, 'title': 'hello.txt'},
                                 'file_request': {'filename': 'hello.txt', 'folder': 'C:\\notes'},
                                 'milestones': [{'id': 'a', 'objective': 'Write ACCEPT', 'filename': 'a.md',
                                                 'checks': checks}]})
        self.result(job, 'ACCEPT valid artifact', 'e1')
        self.store.verify(job, 'a')
        text, _ = self.store.publish(job)
        self.assertTrue(text.startswith("Here's the content for hello.txt \u2014 it passed its checks. "
                                        'I did not create the file in C:\\notes'))
        self.assertIn('ACCEPT valid artifact', text)

    def test_the_lead_in_reads_naturally(self):
        from kel.core import natural_title
        self.assertEqual(natural_title('Garden plan for spring'), 'your garden plan for spring')
        self.assertEqual(natural_title('The ACCEPT note'), 'the ACCEPT note')
        self.assertEqual(natural_title('Your weekly budget'), 'your weekly budget')
        self.assertEqual(natural_title('README update'), 'your README update')
        self.assertEqual(natural_title('iOS release notes'), 'your iOS release notes')
        self.assertEqual(natural_title('Kel'), 'your Kel')
        self.assertEqual(natural_title(''), 'your result')

    def test_unverified_handoff_result_has_no_lead_in(self):
        job = self.job()
        for attempt in range(4):
            self.result(job, 'wrong', 'e%d' % attempt)
            self.store.verify(job, 'a')
            self.store.assess(job)
        self.assertEqual(self.store.get(job)['state'], 'CLOSED')
        text, _ = self.store.publish(job)
        self.assertNotIn('passed its checks', text)
        self.assertNotIn("Here's", text)


if __name__ == '__main__':
    unittest.main()
