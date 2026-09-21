"""V2-09 — routing intelligence: durable outcomes, decayed evidence, honest explanations.

One store (`routing_outcomes`, written by V1.5 and now by this module too), one decision path
(`kel.router.select`), and one explanation that surfaces read back from the stored route. The pins
here are about the rules that keep that honest:

- outcomes decay, so a failure last month does not punish a provider today and recovery is real;
- small samples never report a rate at all — the safe cost/health defaults stand;
- an inferred failure may be refined by a reviewed verdict, never the other way round;
- the evidence only reorders eligible models: an explicit choice and a preference are untouched;
- a message that asks for a command or a connected service is a work request, so the runtime can do
  it (the measured phone gap).
"""
import contextlib
import tempfile
import time
import unittest

from kel.core import Store
from kel.router import Candidate, needs_work, select
from kel.routing_evidence import (DAY, HALF_LIFE_DAYS, MIN_WEIGHT, WINDOW_DAYS, record, score,
                                  summary, weight)

# The exact sentence the live journey measured: a phone turn that asked for the connector and was
# answered conversationally by the saved-context path instead of running anything.
MEASURED_TOOL_TURN = ('Use the connected GitHub service to check which account my token belongs to. '
                      'Run `python -m kel.conn list` first to see the action, then run it. '
                      'Report the login name it gives in one sentence. Change no files.')
