"""V1.6 P2/P3 sweep fixes: multipart header hygiene (SEC-01-multipart) and credentials kept out of
backups (PER-04).

Both findings were verified against the tree during the sweep: `_multipart` interpolated the
caller's filename into `Content-Disposition` unescaped, and a `KEL_DATA_DIR` override can place
`kel-credentials.json` inside the data root that backups copy.
"""
import tempfile
import unittest
from pathlib import Path

import kel.backup as backup
from kel.backup import Backup, MARKER, NEVER_BACKUP, STAGING, apply_pending_restore
from kel.core import PolicyError
from kel.service import Service
from kel.transcription import _header_safe, _multipart


class MultipartHeaderTests(unittest.TestCase):
    def test_a_malicious_filename_cannot_inject_a_part(self):
        evil = 'ok.wav"\r\nContent-Disposition: form-data; name="injected"\r\n\r\npwned'
        body = _multipart('BOUNDARY', [('file', evil, 'audio/wav', b'AUDIO')])
        # The injected text survives as *inline* text inside the parameter, but it can never start a
        # header line of its own, and the part count is unchanged.
        self.assertNotIn(b'\r\nContent-Disposition: form-data; name="injected"', body)
        headers = [line for line in body.split(b'\r\n') if line.startswith(b'Content-Disposition:')]
        self.assertEqual(len(headers), 1)
        self.assertIn(b'name="file"', headers[0])
        self.assertEqual(body.count(b'--BOUNDARY\r\n'), 1)
        self.assertIn(b'AUDIO', body)

    def test_a_clean_filename_still_round_trips(self):
        body = _multipart('BOUNDARY', [('file', 'note.wav', 'audio/wav', b'AUDIO')])
        self.assertIn(b'name="file"; filename="note.wav"', body)
        self.assertTrue(body.endswith(b'--BOUNDARY--\r\n'))

    def test_header_safe_folds_line_breaks_quotes_and_backslashes(self):
        self.assertEqual(_header_safe('a"\r\nb\\c'), "a'  b/c")
        self.assertEqual(_header_safe(None), '')


class BackupCredentialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'data'
        self.root.mkdir()
        (self.root / 'kel-credentials.json').write_text('{"openai": "encrypted"}', encoding='utf-8')
        (self.root / 'notes.txt').write_text('keep me', encoding='utf-8')
        self.dest = Path(self.tmp.name) / 'dest'
        self.dest.mkdir()

    def test_a_backup_never_captures_the_credentials_file(self):
        result = Backup(_Store(self.root)).create(self.dest)
        names = {entry.name for entry in Path(result['folder']).iterdir()}
        self.assertNotIn('kel-credentials.json', names)
        self.assertIn('notes.txt', names)
        self.assertIn('kel-credentials.json', result['skipped'])
        self.assertIn('kel-credentials.json', result['notes'])

    def test_the_guard_is_named_for_the_credentials_file(self):
        self.assertIn('kel-credentials.json', NEVER_BACKUP)


class SnapshotRetentionTests(unittest.TestCase):
    """PER-03: pre-restore snapshots must not accumulate without bound."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'data'
        self.root.mkdir()
        for stamp in ('20260101-000000', '20260102-000000', '20260103-000000'):
            snapshot = self.root.parent / ('data.pre-restore-' + stamp)
            snapshot.mkdir()
            (snapshot / 'old.txt').write_text(stamp, encoding='utf-8')

    def _snapshots(self):
        return sorted(entry.name for entry in self.root.parent.glob('data.pre-restore-*'))

    def test_an_applied_restore_keeps_only_the_newest_two_snapshots(self):
        (self.root / STAGING).mkdir(mode=0o700)
        (self.root / MARKER).write_text('{}', encoding='utf-8')
        self.assertTrue(apply_pending_restore(_Store(self.root)))
        names = self._snapshots()
        self.assertEqual(len(names), 2, names)
        self.assertIn('data.pre-restore-20260103-000000', names)
        self.assertNotIn('data.pre-restore-20260101-000000', names)
        self.assertTrue((self.root.parent / 'data.pre-restore-20260103-000000' / 'old.txt').exists())

    def test_a_failed_restore_still_prunes_and_keeps_its_own_snapshot(self):
        (self.root / STAGING).mkdir(mode=0o700)
        (self.root / 'notes.txt').write_text('live', encoding='utf-8')
        (self.root / STAGING / 'notes.txt').write_text('staged', encoding='utf-8')
        (self.root / MARKER).write_text('{}', encoding='utf-8')
        original = backup._restore_entry

        def explode(source, destination):
            raise OSError('no space left on device')

        backup._restore_entry = explode
        self.addCleanup(setattr, backup, '_restore_entry', original)
        self.assertFalse(apply_pending_restore(_Store(self.root)))
        names = self._snapshots()
        self.assertEqual(len(names), 2, names)
        self.assertTrue((self.root / MARKER).exists(), 'the restore is still pending')
        newest = self.root.parent / names[-1]
        self.assertTrue((newest / 'notes.txt').read_text(encoding='utf-8') == 'live')


class ApprovalActorGuardTests(unittest.TestCase):
    """APR-01: actor identity comes from the session, never from the payload — pinned by a test."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.service = Service(str(Path(self.tmp.name) / 'data'))
        self.addCleanup(self.service.shutdown)

    def test_the_approval_route_refuses_a_payload_actor(self):
        with self.assertRaises(PolicyError) as caught:
            self.service._action('/api/approval',
                                 {'id': 'apr_missing', 'allow': True, 'actor': 'user'})
        self.assertIn('authenticated Kel session', str(caught.exception))

    def test_the_same_guard_covers_the_other_action_families(self):
        for path, payload in (('/api/memory', {'action': 'list'}), ('/api/map', {'action': 'list'})):
            with self.assertRaises(PolicyError):
                self.service._action(path, dict(payload, actor='system'))


class _Store:
    """Minimal stand-in: the backup path reads `root` and `db_path` only."""

    def __init__(self, root):
        self.root = Path(root)
        self.db_path = Path(root) / 'kel.sqlite3'


if __name__ == '__main__':
    unittest.main()
