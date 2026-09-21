"""V2-12 — adaptive staffing: the learned step, on top of the rule table.

The rule table (`staffing.decide`), the D1 delegation path and the D2 pod path already exist. V2-12
adds the directive's remaining clause — learn from outcome history (when solo succeeds, when
specialists help, when high assurance is unnecessary) — as one bounded, explained step of advice over
settled missions at the same tier. It never crosses a hard rule's floor, never jumps more than one
tier, never overrides a cap and never acts on thin history. The pins:
"""
import contextlib
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from workforce_fixtures import candidates  # noqa: E402

from kel.assurance import record_finding  # noqa: E402
from kel.assignment import ensure_archetypes  # noqa: E402
from kel.assignment import ensure_schema as ensure_assignment_schema  # noqa: E402
from kel.core import PolicyError, Store  # noqa: E402
from kel.delegation import delegate, ensure_schema as ensure_delegation_schema  # noqa: E402
from kel.staffing import decide, outcome_advice, resolve  # noqa: E402
from kel.team import ensure_schema as ensure_team_schema  # noqa: E402
from kel.workforce import ensure_schema as ensure_workforce_schema  # noqa: E402

# Band D1 (3.7): a modest single-specialist task.
FEATURES_D1 = {'complexity': 2, 'decomposability': 1, 'sequentiality': 1, 'uncertainty': 0,
               'novelty': 0, 'risk': 0, 'domain_breadth': 0, 'tool_requirements': 0,
               'consequence_of_failure': 0, 'user_facing': 0, 'release_proximity': 0,
               'budget_class': 'standard'}
# Band D2 (5.3) with R1 already fired: sequential, low-decomposition work capped at D2.
FEATURES_D2_LOWD = {'complexity': 2, 'decomposability': 1, 'sequentiality': 2, 'uncertainty': 1,
                    'novelty': 1, 'risk': 0, 'domain_breadth': 0, 'tool_requirements': 1,
                    'consequence_of_failure': 0, 'user_facing': 0, 'release_proximity': 0,
                    'budget_class': 'standard'}


def finding(mission_id, severity='blocker', index=0):
    return {'schema_version': 1, 'mission_id': mission_id, 'task_id': 'tsk_' + 'd' * 8,
            'lens': 'maintainability', 'severity': severity, 'confidence': 9,
            'artifact': 'art_x', 'location': 'loc', 'summary': 'Fixture finding.',
            'evidence': 'fixture', 'fix': '', 'fingerprint': 'fp-%s-%d' % (mission_id, index),
            'status': 'open',
            'by': {'lens': 'maintainability', 'model_family': 'fixture',
                   'assignment': 'asn_' + 'e' * 8}}


def contract():
    return {'request': 'Staffing probe', 'milestones': [
        {'id': 'm1', 'objective': 'Work', 'filename': 'out.md', 'depends_on': [],
         'checks': [{'kind': 'min_chars', 'value': 10}]}]}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.store = Store(Path(self.tmp.name) / 'data')
        ensure_workforce_schema(self.store)
        ensure_assignment_schema(self.store)
        ensure_archetypes(self.store)
        ensure_delegation_schema(self.store)
        ensure_team_schema(self.store)

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def seed_mission(self, index, tier, *, blocked=False):
        """One settled mission exactly as the join reads it: decided tier + closed task (+ finding)."""
        mission = 'mis_%s%s' % (chr(97 + index), 'a' * 7)
        task = 'tsk_%s%s' % (chr(98 + index), 'b' * 7)
        assignment = 'asn_%s%s' % (chr(99 + index), 'c' * 7)
        with self.store.transaction() as db:
            db.execute('INSERT INTO task_contracts(mission_id,task_id,version,digest,data,created)'
                       ' VALUES(?,?,?,?,?,?)',
                       (mission, task, 1, 'digest', json.dumps({'x': 1}), time.time()))
            for kind, row_assignment, detail in (
                    ('staffing.decided', assignment, {'tier': tier}),
                    ('contract.issued', assignment, {'task_id': task}),
                    ('task.closed', None, {'task_id': task, 'outcome': 'done'})):
                db.execute('INSERT INTO team_events(kind,actor,assignment_id,detail,at)'
                           ' VALUES(?,?,?,?,?)',
                           (kind, 'kel', row_assignment, json.dumps(detail), time.time()))
        if blocked:
            record_finding(self.store, finding(mission, index=index))
        return mission