MEASURED_CHAT_TURN = ('Phone continuity check: reply with the words: still here. Change no files.')


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.store = Store(self.tmp.name)

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def outcome(self, run_id, provider, verdict, age_days=0.0, **extra):
        return record(self.store, run_id, provider, verdict,
                      at=time.time() - age_days * DAY, **extra)

    def test_recent_runs_read_as_a_rate_and_old_ones_decay_away(self):
        # Four failures from 25 days ago have decayed below the evidence floor: they cannot demote a
        # provider today (that is recovery), and they no longer report a rate at all.
        for index in range(4):
            self.outcome('old-%d' % index, 'codex', 'FAILED', age_days=25)
        stale = score(self.store, 'codex')
        self.assertEqual(stale['samples'], 4)
        self.assertIsNone(stale['verified_rate'],
                          'old outcomes decay below the floor instead of punishing forever')
        # Four failures from now are a current signal.
        for index in range(4):
            self.outcome('new-%d' % index, 'claude', 'FAILED', age_days=0)
        failing = score(self.store, 'claude')
        self.assertEqual(failing['verified_rate'], 0.0)
        block = summary(self.store, ['claude', 'codex'])
        self.assertTrue(block['claude']['demote'], 'a currently-failing provider steps aside')
        self.assertFalse(block['codex'].get('demote', False))
        # Recovery is real: four verified runs now outweigh the old failures by weight.
        for index in range(4):
            self.outcome('fresh-%d' % index, 'codex', 'VERIFIED', age_days=0)
        recovered = score(self.store, 'codex')
        self.assertGreater(recovered['verified_rate'], 0.8)
        self.assertFalse(summary(self.store, ['codex'])['codex']['demote'])

    def test_small_samples_report_no_rate_at_all(self):
        for index in range(2):
            self.outcome('tiny-%d' % index, 'tiny', 'VERIFIED', age_days=0)
        scored = score(self.store, 'tiny')
        self.assertEqual(scored['samples'], 2)
        self.assertLess(scored['weight'], MIN_WEIGHT)
        self.assertIsNone(scored['verified_rate'], 'two runs are not a rate')
        block = summary(self.store, ['tiny'])
        self.assertEqual(block['tiny']['verified_rate'], None)
        self.assertFalse(block['tiny']['demote'])
        self.assertIn('few recent runs', block['tiny']['sentence'])

    def test_a_provider_recovers_once_its_failures_age_out(self):
        for index in range(4):
            self.outcome('fail-%d' % index, 'grok', 'FAILED', age_days=35)
        self.assertEqual(summary(self.store, ['grok']), {},
                         'outcomes outside the window are not evidence any more')
        self.assertIsNone(score(self.store, 'grok')['verified_rate'])

    def test_half_life_is_the_documented_one(self):
        self.assertAlmostEqual(weight(HALF_LIFE_DAYS * DAY), 0.5, places=6)
        self.assertAlmostEqual(weight(0), 1.0, places=6)
        self.assertEqual(weight(None), 0.0)

    def test_a_review_refines_an_inferred_failure_and_never_the_other_way(self):
        self.outcome('run-1', 'codex', 'FAILED', source='milestone')
        self.outcome('run-1', 'codex', 'VERIFIED', source='review', review_provider='claude',
                     review_model='claude-native')
        with contextlib.closing(self.store.connect()) as db:
            row = dict(db.execute('SELECT * FROM routing_outcomes WHERE run_id=?', ('run-1',)).fetchone())
        self.assertEqual(row['verdict'], 'VERIFIED')
        self.assertEqual(row['source'], 'review')
        self.assertEqual(row['review_provider'], 'claude')
        self.outcome('run-1', 'codex', 'FAILED', source='milestone')
        with contextlib.closing(self.store.connect()) as db:
            again = dict(db.execute('SELECT * FROM routing_outcomes WHERE run_id=?', ('run-1',)).fetchone())
        self.assertEqual(again['verdict'], 'VERIFIED',
                         'an inferred failure never overwrites a reviewed verdict')

    def test_the_row_carries_the_facts_and_no_payload(self):
        record(self.store, 'run-2', 'codex', 'VERIFIED', job_kind='coding', attempts=2,
               escalated=1, model='codex-native', ms=1234, source='review',
               review_provider='claude', review_model='claude-native', cost=0.02)
        with contextlib.closing(self.store.connect()) as db:
            row = dict(db.execute('SELECT * FROM routing_outcomes WHERE run_id=?', ('run-2',)).fetchone())
        self.assertEqual(row['job_kind'], 'coding')
        self.assertEqual(row['attempts'], 2)
        self.assertEqual(row['escalated'], 1)
        self.assertEqual(row['model'], 'codex-native')
        self.assertEqual(row['ms'], 1234)
        self.assertEqual(row['cost'], 0.02)
        self.assertGreater(row['at'], 0)
        self.assertEqual(row['source'], 'review')


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.store = Store(self.tmp.name)

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def candidates(self):
        return [Candidate(name='alpha', cost=1.0, latency=5.0, quality=None),
                Candidate(name='beta', cost=2.0, latency=4.0, quality=None)]

    def test_evidence_only_reorders_and_says_why(self):
        route = select(self.candidates(), evidence={'beta': {'demote': True, 'sentence': 'x'}})
        self.assertEqual(route['selected'], 'alpha')
        self.assertEqual(route['demoted'], ['beta'])
        self.assertEqual(route['why'], 'recent results moved a failing model down')
        self.assertEqual(route['policy'], 'eligible-cost-v2')
        self.assertEqual(route['chain'], ['alpha', 'beta'])
        self.assertIn('beta', route['evidence'])

    def test_a_preference_and_an_explicit_choice_are_never_demoted(self):
        preferred = select(self.candidates(), prefer='beta', evidence={'beta': {'demote': True}})
        self.assertEqual(preferred['selected'], 'beta')
        self.assertEqual(preferred['demoted'], [])
        self.assertEqual(preferred['why'], 'your preferred model')
        explicit = select(self.candidates(), explicit='beta', evidence={'beta': {'demote': True}})
        self.assertEqual(explicit['selected'], 'beta')
        self.assertEqual(explicit['demoted'], [])
        self.assertEqual(explicit['why'], 'your chosen model')

    def test_without_evidence_the_cost_order_is_untouched(self):
        route = select(self.candidates())
        self.assertEqual(route['selected'], 'alpha')
        self.assertEqual(route['demoted'], [])
        self.assertEqual(route['evidence'], {})
        self.assertEqual(route['why'],
                         'lowest cost among the models that are healthy and capable here')


class ToolRequestTests(unittest.TestCase):
    """The measured phone gap: a tool request must be eligible for a real work turn."""

    def test_the_measured_turn_is_a_work_request(self):
        self.assertTrue(needs_work(MEASURED_TOOL_TURN))

    def test_ordinary_chat_is_not_a_work_request(self):
        for text in (MEASURED_CHAT_TURN,
                     'What is happening with Kel?',
                     'Summarize this article for me.',
                     'reply with the words: still here',
                     'thanks!'):
            self.assertFalse(needs_work(text), text)

    def test_command_shaped_requests_are_work(self):
        for text in ('Run the tests, please.',
                     'Please run the command `git status` and tell me what changed.',
                     'check the repository for the failing test',
                     'Execute the script in scripts/ and report the output.',
                     'use the connected service to list my Drive files'):
            self.assertTrue(needs_work(text), text)


if __name__ == '__main__':
    unittest.main()
