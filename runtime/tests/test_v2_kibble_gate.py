"""Priority 9 — the promotion gate's inspection door (Kibble Build Update backend foundation).

Measured first: the directive and roadmap define no "Kibble" section anywhere, and the only in-repo
placement of Ramble/Kibble is Astra's Shell presentation lane (MARATHON_STATE parallel-ownership).
What the queue line names as the backend foundation — the **promotion gate** — already exists as
recorded-never-applied machinery (`learning.queue_promotion` → `proposal.queued` events;
`learning.shadow_proposal` → `staffing.proposed` events with predictions). What was missing was a
door to SEE it. These pins cover that door only: read-only, project-scoped, honest notes, and zero
side effects. The dev-mission schema and candidate model that would define a Kibble Build Update are
deferred pending Nick's definition (D-44) — not guessed here.
"""
import contextlib
import tempfile
import unittest
from pathlib import Path

from kel.assignment import ensure_schema as ensure_assignment_schema
from kel.context import Context
from kel.core import Store
from kel.learning import queue_promotion, shadow_proposal
from kel.memory import ensure_schema as ensure_memory_schema
from kel.team import Team
from kel.team import ensure_schema as ensure_team_schema
from kel.workforce import ensure_schema as ensure_workforce_schema

SHADOW_ON = {'workforce.enabled': True, 'workforce.learning.shadow': True}
SHADOW_OFF = {'workforce.enabled': True, 'workforce.learning.shadow': False}
PROJECT = 'proj-gate'
OTHER = 'proj-other'
MISSION = 'mis_gate'


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.store = Store(Path(self.tmp.name) / 'data')
        ensure_workforce_schema(self.store)
        ensure_assignment_schema(self.store)
        ensure_team_schema(self.store)
        ensure_memory_schema(self.store)
        self.context = Context(self.store)
        self.context.project('Gate Project', project_id=PROJECT)
        self.context.project('Other Project', project_id=OTHER)
        self.team = Team(self.store)

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def counts(self):
        with contextlib.closing(self.store.connect()) as db:
            return {
                'team_events': db.execute('SELECT COUNT(*) FROM team_events').fetchone()[0],
                'memories': db.execute('SELECT COUNT(*) FROM memories').fetchone()[0],
            }


class DoorTests(Base):
    def test_an_empty_queue_reads_as_zero_with_the_honest_note(self):
        result = self.team.apply({'action': 'promotions', 'project_id': PROJECT})
        self.assertEqual(result['count'], 0)
        self.assertIn('never applied', result['note'])
        self.assertIn('explicit decision', result['note'])

    def test_a_queued_promotion_is_visible_and_project_scoped(self):
        queued = queue_promotion(self.store, project_id=PROJECT, proposal_kind='learning.promotion',
                                 subject='a.b', requested={'confidence': 8},
                                 basis={'cap': 5}, flags=SHADOW_ON)
        self.assertTrue(queued['recorded'])
        result = self.team.apply({'action': 'promotions', 'project_id': PROJECT})
        self.assertEqual(result['count'], 1)
        item = result['promotions'][0]
        self.assertEqual(item['subject'], 'a.b')
        self.assertEqual(item['proposal_kind'], 'learning.promotion')
        self.assertEqual(item['state'], 'queued')
        other = self.team.apply({'action': 'promotions', 'project_id': OTHER})
        self.assertEqual(other['count'], 0, 'the queue is project-scoped')

    def test_a_shadow_proposal_is_visible_with_its_prediction(self):
        recorded = shadow_proposal(self.store, project_id=PROJECT, mission_id=MISSION,
                                   proposal={'change': 'keep or raise the tier'},
                                   prediction={'escaped_defects_delta': 0},
                                   confidence='low', basis=['finder-1'], flags=SHADOW_ON)
        self.assertTrue(recorded['recorded'])
        result = self.team.apply({'action': 'shadow', 'project_id': PROJECT})
        self.assertEqual(result['count'], 1)
        item = result['proposals'][0]
        self.assertEqual(item['state'], 'shadow')
        self.assertEqual(item['prediction'], {'escaped_defects_delta': 0})
        self.assertIn('nothing here has been applied', result['note'])
        filtered = self.team.apply({'action': 'shadow', 'project_id': PROJECT,
                                    'mission_id': 'mis_absent'})
        self.assertEqual(filtered['count'], 0, 'mission filtering works')

    def test_the_door_is_read_only(self):
        queue_promotion(self.store, project_id=PROJECT, proposal_kind='learning.promotion',
                        subject='x', requested={}, flags=SHADOW_ON)
        shadow_proposal(self.store, project_id=PROJECT, mission_id=MISSION,
                        proposal={'change': 'c'}, prediction={'p': 1}, confidence='low',
                        flags=SHADOW_ON)
        before = self.counts()
        self.team.apply({'action': 'promotions', 'project_id': PROJECT})
        self.team.apply({'action': 'shadow', 'project_id': PROJECT})
        self.assertEqual(self.counts(), before, 'reads write nothing')

    def test_nothing_is_recorded_when_the_shadow_flag_is_off(self):
        result = queue_promotion(self.store, project_id=PROJECT, proposal_kind='learning.promotion',
                                 subject='x', requested={}, flags=SHADOW_OFF)
        self.assertFalse(result['recorded'])
        self.assertEqual(self.team.apply({'action': 'promotions',
                                          'project_id': PROJECT})['count'], 0)


if __name__ == '__main__':
    unittest.main()
