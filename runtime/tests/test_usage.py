"""Routing 2 §5.2 — measured tokens, wall-clock and cost for every staffed call, from what each
runtime itself reports (shapes copied from real outputs on this PC: a Claude Code `-p` result in
Kel's native log, the Codex 0.142.5 binary's exec and app-server event schemas). No provider is
called; unknown stays unknown and an unpriced model is never free.
"""
import os
import tempfile
import time
import unittest
from pathlib import Path

from kel import staff, task_routing, usage
from kel.core import Store

# The numbers of a real Claude Code result (Data/engine/native-logs, 2026-09-27).
CLAUDE_RESULT = {'outcome': 'SUCCESS', 'cost_usd': 0.051532, 'runtime_ms': 19981,
                 'model_used': 'claude-opus-4-8[1m]',
                 'usage': {'input_tokens': 2, 'cache_creation_input_tokens': 1857,
                           'cache_read_input_tokens': 0, 'output_tokens': 1282}}


class NormalizeTests(unittest.TestCase):
    def test_claude_counts_cache_creation_as_input_and_keeps_its_cost(self):
        out = usage.normalize(CLAUDE_RESULT)
        self.assertEqual((out['input'], out['cached'], out['output'], out['processed']), (1859, 0, 1282, 3141))
        self.assertEqual((out['cost_usd'], out['cost_basis'], out['runtime_ms']), (0.051532, 'reported', 19981))

    def test_codex_exec_input_includes_the_cached_part(self):
        out = usage.normalize({'usage': {'input_tokens': 1200, 'cached_input_tokens': 800, 'output_tokens': 90,
                                         'reasoning_output_tokens': 40}}, model='gpt-6-luna')
        self.assertEqual((out['input'], out['cached'], out['output'], out['reasoning'], out['processed']),
                         (400, 800, 90, 40, 490))
        self.assertEqual(out['cost_basis'], 'estimated')
        self.assertAlmostEqual(out['cost_usd'], (400 * 0.10 + 800 * 0.01 + 90 * 0.50) / 1e6)

    def test_an_unpriced_model_is_unknown_not_free(self):
        out = usage.normalize({'usage': {'input_tokens': 10, 'cached_input_tokens': 0, 'output_tokens': 5}},
                              model='codex')
        self.assertEqual((out['cost_usd'], out['cost_basis']), (None, 'unknown'))

    def test_nothing_reported_stays_unknown(self):
        out = usage.normalize({'outcome': 'SUCCESS'})
        self.assertEqual((out['processed'], out['cost_usd']), (None, None))

    def test_openai_compatible_usage_with_a_reported_cost(self):
        out = usage.normalize({'usage': {'prompt_tokens': 100, 'completion_tokens': 20,
                                         'prompt_cache_hit_tokens': 60, 'cost': 0.00042}}, model='deepseek-flash')
        self.assertEqual((out['input'], out['cached'], out['output'], out['cost_usd'], out['cost_basis']),
                         (40, 60, 20, 0.00042, 'reported'))

    def test_an_app_server_turn_is_the_delta_of_the_thread_total(self):
        tracker = usage.TurnTokens()
        # a resumed thread that had already used 5000 input / 300 output tokens
        tracker.observe('thread/tokenUsage/updated', {'tokenUsage': {
            'total': {'inputTokens': 5600, 'cachedInputTokens': 4000, 'outputTokens': 350, 'totalTokens': 5950},
            'last': {'inputTokens': 600, 'cachedInputTokens': 400, 'outputTokens': 50, 'totalTokens': 650}}})
        tracker.observe('thread/tokenUsage/updated', {'tokenUsage': {
            'total': {'inputTokens': 6400, 'cachedInputTokens': 4600, 'outputTokens': 420, 'totalTokens': 6820},
            'last': {'inputTokens': 800, 'cachedInputTokens': 600, 'outputTokens': 70, 'totalTokens': 870}}})
        result = tracker.apply({'outcome': 'SUCCESS'})
        self.assertEqual((result['usage']['inputTokens'], result['usage']['cachedInputTokens'],
                          result['usage']['outputTokens']), (1400, 1000, 120))
        self.assertEqual(usage.normalize(result)['processed'], 400 + 120)

    def test_the_claude_host_turn_reports_usage_cost_and_duration(self):
        tracker = usage.TurnTokens()
        tracker.observe('turn/completed', {'turn': {'status': 'completed'}, 'usage': CLAUDE_RESULT['usage'],
                                           'cost_usd': 0.05, 'duration_ms': 1200})
        result = tracker.apply({'outcome': 'SUCCESS'})
        self.assertEqual((result['cost_usd'], result['runtime_ms'], usage.normalize(result)['processed']),
                         (0.05, 1200, 3141))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ['CODEX_HOME'] = str(Path(self.tmp.name) / 'codex-home')
        self.store = Store(Path(self.tmp.name) / 'data')
        staff.ensure_schema(self.store)


