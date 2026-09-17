"""Evaluation-harness pilot (Phase 5.3 entry gate): configs A vs C on classes 2/6/8.

Design: `ux-audit/workforce-os/13_EVALUATION_PLAN.md`. The pilot shakes out the harness and
produces the 5.3 exit evidence ("escaped defects strictly below A on classes 2, 6, 8;
interruptions <= budget"). Specialists here are deterministic fixtures: the measurements
exercise the pipeline's accounting (a detected defect becomes a recorded finding and holds
the task; an undetected seeded defect is counted as escaped) rather than model detection
quality — the real-model campaign rides the full matrix later. Configs: A = single
specialist with no verification (`run_d1`, tier pinned to D1); C = D2 pod (`run_d2`).
"""
import tempfile
import time
from pathlib import Path

from kel.assignment import ensure_archetypes
from kel.assignment import ensure_schema as ensure_assignment_schema
from kel.context import Context
from kel.core import Store
from kel.delegation import ensure_schema as ensure_delegation_schema
from kel.delegation import run_d1
from kel.evidence import write_evidence
from kel.pods import VERIFICATION_LENSES, run_d2
from kel.router import Candidate
from kel.workforce import ensure_schema as ensure_workforce_schema

INTERRUPTION_BUDGET = 1  # one planning gate per mission; clean fixture runs stay inside

PILOT_CLASSES = {
    '2': {
        'name': 'medium feature',
        'filename': 'class2_feature.md',
        'features': {'complexity': 2, 'decomposability': 1, 'sequentiality': 1,
                     'uncertainty': 1, 'novelty': 1, 'risk': 0, 'domain_breadth': 0,
                     'tool_requirements': 1, 'consequence_of_failure': 0, 'user_facing': 0,
                     'release_proximity': 0, 'budget_class': 'standard'},
        'seeds': [
            {'id': 's2-ambiguity', 'lens': 'functional-testing', 'severity': 'blocker',
             'summary': 'The delivered feature does not honor the stated acceptance requirement.'},
            {'id': 's2-perf-trap', 'lens': 'performance', 'severity': 'critical',
             'summary': 'The implementation reads the full dataset per row (performance trap).'}],
    },
    '6': {
        'name': 'migration',
        'filename': 'class6_migration.md',
        'features': {'complexity': 2, 'decomposability': 2, 'sequentiality': 0,
                     'uncertainty': 1, 'novelty': 0, 'risk': 1, 'domain_breadth': 0,
                     'tool_requirements': 1, 'consequence_of_failure': 0, 'user_facing': 0,
                     'release_proximity': 0, 'budget_class': 'standard'},
        'seeds': [
            {'id': 's6-idempotency', 'lens': 'functional-testing', 'severity': 'blocker',
             'summary': 'The migration is not idempotent on a second run.'},
            {'id': 's6-rollback-trap', 'lens': 'release-integrity', 'severity': 'blocker',
             'summary': 'The rollback path drops rows the forward path kept.'}],
    },
    '8': {
        'name': 'debugging',
        'filename': 'class8_debug.md',
        'features': {'complexity': 2, 'decomposability': 1, 'sequentiality': 1,
                     'uncertainty': 2, 'novelty': 2, 'risk': 0, 'domain_breadth': 0,
                     'tool_requirements': 1, 'consequence_of_failure': 0, 'user_facing': 0,
                     'release_proximity': 0, 'budget_class': 'standard'},
        'seeds': [
            {'id': 's8-root-cause', 'lens': 'functional-testing', 'severity': 'blocker',
             'summary': 'The root cause two layers below the reported symptom remains.'}],
    },
}


def _fixture_candidates():
    """Deterministic, registry-known candidates (two families) for pilot runs."""
    return [
        Candidate(name='claude-code', capabilities={'text', 'tools', 'edit', 'shell'},
                  installed=True, authenticated=True, cost=5.0),
        Candidate(name='codex', capabilities={'text', 'tools', 'edit', 'shell'},
                  installed=True, authenticated=True, cost=1.0),
        Candidate(name='internal', capabilities={'text', 'vision', 'tools'},
                  installed=True, authenticated=True, cost=3.0),
        Candidate(name='deepseek', capabilities={'text', 'tools'},
                  installed=True, authenticated=True, cost=2.0),
    ]


def _evidence_item(record, artifact_digest, stamp, assignment_id):
    return {'id': record['id'], 'class': record['evidence_class'],
            'command': record['command'], 'exit_code': record['exit_code'],
            'output_digest': record['output_digest'], 'artifact_digest': artifact_digest,
            'ran_at': stamp, 'freshness_ok': True, 'produced_by': assignment_id}


