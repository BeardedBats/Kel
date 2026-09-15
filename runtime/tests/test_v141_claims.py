"""V1.4.1 claims discipline.

These tests pin the corrected release claims so they cannot silently drift back to the V1.4-era
statements that implied execution-path enforcement which did not exist. They check the shipped
documents and shipped UI copy, not the code paths (those have their own tests).
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _norm(body):
    """Collapse whitespace so claims are matched across line wrapping."""
    return re.sub(r'\s+', ' ', body)

BANNED = {
    'docs/v1.4/KEL_V1.4_SECURITY_MODEL.md': (
        'Everything below is enforced in code and covered by a test id',
        'no code path executes a gated action without an APPROVED row',
        'enforced by the locked guardrail module and verified by tests',
        'at run time the engine receives the value as an environment variable',
        'per-role tool policy checked at claim **and** at effect time',
    ),
    'docs/v1.4/KEL_V1.4_AUTONOMY_POLICY.md': (
        'tool layer refuses before execution',
    ),
    'docs/v1.4/KEL_V1.4_TEAM_MODEL.md': (
        'a hard engine check',
    ),
    'docs/v1.4/KEL_V1.4_ARCHITECTURE.md': (
        'lease engine + enforcement',
    ),
}

REQUIRED = {
    'docs/v1.4/KEL_V1.4_SECURITY_MODEL.md': (
        'not yet called on the execution path',
        'not yet enforced against native worker actions',
        'danger-full-access',
        'not a permission sandbox',
        'status V1.4.1): not implemented',
    ),
    'docs/v1.4/KEL_V1.4_AUTONOMY_POLICY.md': (
        'not yet wired',
        'pauses all active or queued jobs',
    ),
    'docs/v1.4/KEL_V1.4_ARCHITECTURE.md': (
        'policy checker',
    ),
    'docs/v1.4/KEL_V1.4_STATUS.md': (
        'Post-release note (added in V1.4.1)',
    ),
    'docs/v1.4.1/02_RUNTIME_TRUST_BOUNDARY.md': (
        'danger-full-access',
        'not a sandbox',
        'deferred to V1.5',
    ),
    'docs/v1.4.1/06_V1_5_DEFERRED_WORK.md': (
        'execution-path',
    ),
    'desktop/packages/desktop/src/renderer/pages/kel/autonomy/index.tsx': (
        'not yet implemented',
        'not yet called on the worker execution path',
    ),
    'desktop/packages/desktop/src/renderer/pages/kel/providers/index.tsx': (
        'not yet injected into provider runs',
    ),
}


class ClaimDisciplineTests(unittest.TestCase):
    def test_no_overclaim_phrases_remain(self):
        for rel, phrases in BANNED.items():
            body = _norm((ROOT / rel).read_text(encoding='utf-8'))
            for phrase in phrases:
                self.assertNotIn(phrase, body, f'{rel} still contains the overclaim: {phrase!r}')

    def test_corrected_claims_are_present(self):
        for rel, phrases in REQUIRED.items():
            path = ROOT / rel
            self.assertTrue(path.exists(), f'{rel} is missing')
            body = _norm(path.read_text(encoding='utf-8'))
            for phrase in phrases:
                self.assertIn(phrase, body, f'{rel} is missing the claim: {phrase!r}')
