"""Central authorization boundary (V1.5 migration 010).

Every effect-capable execution path calls `authorize()` before the real effect: project writes,
repository operations, tool execution, browser use, external actions, and destructive changes.
The boundary is part of the execution path, not a checker beside it:

    intent (actor bound by the caller's trusted context, never by payload)
      -> guardrail integrity + locked rules            (kel.guardrails)
      -> role tool policy, narrowing only              (kel.team)
      -> capability lease: state, expiry, scope        (kel.autonomy -- single source)
      -> boundary expansion (asked once per target, resolved only by the user)
      -> user approval for destructive actions
      -> ALLOW | DENY | REQUIRES_BOUNDARY_EXPANSION | REQUIRES_USER_APPROVAL | EXPIRED_LEASE |
         REVOKED_LEASE | INVALID_CONTEXT | GUARDRAIL_TAMPERED

Trusted actor identities: 'user' (the authenticated loopback session; payload-supplied identity is
rejected by the service), 'kel' (engine-owned work), and 'worker' (validated against the runs table
for the named run; a stopped or orphaned run is not a live worker).

No layer broadens authority granted by a stricter layer: each layer only narrows. Every decision is
recorded in `guardrail_decisions` with the policy version and guardrail digest; repeated identical
checks inside a bounded window collapse into one record so the audit stays signal, not noise.
"""
import contextlib
import json
from pathlib import Path
import time

from .core import PolicyError, encode, uid, digest
from . import guardrails
from .autonomy import Autonomy, KINDS, BLOCKED_KINDS
from .memory import _backup, _is_fresh_database, _table

MIGRATION_VERSION = 10
MIGRATION_NAME = 'v15-authorization'
POLICY_VERSION = 'kel-authz-1.5'
DEDUPE_SECONDS = 300

DDL = """
CREATE TABLE IF NOT EXISTS guardrail_decisions(
  decision_id TEXT PRIMARY KEY, at REAL NOT NULL, actor TEXT NOT NULL,
  worker_id TEXT, role_id TEXT, project_id TEXT, job_id TEXT, milestone_id TEXT,
  lease_id TEXT, action_kind TEXT NOT NULL, tool TEXT, target TEXT,
  decision TEXT NOT NULL, rule TEXT, reason TEXT,
  policy_version TEXT NOT NULL, guardrail_digest TEXT NOT NULL,
  boundary_request_id TEXT, approval_id TEXT, evidence_refs TEXT);
CREATE INDEX IF NOT EXISTS guardrail_decisions_job ON guardrail_decisions(job_id, at);
CREATE INDEX IF NOT EXISTS guardrail_decisions_deci ON guardrail_decisions(decision, at);
"""

OUTCOMES = ('ALLOW', 'DENY', 'REQUIRES_BOUNDARY_EXPANSION', 'REQUIRES_USER_APPROVAL',
            'EXPIRED_LEASE', 'REVOKED_LEASE', 'INVALID_CONTEXT', 'GUARDRAIL_TAMPERED')
ACTORS = ('user', 'kel', 'worker')
WORKER_RUN_STATES = ('RUNNING', 'WAITING_APPROVAL')
# Effect kinds require a lease. Read-only inspection is not an effect and stays lease-free.
EFFECT_KINDS = ('write', 'repo', 'browser', 'tool', 'external', 'destructive')
KIND_SCOPE = {'write': 'root', 'destructive': 'root', 'repo': 'repo',
              'browser': 'domain', 'tool': 'tool', 'external': 'external'}
# A lease that ended for these system reasons is renewed by Kel when the user has resumed the work.
REISSUE_REASONS = ('emergency stop', 'contract revised')


def ensure_schema(store):
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
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(), 'tables=1'))
        return True


def _result(outcome, rule, reason, **extra):
    out = {'outcome': outcome, 'rule': rule, 'reason': str(reason)}
    out.update(extra)
    return out


