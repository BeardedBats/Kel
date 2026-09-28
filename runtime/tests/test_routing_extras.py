"""Routing extras (ROUTING_2.md "Still open"): Codex replies stream, per-model overlays, subscription
quota with pace, local-only work.

No model is called: the Codex app-server is a scripted fake, the CLI outputs are the shapes recorded
live on this PC (Claude Code 2.1.283 `rate_limit_event`, Codex 0.157.1 rollout `rate_limits` and
app-server `item/agentMessage/delta`), and the engine runs fixtures.
"""
import contextlib
import json
import os
import queue
import tempfile
import time
import unittest
from pathlib import Path

from kel import overlays, quota, role_models, router, staff, task_routing, usage
from kel.core import NO_ROUTE_WAIT, Store, encode
from kel.engine import Engine
from kel.native import FixtureAdapter, NativeAdapter
from kel.router import Candidate, select

HOUR = 3600.0

# Recorded live (Claude Code 2.1.283, `-p --output-format stream-json --verbose`), 2026-09-28.
CLAUDE_STREAM = '\n'.join(json.dumps(line) for line in (
    {'type': 'system', 'subtype': 'init', 'session_id': 's1', 'model': 'claude-opus-5-5'},
    {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'ok'}]}, 'session_id': 's1'},
    {'type': 'rate_limit_event', 'rate_limit_info': {
        'status': 'allowed_warning', 'resetsAt': 1790625000, 'rateLimitType': 'five_hour', 'utilization': 0.99,
        'isUsingOverage': False, 'surpassedThreshold': 0.9,
        'unifiedWindows': {'five_hour': {'utilization': 0.99, 'resetsAt': 1790625000},
                           'seven_day': {'utilization': 0.88, 'resetsAt': 1790658000}}},
     'session_id': 's1'},
    {'type': 'result', 'subtype': 'success', 'is_error': False, 'result': 'ok', 'session_id': 's1',
     'total_cost_usd': 0.0135, 'usage': {'input_tokens': 2, 'cache_creation_input_tokens': 1667,
                                         'cache_read_input_tokens': 531, 'output_tokens': 4}},
))
# Recorded live (Codex 0.157.1 rollout file, `token_count` event), 2026-09-28.
CODEX_ROLLOUT_LIMITS = {'limit_id': 'codex', 'limit_name': None,
                        'primary': {'used_percent': 14.0, 'window_minutes': 10080, 'resets_at': 1791047426},
                        'secondary': None, 'credits': {'has_credits': False, 'unlimited': False, 'balance': '0'},
                        'individual_limit': None, 'spend_control_reached': None, 'plan_type': 'prolite',
                        'rate_limit_reached_type': None}


class TempStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ['CODEX_HOME'] = str(Path(self.tmp.name) / 'codex-home')
        os.environ.pop('KEL_WORKFORCE', None)
        self.store = Store(Path(self.tmp.name) / 'data')
        staff.ensure_schema(self.store)

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def put_state(self, adapter, state):
        with self.store.transaction() as db:
            db.execute('INSERT INTO providers VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',
                       (adapter, encode(state)))


# ---- 1. Codex replies stream through the app-server ------------------------------------------------

class FakeConnection:
    """Answers thread/start and turn/start, then plays scripted notifications."""

    def __init__(self, notifications, fail_on=None):
        self.events = queue.Queue()
        self.calls, self.sent = [], []
        self.notifications, self.fail_on = notifications, fail_on
        self.closed = False

    def call(self, method, params, timeout=25):
        self.calls.append((method, params))
        if method == self.fail_on:
            raise RuntimeError("{'message': \"The 'gpt-6-luna' model requires a newer version of Codex\"}")
        if method in ('thread/start', 'thread/resume'):
            return {'thread': {'id': params.get('threadId') or 'th-1'}}
        if method == 'turn/start':
            for note in self.notifications:
                self.events.put(note)
            return {'turn': {'id': 'tu-1'}}
        return {}

    def send(self, message):
        self.sent.append(message)

    def close(self):
        self.closed = True


