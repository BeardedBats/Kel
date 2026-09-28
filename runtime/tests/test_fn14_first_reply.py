"""FN-14: Diagnostics' "First model reply" reads real measurements: how long Kel's model took to
answer recent messages, from the usage Kel records for its own turn and reply calls (D-72)."""
import tempfile
import unittest

from kel.context import Context
from kel.core import Store
from kel.diagnostics import Diagnostics
from kel.usage import record


class FirstReplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        Context(self.store)

    def test_nothing_measured_is_none_not_a_placeholder(self):
        self.assertIsNone(Diagnostics(self.store).performance()['first_reply'])

    def test_recent_turns_give_latest_and_typical(self):
        for index, wall in enumerate((4000, 2000, 3000)):
            record(self.store, 'turn:s%d:x' % index, kind='turn', adapter='claude', model='sonnet',
                   result={'outcome': 'SUCCESS'}, wall=wall)
        record(self.store, 'work:j:x', kind='work', adapter='codex', result={'outcome': 'SUCCESS'}, wall=90000)
        out = Diagnostics(self.store).performance()['first_reply']
        self.assertEqual((out['latest_ms'], out['median_ms'], out['samples']), (3000.0, 3000.0, 3))


if __name__ == '__main__':
    unittest.main()
