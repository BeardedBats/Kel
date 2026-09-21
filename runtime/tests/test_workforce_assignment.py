"""Phase 5.1: agent-to-model assignment — registry v2, routing modes, grants, reservations.

Verification for `kel/assignment.py` (workforce-os docs 03 §7-8, 10, 14 §3): the archetype
registry seeds idempotently and carries the v2 fields; AUTO / PREFERRED / FIXED resolve the
same role to different (provider, model, runtime) bindings; capability grants are fail-closed
against the authority ceiling; budget reservations are recorded and linked; the assignment
snapshot freezes the binding and survives later role edits.
"""
import contextlib
import json
import tempfile
import unittest
from pathlib import Path

from kel.assignment import (ARCHETYPES, DISPATCH_TIERS, REQUIREMENTS, ROUTING_MODES,
                            TOOL_AUTHORITY, assign_worker, candidates_from_providers,
                            ensure_archetypes, flags_snapshot, get_reservation, grants_for,
                            overlay_for, registry_ceilings, release_budget, require_grants,
                            reserve_budget, reservations, resolve_binding,
                            validate_role_fields_v2)
from kel.assignment import ensure_schema as ensure_assignment_schema
from kel.context import Context
from kel.contracts import ROLE_MAX_AUTHORITY, validate_task_contract
from kel.core import PolicyError, Store
from kel.router import Candidate
from kel.team import TOOLS, Team


from workforce_fixtures import candidates, job_contract


def v2_fields(**overrides):
    fields = {'goal': 'Produce the artifact.', 'inputs': 'brief', 'outputs': 'out.md',
              'quality_bar': 'Checks pass.', 'boundaries': 'leased scope only',
              'escalation': 'blockers to commander', 'evidence_expectations': 'test runs',
              'tool_policy': {'allow': ['read', 'write', 'run_tests'], 'deny': ['shell']},
              'budget': 8,
              'authority_max': 'leased-write',
              'capability_requirements': ['repository_edit'],
              'dispatch_tier': 'standard', 'budget_class': 'standard',
              'default_skill_packs': ['testing'],
              'independence': {'may_not_review_own': True,
                               'reviewer_family': 'any_but_executor'},
              'anti_patterns': ['gold-plating']}
    fields.update(overrides)
    return fields


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'data')
        ensure_assignment_schema(self.store)
        self.context = Context(self.store)
        self.conversation = self.context.conversation('default', title='Assignment tests')
        self.team = Team(self.store)
        self.job_id = self.store.create(job_contract(), conversation=self.conversation)


class VocabTests(unittest.TestCase):
    def test_vocabulary_matches_the_design(self):
        self.assertEqual(ROUTING_MODES, ('AUTO', 'PREFERRED', 'FIXED'))
        self.assertEqual(DISPATCH_TIERS, ('fast', 'standard', 'deep', 'assurance'))
        self.assertEqual(len(REQUIREMENTS), 10)
        self.assertEqual(len(TOOL_AUTHORITY), 8)
        for tool in TOOLS:
            self.assertIn(tool, TOOL_AUTHORITY)


class ArchetypeTests(Base):
    def test_archetypes_seed_idempotently(self):
        created = ensure_archetypes(self.store)
        self.assertEqual(created, ['discovery', 'architect', 'designer', 'builder',
                                   'verifier', 'sentinel', 'release'])
        self.assertEqual(ensure_archetypes(self.store), [])
        ids = {row['template_id'] for row in self.team.roster()}
        for template_id, _name, _department, _fields in ARCHETYPES:
            self.assertIn(template_id, ids)

    def test_every_archetype_carries_valid_v2_fields(self):
        ensure_archetypes(self.store)
        for template_id, _name, _department, fields in ARCHETYPES:
            validate_role_fields_v2(fields)
            version, stored = self.team.current_version(template_id)
            self.assertEqual(version, 1)
            self.assertEqual(stored['authority_max'], fields['authority_max'])
            self.assertEqual(stored['capability_requirements'],
                             fields['capability_requirements'])

    def test_role_v2_validation_refuses_malformed_values(self):
        with self.assertRaises(PolicyError):
            validate_role_fields_v2(v2_fields(authority_max='omnipotent'))
        with self.assertRaises(PolicyError):
            validate_role_fields_v2(v2_fields(capability_requirements=['telepathy']))
        with self.assertRaises(PolicyError):
            validate_role_fields_v2(v2_fields(dispatch_tier='turbo'))
        with self.assertRaises(PolicyError):
            validate_role_fields_v2(v2_fields(budget_class='enormous'))
        incomplete = v2_fields()
        del incomplete['anti_patterns']
        with self.assertRaises(PolicyError):
            validate_role_fields_v2(incomplete)

    def test_registry_ceilings_match_the_contract_ceiling_table(self):
        ensure_archetypes(self.store)
        ceilings = registry_ceilings(self.store)
        for role, klass in ROLE_MAX_AUTHORITY.items():
            self.assertEqual(ceilings.get(role), klass)