def delta(text, item='m1'):
    return {'method': 'item/agentMessage/delta', 'params': {'threadId': 'th-1', 'turnId': 'tu-1',
                                                             'itemId': item, 'delta': text}}


class CodexStreamingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def adapter(self, connection):
        adapter = NativeAdapter('codex', Path(self.tmp.name) / 'ws', Path(self.tmp.name) / 'logs',
                                model='gpt-6-luna', effort='low')
        adapter.connection_factory = lambda _adapter: connection
        return adapter

    def test_words_arrive_as_codex_writes_them_and_the_turn_keeps_its_tokens_and_limits(self):
        connection = FakeConnection([
            delta('one '), delta('two '), delta('three'),
            {'method': 'item/completed', 'params': {'threadId': 'th-1', 'item': {
                'type': 'agentMessage', 'id': 'm1', 'text': 'one two three'}}},
            {'method': 'thread/tokenUsage/updated', 'params': {'threadId': 'th-1', 'tokenUsage': {
                'total': {'inputTokens': 900, 'cachedInputTokens': 0, 'outputTokens': 70},
                'last': {'inputTokens': 100, 'cachedInputTokens': 40, 'outputTokens': 7,
                         'reasoningOutputTokens': 0}}}},
            {'method': 'account/rateLimits/updated', 'params': {'rateLimits': {
                'primary': {'usedPercent': 14, 'windowDurationMins': 10080, 'resetsAt': 1791047426},
                'planType': 'prolite'}}},
            {'method': 'turn/completed', 'params': {'threadId': 'th-1', 'turn': {'id': 'tu-1', 'status': 'completed'}}},
        ])
        seen = []
        result = self.adapter(connection).execute('Count to three.', on_text=seen.append)
        self.assertEqual(seen, ['one ', 'one two ', 'one two three'])
        self.assertEqual((result['outcome'], result['text'], result['session_id']), ('SUCCESS', 'one two three', 'th-1'))
        self.assertTrue(result['streamed'])
        self.assertEqual(result['model_used'], 'gpt-6-luna')
        self.assertEqual(usage.normalize(result)['processed'], 67)  # this turn only: 100 − 40 cached + 7
        self.assertEqual(result['rate_limits']['windows'][0]['label'], 'weekly')
        start = dict(connection.calls)['thread/start']
        self.assertEqual((start['sandbox'], start['approvalPolicy'], start['model']), ('read-only', 'never', 'gpt-6-luna'))
        self.assertEqual(dict(connection.calls)['turn/start']['effort'], 'low')
        self.assertTrue(connection.closed)

    def test_a_refused_model_is_a_failure_with_the_runtimes_words_and_is_remembered(self):
        connection = FakeConnection([], fail_on='thread/start')
        adapter = self.adapter(connection)
        refused = []
        adapter.on_refusal = lambda error, version: refused.append(error)
        result = adapter.execute('Hi', on_text=lambda words: None)
        self.assertEqual(result['outcome'], 'FAILED')
        self.assertIn('requires a newer version of Codex', result['error'])
        self.assertEqual(len(refused), 1)

    def test_a_failed_turn_keeps_its_message(self):
        connection = FakeConnection([
            {'method': 'error', 'params': {'threadId': 'th-1', 'willRetry': False,
                                           'error': {'message': 'Usage limit reached'}}},
            {'method': 'turn/completed', 'params': {'threadId': 'th-1', 'turn': {'id': 'tu-1', 'status': 'failed',
                                                                                   'error': {'message': 'Usage limit reached'}}}},
        ])
        result = self.adapter(connection).execute('Hi', on_text=lambda words: None)
        self.assertEqual((result['outcome'], result['error']), ('FAILED', 'Usage limit reached'))

    def test_an_app_server_that_cannot_start_leaves_the_answer_to_exec(self):
        adapter = NativeAdapter('codex', Path(self.tmp.name) / 'ws', Path(self.tmp.name) / 'logs')

        def broken(_adapter):
            raise OSError('no codex')
        adapter.connection_factory = broken
        self.assertIsNone(adapter._codex_stream('Hi', 'r1', None, None, lambda words: None))

    def test_the_app_server_runs_with_execs_limits(self):
        adapter = NativeAdapter('codex', Path(self.tmp.name) / 'ws', Path(self.tmp.name) / 'logs')
        args = adapter.appserver_argv()
        for flag in ('approval_policy="never"', 'sandbox_mode="read-only"', 'web_search="disabled"', 'notify=[]',
                     'mcp_servers={}', 'model_reasoning_effort="low"'):
            self.assertIn(flag, args)
        self.assertIn('shell_tool', args)
        self.assertIn('app-server', args)

    def test_only_a_streamed_reply_uses_the_app_server(self):
        adapter = NativeAdapter('codex', Path(self.tmp.name) / 'ws', Path(self.tmp.name) / 'logs')
        adapter.connection_factory = lambda _adapter: self.fail('staff work never streams')
        adapter._execute = lambda *args: {'outcome': 'SUCCESS', 'text': 'x'}
        self.assertEqual(adapter.execute('Hi')['text'], 'x')
        # A run the broker watches (process observer) keeps exec even with words wanted.
        self.assertEqual(adapter.execute('Hi', process_observer=lambda *a: None, on_text=lambda w: None)['text'], 'x')


