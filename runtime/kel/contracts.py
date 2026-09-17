"""TaskContract and CompletionPacket schemas (v1) for the Workforce OS (Phase 5.0).

Defined by `ux-audit/workforce-os/06_TASK_CONTRACT.md`: a contract freezes what a worker is
asked to do at claim time; a completion packet closes it with evidence, never adjectives.
This module is pure schema validation — contract issuance, claim wiring and closure
enforcement arrive with the D1/D2 increments. Nothing here executes.

Trusted-check rule (mirrors core.validate_contract): verification methods are builtin
checks, independent review, and repository evidence only; executable oracles stay
forbidden. Authority may only narrow the role's ceiling, never widen it.
"""
from .core import PolicyError
from .evidence import COMMAND_BOUND_CLASSES, EVIDENCE_CLASSES
from .workforce import (AUTHORITY_CLASSES, AUTHORITY_RANK, assert_safe, require_integer,
                        require_number, require_text)

SCHEMA_VERSION = 1

ROLES = ('discovery', 'architect', 'designer', 'builder', 'verifier', 'sentinel', 'release')
TIERS = ('D0', 'D1', 'D2', 'D3', 'D4')
CONTRACT_STATES = ('draft', 'approved', 'claimed', 'active', 'verifying', 'closed', 'cancelled')
VERIFICATION_METHODS = ('builtin_check', 'independent_review', 'repository_evidence')
REVIEWER_INDEPENDENCE = ('different_family_if_available', 'any_but_executor')
STOP_CONDITIONS = ('budget_exhausted', 'blocker_unresolvable', 'contract_contradiction',
                   'approval_required_action_reached')
PACKET_OUTCOMES = ('completed', 'failed', 'uncertain', 'blocked')
CLAIM_STATUSES = ('verified', 'failed', 'uncertain')
FINDING_TYPES = ('pitfall', 'pattern', 'preference', 'architecture', 'tool')
FILE_CHANGES = ('added', 'modified', 'deleted')
TEST_RESULTS = ('pass', 'fail', 'skipped')

# Interim static ceilings (doc 03 §7: a contract narrows role authority, never widens it).
# The charters describe richer words (artifact_write, deploy_gated); these are their
# project-effect equivalents. Role registry v2 (increment 5.1) moves these into versioned
# role data and the validator reads the registry instead of this table.
ROLE_MAX_AUTHORITY = {
    'discovery': 'read-only',
    'architect': 'read-only',
    'designer': 'read-only',
    'builder': 'leased-write',
    'verifier': 'read-only',
    'sentinel': 'read-only',
    'release': 'external-effect',
}

CONTRACT_FIELDS = (
    'schema_version', 'mission_id', 'task_id', 'parent_task', 'dedup_fingerprint',
    'objective', 'why', 'scope', 'inputs', 'interfaces', 'role', 'skill_packs', 'tier',
    'staffing_ref', 'authority', 'allowed_tools', 'write_boundaries', 'dependencies',
    'acceptance_criteria', 'evidence_requirements', 'required_reviewer', 'budget',
    'deadline', 'stop_conditions', 'escalation_policy', 'created_by', 'created_at',
    'claimed_by', 'claimed_at', 'state')

PACKET_FIELDS = (
    'schema_version', 'task_id', 'outcome', 'summary', 'artifacts', 'commits_files',
    'evidence', 'tests', 'assumptions', 'decisions', 'findings', 'unresolved_uncertainty',
    'risks', 'blockers', 'follow_ups', 'confidence', 'required_reviewer',
    'reviewer_requirements_met', 'completion_claims', 'budget_spent', 'lineage',
    'resume_hints', 'attestation')


def _object(value, what):
    if not isinstance(value, dict):
        raise PolicyError('%s must be an object' % what)
    return value


def _object_list(value, what):
    if not isinstance(value, list):
        raise PolicyError('%s must be a list' % what)
    for item in value:
        if not isinstance(item, dict):
            raise PolicyError('%s entries must be objects' % what)
    return value


def _enum(value, allowed, what):
    if value not in allowed:
        raise PolicyError('%s must be one of %s' % (what, ', '.join(allowed)))
    return value


