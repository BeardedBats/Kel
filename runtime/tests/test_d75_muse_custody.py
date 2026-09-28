"""D-75.3: one key flow — the Muse (Ramble) key lives in the desktop's credential custody.

The desktop's main process supplies it (at spawn and whenever it changes, in memory only); the
key Ramble saved before keeps working until it is moved into custody, and then its plaintext copy is
dropped. Clearing custody clears Kel's copies only (the Transcriptions app's own key stays readable).
"""
import os
import tempfile
import unittest
from unittest import mock

from kel import transcription
from kel.core import Store
from kel.internal import SECRET_ENV_KEYS
from kel.native import child_env
from kel.transcription import Transcription


class MuseCustodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = mock.patch.dict(os.environ, {}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        for name in ('META_API_KEY', 'MUSE_API_KEY', 'KEL_TRANSCRIPTION_PROVIDER', 'KEL_TRANSCRIPTION_MODE'):
            os.environ.pop(name, None)
        self.shared = mock.patch.object(transcription, 'shared_muse_key', return_value='')
        self.shared.start()
        self.addCleanup(self.shared.stop)
        saved = dict(transcription._CUSTODY)
        self.addCleanup(lambda: transcription._CUSTODY.update(saved))
        transcription._CUSTODY['key'] = ''
        self.t = Transcription(Store(self.tmp.name))

    def test_a_supplied_key_is_used_and_clearing_it_says_so(self):
        self.assertEqual(self.t.status()['mode'], 'unavailable')
        self.assertEqual(self.t.supply('custody-key'), {'has_key': True, 'source': 'kel'})
        self.assertEqual(self.t.api_key(), 'custody-key')
        self.assertEqual(self.t.status()['source'], 'kel')
        self.assertEqual(self.t.supply(clear=True), {'has_key': False, 'source': ''})

    def test_the_key_ramble_saved_keeps_working_until_it_moves_into_custody(self):
        self.t.set_key('older-ramble-key')  # the pre-D-75.3 plaintext copy
        self.assertEqual(self.t.api_key(), 'older-ramble-key')
        self.assertEqual(self.t.legacy_key(), {'key': 'older-ramble-key'})
        # The desktop stores it in custody, then supplies it back and drops the plaintext copy.
        self.t.supply('older-ramble-key', drop_legacy=True)
        self.assertEqual(self.t.legacy_key(), {'key': ''})
        self.assertEqual(self.t.api_key(), 'older-ramble-key')

    def test_clearing_leaves_the_transcriptions_apps_own_key(self):
        self.shared.stop()
        with mock.patch.object(transcription, 'shared_muse_key', return_value='app-key'):
            self.t.supply('custody-key')
            out = self.t.supply(clear=True)
            self.assertEqual(out, {'has_key': True, 'source': 'transcriptions-app'})
        self.shared.start()

    def test_the_spawn_value_never_reaches_a_child_process(self):
        self.assertIn('MUSE_CUSTODY_KEY', SECRET_ENV_KEYS)
        env = child_env('claude', base={'MUSE_CUSTODY_KEY': 'x', 'PATH': 'p'})
        self.assertNotIn('MUSE_CUSTODY_KEY', env)


if __name__ == '__main__':
    unittest.main()
