"""D1 single-specialist delegation (Phase 5.2): staffing decision, contract issuance,
evidence-bound completion, and task/progress ledger projections.

Design: `ux-audit/workforce-os/15_PHASE5_IMPLEMENTATION_SPEC.md` §5.2 and docs 05 (staffing),
06 (TaskContract/CompletionPacket), 14 §2 (ledger projections). One bounded delegated job:
`delegate()` decides (D0 -> nothing; D1 -> one specialist) and issues a frozen TaskContract;
the caller runs exactly one worker; `close_d1()` accepts a CompletionPacket only when every
claim rests on fresh, content-bound evidence — stale-evidence closes are impossible by
construction. `run_d1()` is the fixture orchestrator used by tests and demos. Nothing live
calls these functions yet; with the flag off `delegate()` performs no writes at all.

Boundaries:
- No nested spawning: the workforce tool vocabulary has no spawn tool, and this module creates
  exactly one assignment per task.
- `task_contracts` rows stay append-only (5.0 triggers); migration 18 adds `milestone_id` so
  tasks join to jobs/milestones (doc 14: "keyed to milestone").
- Ledger projections are read-only; no new persistence beyond migration 18's column.
"""
import contextlib
import json
import time

from .assignment import (assign_worker, flags_snapshot, registry_ceilings,
                         reserve_budget, validate_role_fields_v2)
from .contracts import validate_completion_packet, validate_task_contract
from .core import PolicyError, digest, encode, uid
from .staffing import decide
from .team import Team

MIGRATION_VERSION = 18
MIGRATION_NAME = 'v16-workforce-task-link'

# Conservative v0 contract budget defaults (overridable); real mission budget envelopes
# arrive with the budget-class calibration (doc 10 §5).
D1_BUDGET_DEFAULTS = {'tokens_max': 120000, 'cost_max': 2.0, 'wallclock_max': 3600,
                      'attempts_max': 1}

DEFAULT_ROLE = 'builder'


def _table_columns(db, table):
    return {row['name'] for row in db.execute('PRAGMA table_info(%s)' % table)}


def ensure_schema(store):
    """Migration 18: link task contracts to milestones (additive; idempotent).

    Pure schema addition (ALTER ADD COLUMN + index): there is no data backfill, so the
    repository's pre-mutation backup convention is deliberately not invoked (F7 note).
    """
    with contextlib.closing(store.connect()) as db:
        db.execute('CREATE TABLE IF NOT EXISTS schema_migrations('
                   'version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL,'
                   ' note TEXT)')
        if 'milestone_id' not in _table_columns(db, 'task_contracts'):
            db.execute('ALTER TABLE task_contracts ADD COLUMN milestone_id TEXT')
        db.execute('CREATE INDEX IF NOT EXISTS task_contracts_by_milestone'
                   ' ON task_contracts(milestone_id)')
        if not db.execute('SELECT 1 FROM schema_migrations WHERE version=?',
                          (MIGRATION_VERSION,)).fetchone():
            db.execute('INSERT INTO schema_migrations(version,name,applied,note) VALUES(?,?,?,?)',
                       (MIGRATION_VERSION, MIGRATION_NAME, time.time(),
                        'task_contracts.milestone_id (doc 14 keyed-to-milestone)'))
    return True


def _criteria_for(milestone):
    """Acceptance criteria derived from the milestone's engine checks (+ the artifact)."""
    criteria = []
    for index, check in enumerate(milestone.get('checks', []), start=1):
        criteria.append({'id': 'c%d' % index,
                         'criterion': 'milestone check %d (%s) passes on the delivered artifact'
                                      % (index, check.get('kind')),
                         'verification_method': 'builtin_check',
                         'evidence_required': ['check_result']})
    criteria.append({'id': 'artifact',
                     'criterion': 'the delivered artifact is captured and digest-stable',
                     'verification_method': 'repository_evidence',
                     'evidence_required': ['artifact_digest']})
    return criteria


