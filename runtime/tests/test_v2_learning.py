"""V2-10 — Learning 2.0: what Kel learned, off/on, explain, and evidence-thresholded suggestions.

The learning layer already rode the V1.3 memory store (append-only chains, trust ladder, the proposal
queue). This increment adds the person's side and the fence, and these pins are exactly those rules:

- a learning can be switched off without being deleted, and a switched-off learning never reaches
  model context again — while staying inspectable and one call away from being switched back on;
- every learning can be explained: what it says, where it came from, its evidence, its history, and
  its effect in plain words (advisory only, never authority);
- nothing is suggested from fewer than the evidence threshold, and a rejected suggestion never
  returns until its evidence changes (the proposal queue's own dedupe rule);
- no non-user source can record or suggest authority — permission grants, spending, filesystem
  access or irreversible actions are refused outright; the person's own statement is theirs to make;
- suggestions are never decisions or preferences (those come only from the person), and accepting one
  is what makes it the person's own — it is stored as their confirmation.
"""
import contextlib
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from kel.assignment import ensure_schema as ensure_assignment_schema
from kel.connections import ensure_schema as ensure_connections_schema
from kel.context import Context
from kel.core import PolicyError, Store
from kel.learning import (SUGGEST_MIN_EVIDENCE, authority_refusal, explain_learning, learnings_view,
                          record_learning, set_enabled, suggest_learnings)
from kel.memory import Memory, ensure_proposals
from kel.memory import ensure_schema as ensure_memory_schema
from kel.workforce import ensure_schema as ensure_workforce_schema

SHADOW_ON = {'workforce.enabled': True, 'workforce.learning.shadow': True}
PROJECT = 'proj-v210'


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'data')
        ensure_workforce_schema(self.store)
        ensure_assignment_schema(self.store)
        ensure_memory_schema(self.store)
        ensure_proposals(self.store)
        ensure_connections_schema(self.store)
        self.context = Context(self.store)
        self.context.project('Learning V2-10', project_id=PROJECT)

    def learning(self, key='style.terse', **overrides):
        body = dict(project_id=PROJECT, key=key, type='pattern',
                    insight='Short answers work best here.', confidence=5, source='observed',
                    evidence=['mission:one'], flags=SHADOW_ON)
        body.update(overrides)
        return record_learning(self.store, **body)

    def outcome(self, run_id, provider, verdict, kind='coding', at=None):
        with self.store.transaction() as db:
            db.execute('INSERT INTO routing_outcomes(run_id,provider,verdict,job_kind,at)'
                       ' VALUES(?,?,?,?,?)',
                       (run_id, provider, verdict, kind, time.time() if at is None else at))

    def event(self, connection_id='github', action='read', n=1):
        with self.store.transaction() as db:
            for _index in range(n):
                db.execute('INSERT INTO connection_events'
                           '(at,connection_id,action,domain,status,state,attempts,ms)'
                           ' VALUES(?,?,?,?,?,?,?,?)',
                           (time.time(), connection_id, action, 'api.github.com', 200, 'ok', 1, 12))

    def memory_row(self, memory_id):
        with contextlib.closing(self.store.connect()) as db:
            return db.execute('SELECT * FROM memories WHERE id=?', (memory_id,)).fetchone()


class SwitchTests(Base):
    def test_a_learning_the_person_switches_off_never_reaches_context_again(self):
        result = self.learning()
        memory_id = result['memory_id']
        selected = [row['id'] for row in Memory(self.store).select(PROJECT, purpose='context')]
        self.assertIn(memory_id, selected, 'an observed learning reaches context by default')
        off = set_enabled(self.store, memory_id, False)
        self.assertFalse(off['enabled'])
        self.assertNotEqual(off['memory_id'], memory_id, 'off is a superseding record, never an edit')
        new_id = off['memory_id']
        selected = [row['id'] for row in Memory(self.store).select(PROJECT, purpose='context')]
        self.assertNotIn(new_id, selected, 'a switched-off learning never reaches context')
        view = learnings_view(self.store, project_id=PROJECT)
        self.assertEqual(view, [], 'and it leaves the default view')
        everything = learnings_view(self.store, project_id=PROJECT, include_disabled=True)
        self.assertEqual([item['key'] for item in everything], ['style.terse'])
        self.assertFalse(everything[0]['enabled'])
        self.assertEqual(everything[0]['memory_id'], new_id)

    def test_switching_it_back_on_restores_it_from_the_same_chain(self):
        first = self.learning()['memory_id']
        second = set_enabled(self.store, first, False)['memory_id']
        third = set_enabled(self.store, second, True)['memory_id']
        view = learnings_view(self.store, project_id=PROJECT)
        self.assertEqual([item['memory_id'] for item in view], [third])
        selected = [row['id'] for row in Memory(self.store).select(PROJECT, purpose='context')]
        self.assertIn(third, selected)
        chain = Memory(self.store).history(third)
        self.assertEqual(len(chain), 3, 'off/on never deletes: the chain keeps every step')

    def test_removal_takes_it_out_of_every_view(self):
        memory_id = self.learning()['memory_id']
        Memory(self.store).forget(memory_id)
        self.assertEqual(learnings_view(self.store, project_id=PROJECT), [])
        self.assertEqual(learnings_view(self.store, project_id=PROJECT, include_disabled=True), [])

    def test_the_switch_persists_across_a_reopen(self):
        memory_id = set_enabled(self.store, self.learning()['memory_id'], False)['memory_id']
        reopened = Store(self.store.root)
        view = learnings_view(reopened, project_id=PROJECT, include_disabled=True)
        self.assertEqual([item['enabled'] for item in view], [False])

    def test_a_switched_off_learning_is_not_authoritative_about_its_own_trust(self):
        # Switching off must not launder trust: the copy keeps the original source type and trust.
        first = self.learning()['memory_id']
        before = self.memory_row(first)
        after = self.memory_row(set_enabled(self.store, first, False)['memory_id'])
        self.assertEqual(after['source_type'], before['source_type'])
        self.assertEqual(after['trust'], before['trust'])


