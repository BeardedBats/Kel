"""B2: every blocking state answers what/why/tried/next.

Reproduces the five failure modes against the real Store/router code and asserts
the explanation layer surfaces the same four questions each time. The pre-B2
engine showed only generic fallbacks for these paths ('Work state:
WAITING_RESOURCE. Verification: UNCERTAIN.' and 'I could not verify the complete
result.'), so these tests fail on the V1 bytecode and pass with the layer.
"""
import tempfile
import time
import unittest

from kel.core import Store, PolicyError, explain_approval, explain_failure
from kel.router import Candidate, select

LABELS = ('What happened: ', 'Why: ', 'What Kel already tried: ', 'What you can do next: ')


def contract(review=False):
    checks = [{'kind': 'contains', 'value': 'ACCEPT'}, {'kind': 'min_chars', 'value': 6}]
    if review: checks.append({'kind': 'manual_review', 'rubric': 'Clear and accurate'})
    return {'request': 'Write ACCEPT',
            'milestones': [{'id': 'a', 'objective': 'Write ACCEPT', 'filename': 'a.md', 'checks': checks}]}


class FailureSurfacing(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def store(self):
        return Store(self.temp.name)

    def assert_explained(self, text):
        self.assertTrue(text, 'no explanation was produced')
        for label in LABELS:
            self.assertIn(label, text)

    def test_provider_failure_names_the_circuit_state(self):
        store = self.store()
        job = store.create(contract())
        with self.assertRaises(PolicyError) as caught:
            select([Candidate(name='claude', circuit_until=time.time() + 3600),
                    Candidate(name='codex', circuit_until=time.time() + 3600)])
        store.wait_for_route(job, str(caught.exception))
        current = store.get(job)
        text = explain_failure(current)
        self.assert_explained(text)
        self.assertIn('No model could start this work', text)
        self.assertIn('Codex is resting after recent failures', text)  # LIVE-5: plain words, no router jargon
        self.assertEqual(current['state'], 'WAITING_RESOURCE')
        self.assertEqual(current['verdict'], 'UNCERTAIN')

    def test_no_eligible_worker_names_install_and_auth_reasons(self):
        store = self.store()
        job = store.create(contract())
        with self.assertRaises(PolicyError) as caught:
            select([Candidate(name='claude', installed=False),
                    Candidate(name='codex', authenticated=False)])
        store.wait_for_route(job, str(caught.exception))
        current = store.get(job)
        text = explain_failure(current)
        self.assert_explained(text)
        self.assertIn("Claude Code isn't installed", text)
        self.assertIn("Codex isn't signed in", text)
        self.assertIn('No model here can run this work', text)  # nothing can ever run it: Nick decides
        self.assertEqual(current['state'], 'WAITING_RESOURCE')

    def test_approval_wait_explains_the_gate(self):
        store = self.store()
        job = store.create(contract())
        run = store.claim(job, 'a')
        store.request_approval(job, run['id'], {'operation': 'publish', 'target': 'fixture', 'sha': '123'})
        current = store.get(job)
        text = explain_approval('publish to fixture')
        self.assert_explained(text)
        self.assertIn('Kel needs your permission', text)
        self.assertIn('publish to fixture', text)
        self.assertIn('work card at the top of the chat', text)
        self.assertNotIn('Work context', text)
        self.assertEqual(current['state'], 'AWAITING_USER')
        # The ACP layer owns this state; explain_failure must not double-report it.
        self.assertIsNone(explain_failure(current))

    def test_environment_limited_verification_names_the_missing_reviewer(self):
        store = self.store()
        job = store.create(contract(review=True))
        run = store.claim(job, 'a')
        store.enqueue_result('ev', run['id'], run['epoch'],
                             {'outcome': 'SUCCESS', 'text': 'ACCEPT valid artifact content'})
        store.consume()
        store.verify(job, 'a')
        store.assess(job)
        text, _ = store.publish(job)
        self.assert_explained(text)
        self.assertIn('The checks are incomplete', text)
        self.assertIn('Independent rubric review not recorded', text)

    def test_unexpected_worker_exit_explains_preserved_work(self):
        store = self.store()
        job = store.create(contract())
        store.claim(job, 'a')
        store.recover_expired(now=time.time() + 100000)
        current = store.get(job)
        text = explain_failure(current)
        self.assert_explained(text)
        self.assertIn('The model working on this stopped before it finished', text)
        self.assertEqual(current['state'], 'WAITING_RESOURCE')

    def test_settled_and_verified_states_are_not_explained(self):
        store = self.store()
        job = store.create(contract())
        self.assertIsNone(explain_failure(store.get(job)), 'a ready job needs no explanation')


if __name__ == '__main__':
    unittest.main()