class ModeTests(Base):
    def test_auto_selects_the_cheapest_sufficient_eligible(self):
        binding = resolve_binding(candidates(), mode='AUTO', requirements=['repository_edit'])
        self.assertEqual(binding['selected']['provider'], 'codex')
        self.assertEqual(binding['selected']['model'], 'codex-native')
        self.assertEqual(binding['selected']['runtime'], 'native-cli')
        self.assertEqual(binding['policy'], 'eligible-cost-v2')
        self.assertEqual(binding['fallback_basis'], 'eligible-cost-order')
        self.assertEqual([f['provider'] for f in binding['fallbacks']], ['claude-code'])

    def test_preferred_order_is_honored_and_fallbacks_recorded(self):
        binding = resolve_binding(candidates(), mode='PREFERRED',
                                  requirements=['repository_edit'],
                                  preferred=['claude-code', 'codex'])
        self.assertEqual(binding['selected']['provider'], 'claude-code')
        self.assertEqual(binding['fallbacks'][0]['provider'], 'codex')
        self.assertEqual(binding['policy'], 'preferred-order-v1')
        self.assertEqual(binding['fallback_basis'], 'preferred-order-then-cost')

    def test_preferred_needs_an_eligible_entry(self):
        with self.assertRaises(PolicyError):
            resolve_binding(candidates(), mode='PREFERRED', requirements=['vision'],
                            preferred=['codex'])

    def test_fixed_validates_and_never_substitutes(self):
        binding = resolve_binding(candidates(), mode='FIXED', requirements=['repository_edit'],
                                  fixed={'provider': 'claude-code'})
        self.assertEqual(binding['selected']['provider'], 'claude-code')
        self.assertEqual(binding['selected']['model'], 'claude-native')
        self.assertEqual(binding['policy'], 'fixed-pin-v1')
        self.assertEqual(binding['fallback_basis'], 'eligible-cost-order-excluding-pin')

    def test_fixed_ineligible_is_refused(self):
        with self.assertRaises(PolicyError):
            resolve_binding(candidates(), mode='FIXED', requirements=['vision'],
                            fixed={'provider': 'codex'})

    def test_fixed_model_must_declare_the_required_capabilities(self):
        with self.assertRaises(PolicyError):
            resolve_binding(candidates(), mode='FIXED', requirements=['vision'],
                            fixed={'provider': 'internal', 'model': 'not-a-model'})

    def test_mode_contract(self):
        with self.assertRaises(PolicyError):
            resolve_binding(candidates(), mode='AUTO', preferred=['codex'])
        with self.assertRaises(PolicyError):
            resolve_binding(candidates(), mode='BEST')
        with self.assertRaises(PolicyError):
            resolve_binding(candidates(), mode='PREFERRED', preferred=[])
        with self.assertRaises(PolicyError):
            resolve_binding(candidates(), mode='PREFERRED', preferred=['codex'],
                            fixed={'provider': 'codex'})
        with self.assertRaises(PolicyError):
            resolve_binding(candidates(), mode='FIXED', fixed={'provider': 'codex'},
                            preferred=['codex'])

    def test_advisory_requirements_are_recorded_not_filtering(self):
        binding = resolve_binding(candidates(), mode='AUTO',
                                  requirements=['long_context', 'structured_output'])
        self.assertEqual(sorted(binding['requirements']['advisory']),
                         ['long_context', 'structured_output'])
        self.assertEqual(binding['requirements']['enforced'], [])
        self.assertEqual(binding['selected']['provider'], 'codex')

    def test_unsatisfiable_requirement_fails_closed(self):
        with self.assertRaises(PolicyError):
            resolve_binding(candidates(), mode='AUTO', requirements=['web_research'])

    def test_local_only_filters_by_privacy(self):
        with self.assertRaises(PolicyError):
            resolve_binding(candidates(), mode='AUTO', requirements=['local_only'])
        local = candidates()
        local[2].privacy = 'local'
        binding = resolve_binding(local, mode='AUTO', requirements=['local_only'])
        self.assertEqual(binding['selected']['provider'], 'internal')
        self.assertEqual(binding['requirements']['privacy_enforced'], ['local_only'])
        self.assertNotIn('local_only', binding['requirements']['advisory'])

    def test_candidates_from_providers_covers_the_registry(self):
        names = {c.name for c in candidates_from_providers(self.store)}
        self.assertGreaterEqual(names, {'claude-code', 'codex', 'internal', 'deepseek'})

    def test_enforced_capabilities_need_a_model_that_declares_them(self):
        # N1 follow-up: a provider whose capability union is sufficient but whose models
        # cannot be verified must not freeze a binding with model=None (or accept a pin).
        synthetic = [Candidate(name='synthetic', capabilities={'text', 'edit'}, cost=1.0)]
        with self.assertRaises(PolicyError):
            resolve_binding(synthetic, mode='AUTO', requirements=['repository_edit'])
        with self.assertRaises(PolicyError):
            resolve_binding(synthetic, mode='FIXED', requirements=['repository_edit'],
                            fixed={'provider': 'synthetic', 'model': 'synthetic-model'})