class ExplainTests(Base):
    def test_explain_reports_source_evidence_history_and_effect(self):
        memory_id = self.learning()['memory_id']
        detail = explain_learning(self.store, memory_id)
        self.assertEqual(detail['key'], 'style.terse')
        self.assertEqual(detail['source'], 'observed')
        self.assertEqual(detail['evidence'], ['mission:one'])
        self.assertTrue(detail['enabled'])
        self.assertIn('never grants permission, spending, file access', detail['effect'])
        self.assertEqual(len(detail['history']), 1)
        self.assertEqual(detail['provenance']['source_ref'], 'workforce:%s' % PROJECT)

    def test_explain_says_so_when_the_learning_is_off(self):
        memory_id = set_enabled(self.store, self.learning()['memory_id'], False)['memory_id']
        detail = explain_learning(self.store, memory_id)
        self.assertFalse(detail['enabled'])
        self.assertIn("switched off", detail['effect'])

    def test_explain_refuses_a_record_that_is_not_a_learning(self):
        memory_id = Memory(self.store).record(PROJECT, 'convention', 'plain.topic',
                                             {'statement': 'Not a learning.'}, 'Not a learning.',
                                             source_type='repo_inspection')
        self.assertRaises(PolicyError, explain_learning, self.store, memory_id)


class AuthorityFenceTests(Base):
    def test_authority_is_refused_from_every_non_user_source(self):
        for insight in ('Kel may spend up to $50 without asking.',
                        'Grant Kel write access to the project folder.',
                        'You can delete any file in the workspace automatically.'):
            for source in ('observed', 'inferred', 'cross-model'):
                with self.assertRaises(PolicyError) as raised:
                    self.learning(key='authority.one', insight=insight, source=source)
                self.assertIn('yours to decide, every time', str(raised.exception))

    def test_the_persons_own_statement_is_theirs_to_make(self):
        result = self.learning(key='authority.two', source='user-stated', confirmed_by='user',
                               insight='Kel may spend up to $50 without asking.')
        self.assertTrue(result['recorded'])

    def test_ordinary_insights_are_not_blocked(self):
        self.assertIsNone(authority_refusal('Short answers work best here.'))
        self.assertTrue(self.learning(key='style.calm')['recorded'])


