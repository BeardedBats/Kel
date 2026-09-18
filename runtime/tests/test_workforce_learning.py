"""Phase 5.6: the learning loop (shadow) — learnings as memory records, the curator pipeline,
retros, shadow staffing proposals, and the derived performance/validation metrics.

Verification for `kel/learning.py` (workforce-os docs 11 §1-6, 13 §4, 15 §5.6): learnings ride
the V1.3 memory model (provenance/trust ladder, append-only supersede chains, conflict queue),
dedup never forks a key, observed/inferred decay while user-stated does not, preferences are
recorded only from explicit user confirmation, confidence above the auto cap lands in the
promotion queue instead of being applied, the shadow flag gates every write path (zero writes
when off), and the curator records learnings/retro/proposals deterministically from mission
facts without applying anything.
"""
import contextlib
import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from kel.assurance import lenses_for, record_finding, resolve_finding
from kel.assignment import ensure_schema as ensure_assignment_schema
from kel.assignment import flags_snapshot
from kel.context import Context
from kel.core import PolicyError, Store
from kel.learning import (AUTO_CONFIDENCE_CAP, curate, correct_learning, draft_retro,
                          learnings_view, performance_stats, promotion_queue, queue_promotion,
                          record_learning, retro_for, shadow_proposal, shadow_proposals,
                          validation_metrics)
from kel.memory import Memory, ensure_proposals
from kel.memory import ensure_schema as ensure_memory_schema
from kel.parallel import ensure_schema as ensure_parallel_schema
from kel.team import Team
from kel.workforce import ensure_schema as ensure_workforce_schema

SHADOW_ON = {'workforce.enabled': True, 'workforce.learning.shadow': True}
SHADOW_OFF = {'workforce.enabled': True, 'workforce.learning.shadow': False}
PROJECT = 'proj-learner'
MISSION = 'mis_' + 'a' * 8
TASK = 'tsk_' + 'b' * 8
TASK2 = 'tsk_' + 'c' * 8
MISSION2 = 'mis_' + 'd' * 8
DAY = 86400.0


def finding(lens='maintainability', **overrides):
    body = {'schema_version': 1, 'mission_id': MISSION, 'task_id': TASK,
            'lens': lens, 'severity': 'info', 'confidence': 7, 'artifact': 'art_x',
            'location': 'loc', 'summary': 'Fixture finding.', 'evidence': 'fixture',
            'fix': '', 'fingerprint': 'fp-%s-%s' % (lens, overrides.get('fingerprint', 'x')),
            'status': 'open',
            'by': {'lens': lens, 'model_family': 'fixture', 'assignment': 'asn_' + 'c' * 8}}
    body.update(overrides)
    return body


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'data')
        ensure_workforce_schema(self.store)
        ensure_assignment_schema(self.store)
        ensure_parallel_schema(self.store)
        ensure_memory_schema(self.store)
        ensure_proposals(self.store)
        self.context = Context(self.store)
        self.context.project('Learning Project', project_id=PROJECT)
        self.team = Team(self.store)

    # ---- helpers --------------------------------------------------------

    def direct(self, sql, args=()):
        with self.store.transaction() as db:
            return db.execute(sql, args).fetchall()

    def scalar(self, sql, args=()):
        with contextlib.closing(self.store.connect()) as db:
            return db.execute(sql, args).fetchone()[0]

    def memory_rows(self):
        with contextlib.closing(self.store.connect()) as db:
            return [dict(row) for row in db.execute(
                'SELECT * FROM memories ORDER BY created, rowid').fetchall()]

    def events(self, kind=None):
        with contextlib.closing(self.store.connect()) as db:
            if kind:
                return [dict(row) for row in db.execute(
                    'SELECT * FROM team_events WHERE kind=? ORDER BY seq', (kind,)).fetchall()]
            return [dict(row) for row in db.execute('SELECT * FROM team_events ORDER BY seq')
                    .fetchall()]

    def seed_contract(self, mission=MISSION, task=TASK):
        self.direct('INSERT INTO task_contracts(contract_id,task_id,version,mission_id,'
                    'parent_task,digest,data,created) VALUES(?,?,?,?,?,?,?,?)',
                    ('con_' + mission, task, 1, mission, None, 'sha256:fixture', '{}',
                     time.time()))

    def seed_tier(self, tier='D1', task=TASK, assignment='asn_' + '1' * 8):
        # Assignment-scoped, like every production writer (delegation/pods): the tier join in
        # kel/learning.py keys on the assignment id (audit 23, F23-6).
        self.direct('INSERT INTO team_events(at,kind,actor,assignment_id,job_id,milestone_id,'
                    'run_id,refs,detail) VALUES(?,?,?,?,?,?,?,?,?)',
                    (time.time(), 'contract.issued', 'kel', assignment, None, None, None, None,
                     json.dumps({'task_id': task, 'contract_id': 'con_x'})))
        self.direct('INSERT INTO team_events(at,kind,actor,assignment_id,job_id,milestone_id,'
                    'run_id,refs,detail) VALUES(?,?,?,?,?,?,?,?,?)',
                    (time.time(), 'staffing.decided', 'kel', assignment, None, None, None, None,
                     json.dumps({'tier': tier})))

    def seed_finding(self, lens='maintainability', severity='info', **overrides):
        return record_finding(self.store, finding(lens=lens, severity=severity, **overrides))

    def seed_evidence(self):
        self.direct('INSERT INTO evidence_records VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    ('ev_' + 'e' * 16, 1, MISSION, TASK, 'test', 'fixture evidence', None, 0,
                     'sha256:f', None, time.time(), 3600, 'fixture'))
        return 'ev_' + 'e' * 16

    def dismiss(self, record, rationale='fixture false positive'):
        return resolve_finding(self.store, record['id'], resolution='dismissed',
                               rationale=rationale)

    def fix(self, record, evidence_ref):
        return resolve_finding(self.store, record['id'], resolution='fixed',
                               evidence_ref=evidence_ref)

    def record(self, **overrides):
        body = dict(project_id=PROJECT, key='review.fresh-context-bias', type='pattern',
                    insight='Fresh-context reviews catch anchoring earlier.', confidence=4,
                    source='observed', evidence=['fx_1'], mission_id=MISSION,
                    flags=SHADOW_ON)
        body.update(overrides)
        return record_learning(self.store, **body)


