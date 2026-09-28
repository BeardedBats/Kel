"""D-65: in Full access, a verified coding change is applied to the project folder on its own.

Where it runs: the engine settles a coding job (CLOSED, VERIFIED) and calls `settle` just before it
publishes the result, so the one result message can say what was applied, where, and how it was
checked. The write itself is `apply_changes.apply_checked` — the same digest-bound, journaled,
backed-up application Nick's own Apply uses — so snapshots, conflict checks and crash recovery are
identical. `apply_changes.undo_applied` puts the saved files back.

Still waits for Nick (its needs-you card asks Apply / Leave it, D-70): a change that failed or
skipped verification, a change that touches a protected place (Kel's app or data, a system or
credential folder — D-64), and any change while the mode is "Ask first". Kel also waits when the
automatic apply itself is refused (the project changed since coding started, authorization was
withdrawn); the reason is kept and shown.

Idempotent and crash-safe: the decision is written once per job (`auto_applications`) *before* any
file is touched. `applying` means an automatic apply began; a restart resumes it through the
application journal (never repeating a finished replacement) and it still counts as automatic.
`applied` / `waiting` / `manual` are settled and never re-decided, so a restart can neither apply
twice nor lose the waiting state.
"""
import contextlib
import json
import time
from pathlib import Path

from .core import Conflict

DDL = ('CREATE TABLE IF NOT EXISTS auto_applications(job_id TEXT PRIMARY KEY, decision TEXT NOT NULL,'
       ' reason TEXT, mode TEXT, at REAL NOT NULL)')

APPLYING = 'applying'   # an automatic apply began (a restart resumes it)
APPLIED = 'applied'     # applied automatically
WAITING = 'waiting'     # kept for Nick: `reason` says why ('ask' = Ask first is on)
MANUAL = 'manual'       # Nick applied it himself later (after an undo, or from a waiting state)
ASK_REASON = 'ask'
ASK_WORDS = 'Ask first is on'  # the plain waiting reason the card shows for ASK_REASON
ASK_WORDS_BEFORE = 'Ask first was on when it finished'  # …after Nick switched to Full access since


def ensure_schema(store):
    with contextlib.closing(store.connect()) as db:
        db.execute(DDL)


def decision(store, job_id):
    ensure_schema(store)
    with contextlib.closing(store.connect()) as db:
        row = db.execute('SELECT * FROM auto_applications WHERE job_id=?', (str(job_id),)).fetchone()
    return dict(row) if row else None


def _insert(store, job_id, value, reason, mode):
    ensure_schema(store)
    with store.transaction() as db:
        db.execute('INSERT OR IGNORE INTO auto_applications VALUES(?,?,?,?,?)',
                   (job_id, value, reason, mode, time.time()))


def _record(store, job_id, value, reason=None, mode=None, only_if=None):
    """Write the decision. `only_if` guards a transition (e.g. applying -> waiting)."""
    ensure_schema(store)
    with store.transaction() as db:
        row = db.execute('SELECT decision FROM auto_applications WHERE job_id=?', (job_id,)).fetchone()
        if row is None:
            db.execute('INSERT INTO auto_applications VALUES(?,?,?,?,?)',
                       (job_id, value, reason, mode, time.time()))
            return True
        if only_if is not None and row['decision'] != only_if:
            return False
        db.execute('UPDATE auto_applications SET decision=?, reason=?, at=? WHERE job_id=?',
                   (value, reason, time.time(), job_id))
        return True


def changed_paths(store, job):
    """The project-relative paths the verified change touches (from the trusted manifests)."""
    run_id = job['milestones']['code']['artifact']['run_id']
    with contextlib.closing(store.connect()) as db:
        workspace = db.execute('SELECT manifest FROM code_workspaces WHERE job_id=?', (job['id'],)).fetchone()
        evidence = db.execute('SELECT manifest FROM code_evidence WHERE run_id=?', (run_id,)).fetchone()
    if not workspace or not evidence:
        return None
    before, after = json.loads(workspace['manifest']), json.loads(evidence['manifest'])
    return sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))


