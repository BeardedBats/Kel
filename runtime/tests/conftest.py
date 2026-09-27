"""Suite-wide guard: tests never reach a real turn model (D-53).

The conversational turn decision would otherwise call an installed CLI (codex/claude) or the
internal API. Tests that exercise the turn model inject a fake one explicitly.
"""
import os

os.environ.setdefault('KEL_TURN_MODEL', 'none')
# D-62: General's default folder lives in the real Documents folder; tests never create it there.
# Tests of the default folder set KEL_GENERAL_ROOT to a temporary path themselves.
os.environ.setdefault('KEL_GENERAL_ROOT', 'none')