# ---- 3. Subscription quota ---------------------------------------------------------------------------

class QuotaSourceTests(TempStore):
    def test_claude_stream_json_carries_the_plan_limits(self):
        adapter = NativeAdapter('claude', Path(self.tmp.name) / 'ws', Path(self.tmp.name) / 'logs')
        self.assertIn('stream-json', adapter.argv())
        self.assertIn('--verbose', adapter.argv())
        result = adapter.parse(CLAUDE_STREAM)
        self.assertEqual((result['outcome'], result['text']), ('SUCCESS', 'ok'))
        windows = {w['id']: w for w in result['rate_limits']['windows']}
        self.assertEqual((windows['five_hour']['used'], windows['seven_day']['used']), (99.0, 88.0))
        self.assertEqual(windows['five_hour']['label'], '5-hour')

    def test_a_rejected_claude_plan_is_blocked(self):
        snap = quota.from_claude({'status': 'rejected', 'rateLimitType': 'five_hour', 'resetsAt': 2_000_000_000})
        self.assertTrue(snap['blocked'])
        self.assertEqual(snap['windows'][0]['used'], 100.0)

    def test_codex_exec_limits_come_from_its_own_session_log(self):
        home = Path(self.tmp.name) / 'codex-home'
        day = time.localtime()
        folder = home / 'sessions' / ('%04d' % day.tm_year) / ('%02d' % day.tm_mon) / ('%02d' % day.tm_mday)
        folder.mkdir(parents=True)
        (folder / 'rollout-2026-09-28T13-59-01-th-42.jsonl').write_text(
            json.dumps({'type': 'session_meta', 'payload': {}}) + '\n' +
            json.dumps({'type': 'event_msg', 'payload': {'type': 'token_count', 'rate_limits': CODEX_ROLLOUT_LIMITS}}) + '\n',
            encoding='utf-8')
        snap = quota.codex_rollout_limits('th-42', home=home)
        self.assertEqual(snap['windows'][0], {'id': 'primary', 'label': 'weekly', 'used': 14.0, 'minutes': 10080,
                                              'resets_at': 1791047426.0})
        self.assertEqual(snap['plan'], 'prolite')
        self.assertIsNone(quota.codex_rollout_limits('missing', home=home))

    def test_a_recorded_call_records_its_plan_limits_on_every_adapter_of_the_runtime(self):
        now = time.time()
        snap = quota.from_claude({'status': 'allowed', 'unifiedWindows': {
            'five_hour': {'utilization': 0.4, 'resetsAt': now + HOUR}}})
        usage.record(self.store, 'c1', kind='reply', adapter='claude', model='claude-opus-5-5',
                     result={'outcome': 'SUCCESS', 'rate_limits': snap})
        states = self.store.provider_states()
        for adapter in ('claude', 'claude-code', 'claude-web'):
            self.assertEqual(states[adapter]['quota'], 60.0)
            self.assertEqual(states[adapter]['quota_source'], 'Claude Code rate_limit_event')


