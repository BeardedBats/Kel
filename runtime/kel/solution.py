"""Solution quality: briefs, options, comparisons, capability opportunities, reviews
(V1.4 migration 005).

The Best Solution Gate persists the comparison that justifies consequential work
(docs/v1.4/KEL_V1.4_ARCHITECTURE.md §3). Approval requires recorded options, an
existing-solution search, a recommendation carrying evidence-to-switch and a rollback, and an
independent review; self-certification is refused.
"""
import contextlib
import json
import time

from .core import PolicyError, digest, encode, uid
from .memory import _backup, _is_fresh_database, _table

MIGRATION_VERSION = 5
MIGRATION_NAME = 'v14-solution'

DDL = """
CREATE TABLE IF NOT EXISTS solution_briefs(
  brief_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, conversation_id TEXT, job_id TEXT,
  goal TEXT NOT NULL, state TEXT NOT NULL, chosen_option TEXT, author TEXT NOT NULL,
  data TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS solution_options(
  brief_id TEXT NOT NULL, option_id TEXT NOT NULL, digest TEXT NOT NULL, data TEXT NOT NULL,
  created REAL NOT NULL, PRIMARY KEY(brief_id, option_id));
CREATE TABLE IF NOT EXISTS option_comparisons(
  brief_id TEXT NOT NULL, criterion TEXT NOT NULL, option_id TEXT NOT NULL, score INTEGER NOT NULL,
  note TEXT, PRIMARY KEY(brief_id, criterion, option_id));
CREATE TABLE IF NOT EXISTS capability_opportunities(
  op_id TEXT PRIMARY KEY, brief_id TEXT NOT NULL, classification TEXT NOT NULL, data TEXT NOT NULL,
  created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS solution_reviews(
  review_id TEXT PRIMARY KEY, brief_id TEXT NOT NULL, reviewer_id TEXT NOT NULL,
  verdict TEXT NOT NULL, findings TEXT NOT NULL, resolved INTEGER NOT NULL DEFAULT 0,
  created REAL NOT NULL);
"""

OPTION_KINDS = ('implement', 'reuse', 'donor', 'configure', 'defer', 'manual')
OPPORTUNITY_CLASSES = ('PROCEED', 'ASK_ONCE', 'PAUSE')
IDEA_VERDICTS = ('BETTER', 'BETTER_LATER', 'EQUIVALENT', 'WORSE', 'NEEDS_EVIDENCE', 'USER_MANDATE')
WORKAROUND_TYPES = ('permanent', 'temporary', 'mitigation')
REVIEW_VERDICTS = ('OPTIMAL_ENOUGH', 'CHALLENGE', 'BLOCK')
BRIEF_STATES = ('OPEN', 'RECOMMENDED', 'APPROVED')
SEARCH_VERDICTS = ('reuse', 'adapt', 'build', 'none')


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
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(), 'best-solution-gate'))
        return True