class FlagGateTests(Base):
    def test_default_flag_is_off_and_flags_snapshot_carries_it(self):
        self.assertIs(flags_snapshot(env={})['workforce.learning.shadow'], False)

    def test_every_write_path_performs_zero_writes_when_off(self):
        result = record_learning(self.store, project_id=PROJECT, key='a.b', type='pattern',
                                 insight='nope', confidence=3, source='observed',
                                 flags=SHADOW_OFF)
        self.assertFalse(result['recorded'])
        off_calls = [
            queue_promotion(self.store, project_id=PROJECT, proposal_kind='playbook',
                            subject='x', requested={'change': 'x'}, flags=SHADOW_OFF),
            shadow_proposal(self.store, project_id=PROJECT, mission_id=MISSION,
                            proposal={'change': 'x'}, prediction={'delta': 0},
                            confidence='low', flags=SHADOW_OFF),
            draft_retro(self.store, project_id=PROJECT, mission_id=MISSION,
                        flags=SHADOW_OFF),
        ]
        for value in off_calls:
            self.assertFalse(value.get('recorded', False))
            self.assertFalse(value.get('applied', False))
        curate_result = curate(self.store, project_id=PROJECT, mission_id=MISSION,
                               flags=SHADOW_OFF)
        self.assertFalse(curate_result['applied'])
        self.assertEqual(self.scalar('SELECT count(*) FROM memories'), 0)
        self.assertEqual(self.scalar('SELECT count(*) FROM team_events'), 0)

    def test_correct_learning_with_nothing_to_change_is_refused(self):
        with self.assertRaises(PolicyError):
            correct_learning(self.store, 'whatever')


