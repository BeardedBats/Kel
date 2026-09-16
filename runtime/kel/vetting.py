"""Design Vetting Sessions — durable model and the answer-understanding service.

Architecture (non-negotiable): answer understanding is a service, not a composer feature.
`VettingAnswerIngestion` is pure text -> structured updates. It has no UI, no store access and no
model provider. Every input source funnels through it:

    typed chat (ACP)  |  pasted long text  |  future live transcription  |  direct/test harness
                                  |
                        VettingAnswerIngestion.parse(...)
                                  |
                        VettingSession.apply_ingestion(...)  (single state-mutation path)

Confidence: EXPLICIT / INFERRED_HIGH_CONFIDENCE / INFERRED_NEEDS_CONFIRMATION / NOT_AN_ANSWER.
Low-confidence mappings are never applied silently; they become proposals the user confirms.
"""
import json
import re
import time

from .core import uid

MIGRATION_VERSION = 11
MIGRATION_NAME = 'v15-vetting'

STATUSES = ('ANSWERED', 'PARTIALLY_ANSWERED', 'UNSURE', 'NEEDS_EXAMPLES', 'NEEDS_GREYBOX',
            'AWAITING_VISUAL_SELECTION', 'SKIPPED', 'DEFERRED', 'CONFLICTING')
CONFIDENCE = ('EXPLICIT', 'INFERRED_HIGH_CONFIDENCE', 'INFERRED_NEEDS_CONFIRMATION', 'NOT_AN_ANSWER')
SOURCES = ('chat', 'pasted', 'transcript', 'direct', 'api')

DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations(
    version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT);
CREATE TABLE IF NOT EXISTS vetting_sessions(
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL DEFAULT 'default',
    conversation_id TEXT NOT NULL,
    template TEXT NOT NULL,
    topic TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'ACTIVE',
    current_batch INTEGER NOT NULL DEFAULT 1,
    created REAL NOT NULL,
    updated REAL NOT NULL);
CREATE INDEX IF NOT EXISTS vetting_sessions_by_conversation ON vetting_sessions(conversation_id, state);
CREATE TABLE IF NOT EXISTS vetting_batches(
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    title TEXT NOT NULL,
    question_ids TEXT NOT NULL,
    created REAL NOT NULL,
    processed REAL);
CREATE TABLE IF NOT EXISTS vetting_questions(
    id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    bank_id TEXT NOT NULL,
    section TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    prompt TEXT NOT NULL,
    explain TEXT NOT NULL DEFAULT '',
    visual INTEGER NOT NULL DEFAULT 0,
    open INTEGER NOT NULL DEFAULT 0,
    options TEXT NOT NULL DEFAULT '[]',
    created REAL NOT NULL,
    PRIMARY KEY (session_id, id));
CREATE INDEX IF NOT EXISTS vetting_questions_by_session ON vetting_questions(session_id, ordinal);
CREATE TABLE IF NOT EXISTS vetting_answers(
    question_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    status TEXT NOT NULL,
    selected TEXT NOT NULL DEFAULT '[]',
    custom TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    confidence TEXT NOT NULL DEFAULT 'EXPLICIT',
    source TEXT NOT NULL DEFAULT 'chat',
    feedback TEXT NOT NULL DEFAULT '{}',
    updated REAL NOT NULL,
    PRIMARY KEY (session_id, question_id));
