"""First-class continuation (V1.3 migration 003): resume durable work across conversations.

Durable job/milestone/run state is the source of truth; conversation text may filter or rank
candidates but never reconstructs work. See docs/v1.3/KEL_V1.3_CONTINUATION_SPEC.md.
"""
import contextlib
import json
import re
import time
from pathlib import Path

from .core import PolicyError
from .memory import _backup, _is_fresh_database, _table

MIGRATION_VERSION = 3
MIGRATION_NAME = 'v13-continuation'

DDL = """
CREATE TABLE IF NOT EXISTS job_links(
    conversation_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    created REAL NOT NULL,
    reason TEXT,
    PRIMARY KEY(conversation_id, job_id));
"""

CONTINUABLE_STATES = ('READY', 'PAUSED', 'WAITING_RESOURCE', 'AWAITING_USER')
STATUS_ONLY_STATES = ('RUNNING', 'CANCELLING')
OPEN_MILESTONE_STATES = ('READY', 'NEEDS_REPAIR', 'UNCERTAIN', 'INVALIDATED', 'EXHAUSTED')
STATE_PRIORITY = {'AWAITING_USER': 0, 'PAUSED': 1, 'WAITING_RESOURCE': 2, 'READY': 3}
SESSION_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{7,200}$')


def ensure_schema(store):
    """Create migration 003 tables (idempotent; a v1.2 database is backed up once)."""
    with contextlib.closing(store.connect()) as db:
        if _table(db, 'schema_migrations') and db.execute(
                'SELECT 1 FROM schema_migrations WHERE version=?', (MIGRATION_VERSION,)).fetchone():
            return
        first = not _table(db, 'schema_migrations')
        if first:
            if not _is_fresh_database(db):
                _backup(store, db)  # one-time pre-V1.3 backup before the first V1.3 mutation
            db.execute('CREATE TABLE IF NOT EXISTS schema_migrations('
                       'version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL,'
                       ' note TEXT)')
        db.executescript(DDL)
        db.execute('INSERT OR IGNORE INTO schema_migrations VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(), None))


def valid_session_id(value):
    """Shape check for native provider session ids (exact-session discipline)."""
    return isinstance(value, str) and bool(SESSION_RE.match(value.strip()))


def _tokens(text):
    return set(re.findall(r'[a-z0-9]{4,}', str(text or '').lower()))


class Continuation:
    def __init__(self, store):
        self.store = store
        ensure_schema(store)

    def _conversations(self, db, project_id):
        return {r['id'] for r in db.execute(
            'SELECT id FROM conversations WHERE project_id=?', (project_id,))}

    def candidates(self, project_id):
        """Project-scoped continuation candidates derived from durable state only."""
        with contextlib.closing(self.store.connect()) as db:
            conversations = self._conversations(db, project_id)
            if not conversations:
                raise PolicyError('Project missing')
            links = {}
            for row in db.execute('SELECT conversation_id, job_id FROM job_links'):
                if row['conversation_id'] in conversations:
                    links.setdefault(row['job_id'], set()).add(row['conversation_id'])
            out = []
            for row in db.execute('SELECT data FROM jobs ORDER BY rowid DESC LIMIT 200'):
                job = json.loads(row['data'])
                if job.get('conversation') not in conversations and job['id'] not in links:
                    continue
                state = job.get('state')
                verdict = job.get('verdict')
                milestones = job.get('milestones') or {}
                openn = [mid for mid, m in milestones.items()
                         if m.get('state') in OPEN_MILESTONE_STATES and m.get('attempts', 0) < 4]
                eligible = state in CONTINUABLE_STATES or state in STATUS_ONLY_STATES or \
                    (state == 'CLOSED' and verdict in ('FAILED', 'UNCERTAIN') and openn) or \
                    (state == 'CANCELLED' and openn)
                if not eligible:
                    continue
                request = str((job.get('contract') or {}).get('request', ''))
                last = db.execute('SELECT MAX(at) FROM events WHERE aggregate_id=?',
                                  (job['id'],)).fetchone()[0]
                out.append({
                    'job_id': job['id'],
                    'title': request[:80],
                    'state': state,
                    'verdict': verdict,
                    'accepted': sum(1 for m in milestones.values()
                                    if m.get('state') == 'ACCEPTED'),
                    'total': len(milestones),
                    'open': openn,
                    'conversation': job.get('conversation'),
                    'linked': sorted(links.get(job['id'], ())),
                    'last_event_at': last or job.get('created', 0.0),
                })
        return out

    def resolve(self, project_id, conversation_id, text=None):
        """Exactly one obvious candidate -> single; several plausible -> choice; none -> none."""
        rows = self.candidates(project_id)
        rows = [c for c in rows if c['state'] in CONTINUABLE_STATES or
                (c['state'] == 'CLOSED' and c['open'])]
        if not rows:
            return {'kind': 'none', 'candidates': []}
        tokens = _tokens(text)
        for c in rows:
            c['link'] = conversation_id in c['linked'] or c['conversation'] == conversation_id
            c['match'] = len(tokens & _tokens(c['title'])) if tokens else 0

        def key(c):
            return (-c['match'], 0 if c['link'] else 1, STATE_PRIORITY.get(c['state'], 8),
                    -c['accepted'], -c['last_event_at'])

        ranked = sorted(rows, key=key)
        if tokens:
            matching = [c for c in ranked if c['match'] > 0]
            if matching:
                ranked = matching
        top = ranked[0]
        if len(ranked) == 1:
            return {'kind': 'single', 'candidate': top, 'candidates': ranked}
        if top['link'] and key(top) < key(ranked[1]):
            return {'kind': 'single', 'candidate': top, 'candidates': ranked}
        return {'kind': 'choice', 'candidates': ranked[:3]}
    def attach(self, job_id, conversation_id, *, kind='continuation', reason=''):
        """Idempotent conversation-to-job link (origin | continuation)."""
        if kind not in ('origin', 'continuation'):
            raise PolicyError('Unknown link kind')
        with self.store.transaction() as db:
            if not db.execute('SELECT 1 FROM conversations WHERE id=?',
                              (conversation_id,)).fetchone():
                raise PolicyError('Conversation missing')
            if not db.execute('SELECT 1 FROM jobs WHERE id=?', (job_id,)).fetchone():
                raise PolicyError('Job missing')
            cur = db.execute('INSERT OR IGNORE INTO job_links VALUES(?,?,?,?,?)',
                             (conversation_id, job_id, kind, time.time(), str(reason)[:300]))
            return cur.rowcount == 1

    def links(self, job_id):
        with contextlib.closing(self.store.connect()) as db:
            return [dict(r) for r in db.execute(
                'SELECT * FROM job_links WHERE job_id=? ORDER BY created', (job_id,))]

    def plan_resume(self, job_id):
        """What resumes, what stays accepted, what must be revalidated (with reasons)."""
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT data FROM jobs WHERE id=?', (job_id,)).fetchone()
            session_row = db.execute(
                'SELECT provider, model, native_session FROM runs'
                ' WHERE job_id=? AND native_session IS NOT NULL ORDER BY rowid DESC LIMIT 1',
                (job_id,)).fetchone()
        if not row:
            raise PolicyError('Job missing')
        job = json.loads(row['data'])
        milestones = job.get('milestones') or {}
        contract = job.get('contract') or {}
        preserve, reopen, revalidate = [], [], []
        root = contract.get('root')
        current = None
        if root and Path(root).is_dir():
            from .projectmap import fingerprint
            current = fingerprint(Path(root))
        stored = contract.get('source_digest')
        source_changed = bool(stored and current and stored != current)
        for mid, milestone in milestones.items():
            state = milestone.get('state')
            if state == 'ACCEPTED':
                if source_changed:
                    revalidate.append({'id': mid,
                                       'reason': 'source changed since %s' % str(stored)[:24]})
                elif not stored and contract.get('kind') == 'coding':
                    try:
                        from .coding import check_evidence
                        verdict = check_evidence(self.store,
                                                 (milestone.get('artifact') or {}).get('run_id'))
                    except Exception:
                        verdict = 'UNCERTAIN'
                    if verdict == 'VERIFIED':
                        preserve.append(mid)
                    else:
                        revalidate.append({'id': mid, 'reason': 'evidence no longer reproducible'})
                else:
                    preserve.append(mid)
            elif state in OPEN_MILESTONE_STATES and milestone.get('attempts', 0) < 4:
                reopen.append(mid)
        session = {'valid': False, 'reason': 'no stored native session'}
        if session_row and session_row['native_session']:
            value = str(session_row['native_session'])
            if valid_session_id(value):
                session = {'valid': True, 'provider': session_row['provider'],
                           'model': session_row['model'], 'native_session': value}
            else:
                session = {'valid': False, 'reason': 'malformed native session id'}
        return {'job_id': job_id, 'preserve': preserve, 'reopen': reopen,
                'revalidate': revalidate, 'session': session,
                'source_digest': stored, 'current_digest': current}
    def execute_resume(self, job_id, conversation_id, *, reason='user continuation'):
        """Attach + route by state + apply revalidation, then the engine claims the work."""
        plan = self.plan_resume(job_id)
        for item in plan['revalidate']:
            self.store.invalidate_milestone(job_id, item['id'], item['reason'])
        job = self.store.get(job_id)
        state = job['state']
        if state == 'PAUSED':
            self.store.control(job_id, 'resume')
        elif state == 'WAITING_RESOURCE' and job.get('route_block'):
            # A routing block clears itself as soon as a worker is available; the person asking
            # early just stops the waiting.
            self.store.retry_route(job_id)
        elif state in ('WAITING_RESOURCE', 'CLOSED'):
            # WAITING_RESOURCE without a route_block is an interrupted run: the engine fenced its
            # milestone and will not replay it on its own. Reaching here *is* the person's
            # decision, so the fenced milestone is re-armed for a fresh attempt.
            self.store.reopen(job_id, reason=reason)
        created = self.attach(job_id, conversation_id, reason=reason)
        final = self.store.get(job_id)
        return {'job_id': job_id, 'attached': True, 'link_created': created,
                'state': final['state'], 'plan': plan}

    def explain(self, job_id):
        """User-readable resume summary derived from persisted state only."""
        job = self.store.get(job_id)
        milestones = job.get('milestones') or {}
        accepted = [mid for mid, m in milestones.items() if m.get('state') == 'ACCEPTED']
        remaining = [mid for mid, m in milestones.items()
                     if m.get('state') in OPEN_MILESTONE_STATES and m.get('attempts', 0) < 4]
        title = str((job.get('contract') or {}).get('request', ''))[:80]
        return ('Continuing "%s": %d/%d milestones already accepted; resuming %d open '
                'milestone(s).' % (title or job['id'], len(accepted), len(milestones),
                                   len(remaining)))

    def resume_brief(self, job_id):
        """The plain-words brief the Work surface shows (V2-11): shipped, open, why, next.

        Derived from persisted state only — the plan, the milestones, and the error the fence
        wrote. Nothing here re-runs work or guesses: a fenced job says so and says that
        continuing is the person's decision. `needs_you` is true only when no automatic step can
        move the job forward.
        """
        job = self.store.get(job_id)
        plan = self.plan_resume(job_id)
        milestones = job.get('milestones') or {}
        title = str((job.get('contract') or {}).get('request', ''))[:120]
        shipped = [{'id': mid, 'filename': (m.get('artifact') or {}).get('filename')}
                   for mid, m in sorted(milestones.items())
                   if m.get('state') == 'ACCEPTED']
        opens = [{'id': mid, 'state': m.get('state'), 'attempts': m.get('attempts'),
                  'error': m.get('error')}
                 for mid, m in sorted(milestones.items())
                 if m.get('state') in OPEN_MILESTONE_STATES and (m.get('attempts') or 0) < 4]
        fenced = any('requires reconciliation' in str(m.get('error') or '')
                     for m in milestones.values())
        state = job.get('state')
        if state == 'CLOSED' and job.get('verdict') == 'VERIFIED':
            why, nxt, needs = 'Done and verified.', 'Nothing needed — ask for a new change for more work.', False
        elif fenced:
            why = ('An attempt was interrupted and fenced; Kel will not replay it on its own, and '
                   'the file-changing steps were not repeated.')
            nxt = 'Say "continue" to re-arm it as a fresh attempt.'
            needs = True
        elif job.get('route_block'):
            why = 'No model was free: ' + str(job['route_block'])[:160]
            nxt = 'Kel retries automatically as soon as a capable model is healthy.'
            needs = False
        elif state in ('PAUSED', 'PAUSING'):
            why, nxt, needs = 'Paused at your request.', 'Say "continue" to resume it.', True
        elif state == 'AWAITING_USER':
            why = 'Waiting for your decision on a gated step.'
            nxt = 'Decide on the request card in this conversation — or in Work context.'
            needs = True
        elif any(m.get('state') == 'RUNNING' for m in milestones.values()):
            why, nxt, needs = 'Kel is working on it now.', 'Nothing needed right now.', False
        else:
            why, nxt, needs = ('Queued; Kel has not claimed it yet.',
                               'Nothing needed right now.', False)
        return {'job_id': job_id, 'title': title or job_id, 'state': state,
                'verdict': job.get('verdict'), 'shipped': shipped, 'open': opens,
                'fenced': fenced, 'session': plan['session'], 'why': why, 'next': nxt,
                'needs_you': needs}
