"""Suite-wide guard: tests never reach a real turn model (D-53).

The conversational turn decision would otherwise call an installed CLI (codex/claude) or the
internal API. Tests that exercise the turn model inject a fake one explicitly.
"""
import os

os.environ.setdefault('KEL_TURN_MODEL', 'none')
# D-62: General's default folder lives in the real Documents folder; tests never create it there.
# Tests of the default folder set KEL_GENERAL_ROOT to a temporary path themselves.
os.environ.setdefault('KEL_GENERAL_ROOT', 'none')

# New projects (greenfield builds) are created under the projects root; the suite points it at a
# throwaway folder so no test ever creates a project in the real Documents folder.
if not os.environ.get('KEL_PROJECTS_ROOT'):
    import tempfile
    os.environ['KEL_PROJECTS_ROOT'] = os.path.join(tempfile.mkdtemp(prefix='kel-tests-'), 'Kel Projects')
    os.makedirs(os.environ['KEL_PROJECTS_ROOT'], exist_ok=True)

# D-74.1: research routes through the installed Claude Code / Codex web search. The suite never
# sends a real web search from a background job; tests of that route turn it on themselves.
os.environ.setdefault('KEL_CLI_WEB', '0')
