"""Conversation-scoped capability controls (docs/session-tools/).

Precedence under test: hard guardrails and real availability always win; a conversation override may
disable what runs there, may enable an available capability, is spent once when granted for one
action, and never leaks into another conversation or mutates the global default.
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

from kel.acp_host import _without_clauses
from kel.authorize import authorize
from kel.capabilities import (CAPABILITIES, apply_directive, availability, capability_for_tool,
                              directive, directive_clauses, grant_once, reset, resolve, set_global,
                              set_override, snapshot)
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
        # Terminal needs a coding assistant on this machine; without one the control stays honest.
        state, why = availability(self.store, 'terminal')
        self.assertIn(state, ('needs_setup', 'available'))
        if state == 'needs_setup':
            set_override(self.store, 'chat-a', 'terminal', 'on')
            rows = {row['id']: row for row in snapshot(self.store, 'chat-a')}
            self.assertEqual(rows['terminal']['effective'], 'off')
            decision = resolve(self.store, 'terminal', conversation='chat-a')
            self.assertFalse(decision['allowed'])
            self.assertIn(decision['rule'], ('capability-needs-setup', 'capability-unavailable'))
            self.assertTrue(decision['reason'])

    def test_removed_capabilities_are_not_offered_or_settable(self):
        # CAP-01 / V1.6: Google Drive and Connected apps have no production effect path in this
        # release, so they are not offered as switches that could not be kept; a stale caller is
        # refused plainly and their chat aliases are ordinary text again.
        ids = [row['id'] for row in snapshot(self.store, 'chat-a')]
        self.assertEqual(ids, ['web', 'files', 'terminal', 'github'])
        from kel.core import PolicyError
        for removed in ('drive', 'apps'):
            with self.assertRaises(PolicyError):
                set_override(self.store, 'chat-a', removed, 'on')
        self.assertIsNone(directive('drive: off'))
        self.assertIsNone(directive('connected apps: off'))

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
    def test_explicit_commands_converge_on_the_same_state(self):
        self.assertEqual(directive('web: use default'), ('web', 'default'))
        self.assertEqual(directive('terminal: off'), ('terminal', 'off'))
        reply = apply_directive(self.store, 'chat-a', "Don't browse the web in this chat.")
        self.assertTrue(reply and 'Web' in reply)
        self.assertFalse(resolve(self.store, 'web', conversation='chat-a')['allowed'])
        reply = apply_directive(self.store, 'chat-a', 'Use GitHub for this conversation.')
        self.assertTrue(reply and 'GitHub' in reply)
        reply = apply_directive(self.store, 'chat-a', 'Use the default for the web here.')
        self.assertTrue(reply)
        self.assertTrue(resolve(self.store, 'web', conversation='chat-a')['allowed'])

    def test_use_default_syntax_works(self):
        set_override(self.store, 'chat-a', 'web', 'off')
        reply = apply_directive(self.store, 'chat-a', 'web: use default')
        self.assertTrue(reply)
        self.assertEqual(snapshot(self.store, 'chat-a')[0]['override'], 'default')

    def test_ordinary_discussion_never_mutates_state(self):
        # The exact sentences the audit review flagged: none of them is a capability command.
        for text in ('I want to use the browser here to check something',
                     "Please don't use the terminal here, just tell me the answer",
                     'Can you use the web here?',
                     'Remember that we use the terminal here in the build'):
            self.assertIsNone(directive(text))
            self.assertIsNone(apply_directive(self.store, 'chat-a', text))
            self.assertEqual(directive_clauses(text), [])
        for row in snapshot(self.store, 'chat-a'):
            self.assertEqual(row['override'], 'default')

    def test_explicit_clause_inside_a_request_is_found(self):
        text = 'Please refactor parser.py. [terminal: off]'
        clauses = directive_clauses(text)
        self.assertEqual([(c['capability'], c['state']) for c in clauses], [('terminal', 'off')])
        self.assertEqual(clauses[0]['inner'], 'terminal: off')
        self.assertEqual(clauses[0]['text'], '[terminal: off]')
        leading = '[web: use default] Please research this topic.'
        self.assertEqual([(c['capability'], c['state']) for c in directive_clauses(leading)],
                         [('web', 'default')])
        both = '[web: off] [terminal: default] summarize X'
        self.assertEqual([(c['capability'], c['state']) for c in directive_clauses(both)],
                         [('web', 'off'), ('terminal', 'default')])
        mixed = '[Web: OFF] Mixed case clause'
        self.assertEqual([(c['capability'], c['state']) for c in directive_clauses(mixed)],
                         [('web', 'off')])

    def test_standalone_command_corpus_is_healthy(self):
        corpus = {
            'web: off': ('web', 'off'), 'web=off': ('web', 'off'), 'Web: OFF': ('web', 'off'),
            'web: reset': ('web', 'default'), 'web: use default': ('web', 'default'),
            'use default for the web here': ('web', 'default'),
            'set web back to default': ('web', 'default'),
            'reset terminal to default': ('terminal', 'default'),
            "don't use the terminal here": ('terminal', 'off'),
            'no terminal commands here': ('terminal', 'off'),
            'stop using the browser in this chat': ('web', 'off'),
        }
        for text, want in corpus.items():
            self.assertEqual(directive(text), want, text)
            self.assertTrue(apply_directive(self.store, 'chat-corpus', text), text)

    # The audit's mandatory false-positive corpus: ordinary prose containing control-shaped text.
    # Against 4f6535a's substring parser every one of these mutated state and stripped text from the
    # message; the bracket-only grammar must leave all of them untouched.
    ORDINARY_PROSE = (
        'the shell: off limits, so please use python instead',
        'the terminal: disabled by the admin policy here',
        'Browser: off-topic question, but what does this error mean?',
        'he said "web: off" in the meeting yesterday',
        "Someone wrote 'terminal: off' in the docs.",
        'The string web: off appears in this error.',
        'Why does terminal: disabled appear here?',
        'Explain what "web: use default" means.',
        'Please search for the phrase web: off.',
        'In this config, terminal: off means something else.',
        'THE TERMINAL: OFF LIMITS, try again',
        'web:  off is a string in the docs',
        'Hmm, terminal: disabled? Interesting.',
        'Note: web: off: that means something here.',
        'See https://example.com/web:off for details.',
        'See https://example.com/page?x=[web: off] more text',
        'malformed [web off] and [terminal: sideways] and [github: on',
        'Use `terminal: off` in the script.',
        'Run ```\nterminal: off\n``` in the shell.',
    )

    @staticmethod
    def _legacy_substring_rule(text):
        # The 4f6535a matcher, kept ONLY so the regression proves it discriminates. It matched every
        # sentence in ORDINARY_PROSE; the bracket grammar matches none of them.
        return bool(re.search(r'(?i)(?:the\s+)?(?:web|terminal|github|files|browser|shell)\s*[:=]\s*'
                              r'(?:use default|default|on|off|enabled|disabled|enable|disable)', text))

    def test_ordinary_prose_never_mutates_or_alters_the_message(self):
        for text in self.ORDINARY_PROSE:
            self.assertIsNone(directive(text), text)
            self.assertEqual(directive_clauses(text), [], text)
            self.assertIsNone(apply_directive(self.store, 'chat-a', text), text)
            self.assertEqual(_without_clauses(text, []), text, text)    # byte-identical
        for row in snapshot(self.store, 'chat-a'):
            self.assertEqual(row['override'], 'default', row['id'])

    def test_negative_control_the_old_substring_parser_would_have_matched(self):
        matched = [text for text in self.ORDINARY_PROSE if self._legacy_substring_rule(text)]
        self.assertEqual(len(matched), len(self.ORDINARY_PROSE))
        for text in matched:
            self.assertEqual(directive_clauses(text), [])
            self.assertIsNone(apply_directive(self.store, 'chat-a', text))

    def test_clause_removal_preserves_surrounding_text(self):
        cases = [
            ('Please refactor parser.py. [terminal: off]', 'Please refactor parser.py.'),
            ('[web: use default] Please research this topic.', 'Please research this topic.'),
            ('Do X \u2014 [web: off] \u2014 then Y', 'Do X then Y'),
            ('he said "web: off" in the meeting yesterday', 'he said "web: off" in the meeting yesterday'),
        ]
        for text, want in cases:
            self.assertEqual(_without_clauses(text, directive_clauses(text)), want, text)

    def test_ordinary_text_is_not_a_command(self):
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
        self.assertEqual(capability_for_tool('research'), 'web')
        self.assertIsNone(capability_for_tool('something-else'))


class ResearchEffectTests(CapabilityBase):
    """CAP-01 / CAP-03: the REAL production web effect path honours the conversation control.

    These tests drive the production effect point itself (kel.research.ResearchAdapter.execute with
    a real run row created by the real store), never a hand-built capability intent: authorization
    is proven where the engine dispatches research work, before any external request is sent.
    """

    @staticmethod
    def _payload():
        return {'stop_reason': 'end_turn', 'content': [
            {'type': 'server_tool_use', 'name': 'web_search'},
            {'type': 'web_search_tool_result', 'content': [
                {'type': 'web_search_result', 'url': 'https://docs.python.org/3/library/pathlib.html'}]},
            {'type': 'text',
             'text': 'Path.resolve resolves symbolic links and removes parent references. '
                     'Path.absolute makes a path absolute without resolving symbolic links.',
             'citations': [{'type': 'web_search_result_location',
                            'url': 'https://docs.python.org/3/library/pathlib.html',
                            'title': 'Python pathlib'}]}]}

    def _adapter(self, calls):
        from kel.research import ResearchAdapter

        def transport(*args, **kwargs):
            calls.append(1)
            return self._payload()
        return ResearchAdapter(self.store, transport=transport, model='research-fixture')

    def _run(self, conversation='chat-a'):
        from kel.research import compile_research
        job = self.store.create(compile_research('Search the web for the latest Kel release news.'),
                                budget=8, conversation=conversation)
        return job, self.store.claim(job, 'research', provider='research')

    def _settle(self, run, result):
        self.store.enqueue_result('result', run['id'], run['epoch'], result)
        self.store.consume()

    def test_disabled_web_blocks_the_real_effect_before_any_external_request(self):
        calls = []
        adapter = self._adapter(calls)
        set_override(self.store, 'chat-a', 'web', 'off')
        job, run = self._run()
        result = adapter.execute('Search the latest news.', run_id=run['id'])
        self.assertEqual(result['outcome'], 'BLOCKED')
        self.assertEqual(calls, [])  # the external search was never sent
        self.assertEqual(result['authorization'], 'capability-conversation-off')
        self.assertIn('Web', result['error'])
        self._settle(run, result)
        import contextlib
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute("SELECT 1 FROM sqlite_master WHERE name='research_evidence'").fetchone()
            evidence = db.execute('SELECT 1 FROM research_evidence').fetchall() if row else []
        self.assertEqual(evidence, [])

    def test_enabled_web_lets_the_same_production_path_proceed(self):
        calls = []
        adapter = self._adapter(calls)
        set_override(self.store, 'chat-a', 'web', 'off')
        reply = apply_directive(self.store, 'chat-a', 'web: use default')  # back to Default/Enabled
        self.assertTrue(reply)
        job, run = self._run()
        result = adapter.execute('Search the latest news.', run_id=run['id'])
        self.assertEqual(result['outcome'], 'SUCCESS')
        self.assertEqual(len(calls), 1)
        self.assertGreaterEqual(result['sources'], 1)
        self._settle(run, result)

    def test_one_shot_grant_is_spent_by_the_real_effect(self):
        calls = []
        adapter = self._adapter(calls)
        set_override(self.store, 'chat-a', 'web', 'off')
        grant_once(self.store, 'chat-a', 'web')
        job, run = self._run()
        first = adapter.execute('Search the latest news.', run_id=run['id'])
        self.assertEqual(first['outcome'], 'SUCCESS')
        self.assertEqual(len(calls), 1)
        self._settle(run, first)
        # The grant is gone: the next real request is refused before any external call.
        job2, run2 = self._run()
        second = adapter.execute('Search the latest news again.', run_id=run2['id'])
        self.assertEqual(second['outcome'], 'BLOCKED')
        self.assertEqual(len(calls), 1)
        self._settle(run2, second)

    def test_conversation_isolation_via_the_real_effect(self):
        calls = []
        adapter = self._adapter(calls)
        set_override(self.store, 'chat-a', 'web', 'off')
        job, run = self._run(conversation='chat-b')  # a different chat keeps its own state
        result = adapter.execute('Search the latest news.', run_id=run['id'])
        self.assertEqual(result['outcome'], 'SUCCESS')
        self.assertEqual(len(calls), 1)
        self._settle(run, result)

    def test_engine_dispatched_research_never_reaches_the_transport_when_web_is_off(self):
        import time as _time
        from kel.engine import Engine
        from kel.research import compile_research
        calls = []
        adapter = self._adapter(calls)
        set_override(self.store, 'chat-a', 'web', 'off')
        engine = Engine(self.store, {'research': adapter})
        try:
            job = engine.submit(compile_research("Search the web for today's news."),
                                conversation='chat-a')
            for _ in range(400):
                engine.tick()
                if not engine.active:
                    break
                _time.sleep(.01)
        finally:
            engine.close()
        self.assertEqual(calls, [])  # no external request ever left the machine
        current = self.store.get(job)
        self.assertNotEqual(current['milestones']['research']['state'], 'ACCEPTED')


if __name__ == '__main__':
    unittest.main()
