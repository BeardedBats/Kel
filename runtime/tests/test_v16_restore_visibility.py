"""V1.6 PER-02: a failed or partial restore is recorded and surfaced, never silent.

The engine used to discard `apply_pending_restore`'s boolean inside `try/except: pass`, so a
restore that could not even start (or that failed halfway) left no trace the user or the app could
see. The outcome now lands in `restore-outcome.json` beside the data (the database is what a
restore replaces, so the record cannot live in it) and is exposed through `Service.state()`.
"""
import contextlib
import json
import tempfile
import time
import unittest
from pathlib import Path

from kel import backup
from kel.backup import MARKER, OUTCOME, STAGING, apply_pending_restore
from kel.service import Service


class RestoreOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'data'
        self.root.mkdir(parents=True)

    def _pending_restore(self):
        """A staged restore with one file to merge back."""
        staging = self.root / STAGING
        staging.mkdir(parents=True, exist_ok=True)
        (staging / 'notes.txt').write_text('restored\n', encoding='utf-8')
        (self.root / MARKER).write_text(json.dumps({'at': time.time()}), encoding='utf-8')

    def _recorded_outcome(self):
        # Not `_outcome`: that name is unittest.TestCase's own bookkeeping attribute.
        path = self.root / OUTCOME
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None

    def test_nothing_pending_records_nothing(self):
        self.assertFalse(apply_pending_restore(_Store(self.root)))
        self.assertIsNone(self._recorded_outcome())

    def test_a_successful_restore_is_recorded(self):
        self._pending_restore()
        self.assertTrue(apply_pending_restore(_Store(self.root)))
        outcome = self._recorded_outcome()
        self.assertTrue(outcome['ok'])
        self.assertFalse((self.root / MARKER).exists())  # the marker still means "applied"

    def test_a_failed_restore_is_recorded_and_keeps_its_marker(self):
        self._pending_restore()
        original = backup._restore_entry

        def explode(source, destination):
            raise OSError('disk went away')

        backup._restore_entry = explode
        self.addCleanup(setattr, backup, '_restore_entry', original)
        self.assertFalse(apply_pending_restore(_Store(self.root)))
        outcome = self._recorded_outcome()
        self.assertFalse(outcome['ok'])
        self.assertEqual(outcome['detail'], 'OSError')
        self.assertTrue((self.root / MARKER).exists(), 'a half-applied restore must keep its marker')

    def test_the_service_survives_a_restore_that_cannot_start_and_surfaces_it(self):
        original = backup.apply_pending_restore

        def explode(store):
            raise RuntimeError('staging is unreadable')

        # `Service.__init__` imports the symbol at call time, so patching the module is enough.
        backup.apply_pending_restore = explode
        self.addCleanup(setattr, backup, 'apply_pending_restore', original)
        service = Service(str(self.root))
        self.addCleanup(service.shutdown)
        state = service.state()
        self.assertIn('restore', state)
        self.assertFalse(state['restore']['ok'])
        self.assertEqual(state['restore']['detail'], 'RuntimeError')

    def test_a_clean_start_reports_no_restore_attempt(self):
        service = Service(str(self.root))
        self.addCleanup(service.shutdown)
        self.assertIsNone(service.state()['restore'])


class _Store:
    """Minimal stand-in: the restore path only needs `.root`."""

    def __init__(self, root):
        self.root = Path(root)

    def connect(self):
        raise AssertionError('the restore path must not open the databases')


if __name__ == '__main__':
    unittest.main()