class LearningRecordTests(Base):
    def test_learning_is_a_memory_record_with_a_workforce_source(self):
        result = self.record()
        self.assertTrue(result['recorded'])
        rows = self.memory_rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['type'], 'convention')       # pattern -> convention (1:1 map)
        self.assertEqual(row['topic'], 'review.fresh-context-bias')
        self.assertEqual(row['source_type'], 'workforce_observed')
        self.assertEqual(row['trust'], 5)
        value = json.loads(row['value'])
        self.assertEqual(value['schema'], 'learning.v1')
        self.assertEqual(value['type'], 'pattern')
        self.assertEqual(value['confidence'], 4)
        view = learnings_view(self.store, project_id=PROJECT)
        self.assertEqual(len(view), 1)
        self.assertEqual(view[0]['key'], 'review.fresh-context-bias')
        self.assertEqual(view[0]['confidence'], 4)
        self.assertEqual(view[0]['effective_confidence'], 4)
        self.assertFalse(view[0]['stale'])
        self.assertEqual(view[0]['memory_id'], result['memory_id'])
        kinds = [row['kind'] for row in self.events()]
        self.assertIn('learning.recorded', kinds)

    def test_validation_refuses_bad_shapes(self):
        with self.assertRaises(PolicyError):
            self.record(type='vibe')
        with self.assertRaises(PolicyError):
            self.record(source='telepathy')
        with self.assertRaises(PolicyError):
            self.record(key='Bad Key')
        with self.assertRaises(PolicyError):
            self.record(confidence=11)
        with self.assertRaises(PolicyError):
            self.record(insight='')

    def test_dedup_supersedes_and_never_forks_the_key(self):
        first = self.record(insight='First statement.', confidence=3)
        second = self.record(insight='Second statement, better earned.', confidence=4)
        rows = self.memory_rows()
        self.assertEqual(len(rows), 2)
        statuses = {row['id']: row['status'] for row in rows}
        self.assertEqual(statuses[first['memory_id']], 'superseded')
        self.assertEqual(statuses[second['memory_id']], 'active')
        view = learnings_view(self.store, project_id=PROJECT)
        self.assertEqual(len(view), 1)
        self.assertEqual(view[0]['insight'], 'Second statement, better earned.')

    def test_inference_cannot_overwrite_observation(self):
        observed = self.record(insight='Observed.', confidence=4, source='observed')
        inferred = self.record(insight='Inferred later.', confidence=3, source='inferred')
        rows = {row['id']: row for row in self.memory_rows()}
        # trust 6 (inference) < trust 5 (observation) on the ladder: the new row loses (a_wins).
        self.assertEqual(rows[inferred['memory_id']]['status'], 'superseded')
        self.assertEqual(rows[inferred['memory_id']]['superseded_by'], observed['memory_id'])
        view = learnings_view(self.store, project_id=PROJECT)
        self.assertEqual(len(view), 1)
        self.assertEqual(view[0]['source'], 'observed')
        self.assertEqual(view[0]['insight'], 'Observed.')

    def test_distinct_types_share_a_key_without_collision(self):
        # (type, key) is the identity: the same slug recorded as a pattern and as a pitfall are
        # two learnings (different memory types) and must not hide each other (audit 23, F23-5).
        self.record(type='pattern', insight='Recurring shape.', confidence=4)
        self.record(type='pitfall', insight='Recurring trap.', confidence=3)
        view = learnings_view(self.store, project_id=PROJECT)
        types = sorted(item['type'] for item in view
                       if item['key'] == 'review.fresh-context-bias')
        self.assertEqual(types, ['pattern', 'pitfall'])

    def test_decay_and_stale_are_computed_not_written(self):
        result = self.record(confidence=3, source='observed')
        row = {r['id']: r for r in self.memory_rows()}[result['memory_id']]
        base = float(row['created'])
        # Boundary: whole 30-day periods only — 29 days is still 0, 30 days is the first decay.
        self.assertEqual(
            learnings_view(self.store, project_id=PROJECT, now=base + 29 * DAY)[0]
            ['effective_confidence'], 3)
        at_31d = learnings_view(self.store, project_id=PROJECT, now=base + 31 * DAY)
        self.assertEqual(at_31d[0]['effective_confidence'], 2)
        # A losing weaker write bumps the winner's `updated` in the memory store but must NOT
        # reset its decay clock — decay runs from the record's own creation (audit 23, F23-3).
        self.record(insight='Inferred revision.', confidence=2, source='inferred')
        still_31d = learnings_view(self.store, project_id=PROJECT, now=base + 31 * DAY)
        self.assertEqual(still_31d[0]['source'], 'observed')
        self.assertEqual(still_31d[0]['effective_confidence'], 2)
        # 90 days: 3 - 3 -> effective 0 -> stale; stale leaves DEFAULT retrieval...
        default = learnings_view(self.store, project_id=PROJECT, now=base + 90 * DAY)
        self.assertEqual(default, [])
        kept = learnings_view(self.store, project_id=PROJECT, include_stale=True,
                              now=base + 90 * DAY)
        self.assertEqual(len(kept), 1)  # ...but stays inspectable
        self.assertEqual(kept[0]['effective_confidence'], 0)
        self.assertTrue(kept[0]['stale'])
        # user-stated never decays
        stated = self.record(key='pref.tone', type='tool', insight='User likes terse output.',
                             confidence=6, source='user-stated', confirmed_by='user')
        view = learnings_view(self.store, project_id=PROJECT, now=base + 400 * DAY)
        entry = next(item for item in view if item['key'] == 'pref.tone')
        self.assertEqual(entry['effective_confidence'], 6)

    def test_correct_learning_becomes_user_stated(self):
        result = self.record()
        fixed = correct_learning(self.store, result['memory_id'],
                                 insight='Corrected: reviews help.', confidence=7)
        self.assertTrue(fixed['corrected'])
        view = learnings_view(self.store, project_id=PROJECT)
        self.assertEqual(len(view), 1)
        self.assertEqual(view[0]['insight'], 'Corrected: reviews help.')
        self.assertEqual(view[0]['confidence'], 7)
        self.assertEqual(view[0]['source'], 'user-stated')
        row = {r['id']: r for r in self.memory_rows()}[fixed['memory_id']]
        self.assertEqual(row['trust'], 2)
        self.assertEqual(row['user_confirmed'], 1)

    def test_secret_like_content_is_refused_by_the_memory_scan(self):
        with self.assertRaises(PolicyError):
            self.record(insight='token: sk-ant-abcdefghijklmnop0123456789')


