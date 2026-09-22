"""Kibble Build Update backend (D-46): a development mission and a reviewable candidate.

Kibble is the user-facing name for Fix Capture / Dogfood behavior; the internal identifiers stay as
they are (`dogfood_fixes`, `Dogfood`, migration 22 `v20-fix-capture`, `/api/dogfood`). Build Update
takes **selected findings**, creates an **isolated development mission** on the existing work
machinery (a `compile_coding` contract claimed and dispatched by the engine, an isolated
`repositories/<job_id>` worktree, `code_evidence` and the milestone's `manual_review` rubric), and —
once the mission settles — assembles a **separate candidate record** under `candidates/<id>/`:

* its source revision and a separate artifact location;
* the test and verification evidence, verbatim and bounded;
* fixed and unresolved findings (candidate claims only — Fix Capture statuses are never rewritten);
* known limitations;
* an explicit review state that only a human review moves.

Build Update **never installs and never promotes**: `promote()` refuses in plain words and no code
path here touches the running app or the source checkout. Nothing edits installed files in place;
the source is worked on through the coding snapshot, and the candidate lives under the engine data
root, separate from both the source and any installation.
"""
import contextlib
import json
import time
from pathlib import Path

from .core import PolicyError, uid

MIGRATION_VERSION = 29
MIGRATION_NAME = 'v21-build-update'

STAGES = ('OPEN', 'SETTLED')           # the mission's own coarse record
REVIEW_STATES = ('BUILDING', 'READY_FOR_REVIEW', 'APPROVED', 'REJECTED')
SELECTABLE = ('OPEN', 'BATCHED')       # Fix Capture statuses a Build Update may select
MAX_FINDINGS = 20
MAX_EXCERPT = 300
MAX_REQUEST = 4000
MAX_TEST_EXCERPT = 2000

DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations(
    version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT);
CREATE TABLE IF NOT EXISTS build_missions(
    id TEXT PRIMARY KEY,
    created REAL NOT NULL,
    updated REAL NOT NULL,
    job_id TEXT,
    conversation TEXT,
    source_root TEXT NOT NULL,
    baseline_revision TEXT,
    scope TEXT,
    findings TEXT NOT NULL,
    request TEXT,
    stage TEXT NOT NULL DEFAULT 'OPEN');
CREATE TABLE IF NOT EXISTS build_candidates(
    id TEXT PRIMARY KEY,
    mission_id TEXT UNIQUE,
    created REAL NOT NULL,
    updated REAL NOT NULL,
    job_id TEXT,
    review_state TEXT NOT NULL DEFAULT 'BUILDING',
    revision TEXT,
    artifact_location TEXT,
    evidence TEXT,
    fixed_findings TEXT,
    unresolved_findings TEXT,
    limitations TEXT,
    note TEXT,
    reviewed_at REAL,
    reviewed_by TEXT);