def role_for(store, job_id, milestone_id):
    """The frozen role snapshot attached to a run, or None. Assignment is Kel's decision only."""
    with contextlib.closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='team_assignments'").fetchone():
            return None
        row = db.execute('SELECT template_id, snapshot FROM team_assignments WHERE job_id=? AND '
                         'milestone_id=? ORDER BY created DESC LIMIT 1',
                         (job_id, milestone_id)).fetchone()
    if not row:
        return None
    try:
        snapshot = json.loads(row['snapshot'])
    except (TypeError, ValueError):
        snapshot = {}
    return {'template_id': row['template_id'], 'tool_policy': snapshot.get('tool_policy') or {}}


def project_creation_root():
    """The only location where an explicit user request may create a new project folder."""
    return (Path.home() / 'Documents' / 'Kel Projects').resolve()


class Authorizer:
    def __init__(self, store):
        ensure_schema(store)
        self.store = store
        self.autonomy = Autonomy(store)

    # ---- decision ------------------------------------------------------------
    def decide(self, intent, record=True):
        decision = self._decide(intent)
        if record:
            decision['decision_id'] = self._record(intent, decision)
        return decision

    def _decide(self, intent):
        actor = str(intent.get('actor') or '')
        kind = str(intent.get('action_kind') or '')
        tool = str(intent.get('tool') or '')
        target = str(intent.get('target') or '')
        job_id = intent.get('job')
        milestone_id = intent.get('milestone')
        # 1. Guardrail integrity: a modified rule set refuses every effect.
        try:
            guardrails.assert_intact()
        except PolicyError as exc:
            return _result('GUARDRAIL_TAMPERED', 'policy-immutable', exc)
        # 2. Context validity: trusted actor, known kind, real job and milestone.
        if actor not in ACTORS:
            return _result('INVALID_CONTEXT', 'actor-unknown',
                           'Actor identity is not a trusted Kel identity')
        if kind not in KINDS and kind not in BLOCKED_KINDS:
            return _result('INVALID_CONTEXT', 'kind-unknown', 'Unknown action kind')
        run = None
        if actor == 'worker':
            with contextlib.closing(self.store.connect()) as db:
                run = db.execute('SELECT * FROM runs WHERE id=?',
                                 (str(intent.get('worker') or ''),)).fetchone()
            if not run or run['state'] not in WORKER_RUN_STATES:
                return _result('INVALID_CONTEXT', 'worker-not-active',
                               'The worker identity is not a live run')
            if job_id and str(run['job_id']) != str(job_id):
                return _result('INVALID_CONTEXT', 'worker-mismatch',
                               'The worker belongs to another job')
            if milestone_id and str(run['milestone_id']) != str(milestone_id):
                return _result('INVALID_CONTEXT', 'worker-milestone-mismatch',
                               'The worker belongs to another milestone')
        job = None
        if job_id:
            try:
                job = self.store.get(str(job_id))
            except KeyError:
                return _result('INVALID_CONTEXT', 'job-unknown', 'Unknown job')
            if milestone_id and str(milestone_id) not in (job.get('milestones') or {}):
                return _result('INVALID_CONTEXT', 'milestone-unknown', 'Unknown milestone')
        project_id = intent.get('project') or (job or {}).get('contract', {}).get('project_id')
        # 3. Locked guardrails (shared predicates; ids from the locked rule set).
        if kind in BLOCKED_KINDS:
            return _result('DENY', BLOCKED_KINDS[kind], 'Locked guardrail: ' + BLOCKED_KINDS[kind])
        if kind in ('write', 'repo', 'destructive'):
            if guardrails.frozen_path(target):
                return _result('DENY', 'frozen-immutable',
                               'Frozen releases and their manifests are read-only')
            if guardrails.system_path(target):
                return _result('DENY', 'system-path', 'System locations are outside every Kel project')
        if kind in ('write', 'repo', 'destructive', 'browser') and not target.strip():
            return _result('DENY', 'target-required', 'An effect needs an explicit target')
        if kind in ('tool', 'external') and not (tool.strip() or target.strip()):
            return _result('DENY', 'target-required', 'An effect needs an explicit target')
        if kind == 'destructive' and not str(intent.get('snapshot_ref') or '').strip():
            return _result('DENY', 'destructive-snapshot',
                           'A snapshot or backup reference is required before a destructive action')
        # 3b. Creating a new project folder from the user's explicit request is a user-actor effect
        #     confined to the Kel Projects root (guardrail checks above already applied).
        meta = intent.get('metadata') or {}
        if (actor == 'user' and kind == 'write'
                and str(meta.get('operation') or '') == 'create-project'):
            allowed_root = project_creation_root()
            try:
                probe = Path(target).resolve()
            except OSError:
                probe = None
            if probe is None or not probe.is_relative_to(allowed_root):
                return _result('DENY', 'project-create-scope',
                               'New projects are created only under the Kel Projects folder')
            return _result('ALLOW', 'user-project-create',
                           'An explicit user request creates a new project folder')
        # 3c. Conversation capability controls (docs/session-tools/): this conversation may narrow
        #     what runs here, and may enable a capability that is available and not globally denied.
        #     It never overrides the locked guardrails above, never invents availability, and never
        #     replaces the lease or approval gates below.
        capability = str(intent.get('capability') or '')
        if capability and kind in EFFECT_KINDS:
            from .capabilities import resolve
            # An effect spends a one-shot grant exactly once; a pre-flight check (consume=False)
            # sees the same grant without spending it.
            control = resolve(self.store, capability,
                              conversation=intent.get('conversation'), job=intent.get('job'),
                              consume=bool(intent.get('consume', True)))
            if not control.get('allowed'):
                return _result('DENY', control.get('rule') or 'capability-off', control.get('reason') or '')
        # 4. Role tool policy narrows; it can never broaden the lease or the guardrails.
        role = intent.get('role')
        if role and tool:
            snapshot = intent.get('role_tool_policy')
            if isinstance(snapshot, dict):
                # A frozen assignment snapshot governs: role edits never rewrite a run's policy.
                allowed = (tool in (snapshot.get('allow') or [])
                           and tool not in (snapshot.get('deny') or []))
            else:
                from .team import Team
                try:
                    allowed = Team(self.store).tool_allowed(str(role), tool, project_id or '',
                                                            str(intent.get('task') or ''))
                except PolicyError:
                    return _result('DENY', 'role-unknown', 'Unknown role for this action')
            if not allowed:
                return _result('DENY', 'role-policy',
                               'Role %s does not allow tool %s' % (role, tool))
        # 5. Destructive actions additionally require an explicit approved approval.
        if kind == 'destructive':
            approval_id = intent.get('approval_id')
            if not self._approval_ok(approval_id, intent):
                return _result('REQUIRES_USER_APPROVAL', 'destructive-approval',
                               'This destructive action needs explicit user approval',
                               approval_id=approval_id)
        # 6. Capability lease: state, expiry, and scope, in the single shared implementation.
        if kind in EFFECT_KINDS:
            lease = None
            if intent.get('lease_id'):
                lease = self._lease_by_id(str(intent['lease_id']))
                if lease and job_id and str(lease['job_id']) != str(job_id):
                    return _result('INVALID_CONTEXT', 'lease-mismatch',
                                   'The lease belongs to another job')
            elif job_id:
                lease = self.autonomy.latest_lease(str(job_id))
            if not lease:
                return _result('DENY', 'lease-required', 'No capability lease covers this action')
            if lease['state'] == 'REVOKED':
                return _result('REVOKED_LEASE', 'lease-revoked',
                               'Lease was revoked: ' + str(lease.get('reason') or 'no reason recorded'),
                               lease_id=lease['lease_id'])
            if lease['expires_at'] <= time.time():
                return _result('EXPIRED_LEASE', 'lease-expired',
                               'Lease expired at %s' % lease['expires_at'], lease_id=lease['lease_id'])
            check = self.autonomy.check(lease['lease_id'], kind, target, tool,
                                        destructive_snapshot=str(intent.get('snapshot_ref') or ''),
                                        consume=bool(intent.get('consume', True)))
            if check.get('allowed'):
                return _result('ALLOW', 'lease-scope', check.get('reason', ''),
                               lease_id=lease['lease_id'], scope=check.get('scope'))
            rule = str(check.get('rule') or '')
            if rule in ('lease-expired', 'lease-revoked'):
                outcome = 'EXPIRED_LEASE' if rule == 'lease-expired' else 'REVOKED_LEASE'
                return _result(outcome, rule, check.get('reason') or '', lease_id=lease['lease_id'])
            if rule == 'lease-scope':
                return self._expansion(intent, lease, kind, tool, target)
            return _result('DENY', rule or 'lease-denied',
                           check.get('reason') or 'Denied by lease policy',
                           lease_id=lease['lease_id'])
        return _result('ALLOW', 'no-effect', 'Read-only intent is not an effect')

    def _lease_by_id(self, lease_id):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM capability_leases WHERE lease_id=?',
                             (lease_id,)).fetchone()
        return dict(row) if row else None

    def _approval_ok(self, approval_id, intent):
        """A destructive action is approved only by a matching APPROVED approval row.

        APPROVAL-EXACT (Round 2.5 R4): the row must still be inside its approval window, carry the
        digest of the exact action the caller is about to perform, and belong to the same job. A
        resolution that happened before the window closed does not authorize a *later* execution
        outside that window.
        """
        action = (intent.get('metadata') or {}).get('action')
        if not approval_id or action is None:
            return False
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM approvals WHERE id=?', (str(approval_id),)).fetchone()
        if not row or row['status'] != 'APPROVED' or row['action_digest'] != digest(action):
            return False
        if row['expires'] is not None and float(row['expires']) < time.time():
            return False  # the approval window closed before this execution
        if intent.get('job') and str(row['job_id']) != str(intent.get('job')):
            return False  # an approval for another job is not this job's approval
        return True

    def _expansion(self, intent, lease, kind, tool, target):
        """Outside the leased scope: reuse a pending request, honor a denial, or ask once."""
        scope = KIND_SCOPE.get(kind, 'root')
        value = (tool or target) if kind in ('tool', 'external') else target
        with contextlib.closing(self.store.connect()) as db:
            prior = [dict(r) for r in db.execute(
                'SELECT * FROM boundary_expansion_requests WHERE lease_id=? AND scope=? AND target=?'
                ' ORDER BY created DESC', (lease['lease_id'], scope, value))]
        pending = [r for r in prior if r['status'] == 'PENDING']
        if pending:
            return _result('REQUIRES_BOUNDARY_EXPANSION', 'lease-scope',
                           'Outside the leased scope; a boundary request is already waiting for you',
                           lease_id=lease['lease_id'],
                           boundary_request_id=pending[0]['request_id'])
        denied = [r for r in prior if r['status'] == 'DENIED']
        if denied:
            return _result('DENY', 'boundary-denied',
                           'You denied this boundary request; Kel will not re-ask for it',
                           lease_id=lease['lease_id'],
                           boundary_request_id=denied[0]['request_id'])
        meta = intent.get('metadata') or {}
        try:
            created = self.autonomy.request_expansion(
                lease['lease_id'], scope, str(value),
                what=str(meta.get('what') or 'work outside the folder Kel is allowed to use'),
                why=str(meta.get('why') or 'this task needs it to keep going'),
                benefit=str(meta.get('benefit') or ''), fallback=str(meta.get('fallback') or ''),
                risk=str(meta.get('risk') or ''))
        except PolicyError as exc:
            return _result('DENY', 'lease-scope', str(exc), lease_id=lease['lease_id'])
        return _result('REQUIRES_BOUNDARY_EXPANSION', 'lease-scope',
                       'Outside the leased scope; Kel recorded a boundary request for you',
                       lease_id=lease['lease_id'],
                       boundary_request_id=created['request_id'])

    # ---- durable record ------------------------------------------------------
    def _record(self, intent, decision):
        """One inspectable record per distinct decision inside the dedupe window."""
        actor = str(intent.get('actor') or '')
        kind = str(intent.get('action_kind') or '')
        tool = str(intent.get('tool') or '')
        target = str(intent.get('target') or '')
        evidence = encode(intent.get('evidence')) if intent.get('evidence') else None
        with self.store.transaction() as db:
            row = db.execute(
                "SELECT decision_id FROM guardrail_decisions WHERE "
                "IFNULL(job_id,'')=IFNULL(?,'') AND IFNULL(milestone_id,'')=IFNULL(?,'') AND "
                "IFNULL(worker_id,'')=IFNULL(?,'') AND action_kind=? AND IFNULL(tool,'')=IFNULL(?,'')"
                " AND IFNULL(target,'')=IFNULL(?,'') AND decision=? AND IFNULL(rule,'')=IFNULL(?,'')"
                " AND at>?",
                (str(intent.get('job') or ''), str(intent.get('milestone') or ''),
                 str(intent.get('worker') or ''), kind, tool, target, decision['outcome'],
                 decision.get('rule'), time.time() - DEDUPE_SECONDS)).fetchone()
            if row:
                return row['decision_id']
            decision_id = uid()
            db.execute('INSERT INTO guardrail_decisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (decision_id, time.time(), actor, str(intent.get('worker') or '') or None,
                        str(intent.get('role') or '') or None,
                        str(intent.get('project') or '') or None,
                        str(intent.get('job') or '') or None,
                        str(intent.get('milestone') or '') or None,
                        decision.get('lease_id'),
                        kind, tool or None, target or None, decision['outcome'],
                        decision.get('rule'), decision.get('reason'),
                        POLICY_VERSION, guardrails.DIGEST,
                        decision.get('boundary_request_id'), decision.get('approval_id'),
                        evidence))
            return decision_id