def verification_complete(store, job):
    """True only when the trusted tests passed *and* a separate review approved the exact change."""
    if job.get('contract', {}).get('kind') != 'coding' or job.get('verdict') != 'VERIFIED':
        return False
    milestone = (job.get('milestones') or {}).get('code')
    if not milestone or milestone.get('state') != 'ACCEPTED' or not milestone.get('artifact'):
        return False
    checks = [c for c in milestone.get('checks') or [] if isinstance(c, dict)]
    tests = [c for c in checks if c.get('kind') == 'repository_evidence']
    reviews = [c for c in checks if c.get('kind') == 'manual_review']
    if not tests or any(c.get('verdict') != 'VERIFIED' for c in tests):
        return False
    if not reviews or any(c.get('verdict') != 'VERIFIED' or not c.get('reviewer_id') for c in reviews):
        return False
    from .coding import check_evidence
    return check_evidence(store, milestone['artifact']['run_id']) == 'VERIFIED'


def protected_reason(store, job, paths):
    """A plain reason when the change would touch a protected place (D-64), else None."""
    from . import authority, guardrails
    root = Path(job['contract']['root'])
    if guardrails.protected_reason(root):
        return 'a protected system location'
    targets = [str(root / p) for p in paths]
    for target in targets:
        if guardrails.frozen_path(target) or guardrails.system_path(target):
            return 'a protected system location'
    return authority.protected_hit(store, {'changes': targets, 'grantRoot': str(root)})


def why_wait(store, job):
    """None when Kel may apply on its own; otherwise the reason it waits for Nick."""
    from . import authority
    if not authority.is_full(store):
        return ASK_REASON
    if not verification_complete(store, job):
        return 'it did not pass every check'
    # D-66: a staffed pod's verdict must be clean (no live blocker/critical on this change), and a
    # triggered independent second opinion (the Oracle) must have run and found nothing blocking.
    from .pod_review import live_serious
    serious = live_serious(store, job, 'code')
    if serious:
        return 'the independent review found a problem: ' + serious[0]['summary']
    from .oracle import gate as oracle_gate
    reason = oracle_gate(store, job)
    if reason:
        return reason
    paths = changed_paths(store, job)
    if not paths:
        return 'Kel could not read which files it changes'
    reason = protected_reason(store, job, paths)
    if reason:
        return 'it would change ' + reason
    return None


def settle(store, job_id):
    """Apply a settled, verified coding change on its own when D-65 allows it.

    Returns 'applied', 'waiting', 'busy' (the project is being applied by someone else right now —
    try again on the next tick, before publishing) or None (not a verified coding change).
    """
    from .apply_changes import application, init
    init(store)
    ensure_schema(store)
    job = store.get(job_id)
    if job.get('contract', {}).get('kind') != 'coding' or job.get('verdict') != 'VERIFIED':
        return None
    saved = decision(store, job_id)
    current = application(store, job_id)
    if saved is None:
        if current is not None:
            return None  # Nick applied it himself before Kel settled: nothing automatic happened
        reason = why_wait(store, job)
        _insert(store, job_id, WAITING if reason else APPLYING, reason, _mode(store))
        saved = decision(store, job_id)  # the first decision written wins; it is never re-made
    if saved['decision'] == APPLYING:
        return _run(store, job_id)
    if saved['decision'] == APPLIED:
        return 'applied'
    if saved['decision'] == WAITING:
        return 'waiting'
    return None


def _mode(store):
    from . import authority
    return authority.mode(store)