def _claims(evidence_id, claim_ids, status='verified'):
    return [{'claim_id': claim_id, 'status': status, 'evidence_refs': [evidence_id]}
            for claim_id in claim_ids]


def _packet(**overrides):
    body = {
        'schema_version': 1,
        'task_id': 'tsk_unset',
        'outcome': 'completed',
        'summary': 'Deterministic pilot packet.',
        'artifacts': [],
        'commits_files': {'commits': [], 'files': []},
        'evidence': [],
        'tests': [],
        'assumptions': [],
        'decisions': [],
        'findings': [],
        'unresolved_uncertainty': [],
        'risks': [],
        'blockers': [],
        'follow_ups': [],
        'confidence': 7,
        'required_reviewer': {'lenses': [], 'independence': 'any_but_executor',
                              'oracle': False},
        'reviewer_requirements_met': {'lenses_run': [], 'coverage_complete': True,
                                      'oracle': {'ran': False}},
        'completion_claims': [],
        'budget_spent': {'tokens': 1000, 'cost': 0.05, 'wallclock': 60, 'attempts': 1},
        'lineage': {'inputs_consumed': [], 'artifacts_produced': [], 'parent_packet': None},
        'resume_hints': None,
        'attestation': {'provider': 'fixture', 'model': 'fixture-specialist',
                        'runtime': 'internal', 'prompt_hash': 'sha256:fixture',
                        'tool_grants_snapshot': []},
    }
    body.update(overrides)
    return body


def _make_builder(store, class_id, seeds):
    """Deterministic specialist: delivers the class artifact with all seeded defects in it."""

    def worker(prepared):
        stamp = time.time()
        artifact_digest = 'sha256:' + ('%s' % class_id) * 12
        record = write_evidence(store, mission_id=prepared['job_id'],
                                task_id=prepared['task_id'], evidence_class='check_result',
                                label='milestone checks green',
                                command='kel check %s' % prepared['milestone_id'],
                                exit_code=0, output='ok', artifact_digest=artifact_digest,
                                ran_at=stamp, produced_by=prepared['assignment_id'])
        return _packet(task_id=prepared['task_id'],
                       artifacts=[{'id': 'art_%s' % class_id, 'digest': artifact_digest,
                                   'kind': 'document'}],
                       evidence=[_evidence_item(record, artifact_digest, stamp,
                                                prepared['assignment_id'])],
                       completion_claims=_claims(record['id'], ['c1', 'artifact']))
    return worker


def _make_verifier(store, class_id, seeds):
    """Deterministic verifier: detects the seeds its two lenses cover, records findings."""

    def worker(prepared):
        stamp = time.time()
        builder = prepared['builder']
        artifact_digest = builder['packet']['artifacts'][0]['digest']
        artifact_id = builder['packet']['artifacts'][0]['id']
        detected = [seed for seed in seeds if seed['lens'] in VERIFICATION_LENSES]
        findings = [{'schema_version': 1, 'mission_id': prepared['job_id'],
                     'task_id': prepared['task_id'], 'lens': seed['lens'],
                     'severity': seed['severity'], 'confidence': 8, 'artifact': artifact_id,
                     'location': seed['id'], 'summary': seed['summary'],
                     'evidence': 'fixture reproduction for %s' % seed['id'],
                     'fingerprint': '%s:%s:seed' % (builder['task_id'], seed['id']),
                     'status': 'open',
                     'by': {'lens': seed['lens'], 'model_family': 'fixture',
                            'assignment': prepared['assignment_id']}}
                    for seed in detected]
        serious = any(seed['severity'] in ('blocker', 'critical') for seed in detected)
        verdict = 'FAILED' if serious else 'VERIFIED'
        record = write_evidence(store, mission_id=prepared['job_id'],
                                task_id=prepared['task_id'], evidence_class='review_record',
                                label='lenses: %s' % ', '.join(VERIFICATION_LENSES),
                                command='kel verify %s' % prepared['task_id'],
                                produced_by=prepared['assignment_id'],
                                output='verdict %s' % verdict,
                                artifact_digest=artifact_digest, ran_at=stamp)
        completed = verdict == 'VERIFIED'
        return {'findings': findings, 'verdict': verdict,
                'packet': _packet(task_id=prepared['task_id'],
                                  outcome='completed' if completed else 'failed',
                                  summary='Independent verification verdict: %s.' % verdict,
                                  artifacts=[{'id': 'art_verified', 'digest': artifact_digest,
                                              'kind': 'document'}],
                                  evidence=[_evidence_item(record, artifact_digest, stamp,
                                                           prepared['assignment_id'])],
                                  completion_claims=_claims(record['id'], ['c1', 'artifact'],
                                                            status='verified'
                                                            if completed else 'failed'),
                                  unresolved_uncertainty=[]
                                  if completed else ['verification found unresolved defects'],
                                  required_reviewer={'lenses': list(VERIFICATION_LENSES),
                                                     'independence': 'any_but_executor',
                                                     'oracle': False},
                                  reviewer_requirements_met={
                                      'lenses_run': [{'lens': name,
                                                      'verdict': verdict.lower(),
                                                      'coverage_statement':
                                                          'fixture lens pass for class %s'
                                                          % class_id}
                                                     for name in VERIFICATION_LENSES],
                                      'coverage_complete': True,
                                      'oracle': {'ran': False}})}
    return worker


