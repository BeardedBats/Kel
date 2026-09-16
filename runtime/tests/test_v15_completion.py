"""V1.5 G5: explicit CompletionContract claims + bounded, inspectable routing outcomes.

Claims are a deterministic projection of the trusted acceptance checks (never invented work), so
trivial requests stay at one or two objective claims. Claims are attached to **finalized**
contracts only (store create/revise) — transient planner drafts never carry them, so a scope
rewrite can never leave stale claims behind. Routing outcomes record the task class and whether a
verified result required an escalation to a different provider — inputs for routing advice, never
a silent override of the hard filters in `kel.router.select`.
"""
import contextlib
import tempfile
import unittest
from pathlib import Path

from kel.coding import compile_coding, git
from kel.core import Store, completion_claims, validate_contract
from kel.engine import compile_document
from kel.research import compile_research

CLAIM_FIELDS = ('id', 'requirement', 'acceptance_criterion', 'verification_method',
                'objective_or_subjective', 'evidence_required', 'failure_condition', 'dependencies')


class ClaimsTests(unittest.TestCase):
    def test_every_compiled_family_carries_explicit_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project = base / 'proj'
            project.mkdir()
            git(project, 'init')
            (project / 'a.txt').write_text('x')
            git(project, 'add', '-A')
            git(project, '-c', 'user.name=Kel', '-c', 'user.email=kel@localhost',
                'commit', '-m', 'b')
            coding = compile_coding('Change a.txt.', project, ['python', '-m', 'unittest'])
            document = compile_document('Write a short plan for the weekend.')
            research = compile_research('Research the latest Python release.')
        for contract in (coding, document, research):
            claims = completion_claims(contract)
            self.assertTrue(claims, contract.get('compiler'))
            for claim in claims:
                for field in CLAIM_FIELDS:
                    self.assertIn(field, claim, (contract.get('compiler'), field))
            self.assertNotIn('claims', contract,
                             'transient drafts must not carry claims (scope rewrites stay clean)')
        doc_claims = completion_claims(document)
        subjective = [c for c in doc_claims if c['objective_or_subjective'] == 'subjective']
        objective = [c for c in doc_claims if c['objective_or_subjective'] == 'objective']
        self.assertTrue(subjective and objective,
                        'rubric review is subjective; builtin checks are objective')
        methods = ' '.join(c['verification_method'] for c in completion_claims(coding))
        self.assertIn('repository evidence', methods,
                      'coding contracts claim the repository-evidence path')

    def test_stored_contracts_carry_claims_for_inspection(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = Store(Path(tmp.name) / 'data')
        job = store.create({'request': 'Name three primary colors.', 'milestones': [
            {'id': 'm1', 'objective': 'Name three primary colors.', 'filename': 'out.md',
             'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 10}]}]})
        stored = store.get(job)['contract']
        self.assertTrue(stored.get('claims'),
                        'a finalized contract carries its explicit claims')

    def test_trivial_requests_are_not_over_verified(self):
        trivial = {'request': 'Name three primary colors.',
                   'milestones': [{'id': 'm1', 'objective': 'Name three primary colors.',
                                   'filename': 'out.md', 'depends_on': [],
                                   'checks': [{'kind': 'min_chars', 'value': 10}]}]}
        validate_contract(trivial)
        claims = completion_claims(trivial)
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]['objective_or_subjective'], 'objective')

    def test_multi_step_claims_mirror_dependencies(self):
        multi = {'request': 'Two independent parts', 'milestones': [
            {'id': 'a', 'objective': 'part a', 'filename': 'a.md', 'depends_on': [],
             'checks': [{'kind': 'min_chars', 'value': 4}]},
            {'id': 'b', 'objective': 'part b', 'filename': 'b.md', 'depends_on': ['a'],
             'checks': [{'kind': 'manual_review', 'rubric': 'covers b'}]}]}
        validate_contract(multi)
        by_id = {c['id']: c for c in completion_claims(multi)}
        self.assertEqual(by_id['b.c1']['dependencies'], ['a'])
        self.assertEqual(by_id['b.c1']['objective_or_subjective'], 'subjective')


class RoutingOutcomeTests(unittest.TestCase):
    def test_escalation_outcomes_are_recorded_for_learning(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = Store(Path(tmp.name) / 'data')
        job = store.create({'request': 'Do the work', 'milestones': [
            {'id': 'm1', 'objective': 'Produce the phrasing', 'filename': 'out.md',
             'depends_on': [], 'checks': [{'kind': 'contains', 'value': 'good-phrase'},
                                          {'kind': 'manual_review', 'rubric': 'meets the request'}]}]})
        run1 = store.claim(job, 'm1', provider='fixture')
        store.enqueue_result('e1', run1['id'], run1['epoch'],
                             {'outcome': 'SUCCESS', 'text': 'bad phrasing without the literal'})
        store.consume()
        self.assertEqual(store.verify(job, 'm1'), 'FAILED')
        with store.transaction() as db:
            row = store._get(db, job)
            row['milestones']['m1'].update(state='NEEDS_REPAIR')
            row.update(state='READY')
            store._save(db, row, 'test.repair')
        run2 = store.claim(job, 'm1', provider='fixture-two')
        store.enqueue_result('e2', run2['id'], run2['epoch'],
                             {'outcome': 'SUCCESS', 'text': 'a good-phrase now appears here'})
        store.consume()
        self.assertEqual(store.verify(job, 'm1'), 'UNCERTAIN')
        artifact = store.get(job)['milestones']['m1']['artifact']
        store.record_review(job, 'm1', artifact['sha256'], 'reviewer', 'VERIFIED',
                            ['Meets the request.'])
        with contextlib.closing(store.connect()) as db:
            outcome = db.execute('SELECT * FROM routing_outcomes WHERE run_id=?',
                                 (run2['id'],)).fetchone()
        self.assertIsNotNone(outcome, 'a verified outcome is recorded for learning')
        self.assertEqual(outcome['escalated'], 1)
        self.assertEqual(outcome['attempts'], 2)
        self.assertIsNone(outcome['job_kind'])


if __name__ == '__main__':
    unittest.main()