def _authority_for(role_fields, scope):
    """The contract authority implied by the role ceiling (narrow-only; doc 03 §7)."""
    klass = role_fields['authority_max']
    if klass == 'external-effect':
        raise PolicyError('D1 does not carry external-effect roles')
    if klass in ('workspace-write', 'leased-write'):
        return {'class': klass, 'write_scope': list(scope), 'external_effects': 'none'}
    return {'class': klass, 'write_scope': [], 'external_effects': 'none'}


def _build_contract(job, milestone, request, *, role, task_id, staffing_id, staffing_result,
                    role_fields, budget, now):
    scope = request.get('scope') or [milestone.get('filename')]
    if isinstance(scope, str):
        scope = [scope]
    excludes = request.get('excludes') or ['everything outside the milestone deliverable']
    if isinstance(excludes, str):
        excludes = [excludes]
    objective = (request.get('objective') or milestone.get('objective') or '')[:500]
    contract = {
        'schema_version': 1,
        'mission_id': job['id'],
        'task_id': task_id,
        'parent_task': None,
        'dedup_fingerprint': 'sha256:' + digest({
            'objective': objective, 'scope': list(scope), 'milestone': milestone.get('id')}),
        'objective': objective,
        'why': request.get('why') or ('Milestone %s of job %s requires a bounded specialist.'
                                      % (milestone.get('id'), job['id'])),
        'scope': {'includes': list(scope), 'excludes': list(excludes)},
        'inputs': {'artifacts': list(request.get('input_artifacts') or []),
                   'context_refs': list(request.get('context_refs') or [])},
        'interfaces': list(request.get('interfaces') or []),
        'role': role,
        'skill_packs': [],
        'tier': staffing_result['tier'],
        'staffing_ref': staffing_id,
        'authority': _authority_for(role_fields, scope),
        'allowed_tools': list(role_fields['tool_policy'].get('allow') or []),
        'write_boundaries': list(scope),
        'dependencies': {'tasks': [], 'artifacts': []},
        'acceptance_criteria': _criteria_for(milestone),
        'evidence_requirements': {'fresh_within': int(request.get('fresh_within') or 24 * 60),
                                  'command_bound': True, 'content_bound': True},
        'required_reviewer': {'lenses': [], 'independence': 'any_but_executor', 'oracle': False},
        'budget': dict(budget or D1_BUDGET_DEFAULTS),
        'deadline': None,
        'stop_conditions': ['budget_exhausted', 'blocker_unresolvable',
                            'approval_required_action_reached'],
        'escalation_policy': [{'on_blocker': 'commander'}, {'on_scope_guess': 'do_not_proceed'}],
        'created_by': 'kel',
        'created_at': time.time() if now is None else now,
        'claimed_by': None,
        'claimed_at': None,
        'state': 'approved',
    }
    return contract


def _issue_contract(store, contract, milestone_id):
    """Write the frozen contract row (append-only; task_contracts triggers enforce it)."""
    contract_id = 'ctr_' + uid()
    with contextlib.closing(store.connect()) as db:
        db.execute('INSERT INTO task_contracts(contract_id,task_id,version,mission_id,'
                   'parent_task,digest,data,created,milestone_id) VALUES(?,?,?,?,?,?,?,?,?)',
                   (contract_id, contract['task_id'], 1, contract['mission_id'],
                    contract['parent_task'], digest(contract), encode(contract),
                    contract['created_at'], milestone_id))
    return contract_id