def _text_list(value, what, *, allow_empty=False):
    if not isinstance(value, list):
        raise PolicyError('%s must be a list' % what)
    if not allow_empty and not value:
        raise PolicyError('%s needs at least one entry' % what)
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise PolicyError('%s entries must be nonempty strings' % what)
    return value


def _artifact_list(value, what):
    if not isinstance(value, list):
        raise PolicyError('%s must be a list' % what)
    for item in value:
        item = _object(item, what + ' entry')
        require_text(item.get('id'), what + ' entry id')
        require_text(item.get('digest'), what + ' entry digest')
    return value


def _refuse_unknown(mapping, allowed, what):
    unknown = sorted(set(mapping) - set(allowed))
    if unknown:
        raise PolicyError('%s has unknown fields: %s' % (what, ', '.join(unknown)))


def _reviewer(value, what):
    reviewer = _object(value, what)
    _text_list(reviewer.get('lenses'), what + '.lenses', allow_empty=True)
    _enum(reviewer.get('independence'), REVIEWER_INDEPENDENCE, what + '.independence')
    if not isinstance(reviewer.get('oracle'), bool):
        raise PolicyError('%s.oracle must be a boolean' % what)
    return reviewer


def validate_task_contract(contract):
    """Refuse a malformed TaskContract (workforce-os doc 06, schema v1)."""
    contract = _object(contract, 'TaskContract')
    _refuse_unknown(contract, CONTRACT_FIELDS, 'TaskContract')
    if contract.get('schema_version') != SCHEMA_VERSION:
        raise PolicyError('TaskContract schema_version must be %d' % SCHEMA_VERSION)
    require_text(contract.get('mission_id'), 'mission_id')
    task_id = require_text(contract.get('task_id'), 'task_id')
    parent = contract.get('parent_task')
    if parent is not None:
        require_text(parent, 'parent_task')
        if parent == task_id:
            raise PolicyError('A task cannot be its own parent')
    require_text(contract.get('dedup_fingerprint'), 'dedup_fingerprint')
    require_text(contract.get('objective'), 'objective', max_len=500)
    require_text(contract.get('why'), 'why')

    scope = _object(contract.get('scope'), 'scope')
    _text_list(scope.get('includes'), 'scope.includes')
    _text_list(scope.get('excludes'), 'scope.excludes')

    inputs = _object(contract.get('inputs', {}), 'inputs')
    _artifact_list(inputs.get('artifacts', []), 'inputs.artifacts')
    _text_list(inputs.get('context_refs', []), 'inputs.context_refs', allow_empty=True)
    _text_list(contract.get('interfaces', []), 'interfaces', allow_empty=True)

    role = _enum(contract.get('role'), ROLES, 'role (Commander is never spawned)')
    packs = contract.get('skill_packs', [])
    if not isinstance(packs, list) or len(packs) > 4:
        raise PolicyError('skill_packs is a list of at most four packs')
    for pack in packs:
        pack = _object(pack, 'skill_packs entry')
        require_text(pack.get('name'), 'skill pack name')
        require_text(pack.get('version'), 'skill pack version')
    _enum(contract.get('tier'), TIERS, 'tier')
    require_text(contract.get('staffing_ref'), 'staffing_ref')

    authority = _object(contract.get('authority'), 'authority')
    klass = _enum(authority.get('class'), AUTHORITY_CLASSES, 'authority.class')
    if AUTHORITY_RANK[klass] > AUTHORITY_RANK[ROLE_MAX_AUTHORITY[role]]:
        raise PolicyError('Role %s may not hold %s authority (ceiling %s)'
                          % (role, klass, ROLE_MAX_AUTHORITY[role]))
    write_scope = _text_list(authority.get('write_scope', []), 'authority.write_scope',
                             allow_empty=True)
    if klass in ('workspace-write', 'leased-write') and not write_scope:
        raise PolicyError('Write authority needs an explicit write scope')
    if klass not in ('workspace-write', 'leased-write') and write_scope:
        raise PolicyError('Only write authority carries a write scope')
    effects = authority.get('external_effects', 'none')
    if effects == 'none':
        pass
    elif isinstance(effects, list):
        _text_list(effects, 'authority.external_effects')
    else:
        raise PolicyError('authority.external_effects is "none" or a nonempty list')
    if klass == 'external-effect' and effects == 'none':
        raise PolicyError('external-effect authority must list its effects')
    if klass != 'external-effect' and effects != 'none':
        raise PolicyError('Only external-effect authority lists external effects')
    _text_list(contract.get('allowed_tools', []), 'allowed_tools', allow_empty=True)
    _text_list(contract.get('write_boundaries', []), 'write_boundaries', allow_empty=True)

    dependencies = _object(contract.get('dependencies', {}), 'dependencies')
    _text_list(dependencies.get('tasks', []), 'dependencies.tasks', allow_empty=True)
    _artifact_list(dependencies.get('artifacts', []), 'dependencies.artifacts')

    criteria = contract.get('acceptance_criteria')
    if not isinstance(criteria, list) or not criteria:
        raise PolicyError('Acceptance criteria: at least one checkable criterion is required')
    seen = set()
    for item in criteria:
        item = _object(item, 'acceptance criterion')
        criterion_id = require_text(item.get('id'), 'acceptance criterion id')
        if criterion_id in seen:
            raise PolicyError('Acceptance criterion ids must be unique')
        seen.add(criterion_id)
        require_text(item.get('criterion'), 'acceptance criterion text')
        _enum(item.get('verification_method'), VERIFICATION_METHODS,
              'verification_method (trusted checks only; executable oracles are forbidden)')
        _text_list(item.get('evidence_required'), 'evidence_required')

    evidence = _object(contract.get('evidence_requirements'), 'evidence_requirements')
    require_integer(evidence.get('fresh_within'), 'evidence_requirements.fresh_within', lo=1)
    for key in ('command_bound', 'content_bound'):
        if not isinstance(evidence.get(key), bool):
            raise PolicyError('evidence_requirements.%s must be a boolean' % key)

    _reviewer(contract.get('required_reviewer'), 'required_reviewer')

    budget = _object(contract.get('budget'), 'budget')
    require_integer(budget.get('tokens_max'), 'budget.tokens_max', lo=1)
    cost = budget.get('cost_max')
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or cost <= 0:
        raise PolicyError('budget.cost_max must be a positive number')
    require_integer(budget.get('wallclock_max'), 'budget.wallclock_max', lo=1)
    require_integer(budget.get('attempts_max'), 'budget.attempts_max', lo=1, hi=4)

    deadline = contract.get('deadline')
    if deadline is not None and (isinstance(deadline, bool) or not isinstance(deadline, (int, float))):
        raise PolicyError('deadline is a timestamp or null')

    for item in _text_list(contract.get('stop_conditions'), 'stop_conditions'):
        _enum(item, STOP_CONDITIONS, 'stop_conditions entry')
    escalations = contract.get('escalation_policy')
    if not isinstance(escalations, list) or not escalations:
        raise PolicyError('escalation_policy needs at least one rule')
    for item in escalations:
        _object(item, 'escalation rule')
        if not item:
            raise PolicyError('escalation rules are nonempty objects')

    require_text(contract.get('created_by'), 'created_by')
    require_number(contract.get('created_at'), 'created_at')
    if contract.get('claimed_by') is not None:
        require_text(contract['claimed_by'], 'claimed_by')
    if contract.get('claimed_at') is not None:
        require_number(contract['claimed_at'], 'claimed_at')
    _enum(contract.get('state'), CONTRACT_STATES, 'state')

    assert_safe(contract, path='task_contract')
    return contract


