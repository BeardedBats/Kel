"""V1.6 REQ-RK: record-bound resolution kinds on findings (audit carry-forward F18-5).

The learning loop used to infer "accepted risk" from a prefix on the free-text
`dismissal_reason`. The kind is now a column written by the guarded resolution paths
(`resolve_finding`, `waive_gate`) and read by `lens_stats`; rows written before v17 are derived
once from the guarded marker, and free text is never parsed for new rows.
"""
import contextlib
import tempfile
import unittest
from pathlib import Path

from kel.assurance import (ACCEPTANCE_KINDS, RESOLUTION_KINDS, findings, lens_stats,
                           record_finding, resolve_finding, validate_finding, waive_gate)
from kel.core import PolicyError, Store
from kel.evidence import write_evidence
from kel.workforce import MIGRATION_VERSION, ensure_schema as ensure_workforce_schema

TASK = 'tsk_' + 'b' * 8
MISSION = 'mis_' + 'a' * 8


def finding(lens='maintainability', **overrides):
    body = {'id': 'find_' + 'd' * 8, 'schema_version': 1, 'mission_id': MISSION,
            'task_id': TASK, 'lens': lens,
            'severity': 'critical', 'confidence': 8, 'artifact': 'art_x', 'location': 'loc',
            'summary': 'Review found a defect.', 'evidence': 'fixture', 'fix': '',
            'fingerprint': 'fp-%s' % lens, 'status': 'open',
            'by': {'lens': lens, 'model_family': 'fixture', 'assignment': 'asn_' + 'c' * 8}}
    body.update(overrides)
    return body


class ResolutionKindTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'data')
        ensure_workforce_schema(self.store)

    def _record(self, fingerprint, *, lens='maintainability', severity='critical'):
        return record_finding(self.store, finding(lens=lens, severity=severity,
                                                  fingerprint=fingerprint,
                                                  id='find_' + fingerprint.replace('-', '')),
                              now=1000.0)

    def _kinds(self):
        return {row['id']: row['resolution_kind'] for row in findings(self.store)}

    def test_vocabulary_is_enforced(self):
        self.assertEqual(validate_finding(finding(resolution_kind='gate-waived'))['resolution_kind'],
                         'gate-waived')
        with self.assertRaises(PolicyError):
            validate_finding(finding(resolution_kind='because-i-said-so'))
        self.assertEqual(set(RESOLUTION_KINDS), {'fixed', 'risk-accepted', 'gate-waived',
                                                 'false-positive'})
        self.assertEqual(set(ACCEPTANCE_KINDS), {'risk-accepted', 'gate-waived'})

    def test_guarded_paths_write_the_kind(self):
        record = self._record('fp-dismissed')
        updated = resolve_finding(self.store, record['id'], resolution='dismissed',
                                  rationale='not a defect')
        self.assertEqual(updated['resolution_kind'], 'false-positive')
        self.assertTrue(updated['dismissal_reason'].startswith('dismissed:'))

        accepted = self._record('fp-accepted')
        updated = resolve_finding(self.store, accepted['id'], resolution='accepted',
                                  rationale='pilot risk, user informed')
        self.assertEqual(updated['resolution_kind'], 'risk-accepted')

        fixed = self._record('fp-fixed')
        evidence = write_evidence(self.store, mission_id=MISSION, task_id=TASK,
                                  evidence_class='test_run', label='suite', produced_by='fixture',
                                  command='python -m pytest -q', output='green')
        updated = resolve_finding(self.store, fixed['id'], resolution='fixed',
                                  evidence_ref=evidence['id'])
        self.assertEqual(updated['resolution_kind'], 'fixed')

    def test_waive_gate_writes_gate_waived(self):
        record = self._record('fp-waived', severity='blocker')
        self.assertTrue(waive_gate(self.store, task_id=TASK, authority='user',
                                   rationale='ship the pilot')['waived'])
        self.assertEqual(self._kinds()[record['id']], 'gate-waived')

    def test_the_column_wins_over_the_reason_text(self):
        # A hand-written acceptance marker must not count as an acceptance when the record says
        # false-positive (this is exactly what the old prefix test got wrong).
        record = self._record('fp-spoof')
        with contextlib.closing(self.store.connect()) as db:
            db.execute("UPDATE findings SET status='dismissed', dismissal_reason=?, "
                       "resolution_kind=? WHERE id=?",
                       ('risk-accepted: hand written', 'false-positive', record['id']))
        stats = lens_stats(self.store)
        self.assertEqual(stats['maintainability']['accepted'], 0)
        self.assertEqual(stats['maintainability']['false_positive'], 1)

        # And a real acceptance keeps counting even if the human-readable reason is reworded.
        accepted = self._record('fp-rewritten')
        resolve_finding(self.store, accepted['id'], resolution='accepted', rationale='pilot risk')
        with contextlib.closing(self.store.connect()) as db:
            db.execute("UPDATE findings SET dismissal_reason='reworded rationale' WHERE id=?",
                       (accepted['id'],))
        stats = lens_stats(self.store)
        self.assertEqual(stats['maintainability']['accepted'], 1)

    def test_legacy_rows_without_a_kind_are_derived_once(self):
        record = self._record('fp-legacy')
        with contextlib.closing(self.store.connect()) as db:
            db.execute("UPDATE findings SET status='dismissed', dismissal_reason=?, "
                       "resolution_kind=NULL WHERE id=?",
                       ('risk-accepted: legacy row', record['id']))
        self.assertEqual(lens_stats(self.store)['maintainability']['accepted'], 1)
        self.assertIsNone(self._kinds()[record['id']])

    def test_migration_adds_the_column_to_an_existing_database(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        legacy = Store(Path(tmp.name) / 'legacy')
        ensure_workforce_schema(legacy)
        with contextlib.closing(legacy.connect()) as db:
            db.execute('ALTER TABLE findings DROP COLUMN resolution_kind')  # pre-v17 shape
            db.execute('DELETE FROM schema_migrations WHERE version=?', (MIGRATION_VERSION,))
            before = [row[1] for row in db.execute('PRAGMA table_info(findings)')]
        self.assertNotIn('resolution_kind', before)
        ensure_workforce_schema(legacy)
        with contextlib.closing(legacy.connect()) as db:
            after = [row[1] for row in db.execute('PRAGMA table_info(findings)')]
            recorded = db.execute('SELECT name FROM schema_migrations WHERE version=?',
                                  (MIGRATION_VERSION,)).fetchone()
        self.assertIn('resolution_kind', after)
        self.assertEqual(recorded['name'], 'v17-finding-resolution-kind')
        # Idempotent: a second run changes nothing.
        with contextlib.closing(legacy.connect()) as db:
            rows_before = len(list(db.execute('SELECT * FROM schema_migrations')))
        ensure_workforce_schema(legacy)
        with contextlib.closing(legacy.connect()) as db:
            rows_after = len(list(db.execute('SELECT * FROM schema_migrations')))
        self.assertEqual(rows_before, rows_after)


if __name__ == '__main__':
    unittest.main()