def delegate(store, job_id, milestone_id, request=None, *, role=None, mode='AUTO',
             preferred=None, fixed=None, features=None, mission_flags=(), tier_max=None,
             budget_class=None, budget=None, budget_estimate=None, project_id='',
             candidates=None, runtimes=None, enabled=None, now=None):
    """Decide staffing and issue the D1 contract (no worker runs here).

    With `workforce.enabled` off this performs no writes at all and returns
    `{'delegated': False, ...}` (B-config parity by construction). D0 missions return
    not-delegated; D2+ tiers are refused explicitly (pods arrive with 5.3).
    """
    request = dict(request or {})
    if enabled is None:
        enabled = flags_snapshot()['workforce.enabled']
    if not enabled:
        return {'delegated': False, 'reason': 'workforce.enabled is off',
                'flags': flags_snapshot()}
    try:
        job = store.get(job_id)
    except KeyError:
        raise PolicyError('Unknown job: %s' % job_id)
    spec = next((item for item in job.get('contract', {}).get('milestones', [])
                 if item.get('id') == milestone_id), None)
    if spec is None or milestone_id not in (job.get('milestones') or {}):
        raise PolicyError('Unknown milestone %s for job %s' % (milestone_id, job_id))
    if features is None:
        raise PolicyError('Staffing features are required (doc 05 feature vector)')
    decision = decide(features, flags=tuple(mission_flags), tier_max=tier_max,
                      budget_class=budget_class)
    if decision['tier'] == 'D0':
        return {'delegated': False, 'reason': 'no specialist warranted (D0)',
                'staffing': decision}
    if decision['tier'] != 'D1':
        raise PolicyError('Staffing chose %s; the D1 path supports exactly one specialist '
                          '(small pods arrive with 5.3)' % decision['tier'])
    role_id = role or DEFAULT_ROLE
    task_id = 'tsk_' + uid()
    staffing_id = 'stf_' + uid()
    team = Team(store)
    role_fields = team.resolve_role(role_id, project_id, task_id)['fields']
    validate_role_fields_v2(role_fields)
    contract = _build_contract(job, spec, request, role=role_id, task_id=task_id,
                               staffing_id=staffing_id, staffing_result=decision,
                               role_fields=role_fields, budget=budget, now=now)
    validate_task_contract(contract,
                           ceilings=registry_ceilings(store, project_id, task_id) or None)
    contract_id = _issue_contract(store, contract, milestone_id)
    reservation_row = None
    if budget_estimate:
        missing = [key for key in ('tokens', 'wallclock', 'cost') if key not in budget_estimate]
        if missing:
            raise PolicyError('budget_estimate needs %s' % ', '.join(missing))
        reservation_row = reserve_budget(store, job_id, budget_class=decision['budget_class'],
                                         tokens=budget_estimate['tokens'],
                                         wallclock=budget_estimate['wallclock'],
                                         cost=budget_estimate['cost'],
                                         milestone_id=milestone_id, now=now)
    try:
        assigned = assign_worker(store, job_id, milestone_id, role_id, mode=mode,
                                 preferred=preferred, fixed=fixed, project_id=project_id,
                                 task_id=task_id, candidates=candidates, runtimes=runtimes,
                                 reservation=reservation_row['reservation_id'] if reservation_row
                                 else None)
    except PolicyError as exc:
        # F3 (audit 12): the contract is append-only, so a failed assignment cannot be rolled
        # back; name the orphan explicitly and leave it queryable via the task ledger.
        raise PolicyError('Contract %s was issued, but no worker could be assigned (%s); the '
                          'contract remains as an audit record' % (contract_id, exc))
    team.record_activity(assigned['assignment_id'], 'staffing.decided',
                         {'staffing_id': staffing_id, 'tier': decision['tier'],
                          'score': decision['score'],
                          'rules': [item['id'] for item in decision['rules_fired']],
                          'reasons': decision['reasons'],
                          'budget_class': decision['budget_class']})
    team.record_activity(assigned['assignment_id'], 'contract.issued',
                         {'contract_id': contract_id, 'task_id': task_id,
                          'milestone_id': milestone_id, 'digest': digest(contract)})
    return {'delegated': True, 'task_id': task_id, 'contract_id': contract_id,
            'assignment_id': assigned['assignment_id'], 'staffing_id': staffing_id,
            'staffing': decision, 'binding': assigned['binding'],
            'grants': assigned['grants'], 'reservation': reservation_row,
            'job_id': job_id, 'milestone_id': milestone_id, 'contract': contract}


