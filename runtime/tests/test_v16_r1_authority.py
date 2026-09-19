"""Round 2.5 R1 — AUTH-DELEGATION: delegation may narrow authority, never create it.

Three layers of evidence:
1. the pure containment primitive (`authority_within`) over every dimension a TaskContract
   carries;
2. the issuance-time check (`validate_task_contract(parent_authority=...)`) — widening attempts
   refused on each dimension, genuine narrowing accepted, a nested contract that names no
   delegator refused outright;
3. the real D1/D2 issuance path (`issue_task_contract`) passing the envelope through.
"""
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from workforce_fixtures import contract  # noqa: E402

from kel import assignment, delegation, workforce  # noqa: E402
from kel.contracts import validate_task_contract  # noqa: E402
from kel.core import PolicyError, Store  # noqa: E402
from kel.workforce import authority_within  # noqa: E402


class AuthorityWithinTests(unittest.TestCase):
    """The executable form of AUTH-DELEGATION over the contract-carried dimensions."""

    def _parent(self, **overrides):
        parent = {'class': 'leased-write', 'write_scope': ['src', 'tests'],
                  'external_effects': 'none',
                  'allowed_tools': ['read_context', 'write_files', 'run_tests'],
                  'write_boundaries': ['src', 'tests']}
        parent.update(overrides)
        return parent

    def test_an_equal_or_narrower_child_is_contained(self):
        parent = self._parent()
        for child in (parent,
                      {'class': 'read-only', 'write_scope': [], 'external_effects': 'none',
                       'allowed_tools': ['read_context'], 'write_boundaries': []},
                      {'class': 'leased-write', 'write_scope': ['src/app.py'],
                       'external_effects': 'none', 'allowed_tools': ['write_files'],
                       'write_boundaries': ['src']}):
            self.assertIsNone(authority_within(child, parent), child)

    def test_a_wider_class_is_refused(self):
        gap = authority_within({'class': 'external-effect'},
                               self._parent(external_effects=['deploy']))
        self.assertIn('external-effect exceeds leased-write', gap)

    def test_a_scope_that_escapes_the_delegator_is_refused(self):
        gap = authority_within({'write_scope': ['secrets/keys.txt']}, self._parent())
        self.assertIn('escapes the delegator scope', gap)
        self.assertIsNone(authority_within({'write_scope': ['src/nested/file.py']},
                                           self._parent()))

    def test_an_effect_the_delegator_does_not_hold_is_refused(self):
        parent = self._parent(**{'class': 'external-effect', 'external_effects': ['deploy']})
        gap = authority_within({'class': 'external-effect', 'external_effects': ['publish']}, parent)
        self.assertIn('external effect', gap)
        self.assertIsNone(authority_within({'class': 'external-effect',
                                            'external_effects': ['deploy']}, parent))

    def test_a_tool_outside_the_delegator_grant_is_refused(self):
        gap = authority_within({'allowed_tools': ['run_tests', 'deploy_app']}, self._parent())
        self.assertIn("tool 'deploy_app'", gap)

    def test_an_empty_delegator_scope_is_a_real_ceiling(self):
        parent = self._parent(**{'class': 'read-only', 'write_scope': []})
        gap = authority_within({'write_scope': ['src/app.py']}, parent)
        self.assertIn('escapes the delegator scope', gap)

    def test_an_unconstrained_dimension_places_no_ceiling(self):
        self.assertIsNone(authority_within({'allowed_tools': ['anything'],
                                            'write_scope': ['src/app.py']},
                                           {'class': 'leased-write'}))
        self.assertIsNone(authority_within({'external_effects': []}, {'class': 'leased-write'}))

    def test_an_unknown_class_is_refused_not_silently_allowed(self):
        self.assertIn('unknown authority class',
                      authority_within({'class': 'root'}, {'class': 'read-only'}))