def authorize(store, intent, record=True):
    """The single entry point every effect-capable path calls before acting."""
    return Authorizer(store).decide(intent, record=record)


def decisions(store, job_id=None, limit=50):
    """Recent authorization decisions for diagnostics and after-the-fact inspection."""
    ensure_schema(store)
    limit = max(1, min(int(limit or 50), 200))
    with contextlib.closing(store.connect()) as db:
        if job_id:
            rows = db.execute('SELECT * FROM guardrail_decisions WHERE job_id=? '
                              'ORDER BY at DESC LIMIT ?', (str(job_id), limit)).fetchall()
        else:
            rows = db.execute('SELECT * FROM guardrail_decisions ORDER BY at DESC LIMIT ?',
                              (limit,)).fetchall()
    return [dict(r) for r in rows]


def ensure_job_lease(store, job):
    """Return (lease_id, None) when an execution lease is available, or (None, decision).

    Kel issues and renews its own execution leases for effect-capable jobs, bound to the compiled
    contract digest. An expiry is renewed; a lease revoked for a system reason (emergency stop the
    user has resumed past, or a revised contract) is renewed with a recorded decision. A targeted
    revoke is never silently undone.
    """
    contract = job.get('contract') or {}
    autonomy = Autonomy(store)
    latest = autonomy.latest_lease(job['id'])
    now = time.time()
    if latest and latest['state'] == 'ACTIVE' and latest['expires_at'] > now:
        return latest['lease_id'], None
    if latest and latest['state'] == 'REVOKED':
        reason = str(latest.get('reason') or '')
        if not (reason in REISSUE_REASONS and job.get('state') == 'READY'):
            return None, _result('REVOKED_LEASE', 'lease-revoked',
                                 'Lease was revoked: ' + (reason or 'no reason recorded'))
    root = contract.get('root')
    if not root:
        return None, _result('INVALID_CONTEXT', 'root-missing',
                             'This job has no project root to lease')
    try:
        issued = autonomy.issue(job['id'], project_id=contract.get('project_id', 'default'),
                                profile='kel-job', review_ref='kel-contract:' + digest(contract),
                                roots=[str(root)], repositories=[str(root)],
                                tools=('git', 'run_tests'))
    except PolicyError as exc:
        return None, _result('DENY', 'lease-ineligible', exc)
    return issued['lease_id'], None