CREATE TABLE IF NOT EXISTS vetting_answer_revisions(
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT UNIQUE NOT NULL,
    session_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    previous TEXT NOT NULL,
    next TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'chat',
    at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS vetting_decisions(
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    statement TEXT NOT NULL,
    rationale TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'CONFIRMED',
    created REAL NOT NULL,
    updated REAL NOT NULL);
CREATE INDEX IF NOT EXISTS vetting_decisions_by_session ON vetting_decisions(session_id, status);
CREATE TABLE IF NOT EXISTS vetting_conflicts(
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    question_a TEXT NOT NULL,
    question_b TEXT NOT NULL,
    statement TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'OPEN',
    resolution TEXT,
    created REAL NOT NULL,
    resolved_at REAL);
CREATE TABLE IF NOT EXISTS vetting_help(
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS vetting_greyboxes(
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    traits TEXT NOT NULL DEFAULT '{}',
    svg TEXT NOT NULL DEFAULT '',
    is_base INTEGER NOT NULL DEFAULT 0,
    composite_of TEXT NOT NULL DEFAULT '[]',
    created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS vetting_greybox_feedback(
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    greybox_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS vetting_specs(
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    markdown TEXT NOT NULL,
    coverage TEXT NOT NULL DEFAULT '{}',
    created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS vetting_events(
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT UNIQUE NOT NULL,
    session_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'user',
    detail TEXT,
    at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS vetting_events_by_session ON vetting_events(session_id, seq);
"""


def _table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def ensure_schema(store):
    with store.transaction() as db:
        db.execute("CREATE TABLE IF NOT EXISTS schema_migrations("
                   "version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT)")
        if db.execute('SELECT 1 FROM schema_migrations WHERE version=?', (MIGRATION_VERSION,)).fetchone():
            return False
        fresh = not _table(db, 'jobs')
        for statement in filter(None, (part.strip() for part in DDL.split(';'))):
            db.execute(statement)
        db.execute('INSERT OR IGNORE INTO schema_migrations(version, name, applied, note) VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(),
                    'fresh database' if fresh else 'pre-existing database'))
        return True


def _now():
    return time.time()


def _loads(raw, fallback):
    try:
        value = json.loads(raw) if raw else fallback
    except Exception:
        return fallback
    return value if value is not None else fallback


# ---------------------------------------------------------------------------------------------
# Text understanding (pure). Source-agnostic by construction.
# ---------------------------------------------------------------------------------------------

SEGMENT_RE = re.compile(r'(?m)(?=^\s*(?:Q)?\d{1,3}\s*(?::|\.|,|\)|-|\u2013)\s*)')
ID_RE = re.compile(r'^\s*(?:Q)?(\d{1,3})\s*(?::|\.|,|\)|-|\u2013)?\s*(.*)$', re.S)
CODE_RE = re.compile(r'\b([A-L]|[1-9]|1[0-2])\b', re.I)
NATURAL_SPLIT = re.compile(r'(?:^|\s)(?:Q)?(\d{1,3})\s*[:.\-\u2013]\s*')
CONTROL_PATTERNS = (
    ('finish_spec', re.compile(r'(?i)\b(finish spec(?: now)?|finish (?:the )?spec|generate (?:the )?spec now)\b')),
    ('process', re.compile(r'(?i)\b(process (?:the )?answers?|process (?:this )?batch|synthesi[sz]e(?: now)?)\b')),
    ('pause', re.compile(r'(?i)\b(pause (?:the )?vetting|pause session|pause vetting)\b')),
    ('resume', re.compile(r'(?i)\b(continue|resume) (?:the )?[a-z0-9 \-]{0,40}?vetting(?: session)?\b')),
    ('preview_spec', re.compile(r'(?i)\b(preview (?:the )?spec|show (?:the )?spec)\b')),
    ('decisions', re.compile(r'(?i)\b(view|show) decisions\b')),
    ('open_questions', re.compile(r'(?i)\b(view|show) (?:open|unresolved|unanswered)\b')),
    ('show_unanswered', re.compile(r'(?i)\bshow unanswered only\b')),
    ('greybox', re.compile(r'(?i)\b(?:show )?greyboxes?\b')),
    ('help_explain', re.compile(r'(?i)\bexplain simply\b|\bexplain (?:the )?question\b|\bexplain\s+(?:q)?\d{1,3}\b')),
    ('help_more', re.compile(r'(?i)\bmore options\b')),
    ('help_challenge', re.compile(r'(?i)\bchallenge (?:this|my answer)\b|\bchallenge\s+(?:q)?\d{1,3}\b')),
)
CONFIRM_YES = re.compile(r'(?i)^\s*(yes|y|confirm|sure|do it|apply)\b')
CONFIRM_NO = re.compile(r'(?i)^\s*(no|n|skip that|leave it)\b')


def parse_control(text):
    """Recognize conversational batch/help controls. Returns (verb, arg) or (None, '')."""
    stripped = (text or '').strip()
    if not stripped:
        return None, ''
    for verb, pattern in CONTROL_PATTERNS:
        if pattern.search(stripped):
            match = re.search(r'(?:Q)?(\d{1,3})', stripped)
            return verb, (match.group(1) if match else '')
    if CONFIRM_YES.match(stripped):
        return 'confirm', ''
    if CONFIRM_NO.match(stripped):
        return 'reject', ''
    return None, ''


def _normalize(text):
    return re.sub(r'\s+', ' ', (text or '').strip().lower())


def _option_index(question):
    index = {}
    for option in question['options']:
        index[option['code'].lower()] = option
        for keyword in option.get('keywords', []):
            index.setdefault('kw:' + keyword.lower(), option)
    return index


STOPWORDS = {'with', 'from', 'this', 'that', 'into', 'your', 'their', 'when', 'then', 'than',
             'they', 'them', 'also', 'only', 'other', 'more', 'most', 'some', 'such', 'just',
             'have', 'here', 'each', 'very', 'well', 'will', 'would', 'could', 'should', 'about',
             'above', 'after', 'before', 'below', 'over', 'under', 'between', 'there', 'what',
             'which', 'where', 'while', 'does', 'must'}


def _match_natural(payload, questions, answers, loose=False):
    """Unique-keyword mapping when no id was given. Returns (question, option, score) or None.

    Strict mode applies answers at INFERRED_HIGH_CONFIDENCE; loose mode (used only to *propose*
    under-threshold matches for confirmation) accepts a single strong keyword.
    """
    needle = _normalize(payload)
    if len(needle) < 3:
        return None
    best = None
    for question in questions:
        for option in question['options']:
            words = [w for w in _normalize(option.get('label', '') + ' ' + option.get('desc', '')).split()
                     if len(w) > 3 and w not in STOPWORDS]
            words += [w.lower() for w in option.get('keywords', [])]
            if not words:
                continue
            hits = sum(1 for word in set(words) if word in needle)
            if hits:
                score = hits / max(4, len(set(words)))
                if best is None or score > best[2]:
                    best = (question, option, score, hits)
    min_hits = 1 if loose else 2
    min_score = 0.15 if loose else 0.34
    if best and best[3] >= min_hits and best[2] >= min_score:
        return best[0], best[1], best[2]
    return None


class VettingAnswerIngestion:
    """Pure answer understanding. No store, no UI, no provider."""

    def __init__(self, questions, answers):
        # questions: [{id, prompt, options:[{code,label,desc?,keywords?}], open, visual}]
        # answers: {question_id: {status, selected, custom, notes, feedback}}
        self.questions = list(questions)
        self.answers = dict(answers or {})
        self.by_number = {question['id'].lstrip('Q'): question for question in self.questions}

    def parse(self, text, source='chat'):
        result = {'updates': [], 'proposals': [], 'revisions': [], 'unmatched': [],
                  'control': None, 'confidence_summary': {}}
        verb, arg = parse_control(text)
        if verb:
            result['control'] = {'verb': verb, 'arg': arg}
            # "17: make greyboxes" also carries an answer-shaped greybox request; keep both.
            if verb != 'greybox' or not arg:
                return result
        text = (text or '').strip()
        if not text:
            return result
        segments = self._segments(text)
        for number, payload in segments:
            question = self.by_number.get(number) if number else None
            if number and question is None:
                result['unmatched'].append({'number': number, 'payload': payload[:200],
                                            'reason': 'no question with that id in this session'})
                continue
            if question is None:
                question, option, score = _match_natural(payload, self.questions, self.answers) or (None, None, 0)
                if question and option:
                    update = self._update(question, [option['code']], '', '', 'INFERRED_HIGH_CONFIDENCE',
                                          source, {'matched_on': option['label'][:80], 'score': round(score, 2)})
                    self._commit(result, question, update)
                else:
                    proposals = self._propose_natural(payload)
                    if proposals:
                        result['proposals'].extend(proposals)
                    elif payload:
                        result['unmatched'].append({'number': None, 'payload': payload[:200],
                                                    'reason': 'could not map this to an open question'})
                continue
            update = self._payload_update(question, payload, source)
            if update is not None:
                self._commit(result, question, update)
            else:
                proposals = self._propose_natural(payload, question=question)
                result['proposals'].extend(proposals)
                if not proposals:
                    result['unmatched'].append({'number': number, 'payload': payload[:200],
                                                'reason': 'not an option code, control word or confident match'})
        counts = {}
        for update in result['updates']:
            counts[update['confidence']] = counts.get(update['confidence'], 0) + 1
        for proposal in result['proposals']:
            counts['INFERRED_NEEDS_CONFIRMATION'] = counts.get('INFERRED_NEEDS_CONFIRMATION', 0) + 1
        result['confidence_summary'] = counts
        return result

    # -- internals ------------------------------------------------------------------------------

    def _segments(self, text):
        if SEGMENT_RE.search(text):
            parts = [part for part in SEGMENT_RE.split(text) if part.strip()]
            segments = []
            for part in parts:
                match = ID_RE.match(part)
                if match:
                    segments.append((match.group(1), match.group(2).strip()))
            if segments:
                return segments
        segments = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            match = ID_RE.match(line)
            if match and match.group(1) in self.by_number:
                segments.append((match.group(1), match.group(2).strip()))
        if segments:
            return segments
        return [(None, text)]

    def _payload_update(self, question, payload, source):
        lowered = _normalize(payload)
        if not lowered:
            return None
        if re.match(r'^(skip|skip for now|pass)\b', lowered):
            return self._update(question, [], '', '', 'EXPLICIT', source, {'status': 'SKIPPED'}, status='SKIPPED')
        if re.match(r'^(defer|later|decide later|not now)\b', lowered):
            return self._update(question, [], '', '', 'EXPLICIT', source, {}, status='DEFERRED')
        if re.search(r'\b(greybox|greyboxes|mock-?ups?|wireframes?)\b', lowered) and \
                re.search(r'\b(make|show|generate|need|want|give)\b', lowered):
            return self._update(question, [], '', '', 'EXPLICIT', source,
                                {'greybox_request': True}, status='AWAITING_VISUAL_SELECTION')
        unsure = re.search(r"\b(not sure|unsure|don'?t know|no idea|not certain)\b", lowered)
        if unsure:
            wants_examples = bool(re.search(r'example|show me|show examples', lowered))
            return self._update(question, [], '', '', 'EXPLICIT', source,
                                {'wants_examples': wants_examples},
                                status='NEEDS_EXAMPLES' if wants_examples else 'UNSURE')
        none_of_these = re.match(r'^none of these\b[:,]?\s*(.*)$', lowered, re.S)
        if none_of_these:
            custom = payload.split('these', 1)[1].lstrip(' :,-') if 'these' in payload else ''
            return self._update(question, [], custom.strip(), '', 'EXPLICIT', source,
                                {'none_of_these': True})
        revise = re.match(r'^(?:change|revise|update|actually)\s*(?:it\s*)?(?:to|:)?\s*(.+)$', lowered)
        if revise:
            nested = self._payload_update(question, revise.group(1), source)
            if nested is not None:
                nested['reason'] = 'user revised this answer'
                nested['is_revision'] = True
            return nested
        index = _option_index(question)
        tokens = CODE_RE.findall(payload)
        if tokens and not re.search(r'[a-z]{4,}', re.sub(r'\b(and|or)\b', ' ', lowered)):
            picked, unknown = [], []
            for token in tokens:
                option = index.get(token.lower())
                (picked.append(option['code']) if option else unknown.append(token))
            if picked and not unknown:
                return self._update(question, sorted(set(picked)), '', '', 'EXPLICIT', source, {})
            if unknown and picked:
                return self._update(question, sorted(set(picked)), '', '', 'EXPLICIT', source,
                                    {'unknown_codes': unknown})
            if unknown and not picked:
                return None
        if question['open'] or (tokens and re.search(r'[a-z]{4,}', lowered)):
            # A mixed answer like "F but waiver rows should fold away" keeps F and stores the note.
            picked = [index[t.lower()]['code'] for t in tokens if t.lower() in index]
            if picked:
                note = payload
                return self._update(question, sorted(set(picked)), '', note, 'EXPLICIT', source, {})
            if question['open']:
                return self._update(question, [], payload, '', 'EXPLICIT', source, {})
        natural = _match_natural(payload, [question], self.answers)
        if natural and natural[1]:
            return self._update(question, [natural[1]['code']], '', '', 'INFERRED_HIGH_CONFIDENCE', source,
                                {'matched_on': natural[1]['label'][:80]})
        return None

    def _propose_natural(self, payload, question=None):
        proposals = []
        candidates = [question] if question else self.questions
        for candidate in candidates:
            natural = _match_natural(payload, [candidate], self.answers, loose=True)
            if natural and natural[1]:
                proposals.append({'kind': 'map_answer', 'question_id': candidate['id'],
                                  'option': natural[1]['code'], 'option_label': natural[1]['label'],
                                  'payload': payload[:200], 'confidence': 'INFERRED_NEEDS_CONFIRMATION',
                                  'reason': 'closest option match — confirm to apply'})
        return proposals[:3]

    def _update(self, question, selected, custom, notes, confidence, source, feedback,
                status=None):
        if status is None:
            status = 'ANSWERED' if (selected or custom.strip()) else 'PARTIALLY_ANSWERED'
        return {'question_id': question['id'], 'status': status, 'selected': list(selected),
                'custom': custom, 'notes': notes, 'confidence': confidence, 'source': source,
                'feedback': feedback or {}}

    def _commit(self, result, question, update):
        previous = self.answers.get(question['id']) or {}
        changed = (previous.get('status') != update['status'] or
                   list(previous.get('selected') or []) != list(update['selected']) or
                   (previous.get('custom') or '') != update['custom'])
        if changed and previous.get('status'):
            update['is_revision'] = True
            result['revisions'].append({'question_id': question['id'], 'previous': previous, 'next': update,
                                        'reason': update.pop('reason', 'answer changed')})
        result['updates'].append(update)
        self.answers[question['id']] = {'status': update['status'], 'selected': update['selected'],
                                        'custom': update['custom'], 'notes': update['notes'],
                                        'feedback': update['feedback']}


def think_out_loud_buckets(text):
    """Deterministic Think-Out-Loud extraction over a spoken transcript (no provider involved).

    Decisions/preferences come from the ingestion parse at review time; here we classify the raw
    sentences into the buckets the review surface shows so nothing said is silently dropped.
    """
    buckets = {'requirements': [], 'concerns': [], 'unresolved': []}
    for sentence in re.split(r'(?<=[.!?])\s+|\n+', text or ''):
        clean = sentence.strip()
        if len(clean) < 8:
            continue
        lowered = clean.lower()
        if re.search(r'\b(must|need to|needs to|have to|has to|should|require[sd]?|shall)\b', lowered):
            buckets['requirements'].append(clean)
        if re.search(r'\b(worry|worried|concern|concerned|risk|afraid|problem|issue|danger|break)\b', lowered):
            buckets['concerns'].append(clean)
        if re.search(r'\b(not sure|unsure|open question|later|tbd|decide later|need to decide|'
                     r'figure out|unclear)\b', lowered):
            buckets['unresolved'].append(clean)
    return {key: value[:8] for key, value in buckets.items()}
