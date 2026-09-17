"""D2 small pods (Phase 5.3): hands-off Builder→Verifier sequencing with findings, messages,
arbitration v1 and stall detection.

Design: `ux-audit/workforce-os/` docs 05 (staffing), 07 (protocol), 08 (assurance), 13
(evaluation), 15 §5.3. One pod = one milestone: a Builder task and a dependent Verifier task,
each with its own frozen contract; the builder hands off with a recorded HANDOFF message; the
verifier runs the two Phase-5.3 lenses (functional-testing, maintainability), records findings
through the assurance pipeline, and returns a verdict; verdicts are cross-checked against open
serious findings (never a clean pass over open blockers/criticals). Findings close on the
arbitration ladder via `assurance.resolve_finding` (evidence beats assertions; blockers need
recorded evidence to close). Stall detection is a read-only probe over the event stream.

Boundaries: no parallelism and no oracle (5.4/5.5 non-goals); the workforce tool vocabulary has
no spawn tool and run_d2 creates exactly two assignments; with `workforce.enabled` off it
performs zero writes.
"""
import contextlib
import time

from .assurance import record_finding
from .assignment import (assign_worker, candidates_from_providers, flags_snapshot, reserve_budget,
                         validate_role_fields_v2)
from .commander import PROVIDER_FAMILIES
from .core import PolicyError, uid
from .delegation import close_d1, issue_task_contract
from .messages import messages, send_message
from .staffing import decide
from .team import Team

VERIFICATION_LENSES = ('functional-testing', 'maintainability')
INTERRUPTION_TYPES = ('BLOCKER', 'DECISION_PROPOSAL', 'REPLAN_REQUEST')
STALL_THRESHOLD_MINUTES = 30
VERDICTS = ('VERIFIED', 'FAILED', 'UNCERTAIN')


def family_of(provider):
    """Provider family for diversity checks (unknown providers count as their own family)."""
    return PROVIDER_FAMILIES.get(provider, provider)


def _diverse_order(candidates, builder_provider):
    """Order candidate names so a different-family Verifier is preferred when available."""
    builder_family = family_of(builder_provider)
    different = [item.name for item in candidates if family_of(item.name) != builder_family]
    same = [item.name for item in candidates if family_of(item.name) == builder_family]
    if different:
        return different + same, 'different'
    return same, 'unavailable'


def _safe_error(exc):
    """Worker-failure text for durable records: truncated and screened (matches delegation)."""
    detail = str(exc)[:160]
    from .workforce import find_unsafe
    if find_unsafe(detail, path='worker error'):
        return '(message withheld by the no-secret screen)'
    return detail


def check_stall(store, assignment_id, *, now=None, threshold_minutes=STALL_THRESHOLD_MINUTES):
    """Stall detection v1 (doc 07 §8): an ACTIVE task with no activity beyond the threshold."""
    with contextlib.closing(store.connect()) as db:
        row = db.execute('SELECT state FROM team_assignments WHERE assignment_id=?',
                         (assignment_id,)).fetchone()
        if row is None:
            raise PolicyError('Unknown assignment: %s' % assignment_id)
        state = row['state']
        last = db.execute('SELECT max(at) FROM team_events WHERE assignment_id=?',
                          (assignment_id,)).fetchone()[0]
    stamp = time.time() if now is None else now
    if state != 'ACTIVE':
        return {'stalled': False, 'reason': 'not active (%s)' % state, 'last_activity': last}
    if last is None:
        return {'stalled': True, 'reason': 'no recorded activity', 'last_activity': None}
    idle = (stamp - float(last)) / 60.0
    if idle > threshold_minutes:
        return {'stalled': True,
                'reason': 'no activity for %.0f minutes (threshold %d)'
                          % (idle, threshold_minutes),
                'last_activity': last, 'idle_minutes': round(idle, 1)}
    return {'stalled': False, 'reason': 'active (%.0f minutes idle)' % idle,
            'last_activity': last, 'idle_minutes': round(idle, 1)}


