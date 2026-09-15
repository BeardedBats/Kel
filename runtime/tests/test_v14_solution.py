"""V1.4 Gate 3: solution quality — briefs, options, search, opportunities, reviews (SLN-*)."""
import contextlib
import json
import tempfile
import unittest

from kel.core import PolicyError, Store
from kel.solution import (OPTION_KINDS, SolutionBriefs, ensure_schema)


def brief_with_options(briefs, options=2):
    brief_id = briefs.open_brief('default', 'Reduce onboarding friction without new services.')
    briefs.update(brief_id, request='User asked for a faster first run.',
                  assumptions=['provider CLIs are optional'],
                  verified_constraints=['engine suite must stay green'])
    briefs.add_option(brief_id, 'reuse', 'Reuse recipient flow', 'Extend the existing flow.', 'reuse',
                      tradeoffs=['less new code'], cost='low', complexity=2, reversible=True)
    if options == 2:
        briefs.add_option(brief_id, 'build', 'Build dedicated flow', 'New surface.', 'implement',
                          tradeoffs=['more work'], cost='high', complexity=4, reversible=False)
    briefs.search(brief_id, [{'what': 'existing onboarding', 'where': 'desktop renderer',
                              'ref': 'desktop/packages/desktop/src/renderer/pages/guid',
                              'verdict': 'reuse'}])
    return brief_id


class SolutionCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.briefs = SolutionBriefs(self.store)

    def test_brief_creation_and_defaults(self):
        brief_id = self.briefs.open_brief('default', 'Goal text')
        brief = self.briefs.get(brief_id)
        self.assertEqual(brief['state'], 'OPEN')
        self.assertIsNone(brief['chosen_option'])
        for key in ('request', 'assumptions', 'search', 'criteria', 'recommendation'):
            self.assertIn(key, brief['data'])
        self.assertEqual(self.briefs.list('default')[0]['brief_id'], brief_id)

    def test_unknown_fields_and_types_refused(self):
        brief_id = self.briefs.open_brief('default', 'Goal')
        with self.assertRaises(PolicyError):
            self.briefs.update(brief_id, mystery=1)
        with self.assertRaises(PolicyError):
            self.briefs.update(brief_id, assumptions='not-a-list')
        updated = self.briefs.update(brief_id, staffing=[{'milestone': 'm1', 'role': 'qa'}])
        self.assertEqual(updated['data']['staffing'][0]['role'], 'qa')

    def test_option_validation(self):
        brief_id = self.briefs.open_brief('default', 'Goal')
        self.briefs.add_option(brief_id, 'a', 'A', 'summary', 'implement')
        with self.assertRaises(PolicyError):
            self.briefs.add_option(brief_id, 'a', 'A again', 'dup', 'implement')
        with self.assertRaises(PolicyError):
            self.briefs.add_option(brief_id, 'b', 'B', 'summary', 'invent')
        with self.assertRaises(PolicyError):
            self.briefs.add_option(brief_id, 'c', 'C', 'summary', 'implement', complexity=9)

    def test_compare_requires_option_and_score_range(self):
        brief_id = brief_with_options(self.briefs)
        self.briefs.compare(brief_id, 'effort', 'reuse', 2, 'low effort')
        with self.assertRaises(PolicyError):
            self.briefs.compare(brief_id, 'effort', 'missing', 2)
        with self.assertRaises(PolicyError):
            self.briefs.compare(brief_id, 'effort', 'reuse', 7)

    def test_search_record_requires_findings(self):
        brief_id = self.briefs.open_brief('default', 'Goal')
        with self.assertRaises(PolicyError):
            self.briefs.search(brief_id, [])
        with self.assertRaises(PolicyError):
            self.briefs.search(brief_id, [{'what': 'x', 'where': 'y', 'verdict': 'maybe'}])
        brief = self.briefs.search(brief_id, [{'what': 'x', 'where': 'y', 'verdict': 'build'}])
        self.assertEqual(brief['data']['search'][0]['verdict'], 'build')

    def test_capability_opportunity_classification(self):
        brief_id = self.briefs.open_brief('default', 'Goal')
        result = self.briefs.opportunity(brief_id, 'Figma source', 'Better visual fidelity',
                                         'higher quality', 'source-derived audit', 'PAUSE',
                                         access_needed='')
        self.assertEqual(result['classification'], 'PAUSE')
        with self.assertRaises(PolicyError):
            self.briefs.opportunity(brief_id, 'staging', 'why', 'benefit', 'fallback', 'ASK_ONCE')
        ok = self.briefs.opportunity(brief_id, 'staging', 'why', 'benefit', 'fallback', 'ASK_ONCE',
                                     access_needed='read-only staging URL')
        self.assertEqual(ok['classification'], 'ASK_ONCE')
        with self.assertRaises(PolicyError):
            self.briefs.opportunity(brief_id, 'x', 'y', 'z', 'f', 'MAYBE')

    def test_user_idea_evaluation_is_classified_not_flattered(self):
        brief_id = self.briefs.open_brief('default', 'Goal')
        brief = self.briefs.idea(brief_id, 'Use a queue', 'BETTER_LATER', 'later, not now')
        self.assertEqual(brief['data']['user_ideas'][0]['verdict'], 'BETTER_LATER')
        with self.assertRaises(PolicyError):
            self.briefs.idea(brief_id, 'Do it anyway', 'USER_MANDATE')
        with self.assertRaises(PolicyError):
            self.briefs.idea(brief_id, 'Idea', 'GREAT')
        brief = self.briefs.idea(brief_id, 'Do it anyway', 'USER_MANDATE', 'explicit instruction')
        self.assertEqual(len(brief['data']['user_ideas']), 2)

    def test_recommendation_gate(self):
        brief_id = brief_with_options(self.briefs, options=1)
        with self.assertRaises(PolicyError):
            self.briefs.recommend(brief_id, 'reuse', 'r', 'e', 'rollback')
        brief_id = brief_with_options(self.briefs)
        with self.assertRaises(PolicyError):
            self.briefs.recommend(brief_id, 'reuse', 'r', 'e', 'rollback', workaround_type='magic')
        brief = self.briefs.recommend(brief_id, 'reuse', 'smallest coherent change',
                                      'if reuse blocks a2, build the flow',
                                      'revert the renderer commit')
        self.assertEqual(brief['state'], 'RECOMMENDED')
        self.assertEqual(brief['chosen_option'], 'reuse')

    def test_no_self_certification(self):
        brief_id = brief_with_options(self.briefs)
        self.briefs.recommend(brief_id, 'reuse', 'r', 'e', 'rollback')
        with self.assertRaises(PolicyError):
            self.briefs.review(brief_id, 'kel', 'OPTIMAL_ENOUGH', 'looks fine')
        with self.assertRaises(PolicyError):
            self.briefs.review(brief_id, 'reviewer-1', 'PERFECT', 'findings')
        review = self.briefs.review(brief_id, 'reviewer-1', 'OPTIMAL_ENOUGH', 'compared fairly')
        self.assertEqual(review['verdict'], 'OPTIMAL_ENOUGH')

    def test_approval_requires_independent_review_and_resolved_blocks(self):
        brief_id = brief_with_options(self.briefs)
        self.briefs.recommend(brief_id, 'reuse', 'r', 'e', 'revert the renderer commit')
        with self.assertRaises(PolicyError):
            self.briefs.approve(brief_id)
        block = self.briefs.review(brief_id, 'reviewer-1', 'BLOCK', 'ignores donor pattern')
        with self.assertRaises(PolicyError):
            self.briefs.approve(brief_id)
        self.briefs.resolve_block(brief_id, block['review_id'], 'donor pattern adopted')
        with self.assertRaises(PolicyError):
            self.briefs.approve(brief_id)
        self.briefs.review(brief_id, 'reviewer-2', 'OPTIMAL_ENOUGH', 'now optimal enough')
        approved = self.briefs.approve(brief_id, actor='user')
        self.assertEqual(approved['state'], 'APPROVED')
        self.assertEqual(approved['rollback'], 'revert the renderer commit')

    def test_schema_migration_idempotent(self):
        self.assertTrue(ensure_schema(self.store))
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT version, name FROM schema_migrations WHERE version=5').fetchone()
        self.assertEqual(row['name'], 'v14-solution')
        again = SolutionBriefs(self.store)
        self.briefs.open_brief('default', 'Goal after reopen')
        self.assertEqual(len(again.list('default')), 1)

    def test_service_envelope_end_to_end(self):
        brief_id = self.briefs.apply({'action': 'create', 'project_id': 'default',
                                      'goal': 'Ship image tooling'})['id']
        for option in ('patch', 'rewrite'):
            self.briefs.apply({'action': 'option', 'brief': brief_id, 'option_id': option,
                               'title': option, 'summary': 'summary', 'kind': 'implement'})
        self.briefs.apply({'action': 'search', 'brief': brief_id,
                           'findings': [{'what': 'x', 'where': 'y', 'verdict': 'none'}]})
        self.briefs.apply({'action': 'recommend', 'brief': brief_id, 'option_id': 'patch',
                           'rationale': 'least change', 'evidence_to_switch': 'if blocked',
                           'rollback': 'git revert'})
        self.briefs.apply({'action': 'review', 'brief': brief_id, 'reviewer_id': 'r1',
                           'verdict': 'OPTIMAL_ENOUGH', 'findings': 'ok'})
        result = self.briefs.apply({'action': 'approve', 'brief': brief_id})
        self.assertEqual(result['state'], 'APPROVED')
        self.assertEqual(result['chosen_option'], 'patch')


if __name__ == '__main__':
    unittest.main()
