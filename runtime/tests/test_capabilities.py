"""Conversation-scoped capability controls (docs/session-tools/).

Precedence under test: hard guardrails and real availability always win; a conversation override may
disable what runs there, may enable an available capability, is spent once when granted for one
action, and never leaks into another conversation or mutates the global default.
"""
import sys
import tempfile
import unittest
from pathlib import Path

from kel.authorize import authorize
from kel.capabilities import (CAPABILITIES, apply_directive, availability, capability_for_tool,
                              directive, grant_once, reset, resolve, set_global, set_override,
                              snapshot)
from kel.core import Store


class CapabilityBase(unittest.TestCase):
    def setUp(self):
        sys.stdout.reconfigure(errors='replace') if hasattr(sys.stdout, 'reconfigure') else None
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'data'
        self.store = Store(self.path)

    def tearDown(self):
        self.tmp.cleanup()


class SnapshotTests(CapabilityBase):
    def test_plain_names_and_honest_states(self):
        rows = snapshot(self.store, 'chat-a')
        self.assertEqual([row['id'] for row in rows], [item['id'] for item in CAPABILITIES])
        for row in rows:
            self.assertTrue(row['label'] and row['description'])
            self.assertIn(row['availability'], ('available', 'needs_setup', 'unavailable'))
            self.assertIn(row['override'], ('default', 'on', 'off'))
            # No raw tool ids or runtime words reach the surface.
            self.assertNotIn('mcp', row['label'].lower())

    def test_labels_are_user_words(self):
        labels = {row['id']: row['label'] for row in snapshot(self.store, 'chat-a')}
        self.assertEqual(labels['web'], 'Web')
        self.assertEqual(labels['github'], 'GitHub')
        self.assertEqual(labels['terminal'], 'Terminal')


class ScopeTests(CapabilityBase):
    def test_override_disables_only_that_conversation(self):
        set_override(self.store, 'chat-a', 'web', 'off')
        self.assertFalse(resolve(self.store, 'web', conversation='chat-a')['allowed'])
        self.assertTrue(resolve(self.store, 'web', conversation='chat-b')['allowed'])
        self.assertTrue(resolve(self.store, 'web', conversation='chat-c')['allowed'])

    def test_override_survives_reopen(self):
        set_override(self.store, 'chat-a', 'terminal', 'off')
        reopened = Store(self.path)
        self.assertFalse(resolve(reopened, 'terminal', conversation='chat-a')['allowed'])
        self.assertEqual(len(reopened.db_path.name) > 0, True)

    def test_reset_returns_to_default(self):
        set_override(self.store, 'chat-a', 'web', 'off')
        self.assertFalse(resolve(self.store, 'web', conversation='chat-a')['allowed'])
        reset(self.store, 'chat-a')
        self.assertTrue(resolve(self.store, 'web', conversation='chat-a')['allowed'])
        self.assertEqual(snapshot(self.store, 'chat-a')[0]['override'], 'default')


class GlobalTests(CapabilityBase):
    def test_conversation_override_never_mutates_the_global_default(self):
        set_global(self.store, 'web', 'off')
        self.assertFalse(resolve(self.store, 'web', conversation='chat-b')['allowed'])
        set_override(self.store, 'chat-a', 'web', 'on')
        self.assertTrue(resolve(self.store, 'web', conversation='chat-a')['allowed'])
        # chat-b still follows the global default, and the default itself is unchanged.
        self.assertFalse(resolve(self.store, 'web', conversation='chat-b')['allowed'])
        rows = {row['id']: row for row in snapshot(self.store, 'chat-b')}
        self.assertEqual(rows['web']['global'], 'off')
        self.assertEqual(rows['web']['override'], 'default')


class AvailabilityTests(CapabilityBase):
    def test_needs_setup_capability_cannot_be_enabled(self):
        state, why = availability(self.store, 'drive')
        self.assertIn(state, ('needs_setup', 'unavailable'))
        set_override(self.store, 'chat-a', 'drive', 'on')
        rows = {row['id']: row for row in snapshot(self.store, 'chat-a')}
        self.assertEqual(rows['drive']['effective'], 'off')
        decision = resolve(self.store, 'drive', conversation='chat-a')
        self.assertFalse(decision['allowed'])
        self.assertIn(decision['rule'], ('capability-needs-setup', 'capability-unavailable'))
        self.assertTrue(decision['reason'])

    def test_unknown_capability_is_refused_plainly(self):
        from kel.core import PolicyError
        with self.assertRaises(PolicyError):
            set_override(self.store, 'chat-a', 'quantum-radio', 'on')