class PreferenceTests(Base):
    def test_preferences_require_explicit_user_confirmation(self):
        with self.assertRaises(PolicyError):
            self.record(type='preference', source='observed')
        with self.assertRaises(PolicyError):
            self.record(type='preference', source='user-stated')  # no confirmed_by
        result = self.record(type='preference', source='user-stated', confirmed_by='user',
                             key='pref.report-style', insight='User wants short retros.')
        row = {r['id']: r for r in self.memory_rows()}[result['memory_id']]
        self.assertEqual(row['type'], 'preference')
        self.assertEqual(row['trust'], 2)
        self.assertEqual(row['user_confirmed'], 1)

    def test_user_stated_learnings_skip_the_auto_cap(self):
        result = self.record(type='pitfall', source='user-stated', confirmed_by='user',
                             confidence=9, key='pitfall.user-known')
        self.assertEqual(result['stored_confidence'], 9)
        self.assertFalse(result['cap_applied'])
        self.assertEqual(promotion_queue(self.store, project_id=PROJECT), [])


class PromotionQueueTests(Base):
    def test_confidence_above_the_cap_is_stored_capped_and_queued(self):
        result = self.record(confidence=9, source='observed')
        self.assertEqual(result['stored_confidence'], AUTO_CONFIDENCE_CAP)
        self.assertTrue(result['cap_applied'])
        view = learnings_view(self.store, project_id=PROJECT)
        self.assertEqual(view[0]['confidence'], AUTO_CONFIDENCE_CAP)
        queue = promotion_queue(self.store, project_id=PROJECT)
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]['proposal_kind'], 'learning.promotion')
        self.assertEqual(queue[0]['subject'], 'review.fresh-context-bias')
        self.assertEqual(queue[0]['requested']['confidence'], 9)
        self.assertEqual(queue[0]['state'], 'queued')
        kinds = sorted(row['kind'] for row in self.events())
        self.assertEqual(kinds, ['learning.recorded', 'proposal.queued'])

    def test_promotion_queue_is_project_scoped_and_nothing_applies(self):
        self.record(confidence=8)
        self.assertEqual(promotion_queue(self.store, project_id='other'), [])
        queued = queue_promotion(self.store, project_id=PROJECT,
                                 proposal_kind='playbook', subject='role-versions',
                                 requested={'change': 'raise reviewer floor'},
                                 basis={'basis': 'fixture'}, flags=SHADOW_ON)
        self.assertTrue(queued['recorded'])
        items = promotion_queue(self.store, project_id=PROJECT)
        self.assertEqual([item['proposal_kind'] for item in items],
                         ['learning.promotion', 'playbook'])