class GrantTests(Base):
    def test_grants_pass_inside_the_ceiling(self):
        grants = require_grants('leased-write',
                                {'allow': ['read', 'write', 'run_tests', 'git'], 'deny': []})
        self.assertEqual(sorted(grants['allowed']), ['git', 'read', 'run_tests', 'write'])
        self.assertEqual(grants['denied'], {})

    def test_grants_fail_closed_outside_the_ceiling(self):
        grants = grants_for('read-only', {'allow': ['read', 'write', 'shell'], 'deny': []})
        self.assertIn('write', grants['denied'])
        self.assertIn('shell', grants['denied'])
        self.assertIn('read', grants['allowed'])
        with self.assertRaises(PolicyError):
            require_grants('read-only', {'allow': ['write'], 'deny': []})

    def test_archetype_grants_are_inside_their_ceilings(self):
        for template_id, _name, _department, fields in ARCHETYPES:
            require_grants(fields['authority_max'], fields['tool_policy'])


class ReservationTests(Base):
    def test_reserve_release_and_inspect(self):
        row = reserve_budget(self.store, self.job_id, budget_class='standard',
                             tokens=40000, wallclock=900, cost=1.5, milestone_id='m1')
        self.assertEqual(row['state'], 'reserved')
        listed = reservations(self.store, job_id=self.job_id, state='reserved')
        self.assertEqual(listed[0]['tokens'], 40000)
        released = release_budget(self.store, row['reservation_id'])
        self.assertEqual(released['state'], 'released')
        with self.assertRaises(PolicyError):
            release_budget(self.store, row['reservation_id'])

    def test_reservations_validate_inputs(self):
        with self.assertRaises(PolicyError):
            reserve_budget(self.store, 'job_nope', budget_class='standard', tokens=1,
                           wallclock=1, cost=0)
        with self.assertRaises(PolicyError):
            reserve_budget(self.store, self.job_id, budget_class='enormous', tokens=1,
                           wallclock=1, cost=0)
        with self.assertRaises(PolicyError):
            reserve_budget(self.store, self.job_id, budget_class='standard', tokens=0,
                           wallclock=1, cost=0)

    def test_unknown_reservation_is_refused(self):
        with self.assertRaises(PolicyError):
            get_reservation(self.store, 'nope')

    def test_state_filter_is_validated(self):
        with self.assertRaises(PolicyError):
            reservations(self.store, state='bogus')