def interruptions(store, *, job_id=None, task_id=None):
    """User-interruption count on the message ledger (BLOCKER/DECISION_PROPOSAL/REPLAN to cmd)."""
    rows = messages(store, task_id=task_id, mission_id=job_id)
    counted = [row for row in rows
               if row['recipient'] == 'cmd' and row['type'] in INTERRUPTION_TYPES]
    return {'count': len(counted), 'messages': [row['id'] for row in counted]}


def run_d2(store, job_id, milestone_id, request, builder_worker, verifier_worker, *,
           builder_tools=(), verifier_tools=(), features=None, mission_flags=(), tier_max=None,
           budget_class=None, budget=None, budget_estimate=None, project_id='',
           candidates=None, enabled=None, now=None):
    """Run one D2 pod: builder → handoff → verifier, with evidence-bound closes throughout.

    `builder_worker(prepared)` returns a CompletionPacket; `verifier_worker(prepared)` returns
    `{'findings': [finding...], 'verdict': VERIFIED|FAILED|UNCERTAIN, 'packet': CompletionPacket}`.
    Worker tools are checked against the frozen grants before either worker runs.
    """
    request = dict(request or {})
    if enabled is None:
        enabled = flags_snapshot()['workforce.enabled']
    if not enabled:
        return {'delegated': False, 'reason': 'workforce.enabled is off', 'flags': flags_snapshot()}
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
    if decision['tier'] != 'D2':
        raise PolicyError('run_d2 needs a D2 staffing decision (got %s); D0/D1 use run_d1 and '
                          'D3+ arrives with 5.5' % decision['tier'])
    team = Team(store)
    staffing_id = 'stf_' + uid()
    builder_task = 'tsk_' + uid()
    verifier_task = 'tsk_' + uid()
    builder_fields = team.resolve_role('builder', project_id, builder_task)['fields']
    validate_role_fields_v2(builder_fields)
    verifier_fields = team.resolve_role('verifier', project_id, verifier_task)['fields']
    validate_role_fields_v2(verifier_fields)

    builder_contract, builder_cid = issue_task_contract(
        store, job, spec, request, role='builder', task_id=builder_task, staffing_id=staffing_id,
        staffing_result=decision, role_fields=builder_fields, budget=budget, now=now,
        project_id=project_id)
    verifier_criteria = [
        {'id': 'c1',
         'criterion': 'independent verification recorded for the delivered artifact '
                      '(lenses run, verdict stated)',
         'verification_method': 'repository_evidence', 'evidence_required': ['review_record']},
        {'id': 'artifact',
         'criterion': 'the verified artifact digest matches the delivered artifact',
         'verification_method': 'repository_evidence', 'evidence_required': ['artifact_digest']}]
    verifier_request = {
        'objective': 'Independently verify the artifact delivered for task %s' % builder_task,
        'why': 'D2 pods separate the builder from the verifier; review is artifact-first.',
        'scope': list(request.get('scope') or [spec.get('filename')]),
        'excludes': ['authoring or fixing the artifact (the verifier is read-only)'],
        'context_refs': [builder_task]}
    verifier_contract, verifier_cid = issue_task_contract(
        store, job, spec, verifier_request, role='verifier', task_id=verifier_task,
        staffing_id=staffing_id, staffing_result=decision, role_fields=verifier_fields,
        budget=budget, now=now, project_id=project_id, criteria=verifier_criteria,
        reviewer_lenses=list(VERIFICATION_LENSES), depends_on_tasks=[builder_task])

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

    cands = candidates if candidates is not None else candidates_from_providers(store)
    builder_assigned = assign_worker(store, job_id, milestone_id, 'builder',
                                     project_id=project_id, task_id=builder_task,
                                     candidates=cands,
                                     reservation=reservation_row['reservation_id']
                                     if reservation_row else None)
    verifier_order, diversity = _diverse_order(
        cands, builder_assigned['binding']['selected']['provider'])
    verifier_assigned = assign_worker(store, job_id, milestone_id, 'verifier', mode='PREFERRED',
                                      preferred=verifier_order, project_id=project_id,
                                      task_id=verifier_task, candidates=cands)
    builder_aid = builder_assigned['assignment_id']
    verifier_aid = verifier_assigned['assignment_id']
    if builder_aid == verifier_aid:  # structurally impossible; belt and suspenders
        raise PolicyError('Builder and Verifier assignments must differ')

    team.record_activity(builder_aid, 'staffing.decided',
                         {'staffing_id': staffing_id, 'tier': decision['tier'],
                          'score': decision['score'],
                          'rules': [item['id'] for item in decision['rules_fired']],
                          'reasons': decision['reasons'],
                          'budget_class': decision['budget_class'], 'pod': 'd2'})
    team.record_activity(verifier_aid, 'staffing.decided',
                         {'staffing_id': staffing_id, 'tier': decision['tier'],
                          'score': decision['score'],
                          'rules': [item['id'] for item in decision['rules_fired']],
                          'reasons': decision['reasons'],
                          'budget_class': decision['budget_class'], 'pod': 'd2',
                          'family_diversity': diversity})
    team.record_activity(builder_aid, 'contract.issued',
                         {'contract_id': builder_cid, 'task_id': builder_task,
                          'milestone_id': milestone_id})
    team.record_activity(verifier_aid, 'contract.issued',
                         {'contract_id': verifier_cid, 'task_id': verifier_task,
                          'milestone_id': milestone_id, 'depends_on': [builder_task]})

    pod = {'job_id': job_id, 'milestone_id': milestone_id, 'staffing_id': staffing_id,
           'task_ids': {'builder': builder_task, 'verifier': verifier_task},
           'assignment_ids': {'builder': builder_aid, 'verifier': verifier_aid},
           'contract_ids': {'builder': builder_cid, 'verifier': verifier_cid}}

    outside = sorted(set(builder_tools) - set(builder_assigned['grants']['allowed']))
    if outside:
        raise PolicyError('Builder tools outside the frozen grants: %s' % ', '.join(outside))
    outside = sorted(set(verifier_tools) - set(verifier_assigned['grants']['allowed']))
    if outside:
        raise PolicyError('Verifier tools outside the frozen grants: %s' % ', '.join(outside))

    team.set_state(builder_aid, 'ACTIVE')
    try:
        builder_packet = builder_worker({**pod, 'role': 'builder', 'task_id': builder_task,
                                         'assignment_id': builder_aid,
                                         'contract_id': builder_cid})
    except PolicyError as exc:
        detail = _safe_error(exc)
        team.record_activity(builder_aid, 'task.closed',
                             {'task_id': builder_task, 'outcome': 'failed',
                              'violations': ['worker refused: %s' % detail]})
        team.set_state(builder_aid, 'FAILED')
        return {'delegated': True, 'closed': True, 'verdict': 'FAILED', 'stage': 'builder',
                'error': detail, 'pod': pod, 'findings': [],
                'stalls': {'builder': {'stalled': False, 'reason': 'failed before close'},
                           'verifier': None},
                'interruptions': interruptions(store, job_id=job_id)['count'],
                'messages': [], 'family_diversity': diversity, 'reservation': reservation_row}
    except Exception as exc:  # worker failures close the task honestly (mirrors run_d1)
        team.record_activity(builder_aid, 'task.closed',
                             {'task_id': builder_task, 'outcome': 'failed',
                              'violations': ['worker error: %s' % type(exc).__name__]})
        team.set_state(builder_aid, 'FAILED')
        return {'delegated': True, 'closed': True, 'verdict': 'FAILED', 'stage': 'builder',
                'error': type(exc).__name__, 'pod': pod, 'findings': [],
                'stalls': {'builder': {'stalled': False, 'reason': 'failed before close'},
                           'verifier': None},
                'interruptions': interruptions(store, job_id=job_id)['count'],
                'messages': [], 'family_diversity': diversity, 'reservation': reservation_row}
    builder_stall = check_stall(store, builder_aid, now=now)
    builder_closed = close_d1(store, builder_task, builder_packet, now=now)

    handoff = send_message(store, {
        'schema_version': 1, 'mission_id': job_id, 'task_id': verifier_task,
        'from': builder_aid, 'to': verifier_aid, 'type': 'HANDOFF',
        'summary': 'Artifact delivered for task %s; independent verification requested.'
                   % builder_task,
        'refs': [builder_task, builder_cid]
                + [item.get('id') for item in builder_packet.get('artifacts', [])
                   if item.get('id')],
        'required_action': 'Verify the delivered artifact against the contract criteria.'},
        now=now)

    team.set_state(verifier_aid, 'ACTIVE')
    try:
        verification = verifier_worker({**pod, 'role': 'verifier', 'task_id': verifier_task,
                                        'assignment_id': verifier_aid,
                                        'contract_id': verifier_cid,
                                        'builder': {'task_id': builder_task,
                                                    'assignment_id': builder_aid,
                                                    'contract_id': builder_cid,
                                                    'packet': builder_packet}})
    except PolicyError as exc:
        detail = _safe_error(exc)
        team.record_activity(verifier_aid, 'task.closed',
                             {'task_id': verifier_task, 'outcome': 'failed',
                              'violations': ['worker refused: %s' % detail]})
        team.set_state(verifier_aid, 'FAILED')
        return {'delegated': True, 'closed': True, 'verdict': 'UNCERTAIN', 'stage': 'verifier',
                'error': detail, 'pod': pod, 'findings': [],
                'stalls': {'builder': builder_stall, 'verifier': None},
                'interruptions': interruptions(store, job_id=job_id)['count'],
                'messages': [handoff['id']], 'family_diversity': diversity,
                'reservation': reservation_row}
    except Exception as exc:  # worker failures close the task honestly (mirrors run_d1)
        team.record_activity(verifier_aid, 'task.closed',
                             {'task_id': verifier_task, 'outcome': 'failed',
                              'violations': ['worker error: %s' % type(exc).__name__]})
        team.set_state(verifier_aid, 'FAILED')
        return {'delegated': True, 'closed': True, 'verdict': 'UNCERTAIN', 'stage': 'verifier',
                'error': type(exc).__name__, 'pod': pod, 'findings': [],
                'stalls': {'builder': builder_stall, 'verifier': None},
                'interruptions': interruptions(store, job_id=job_id)['count'],
                'messages': [handoff['id']], 'family_diversity': diversity,
                'reservation': reservation_row}

    findings_records = [record_finding(store, item, now=now)
                        for item in verification.get('findings', [])]
    verdict = verification.get('verdict')
    if verdict not in VERDICTS:
        raise PolicyError('Verification verdicts are %s' % ', '.join(VERDICTS))
    open_serious = [item for item in findings_records
                    if item['severity'] in ('blocker', 'critical') and item['status'] == 'open']
    if verdict == 'VERIFIED' and open_serious:
        raise PolicyError('Verdict contradicts findings: %d open blocker/critical finding(s)'
                          % len(open_serious))
    verifier_stall = check_stall(store, verifier_aid, now=now)
    verifier_packet = verification.get('packet')
    if verifier_packet is None:
        raise PolicyError('Verification must include a completion packet')
    verifier_closed = close_d1(store, verifier_task, verifier_packet, now=now)

    final_handoff = send_message(store, {
        'schema_version': 1, 'mission_id': job_id, 'task_id': verifier_task,
        'from': verifier_aid, 'to': 'cmd', 'type': 'HANDOFF',
        'summary': 'Verification of task %s finished with verdict %s (%d findings).'
                   % (builder_task, verdict, len(findings_records)),
        'refs': [verifier_task, verifier_cid] + [item['id'] for item in findings_records],
        'required_action': 'Accept the verified artifact or commission rework per the verdict.'},
        now=now)
    interrupts = interruptions(store, job_id=job_id)
    return {'delegated': True, 'closed': True, 'verdict': verdict, 'pod': pod,
            'builder': {'packet_outcome': builder_closed['outcome'],
                        'assignment_state': builder_closed['assignment_state'],
                        'stall': builder_stall},
            'verifier': {'packet_outcome': verifier_closed['outcome'],
                         'assignment_state': verifier_closed['assignment_state'],
                         'stall': verifier_stall},
            'findings': findings_records, 'family_diversity': diversity,
            'messages': [handoff['id'], final_handoff['id']],
            'interruptions': interrupts['count'], 'reservation': reservation_row}
