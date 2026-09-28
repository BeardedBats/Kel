"""The live audit's engine findings (LIVE-2..LIVE-13, D-74) and the functional audit's FN-03/05/06/07.

Fake runtimes only; no provider is ever called. The CLI output samples are the real shapes the
installed Claude Code 2.1.283 and Codex 0.142.5 printed for one tiny web search (2026-09-28).
"""
import contextlib
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import unittest.mock
from pathlib import Path

from kel import needs_answer, office, research, scoping, staff
from kel.continuation import Continuation
from kel.core import (INTERRUPTED_NOTE, NO_ROUTE_WAIT, STUCK_WAIT, Store, encode, explain_failure,
                      result_lead, route_wait_kind, verification_lines)
from kel.engine import Engine
from kel.native import FixtureAdapter, NativeAdapter
from kel.router import classify, explicit_new_project, greenfield_intent

sys.path.insert(0, str(Path(__file__).parent))
from test_office import writing  # noqa: E402

CLAUDE_WEB = json.dumps({
    'type': 'result', 'subtype': 'success', 'is_error': False, 'session_id': 'b7280996-1f05-47ed-a1f5-88b062776d6a',
    'result': 'The latest stable Python version is 3.14.7, released on August 5, 2026.\n\nSources:\n'
              '- [Download Python | Python.org](https://www.python.org/downloads/)',
    'usage': {'input_tokens': 4, 'cache_creation_input_tokens': 2873, 'cache_read_input_tokens': 12299,
              'output_tokens': 160, 'server_tool_use': {'web_search_requests': 0, 'web_fetch_requests': 0}},
    'modelUsage': {'claude-sonnet-5': {'outputTokens': 160, 'webSearchRequests': 0},
                   'claude-haiku-4-5-20251001': {'outputTokens': 163, 'webSearchRequests': 1}},
    'total_cost_usd': 0.0387378})
CODEX_WEB = '\n'.join(json.dumps(line) for line in (
    {'type': 'thread.started', 'thread_id': '01a0e884-2ed6-7583-a340-35d16686e3ed'},
    {'type': 'turn.started'},
    {'type': 'item.started', 'item': {'id': 'item_0', 'type': 'web_search', 'query': '', 'action': {'type': 'other'}}},
    {'type': 'item.completed', 'item': {'id': 'item_0', 'type': 'web_search', 'query': 'latest stable Python version official',
                                        'action': {'type': 'search', 'query': 'latest stable Python version official'}}},
    {'type': 'item.completed', 'item': {'id': 'item_1', 'type': 'agent_message',
                                        'text': 'The latest stable Python version is Python 3.14.7, per Python.org: '
                                                'https://www.python.org/downloads/release/python-3147/'}},
    {'type': 'turn.completed', 'usage': {'input_tokens': 16807, 'cached_input_tokens': 2432, 'output_tokens': 74,
                                         'reasoning_output_tokens': 38}}))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ.pop('KEL_WORKFORCE', None)
        os.environ['CODEX_HOME'] = str(Path(self.tmp.name) / 'codex-home')
        self.store = Store(Path(self.tmp.name) / 'data')
        staff.ensure_schema(self.store)

    def job(self, contract=None, budget=12):
        return self.store.create(contract or writing('Write a haiku about autumn'), budget=budget)

    def events(self, job):
        with contextlib.closing(self.store.connect()) as db:
            return db.execute('SELECT COUNT(*) FROM events WHERE aggregate_id=?', (job,)).fetchone()[0]


# ---- LIVE-2 / D-74.2 ----------------------------------------------------------------------------

class ProjectRoutingTests(unittest.TestCase):
    def test_this_project_is_never_a_new_project(self):
        for text in ('In this project, add a power function', 'make this project build again',
                     'build the app in my project', 'fix the tests in the current project so the project builds'):
            self.assertFalse(greenfield_intent(text), text)
            self.assertNotEqual(classify(text).get('greenfield'), True, text)

    def test_building_something_new_is_still_greenfield(self):
        self.assertTrue(greenfield_intent('I want to create a little app that shows the weather'))
        self.assertTrue(classify('create a new separate project: a weather app')['greenfield'])

    def test_only_an_explicit_request_asks_for_a_new_project(self):
        self.assertTrue(explicit_new_project('create a new separate project: a weather app'))
        self.assertTrue(explicit_new_project('Build me a new app for tracking plants'))
        self.assertTrue(explicit_new_project('start it from scratch in its own folder'))
        self.assertFalse(explicit_new_project('I want to create a little app that shows the weather'))
        self.assertFalse(explicit_new_project('add a new function to this project'))