def block_job(store, job_id, milestone_id, decision):
    """Pause a job for authorization, once, with a visible reason and a linked request."""
    with store.transaction() as db:
        job = store._get(db, job_id)
        if job['state'] in ('CLOSED', 'CANCELLED', 'CANCELLING', 'PAUSED', 'PAUSING'):
            return False
        marker = {'milestone': milestone_id, 'outcome': decision.get('outcome'),
                  'rule': decision.get('rule'), 'request': decision.get('boundary_request_id'),
                  'reason': decision.get('reason')}
        active = db.execute("SELECT count(*) FROM runs WHERE job_id=? AND state IN "
                            "('RUNNING','WAITING_APPROVAL','CANCEL_REQUESTED')",
                            (job_id,)).fetchone()[0]
        unchanged = job.get('authz') == marker
        if unchanged and (active or job['state'] == 'AWAITING_USER'):
            return False  # already announced for this exact block; never repeat the message
        from .chat_approvals import plain_block_reason, record_announcement
        plain = plain_block_reason(decision)
        if decision.get('outcome') == 'REQUIRES_BOUNDARY_EXPANSION':
            message = ('Kel needs your permission to continue: ' + plain +
                       ' You can decide right in this chat.')
        elif decision.get('outcome') == 'REQUIRES_USER_APPROVAL':
            message = 'Kel needs your approval before it continues: ' + plain
        else:
            message = 'Kel cannot continue this step: ' + plain
        m = (job.get('milestones') or {}).get(milestone_id)
        if m is not None and m.get('state') != 'RUNNING':
            m['error'] = message
        job['authz'] = marker
        if not active:
            job['state'] = 'AWAITING_USER'
        store._save(db, job, 'authorization.blocked',
                    {'outcome': decision.get('outcome'), 'rule': decision.get('rule'),
                     'request': decision.get('boundary_request_id')})
        if not unchanged:
            cur = db.execute('INSERT INTO messages(conversation_id,role,text,job_id,at) VALUES(?,?,?,?,?)',
                             (job['conversation'], 'assistant', message, job_id, time.time()))
            # Chat renders the decision card in place of this message; the link is
            # written with the message so it can never point at nothing.
            if decision.get('boundary_request_id'):
                record_announcement(db, job['conversation'], 'access',
                                    decision['boundary_request_id'], cur.lastrowid)
        return True


