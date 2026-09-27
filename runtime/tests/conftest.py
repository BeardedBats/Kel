"""Suite-wide guard: tests never reach a real turn model (D-53).

The conversational turn decision would otherwise call an installed CLI (codex/claude) or the
internal API. Tests that exercise the turn model inject a fake one explicitly.
"""
import os

os.environ.setdefault('KEL_TURN_MODEL', 'none')
