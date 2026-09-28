"""VIS-24: Providers speaks plain names — models carry their labels, and Claude is named the same
way on Providers as on the Model page ("Claude (built-in)")."""
import tempfile
import unittest

from kel.core import Store
from kel.model_prefs import MODEL_LABELS
from kel.providers import Providers


class ProviderNameTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.providers = Providers(Store(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_model_carries_its_plain_name(self):
        for entry in self.providers.all_status():
            for model in entry['models']:
                self.assertEqual(model['label'], MODEL_LABELS[model['id']])

    def test_claude_is_named_like_the_model_page(self):
        claude = self.providers.status('claude-code')
        self.assertEqual(claude['label'], 'Claude (built-in)')
        self.assertEqual(claude['label'], MODEL_LABELS['claude-native'])

    def test_readiness_names_the_chosen_model(self):
        self.providers.set_credential_metadata('internal', ['api_key'], 'kel:provider:internal:api_key')
        chosen = self.providers.readiness('vision')['chosen']
        if chosen:
            self.assertEqual(chosen['model_label'], MODEL_LABELS[chosen['model']])


if __name__ == '__main__':
    unittest.main()