def validate_completion_packet(packet):
    """Refuse a malformed CompletionPacket (workforce-os doc 06, schema v1).

    Structural form of closure rules 1-3: a 'completed' outcome cannot carry unverified
    claims, needs complete reviewer coverage, and needs the Oracle when one was required.
    """
    packet = _object(packet, 'CompletionPacket')
    _refuse_unknown(packet, PACKET_FIELDS, 'CompletionPacket')
    if packet.get('schema_version') != SCHEMA_VERSION:
        raise PolicyError('CompletionPacket schema_version must be %d' % SCHEMA_VERSION)
    require_text(packet.get('task_id'), 'task_id')
    outcome = _enum(packet.get('outcome'), PACKET_OUTCOMES, 'outcome')
    require_text(packet.get('summary'), 'summary', max_len=700)

    for item in _object_list(packet.get('artifacts', []), 'artifacts'):
        require_text(item.get('id'), 'artifact id')
        require_text(item.get('digest'), 'artifact digest')
        require_text(item.get('kind'), 'artifact kind')
        if item.get('path') is not None:
            require_text(item['path'], 'artifact path')
        if item.get('bytes') is not None:
            require_integer(item['bytes'], 'artifact bytes', lo=0)

    commits_files = _object(packet.get('commits_files', {}), 'commits_files')
    _text_list(commits_files.get('commits', []), 'commits_files.commits', allow_empty=True)
    for change in _object_list(commits_files.get('files', []), 'commits_files.files'):
        require_text(change.get('path'), 'file path')
        _enum(change.get('change'), FILE_CHANGES, 'file change')
        require_text(change.get('digest'), 'file digest')

    evidence_ids = set()
    for item in _object_list(packet.get('evidence', []), 'evidence'):
        evidence_ids.add(require_text(item.get('id'), 'evidence id'))
        klass = _enum(item.get('class'), EVIDENCE_CLASSES, 'evidence class')
        if klass in COMMAND_BOUND_CLASSES:
            require_text(item.get('command'),
                         'evidence command (command-bound evidence needs the exact command)')
        elif item.get('command') is not None:
            require_text(item['command'], 'evidence command')
        if item.get('exit_code') is not None:
            require_integer(item['exit_code'], 'evidence exit_code')
        output_digest = item.get('output_digest')
        artifact_digest = item.get('artifact_digest')
        if output_digest is not None:
            require_text(output_digest, 'evidence output_digest')
        if artifact_digest is not None:
            require_text(artifact_digest, 'evidence artifact_digest')
        if output_digest is None and artifact_digest is None:
            raise PolicyError('Evidence must bind to something: output_digest or '
                              'artifact_digest is required')
        require_number(item.get('ran_at'), 'evidence ran_at')
        if not isinstance(item.get('freshness_ok'), bool):
            raise PolicyError('evidence freshness_ok must be a boolean')
        require_text(item.get('produced_by'), 'evidence produced_by (never blank)')

    for test in _object_list(packet.get('tests', []), 'tests'):
        require_text(test.get('name'), 'test name')
        require_text(test.get('command'), 'test command')
        _enum(test.get('result'), TEST_RESULTS, 'test result')
        require_text(test.get('digest'), 'test digest')

    _text_list(packet.get('assumptions', []), 'assumptions', allow_empty=True)
    for decision in _object_list(packet.get('decisions', []), 'decisions'):
        require_text(decision.get('id'), 'decision id')
        require_text(decision.get('decision'), 'decision text')
        _text_list(decision.get('alternatives_considered', []), 'decision alternatives',
                   allow_empty=True)
        require_text(decision.get('rationale'), 'decision rationale')
        if decision.get('supersedes') is not None:
            require_text(decision['supersedes'], 'decision supersedes')
    for finding in _object_list(packet.get('findings', []), 'findings'):
        _enum(finding.get('type'), FINDING_TYPES, 'finding type')
        require_text(finding.get('key'), 'finding key')
        require_text(finding.get('insight'), 'finding insight')
        require_integer(finding.get('confidence'), 'finding confidence', lo=1, hi=10)

    uncertainty = _text_list(packet.get('unresolved_uncertainty', []), 'unresolved_uncertainty',
                             allow_empty=True)
    if outcome != 'completed' and not uncertainty:
        raise PolicyError('unresolved_uncertainty is required when the outcome is not completed')

    for risk in _object_list(packet.get('risks', []), 'risks'):
        require_text(risk.get('description'), 'risk description')
        require_text(risk.get('severity'), 'risk severity')
        require_text(risk.get('mitigation_or_acceptance'), 'risk mitigation or acceptance')
    for blocker in _object_list(packet.get('blockers', []), 'blockers'):
        require_text(blocker.get('description'), 'blocker description')
        require_text(blocker.get('owner'), 'blocker owner')
        require_text(blocker.get('requested_action'), 'blocker requested action')
    _text_list(packet.get('follow_ups', []), 'follow_ups', allow_empty=True)

    require_integer(packet.get('confidence'), 'confidence (advisory)', lo=1, hi=10)
    required_reviewer = _reviewer(packet.get('required_reviewer'), 'required_reviewer')
    met = _object(packet.get('reviewer_requirements_met'), 'reviewer_requirements_met')
    for item in _object_list(met.get('lenses_run', []), 'lenses_run'):
        require_text(item.get('lens'), 'lens name')
        require_text(item.get('verdict'), 'lens verdict')
        require_text(item.get('coverage_statement'), 'lens coverage statement')
    if not isinstance(met.get('coverage_complete'), bool):
        raise PolicyError('coverage_complete must be a boolean (missing coverage is never clean)')
    oracle = _object(met.get('oracle', {}), 'reviewer_requirements_met.oracle')
    if not isinstance(oracle.get('ran'), bool):
        raise PolicyError('oracle.ran must be a boolean')

    claims = packet.get('completion_claims')
    if not isinstance(claims, list) or not claims:
        raise PolicyError('completion_claims: at least one claim is required')
    for claim in claims:
        claim = _object(claim, 'completion claim')
        require_text(claim.get('claim_id'), 'claim id')
        status = _enum(claim.get('status'), CLAIM_STATUSES, 'claim status')
        refs = _text_list(claim.get('evidence_refs', []), 'claim evidence_refs', allow_empty=True)
        if status == 'verified' and not refs:
            raise PolicyError('A verified claim must reference at least one evidence record')
        for ref in refs:
            if ref not in evidence_ids:
                raise PolicyError('Claim evidence %s is not in the packet evidence' % ref)

    budget_spent = _object(packet.get('budget_spent'), 'budget_spent')
    for key in ('tokens', 'wallclock', 'attempts'):
        require_integer(budget_spent.get(key), 'budget_spent.' + key, lo=0)
    cost = budget_spent.get('cost')
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or cost < 0:
        raise PolicyError('budget_spent.cost must be a non-negative number')

    lineage = _object(packet.get('lineage', {}), 'lineage')
    _text_list(lineage.get('inputs_consumed', []), 'lineage.inputs_consumed', allow_empty=True)
    _text_list(lineage.get('artifacts_produced', []), 'lineage.artifacts_produced', allow_empty=True)
    if lineage.get('parent_packet') is not None:
        require_text(lineage['parent_packet'], 'lineage.parent_packet')
    if packet.get('resume_hints') is not None:
        require_text(packet['resume_hints'], 'resume_hints')

    attestation = _object(packet.get('attestation'), 'attestation')
    for key in ('provider', 'model', 'runtime', 'prompt_hash'):
        require_text(attestation.get(key), 'attestation.' + key)
    _text_list(attestation.get('tool_grants_snapshot', []), 'attestation.tool_grants_snapshot',
               allow_empty=True)

    if outcome == 'completed':
        for claim in claims:
            if claim.get('status') != 'verified':
                raise PolicyError('A completed task cannot carry a %s claim' % claim.get('status'))
        if not met.get('coverage_complete'):
            raise PolicyError('A completed task needs complete reviewer coverage')
        covered = {item.get('lens') for item in met.get('lenses_run', [])}
        missing = [name for name in required_reviewer.get('lenses', []) if name not in covered]
        if missing:
            raise PolicyError('A completed packet is missing required reviewer coverage: %s'
                              % ', '.join(missing))
        if required_reviewer.get('oracle') and not oracle.get('ran'):
            raise PolicyError('This packet requires an Oracle review that did not run')

    assert_safe(packet, path='completion_packet')
    return packet
