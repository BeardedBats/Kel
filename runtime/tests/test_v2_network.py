"""V2-14 — network permissions: modes, scopes, asks, and the one choke point.

Directive §19, kept practical. The `NETWORK_RULES` seam already existed (asked before anything leaves
the computer, again for a redirect's host, fail-closed when the rule source errors); this module is
its rule source. The pins: with no policy rows nothing changes (default full); NO INTERNET blocks
with a plain sentence and records it; APPROVED DOMAINS matches exactly or as a parent domain and
**asks** about a new host instead of sending it (a pending request names the one action that fixes
it); approving adds the host to that scope's list and the next attempt passes; denying keeps it
blocked; per-Project scopes beat the default and per-tool rules beat the project; the seam refuses
before any network I/O; bind/unbind never leaks a store into another one; and a one-argument hook
keeps working.
"""
import contextlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kel import network_policy  # noqa: E402
from kel.connections import network_rule, perform_request  # noqa: E402
from kel.core import PolicyError, Store  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.store = Store(Path(self.tmp.name) / 'data')

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass


class ModeTests(Base):
    def test_the_default_is_full_internet_and_nothing_changes(self):
        decision = network_policy.decide(self.store, 'api.github.com')
        self.assertTrue(decision['allowed'])
        self.assertEqual(decision['mode'], 'full')
        events = network_policy.history(self.store)['events']
        self.assertEqual(events[0]['decision'], 'allowed')

    def test_no_internet_blocks_with_one_plain_sentence(self):
        network_policy.set_mode(self.store, 'none')
        decision = network_policy.decide(self.store, 'api.github.com', tool='github.read')
        self.assertFalse(decision['allowed'])
        self.assertIn('no internet', decision['reason'])
        self.assertEqual(network_policy.history(self.store)['events'][0]['decision'], 'blocked')

    def test_approved_domains_allows_a_listed_parent_and_its_children(self):
        network_policy.set_mode(self.store, 'approved', domains=['github.com'])
        for host in ('api.github.com', 'github.com'):
            decision = network_policy.decide(self.store, host)
            self.assertTrue(decision['allowed'], host)
            self.assertEqual(decision['matched'], 'github.com')

    def test_a_new_host_is_asked_about_never_sent(self):
        network_policy.set_mode(self.store, 'approved', domains=['github.com'])
        decision = network_policy.decide(self.store, 'api.stripe.com', tool='stripe.read',
                                         project='proj-1')
        self.assertFalse(decision['allowed'])
        self.assertIn('not on the approved list', decision['reason'])
        pending = network_policy.requests(self.store)['requests']
        self.assertEqual([item['host'] for item in pending], ['api.stripe.com'])
        self.assertEqual(pending[0]['tool'], 'stripe.read')
        self.assertEqual(pending[0]['scope'], 'default')

    def test_approving_adds_the_host_and_the_next_attempt_passes(self):
        network_policy.set_mode(self.store, 'approved')
        decision = network_policy.decide(self.store, 'api.stripe.com')
        resolved = network_policy.resolve_request(self.store, decision['request'], True)
        self.assertEqual(resolved['state'], 'approved')
        again = network_policy.decide(self.store, 'api.stripe.com')
        self.assertTrue(again['allowed'])
        self.assertEqual(again['matched'], 'api.stripe.com')
        self.assertEqual(network_policy.requests(self.store)['requests'], [],
                         'the ask is answered, not left pending')

    def test_denying_keeps_it_blocked_and_records_the_answer(self):
        network_policy.set_mode(self.store, 'approved')
        decision = network_policy.decide(self.store, 'evil.example')
        network_policy.resolve_request(self.store, decision['request'], False)
        self.assertEqual(network_policy.requests(self.store, state='denied')['requests'][0]['host'],
                         'evil.example')
        again = network_policy.decide(self.store, 'evil.example')
        self.assertFalse(again['allowed'], 'a denied host is not sent')


