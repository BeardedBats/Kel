"""Shared workforce test fixtures (Phase 5.x): contracts, evidence items, completion packets,
routing candidates and a fixture job contract.

One definition per shape, imported by `test_workforce_schemas.py`,
`test_workforce_assignment.py` and `test_workforce_d1.py` (S3, audit increment 11).
"""
from kel.router import Candidate


def contract(**overrides):
    body = {
        'schema_version': 1,
        'mission_id': 'mis_' + 'a' * 12,
        'task_id': 'tsk_' + 'b' * 12,
        'parent_task': None,
        'dedup_fingerprint': 'sha256:implement-export-csv|src/api/export',
        'objective': 'Implement GET /api/export.csv with streaming, per plan ARCH-4.',
        'why': 'The mission plan asks for a CSV export endpoint.',
        'scope': {'includes': ['src/api/export.py', 'tests/test_export.py'],
                  'excludes': ['schema changes', 'UI']},
        'inputs': {'artifacts': [{'id': 'art_arch4', 'digest': 'sha256:ab12'}],
                   'context_refs': []},
        'interfaces': ['Response: text/csv; columns per ARCH-4 section 2'],
        'role': 'builder',
        'skill_packs': [{'name': 'python-fastapi', 'version': '2.1.0'}],
        'tier': 'D1',
        'staffing_ref': 'stf_' + 'c' * 12,
        'authority': {'class': 'leased-write',
                      'write_scope': ['src/api/export.py', 'tests/test_export.py'],
                      'external_effects': 'none'},
        'allowed_tools': ['read_context', 'write_files', 'run_tests'],
        'write_boundaries': ['src', 'tests'],
        'dependencies': {'tasks': [], 'artifacts': []},
        'acceptance_criteria': [
            {'id': 'c1', 'criterion': 'GET /api/export.csv returns 200 with text/csv',
             'verification_method': 'repository_evidence',
             'evidence_required': ['check_result', 'artifact_digest']},
            {'id': 'c2', 'criterion': 'pytest tests/test_export.py passes',
             'verification_method': 'builtin_check', 'evidence_required': ['check_result']}],
        'evidence_requirements': {'fresh_within': 1440, 'command_bound': True,
                                  'content_bound': True},
        'required_reviewer': {'lenses': ['functional-testing'],
                              'independence': 'any_but_executor', 'oracle': False},
        'budget': {'tokens_max': 120000, 'cost_max': 2.0, 'wallclock_max': 3600,
                   'attempts_max': 4},
        'deadline': None,
        'stop_conditions': ['budget_exhausted', 'blocker_unresolvable',
                            'approval_required_action_reached'],
        'escalation_policy': [{'on_blocker': 'commander'}, {'on_scope_guess': 'do_not_proceed'}],
        'created_by': 'commander', 'created_at': 1758123456.0,
        'claimed_by': None, 'claimed_at': None,
        'state': 'draft',
    }
    body.update(overrides)
    return body


EVIDENCE_ITEM = {
    'id': 'ev_101', 'class': 'test_run', 'command': 'python -m pytest tests/test_export.py -q',
    'exit_code': 0, 'output_digest': 'sha256:91aa', 'artifact_digest': 'sha256:77bb',
    'ran_at': 1758123456.0, 'freshness_ok': True, 'produced_by': 'run_8841'}


def packet(**overrides):
    body = {
        'schema_version': 1,
        'task_id': 'tsk_' + 'b' * 12,
        'outcome': 'completed',
        'summary': 'CSV export endpoint implemented and streaming; tests green.',
        'artifacts': [{'id': 'art_e51', 'digest': 'sha256:77bb', 'kind': 'code',
                       'path': 'src/api/export.py', 'bytes': 2048}],
        'commits_files': {'commits': ['4f2a9c1'],
                          'files': [{'path': 'src/api/export.py', 'change': 'added',
                                     'digest': 'sha256:77bb'}]},
        'evidence': [dict(EVIDENCE_ITEM)],
        'tests': [{'name': 'test_export_streams',
                   'command': 'python -m pytest tests/test_export.py::test_export_streams',
                   'result': 'pass', 'digest': 'sha256:9d1c'}],
        'assumptions': ['Dataset size stays under 1M rows for the streaming test bounds'],
        'decisions': [{'id': 'd1', 'decision': 'Use generator-based streaming',
                       'alternatives_considered': ['temp file'],
                       'rationale': 'Keeps memory bounded', 'supersedes': None}],
        'findings': [{'type': 'pattern', 'key': 'fastapi-streaming-csv',
                      'insight': 'Generator response with csv writer keeps memory constant',
                      'confidence': 7}],
        'unresolved_uncertainty': [],
        'risks': [{'description': 'No load test at 10M rows', 'severity': 'low',
                   'mitigation_or_acceptance': 'follow-up load test recommended'}],
        'blockers': [],
        'follow_ups': ['Add a load test for 10M rows'],
        'confidence': 8,
        'required_reviewer': {'lenses': ['functional-testing'],
                              'independence': 'any_but_executor', 'oracle': False},
        'reviewer_requirements_met': {
            'lenses_run': [{'lens': 'functional-testing', 'verdict': 'pass',
                            'coverage_statement': 'unit + integration on the export path'}],
            'coverage_complete': True,
            'oracle': {'ran': False}},
        'completion_claims': [{'claim_id': 'c1', 'status': 'verified',
                               'evidence_refs': ['ev_101']}],
        'budget_spent': {'tokens': 88400, 'cost': 1.31, 'wallclock': 1520, 'attempts': 1},
        'lineage': {'inputs_consumed': ['art_arch4'], 'artifacts_produced': ['art_e51'],
                    'parent_packet': 'pkt_0007'},
        'resume_hints': 'Continue from the export endpoint tests.',
        'attestation': {'provider': 'anthropic', 'model': 'claude-tier', 'runtime': 'internal',
                        'prompt_hash': 'sha256:deadbeef',
                        'tool_grants_snapshot': ['read_context']},
    }
    body.update(overrides)
    return body


def candidates():
    """Deterministic registry-known candidates with controlled eligibility and cost."""
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


def job_contract():
    return {'request': 'Do the work',
            'milestones': [{'id': 'm1', 'objective': 'Draft the thing', 'filename': 'out.md',
                            'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 40}]}]}