def _run(store, job_id):
    from .apply_changes import apply_checked, application
    from .authorize import ensure_job_lease
    try:
        ensure_job_lease(store, store.get(job_id))  # renews an expired lease; a revoked one stays revoked
    except Exception:
        pass  # authorization below decides and reports
    try:
        apply_checked(store, job_id, actor='kel', auto=True)
        return 'applied'
    except Conflict:
        return 'busy'
    except Exception as exc:  # refused or failed: it waits for Nick instead (never retried in a loop)
        current = application(store, job_id)
        if current and current['state'] == 'APPLIED':
            return 'applied'
        if current and current['state'] == 'PREPARED':
            # Stopped part-way: a restart must not finish it on its own now that it waits for Nick.
            # The journal and backup stay; the Apply button resumes it.
            with store.transaction() as db:
                db.execute("UPDATE change_applications SET state='BLOCKED' WHERE job_id=? AND state='PREPARED'",
                           (job_id,))
        _record(store, job_id, WAITING, _plain(exc), only_if=APPLYING)
        return 'waiting'


def _plain(exc):
    text = str(exc).strip().rstrip('.')
    return text[:1].lower() + text[1:] if text else 'the automatic apply was refused'


def _count(n, word):
    return '%d %s%s' % (n, word, '' if n == 1 else 's')


def _names(paths, limit=4):
    shown = [str(p) for p in paths[:limit]]
    more = len(paths) - len(shown)
    if more:
        return ', '.join(shown) + ' and ' + _count(more, 'more file')
    if len(shown) > 1:
        return ', '.join(shown[:-1]) + ' and ' + shown[-1]
    return shown[0] if shown else ''


def _select(store, sql, *args):
    try:
        with contextlib.closing(store.connect()) as db:
            row = db.execute(sql, args).fetchone()
    except Exception:  # a store that never ran D-65 has no such table: nothing automatic happened
        return None
    return dict(row) if row else None


_SLASHES = '\\/'


def _folder_name(root):
    text = str(root or '').rstrip(_SLASHES)
    return Path(text).name or text


def place(store, root, project_id=None):
    """Where a change went, in words Nick knows: the project's name and its folder, once.

    {'project_name', 'folder', 'words'} — 'words' is "Calc demo (folder R6Proj)", or just the folder
    when the project is named after it (or has no saved name). Never the full path: that stays
    behind "Open folder"."""
    folder = _folder_name(root)
    name = None
    try:
        with contextlib.closing(store.connect()) as db:
            # Only a project whose own folder is this one names it (the job's project may be General
            # while the change went to another folder).
            wanted = str(Path(str(root))).rstrip(_SLASHES).lower() if root else None
            row = None
            candidates = db.execute("SELECT id, name, root FROM projects WHERE root IS NOT NULL AND root<>''").fetchall()
            for candidate in sorted(candidates, key=lambda c: c['id'] != project_id):
                if wanted and str(Path(candidate['root'])).rstrip(_SLASHES).lower() == wanted:
                    row = candidate
                    break
            name = (row['name'] if row else None) or None
    except Exception:
        name = None
    name = str(name).strip() if name else None
    if not name or not folder or name.lower() == folder.lower():
        words = name or folder or 'your project'
    else:
        words = '%s (folder %s)' % (name, folder)
    return {'project_name': name, 'folder': folder or None, 'words': words}