class ScopeTests(Base):
    def test_a_project_scope_beats_the_default_and_others_fall_through(self):
        network_policy.set_mode(self.store, 'full')
        network_policy.set_mode(self.store, 'none', scope='project:p1')
        self.assertFalse(network_policy.decide(self.store, 'x.example', project='p1')['allowed'])
        self.assertTrue(network_policy.decide(self.store, 'x.example', project='p2')['allowed'],
                        'an unconfigured project follows the default')

    def test_a_tool_rule_beats_the_project_scope(self):
        network_policy.set_mode(self.store, 'none')
        network_policy.set_tool_rule(self.store, 'github.read', 'full')
        self.assertTrue(network_policy.decide(self.store, 'api.github.com', tool='github.read',
                                              project='p1')['allowed'])
        self.assertFalse(network_policy.decide(self.store, 'api.github.com', tool='github.list',
                                               project='p1')['allowed'])
        policy = network_policy.get_policy(self.store)
        self.assertEqual([item['tool'] for item in policy['tools']], ['github.read'])
        network_policy.clear_tool_rule(self.store, 'github.read')
        self.assertFalse(network_policy.decide(self.store, 'api.github.com', tool='github.read',
                                               project='p1')['allowed'])

    def test_approving_a_tool_scoped_ask_updates_that_tool_rule_only(self):
        network_policy.set_mode(self.store, 'full')
        network_policy.set_tool_rule(self.store, 'con.read', 'approved')
        decision = network_policy.decide(self.store, 'api.github.com', tool='con.read')
        self.assertEqual(decision['scope'], 'tool:con.read')
        network_policy.resolve_request(self.store, decision['request'], True)
        self.assertTrue(network_policy.decide(self.store, 'api.github.com',
                                              tool='con.read')['allowed'])
        policy = network_policy.get_policy(self.store)
        self.assertEqual(policy['tools'][0]['domains'], ['api.github.com'])
        self.assertEqual(policy['default']['domains'], [], 'the default list was not touched')

    def test_a_domain_entry_must_look_like_a_domain(self):
        with self.assertRaises(PolicyError):
            network_policy.set_mode(self.store, 'approved', domains=['bad name'])
        with self.assertRaises(PolicyError):
            network_policy.set_mode(self.store, 'sometimes')


class SeamTests(Base):
    def test_the_choke_point_refuses_before_any_network_io(self):
        network_policy.set_mode(self.store, 'none')
        token = network_policy.bind(self.store)
        try:
            with self.assertRaises(PolicyError) as raised:
                # An address that cannot answer: any real attempt would hang or fail, never fail fast.
                perform_request('http://203.0.113.1/never', {})
        finally:
            network_policy.unbind(token)
        self.assertIn('no internet', str(raised.exception))

    def test_bind_and_unbind_never_leak_a_store(self):
        self.assertEqual(network_rule('x.example'), (True, ''), 'unbound: the seam is open')
        token = network_policy.bind(self.store)
        network_policy.set_mode(self.store, 'none')
        allowed, reason = network_rule('x.example')
        self.assertFalse(allowed)
        self.assertIn('no internet', reason)
        network_policy.unbind(token)
        self.assertTrue(network_rule('x.example')[0], 'after unbind the seam is open again')

    def test_a_one_argument_hook_keeps_working(self):
        from kel import connections
        previous = connections.NETWORK_RULES
        try:
            connections.NETWORK_RULES = lambda host: (False, 'old style')
            self.assertEqual(network_rule('x.example'), (False, 'old style'))
        finally:
            connections.NETWORK_RULES = previous

    def test_a_failing_rule_source_fails_closed(self):
        from kel import connections
        previous = connections.NETWORK_RULES
        try:
            def broken(host, context=None):
                raise RuntimeError('boom')
            connections.NETWORK_RULES = broken
            allowed, reason = network_rule('x.example')
            self.assertFalse(allowed)
            self.assertIn('could not check', reason)
        finally:
            connections.NETWORK_RULES = previous


if __name__ == '__main__':
    unittest.main()