def _contract_row(store, task_id):
    with contextlib.closing(store.connect()) as db:
        row = db.execute('SELECT * FROM task_contracts WHERE task_id=? ORDER BY version DESC'
                         ' LIMIT 1', (task_id,)).fetchone()
    if row is None:
        raise PolicyError('Unknown task contract: %s' % task_id)
    return row


def _assignment_for_task(store, task_id):
    """The assignment that issued this task's contract (joined via the issued event)."""
    with contextlib.closing(store.connect()) as db:
        row = db.execute("SELECT assignment_id FROM team_events WHERE kind='contract.issued'"
                         " AND json_extract(detail, '$.task_id')=?"
                         " ORDER BY at DESC LIMIT 1", (task_id,)).fetchone()
        if row is None:
            raise PolicyError('No assignment recorded for task %s' % task_id)
        assignment = db.execute('SELECT * FROM team_assignments WHERE assignment_id=?',
                                (row['assignment_id'],)).fetchone()
    if assignment is None:
        raise PolicyError('Assignment row missing for task %s' % task_id)
    return assignment


def _already_closed(store, assignment_id):
    with contextlib.closing(store.connect()) as db:
        row = db.execute("SELECT 1 FROM team_events WHERE kind='task.closed'"
                         " AND assignment_id=? LIMIT 1", (assignment_id,)).fetchone()
    return row is not None


def _evidence_violations(store, contract, packet, *, assignment_id=None, now=None):
    """Every stale, unbound or foreign evidence reference behind the packet's claims."""
    requirements = contract.get('evidence_requirements', {})
    contract_window = requirements.get('fresh_within', 24 * 60)
    stamp = time.time() if now is None else now
    delivered = {item.get('digest') for item in packet.get('artifacts', [])}
    violations = []
    with contextlib.closing(store.connect()) as db:
        for claim in packet.get('completion_claims', []):
            for ref in claim.get('evidence_refs', []):
                row = db.execute('SELECT * FROM evidence_records WHERE id=?',
                                 (ref,)).fetchone()
                if row is None:
                    violations.append('claim %s: evidence %s is not in the ledger'
                                      % (claim.get('claim_id'), ref))
                    continue
                record = dict(row)
                window = min(contract_window, record.get('freshness_window') or contract_window)
                age = (stamp - float(record.get('ran_at') or 0)) / 60.0
                if age > window:
                    violations.append('claim %s: evidence %s is stale (%.0f min old, window '
                                      '%d min)' % (claim.get('claim_id'), ref, age, window))
                if assignment_id is not None and record.get('produced_by') != assignment_id:
                    violations.append('claim %s: evidence %s was produced by %r, not the '
                                      'assigned worker' % (claim.get('claim_id'), ref,
                                                           record.get('produced_by')))
                if requirements.get('content_bound'):
                    artifact_digest = record.get('artifact_digest')
                    if not artifact_digest:
                        violations.append('claim %s: evidence %s has no artifact digest for a '
                                          'content-bound contract'
                                          % (claim.get('claim_id'), ref))
                    elif artifact_digest not in delivered:
                        violations.append('claim %s: evidence %s is not bound to a delivered '
                                          'artifact' % (claim.get('claim_id'), ref))
                if requirements.get('command_bound') and not record.get('command'):
                    violations.append('claim %s: evidence %s has no command for a '
                                      'command-bound contract' % (claim.get('claim_id'), ref))
    return violations


