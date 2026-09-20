"""Team model: role templates, append-only versions, scoped overrides, assignments with frozen
snapshots, and the append-only activity stream (V1.4 migration 006).

See docs/v1.4/KEL_V1.4_TEAM_MODEL.md. Structural rules enforced here:
- role edits create new versions; history is never rewritten (rollback = copy-forward),
- project overrides beat global defaults, task overrides beat project overrides,
- an assignment freezes the resolved role version plus policy/model/budget snapshot,
- only Kel creates assignments (no recursive delegation),
- activity events are a fixed contract and never carry hidden reasoning.
"""
import contextlib
import json
import time

from .core import PolicyError, digest, encode, uid
from .guardrails import assert_no_lock_edits, locked_block
from .memory import _backup, _is_fresh_database, _table

MIGRATION_VERSION = 6
MIGRATION_NAME = 'v14-team'

DDL = """
CREATE TABLE IF NOT EXISTS role_templates(
  template_id TEXT PRIMARY KEY, name TEXT NOT NULL, department TEXT NOT NULL,
  status TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS role_versions(
  template_id TEXT NOT NULL, version INTEGER NOT NULL, digest TEXT NOT NULL,
  data TEXT NOT NULL, author TEXT NOT NULL, created REAL NOT NULL,
  PRIMARY KEY(template_id, version));
CREATE TABLE IF NOT EXISTS role_overrides(
  template_id TEXT NOT NULL, scope TEXT NOT NULL, project_id TEXT NOT NULL DEFAULT '',
  task_id TEXT NOT NULL DEFAULT '', version INTEGER NOT NULL, data TEXT NOT NULL,
  updated REAL NOT NULL, PRIMARY KEY(template_id, scope, project_id, task_id));
CREATE TABLE IF NOT EXISTS team_assignments(
  assignment_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, milestone_id TEXT NOT NULL,
  run_id TEXT, template_id TEXT NOT NULL, role_version INTEGER NOT NULL,
  snapshot TEXT NOT NULL, state TEXT NOT NULL, blocker TEXT, budget INTEGER,
  provider TEXT, model TEXT, created REAL NOT NULL, updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS team_events(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL, kind TEXT NOT NULL, actor TEXT NOT NULL,
  assignment_id TEXT, job_id TEXT, milestone_id TEXT, run_id TEXT, refs TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS assignment_artifacts(
  assignment_id TEXT NOT NULL, digest TEXT NOT NULL, filename TEXT NOT NULL,
  evidence_class TEXT NOT NULL, created REAL NOT NULL, PRIMARY KEY(assignment_id, digest));
"""

ROLE_FIELDS = ('goal', 'inputs', 'outputs', 'quality_bar', 'boundaries', 'escalation',
               'evidence_expectations', 'tool_policy', 'model_preference', 'budget',
               # Workforce v2 additions (doc 03 §7; values are validated by kel.assignment
               # when a role is used for worker assignment — additive, legacy roles keep v1).
               'authority_max', 'capability_requirements', 'dispatch_tier', 'budget_class',
               'default_skill_packs', 'independence', 'anti_patterns')
REQUIRED_ROLE_FIELDS = ('goal', 'outputs', 'quality_bar', 'tool_policy', 'budget')
ASSIGNMENT_STATES = ('QUEUED', 'ACTIVE', 'WAITING', 'BLOCKED', 'DONE', 'UNCERTAIN', 'FAILED')
EVENT_KINDS = ('assignment.created', 'assignment.started', 'step.started', 'step.finished',
               'artifact.produced', 'evidence.recorded', 'decision.made', 'approval.requested',
               'blocked', 'assignment.finished',
               # Workforce kinds (Phase 5.2; additive; the same detail prohibitions apply).
               'staffing.decided', 'contract.issued', 'task.closed',
               # Workforce learning loop (Phase 5.6; additive; mission-scoped records).
               'learning.recorded', 'retro.drafted', 'staffing.proposed', 'proposal.queued')
FORBIDDEN_DETAIL_KEYS = ('reasoning', 'chain_of_thought', 'thoughts', 'prompt', 'hidden_reasoning')
TOOLS = ('read', 'write', 'run_tests', 'install', 'browser', 'git', 'external_api', 'shell')
EVIDENCE_CLASSES = ('artifact', 'test', 'review', 'research', 'screenshot', 'receipt')
DEPARTMENTS = ('Strategy', 'Product', 'Engineering', 'Verification', 'Delivery')

