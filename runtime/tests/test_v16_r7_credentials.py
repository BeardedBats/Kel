"""Round 2.5 R7 — CREDENTIAL-CONTAINMENT: a provider process gets the credential it needs and
nothing else, and a raw credential never becomes prompts, artifacts, packets, logs, diagnostics or
durable content.

The inventory and the honest network-boundary statement are recorded in
`docs/v1.6/pre-audit/increments/R7-CREDENTIAL-BOUNDARY.md`. Every test uses synthetic sentinel
values injected into the environment, and restores the environment afterwards.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kel.core import PolicyError  # noqa: E402
from kel.internal import child_env, redact  # noqa: E402
from kel.memory import scan_secret  # noqa: E402
from kel.workforce import assert_safe  # noqa: E402

KEYS = ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'DEEPSEEK_API_KEY')
SENTINEL = 'sk-' + 'sentinel0' * 4  # secret-shaped (matches the api-key pattern)


class CredentialContainmentTests(unittest.TestCase):
    def setUp(self):
        self.saved = {name: os.environ.get(name) for name in KEYS}
        for name in KEYS:
            os.environ[name] = SENTINEL
        self.addCleanup(self._restore)

    def _restore(self):
        for name, value in self.saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def test_a_child_receives_only_the_credential_it_requires(self):
        claude = child_env(keep=('ANTHROPIC_API_KEY',))
        self.assertEqual(claude['ANTHROPIC_API_KEY'], SENTINEL)
        self.assertNotIn('OPENAI_API_KEY', claude)
        self.assertNotIn('DEEPSEEK_API_KEY', claude)
        codex = child_env(keep=('OPENAI_API_KEY',))
        self.assertEqual(codex['OPENAI_API_KEY'], SENTINEL)
        self.assertNotIn('ANTHROPIC_API_KEY', codex)
        self.assertNotIn('DEEPSEEK_API_KEY', codex)

    def test_a_child_that_needs_no_provider_credential_receives_none(self):
        env = child_env()
        for name in KEYS:
            self.assertNotIn(name, env)

    def test_redact_masks_live_values_and_secret_shaped_tokens(self):
        self.assertNotIn(SENTINEL, redact('boom: ' + SENTINEL))
        self.assertIn('[redacted]', redact('key ' + SENTINEL))
        self.assertIn('[redacted]', redact('Authorization: Bearer sk-abc1234567890'))
        self.assertEqual(redact('ordinary text'), 'ordinary text')

    def test_a_secret_shaped_value_is_detected_before_it_becomes_durable(self):
        self.assertIsNotNone(scan_secret('token ' + SENTINEL))
        self.assertIsNone(scan_secret('an ordinary sentence'))
        with self.assertRaises(PolicyError) as caught:
            assert_safe({'note': 'remember to rotate ' + SENTINEL}, path='record.note')
        self.assertIn('Unsafe workforce record', str(caught.exception))

    def test_the_containment_is_wired_where_processes_are_spawned(self):
        root = Path(__file__).resolve().parent.parent / 'kel'
        appserver = (root / 'appserver.py').read_text(encoding='utf-8')
        self.assertNotIn('os.environ.copy()', appserver)
        self.assertIn('child_env(keep=(\'OPENAI_API_KEY\',))', appserver)
        coding = (root / 'coding.py').read_text(encoding='utf-8')
        for name in KEYS:
            self.assertIn("'%s':None" % name, coding)