class RecordTests(Base):
    def test_one_row_per_call_and_the_job_spend(self):
        usage.record(self.store, 'run-1', job_id='j', kind='work', adapter='claude-code', task_class='coding',
                     result=dict(CLAUDE_RESULT, model_used='claude-opus-5-5', wall_ms=21000))
        usage.record(self.store, 'run-1', job_id='j', kind='work', adapter='claude-code', task_class='coding',
                     result=dict(CLAUDE_RESULT, wall_ms=99999))
        usage.record(self.store, 'rev-1', job_id='j', kind='check', adapter='codex', model='gpt-6-astra',
                     task_class='review', result={'usage': {'input_tokens': 500, 'cached_input_tokens': 0,
                                                             'output_tokens': 100}, 'wall_ms': 4000})
        spend = usage.job_spend(self.store, 'j')
        self.assertEqual(spend['calls'], 2, 'a call is recorded once')
        self.assertEqual(spend['processed'], 3141 + 600)
        self.assertEqual(spend['wall_ms'], 25000)
        self.assertAlmostEqual(spend['cost_usd'], 0.051532 + (500 * 10 + 100 * 50) / 1e6, places=6)
        stats = usage.model_stats(self.store)
        self.assertEqual(stats['claude-opus-5-5']['runs'], 1)
        self.assertEqual(stats['gpt-6-astra']['cost_basis'], 'estimated')
        self.assertEqual(stats['claude-opus-5-5']['median_ms'], 21000)

    def test_no_payload_is_stored(self):
        data = usage.record(self.store, 'run-2', job_id='j', adapter='codex',
                            result={'outcome': 'SUCCESS', 'text': 'SECRET ANSWER', 'usage': {}})
        self.assertNotIn('SECRET', str(data))

    def test_a_consumed_run_records_its_usage(self):
        contract = {'request': 'Write a haiku', 'milestones': [{'id': 'd', 'objective': 'Write a haiku',
                    'filename': 'd.md', 'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 3}]}]}
        contract['staffing'] = staff.plan_job(self.store, contract)
        job = self.store.create(contract)
        run = self.store.claim(job, 'd', provider='codex')
        self.store.enqueue_result('r', run['id'], run['epoch'], {
            'outcome': 'SUCCESS', 'text': 'Leaves fall softly.', 'model_used': 'gpt-6-luna', 'wall_ms': 3200,
            'usage': {'input_tokens': 900, 'cached_input_tokens': 100, 'output_tokens': 40}})
        self.store.consume()
        row = usage.rows(self.store, job_id=job)[0]
        self.assertEqual((row['kind'], row['model'], row['wall_ms'], row['processed']), ('work', 'gpt-6-luna', 3200, 840))
        self.assertEqual(row['task_class'], staff.step_routing(self.store.get(job), 'd')[0])

    def test_the_ranking_uses_measured_cost_and_latency(self):
        from kel import role_models
        role_models.set_role(self.store, 'utility', 'automatic')
        now = time.time()
        for index in range(3):
            usage.record(self.store, 'a%d' % index, adapter='codex', model='gpt-6-luna', task_class='utility',
                         result={'usage': {'input_tokens': 1000, 'cached_input_tokens': 0, 'output_tokens': 100},
                                 'wall_ms': 2000}, at=now)
        entry = next(e for e in task_routing.ranking(self.store, 'utility', adapters={'codex', 'claude'},
                                                     tier='fast') if e['model'] == 'gpt-6-luna')
        self.assertEqual(entry['measured']['runs'], 3)
        self.assertIn('usually 2 s', entry['why'])
        self.assertIn('$0.000', entry['why'])


if __name__ == '__main__':
    unittest.main()
