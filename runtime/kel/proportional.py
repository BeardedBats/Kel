"""D-85: review depth proportional to what is at stake.

The default is the lightest check that fits. Small, reversible or exploratory work runs the project's
own tests (or, for writing, the built-in checks) and no independent reviewer; Undo covers the rest. The
Verifier reviews real code changes of meaningful size or risk. The Oracle, Sentinel and the Red Team
have their own, narrower triggers (`staff.plan_job`, `oracle.trigger`).

The decision is made at intake from the frozen staffing record (`staffing['review']['verifier']`) and,
for code, finished on the verified diff's size. Jobs staffed before D-85 carry no verifier decision and
keep their Verifier; an unstaffed job keeps it too. Never re-decided after a restart: the intake part is
frozen with the contract and the size part is read from the trusted evidence.
"""
import contextlib
import json

# A code change is "of meaningful size" above either threshold (measured on the trusted diff).
VERIFIER_FILES = 3
VERIFIER_LINES = 80
# Flags that make any change worth an independent review, whatever its size.
RISK_FLAGS = ('security_boundary', 'privacy', 'data_migration', 'irreversible', 'release', 'new_dependency')
TIER_RANK = {'D0': 0, 'D1': 1, 'D2': 2, 'D3': 3, 'D4': 4}
REVIEWER_ID = 'kel:proportional'


def verifier_decision(kind, tier, flags, contract=None):
    """{'when': 'always'|'if_large'|'never', 'why': str, 'size': {...}} for one staffed job (frozen)."""
    contract = contract or {}
    risky = [flag for flag in flags or () if flag in RISK_FLAGS]
    size = {'files': VERIFIER_FILES, 'lines': VERIFIER_LINES}
    if tier == 'D4':
        return {'when': 'always', 'why': 'high-assurance work is always reviewed independently', 'size': None}
    if risky:
        return {'when': 'always', 'why': 'the work touches %s' % ', '.join(f.replace('_boundary', '').replace('_', ' ')
                                                                       for f in risky), 'size': None}
    if kind == 'code':
        if contract.get('greenfield'):
            return {'when': 'never', 'size': None,
                    'why': 'a new prototype project gets a quick sanity check: its own smoke test'}
        return {'when': 'if_large', 'size': size,
                'why': 'a code change is reviewed independently only when it is large (more than %d files or '
                       '%d changed lines)' % (VERIFIER_FILES, VERIFIER_LINES)}
    if kind == 'research':
        return {'when': 'always', 'why': 'research claims are checked against their sources', 'size': None}
    if TIER_RANK.get(tier, 0) >= 2:
        return {'when': 'always', 'why': 'larger written work is reviewed independently', 'size': None}
    return {'when': 'never', 'size': None,
            'why': 'a short draft gets a quick sanity check (Kel\'s built-in checks), not an independent review'}


def _decision(job):
    from .staff import staffing_of
    record = staffing_of(job)
    if not record:
        return None
    return (record.get('review') or {}).get('verifier')


def diff_size(store, run_id):
    """(files, changed lines, test_changes guard) of one coding run's trusted evidence; None when absent."""
    if not run_id:
        return None
    with contextlib.closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='code_evidence'").fetchone():
            return None
        row = db.execute('SELECT patch, tests FROM code_evidence WHERE run_id=?', (run_id,)).fetchone()
    if not row:
        return None
    patch = str(row['patch'] or '')
    files = sum(1 for line in patch.splitlines() if line.startswith('diff --git '))
    lines = sum(1 for line in patch.splitlines() if line[:1] in '+-' and not line.startswith(('+++', '---')))
    try:
        guard = json.loads(row['tests']).get('test_changes_guard')
    except (TypeError, ValueError):
        guard = None
    return files, lines, guard


def verifier_needed(job, files=None, lines=None):
    """(needed, plain why) from the frozen decision and, for `if_large`, the measured size."""
    decision = _decision(job)
    if not decision:
        return True, None
    when = decision.get('when')
    if when == 'always':
        return True, decision.get('why')
    if when == 'never':
        return False, decision.get('why')
    size = decision.get('size') or {'files': VERIFIER_FILES, 'lines': VERIFIER_LINES}
    if files is None or lines is None:
        return True, 'the size of the change could not be measured'
    if files > int(size.get('files') or VERIFIER_FILES) or lines > int(size.get('lines') or VERIFIER_LINES):
        return True, 'a sizeable change (%d files, %d changed lines)' % (files, lines)
    return False, 'a small change (%s, %s)' % (_count(files, 'file'), _count(lines, 'changed line'))


def _count(n, noun):
    return '%d %s%s' % (n, noun, '' if n == 1 else 's')


def review_skip(store, job, milestone_id):
    """A plain reason no independent review is needed for this step (D-85), or None to review it."""
    if not _decision(job):
        return None
    milestone = (job.get('milestones') or {}).get(milestone_id) or {}
    measured = None
    if (job.get('contract') or {}).get('kind') == 'coding':
        measured = diff_size(store, (milestone.get('artifact') or {}).get('run_id'))
        if measured is None:
            return None
        if measured[2] == 'verifier':
            return None  # D-84: this change's test edits were left to the Verifier
    needed, why = verifier_needed(job, *(measured[:2] if measured else (None, None)))
    if needed:
        return None
    if (job.get('contract') or {}).get('kind') == 'coding':
        return ('No independent review was needed: %s whose tests pass. Undo puts it back.'
                % (why or 'a small change'))
    return 'No independent review was needed: %s.' % (why or 'a short draft')


def independently_reviewed(job):
    """True when a real reviewer (not the D-85 skip) approved every reviewed step."""
    checks = [c for m in (job.get('milestones') or {}).values() for c in m.get('checks') or []
              if isinstance(c, dict) and c.get('kind') == 'manual_review']
    return bool(checks) and not any(c.get('proportional') for c in checks)