SEED_ROLES = (
    ('solution-strategist', 'Solution Strategist', 'Strategy',
     {'goal': 'Turn a request into the best reasonable plan and record why.', 'inputs': 'goal, constraints, project map, memory',
      'outputs': 'solution brief with options, comparison, recommendation', 'quality_bar': 'every option compared; evidence-to-switch recorded',
      'tool_policy': {'allow': ['read', 'write'], 'deny': ['install', 'shell']}, 'budget': 12}),
    ('ui-ux-expert', 'UI/UX Expert', 'Product',
     {'goal': 'Define and defend the interaction and visual result of a surface.', 'inputs': 'rendered captures, design system, brief',
      'outputs': 'interaction spec, states, before/after evidence', 'quality_bar': 'rendered review only; no source-only claims',
      'tool_policy': {'allow': ['read', 'write', 'browser'], 'deny': ['install']}, 'budget': 16}),
    ('research-specialist', 'Research Specialist', 'Product',
     {'goal': 'Find existing solutions, donors, and prior art before building.', 'inputs': 'problem statement, donor audit',
      'outputs': 'search record with refs and verdicts', 'quality_bar': 'every claim carries a source reference',
      'tool_policy': {'allow': ['read', 'browser', 'external_api'], 'deny': ['write', 'install']}, 'budget': 10}),
    ('implementation-engineer', 'Implementation Engineer', 'Engineering',
     {'goal': 'Make the smallest coherent change that satisfies the plan.', 'inputs': 'plan, lease, repository',
      'outputs': 'code change, tests, evidence', 'quality_bar': 'tests pass; no unexplained edits',
      'tool_policy': {'allow': ['read', 'write', 'run_tests', 'install', 'git'], 'deny': ['shell']}, 'budget': 24}),
    ('qa-engineer', 'QA Engineer', 'Verification',
     {'goal': 'Try to falsify the result with checks the author did not write.', 'inputs': 'artifact, acceptance matrix',
      'outputs': 'test results, failure details, flaky flags', 'quality_bar': 'a check exists for every acceptance row',
      'tool_policy': {'allow': ['read', 'write', 'run_tests'], 'deny': ['install']}, 'budget': 16}),
    ('security-reviewer', 'Security Reviewer', 'Verification',
     {'goal': 'Find credential, boundary, and injection defects.', 'inputs': 'diff, security model',
      'outputs': 'findings with severity and evidence', 'quality_bar': 'every finding reproducible',
      'tool_policy': {'allow': ['read', 'run_tests'], 'deny': ['write', 'install', 'shell']}, 'budget': 12}),
    ('independent-reviewer', 'Independent Reviewer', 'Verification',
     {'goal': 'Judge the plan or result against criteria; never self-certify.', 'inputs': 'brief or artifact under review',
      'outputs': 'verdict OPTIMAL_ENOUGH/CHALLENGE/BLOCK with findings', 'quality_bar': 'reviewer differs from the author',
      'tool_policy': {'allow': ['read'], 'deny': ['write', 'install', 'shell']}, 'budget': 10}),
    ('release-engineer', 'Release Engineer', 'Delivery',
     {'goal': 'Package, verify, and freeze a candidate release.', 'inputs': 'green build, release checklist',
      'outputs': 'hashes, manifest, verification report', 'quality_bar': 'byte-level hashes verified; frozen set untouched',
      'tool_policy': {'allow': ['read', 'write', 'install', 'run_tests'], 'deny': ['external_api']}, 'budget': 18}),
    ('documentation-specialist', 'Documentation Specialist', 'Delivery',
     {'goal': 'Keep the written record accurate and current.', 'inputs': 'changes, receipts, docs',
      'outputs': 'updated documents with evidence links', 'quality_bar': 'docs match observed behaviour',
      'tool_policy': {'allow': ['read', 'write'], 'deny': ['install', 'shell']}, 'budget': 8}),
)