def _make_store(run_dir):
    store = Store(Path(run_dir) / 'data')
    ensure_workforce_schema(store)
    ensure_assignment_schema(store)
    ensure_delegation_schema(store)
    ensure_archetypes(store)
    return store


def _make_job(store, class_id, spec):
    ctx = Context(store)
    conversation = ctx.conversation('default', title='pilot class %s' % class_id)
    return store.create({'request': 'Pilot class %s: %s' % (class_id, spec['name']),
                         'milestones': [{'id': 'm1', 'objective': spec['name'],
                                         'filename': spec['filename'], 'depends_on': [],
                                         'checks': [{'kind': 'min_chars', 'value': 20}]}]},
                        conversation=conversation)


def _detected_seeds(store, job_id, seeds):
    from kel.assurance import findings as findings_reader
    seed_ids = {seed['id'] for seed in seeds}
    return sum(1 for row in findings_reader(store, mission_id=job_id)
               if row['location'] in seed_ids)


def _run_config(run_dir, class_id, config, stamp):
    store = _make_store(run_dir)
    spec = PILOT_CLASSES[class_id]
    job_id = _make_job(store, class_id, spec)
    builder = _make_builder(store, class_id, spec['seeds'])
    if config == 'A':
        result = run_d1(store, job_id, 'm1', {'objective': spec['name']}, builder,
                        enabled=True, features=dict(spec['features']), tier_max='D1',
                        candidates=_fixture_candidates(), now=stamp)
    else:
        verifier = _make_verifier(store, class_id, spec['seeds'])
        result = run_d2(store, job_id, 'm1', {'objective': spec['name']}, builder, verifier,
                        enabled=True, features=dict(spec['features']),
                        candidates=_fixture_candidates(), now=stamp)
    detected = _detected_seeds(store, job_id, spec['seeds'])
    return {'class': class_id, 'config': config, 'job_id': job_id,
            'seeded': len(spec['seeds']), 'detected': detected,
            'escaped': len(spec['seeds']) - detected,
            'verdict': result.get('verdict', result.get('packet_outcome', 'n/a')),
            'interruptions': result.get('interruptions', 0), 'result': result}


def run_pilot(*, classes=('2', '6', '8'), workdir=None, now=None):
    """Run the A/C pilot; returns per-run metrics and the per-class exit gates.

    Gates (doc 15 §5.3): escaped defects strictly below config A per class, and C's
    user-interruption count within budget. `workdir` may be supplied to keep the run
    databases (tests do); otherwise the harness cleans up after itself.
    """
    stamp = time.time() if now is None else now
    owned = None
    if workdir is None:
        owned = tempfile.TemporaryDirectory()
        workdir = owned.name
    try:
        runs = []
        for class_id in classes:
            for config in ('A', 'C'):
                run_dir = Path(workdir) / ('class%s-%s' % (class_id, config))
                run_dir.mkdir(parents=True, exist_ok=True)
                runs.append(_run_config(run_dir, class_id, config, stamp))
        per_class = {}
        gates_ok = True
        for class_id in classes:
            config_a = next(r for r in runs if r['class'] == class_id and r['config'] == 'A')
            config_c = next(r for r in runs if r['class'] == class_id and r['config'] == 'C')
            escaped_below = config_c['escaped'] < config_a['escaped']
            interruptions_ok = config_c['interruptions'] <= INTERRUPTION_BUDGET
            per_class[class_id] = {'escaped_A': config_a['escaped'],
                                   'escaped_C': config_c['escaped'],
                                   'escaped_below_A': escaped_below,
                                   'interruptions_C': config_c['interruptions'],
                                   'interruptions_ok': interruptions_ok}
            gates_ok = gates_ok and escaped_below and interruptions_ok
        return {'runs': runs, 'per_class': per_class, 'gates_ok': gates_ok}
    finally:
        if owned is not None:
            owned.cleanup()