"""


def ensure_schema(store):
    with store.transaction() as db:
        db.execute('CREATE TABLE IF NOT EXISTS schema_migrations('
                   'version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT)')
        if db.execute('SELECT 1 FROM schema_migrations WHERE version=?',
                      (MIGRATION_VERSION,)).fetchone():
            return False
        fresh = not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='jobs'"
                               ).fetchone()
        for statement in filter(None, (part.strip() for part in DDL.split(';'))):
            if 'schema_migrations' in statement and 'CREATE' in statement.upper():
                continue
            db.execute(statement)
        db.execute('INSERT OR IGNORE INTO schema_migrations(version, name, applied, note) VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(),
                    'fresh database' if fresh else 'pre-existing database'))
        return True


def _short(value, limit):
    text = ' '.join(str(value or '').split())
    return text[:limit]


def _excerpt(value, limit=MAX_EXCERPT):
    return _short(value, limit)


def _loads(raw, fallback):
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return fallback


class BuildUpdate:
    """Selected findings in, an isolated mission and a reviewable candidate out. Never an install."""

    def __init__(self, store):
        self.store = store
        ensure_schema(store)
        self.candidates_dir = Path(store.root) / 'candidates'

    # -- reads -------------------------------------------------------------------------------------

    def _mission_row(self, mission_id):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM build_missions WHERE id=?', (str(mission_id),)).fetchone()
        if row is None:
            raise PolicyError('Kel has no development mission with that id.')
        return dict(row)

    def _candidate_row(self, candidate_id):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM build_candidates WHERE id=?',
                             (str(candidate_id),)).fetchone()
        if row is None:
            raise PolicyError('Kel has no candidate with that id.')
        return dict(row)

    def _candidate_dict(self, row):
        item = dict(row)
        item['evidence'] = _loads(row['evidence'], {})
        item['fixed_findings'] = _loads(row['fixed_findings'], [])
        item['unresolved_findings'] = _loads(row['unresolved_findings'], [])
        item['limitations'] = _loads(row['limitations'], [])
        return item

    def _mission_dict(self, row):
        item = dict(row)
        item['findings'] = _loads(row['findings'], [])
        item['scope'] = _loads(row['scope'], None)
        return item

    # -- the development mission -------------------------------------------------------------------

    def start(self, findings, *, source_root, tests, scope=None, conversation='main',
              project_id=None):
        """Create the mission: selected findings + verified repo identity + a coding contract."""
        from .coding import compile_coding, git
        from .containment import assert_usable_root
        from .dogfood import Dogfood

        if not isinstance(findings, (list, tuple)) or not findings:
            raise PolicyError('Select at least one finding for the Build Update.')
        if len(findings) > MAX_FINDINGS:
            raise PolicyError('A Build Update takes at most %d findings.' % MAX_FINDINGS)
        ordered, seen = [], set()
        for fix_id in findings:
            value = str(fix_id or '').strip()
            if value and value not in seen:
                seen.add(value)
                ordered.append(value)
        store_fixes = Dogfood(self.store)
        context = []
        for fix_id in ordered:
            try:
                fix = store_fixes.get(fix_id)
            except PolicyError:
                fix = None
            if fix is None:
                raise PolicyError('Kel has no finding with the id %s.' % fix_id)
            if fix.get('status') not in SELECTABLE:
                raise PolicyError('%s is already %s; Build Update selects open findings.'
                                  % (fix_id, str(fix.get('status') or 'closed').lower()))
            context.append({'id': fix_id, 'route': fix.get('route'), 'version': fix.get('version'),
                            'page_title': fix.get('page_title'),
                            'has_screenshot': bool(fix.get('has_screenshot')),
                            'transcript_excerpt': _excerpt(fix.get('transcript'))})
        root = Path(str(source_root or '')).expanduser()
        if not root.is_dir():
            raise PolicyError('Pick the repository folder the mission should work in.')
        assert_usable_root(root, purpose='a development mission', store=self.store)
        try:
            top = git(root, 'rev-parse', '--show-toplevel').decode().strip()
        except PolicyError as exc:
            # Measured in the V2-18 acceptance journey: a raw git message reached the person
            # ("fatal: not a git repository…") instead of one of Kel's own sentences. Kel says what
            # it needs and keeps the underlying detail in parentheses.
            detail = ' '.join(str(exc).split())[:200]
            raise PolicyError('That folder is not a Git repository, so Kel cannot verify a baseline.'
                              + (' (%s)' % detail if detail else '')) from None
        except Exception:
            raise PolicyError('That folder is not a Git repository, so Kel cannot verify a baseline.'
                              ) from None
        if Path(top).resolve() != root.resolve():
            raise PolicyError('Point the mission at the repository root itself (%s).' % top)
        if git(root, 'status', '--porcelain').strip():
            raise PolicyError('The source has uncommitted changes. Commit or stash them first; a '
                              'mission needs a clean baseline.')
        baseline = git(root, 'rev-parse', 'HEAD').decode().strip()
        if not isinstance(tests, (list, tuple)) or not tests:
            raise PolicyError('A Build Update needs the test command as an argument list.')
        lines = ['Repair the selected Kibble findings in this source tree.', '']
        for item in context:
            lines.append('%s%s: %s' % (item['id'], (' (%s, %s)' % (item['route'], item['version']))
                                       if item['route'] or item['version'] else '',
                                       item['transcript_excerpt']))
        lines.append('')
        lines.append('Change only what these findings require; keep the existing tests passing; '
                     'do not touch installed files, and do not publish anything.')
        request = '\n'.join(lines)[:MAX_REQUEST]
        contract = compile_coding(request, root, list(tests),
                                  project_id=project_id or 'default', greenfield=False)
        job = self.store.create(contract, conversation=conversation or 'main')
        job_id = job['id'] if isinstance(job, dict) else job
        mission_id = 'kbm_' + uid()
        now = time.time()
        with self.store.transaction() as db:
            db.execute('INSERT INTO build_missions(id,created,updated,job_id,conversation,source_root,'
                       'baseline_revision,scope,findings,request,stage) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (mission_id, now, now, job_id, conversation or 'main', str(root), baseline,
                        json.dumps(scope) if scope else None, json.dumps(context), request, 'OPEN'))
        return {'mission': self._mission_dict(self._mission_row(mission_id)),
                'job': job_id, 'contract': contract}

    def status(self, mission_id):
        """Live mission state: the record plus the job's own state (a pure read)."""
        mission = self._mission_dict(self._mission_row(mission_id))
        job = self.store.get(mission['job_id']) if mission.get('job_id') else None
        summary = None
        if job:
            milestones = job.get('milestones') or {}
            summary = {'id': job['id'], 'state': job['state'], 'verdict': job.get('verdict'),
                       'milestones': {mid: {'state': m.get('state'), 'attempts': m.get('attempts')}
                                      for mid, m in milestones.items()}}
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM build_candidates WHERE mission_id=?',
                             (mission['id'],)).fetchone()
        return {'mission': mission, 'job': summary,
                'candidate': self._candidate_dict(row) if row else None}

    # -- the candidate -----------------------------------------------------------------------------

    def candidate(self, mission_id):
        """Assemble (or return) the candidate. Before the mission settles it only reports BUILDING."""
        mission = self._mission_dict(self._mission_row(mission_id))
        with contextlib.closing(self.store.connect()) as db:
            existing = db.execute('SELECT * FROM build_candidates WHERE mission_id=?',
                                  (mission['id'],)).fetchone()
        if existing is not None and existing['review_state'] in ('APPROVED', 'REJECTED'):
            return {'state': existing['review_state'], 'candidate': self._candidate_dict(existing)}
        job = self.store.get(mission['job_id']) if mission.get('job_id') else None
        if job is None or job.get('state') != 'CLOSED':
            return {'state': 'BUILDING',
                    'candidate': self._candidate_dict(existing) if existing else None,
                    'job_state': (job or {}).get('state')}
        candidate = self._assemble(mission, job, existing)
        return {'state': candidate['review_state'], 'candidate': candidate}

    def _assemble(self, mission, job, existing):
        from .coding import check_evidence, git
        milestone = (job.get('milestones') or {}).get('code') or {}
        artifact = milestone.get('artifact') or {}
        run_id = artifact.get('run_id')
        evidence = {'verified': False, 'note': 'the mission produced no artifact'}
        revision = None
        if run_id:
            try:
                evidence['verified'] = (check_evidence(self.store, run_id) == 'VERIFIED')
            except Exception:
                evidence['verified'] = False
            with contextlib.closing(self.store.connect()) as db:
                row = db.execute('SELECT * FROM code_evidence WHERE run_id=?', (run_id,)).fetchone()
            if row:
                evidence['tests'] = _excerpt(row['tests'], MAX_TEST_EXCERPT)
                evidence['baseline_tests'] = _excerpt(row['baseline_tests'], MAX_TEST_EXCERPT)
                evidence['patch_digest'] = row['patch_digest']
                evidence['workspace'] = row['workspace']
                try:
                    revision = git(Path(row['workspace']), 'rev-parse', 'HEAD').decode().strip()
                except Exception:
                    revision = None
        selected = [item['id'] for item in mission['findings']]
        fixed = list(selected) if evidence.get('verified') else []
        unresolved = [fix_id for fix_id in selected if fix_id not in fixed]
        limitations = ['Nothing was installed; the running app and the source checkout are untouched.']
        if not evidence.get('verified'):
            limitations.append('The mission did not reach verified evidence, so no finding is even '
                               'claimed as repaired here.')
        candidate_id = existing['id'] if existing else ('kbc_' + uid())
        created = existing['created'] if existing else time.time()
        folder = self.candidates_dir / candidate_id
        folder.mkdir(parents=True, exist_ok=True)
        record = {'id': candidate_id, 'mission_id': mission['id'], 'created': created,
                  'updated': time.time(), 'job_id': mission['job_id'],
                  'review_state': 'READY_FOR_REVIEW', 'revision': revision,
                  'artifact_location': str(folder), 'evidence': evidence,
                  'fixed_findings': fixed, 'unresolved_findings': unresolved,
                  'limitations': limitations,
                  'source_root': mission['source_root'],
                  'baseline_revision': mission['baseline_revision'],
                  'note': 'Fixed findings are candidate claims pending your review; Fix Capture '
                          'statuses are unchanged.'}
        (folder / 'build-report.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
        now = time.time()
        with self.store.transaction() as db:
            if existing:
                db.execute('UPDATE build_candidates SET updated=?,revision=?,artifact_location=?,'
                           "evidence=?,fixed_findings=?,unresolved_findings=?,limitations=?,"
                           "review_state='READY_FOR_REVIEW' WHERE id=?",
                           (now, revision, str(folder), json.dumps(evidence), json.dumps(fixed),
                            json.dumps(unresolved), json.dumps(limitations), candidate_id))
            else:
                db.execute('INSERT INTO build_candidates(id,mission_id,created,updated,job_id,'
                           'review_state,revision,artifact_location,evidence,fixed_findings,'
                           'unresolved_findings,limitations,note) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                           (candidate_id, mission['id'], created, now, mission['job_id'],
                            'READY_FOR_REVIEW', revision, str(folder), json.dumps(evidence),
                            json.dumps(fixed), json.dumps(unresolved), json.dumps(limitations),
                            record['note']))
            db.execute("UPDATE build_missions SET updated=?,stage='SETTLED' WHERE id=?",
                       (now, mission['id']))
        return self._candidate_dict(self._candidate_row(candidate_id))

    def review(self, candidate_id, decision, *, note='', actor='user'):
        """The human review: approve or reject the candidate. Only a person can move this state."""
        if actor != 'user':
            raise PolicyError('Only you can review a candidate.')
        decided = {'approve': 'APPROVED', 'reject': 'REJECTED'}.get(str(decision or '').lower())
        if decided is None:
            raise PolicyError('A review is approve or reject.')
        row = self._candidate_row(candidate_id)
        if row['review_state'] == 'BUILDING':
            raise PolicyError('That candidate is still being built; review it when it is ready.')
        if row['review_state'] in ('APPROVED', 'REJECTED'):
            raise PolicyError('That candidate was already reviewed.')
        with self.store.transaction() as db:
            db.execute('UPDATE build_candidates SET review_state=?,reviewed_at=?,reviewed_by=?,'
                       'note=?,updated=? WHERE id=?',
                       (decided, time.time(), actor, _short(note, 500), time.time(), row['id']))
        return self._candidate_dict(self._candidate_row(row['id']))

    def promote(self, candidate_id=None):
        """Never happens here: Build Update authorizes creating and verifying a candidate, not installing."""
        raise PolicyError('Installing a candidate is not part of Build Update. Nothing was installed '
                          'and nothing changed; promotion is a separate, explicit step that this '
                          'backend does not perform.')