# ---- FN-03 --------------------------------------------------------------------------------------

class StallTests(Base):
    def test_an_assessment_that_changes_nothing_writes_nothing(self):
        job = self.job()
        self.store.assess(job)
        before = self.events(job)
        for _ in range(20):
            self.store.assess(job)
        self.assertEqual(self.events(job), before)

    def test_a_step_waiting_on_a_dead_step_does_not_keep_the_job_ready(self):
        contract = {'request': 'Two parts', 'milestones': [
            {'id': 'a', 'objective': 'A', 'filename': 'a.md', 'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 5}]},
            {'id': 'b', 'objective': 'B', 'filename': 'b.md', 'depends_on': ['a'], 'checks': [{'kind': 'min_chars', 'value': 5}]}]}
        job = self.job(contract)
        with self.store.transaction() as db:
            record = self.store._get(db, job)
            record['milestones']['a'].update(state='EXHAUSTED', attempts=2)
            self.store._save(db, record, 'test.setup')
        self.store.assess(job)
        self.assertEqual(self.store.get(job)['state'], 'CLOSED')
        self.assertEqual(self.store.get(job)['verdict'], 'FAILED')

    def test_a_job_out_of_tries_stops_and_asks_nick(self):
        job = self.job(budget=1)
        engine = Engine(self.store, {'fixture': FixtureAdapter()})
        try:
            engine.tick()
            engine.tick()
            record = self.store.get(job)
            self.assertEqual(record['state'], 'WAITING_RESOURCE')
            self.assertEqual(route_wait_kind(record['route_block']), 'stuck')
            before = self.events(job)
            for _ in range(10):
                engine.tick()
            self.assertEqual(self.events(job), before, 'a stuck job writes nothing on each pass')
        finally:
            engine.close()
        brief = Continuation(self.store).resume_brief(job)
        self.assertTrue(brief['needs_you'])
        self.assertIn('Try again', brief['next'])
        question = needs_answer.question(self.store, self.store.get(job), brief['why'], brief['next'])
        self.assertEqual(question['kind'], 'out_of_tries')
        self.assertEqual([o['id'] for o in question['options']], ['continue'])
        self.assertEqual(office.state_of(self.store, self.store.get(job))[0], 'needs_you')
        # Try again gives it more tries.
        Continuation(self.store).execute_resume(job, 'main')
        again = self.store.get(job)
        self.assertEqual(again['state'], 'READY')
        self.assertGreaterEqual(again['budget'] - again['spent'] - again['reserved'], 2)


# ---- LIVE-3 -------------------------------------------------------------------------------------

class NeedsYouTests(Base):
    def test_an_interrupted_step_carries_a_marker_and_asks(self):
        job = self.job()
        self.store.claim(job, 'document', provider='fixture', model='fixture')
        self.store.recover_abandoned(now=time.time() + 600)
        record = self.store.get(job)
        milestone = record['milestones']['document']
        self.assertTrue(milestone['interrupted'])
        self.assertEqual(milestone['error'], INTERRUPTED_NOTE)
        brief = Continuation(self.store).resume_brief(job)
        self.assertEqual((brief['needs_you'], brief['wait']), (True, 'interrupted'))
        question = needs_answer.question(self.store, record)
        self.assertEqual(question['kind'], 'interrupted')
        self.assertEqual(question['options'][0], {'id': 'continue', 'label': 'Try again'})
        self.assertIn('the app restarted', explain_failure(record))
        self.assertNotIn('Worker broker', explain_failure(record))

    def test_no_route_at_all_is_needs_you_with_a_plain_reason(self):
        contract = research.compile_research('Search the web for the latest Python release.')
        job = self.job(contract)
        engine = Engine(self.store, {'fixture': FixtureAdapter()})
        try:
            engine.tick()
        finally:
            engine.close()
        record = self.store.get(job)
        self.assertEqual(record['state'], 'WAITING_RESOURCE')
        self.assertTrue(record['route_block'].startswith(NO_ROUTE_WAIT))
        self.assertIn('search the web', record['route_block'])
        brief = Continuation(self.store).resume_brief(job)
        self.assertTrue(brief['needs_you'])
        self.assertIn('Staff & models', brief['next'])
        question = needs_answer.question(self.store, record, brief['why'], brief['next'])
        self.assertEqual(question['kind'], 'no_model')
        self.assertEqual([o['id'] for o in question['options']], ['continue', 'open_staff'])
        self.assertEqual(question['options'][1]['action'], 'open_settings')
        explained = explain_failure(record)
        why = explained.split('Why: ', 1)[1].split('\n', 1)[0]
        self.assertTrue(why.strip())
        self.assertNotIn('{', why)

    def test_an_empty_router_block_never_gives_a_blank_why(self):
        job = self.job()
        self.store.wait_for_route(job, 'No eligible route: {}')
        why = explain_failure(self.store.get(job)).split('Why: ', 1)[1].split('\n', 1)[0]
        self.assertTrue(why.strip())
        self.assertEqual(route_wait_kind('No eligible route: {}'), 'no_route')
        self.assertEqual(route_wait_kind("No eligible route: {'codex': ['quota exhausted']}"), 'waiting')

    def test_staff_rows_mark_a_model_that_cannot_do_the_role(self):
        from kel import role_models
        from kel.core import PolicyError
        role_models.set_role(self.store, 'builder', 'PREFERRED', 'deepseek-flash')
        rows = {row['role']: row for row in role_models.listing(self.store, {'codex', 'codex-code', 'deepseek'})['roles']}
        builder = rows['builder']
        self.assertFalse(builder['available'])
        self.assertIn("can't change code", builder['note'])
        options = {o['id']: o for o in builder['model_options']}
        self.assertFalse(options['deepseek-flash']['available'])
        self.assertTrue(options['gpt-6-astra']['available'] or 'Codex' in (options['gpt-6-astra']['note'] or ''))
        with self.assertRaises(PolicyError):
            role_models.set_role(self.store, 'builder', 'FIXED', 'deepseek-flash')
        discovery = rows['discovery']
        self.assertEqual(discovery['purpose'], 'web')


# ---- LIVE-5 / D-74.1 ------------------------------------------------------------------------------

class WebResearchTests(Base):
    def test_the_runtimes_are_asked_for_their_own_web_search(self):
        codex = NativeAdapter('codex', Path(self.tmp.name) / 'w', Path(self.tmp.name) / 'l', web=True)
        claude = NativeAdapter('claude', Path(self.tmp.name) / 'w', Path(self.tmp.name) / 'l', web=True)
        plain = NativeAdapter('codex', Path(self.tmp.name) / 'w', Path(self.tmp.name) / 'l')
        try:
            self.assertIn('web_search="live"', codex.argv())
            self.assertIn('web_search="disabled"', plain.argv())
            args = claude.argv()
            self.assertEqual(args[args.index('--tools') + 1], 'WebSearch,WebFetch')
        except RuntimeError:
            self.skipTest('the CLIs are not installed here')

    def test_parsing_counts_real_searches(self):
        claude = NativeAdapter('claude', Path(self.tmp.name) / 'w', Path(self.tmp.name) / 'l', web=True).parse(CLAUDE_WEB)
        self.assertEqual(claude['searches'], 1)
        self.assertEqual(claude['model_used'], 'claude-sonnet-5', 'the helper that only searched did not write it')
        codex = NativeAdapter('codex', Path(self.tmp.name) / 'w', Path(self.tmp.name) / 'l', web=True).parse(CODEX_WEB)
        self.assertEqual(codex['searches'], 1)
        self.assertEqual(codex['queries'], ['latest stable Python version official'])

    def test_an_answer_counts_only_with_a_search_receipt_and_links(self):
        parsed = NativeAdapter('codex', Path(self.tmp.name) / 'w', Path(self.tmp.name) / 'l', web=True).parse(CODEX_WEB)
        settled = research.settle_cli_research(self.store, 'run-1', dict(parsed, text=parsed['text'] + ' ' * 10 +
                                                                         'More detail follows here for length.'), 'codex')
        self.assertEqual(settled['outcome'], 'SUCCESS')
        self.assertTrue(research.check_research_evidence(self.store, 'run-1', settled['text']))
        unsearched = research.settle_cli_research(self.store, 'run-2', dict(parsed, searches=0), 'codex')
        self.assertEqual(unsearched['outcome'], 'FAILED')
        unlinked = research.settle_cli_research(self.store, 'run-3', dict(parsed, text='x' * 100), 'codex')
        self.assertEqual(unlinked['outcome'], 'FAILED')

    def test_discovery_runs_on_a_coding_runtime_without_an_api_key(self):
        from kel.role_models import adapter_for
        self.assertEqual(adapter_for('claude-sonnet', 'web', {'claude', 'claude-web'})[0], 'claude-web')
        self.assertEqual(adapter_for('claude-sonnet', 'web', {'research'})[0], 'research')
        self.assertEqual(adapter_for('gpt-6-astra', 'web', {'codex', 'codex-web'})[0], 'codex-web')


# ---- LIVE-6 -------------------------------------------------------------------------------------

class PlannerModel:
    provider, model = 'codex', 'gpt-6-luna'

    def __init__(self, answer):
        self.answer = answer
        self.prompts = []

    def execute(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return {'outcome': 'SUCCESS', 'text': json.dumps(self.answer)}


class ResearchPlanTests(Base):
    def test_independent_parts_become_parallel_research_steps(self):
        from kel.commander import Commander
        model = PlannerModel({'independent': True, 'parts': [
            {'question': 'What is the latest stable release of Python?'},
            {'question': 'What is the latest stable release of Node.js?'}]})
        contract = research.compile_research('Compare the latest Python and Node.js releases.', Commander(model))
        self.assertEqual(contract['compiler'], 'research-plan-v1')
        parts = [m for m in contract['milestones'] if m['id'] != contract['final_milestone']]
        self.assertEqual(len(parts), 2)
        self.assertTrue(all(m['required_capabilities'] == ['web_research'] for m in parts))
        decision = staff.plan_job(self.store, contract, contract['request'])
        self.assertEqual(decision['tier'], 'D3')
        self.assertIn('Plan a web research job', model.prompts[0])

    def test_one_question_stays_one_step(self):
        from kel.commander import Commander
        model = PlannerModel({'independent': False, 'parts': [{'question': 'Latest Python release?'}]})
        contract = research.compile_research('What is the latest Python release?', Commander(model))
        self.assertEqual(len(contract['milestones']), 1)
        self.assertEqual(contract['required_capabilities'], ['web_research'])

    def test_history_advice_never_lowers_research_below_a_specialist(self):
        from kel import staffing
        features = {'complexity': 0, 'decomposability': 0, 'sequentiality': 1, 'uncertainty': 2, 'novelty': 1,
                    'risk': 0, 'domain_breadth': 1, 'tool_requirements': 1, 'consequence_of_failure': 0,
                    'user_facing': 0, 'release_proximity': 0}
        base = staffing.decide(features)['tier']
        with unittest.mock.patch.object(staffing, '_mission_tiers',
                                        return_value=({'m%d' % i: base for i in range(20)}, {})):
            advice = staffing.outcome_advice(self.store, features, minimum=3)
        self.assertNotEqual(advice['advised_tier'], 'D0')


# ---- LIVE-8 / FN-07 -----------------------------------------------------------------------------

class ScopingFitTests(Base):
    def test_a_small_change_is_not_asked_who_will_use_it(self):
        prompts = [q['prompt'] for q in scoping._bank('code', 'Fix the password check in auth.py', greenfield=False)]
        self.assertNotIn('Who will use it?', prompts)
        self.assertIn('Where should secrets live?', prompts)
        new = [q['prompt'] for q in scoping._bank('code', 'Build me a weather app', greenfield=True)]
        self.assertIn('Who will use it?', new)

    def test_a_security_word_alone_is_not_a_reason_to_ask_first(self):
        guess = scoping.estimate(self.store, 'Write a short note explaining what an API token is', 'writing')
        self.assertIn('security_boundary', guess['flags'])
        self.assertLess(scoping.TIER_RANK[guess['size_tier']], scoping.TIER_RANK['D2'])
        self.assertIsNone(scoping.consider(self.store, 'Write a short note explaining what an API token is',
                                           'writing', {}))


# ---- LIVE-9 -------------------------------------------------------------------------------------

class TurnEffortTests(unittest.TestCase):
    def test_the_turn_reports_its_own_reasoning_level(self):
        import queue
        from kel.appserver import CodexConnection as AppServer
        server = AppServer.__new__(AppServer)
        server.workspace = '.'
        server.events = queue.Queue()
        answers = {'model/list': {'data': []},
                   'thread/start': {'thread': {'id': 't1'}, 'model': 'gpt-6-astra', 'reasoningEffort': 'medium'},
                   'turn/start': {'turn': {'id': 'u1'}}}
        server.call = lambda method, params: answers[method]
        server.events.put({'method': 'turn/completed', 'params': {'threadId': 't1', 'turn': {'status': 'completed'}}})
        seen = []
        server.run('do it', on_event=seen.append, effort='low', model='gpt-6-astra')
        levels = [(e['method'], e['params'].get('reasoningEffort')) for e in seen if e['method'] in ('kel/thread', 'kel/turn')]
        self.assertEqual(levels, [('kel/thread', 'medium'), ('kel/turn', 'low')])


# ---- LIVE-10 / LIVE-11 / LIVE-12 -----------------------------------------------------------------

class WordsTests(Base):
    def test_an_instruction_title_reads_as_done(self):
        self.assertEqual(result_lead('Add power function with test'),
                         'Done: add power function with test. It passed its checks.')
        self.assertEqual(result_lead('Garden plan'), "Here's your garden plan — it passed its checks.")

    def test_verification_lines_have_no_bullets_or_verdict(self):
        job = self.job()
        run = self.store.claim(job, 'document', provider='codex', model='gpt-6-astra')
        self.store.enqueue_result('r', run['id'], run['epoch'], {'outcome': 'SUCCESS', 'text': 'A finished haiku.'})
        self.store.consume()
        self.store.verify(job, 'document')
        self.store.assess(job)
        lines = verification_lines(self.store.get(job))
        self.assertTrue(lines)
        self.assertFalse(any(line.startswith('•') for line in lines))
        self.assertNotIn('Uncertain', lines)
        self.assertIn('Done by GPT-6 Astra in Codex.', lines)

    def test_a_restart_with_a_change_is_not_you_stopped_this(self):
        job = self.job()
        self.store.control(job, 'cancel')
        from kel import handoff
        handoff.ensure_schema(self.store)
        with self.store.transaction() as db:
            db.execute('INSERT INTO handoff_restarts VALUES(?,?,?,?)', ('sub-1', job, 'sub-2', time.time()))
        state, line, _needs, _why, _next = office.state_of(self.store, self.store.get(job))
        self.assertEqual((state, line), ('stopped', 'Restarted with your change.'))

    def test_undo_does_not_move_the_finish_time(self):
        contract = writing('Write a haiku about autumn')
        contract['staffing'] = staff.plan_job(self.store, contract)
        job = self.store.create(contract)
        run = self.store.claim(job, 'document', provider='fixture', model='fixture')
        self.store.enqueue_result('r', run['id'], run['epoch'], {'outcome': 'SUCCESS', 'text': 'A finished haiku.'})
        self.store.consume()
        with self.store.transaction() as db:
            record = self.store._get(db, job)
            record['state'] = 'CANCELLED'
            self.store._save(db, record, 'job.cancel')
        first = office.items(self.store)['items'][0]['finished_at']
        time.sleep(.05)
        with self.store.transaction() as db:
            self.store._save(db, self.store._get(db, job), 'changes.undone', {'files': 2, 'folders': 1})
        item = office.items(self.store)['items'][0]
        self.assertEqual(item['finished_at'], first)
        self.assertEqual(item['undone']['files'], 2)
        self.assertIn('verdict', item)  # the row itself tells passed from unconfirmed work
        self.assertIsNone(item['application'], 'writing work has no application')

    def test_undo_removes_only_the_folders_the_apply_made(self):
        from kel.apply_changes import _note_created_dirs, _remove_created_dirs
        root = Path(self.tmp.name) / 'project'
        (root / 'kept').mkdir(parents=True)
        vault = Path(self.tmp.name) / 'vault'
        vault.mkdir()
        _note_created_dirs(vault, root, root / 'src' / 'deep')
        (root / 'src' / 'deep').mkdir(parents=True)
        self.assertEqual(_remove_created_dirs(vault, root), 2)
        self.assertFalse((root / 'src').exists())
        self.assertTrue((root / 'kept').exists())


# ---- LIVE-13 ------------------------------------------------------------------------------------

class StoppedUsageTests(Base):
    def test_a_stopped_run_records_what_it_used(self):
        from kel.usage import job_spend
        job = self.job()
        run = self.store.claim(job, 'document', provider='codex', model='gpt-6-astra')
        self.store.acknowledge_stop(run['id'], run['epoch'], result={
            'outcome': 'CANCELLED', 'usage': {'input_tokens': 1000, 'cached_input_tokens': 0, 'output_tokens': 50},
            'wall_ms': 4000})
        spend = job_spend(self.store, job)
        self.assertEqual(spend['calls'], 1)
        self.assertEqual(spend['processed'], 1050)
        self.assertEqual(spend['wall_ms'], 4000)

    def test_a_lost_run_records_its_time(self):
        from kel.usage import job_spend
        job = self.job()
        run = self.store.claim(job, 'document', provider='codex', model='gpt-6-astra')
        self.assertTrue(self.store.record_lost_usage(run['id']))
        self.assertEqual(job_spend(self.store, job)['calls'], 1)


# ---- LIVE-7 / LIVE-8 / FN-05 / FN-06 / D-74.4 at the service ------------------------------------

class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ.pop('ANTHROPIC_API_KEY', None)
        os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none')
        from kel.service import Service
        self.service = Service(Path(self.tmp.name) / 'data')
        self.cid = self.service.context.conversation('default')

    def tearDown(self):
        with contextlib.suppress(Exception):
            self.service.shutdown()
        with contextlib.suppress(Exception):
            self.tmp.cleanup()

    def test_messages_with_details_are_listed_since_a_seq(self):
        first = self.service.messages_since(0)
        with self.service.store.transaction() as db:
            db.execute('INSERT INTO messages(conversation_id,role,text,at,meta) VALUES(?,?,?,?,?)',
                       (self.cid, 'assistant', 'plain', time.time(), None))
            db.execute('INSERT INTO messages(conversation_id,role,text,at,meta) VALUES(?,?,?,?,?)',
                       (self.cid, 'assistant', 'card', time.time(), encode({'kind': 'scoping', 'scoping': 's1'})))
        later = self.service.messages_since(first['latest'])
        self.assertEqual([item['conversation_id'] for item in later['items']], [self.cid])
        self.assertEqual(later['latest'], first['latest'] + 2)

    def _open_scope(self):
        sid = 'sub-scope'
        with self.service.store.transaction() as db:
            db.execute('INSERT INTO submissions VALUES(?,?,?,?,?,?,?)',
                       (sid, self.cid, 'Build a plumbing website', 'PLANNING', None, None, time.time()))
        packet = {'project': {'id': 'default', 'root': None}, 'files': []}
        plan = {'questions': scoping._bank('code', 'Build a plumbing website', greenfield=True), 'summary': None,
                'why': 'size', 'estimate': {'tier': 'D2', 'flags': []}, 'threshold': 'D2'}
        return scoping.open_scope(self.service, sid, self.cid, 'Build a plumbing website', packet, 'coding', True,
                                  {'title': 'Plumbing website'}, None, plan, 'code')

    def test_not_now_cancels_the_scoping_and_starts_nothing(self):
        scoping_id = self._open_scope()
        out = office.dismiss(self.service.store, scoping_id, service=self.service)
        self.assertEqual((out['dismissed'], out['scoping']), (True, True))
        self.assertEqual(scoping.view(self.service.store, scoping_id)['state'], 'dismissed')
        self.assertEqual(scoping.office_items(self.service.store), [])
        self.assertEqual(self.service.store.list_jobs(), [])
        again = scoping.action(self.service, {'action': 'dismiss', 'id': scoping_id})
        self.assertTrue(again['already'])
        from kel.activity import timeline
        self.assertTrue(any(e['type'] == 'scoping.dismissed' for e in timeline(self.service.store)['entries']))

    def test_a_refused_request_is_recorded(self):
        self.service._record_refusal('sub-x', self.cid, "I can't write into Kel's own data folder.")
        self.service._record_refusal('sub-x', self.cid, "I can't write into Kel's own data folder.")
        from kel.activity import timeline
        rows = [e for e in timeline(self.service.store)['entries'] if e['type'] == 'request.refused']
        self.assertEqual(len(rows), 1)

    def test_kel_has_one_model_source(self):
        from kel import role_models
        from kel.core import PolicyError
        from kel.model_prefs import ModelPrefs
        self.assertEqual(self.service.kel_model_source(), 'role_default')
        # D-73.3: the older default is retired — it never decides Kel's model, even when present.
        ModelPrefs(self.service.store).set_default('claude-code', 'claude-native')
        self.assertEqual(self.service.kel_model_source(), 'role_default')
        role_models.set_role(self.service.store, 'kel', 'PREFERRED', 'gpt-6-luna')
        self.assertEqual(self.service.kel_model_source(), 'staff_role')
        self.service._model_action({'action': 'set_role', 'role': 'kel', 'mode': 'PREFERRED', 'model': 'gpt-6-luna'})
        self.assertIsNone(ModelPrefs(self.service.store).default(), 'writing the Kel role clears the older default')
        with self.assertRaises(PolicyError):
            self.service._model_action({'action': 'set_default', 'choice': {'provider': 'claude-code', 'model': 'claude-native'}})
        self.service._model_action({'action': 'set_default', 'choice': {'model': 'gpt-6-astra'}})
        self.assertEqual(role_models.setting(self.service.store, 'kel')['model'], 'gpt-6-astra')
        # The per-chat override takes Kel-role catalog ids.
        self.service._model_action({'action': 'set_conversation', 'conversation': self.cid,
                                    'choice': {'model': 'claude-opus-5-5'}})
        view = self.service.kel_model_view(self.cid)
        self.assertEqual((view['kel']['model'], view['in_effect'], view['conversation_override']['label']),
                         ('gpt-6-astra', 'conversation', 'Claude Opus 5.5'))
        listing = self.service._model_action({'action': 'get', 'conversation': self.cid})
        self.assertEqual(listing['kel_model']['in_effect'], 'conversation')

    def test_vetting_search_results_name_their_chat(self):
        from kel.search import Search
        from kel.vetting import ensure_schema
        ensure_schema(self.service.store)
        with self.service.store.transaction() as db:
            db.execute("INSERT INTO vetting_sessions(id,conversation_id,template,topic,created,updated) "
                       "VALUES('v1',?,'t','Plumbing website scope',1,1)", (self.cid,))
        found = Search(self.service.store).run('Plumbing')['vetting']
        self.assertEqual([(r['id'], r['conversation_id']) for r in found], [('v1', self.cid)])

    def test_settled_means_nothing_moving(self):
        self.assertTrue(self.service.settled())
        self.service.store.create(writing('Write a haiku'), conversation=self.cid)
        self.assertFalse(self.service.settled())


class IdleExitTests(unittest.TestCase):
    def test_the_engine_exits_once_settled_and_unattached(self):
        from kel import service as kel_service
        tmp = tempfile.mkdtemp()
        saved = dict(os.environ)
        try:
            os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none',
                              KEL_IDLE_EXIT_SECONDS='1')
            os.environ.pop('ANTHROPIC_API_KEY', None)
            data = Path(tmp) / 'data'
            thread = threading.Thread(target=kel_service.serve, args=(str(data), 0), daemon=True)
            thread.start()
            deadline = time.time() + 30
            while not (data / 'desktop-session.json').exists() and time.time() < deadline:
                time.sleep(.05)
            self.assertTrue((data / 'desktop-session.json').exists())
            thread.join(timeout=30)
            self.assertFalse(thread.is_alive(), 'the engine left on its own')
            self.assertFalse((data / 'desktop-session.json').exists(), 'no stale descriptor for the next launch')
        finally:
            os.environ.clear()
            os.environ.update(saved)


if __name__ == '__main__':
    unittest.main()