class CuratorTests(Base):
    def seed_lens_history(self):
        ev = self.seed_evidence()
        for index in range(2):
            self.dismiss(self.seed_finding(lens='maintainability',
                                           fingerprint='dismiss-%d' % index))
        for index in range(2):
            self.fix(self.seed_finding(lens='maintainability', severity='info',
                                       fingerprint='fix-%d' % index), ev)

    def test_curator_records_learnings_retro_and_nothing_is_applied(self):
        self.seed_contract()
        self.seed_tier('D3')
        self.seed_lens_history()
        self.direct('INSERT INTO budget_reservations(reservation_id,job_id,milestone_id,'
                    'assignment_id,budget_class,tokens,wallclock,cost,state,note,created,'
                    'updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                    ('res_x', 'job_x', None, 'asn_' + '1' * 8, 'standard', 100, 60, 1.5,
                     'reserved', None, time.time(), time.time()))
        before_events = len(self.events())
        result = curate(self.store, project_id=PROJECT, mission_id=MISSION, flags=SHADOW_ON)
        self.assertTrue(result['applied'])
        keys = [item['key'] for item in result['learnings'] if item['recorded']]
        self.assertIn('lens.maintainability.false-positive', keys)
        self.assertIn('lens.maintainability.proven', keys)
        view = {item['key']: item for item in learnings_view(self.store, project_id=PROJECT)}
        self.assertIn('lens.maintainability.false-positive', view)
        self.assertEqual(view['lens.maintainability.proven']['type'], 'pattern')
        retro = retro_for(self.store, mission_id=MISSION)
        self.assertIsNotNone(retro)
        self.assertEqual(retro['schema'], 'retro.v1')
        self.assertIn('lens.maintainability.proven', retro['learned'])
        self.assertEqual(retro['cost']['reserved'], 1)
        self.assertEqual(retro['cost']['tokens'], 100)
        self.assertIn('validation', result)
        self.assertIn('gating_precision', result['validation'])
        # nothing applied: the only new events are learning.recorded / retro.drafted
        kinds = [row['kind'] for row in self.events()][before_events:]
        self.assertTrue(set(kinds) <= {'learning.recorded', 'retro.drafted'})

    def test_curator_rerun_does_not_fork_keys(self):
        self.seed_contract()
        self.seed_tier('D3')
        self.seed_lens_history()
        curate(self.store, project_id=PROJECT, mission_id=MISSION, flags=SHADOW_ON)
        curate(self.store, project_id=PROJECT, mission_id=MISSION, flags=SHADOW_ON)
        view = learnings_view(self.store, project_id=PROJECT)
        keys = [item['key'] for item in view]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn('lens.maintainability.false-positive', keys)

    def test_user_corrections_become_user_stated_candidates(self):
        memory = Memory(self.store)
        mid = memory.record(PROJECT, 'convention', 'board.layout', {'note': 'fixture'},
                            'Board layout note.', source_type='repo_inspection')
        first = memory.correct(mid, summary='Corrected board layout note (1).')
        memory.correct(first, summary='Corrected board layout note (2).')
        result = curate(self.store, project_id=PROJECT, mission_id=MISSION, flags=SHADOW_ON)
        keys = [item['key'] for item in result['learnings'] if item['recorded']]
        self.assertIn('correction.board.layout', keys)
        view = {item['key']: item for item in learnings_view(self.store, project_id=PROJECT)}
        self.assertEqual(view['correction.board.layout']['source'], 'user-stated')

    def test_lens_candidates_scope_to_the_given_missions(self):
        # Two missions, both with dismissed maintainability findings; scoping to one mission
        # must keep the other mission's counts and finding ids out of the learning (audit 23,
        # F23-2; doc 11 §7 cross-project leakage).
        self.seed_contract()
        self.seed_contract(mission=MISSION2, task=TASK2)
        scoped = [self.dismiss(self.seed_finding(lens='maintainability',
                                                 fingerprint='scope-a-%d' % index))
                  for index in range(2)]
        for index in range(2):
            self.dismiss(self.seed_finding(lens='maintainability', mission_id=MISSION2,
                                           task_id=TASK2, fingerprint='scope-b-%d' % index))
        curate(self.store, project_id=PROJECT, mission_id=MISSION, missions=[MISSION],
               flags=SHADOW_ON)
        view = {item['key']: item for item in learnings_view(self.store, project_id=PROJECT)}
        entry = view['lens.maintainability.false-positive']
        self.assertEqual(entry['confidence'], 4)                    # 2 + the two scoped ones
        self.assertEqual(set(entry['evidence']), {item['id'] for item in scoped})
        self.assertIn('this project', entry['insight'])

    def test_shadow_staffing_proposals_are_recorded_with_predictions(self):
        self.seed_contract()
        self.seed_tier('D2')
        result = curate(self.store, project_id=PROJECT, mission_id=MISSION, flags=SHADOW_ON)
        proposals = shadow_proposals(self.store, project_id=PROJECT, mission_id=MISSION)
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]['state'], 'shadow')
        self.assertIn('prediction', proposals[0])
        self.assertIn('wallclock_saved_pct', proposals[0]['prediction'])
        self.assertIn('one lower tier', proposals[0]['proposal']['change'])
        self.assertTrue(result['proposal']['recorded'])

    def test_blockers_derive_the_keep_or_raise_proposal(self):
        self.seed_contract(mission=MISSION2, task=TASK2)
        self.seed_tier('D2', task=TASK2)
        self.seed_finding(lens='functional-testing', severity='blocker',
                          mission_id=MISSION2, task_id=TASK2, fingerprint='blocker-1')
        curate(self.store, project_id=PROJECT, mission_id=MISSION2, flags=SHADOW_ON)
        proposals = shadow_proposals(self.store, mission_id=MISSION2)
        self.assertEqual(len(proposals), 1)
        self.assertIn('keep or raise', proposals[0]['proposal']['change'])

    def test_queue_promotion_validates_and_records_never_applies(self):
        queued = queue_promotion(self.store, project_id=PROJECT, proposal_kind='gating',
                                 subject='adaptive-enablement',
                                 requested={'change': 'enable non-insurance gating'},
                                 basis={'campaign': 'pending'}, flags=SHADOW_ON)
        self.assertTrue(queued['recorded'])
        self.assertEqual(queued['state'], 'queued')
        with self.assertRaises(PolicyError):
            self.team.record_mission_activity('retro.drafted', detail={'reasoning': 'hidden'})
        with self.assertRaises(PolicyError):
            self.team.record_mission_activity('not-a-kind')