def resume_after_grant(store, request_id):
    """After a boundary grant resolves, wake exactly the job that was waiting on it."""
    with store.transaction() as db:
        req = db.execute('SELECT * FROM boundary_expansion_requests WHERE request_id=?',
                         (str(request_id),)).fetchone()
        if not req or req['status'] != 'GRANTED':
            return False
        lease = db.execute('SELECT * FROM capability_leases WHERE lease_id=?',
                           (req['lease_id'],)).fetchone()
        if not lease:
            return False
        row = db.execute('SELECT data FROM jobs WHERE id=?', (lease['job_id'],)).fetchone()
        if not row:
            return False
        job = json.loads(row['data'])
        authz = job.get('authz') or {}
        if str(authz.get('request') or '') != str(request_id) or job['state'] != 'AWAITING_USER':
            return False
        job['state'] = 'READY'
        job['authz'] = None
        m = (job.get('milestones') or {}).get(str(authz.get('milestone') or ''))
        if m is not None and m.get('error'):
            m['error'] = None
        store._save(db, job, 'authorization.granted', {'request_id': request_id})
        db.execute('INSERT INTO messages(conversation_id,role,text,job_id,at) VALUES(?,?,?,?,?)',
                   (job['conversation'], 'assistant',
                    'Permission granted; Kel is continuing the paused work.', job['id'], time.time()))
        return True