class ReservationAccountingTests(Base):
    """AUD-MINOR-002 (Campaign C): commitments aggregate; the envelope is shared.

    The job envelope is the delegator's budget authority: every reservation that has not been
    explicitly released narrows it (reserved AND consumed), so successive reservations can
    never sum beyond `budget - spent - reserved`.
    """

    def _reserve(self, job_id, cost, **overrides):
        params = {'budget_class': 'standard', 'tokens': 1000, 'wallclock': 60, 'cost': cost}
        params.update(overrides)
        return reserve_budget(self.store, job_id, **params)

    def test_the_second_reservation_sees_the_first(self):
        first = self._reserve(self.job_id, 1)
        self.assertEqual(first['state'], 'reserved')
        with self.assertRaises(PolicyError) as caught:
            self._reserve(self.job_id, 8)
        # 8 (budget) - 1 (live commitment) = 7 remains; the first reservation is intact.
        self.assertIn('remaining job budget', str(caught.exception))
        self.assertIn('7.0', str(caught.exception))
        self.assertEqual(len(reservations(self.store, job_id=self.job_id, state='reserved')), 1)

    def test_cumulative_reservations_fill_then_exceed_the_envelope(self):
        self._reserve(self.job_id, 3)
        self._reserve(self.job_id, 4)                    # 3 + 4 = 7 <= 8
        with self.assertRaises(PolicyError) as caught:
            self._reserve(self.job_id, 2)                # 7 + 2 = 9 > 8
        self.assertIn('1.0', str(caught.exception))
        self.assertEqual(self._reserve(self.job_id, 1)['state'], 'reserved')  # exactly fills

    def test_release_frees_the_envelope_for_the_next_commitment(self):
        first = self._reserve(self.job_id, 1)
        with self.assertRaises(PolicyError):
            self._reserve(self.job_id, 8)
        released = release_budget(self.store, first['reservation_id'])
        self.assertEqual(released['state'], 'released')
        self.assertEqual(self._reserve(self.job_id, 8)['state'], 'reserved')

    def test_a_consumed_estimate_keeps_narrowing_the_envelope(self):
        # 'consumed' means the estimate was used; only an explicit release returns budget.
        first = self._reserve(self.job_id, 5)
        release_budget(self.store, first['reservation_id'], consumed=True)
        with self.assertRaises(PolicyError) as caught:
            self._reserve(self.job_id, 4)                # only 3 remains
        self.assertIn('3.0', str(caught.exception))

    def test_zero_and_exact_values_are_accepted(self):
        self.assertEqual(self._reserve(self.job_id, 0)['state'], 'reserved')
        self.assertEqual(self._reserve(self.job_id, 8)['state'], 'reserved')  # exact envelope

    def test_disjoint_jobs_do_not_share_the_envelope(self):
        other = self.store.create(job_contract(), conversation=self.conversation)
        self._reserve(self.job_id, 8)
        self.assertEqual(self._reserve(other, 8)['state'], 'reserved')

    def test_retry_after_release_reserves_again_without_stacking(self):
        first = self._reserve(self.job_id, 5, milestone_id='m1')
        release_budget(self.store, first['reservation_id'])        # attempt failed; free it
        second = self._reserve(self.job_id, 5, milestone_id='m1')  # retry may claim it again
        self.assertEqual(second['state'], 'reserved')
        states = {row['state'] for row in reservations(self.store, job_id=self.job_id)}
        self.assertEqual(states, {'released', 'reserved'})

    def test_token_and_wallclock_stay_disclosed_not_enforced(self):
        # Disclosed policy (R1-AUTHORITY-CEILING limitations): only cost is checked against
        # the envelope; tokens/wallclock are validated for shape and recorded. Pinned so any
        # future enforcement change is deliberate, not drift.
        row = self._reserve(self.job_id, 1, tokens=10 ** 12, wallclock=10 ** 7)
        self.assertEqual(row['tokens'], 10 ** 12)
        with self.assertRaises(PolicyError):
            self._reserve(self.job_id, 1, tokens=0)