def close_d1(store, task_id, packet, *, now=None):
    """Evidence-bound close: a clean close is impossible on any stale or unbound evidence."""
    contract_row = _contract_row(store, task_id)
    contract = json.loads(contract_row['data'])
    validate_completion_packet(packet)
    if packet.get('task_id') != task_id:
        raise PolicyError('Packet task_id %r does not match the task being closed (%s)'
                          % (packet.get('task_id'), task_id))
    assignment = _assignment_for_task(store, task_id)
    if _already_closed(store, assignment['assignment_id']):
        raise PolicyError('Task %s is already closed' % task_id)
    violations = _evidence_violations(store, contract, packet,
                                      assignment_id=assignment['assignment_id'], now=now)
    outcome = packet['outcome']
    if outcome == 'completed':
        verified = {claim['claim_id'] for claim in packet['completion_claims']
                    if claim.get('status') == 'verified'}
        missing = sorted({item['id'] for item in contract['acceptance_criteria']} - verified)
        if missing:
            violations = violations + ['acceptance criteria without verified claims: %s'
                                       % ', '.join(missing)]
    if outcome == 'completed' and violations:
        raise PolicyError('Evidence-bound close refused: %s' % '; '.join(violations[:5]))
    team = Team(store)
    team.record_activity(assignment['assignment_id'], 'task.closed',
                         {'task_id': task_id, 'outcome': outcome,
                          'violations': violations,
                          'claims': len(packet['completion_claims']),
                          'contract_id': contract_row['contract_id']})
    state = {'completed': 'DONE', 'failed': 'FAILED'}.get(outcome, 'UNCERTAIN')
    team.set_state(assignment['assignment_id'], state)
    return {'closed': True, 'task_id': task_id, 'outcome': outcome,
            'violations': violations, 'assignment_state': state,
            'contract_id': contract_row['contract_id']}


def _safe_error_text(exc):
    """Worker-failure text for durable records: truncated and scanned (F6, audit 12)."""
    detail = str(exc)[:160]
    # Function-scope import: kel.workforce imports kel.team at load time.
    from .workforce import find_unsafe
    if find_unsafe(detail, path='worker error'):
        return '(message withheld by the no-secret screen)'
    return detail


def run_d1(store, job_id, milestone_id, request, worker, *, worker_tools=(), enabled=None,
           candidates=None, features=None, flags=(), role=None, mode='AUTO',
           budget_estimate=None, budget_class=None, project_id='', now=None):
    """Prepare, run exactly one worker, and close with evidence-bound checks.

    `worker` receives the delegation record and must return a CompletionPacket. When it
    declares tools (`worker_tools`), every tool must be inside the frozen grant set or the
    worker is refused before it runs (S6, audit 11). Worker errors close the task as failed
    with a recorded reason; evidence-refused closes propagate so the caller can correct the
    packet (the assignment stays open until a valid close).
    """
    prepared = delegate(store, job_id, milestone_id, request, role=role, mode=mode,
                        features=features, mission_flags=flags,
                        budget_estimate=budget_estimate, budget_class=budget_class,
                        project_id=project_id, candidates=candidates, enabled=enabled, now=now)
    if not prepared.get('delegated'):
        return prepared
    grants = set(prepared['grants']['allowed'])
    outside = sorted(set(worker_tools) - grants)
    if outside:
        raise PolicyError('Worker tools outside the frozen grants: %s' % ', '.join(outside))
    team = Team(store)
    assignment_id = prepared['assignment_id']
    team.set_state(assignment_id, 'ACTIVE')
    try:
        packet = worker(prepared)
    except PolicyError as exc:
        message = _safe_error_text(exc)
        team.record_activity(assignment_id, 'task.closed',
                             {'task_id': prepared['task_id'], 'outcome': 'failed',
                              'violations': ['worker refused: %s' % message]})
        team.set_state(assignment_id, 'FAILED')
        return {'delegated': True, 'closed': True, 'outcome': 'failed',
                'error': message, 'task_id': prepared['task_id'],
                'assignment_id': assignment_id}
    except Exception as exc:  # worker failures close the task honestly
        team.record_activity(assignment_id, 'task.closed',
                             {'task_id': prepared['task_id'], 'outcome': 'failed',
                              'violations': ['worker error: %s' % type(exc).__name__]})
        team.set_state(assignment_id, 'FAILED')
        return {'delegated': True, 'closed': True, 'outcome': 'failed',
                'error': type(exc).__name__, 'task_id': prepared['task_id'],
                'assignment_id': assignment_id}
    closed = close_d1(store, prepared['task_id'], packet, now=now)
    return {'delegated': True, 'closed': True, 'packet_outcome': closed['outcome'],
            'violations': closed['violations'],
            'assignment_state': closed['assignment_state'],
            'task_id': prepared['task_id'], 'assignment_id': assignment_id,
            'contract_id': prepared['contract_id']}