class ContractParentAuthorityTests(unittest.TestCase):
    """Issuance-time enforcement on the frozen TaskContract schema."""

    def _parent(self, **overrides):
        parent = {'class': 'leased-write', 'write_scope': ['src', 'tests'],
                  'external_effects': 'none',
                  'allowed_tools': ['read_context', 'write_files', 'run_tests']}
        parent.update(overrides)
        return parent

    def test_genuine_narrowing_is_accepted(self):
        narrowed = contract(
            authority={'class': 'read-only', 'write_scope': [], 'external_effects': 'none'},
            allowed_tools=['read_context'], write_boundaries=[])
        validate_task_contract(narrowed, parent_authority=self._parent())

    def test_a_wider_authority_class_is_refused(self):
        # The class stays inside the role ceiling (builder → leased-write) so this isolates the
        # delegation dimension: the delegator holds only read authority, the child writes.
        wider = contract(authority={'class': 'leased-write', 'write_scope': ['src/app.py'],
                                    'external_effects': 'none'},
                         write_boundaries=['src'], allowed_tools=['read_context'])
        parent = self._parent(**{'class': 'read-only', 'write_scope': []})
        with self.assertRaises(PolicyError) as caught:
            validate_task_contract(wider, parent_authority=parent)
        self.assertIn('Delegation may narrow authority but never create it', str(caught.exception))

    def test_a_scope_outside_the_delegator_is_refused(self):
        escaped = contract(authority={'class': 'leased-write',
                                      'write_scope': ['secrets/keys.txt'],
                                      'external_effects': 'none'},
                           write_boundaries=['secrets'])
        with self.assertRaises(PolicyError) as caught:
            validate_task_contract(escaped, parent_authority=self._parent())
        self.assertIn('never create it', str(caught.exception))

    def test_a_tool_outside_the_delegator_grant_is_refused(self):
        with self.assertRaises(PolicyError) as caught:
            validate_task_contract(contract(), parent_authority=self._parent(
                allowed_tools=['read_context']))
        self.assertIn("tool 'write_files'", str(caught.exception))

    def test_an_effect_outside_the_delegator_is_refused(self):
        # The `release` role is the one whose ceiling permits external-effect authority, so the
        # refusal here is the delegation check rather than the role ceiling.
        child = contract(role='release',
                         authority={'class': 'external-effect', 'write_scope': [],
                                    'external_effects': ['publish']},
                         write_boundaries=[], allowed_tools=['read_context'])
        parent = self._parent(**{'class': 'external-effect', 'external_effects': ['deploy']})
        with self.assertRaises(PolicyError) as caught:
            validate_task_contract(child, parent_authority=parent)
        self.assertIn('external effect', str(caught.exception))

    def test_a_nested_contract_without_a_declared_delegator_is_refused(self):
        nested = contract(parent_task='tsk_' + 'd' * 12)
        with self.assertRaises(PolicyError) as caught:
            validate_task_contract(nested)
        self.assertIn('must declare its delegator authority', str(caught.exception))

    def test_a_write_scope_outside_the_declared_boundaries_is_refused(self):
        contradictory = contract(authority={'class': 'leased-write',
                                            'write_scope': ['other/thing.py'],
                                            'external_effects': 'none'},
                                 write_boundaries=['src', 'tests'])
        with self.assertRaises(PolicyError) as caught:
            validate_task_contract(contradictory)
        self.assertIn('write_scope must stay inside the declared write boundaries',
                      str(caught.exception))

    def test_the_plain_contract_still_validates_without_a_parent(self):
        validate_task_contract(contract())