class TelemetryTests(TempStore):
    def test_the_codex_poll_records_windows_and_the_subscription_cost(self):
        from kel.telemetry import refresh_codex
        now = time.time()

        class Poll:
            def quota(self):
                return {'rateLimitsByLimitId': {'codex': {'primary': {'usedPercent': 14, 'windowDurationMins': 10080,
                                                                      'resetsAt': now + 90 * HOUR},
                                                          'planType': 'prolite'}}}

            def close(self):
                pass
        out = refresh_codex(self.store, connection_factory=lambda folder, logs: Poll())
        self.assertEqual(out['remaining'], 86.0)
        state = self.store.provider_states()['codex']
        self.assertEqual((state['quota'], state['cost'], state['planType']), (86.0, 0, 'prolite'))
        self.assertEqual(state['quota_windows'][0]['label'], 'weekly')


class QuotaStandingTests(TempStore):
    def test_a_used_up_plan_says_until_when_and_comes_back_at_its_reset(self):
        now = 1_800_000_000.0
        snap = quota.from_claude({'status': 'rejected', 'rateLimitType': 'five_hour', 'resetsAt': now + HOUR,
                                  'unifiedWindows': {'five_hour': {'utilization': 1.0, 'resetsAt': now + HOUR},
                                                     'seven_day': {'utilization': 0.5, 'resetsAt': now + 90 * HOUR}}})
        state = quota.apply({}, snap, now)
        view = quota.standing(state, 'claude', now)
        self.assertEqual(view['level'], 'exhausted')
        self.assertIn("your Claude plan's 5-hour limit is used up until", view['reason'])
        later = quota.standing(state, 'claude', now + HOUR + 1)
        self.assertEqual((later['level'], later['left']), ('ok', 50.0))  # the 5-hour window reset

    def test_nearly_used_up_and_on_pace_to_run_out_are_low(self):
        now = 1_800_000_000.0
        codex = lambda used: {'primary': {'usedPercent': used, 'windowDurationMins': 300, 'resetsAt': now + 4 * HOUR}}
        state = quota.apply({}, quota.from_codex(codex(92)), now)
        view = quota.standing(state, 'codex', now)
        self.assertEqual(view['level'], 'low')
        self.assertIn('8% of its 5-hour limit left', view['reason'])
        # 60% → 80% in 20 minutes: on pace to run out long before the reset in 4 hours.
        state = quota.apply({}, quota.from_codex(codex(60)), now)
        state = quota.apply(state, quota.from_codex(codex(80)), now + 1200)
        view = quota.standing(state, 'codex', now + 1200)
        self.assertEqual(view['level'], 'low')
        self.assertIn('on pace to use up its 5-hour limit', view['reason'])
        self.assertEqual(view['windows'][0]['pace']['per_hour'], 60.0)
        # A slow burn is fine.
        state = quota.apply({}, quota.from_codex(codex(60)), now)
        state = quota.apply(state, quota.from_codex(codex(61)), now + 1200)
        self.assertEqual(quota.standing(state, 'codex', now + 1200)['level'], 'ok')

    def test_unknown_stays_unknown(self):
        self.assertEqual(quota.standing({}, 'claude')['level'], 'unknown')
        self.assertIsNone(quota.left({}))

    def test_expire_rewrites_a_reset_plan(self):
        now = time.time()
        snap = quota.from_codex({'primary': {'usedPercent': 100, 'resetsAt': now - 5}})
        self.put_state('codex', quota.apply({}, snap, now - 60))
        self.assertEqual(self.store.provider_states()['codex']['quota'], 0.0)
        self.assertEqual(quota.expire(self.store), 1)
        self.assertIsNone(self.store.provider_states()['codex']['quota'])

    def test_settings_see_both_plans(self):
        now = time.time()
        quota.observe(self.store, quota.from_codex({'primary': {'usedPercent': 30, 'windowDurationMins': 10080,
                                                                'resetsAt': now + 50 * HOUR}}))
        plans = {p['runtime']: p for p in quota.plans(self.store)}
        self.assertEqual(plans['codex']['level'], 'ok')
        self.assertIn('Weekly: 30% used', plans['codex']['summary'])
        self.assertEqual(plans['claude']['level'], 'unknown')
        self.assertIn('Not reported yet', plans['claude']['summary'])
        listing = role_models.listing(self.store, {'codex', 'claude'})
        self.assertEqual({p['runtime'] for p in listing['plans']}, {'codex', 'claude'})
        overview = task_routing.overview(self.store, {'codex', 'claude'})
        self.assertEqual(len(overview['plans']), 2)