def _text(value, name, limit=4000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise PolicyError('%s must be 1 to %d characters' % (name, limit))
    return value.strip()


class SolutionBriefs:
    """One persisted comparison record per consequential decision (docs/v1.4 §6)."""

    def __init__(self, store):
        self.store = store
        ensure_schema(store)

    # ---- reads -----------------------------------------------------------------
    def _row(self, db, brief_id):
        row = db.execute('SELECT * FROM solution_briefs WHERE brief_id=?', (brief_id,)).fetchone()
        if not row:
            raise PolicyError('Solution brief not found')
        return row

    def get(self, brief_id):
        with contextlib.closing(self.store.connect()) as db:
            row = self._row(db, brief_id)
            data = json.loads(row['data'])
            options = [dict(option_id=r['option_id'], digest=r['digest'], **json.loads(r['data']))
                       for r in db.execute('SELECT * FROM solution_options WHERE brief_id=?'
                                           ' ORDER BY created', (brief_id,))]
            comparisons = [dict(r) for r in db.execute(
                'SELECT criterion, option_id, score, note FROM option_comparisons'
                ' WHERE brief_id=? ORDER BY criterion', (brief_id,))]
            opportunities = [dict(op_id=r['op_id'], classification=r['classification'],
                                  **json.loads(r['data']))
                             for r in db.execute('SELECT * FROM capability_opportunities'
                                                 ' WHERE brief_id=? ORDER BY created', (brief_id,))]
            reviews = [dict(review_id=r['review_id'], reviewer_id=r['reviewer_id'],
                            verdict=r['verdict'], findings=r['findings'],
                            resolved=bool(r['resolved']), created=r['created'])
                       for r in db.execute('SELECT * FROM solution_reviews WHERE brief_id=?'
                                           ' ORDER BY created', (brief_id,))]
        return {'brief_id': row['brief_id'], 'project_id': row['project_id'],
                'conversation_id': row['conversation_id'], 'job_id': row['job_id'],
                'goal': row['goal'], 'state': row['state'], 'chosen_option': row['chosen_option'],
                'author': row['author'], 'created': row['created'], 'updated': row['updated'],
                'data': data, 'options': options, 'comparisons': comparisons,
                'opportunities': opportunities, 'reviews': reviews}

    def list(self, project_id):
        with contextlib.closing(self.store.connect()) as db:
            return [dict(brief_id=r['brief_id'], goal=r['goal'], state=r['state'],
                         chosen_option=r['chosen_option'], updated=r['updated'])
                    for r in db.execute('SELECT * FROM solution_briefs WHERE project_id=?'
                                        ' ORDER BY updated DESC', (project_id,))]

    # ---- writes ----------------------------------------------------------------
    def open_brief(self, project_id, goal, conversation_id='main', job_id=None, author='kel'):
        goal = _text(goal, 'Goal', 2000)
        brief_id = uid()
        now = time.time()
        data = {'request': '', 'assumptions': [], 'verified_constraints': [],
                'unverified_constraints': [], 'search': [], 'missing_access': [],
                'criteria': [], 'recommendation': None, 'rejected': [], 'evidence_to_switch': '',
                'rollback': '', 'workaround_type': None, 'wrong_layer': None,
                'rework_forecast': ''}
        with self.store.transaction() as db:
            db.execute('INSERT INTO solution_briefs VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (brief_id, project_id, conversation_id, job_id, goal, 'OPEN', None, author,
                        encode(data), now, now))
        return brief_id

    def update(self, brief_id, **fields):
        allowed = {'request', 'assumptions', 'verified_constraints', 'unverified_constraints',
                   'missing_access', 'criteria', 'rework_forecast', 'staffing'}
        unknown = set(fields) - allowed
        if unknown:
            raise PolicyError('Unknown brief field(s): %s' % ', '.join(sorted(unknown)))
        with self.store.transaction() as db:
            row = self._row(db, brief_id)
            data = json.loads(row['data'])
            for key, value in fields.items():
                if key in ('assumptions', 'verified_constraints', 'unverified_constraints',
                           'missing_access', 'criteria') and not isinstance(value, list):
                    raise PolicyError('%s must be a list' % key)
                data[key] = value
            db.execute('UPDATE solution_briefs SET data=?, updated=? WHERE brief_id=?',
                       (encode(data), time.time(), brief_id))
        return self.get(brief_id)

    def add_option(self, brief_id, option_id, title, summary, kind, source='',
                   tradeoffs=(), evidence=(), cost='', complexity=None, reversible=None):
        option_id = _text(option_id, 'Option id', 120)
        title = _text(title, 'Title', 200)
        summary = _text(summary, 'Summary', 2000)
        if kind not in OPTION_KINDS:
            raise PolicyError('Option kind must be one of %s' % ', '.join(OPTION_KINDS))
        if cost not in ('', 'low', 'medium', 'high'):
            raise PolicyError('Cost must be low, medium, or high')
        if complexity is not None and (not isinstance(complexity, int) or not 1 <= complexity <= 5):
            raise PolicyError('Complexity must be 1 to 5')
        payload = {'title': title, 'summary': summary, 'kind': kind, 'source': source,
                   'tradeoffs': list(tradeoffs), 'evidence': list(evidence), 'cost': cost,
                   'complexity': complexity, 'reversible': reversible}
        with self.store.transaction() as db:
            self._row(db, brief_id)
            if db.execute('SELECT 1 FROM solution_options WHERE brief_id=? AND option_id=?',
                          (brief_id, option_id)).fetchone():
                raise PolicyError('Option id already exists in this brief')
            db.execute('INSERT INTO solution_options VALUES(?,?,?,?,?)',
                       (brief_id, option_id, digest(payload), encode(payload), time.time()))
            db.execute('UPDATE solution_briefs SET updated=? WHERE brief_id=?',
                       (time.time(), brief_id))
        return option_id

    def compare(self, brief_id, criterion, option_id, score, note=''):
        criterion = _text(criterion, 'Criterion', 120)
        if not isinstance(score, int) or not 0 <= score <= 5:
            raise PolicyError('Score must be an integer 0 to 5')
        with self.store.transaction() as db:
            self._row(db, brief_id)
            if not db.execute('SELECT 1 FROM solution_options WHERE brief_id=? AND option_id=?',
                              (brief_id, option_id)).fetchone():
                raise PolicyError('Compare against a recorded option')
            db.execute('INSERT INTO option_comparisons VALUES(?,?,?,?,?)'
                       ' ON CONFLICT(brief_id,criterion,option_id) DO UPDATE SET score=excluded.score,'
                       ' note=excluded.note', (brief_id, criterion, option_id, score, note))
            db.execute('UPDATE solution_briefs SET updated=? WHERE brief_id=?',
                       (time.time(), brief_id))
        return self.get(brief_id)

    def search(self, brief_id, findings):
        """Existing-solution search record: project code, open source, platform, donors."""
        if not isinstance(findings, list) or not findings:
            raise PolicyError('Search record needs at least one finding')
        rows = []
        for finding in findings:
            if not isinstance(finding, dict):
                raise PolicyError('Each finding must be an object')
            where = _text(finding.get('where', ''), 'Finding location', 300)
            verdict = finding.get('verdict')
            if verdict not in SEARCH_VERDICTS:
                raise PolicyError('Finding verdict must be one of %s' % ', '.join(SEARCH_VERDICTS))
            rows.append({'what': _text(finding.get('what', ''), 'Finding', 300), 'where': where,
                         'ref': str(finding.get('ref', ''))[:500], 'verdict': verdict})
        return self._set(brief_id, search=rows)

    def _set(self, brief_id, **fields):
        with self.store.transaction() as db:
            row = self._row(db, brief_id)
            data = json.loads(row['data'])
            data.update(fields)
            db.execute('UPDATE solution_briefs SET data=?, updated=? WHERE brief_id=?',
                       (encode(data), time.time(), brief_id))
        return self.get(brief_id)

    def opportunity(self, brief_id, what, why, benefit, fallback, classification='PROCEED',
                    access_needed=''):
        """Capability-opportunity check: would access we must not assume unlock a better solution?"""
        if classification not in OPPORTUNITY_CLASSES:
            raise PolicyError('Classification must be one of %s' % ', '.join(OPPORTUNITY_CLASSES))
        payload = {'what': _text(what, 'Opportunity', 300), 'why': _text(why, 'Why', 600),
                   'benefit': _text(benefit, 'Benefit', 600),
                   'fallback': _text(fallback, 'Fallback', 600),
                   'access_needed': str(access_needed)[:300]}
        if classification == 'ASK_ONCE' and not payload['access_needed'].strip():
            raise PolicyError('ASK_ONCE opportunities must name the access they need')
        op_id = uid()
        with self.store.transaction() as db:
            self._row(db, brief_id)
            db.execute('INSERT INTO capability_opportunities VALUES(?,?,?,?,?)',
                       (op_id, brief_id, classification, encode(payload), time.time()))
        return {'op_id': op_id, 'classification': classification}

    def idea(self, brief_id, idea, verdict, rationale=''):
        """User suggestions are candidates, not conclusions."""
        if verdict not in IDEA_VERDICTS:
            raise PolicyError('Verdict must be one of %s' % ', '.join(IDEA_VERDICTS))
        entry = {'idea': _text(idea, 'Idea', 600), 'verdict': verdict,
                 'rationale': str(rationale)[:1000], 'at': time.time()}
        if verdict == 'USER_MANDATE' and not entry['rationale'].strip():
            raise PolicyError('An explicit user mandate needs the recorded rationale')
        brief = self.get(brief_id)
        ideas = (brief['data'].get('user_ideas') or []) + [entry]
        return self._set(brief_id, user_ideas=ideas)

    def recommend(self, brief_id, option_id, rationale, evidence_to_switch, rollback,
                  workaround_type='permanent', wrong_layer=None, rework_forecast='', rejected=()):
        brief = self.get(brief_id)
        if len(brief['options']) < 2:
            raise PolicyError('Consequential work needs at least two materially different options')
        if not brief['data'].get('search'):
            raise PolicyError('Record the existing-solution search before recommending')
        if workaround_type not in WORKAROUND_TYPES:
            raise PolicyError('Workaround type must be one of %s' % ', '.join(WORKAROUND_TYPES))
        if not any(o['option_id'] == option_id for o in brief['options']):
            raise PolicyError('Recommend a recorded option')
        payload = {'option_id': option_id, 'rationale': _text(rationale, 'Rationale', 2000),
                   'evidence_to_switch': _text(evidence_to_switch, 'Evidence to switch', 1000),
                   'rollback': _text(rollback, 'Rollback', 1000), 'workaround_type': workaround_type,
                   'wrong_layer': wrong_layer, 'rework_forecast': str(rework_forecast)[:1000],
                   'rejected': [str(r)[:300] for r in rejected], 'at': time.time()}
        with self.store.transaction() as db:
            row = self._row(db, brief_id)
            data = json.loads(row['data'])
            data['recommendation'] = payload
            db.execute("UPDATE solution_briefs SET data=?, state='RECOMMENDED', chosen_option=?,"
                       " updated=? WHERE brief_id=?", (encode(data), option_id, time.time(), brief_id))
        return self.get(brief_id)

    def review(self, brief_id, reviewer_id, verdict, findings, resolved=False):
        if verdict not in REVIEW_VERDICTS:
            raise PolicyError('Review verdict must be one of %s' % ', '.join(REVIEW_VERDICTS))
        with self.store.transaction() as db:
            brief = self._row(db, brief_id)
            if reviewer_id == brief['author']:
                raise PolicyError('Self-certification is refused: the reviewer must be independent')
            review_id = uid()
            db.execute('INSERT INTO solution_reviews VALUES(?,?,?,?,?,?,?)',
                       (review_id, brief_id, reviewer_id, verdict,
                        _text(findings, 'Findings', 2000), 1 if resolved else 0, time.time()))
        return {'review_id': review_id, 'verdict': verdict}

    def resolve_block(self, brief_id, review_id, note=''):
        with self.store.transaction() as db:
            row = db.execute('SELECT * FROM solution_reviews WHERE brief_id=? AND review_id=?',
                             (brief_id, review_id)).fetchone()
            if not row or row['verdict'] != 'BLOCK':
                raise PolicyError('Only a BLOCK review can be resolved')
            db.execute('UPDATE solution_reviews SET resolved=1 WHERE review_id=?', (review_id,))
        return {'review_id': review_id, 'resolved': True, 'note': str(note)[:500]}

    def approve(self, brief_id, actor='user'):
        brief = self.get(brief_id)
        if brief['state'] != 'RECOMMENDED':
            raise PolicyError('Record a recommendation before approving')
        if any(r['verdict'] == 'BLOCK' and not r['resolved'] for r in brief['reviews']):
            raise PolicyError('An unresolved reviewer BLOCK must be resolved before approval')
        if not any(r['verdict'] == 'OPTIMAL_ENOUGH' for r in brief['reviews']):
            raise PolicyError('Approval needs an independent OPTIMAL_ENOUGH review')
        with self.store.transaction() as db:
            db.execute("UPDATE solution_briefs SET state='APPROVED', updated=? WHERE brief_id=?",
                       (time.time(), brief_id))
        return {'brief_id': brief_id, 'state': 'APPROVED', 'chosen_option': brief['chosen_option'],
                'approved_by': actor, 'approved_at': time.time(),
                'evidence_to_switch': brief['data']['recommendation']['evidence_to_switch'],
                'rollback': brief['data']['recommendation']['rollback']}

    def apply(self, data):
        action = data.get('action')
        if action == 'create':
            return {'id': self.open_brief(data['project_id'], data['goal'],
                                          data.get('conversation_id', 'main'), data.get('job_id'))}
        if action == 'get':
            return self.get(data['brief'])
        if action == 'list':
            return {'briefs': self.list(data['project_id'])}
        if action == 'fields':
            return self._set(data['brief'], **data.get('fields', {}))
        if action == 'option':
            return {'option_id': self.add_option(
                data['brief'], data['option_id'], data['title'], data['summary'], data['kind'],
                source=data.get('source', ''), tradeoffs=data.get('tradeoffs', ()),
                evidence=data.get('evidence', ()), cost=data.get('cost', ''),
                complexity=data.get('complexity'), reversible=data.get('reversible'))}
        if action == 'compare':
            return self.compare(data['brief'], data['criterion'], data['option_id'],
                                int(data['score']), data.get('note', ''))
        if action == 'search':
            return self.search(data['brief'], data['findings'])
        if action == 'opportunity':
            return self.opportunity(data['brief'], data['what'], data['why'], data['benefit'],
                                    data['fallback'], data.get('classification', 'PROCEED'),
                                    data.get('access_needed', ''))
        if action == 'idea':
            return self.idea(data['brief'], data['idea'], data['verdict'], data.get('rationale', ''))
        if action == 'recommend':
            return self.recommend(data['brief'], data['option_id'], data['rationale'],
                                  data['evidence_to_switch'], data['rollback'],
                                  data.get('workaround_type', 'permanent'),
                                  data.get('wrong_layer'), data.get('rework_forecast', ''),
                                  data.get('rejected', ()))
        if action == 'review':
            return self.review(data['brief'], data['reviewer_id'], data['verdict'],
                               data['findings'], bool(data.get('resolved')))
        if action == 'resolve_block':
            return self.resolve_block(data['brief'], data['review_id'], data.get('note', ''))
        if action == 'approve':
            return self.approve(data['brief'], data.get('actor', 'user'))
        raise PolicyError('Unknown brief action: %s' % action)