class DerivedViewTests(Base):
    def test_performance_stats_rates_and_small_samples(self):
        ev = self.seed_evidence()
        for index in range(2):
            self.fix(self.seed_finding(lens='maintainability', severity='info',
                                       fingerprint='p-fix-%d' % index), ev)
        self.dismiss(self.seed_finding(lens='maintainability', severity='info',
                                       fingerprint='p-dismiss'))
        self.seed_finding(lens='functional-testing', severity='info', fingerprint='p-open')
        stats = performance_stats(self.store)
        maint = stats['lens']['maintainability']
        self.assertEqual(maint['raised'], 3)
        self.assertEqual(maint['confirmed'], 2)
        self.assertEqual(maint['dismissed'], 1)
        self.assertEqual(maint['basis'], 'n=3')
        self.assertAlmostEqual(maint['false_positive_rate'], 0.333, places=3)
        func = stats['lens']['functional-testing']
        self.assertEqual(func['basis'], 'insufficient (n<3)')
        self.assertIn('budget', stats)
        self.assertIn('conflicts', stats)

    def test_validation_metrics_gating_precision_and_false_skip(self):
        self.seed_contract()
        plan = lenses_for('D1')
        skipped_lens = sorted(plan['skipped'])[0]
        self.seed_tier('D1')
        ev = self.seed_evidence()
        self.fix(self.seed_finding(lens=skipped_lens, severity='info', fingerprint='skip-1'), ev)
        for index in range(2):
            self.dismiss(self.seed_finding(lens='maintainability', severity='info',
                                           fingerprint='v-dismiss-%d' % index))
        metrics = validation_metrics(self.store)
        precision = metrics['gating_precision']
        self.assertEqual(precision['basis'], 'n=3')
        # 1 live (fixed/open) + 2 dismissed: precision over judged = confirmed/judged
        self.assertIsNotNone(precision['value'])
        self.assertGreaterEqual(precision['confirmed'], 1)
        self.assertEqual(precision['dismissed'], 2)
        false_skip = metrics['false_skip']
        self.assertEqual(false_skip['skipped_total'], len(plan['skipped']))
        self.assertGreaterEqual(len(false_skip['misses']), 1)
        self.assertEqual(false_skip['misses'][0]['lens'], skipped_lens)
        self.assertEqual(false_skip['misses'][0]['tier'], 'D1')
        self.assertIn(metrics['note'], 'shadow metrics only; nothing here gates or changes live '
                                       'behavior')

    def test_retro_draft_roundtrip(self):
        self.seed_contract()
        retro = draft_retro(self.store, project_id=PROJECT, mission_id=MISSION,
                            learnings=['x.y'], proposals=[7], flags=SHADOW_ON)
        self.assertEqual(retro['schema'], 'retro.v1')
        again = retro_for(self.store, mission_id=MISSION)
        self.assertEqual(again['mission_id'], MISSION)
        self.assertEqual(again['proposals'], [7])
        self.assertEqual(again['learned'], ['x.y'])


if __name__ == '__main__':
    unittest.main()