def result_text(store, job):
    """The coding result message when D-65 applied the change, or held it for Nick (Full access or
    Ask first) — naming the Apply control the card really has.

    None keeps today's text (nothing was decided for this job).
    """
    if job.get('contract', {}).get('kind') != 'coding' or job.get('verdict') != 'VERIFIED':
        return None
    # Read-only (no schema writes): this runs inside publish()'s open write transaction.
    saved = _select(store, 'SELECT * FROM auto_applications WHERE job_id=?', job['id'])
    if not saved:
        return None
    root = str(job['contract'].get('root'))
    where = place(store, root, job['contract'].get('project_id'))['words']
    tests = ' '.join(str(part) for part in job['contract'].get('test_command') or [])
    how = ('How it was checked: ' + ('`' + tests + '`' if tests else 'the project tests') +
           ' passed in a separate copy of the project, and a separate review approved the change.')
    if saved['decision'] == APPLIED:
        current = _select(store, 'SELECT plan FROM change_applications WHERE job_id=?', job['id']) or {}
        try:
            changes = json.loads(current.get('plan') or '{}').get('changes') or {}
        except (TypeError, ValueError):
            changes = {}
        added = [p for p, c in changes.items() if c.get('before') is None]
        removed = [p for p, c in changes.items() if c.get('after') is None]
        edited = [p for p in changes if p not in added and p not in removed]
        parts = []
        if edited:
            parts.append('changed ' + _names(edited))
        if added:
            parts.append('added ' + _names(added))
        if removed:
            parts.append('removed ' + _names(removed))
        what = '; '.join(parts) or 'no files'
        lead = ('Your new project is ready. ' if job['contract'].get('greenfield') else '')
        return (lead + 'Applied to ' + where + ': ' + what + ' (' + _count(len(changes), 'file') + ').\n\n'
                + how + '\n\nThe earlier files are saved — Undo on the result card puts them back.')
    if saved['decision'] == WAITING and saved.get('reason') and saved['reason'] != ASK_REASON:
        return ('The change passed its tests and a separate review. Kel did not apply it on its own: '
                + saved['reason'] + '. Choose Apply anyway on its work card at the top of this chat to write it into ' + where
                + ' — Kel checks your project for conflicts and saves a backup first.')
    if saved['decision'] == WAITING and saved.get('reason') == ASK_REASON:
        lead = ('The code for your new project passed its tests and a separate review.'
                if job['contract'].get('greenfield') else 'The change passed its tests and a separate review.')
        return (lead + ' Ask first is on, so Kel has not changed ' + where + ' yet. Choose Apply on its work card'
                + ' at the top of this chat to write it in, or Leave it — Kel checks your project for conflicts'
                + ' and saves a backup first, so you can undo it.\n\n' + how)
    return None


def describe(store, job_ids):
    """What the Work card needs per coding job: application state, automatic or not, and why it waits."""
    ids = [str(j) for j in job_ids]
    if not ids:
        return {}
    out = {}
    marks = ','.join('?' * len(ids))
    rows, decisions, answered = {}, {}, set()
    with contextlib.closing(store.connect()) as db:  # read-only: /api/state polls this
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'change_applications' in tables:
            rows = {r['job_id']: r for r in db.execute(
                'SELECT job_id,root,plan,state FROM change_applications WHERE job_id IN (%s)' % marks, ids)}
        if 'auto_applications' in tables:
            decisions = {r['job_id']: r for r in db.execute(
                'SELECT job_id,decision,reason FROM auto_applications WHERE job_id IN (%s)' % marks, ids)}
        if 'needs_you_answers' in tables:  # D-70: Nick answered Apply / Leave it on the card
            answered = {r['job_id'] for r in db.execute(
                'SELECT job_id FROM needs_you_answers WHERE job_id IN (%s)' % marks, ids)}
    ask_words = []  # read the mode once, only when an Ask-first change is waiting

    def asked():
        if not ask_words:
            from . import authority
            ask_words.append(ASK_WORDS_BEFORE if authority.is_full(store) else ASK_WORDS)
        return ask_words[0]

    for job_id in ids:
        row, dec = rows.get(job_id), decisions.get(job_id)
        if not row and not dec:
            continue
        entry = {'state': row['state'] if row else None,
                 'auto': bool(dec and dec['decision'] in (APPLIED, APPLYING)),
                 'decision': dec['decision'] if dec else None,
                 'root': row['root'] if row else None, 'files': None, 'waiting_reason': None,
                 'ask_first': False}
        if row and row['root']:
            entry.update({k: v for k, v in place(store, row['root']).items() if k in ('project_name', 'folder')})
        if row:
            try:
                entry['files'] = len(json.loads(row['plan']).get('changes') or {})
            except (TypeError, ValueError):
                pass
        # Waiting for Nick until he answers: under Ask first the reason is the mode itself.
        if dec and dec['decision'] == WAITING and job_id not in answered:
            entry['ask_first'] = dec['reason'] == ASK_REASON
            entry['waiting_reason'] = asked() if entry['ask_first'] else dec['reason']
        out[job_id] = entry
    return out