class SuggestionTests(Base):
    def pending(self):
        return [item for item in Memory(self.store).proposals(PROJECT) if item['state'] == 'pending']

    def test_suggestions_need_evidence_before_anything_is_proposed(self):
        empty = suggest_learnings(self.store, project_id=PROJECT)
        self.assertEqual(empty['suggested'], [])
        self.assertEqual(empty['minimum'], SUGGEST_MIN_EVIDENCE)
        self.assertEqual(self.pending(), [])
        self.outcome('r1', 'codex', 'VERIFIED')
        self.outcome('r2', 'codex', 'VERIFIED')
        self.assertEqual(suggest_learnings(self.store, project_id=PROJECT)['suggested'], [],
                         'below the threshold nothing is even suggested')
        self.outcome('r3', 'codex', 'VERIFIED')
        result = suggest_learnings(self.store, project_id=PROJECT)
        self.assertEqual(len(result['suggested']), 1)
        self.assertEqual(result['suggested'][0]['state'], 'pending')
        self.assertEqual(result['suggested'][0]['key'], 'model.coding.codex')
        self.assertEqual(Memory(self.store).records(PROJECT, type='convention'), [],
                         'a suggestion is never applied — it waits in the review queue')

    def test_a_run_mix_below_the_share_floor_is_not_suggested(self):
        self.outcome('a1', 'codex', 'VERIFIED')
        self.outcome('a2', 'codex', 'VERIFIED')
        self.outcome('a3', 'codex', 'FAILED')
        self.assertEqual(suggest_learnings(self.store, project_id=PROJECT)['suggested'], [])
        self.outcome('a4', 'codex', 'VERIFIED')
        self.assertEqual(len(suggest_learnings(self.store, project_id=PROJECT)['suggested']), 1)

    def test_a_rejected_suggestion_never_returns_until_the_evidence_changes(self):
        for index in range(3):
            self.outcome('r%d' % index, 'codex', 'VERIFIED')
        first = suggest_learnings(self.store, project_id=PROJECT)['suggested'][0]
        Memory(self.store).reject_proposal(first['id'])
        again = suggest_learnings(self.store, project_id=PROJECT)['suggested'][0]
        self.assertTrue(again['suppressed'], 'the same evidence stays turned down')
        self.assertEqual(self.pending(), [])
        self.outcome('r9', 'codex', 'VERIFIED')
        fresh = suggest_learnings(self.store, project_id=PROJECT)['suggested']
        self.assertEqual(len(fresh), 1)
        self.assertEqual(fresh[0]['state'], 'pending',
                         'changed evidence may ask again — exactly once')
        self.assertEqual(len(self.pending()), 1)

    def test_accepting_a_suggestion_writes_it_as_the_persons_own(self):
        for index in range(3):
            self.outcome('r%d' % index, 'codex', 'VERIFIED')
        suggestion = suggest_learnings(self.store, project_id=PROJECT)['suggested'][0]
        decision = Memory(self.store).accept_proposal(suggestion['id'])
        memory_id = decision['memory']
        row = self.memory_row(memory_id)
        self.assertEqual(row['source_type'], 'user_confirmation',
                         'accepting is the person speaking, so it carries their trust')
        view = learnings_view(self.store, project_id=PROJECT)
        self.assertEqual([item['key'] for item in view], ['model.coding.codex'])
        self.assertEqual(view[0]['source'], 'observed', 'the origin stays honest in the record')

    def test_repeated_corrections_become_a_suggestion(self):
        memory = Memory(self.store)
        memory_id = memory.record(PROJECT, 'convention', 'tone.choice', {'statement': 'Say it short.'},
                                  'Say it short.', source_type='model_inference', confidence=0.5)
        for index in range(SUGGEST_MIN_EVIDENCE):
            memory_id = memory.correct(memory_id, summary='Say it short. (%d)' % index)
        result = suggest_learnings(self.store, project_id=PROJECT)
        keys = [item['key'] for item in result['suggested']]
        self.assertIn('correction.tone.choice', keys)

    def test_connection_usage_is_suggested_after_the_threshold(self):
        self.event(n=SUGGEST_MIN_EVIDENCE - 1)
        self.assertEqual(suggest_learnings(self.store, project_id=PROJECT)['suggested'], [])
        self.event(n=1)
        result = suggest_learnings(self.store, project_id=PROJECT)
        keys = [item['key'] for item in result['suggested']]
        self.assertIn('connection.github.read', keys)

    def test_suggestions_are_never_decisions_or_preferences(self):
        for index in range(3):
            self.outcome('r%d' % index, 'codex', 'VERIFIED')
        self.event(n=3)
        suggest_learnings(self.store, project_id=PROJECT)
        for item in self.pending():
            self.assertEqual(item['kind'], 'user_change')
            self.assertNotIn(item['type'], ('decision', 'preference'))


class SurfaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('ANTHROPIC_API_KEY', None)
            os.environ.pop('KEL_INTERNAL_MODEL', None)
            os.environ['KEL_SKIP_TELEMETRY'] = '1'
            os.environ['KEL_REVIEWER'] = 'none'
            from kel.service import Service
            self.service = Service(self.tmp.name)

    def tearDown(self):
        self.service.shutdown()

    def test_the_memory_surface_carries_the_learning_actions(self):
        listing = self.service.action('/api/memory', {'action': 'learnings', 'conversation': 'main'})
        self.assertEqual(listing, {'learnings': []})
        result = self.service.action('/api/memory',
                                     {'action': 'suggest_learnings', 'conversation': 'main'})
        self.assertEqual(result['minimum'], SUGGEST_MIN_EVIDENCE)
        self.assertEqual(result['suggested'], [])
        with self.assertRaises(PolicyError):
            self.service.action('/api/memory',
                                {'action': 'learning', 'conversation': 'main',
                                 'id': 'mem_' + '0' * 8})


if __name__ == '__main__':
    unittest.main()