class QuotaRoutingTests(TempStore):
    def observe(self, runtime, used, reset_in=4 * HOUR):
        now = time.time()
        if runtime == 'codex':
            snap = quota.from_codex({'primary': {'usedPercent': used, 'windowDurationMins': 300,
                                                 'resetsAt': now + reset_in}})
        else:
            snap = quota.from_claude({'status': 'rejected' if used >= 100 else 'allowed',
                                      'rateLimitType': 'five_hour', 'resetsAt': now + reset_in,
                                      'unifiedWindows': {'five_hour': {'utilization': used / 100.0,
                                                                       'resetsAt': now + reset_in}}})
        quota.observe(self.store, snap)

    def test_a_used_up_plan_is_unrunnable_with_the_plain_reason(self):
        self.observe('claude', 100)
        ranked = task_routing.ranking(self.store, 'review', adapters={'codex', 'claude'})
        opus = next(e for e in ranked if e['model'] == 'claude-opus-5-5')
        self.assertFalse(opus['runnable'])
        self.assertIn("your Claude plan's 5-hour limit is used up until", opus['why'])
        # The role's own resolution steps past it and says why.
        role_models.set_role(self.store, 'builder', 'PREFERRED', 'claude-opus-5-5')
        binding = role_models.resolve(self.store, 'builder', adapters={'codex', 'claude'})
        self.assertEqual(binding['model'], 'codex')
        self.assertIn("Claude Opus 5.5 can't run right now: your Claude plan's 5-hour limit", binding['why'])
        options = {o['id']: o for o in role_models.listing(self.store, {'codex', 'claude'})['roles'][3]['model_options']}
        self.assertFalse(options['claude-opus-5-5']['available'])

    def test_a_nearly_used_up_plan_is_ranked_lower_but_never_past_nicks_choice(self):
        self.observe('codex', 95)
        role_models.set_role(self.store, 'utility', 'AUTOMATIC')
        ranked = task_routing.ranking(self.store, 'utility', adapters={'codex', 'claude'})
        runnable = [e for e in ranked if e['runnable']]
        luna = next(e for e in runnable if e['model'] == 'gpt-6-luna')
        self.assertTrue(luna.get('quota_low'))
        self.assertIn('moved down: your ChatGPT plan (Codex) has 5% of its 5-hour limit left', luna['why'])
        self.assertEqual(runnable[0]['adapter'], 'claude')
        # Nick's Preferred model stays first even when its plan is low.
        role_models.set_role(self.store, 'utility', 'PREFERRED', 'gpt-6-luna')
        ranked = task_routing.ranking(self.store, 'utility', adapters={'codex', 'claude'})
        self.assertEqual(ranked[0]['model'], 'gpt-6-luna')

    def test_the_router_ranks_a_low_plan_after_the_others_and_excludes_a_used_up_one(self):
        cheap = Candidate('codex', cost=0, quota=5, quota_low=True)
        other = Candidate('claude', cost=1, quota=80)
        route = select([cheap, other])
        self.assertEqual(route['selected'], 'claude')
        self.assertEqual(route['quota_low'], ['codex'])
        self.assertIn('nearly used up', route['why'])
        self.assertEqual(select([cheap, other], prefer='codex')['selected'], 'codex')
        self.assertEqual(select([cheap])['selected'], 'codex')  # low is never excluded
        with self.assertRaises(Exception) as caught:
            select([Candidate('codex', quota=0)])
        self.assertIn('quota exhausted', str(caught.exception))

    def test_the_engines_quota_input_forgets_a_window_that_reset(self):
        now = time.time()
        state = quota.apply({}, quota.from_claude({'status': 'rejected', 'rateLimitType': 'five_hour',
                                                   'resetsAt': now + 60}), now)
        self.assertEqual(quota.candidate_fields(state, 'claude-code', now)['quota'], 0.0)
        self.assertIsNone(quota.candidate_fields(state, 'claude-code', now + 61)['quota'])
        self.assertEqual(quota.candidate_fields({'quota': 0}, 'deepseek'), {'quota': 0, 'quota_low': False})


