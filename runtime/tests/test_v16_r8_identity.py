"""Round 2.5 R8.B — package identity.

The desktop refuses to reuse a live engine whose reported version differs from the app it shipped
with (`engineVersionAccepted`, expectation = `app.getVersion()` = `desktop/package.json`'s version).
The engine reports its own `__version__` in the descriptor and in `/api/state`. These tests pin the
two ends together so a release can never ship an engine whose identity disagrees with its desktop.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kel import __version__  # noqa: E402
from kel import service  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent


class EngineIdentityTests(unittest.TestCase):
    def test_the_engine_reports_one_version_everywhere(self):
        self.assertEqual(service.ENGINE_VERSION, __version__)
        self.assertEqual(__version__, '1.6.0')

    def test_the_desktop_expects_exactly_the_engine_it_ships(self):
        desktop = json.loads((REPO / 'desktop' / 'package.json').read_text(encoding='utf-8'))
        self.assertEqual(desktop['version'], __version__,
                         'desktop/package.json version (app.getVersion()) must equal the engine '
                         'version, or the packaged app refuses its own engine')

    def test_the_descriptor_and_state_carry_that_version(self):
        source = (REPO / 'runtime' / 'kel' / 'service.py').read_text(encoding='utf-8')
        self.assertEqual(source.count("'engine_version':ENGINE_VERSION"), 3)
        self.assertNotIn("ENGINE_VERSION='", source)  # no second literal to drift