class IssuanceWiringTests(unittest.TestCase):
    """The real D1/D2 issuance path carries the delegator envelope into validation."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup_tmp)
        self.store = Store(Path(self.tmp.name) / 'kel.sqlite3')
        workforce.ensure_schema(self.store)
        delegation.ensure_schema(self.store)
        assignment.ensure_schema(self.store)

    def _cleanup_tmp(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def _parts(self, klass='leased-write'):
        job = {'id': 'job_r1',
               'contract': {'milestones': [{'id': 'm1', 'objective': 'Draft the thing',
                                            'filename': 'out.md', 'checks': []}]}}
        spec = job['contract']['milestones'][0]
        role_fields = {'authority_max': klass, 'tool_policy': {'allow': ['read_context']}}
        return job, spec, role_fields

    def _issue(self, parent_authority):
        job, spec, role_fields = self._parts()
        return delegation.issue_task_contract(
            self.store, job, spec, {'scope': ['src/app.py']}, role='builder',
            task_id='tsk_' + 'e' * 12, staffing_id='stf_' + 'f' * 12,
            staffing_result={'tier': 'D2'}, role_fields=role_fields,
            parent_authority=parent_authority)

    def test_a_child_wider_than_the_delegator_is_refused(self):
        with self.assertRaises(PolicyError) as caught:
            self._issue({'class': 'read-only', 'write_scope': [], 'external_effects': 'none'})
        self.assertIn('never create it', str(caught.exception))

    def test_the_same_issuance_is_accepted_inside_a_held_envelope(self):
        contract_row, contract_id = self._issue(
            {'class': 'leased-write', 'write_scope': ['src'], 'external_effects': 'none'})
        self.assertTrue(contract_id.startswith('ctr_'))
        self.assertEqual(contract_row['authority']['class'], 'leased-write')
        self.assertEqual(contract_row['parent_task'], None)

    def test_without_a_parent_authority_the_existing_path_is_unchanged(self):
        contract_row, contract_id = self._issue(None)
        self.assertTrue(contract_id.startswith('ctr_'))

    def test_reserving_inside_the_job_envelope_is_accepted(self):
        job = self.store.create({
            'request': 'R1 budget fixture',
            'milestones': [{'id': 'm1', 'objective': 'Draft', 'filename': 'out.md',
                            'depends_on': [],
                            'checks': [{'kind': 'min_chars', 'value': 20}]}]})
        row = delegation.reserve_budget(self.store, job, budget_class='standard',
                                        tokens=1000, wallclock=60, cost=8)
        self.assertEqual(row['state'], 'reserved')

    def test_reserving_beyond_the_job_envelope_is_refused(self):
        # AUTH-DELEGATION, budget dimension: the job envelope is the delegator's budget
        # authority; a delegated reservation may narrow it, never create more.
        job = self.store.create({
            'request': 'R1 budget fixture',
            'milestones': [{'id': 'm1', 'objective': 'Draft', 'filename': 'out.md',
                            'depends_on': [],
                            'checks': [{'kind': 'min_chars', 'value': 20}]}]})
        with self.assertRaises(PolicyError) as caught:
            delegation.reserve_budget(self.store, job, budget_class='standard',
                                      tokens=1000, wallclock=60, cost=9)
        self.assertIn('exceeds the remaining job budget', str(caught.exception))

    def test_a_second_reservation_sees_the_first_commitment(self):
        # Campaign C AUD-MINOR-002: successive delegated reservations aggregate against the
        # same job envelope; the second may not pass on the first's margin.
        job = self.store.create({
            'request': 'R1 budget fixture',
            'milestones': [{'id': 'm1', 'objective': 'Draft', 'filename': 'out.md',
                            'depends_on': [],
                            'checks': [{'kind': 'min_chars', 'value': 20}]}]})
        first = delegation.reserve_budget(self.store, job, budget_class='standard',
                                          tokens=1000, wallclock=60, cost=5)
        self.assertEqual(first['state'], 'reserved')
        with self.assertRaises(PolicyError) as caught:
            delegation.reserve_budget(self.store, job, budget_class='standard',
                                      tokens=1000, wallclock=60, cost=4)
        self.assertIn('exceeds the remaining job budget', str(caught.exception))
        self.assertIn('3.0', str(caught.exception))
        tail = delegation.reserve_budget(self.store, job, budget_class='standard',
                                         tokens=1000, wallclock=60, cost=3)
        self.assertEqual(tail['state'], 'reserved')


if __name__ == '__main__':
    unittest.main()