# ---- 2. Per-model overlays ------------------------------------------------------------------------------

class OverlayTests(TempStore):
    def test_the_registry_is_empty_and_changes_nothing(self):
        self.assertEqual(overlays.REGISTRY, {})
        self.assertEqual(overlays.apply('Answer.', 'codex', 'gpt-6-luna'), ('Answer.', None))
        binding = role_models.resolve(self.store, 'kel', adapters={'codex', 'claude'})
        self.assertNotIn('overlay', binding)
        self.assertNotIn('overlay', binding['asked'])

    def test_an_entry_is_appended_as_a_subordinate_note_and_recorded_with_its_version(self):
        registry = {('codex', 'openai'): {'version': 3, 'verbosity': 'concise', 'literal': True}}
        self.assertEqual(overlays.lookup('codex', 'gpt-6-luna', registry)['key'], 'codex:openai')
        self.assertIsNone(overlays.lookup('claude', 'claude-opus-5-5', registry))
        exact = dict(registry)
        exact[('codex', 'gpt-6-luna')] = {'version': 1, 'effort_match': True}
        self.assertEqual(overlays.lookup('codex', 'gpt-6-luna', exact)['key'], 'codex:gpt-6-luna')
        prompt, record = overlays.apply('Answer as Kel.', 'codex', 'gpt-6-luna', registry)
        self.assertTrue(prompt.startswith('Answer as Kel.'))
        self.assertIn('subordinate: it never overrides anything above', prompt)
        self.assertIn('Keep the answer brief', prompt)
        self.assertEqual(record, {'key': 'codex:openai', 'version': 3})
        saved = dict(overlays.REGISTRY)
        overlays.REGISTRY.update(registry)
        try:
            binding = role_models.resolve(self.store, 'kel', adapters={'codex', 'claude'})
            self.assertEqual(binding['asked']['overlay'], {'key': 'codex:openai', 'version': 3})
            adapter = NativeAdapter('codex', Path(self.tmp.name) / 'ws', Path(self.tmp.name) / 'logs', model='gpt-6-luna')
            asked = []
            adapter._execute = lambda prompt, *rest: asked.append(prompt) or {'outcome': 'SUCCESS', 'text': 'x'}
            result = adapter.execute('Hi')
            self.assertIn('Model note', asked[0])
            self.assertEqual(result['overlay'], {'key': 'codex:openai', 'version': 3})
            # The coding bridge does not apply overlays, so nothing is recorded for it.
            coding = role_models.resolve(self.store, 'builder', adapters={'codex-code'}, purpose='code')
            self.assertNotIn('overlay', coding['asked'])
        finally:
            overlays.REGISTRY.clear()
            overlays.REGISTRY.update(saved)