class OnceTests(CapabilityBase):
    def test_one_action_grant_is_spent_once_and_expires(self):
        set_override(self.store, 'chat-a', 'web', 'off')
        grant_once(self.store, 'chat-a', 'web')
        # A pre-flight check sees the grant without spending it.
        self.assertTrue(resolve(self.store, 'web', conversation='chat-a', consume=False)['allowed'])
        # The real effect spends it.
        self.assertEqual(resolve(self.store, 'web', conversation='chat-a', consume=True)['rule'],
                         'capability-once')
        self.assertFalse(resolve(self.store, 'web', conversation='chat-a', consume=True)['allowed'])
        # A grant belongs to its conversation only: chat-b follows its own default and stays on.
        grant_once(self.store, 'chat-a', 'web')
        self.assertEqual(resolve(self.store, 'web', conversation='chat-a', consume=True)['rule'],
                         'capability-once')
        self.assertTrue(resolve(self.store, 'web', conversation='chat-b')['allowed'])
        # ... and a second grant brings the capability back for exactly one more action.
        self.assertEqual(resolve(self.store, 'web', conversation='chat-a', consume=True)['rule'],
                         'capability-conversation-off')


class DirectiveTests(CapabilityBase):
    def test_natural_language_converges_on_the_same_state(self):
        reply = apply_directive(self.store, 'chat-a', "Don't browse the web in this chat.")
        self.assertTrue(reply and 'Web' in reply)
        self.assertFalse(resolve(self.store, 'web', conversation='chat-a')['allowed'])
        reply = apply_directive(self.store, 'chat-a', 'Use GitHub for this conversation.')
        self.assertTrue(reply and 'GitHub' in reply)
        self.assertEqual(snapshot(self.store, 'chat-a')[0]['override'], 'off')
        reply = apply_directive(self.store, 'chat-a', 'Use the default for the web here.')
        self.assertTrue(reply)
        self.assertTrue(resolve(self.store, 'web', conversation='chat-a')['allowed'])

    def test_ordinary_text_is_not_a_directive(self):
        self.assertIsNone(directive('Write a short note about the weather tomorrow.'))
        self.assertIsNone(apply_directive(self.store, 'chat-a', 'Fix the failing test in parser.py'))


class AuthorizationTests(CapabilityBase):
    def test_authorize_honours_a_disabled_capability(self):
        set_override(self.store, 'chat-a', 'web', 'off')
        decision = authorize(self.store, {'actor': 'user', 'conversation': 'chat-a',
                                          'capability': 'web', 'action_kind': 'browser',
                                          'target': 'https://example.com'})
        self.assertEqual(decision['outcome'], 'DENY')
        self.assertEqual(decision['rule'], 'capability-conversation-off')

    def test_guardrails_still_win_over_an_enabled_capability(self):
        set_override(self.store, 'chat-a', 'terminal', 'on')
        decision = authorize(self.store, {'actor': 'user', 'conversation': 'chat-a',
                                          'capability': 'terminal', 'action_kind': 'destructive',
                                          'target': 'C:/Windows/System32'})
        self.assertEqual(decision['outcome'], 'DENY')
        # A locked guardrail rule, never the capability layer.
        self.assertNotIn(decision['rule'], ('capability-conversation-off', 'capability-once'))

    def test_capability_layer_does_not_replace_the_lease_gate(self):
        decision = authorize(self.store, {'actor': 'user', 'conversation': 'chat-a',
                                          'capability': 'files', 'action_kind': 'write',
                                          'target': str(self.path), 'consume': False})
        self.assertTrue(decision['outcome'] != 'ALLOW')
        self.assertIn(decision['outcome'], ('DENY', 'REQUIRES_USER_APPROVAL',
                                            'REQUIRES_BOUNDARY_EXPANSION', 'EXPIRED_LEASE'))

    def test_allow_once_is_spent_by_the_authorization_path(self):
        # "Allow once (next request only)" must be one action, not a wall-clock window: the grant is
        # spent by the effect-time authorization itself, and the gates below still govern that action.
        set_override(self.store, 'chat-a', 'web', 'off')
        grant_once(self.store, 'chat-a', 'web')
        intent = {'actor': 'user', 'conversation': 'chat-a', 'capability': 'web',
                  'action_kind': 'browser', 'target': 'https://example.com'}
        # A pre-flight check (consume=False) sees the grant and leaves it live.
        preflight = authorize(self.store, dict(intent, consume=False))
        self.assertNotEqual(preflight['rule'], 'capability-conversation-off')
        # The effect spends it: the capability layer passes, and the lease gate below is unchanged.
        first = authorize(self.store, intent)
        self.assertEqual(first['rule'], 'lease-required')
        # The next request is refused again - no standing consent.
        second = authorize(self.store, intent)
        self.assertEqual(second['outcome'], 'DENY')
        self.assertEqual(second['rule'], 'capability-conversation-off')

    def test_tool_mapping_is_plain(self):
        self.assertEqual(capability_for_tool('git'), 'github')
        self.assertEqual(capability_for_tool('run_tests'), 'terminal')
        self.assertEqual(capability_for_tool('write'), 'files')
        self.assertIsNone(capability_for_tool('something-else'))


if __name__ == '__main__':
    unittest.main()