# ---- read-only ledger projections (doc 14 §2: query projections, no new persistence) ------

def task_ledger(store, *, job_id=None):
    """Read-only Task Ledger: contracts joined to assignments and close records."""
    clause = ' WHERE mission_id=?' if job_id else ''
    args = (job_id,) if job_id else ()
    with contextlib.closing(store.connect()) as db:
        contracts = [dict(row) for row in db.execute(
            'SELECT * FROM task_contracts%s ORDER BY created' % clause, args)]
        rows = []
        for item in contracts:
            data = json.loads(item['data'])
            issued = db.execute(
                "SELECT assignment_id FROM team_events WHERE kind='contract.issued'"
                " AND json_extract(detail, '$.task_id')=? ORDER BY at DESC LIMIT 1",
                (item['task_id'],)).fetchone()
            assignment = None
            closed = None
            if issued:
                arow = db.execute('SELECT assignment_id, state, provider, model, template_id'
                                  ' FROM team_assignments WHERE assignment_id=?',
                                  (issued['assignment_id'],)).fetchone()
                if arow:
                    assignment = dict(arow)
                crow = db.execute("SELECT detail, at FROM team_events WHERE kind='task.closed'"
                                  " AND assignment_id=? ORDER BY at DESC LIMIT 1",
                                  (issued['assignment_id'],)).fetchone()
                if crow:
                    closed = json.loads(crow['detail'])
                    closed['at'] = crow['at']
            rows.append({'task_id': item['task_id'], 'contract_id': item['contract_id'],
                         'version': item['version'], 'milestone_id': item['milestone_id'],
                         'tier': data.get('tier'), 'role': data.get('role'),
                         'assignment': assignment, 'closed': closed,
                         'created': item['created']})
        return rows


def progress_ledger(store, *, job_id):
    """Read-only Progress Ledger for one job (milestones + tasks + evidence + assignments)."""
    try:
        job = store.get(job_id)
    except KeyError:
        raise PolicyError('Unknown job: %s' % job_id)
    spec_by_id = {item.get('id'): item
                  for item in job.get('contract', {}).get('milestones', [])}
    milestones = []
    for milestone_id, state in sorted((job.get('milestones') or {}).items()):
        spec = spec_by_id.get(milestone_id, {})
        milestones.append({'id': milestone_id, 'objective': spec.get('objective'),
                           'state': state.get('state'), 'attempts': state.get('attempts'),
                           'filename': spec.get('filename')})
    tasks = task_ledger(store, job_id=job_id)
    with contextlib.closing(store.connect()) as db:
        evidence = [dict(row) for row in db.execute(
            'SELECT id, task_id, evidence_class, label, ran_at FROM evidence_records'
            ' WHERE mission_id=? ORDER BY ran_at', (job_id,))]
        assignments = [dict(row) for row in db.execute(
            'SELECT assignment_id, milestone_id, template_id, state, provider, model'
            ' FROM team_assignments WHERE job_id=? ORDER BY created', (job_id,))]
    closed = [item['closed'] for item in tasks if item.get('closed')]
    return {'job_id': job_id, 'state': job.get('state'), 'milestones': milestones,
            'tasks': tasks, 'evidence': evidence, 'assignments': assignments,
            'closed': {'count': len(closed),
                       'outcomes': sorted({item.get('outcome') for item in closed})}}