class AssignWorkerTests(Base):
    def setUp(self):
        super().setUp()
        ensure_archetypes(self.store)

    def _snapshot(self, assignment_id):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT provider, model, snapshot FROM team_assignments'
                             ' WHERE assignment_id=?', (assignment_id,)).fetchone()
        return row, json.loads(row['snapshot'])

    def test_assign_worker_snapshots_the_binding(self):
        result = assign_worker(self.store, self.job_id, 'm1', 'builder', mode='FIXED',
                               fixed={'provider': 'codex'}, candidates=candidates())
        row, snapshot = self._snapshot(result['assignment_id'])
        self.assertEqual(row['provider'], 'codex')
        self.assertEqual(row['model'], 'codex-native')
        workforce = snapshot['workforce']
        self.assertEqual(workforce['mode'], 'FIXED')
        self.assertEqual(workforce['binding']['selected'],
                         {'provider': 'codex', 'model': 'codex-native', 'runtime': 'native-cli'})
        self.assertEqual(workforce['role_authority_max'], 'leased-write')
        self.assertEqual(workforce['grants']['allowed'],
                         sorted(['read', 'write', 'run_tests', 'install', 'git']))
        self.assertFalse(workforce['flags']['workforce.enabled'])

    def test_snapshot_survives_a_later_role_edit(self):
        result = assign_worker(self.store, self.job_id, 'm1', 'builder', mode='AUTO',
                               candidates=candidates())
        self.team.edit_role('builder', {'authority_max': 'read-only'})
        _row, snapshot = self._snapshot(result['assignment_id'])
        self.assertEqual(snapshot['workforce']['role_authority_max'], 'leased-write')
        resolved = self.team.resolve_role('builder')
        self.assertEqual(resolved['fields']['authority_max'], 'read-only')
        with self.assertRaises(PolicyError):
            assign_worker(self.store, self.job_id, 'm1', 'builder', mode='AUTO',
                          candidates=candidates())

    def test_assign_worker_refuses_legacy_roles_without_v2_fields(self):
        self.team.seed_defaults()
        with self.assertRaises(PolicyError):
            assign_worker(self.store, self.job_id, 'm1', 'implementation-engineer',
                          mode='AUTO', candidates=candidates())

    def test_reservation_links_into_the_assignment(self):
        row = reserve_budget(self.store, self.job_id, budget_class='standard',
                             tokens=1000, wallclock=60, cost=0.5)
        result = assign_worker(self.store, self.job_id, 'm1', 'builder', mode='AUTO',
                               candidates=candidates(), reservation=row['reservation_id'])
        linked = get_reservation(self.store, row['reservation_id'])
        self.assertEqual(linked['assignment_id'], result['assignment_id'])
        _row, snapshot = self._snapshot(result['assignment_id'])
        self.assertEqual(snapshot['workforce']['reservation_id'], row['reservation_id'])

    def test_reservation_from_another_job_is_refused(self):
        other_job = self.store.create(job_contract(), conversation=self.conversation)
        row = reserve_budget(self.store, other_job, budget_class='standard', tokens=1,
                             wallclock=1, cost=0)
        with self.assertRaises(PolicyError):
            assign_worker(self.store, self.job_id, 'm1', 'builder', mode='AUTO',
                          candidates=candidates(), reservation=row['reservation_id'])

    def test_reservation_milestone_must_match(self):
        row = reserve_budget(self.store, self.job_id, budget_class='standard', tokens=1,
                             wallclock=1, cost=0, milestone_id='m2')
        with self.assertRaises(PolicyError):
            assign_worker(self.store, self.job_id, 'm1', 'builder', mode='AUTO',
                          candidates=candidates(), reservation=row['reservation_id'])

    def test_snapshot_extras_are_guarded(self):
        with self.assertRaises(PolicyError):
            self.team.create_assignment(self.job_id, 'm1', 'builder',
                                        extra={'role_template': 'spoofed'})
        with self.assertRaises(PolicyError):
            self.team.create_assignment(self.job_id, 'm1', 'builder',
                                        extra={'notes': {'chain_of_thought': 'because'}})


class OverlayTests(unittest.TestCase):
    def test_absent_overlay_is_a_graceful_noop(self):
        self.assertIsNone(overlay_for('codex', 'codex-native'))
        binding = resolve_binding(candidates(), mode='AUTO', requirements=['repository_edit'])
        self.assertIsNone(binding['overlay'])

    def test_overlay_registry_hits_exact_then_family(self):
        registry = {'codex:codex-native': {'note': 'exact'},
                    'codex:*': {'note': 'family'}}
        self.assertEqual(overlay_for('codex', 'codex-native', registry=registry)['note'],
                         'exact')
        self.assertEqual(overlay_for('codex', 'other-model', registry=registry)['note'],
                         'family')


class FlagsTests(unittest.TestCase):
    def test_workforce_flags_default_off_and_env_opt_in(self):
        self.assertFalse(flags_snapshot(env={})['workforce.enabled'])
        self.assertTrue(flags_snapshot(env={'KEL_WORKFORCE': '1'})['workforce.enabled'])
        self.assertTrue(flags_snapshot(env={'KEL_WORKFORCE': 'true'})['workforce.enabled'])
        self.assertFalse(flags_snapshot(env={'KEL_WORKFORCE': '0'})['workforce.enabled'])


class CeilingTests(Base):
    def test_ceilings_table_flows_from_the_registry(self):
        from workforce_fixtures import contract as task_contract
        ensure_archetypes(self.store)
        ceilings = registry_ceilings(self.store)
        widened = task_contract(role='verifier',
                                authority={'class': 'leased-write',
                                           'write_scope': ['src/api/export.py'],
                                           'external_effects': 'none'})
        with self.assertRaises(PolicyError):
            validate_task_contract(widened, ceilings=ceilings)
        with self.assertRaises(PolicyError):
            validate_task_contract(task_contract(),
                                   ceilings={'builder': 'workspace-write'})


if __name__ == '__main__':
    unittest.main()