class AdviceTests(Base):
    def test_thin_history_changes_nothing(self):
        base = decide(FEATURES_D1)
        advice = outcome_advice(self.store, FEATURES_D1)
        self.assertEqual(advice['direction'], 'none')
        self.assertFalse(advice['applied'])
        self.assertEqual(advice['advised_tier'], base['tier'])
        self.assertEqual(advice['history']['settled'], 0)
        self.assertIn('minimum 3', advice['reasons'][0])
        self.assertEqual(resolve(self.store, FEATURES_D1)['tier'], base['tier'],
                         'with no history, resolve is exactly decide')

    def test_two_settled_missions_are_below_the_floor(self):
        for index in range(2):
            self.seed_mission(index, 'D1', blocked=True)
        advice = outcome_advice(self.store, FEATURES_D1)
        self.assertEqual(advice['direction'], 'none')
        self.assertIn('2 settled missions at D1', advice['reasons'][0])

    def test_blocker_history_asks_for_one_more_step(self):
        for index in range(3):
            self.seed_mission(index, 'D1', blocked=True)
        advice = outcome_advice(self.store, FEATURES_D1)
        self.assertEqual(advice['direction'], 'raise')
        self.assertEqual(advice['advised_tier'], 'D2')
        self.assertTrue(advice['applied'])
        self.assertIn('3 of 3 settled missions at D1', advice['reasons'][0])

    def test_clean_history_asks_for_one_fewer_specialist(self):
        for index in range(3):
            self.seed_mission(index, 'D2')
        advice = outcome_advice(self.store, FEATURES_D2_LOWD)
        self.assertEqual(advice['direction'], 'lower')
        self.assertEqual(advice['advised_tier'], 'D1')
        self.assertTrue(advice['applied'])
        self.assertIn('without blocker-class findings', advice['reasons'][0])

    def test_hard_rule_floor_holds_against_a_lower(self):
        for index in range(3):
            self.seed_mission(index, 'D2')
        advice = outcome_advice(self.store, FEATURES_D2_LOWD, flags=('security_boundary',))
        self.assertEqual(advice['advised_tier'], 'D2')
        self.assertFalse(advice['applied'])
        self.assertTrue(any('requires at least D2' in reason for reason in advice['reasons']))

    def test_mixed_history_is_not_evidence(self):
        self.seed_mission(0, 'D1', blocked=True)
        self.seed_mission(1, 'D1', blocked=True)
        self.seed_mission(2, 'D1')
        advice = outcome_advice(self.store, FEATURES_D1)
        self.assertEqual(advice['direction'], 'none')
        self.assertIn('mixed history', advice['reasons'][0])

    def test_the_raise_never_breaks_the_rule_table(self):
        for index in range(3):
            self.seed_mission(index, 'D2', blocked=True)
        advice = outcome_advice(self.store, FEATURES_D2_LOWD)
        self.assertEqual(advice['advised_tier'], 'D2', 'R1-capable work stays at D2')
        self.assertFalse(advice['applied'])
        self.assertTrue(any('D2' in reason for reason in advice['reasons'][1:]))

    def test_resolve_applies_the_legal_step(self):
        for index in range(3):
            self.seed_mission(index, 'D1', blocked=True)
        decision = resolve(self.store, FEATURES_D1)
        self.assertEqual(decision['tier'], 'D2')
        self.assertTrue(decision['advice']['applied'])
        self.assertEqual(decide(FEATURES_D1)['tier'], 'D1', 'the plain rule table is untouched')

    def test_graceful_without_workforce_tables(self):
        bare = Store(Path(self.tmp.name) / 'bare')
        advice = outcome_advice(bare, FEATURES_D1)
        self.assertEqual(advice['direction'], 'none')
        self.assertEqual(advice['history']['settled'], 0)


class PathTests(Base):
    def test_delegation_honours_a_lower_to_solo(self):
        for index in range(3):
            self.seed_mission(index, 'D1')
        job_id = self.store.create(contract(), conversation='main')
        result = delegate(self.store, job_id, 'm1', {'objective': 'Probe'},
                          features=FEATURES_D1, enabled=True, candidates=candidates())
        self.assertFalse(result['delegated'])
        self.assertEqual(result['staffing']['tier'], 'D0')
        self.assertEqual(result['staffing']['advice']['direction'], 'lower')
        self.assertTrue(any('history advice applied' in reason
                            for reason in result['staffing']['reasons']))

    def test_delegation_without_history_delegates_exactly_as_before(self):
        job_id = self.store.create(contract(), conversation='main')
        result = delegate(self.store, job_id, 'm1', {'objective': 'Probe'},
                          features=FEATURES_D1, enabled=True, candidates=candidates())
        self.assertTrue(result['delegated'], 'no history must change nothing')
        self.assertEqual(result['staffing']['tier'], 'D1')
        self.assertFalse(result['staffing']['advice']['applied'])
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute("SELECT detail FROM team_events WHERE kind='staffing.decided'"
                             " ORDER BY seq DESC LIMIT 1").fetchone()
        detail = json.loads(row['detail'])
        self.assertEqual(detail['tier'], 'D1')
        self.assertIn('advice', detail, 'every recorded decision carries its learned basis')

    def test_a_raise_is_recorded_not_smuggled_into_the_d1_path(self):
        for index in range(3):
            self.seed_mission(index, 'D1', blocked=True)
        job_id = self.store.create(contract(), conversation='main')
        result = delegate(self.store, job_id, 'm1', {'objective': 'Probe'},
                          features=FEATURES_D1, enabled=True, candidates=candidates())
        self.assertTrue(result['delegated'], 'the D1 path still carries one specialist')
        self.assertEqual(result['staffing']['tier'], 'D1')
        self.assertEqual(result['staffing']['advice']['direction'], 'raise')

    def test_the_pods_path_refuses_with_the_reason_when_history_steps_down(self):
        for index in range(3):
            self.seed_mission(index, 'D2')
        from kel.pods import run_d2
        job_id = self.store.create(contract(), conversation='main')
        with self.assertRaises(PolicyError) as raised:
            run_d2(self.store, job_id, 'm1', {'objective': 'Probe'}, None, None,
                   features=FEATURES_D2_LOWD, enabled=True)
        message = str(raised.exception)
        self.assertIn('D2 staffing decision', message)
        self.assertIn('run_d1', message)


if __name__ == '__main__':
    unittest.main()
