"""V1.2 D: trust/verification summary for settled jobs.

The summary is built only from persisted job state, keeps the B2 failure
explanation intact, and reports the verdict, evidence, identities, and
limitations without worker text or routing internals.
"""
import tempfile
import unittest

from kel.core import Store, verification_summary
from kel.engine import compile_document


def settled(verdict, milestones):
    return {'state': 'CLOSED', 'verdict': verdict, 'milestones': milestones}


class TrustSummaryTests(unittest.TestCase):
    def test_verified_coding_summary(self):
        job = settled('VERIFIED', {'code': {
            'provider': 'codex-code', 'model': None, 'error': None,
            'checks': [
                {'kind': 'artifact_digest', 'verdict': 'VERIFIED'},
                {'kind': 'repository_evidence', 'verdict': 'VERIFIED'},
                {'kind': 'min_chars', 'verdict': 'VERIFIED'},
                {'kind': 'manual_review', 'verdict': 'VERIFIED', 'reviewer_provider': 'claude',
                 'reviewer_model': None, 'findings': ['Meets request.']},
            ]}})
        summary = verification_summary(job)
        self.assertEqual(summary.splitlines()[0], 'Verified')
        self.assertIn('• Tests: passed', summary)
        self.assertIn('• Executed by: Codex', summary)
        self.assertIn('• Reviewed by: Claude Code', summary)

    def test_uncertain_limitation_is_reported(self):
        job = settled('UNCERTAIN', {'document': {
            'provider': 'claude', 'model': None, 'error': None,
            'checks': [
                {'kind': 'artifact_digest', 'verdict': 'VERIFIED'},
                {'kind': 'min_chars', 'verdict': 'VERIFIED'},
                {'kind': 'manual_review', 'verdict': 'UNCERTAIN',
                 'reason': 'microphone hardware unavailable for physical round-trip'},
            ]}})
        summary = verification_summary(job)
        self.assertEqual(summary.splitlines()[0], 'Uncertain')
        self.assertIn('• Limitation: microphone hardware unavailable for physical round-trip', summary)
        self.assertIn('• Executed by: Claude Code', summary)

    def test_failed_checks_are_named(self):
        job = settled('FAILED', {'document': {
            'provider': 'codex', 'model': None, 'error': None,
            'checks': [
                {'kind': 'contains', 'verdict': 'FAILED', 'expected': 'ACCEPT'},
                {'kind': 'manual_review', 'verdict': 'VERIFIED', 'reviewer_provider': 'claude',
                 'reviewer_model': None, 'findings': ['ok']},
            ]}})
        summary = verification_summary(job)
        self.assertEqual(summary.splitlines()[0], 'Failed')
        self.assertIn('• Failed check: contains (expected ACCEPT)', summary)

    def test_internal_reviewer_uses_model_label(self):
        job = settled('UNCERTAIN', {'document': {
            'provider': 'claude', 'model': None, 'error': None,
            'checks': [
                {'kind': 'manual_review', 'verdict': 'VERIFIED', 'reviewer_provider': 'internal',
                 'reviewer_model': 'claude-sonnet-4-6', 'findings': ['ok']},
            ]}})
        self.assertIn('• Reviewed by: Claude Sonnet', verification_summary(job))

    def test_unsettled_jobs_have_no_summary(self):
        self.assertIsNone(verification_summary({'state': 'RUNNING', 'verdict': 'UNCERTAIN', 'milestones': {}}))
        self.assertIsNone(verification_summary({'state': 'CLOSED'}))
        self.assertIsNone(verification_summary({'state': 'CLOSED', 'verdict': 'VERIFIED',
                                                'milestones': {'a': {'checks': []}}}))

    def test_publish_appends_summary_for_verified_jobs(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = Store(temp.name)
        job = store.create(compile_document('Write a plain guide.'))
        run = store.claim(job, 'document', provider='codex', model=None)
        store.enqueue_result('receipt', run['id'], run['epoch'],
                             {'outcome': 'SUCCESS', 'text': 'A completed artifact ready for independent review.'})
        store.consume()
        store.verify(job, 'document')
        store.record_review(job, 'document', store.get(job)['milestones']['document']['artifact']['sha256'],
                            'reviewer-1', 'VERIFIED', ['Meets request.'], store.get(job)['contract_version'],
                            reviewer_provider='claude', reviewer_model=None)
        store.assess(job)
        text, published = store.publish(job)
        self.assertTrue(published)
        self.assertIn('Verified', text)
        self.assertIn('• Executed by: Codex', text)
        self.assertIn('• Reviewed by: Claude Code', text)

    def test_publish_keeps_b2_explanation_for_uncertain_jobs(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = Store(temp.name)
        job = store.create(compile_document('Write a plain guide.'))
        run = store.claim(job, 'document', provider='codex', model=None)
        store.enqueue_result('receipt', run['id'], run['epoch'],
                             {'outcome': 'SUCCESS', 'text': 'A completed artifact ready for independent review.'})
        store.consume()
        store.verify(job, 'document')
        store.assess(job)
        text, published = store.publish(job)
        self.assertTrue(published)
        self.assertIn('Kel could not fully verify the result', text)
        self.assertIn('What you can do next: ', text)
        self.assertIn('Uncertain', text)
        self.assertIn('• Limitation: Independent rubric review not recorded', text)


if __name__ == '__main__':
    unittest.main()
