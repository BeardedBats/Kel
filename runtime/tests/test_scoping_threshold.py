"""The scoping threshold as a Settings choice (Settings → Staff & models): always for bigger work (the
default, a Builder + Verifier pod or larger), only for very big work, or never. One engine setting.
Fake models only.
"""
import sys
import unittest
from pathlib import Path

from kel import scoping
from kel.core import PolicyError

sys.path.insert(0, str(Path(__file__).parent))
from test_d70_cards import BIG_WORK, PLUMBING, QUESTIONS, SMALL_WORK, ServiceBase  # noqa: E402


class ThresholdSettingTests(ServiceBase):
    def test_the_choices_are_plain_and_the_default_is_bigger_work(self):
        view = self.service.action('/api/scoping', {'action': 'threshold'})
        self.assertEqual(view['threshold'], 'D2')
        self.assertEqual([(o['id'], o['label']) for o in view['options']],
                         [('D2', 'Always for bigger work'), ('D3', 'Only for very big work'), ('never', 'Never')])

    def test_setting_it_changes_what_is_scoped(self):
        out = self.service.action('/api/scoping', {'action': 'set_threshold', 'value': 'D3'})
        self.assertEqual(out['threshold'], 'D3')
        self.assertEqual(scoping.threshold(self.service.store), 'D3')
        # A pod-sized request no longer waits for questions.
        self.turn.answer = BIG_WORK
        sid = self.service.submit({'text': PLUMBING, 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'DISPATCHED')
        self.assertEqual(self.scopings(), [])

    def test_never_means_never_even_with_open_questions(self):
        self.service.action('/api/scoping', {'action': 'set_threshold', 'value': 'never'})
        self.turn.answer = dict(SMALL_WORK, scoping=QUESTIONS)
        sid = self.service.submit({'text': 'Write me a spring garden plan for the back yard', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'DISPATCHED')
        self.assertEqual(self.scopings(), [])

    def test_an_older_value_is_still_named_and_bad_values_refused(self):
        scoping.set_threshold(self.service.store, 'off')
        view = scoping.threshold_view(self.service.store)
        self.assertEqual(view['options'][-1]['label'], 'Only when Kel has open questions')
        with self.assertRaisesRegex(PolicyError, 'never'):
            self.service.action('/api/scoping', {'action': 'set_threshold', 'value': 'huge'})


if __name__ == '__main__':
    unittest.main()