# ---- 4. Local-only work ---------------------------------------------------------------------------------

class LocalOnlyTests(TempStore):
    def test_nothing_local_is_reported_plainly_and_a_running_runtime_is_named(self):
        def refused(url):
            raise OSError('connection refused')
        view = router.local_models(fetch=refused)
        self.assertEqual((view['found'], view['usable']), ([], []))
        self.assertEqual(view['note'], 'No local models on this computer: every model Kel can use runs in the cloud.')
        ollama = router.local_models(fetch=lambda url: {'models': [{'name': 'llama3.2'}]} if '11434' in url else None)
        self.assertEqual(ollama['found'], [{'runtime': 'Ollama', 'models': ['llama3.2']}])
        self.assertIn('Ollama is running here (1 model), but Kel cannot run local models yet', ollama['note'])
        self.assertEqual(ollama['usable'], [])

    def test_the_block_names_the_cloud_runtimes_in_plain_words(self):
        words = router.local_only_block(['codex', 'claude', 'codex-code'], local={'note': 'No local models here.'})
        self.assertEqual(words, 'This work is marked local-only, so Kel may not send it to a model in the cloud '
                                '(Codex and Claude Code run there). No local models here.')
        self.assertTrue(router.is_local_only({'local_only': True}))
        self.assertTrue(router.is_local_only({'requirements': ['local_only']}))
        self.assertFalse(router.is_local_only({}))

    def test_the_ranking_excludes_every_cloud_model(self):
        ranked = task_routing.ranking(self.store, 'writing', adapters={'codex', 'claude'}, local_only=True)
        self.assertFalse(any(e['runnable'] for e in ranked))
        luna = next(e for e in ranked if e['model'] == 'gpt-6-luna')
        self.assertIn('runs in the cloud, and this work is local-only', luna['why'])

    def test_local_only_work_waits_with_the_plain_reason_and_never_reaches_a_cloud_model(self):
        router._LOCAL_CACHE.update(at=time.time(), value={'found': [], 'usable': [],
                                                           'note': 'No local models on this computer.'})
        self.addCleanup(router._LOCAL_CACHE.clear)
        cloud = FixtureAdapter(output='## Result\nsent to the cloud')
        text = 'Summarise my notes'
        job = self.store.create({'request': text, 'local_only': True, 'milestones': [
            {'id': 'd', 'objective': text, 'filename': 'd.md', 'depends_on': [],
             'checks': [{'kind': 'min_chars', 'value': 5}]}]})
        engine = Engine(self.store, {'codex': cloud})
        try:
            for _ in range(20):
                engine.tick()
                if self.store.get(job)['state'] == 'WAITING_RESOURCE':
                    break
                time.sleep(.02)
        finally:
            engine.close()
        record = self.store.get(job)
        self.assertEqual(record['state'], 'WAITING_RESOURCE')
        self.assertTrue(record['route_block'].startswith(NO_ROUTE_WAIT))
        self.assertIn('marked local-only', record['route_block'])
        self.assertIn('(Codex runs there)', record['route_block'])
        self.assertEqual(cloud.calls, 0)

    def test_local_only_work_still_runs_on_a_local_model(self):
        local = FixtureAdapter(output='## Result\nDone locally.')
        text = 'Summarise my notes'
        job = self.store.create({'request': text, 'local_only': True, 'milestones': [
            {'id': 'd', 'objective': text, 'filename': 'd.md', 'depends_on': [],
             'checks': [{'kind': 'min_chars', 'value': 5}]}]})
        engine = Engine(self.store, {'fixture': local})
        try:
            deadline = time.time() + 20
            while time.time() < deadline and self.store.get(job)['state'] != 'CLOSED':
                engine.tick()
                time.sleep(.02)
        finally:
            engine.close()
        self.assertEqual(self.store.get(job)['state'], 'CLOSED')
        self.assertEqual(local.calls, 1)


if __name__ == '__main__':
    unittest.main()
