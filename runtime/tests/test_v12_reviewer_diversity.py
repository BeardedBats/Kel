"""V1.2 C: reviewer diversity.

When a second eligible reviewer provider exists, the reviewer for one
artifact prefers a genuinely different model family/provider from the
executor. A single eligible reviewer keeps the current fallback behavior,
and provenance records the reviewer that actually ran.
"""
import json
import tempfile
import unittest

from kel.commander import Commander
from kel.core import Store
from kel.engine import compile_document


class FakeReviewer:
    def __init__(self, provider, model=None):
        self.provider = provider
        self.model = model

    def execute(self, prompt, run_id=None, **kwargs):
        return {'outcome': 'SUCCESS',
                'text': json.dumps({'verdict': 'VERIFIED', 'findings': ['Independently checked.']})}


def pending_review_job(store, provider, model=None):
    job = store.create(compile_document('Write a plain guide.'))
    run = store.claim(job, 'document', provider=provider, model=model)
    store.enqueue_result('receipt', run['id'], run['epoch'],
                         {'outcome': 'SUCCESS', 'text': 'A completed artifact ready for independent review.'})
    store.consume()
    store.verify(job, 'document')
    return job


class ReviewerSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)

    def test_two_providers_prefer_a_different_family(self):
        commander = Commander(FakeReviewer('internal', 'claude-sonnet-4-6'), [FakeReviewer('codex')])
        picked = commander._reviewer(self.store, 'claude-code', None)
        self.assertEqual(picked.provider, 'codex')

    def test_two_providers_prefer_a_different_provider(self):
        commander = Commander(FakeReviewer('internal', 'claude-sonnet-4-6'), [FakeReviewer('codex')])
        picked = commander._reviewer(self.store, 'codex-code', None)
        self.assertEqual(picked.provider, 'internal')

    def test_single_provider_keeps_current_fallback(self):
        commander = Commander(FakeReviewer('internal', 'claude-sonnet-4-6'))
        picked = commander._reviewer(self.store, 'claude-code', None)
        self.assertEqual(picked.provider, 'internal')

    def test_unhealthy_independent_provider_yields_to_healthy_one(self):
        self.store.provider_outcome('codex', {'outcome': 'FAILED', 'error': '401 authentication failed'})
        commander = Commander(FakeReviewer('internal', 'claude-sonnet-4-6'), [FakeReviewer('codex')])
        picked = commander._reviewer(self.store, 'claude-code', None)
        self.assertEqual(picked.provider, 'internal')

    def test_review_records_the_reviewer_that_ran(self):
        commander = Commander(FakeReviewer('internal', 'claude-sonnet-4-6'), [FakeReviewer('codex')])
        job = pending_review_job(self.store, 'claude-code')
        commander.review(self.store, job, 'document')
        check = next(c for c in self.store.get(job)['milestones']['document']['checks']
                     if c['kind'] == 'manual_review')
        self.assertEqual(check['reviewer_provider'], 'codex')

    def test_single_reviewer_provenance_records_actual(self):
        commander = Commander(FakeReviewer('internal', 'claude-sonnet-4-6'))
        job = pending_review_job(self.store, 'claude-code')
        commander.review(self.store, job, 'document')
        check = next(c for c in self.store.get(job)['milestones']['document']['checks']
                     if c['kind'] == 'manual_review')
        self.assertEqual(check['reviewer_provider'], 'internal')
        self.assertEqual(check['reviewer_model'], 'claude-sonnet-4-6')

    def test_descriptor_with_context_reports_the_actual_reviewer(self):
        commander = Commander(FakeReviewer('internal', 'claude-sonnet-4-6'), [FakeReviewer('codex')])
        job = pending_review_job(self.store, 'claude-code')
        self.assertEqual(commander.descriptor(self.store, job, 'document'),
                         {'provider': 'codex', 'model': None})
        self.assertEqual(commander.descriptor(),
                         {'provider': 'internal', 'model': 'claude-sonnet-4-6'})


if __name__ == '__main__':
    unittest.main()