def ensure_schema(store):
    """Create the V1.4 team tables (idempotent, additive)."""
    with contextlib.closing(store.connect()) as db:
        if _table(db, 'schema_migrations') and db.execute(
                'SELECT 1 FROM schema_migrations WHERE version=?', (MIGRATION_VERSION,)).fetchone():
            return True
        first = not _table(db, 'schema_migrations')
        if first:
            if not _is_fresh_database(db):
                _backup(store, db)
            db.execute('CREATE TABLE IF NOT EXISTS schema_migrations('
                       'version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL,'
                       ' note TEXT)')
        db.executescript(DDL)
        db.execute('INSERT OR IGNORE INTO schema_migrations VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(), 'tables=6'))
        return True


def derive_state(job, run=None):
    """Assignment state is computed from engine truth, never authored by a UI or a role."""
    if run and run.get('state') == 'RUNNING':
        return 'ACTIVE'
    if run and run.get('state') in ('WAITING_APPROVAL', 'CANCEL_REQUESTED'):
        return 'WAITING'
    state = (job or {}).get('state')
    verdict = (job or {}).get('verdict')
    if state in ('AWAITING_USER', 'WAITING_RESOURCE', 'PAUSED'):
        return 'WAITING'
    if state == 'BLOCKED':
        return 'BLOCKED'
    if state == 'CLOSED':
        if verdict == 'VERIFIED':
            return 'DONE'
        if verdict == 'UNCERTAIN':
            return 'UNCERTAIN'
        return 'FAILED'
    if state == 'CANCELLED':
        return 'FAILED'
    return 'QUEUED'


class Team:
    """Roles, overrides, assignments, and the activity stream for one Kel store."""

    def __init__(self, store):
        self.store = store
        ensure_schema(store)

    # ---- roles ----------------------------------------------------------
    def _template(self, db, template_id, required=True):
        row = db.execute('SELECT * FROM role_templates WHERE template_id=?', (template_id,)).fetchone()
        if row is None and required:
            raise PolicyError('Unknown role template')
        return row

    def _validate_fields(self, fields, partial=False):
        if not isinstance(fields, dict):
            raise PolicyError('Role fields must be an object')
        assert_no_lock_edits(fields)
        unknown = [key for key in fields if key not in ROLE_FIELDS]
        if unknown:
            raise PolicyError('Unknown role field(s): %s' % ', '.join(sorted(unknown)))
        if not partial:
            missing = [key for key in REQUIRED_ROLE_FIELDS if key not in fields]
            if missing:
                raise PolicyError('Missing required role field(s): %s' % ', '.join(missing))
        if 'tool_policy' in fields:
            policy = fields['tool_policy']
            if not isinstance(policy, dict):
                raise PolicyError('tool_policy must be an object with allow/deny lists')
            for side in policy:
                if side not in ('allow', 'deny'):
                    raise PolicyError('tool_policy accepts only allow/deny')
                if not isinstance(policy[side], list) or any(t not in TOOLS for t in policy[side]):
                    raise PolicyError('Unknown tool in tool_policy: %s' % policy[side])
        if 'budget' in fields and (not isinstance(fields['budget'], int)
                                   or not 1 <= fields['budget'] <= 100):
            raise PolicyError('Budget must be 1 to 100 attempt units')
        if 'goal' in fields and (not isinstance(fields['goal'], str) or not fields['goal'].strip()):
            raise PolicyError('Role goal must be a non-empty string')
        return fields

    def current_version(self, template_id):
        with contextlib.closing(self.store.connect()) as db:
            self._template(db, template_id)
            row = db.execute('SELECT version, data FROM role_versions WHERE template_id=?'
                             ' ORDER BY version DESC LIMIT 1', (template_id,)).fetchone()
        return row['version'], json.loads(row['data'])

    def define_role(self, template_id, name, department, fields, author='kel'):
        if not isinstance(template_id, str) or not template_id.strip():
            raise PolicyError('Role id must be a non-empty string')
        if not isinstance(name, str) or not name.strip():
            raise PolicyError('Role name must be a non-empty string')
        if department not in DEPARTMENTS:
            raise PolicyError('Unknown department: %s' % department)
        self._validate_fields(fields)
        now = time.time()
        with self.store.transaction() as db:
            if self._template(db, template_id, required=False) is not None:
                raise PolicyError('Role already exists; edit it to create a new version')
            db.execute('INSERT INTO role_templates VALUES(?,?,?,?,?,?)',
                       (template_id, name.strip(), department, 'active', now, now))
            db.execute('INSERT INTO role_versions VALUES(?,?,?,?,?,?)',
                       (template_id, 1, digest(fields), encode(fields), author, now))
        return {'template_id': template_id, 'version': 1}

    def edit_role(self, template_id, fields, author='kel'):
        self._validate_fields(fields, partial=True)
        version, current = self.current_version(template_id)
        merged = dict(current)
        merged.update(fields)
        self._validate_fields(merged)
        now = time.time()
        with self.store.transaction() as db:
            db.execute('INSERT INTO role_versions VALUES(?,?,?,?,?,?)',
                       (template_id, version + 1, digest(merged), encode(merged), author, now))
            db.execute('UPDATE role_templates SET updated=? WHERE template_id=?', (now, template_id))
        return {'template_id': template_id, 'version': version + 1}

    def role_diff(self, template_id, from_version, to_version):
        with contextlib.closing(self.store.connect()) as db:
            rows = {r['version']: json.loads(r['data']) for r in db.execute(
                'SELECT version, data FROM role_versions WHERE template_id=? AND version IN (?,?)',
                (template_id, from_version, to_version))}
        if from_version not in rows or to_version not in rows:
            raise PolicyError('Unknown role version')
        before, after = rows[from_version], rows[to_version]
        return {key: {'from': before.get(key), 'to': after.get(key)}
                for key in set(before) | set(after) if before.get(key) != after.get(key)}

    def rollback_role(self, template_id, to_version, author='kel'):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT data FROM role_versions WHERE template_id=? AND version=?',
                             (template_id, to_version)).fetchone()
        if not row:
            raise PolicyError('Unknown role version')
        return self.edit_role(template_id, json.loads(row['data']), author=author)

    # ---- overrides ------------------------------------------------------
    def set_override(self, template_id, scope, fields, project_id='', task_id='', author='kel'):
        if scope not in ('project', 'task'):
            raise PolicyError('Override scope must be project or task')
        if scope == 'project' and not project_id:
            raise PolicyError('Project override needs a project id')
        if scope == 'task' and not (project_id and task_id):
            raise PolicyError('Task override needs project and task ids')
        self._validate_fields(fields, partial=True)
        version, _current = self.current_version(template_id)
        with self.store.transaction() as db:
            db.execute('INSERT INTO role_overrides VALUES(?,?,?,?,?,?,?)'
                       ' ON CONFLICT(template_id, scope, project_id, task_id)'
                       ' DO UPDATE SET version=excluded.version, data=excluded.data, updated=excluded.updated',
                       (template_id, scope, project_id, task_id, version, encode(fields), time.time()))
        return {'template_id': template_id, 'scope': scope, 'project_id': project_id,
                'task_id': task_id, 'version': version}

    def resolve_role(self, template_id, project_id='', task_id=''):
        try:
            version, fields = self.current_version(template_id)
        except PolicyError:
            # Kel manages its own roster: a role that ships with the product is seeded on first
            # use, so a person never has to manage rosters. Unknown ids still fail closed.
            if template_id not in {seed[0] for seed in SEED_ROLES}:
                raise
            self.seed_defaults()
            version, fields = self.current_version(template_id)
        resolved = dict(fields)
        sources = ['global@v%d' % version]
        with contextlib.closing(self.store.connect()) as db:
            rows = [r for r in db.execute(
                'SELECT * FROM role_overrides WHERE template_id=?', (template_id,))]
        for row in rows:
            if row['scope'] == 'project' and row['project_id'] == project_id:
                resolved.update(json.loads(row['data']))
                sources.append('project:%s@v%d' % (project_id, row['version']))
            elif row['scope'] == 'task' and row['project_id'] == project_id and row['task_id'] == task_id:
                resolved.update(json.loads(row['data']))
                sources.append('task:%s@v%d' % (task_id, row['version']))
        return {'template_id': template_id, 'role_version': version, 'fields': resolved,
                'sources': sources, 'locked_block': locked_block()}

    # ---- assignments ----------------------------------------------------
    def create_assignment(self, job_id, milestone_id, template_id, project_id='', task_id='',
                          actor='kel', run_id=None, provider=None, model=None, budget=None,
                          extra=None):
        if actor != 'kel':
            raise PolicyError('Delegation is Kel’s decision only')
        job = self.store.get(job_id)
        milestone = (job.get('milestones') or {}).get(milestone_id)
        if milestone is None:
            raise PolicyError('Unknown milestone for this job')
        resolved = self.resolve_role(template_id, project_id, task_id)
        fields = resolved['fields']
        snapshot = {'role_template': template_id, 'role_version': resolved['role_version'],
                    'sources': resolved['sources'], 'instructions_digest': digest(fields),
                    'tool_policy': fields.get('tool_policy', {}),
                    'model_preference': fields.get('model_preference'),
                    'budget': budget if budget is not None else fields.get('budget')}
        if extra is not None:
            if not isinstance(extra, dict):
                raise PolicyError('Assignment snapshot extras must be an object')
            collisions = sorted(set(extra) & set(snapshot))
            if collisions:
                raise PolicyError('Extras may not override snapshot keys: %s'
                                  % ', '.join(collisions))
            # Function-scope import: kel.workforce imports this module at load time.
            from .workforce import find_unsafe
            unsafe = find_unsafe(extra, path='snapshot extras')
            if unsafe:
                raise PolicyError('Unsafe assignment snapshot extras: %s'
                                  % '; '.join(unsafe[:3]))
            snapshot.update(extra)
        assignment_id = uid()
        now = time.time()
        with self.store.transaction() as db:
            db.execute('INSERT INTO team_assignments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (assignment_id, job_id, milestone_id, run_id, template_id,
                        resolved['role_version'], encode(snapshot), 'QUEUED', None,
                        snapshot['budget'], provider, model, now, now))
            self._event(db, 'assignment.created', actor, assignment_id, job_id, milestone_id,
                        run_id, {'role_template': template_id, 'role_version': resolved['role_version']})
        return {'assignment_id': assignment_id, 'snapshot': snapshot}

    def _event(self, db, kind, actor, assignment_id=None, job_id=None, milestone_id=None,
               run_id=None, detail=None, refs=None):
        if kind not in EVENT_KINDS:
            raise PolicyError('Unknown activity kind: %s' % kind)
        payload = detail or {}
        if isinstance(payload, dict):
            for key in payload:
                if key in FORBIDDEN_DETAIL_KEYS:
                    raise PolicyError('Activity never carries hidden reasoning')
        db.execute('INSERT INTO team_events(at,kind,actor,assignment_id,job_id,milestone_id,run_id,refs,detail)'
                   ' VALUES(?,?,?,?,?,?,?,?,?)',
                   (time.time(), kind, actor, assignment_id, job_id, milestone_id, run_id,
                    encode(refs) if refs is not None else None,
                    encode(payload) if payload else None))

    def _assignment(self, db, assignment_id):
        row = db.execute('SELECT * FROM team_assignments WHERE assignment_id=?',
                         (assignment_id,)).fetchone()
        if not row:
            raise PolicyError('Unknown assignment')
        return row

    def attach_run(self, assignment_id, run_id, provider=None, model=None):
        with self.store.transaction() as db:
            row = self._assignment(db, assignment_id)
            db.execute('UPDATE team_assignments SET run_id=?, provider=?, model=?, state=?, updated=?'
                       ' WHERE assignment_id=?',
                       (run_id, provider, model, 'ACTIVE', time.time(), assignment_id))
            self._event(db, 'assignment.started', 'kel', assignment_id, row['job_id'],
                        row['milestone_id'], run_id, {'provider': provider, 'model': model})
        return {'assignment_id': assignment_id, 'run_id': run_id}

    def record_activity(self, assignment_id, kind, detail=None, refs=None, actor=None):
        with self.store.transaction() as db:
            row = self._assignment(db, assignment_id)
            self._event(db, kind, actor or assignment_id, assignment_id, row['job_id'],
                        row['milestone_id'], row['run_id'], detail, refs)
        return {'ok': True}

    def record_mission_activity(self, kind, detail=None, refs=None, actor='kel'):
        """Append one mission-scoped event not tied to a single assignment (learning loop).

        Used by the Phase 5.6 shadow loop (doc 11) for learning/retro/proposal records; the
        same EVENT_KINDS validation and reasoning-key prohibitions as every other activity
        apply, and the row is append-only exactly like assignment-scoped activities.
        """
        if kind not in EVENT_KINDS:
            raise PolicyError('Unknown activity kind: %s' % kind)
        with self.store.transaction() as db:
            self._event(db, kind, actor, None, None, None, None, detail, refs)
            seq = db.execute('SELECT max(seq) FROM team_events').fetchone()[0]
        return {'ok': True, 'seq': seq}

    def add_artifact(self, assignment_id, artifact_digest, filename, evidence_class):
        if evidence_class not in EVIDENCE_CLASSES:
            raise PolicyError('Unknown evidence class: %s' % evidence_class)
        if not isinstance(filename, str) or '/' in filename or '\\' in filename:
            raise PolicyError('Artifact filename must be a simple name')
        with self.store.transaction() as db:
            row = self._assignment(db, assignment_id)
            db.execute('INSERT OR IGNORE INTO assignment_artifacts VALUES(?,?,?,?,?)',
                       (assignment_id, artifact_digest, filename, evidence_class, time.time()))
            self._event(db, 'artifact.produced' if evidence_class == 'artifact' else 'evidence.recorded',
                        assignment_id, assignment_id, row['job_id'], row['milestone_id'],
                        row['run_id'], {'digest': artifact_digest, 'filename': filename,
                                        'evidence_class': evidence_class})
        return {'ok': True}

    def set_state(self, assignment_id, state, blocker=None):
        if state not in ASSIGNMENT_STATES:
            raise PolicyError('Unknown assignment state: %s' % state)
        with self.store.transaction() as db:
            row = self._assignment(db, assignment_id)
            db.execute('UPDATE team_assignments SET state=?, blocker=?, updated=?'
                       ' WHERE assignment_id=?', (state, blocker, time.time(), assignment_id))
            if state in ('DONE', 'FAILED', 'UNCERTAIN'):
                self._event(db, 'assignment.finished', 'kel', assignment_id, row['job_id'],
                            row['milestone_id'], row['run_id'], {'state': state, 'blocker': blocker})
            elif state == 'BLOCKED':
                self._event(db, 'blocked', 'kel', assignment_id, row['job_id'], row['milestone_id'],
                            row['run_id'], {'blocker': blocker or 'guardrail'})
        return {'assignment_id': assignment_id, 'state': state}

    def tool_allowed(self, template_id, tool, project_id='', task_id=''):
        if tool not in TOOLS:
            raise PolicyError('Unknown tool: %s' % tool)
        policy = self.resolve_role(template_id, project_id, task_id)['fields'].get('tool_policy') or {}
        if tool in (policy.get('deny') or []):
            return False
        return tool in (policy.get('allow') or [])

    def activity(self, assignment_id):
        with contextlib.closing(self.store.connect()) as db:
            self._assignment(db, assignment_id)
            rows = [dict(r) for r in db.execute(
                'SELECT * FROM team_events WHERE assignment_id=? ORDER BY seq', (assignment_id,))]
        for row in rows:
            row['detail'] = json.loads(row['detail']) if row['detail'] else None
            row['refs'] = json.loads(row['refs']) if row['refs'] else None
        return rows

    def assignments(self, project_id=None):
        with contextlib.closing(self.store.connect()) as db:
            rows = [dict(r) for r in db.execute(
                'SELECT * FROM team_assignments ORDER BY created DESC')]
        out = []
        for row in rows:
            try:
                job = self.store.get(row['job_id'])
            except KeyError:
                continue  # assignments must reference real jobs; orphan rows never surface
            run = None
            with contextlib.closing(self.store.connect()) as db:
                run = db.execute('SELECT * FROM runs WHERE job_id=? AND milestone_id=?'
                                 ' ORDER BY rowid DESC LIMIT 1',
                                 (row['job_id'], row['milestone_id'])).fetchone()
            state = derive_state(job, dict(run) if run else None)
            with contextlib.closing(self.store.connect()) as db:
                name = db.execute('SELECT name FROM role_templates WHERE template_id=?',
                                  (row['template_id'],)).fetchone()
            out.append({'assignment_id': row['assignment_id'], 'job_id': row['job_id'],
                        'milestone_id': row['milestone_id'], 'run_id': row['run_id'],
                        'role': (name['name'] if name else row['template_id']),
                        'role_version': row['role_version'],
                        'derived_state': state, 'blocker': row['blocker'],
                        'budget': row['budget'], 'spent': job.get('spent'),
                        'provider': row['provider'], 'model': row['model'],
                        'created': row['created'], 'updated': max(row['updated'], job.get('created', 0)),
                        'snapshot_digest': json.loads(row['snapshot'])['instructions_digest']})
        return out

    def roster(self):
        with contextlib.closing(self.store.connect()) as db:
            templates = [dict(r) for r in db.execute(
                'SELECT * FROM role_templates ORDER BY department, name')]
            for row in templates:
                latest = db.execute('SELECT version FROM role_versions WHERE template_id=?'
                                    ' ORDER BY version DESC LIMIT 1',
                                    (row['template_id'],)).fetchone()
                row['version'] = latest['version'] if latest else None
                row['assignments'] = db.execute(
                    'SELECT count(*) FROM team_assignments WHERE template_id=?',
                    (row['template_id'],)).fetchone()[0]
        return templates

    def seed_defaults(self, author='kel'):
        created = []
        for template_id, name, department, fields in SEED_ROLES:
            try:
                self.define_role(template_id, name, department, fields, author=author)
                created.append(template_id)
            except PolicyError:
                continue  # already present; seeding is idempotent
        return created

    def staffing(self, brief_id, entries):
        """Record the staffing plan (why this specialist) inside the solution brief."""
        from .solution import SolutionBriefs
        if not isinstance(entries, list) or not entries:
            raise PolicyError('Staffing plan needs at least one entry')
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get('milestone') or not entry.get('role'):
                raise PolicyError('Staffing entries need milestone and role')
            if not entry.get('reasons'):
                raise PolicyError('Staffing entries need recorded reasons')
        return SolutionBriefs(self.store).update(brief_id, staffing=entries)

    def apply(self, data):
        action = data.get('action')
        if action == 'seed':
            return {'created': self.seed_defaults()}
        if action == 'roster':
            return {'roles': self.roster(), 'departments': list(DEPARTMENTS)}
        if action == 'office':
            return {'assignments': self.assignments(data.get('project_id'))}
        if action == 'role':
            return self.resolve_role(data['template_id'], data.get('project_id', ''),
                                     data.get('task_id', ''))
        if action == 'history':
            with contextlib.closing(self.store.connect()) as db:
                rows = [dict(r) for r in db.execute(
                    'SELECT version, digest, author, created FROM role_versions'
                    ' WHERE template_id=? ORDER BY version', (data['template_id'],))]
            return {'versions': rows}
        if action == 'diff':
            return self.role_diff(data['template_id'], int(data['from']), int(data['to']))
        if action == 'rollback':
            return self.rollback_role(data['template_id'], int(data['to']))
        if action == 'override':
            return self.set_override(data['template_id'], data['scope'], data['fields'],
                                     data.get('project_id', ''), data.get('task_id', ''))
        if action == 'assignment':
            return self.create_assignment(data['job'], data['milestone'], data['template_id'],
                                          data.get('project_id', ''), data.get('task_id', ''),
                                          run_id=data.get('run_id'), provider=data.get('provider'),
                                          model=data.get('model'), budget=data.get('budget'))
        if action == 'activity':
            return self.record_activity(data['assignment_id'], data['kind'], data.get('detail'),
                                        data.get('refs'))
        if action == 'artifact':
            return self.add_artifact(data['assignment_id'], data['digest'], data['filename'],
                                     data.get('evidence_class', 'artifact'))
        if action == 'state':
            return self.set_state(data['assignment_id'], data['state'], data.get('blocker'))
        if action == 'timeline':
            return {'events': self.activity(data['assignment_id'])}
        if action == 'tool_check':
            return {'allowed': self.tool_allowed(data['template_id'], data['tool'],
                                                 data.get('project_id', ''), data.get('task_id', ''))}
        if action == 'staffing':
            return self.staffing(data['brief'], data['entries'])
        raise PolicyError('Unknown team action: %s' % action)
