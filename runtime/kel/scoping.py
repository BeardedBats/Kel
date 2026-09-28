"""D-70 item 4 — scoping before big work (D-55: Kel asks before it starts, never after).

When Kel would staff a request as a Builder + Verifier pod or larger (the one threshold setting,
`threshold`), or when Kel's own plan has open questions that change the result, Kel does not hand
the work off yet. It says so in one short line and shows a brief card: two or three questions, each
with quick picks and "Something else…", an "I'll build: …" line, Start and "Just start with your
best guess". Nothing is compiled, created or run until Nick chooses (D-55); the top of the chat
shows the work as "Scoping" meanwhile.

Start (or best guess) then goes through the normal hand-off: a new submission whose request carries
the answers, an acknowledgement, and `Service._start_work` on the planning pool — the answers travel
in the contract (`contract['context']['scoping']`) and in the request text. Every answer, picked or
typed, is understood by the same `VettingAnswerIngestion` as any other vetting source (the questions
are a vetting session that never becomes the chat's active session). Asked, started and best-guess
are each one Activity line.

The trigger is consulted from `Service._plan` only for work the turn model chose (a keyword-gate
hand-off has no model to write tailored questions, and scheduled runs, recipes and continuations are
never scoped).
"""
import contextlib
import json
import re
import secrets
import time

from .core import PolicyError, encode, uid

DDL = """
CREATE TABLE IF NOT EXISTS scopings(
  id TEXT PRIMARY KEY, submission_id TEXT NOT NULL, conversation_id TEXT NOT NULL, project_id TEXT,
  title TEXT NOT NULL, request TEXT NOT NULL, kind TEXT, packet TEXT NOT NULL, greenfield INTEGER NOT NULL,
  questions TEXT NOT NULL, summary TEXT NOT NULL, why TEXT NOT NULL, estimate TEXT NOT NULL,
  session_id TEXT NOT NULL, message_seq INTEGER, state TEXT NOT NULL, answers TEXT,
  started_submission TEXT, started_at REAL, created REAL NOT NULL);
CREATE INDEX IF NOT EXISTS scopings_by_conversation ON scopings(conversation_id, state);
CREATE TABLE IF NOT EXISTS scoping_prefs(key TEXT PRIMARY KEY, value TEXT NOT NULL, updated REAL NOT NULL);
"""

OPEN, STARTED, BEST_GUESS = 'open', 'started', 'best_guess'

# The one threshold setting (D-70: "until Nick sets one"): the smallest staffing tier that is scoped
# first. D2 = a Builder + Verifier pod; 'off' never scopes by size (open questions still do).
THRESHOLDS = ('D1', 'D2', 'D3', 'D4', 'off')
DEFAULT_THRESHOLD = 'D2'
TIER_RANK = {'D0': 0, 'D1': 1, 'D2': 2, 'D3': 3, 'D4': 4}

MAX_QUESTIONS = 3
MAX_OPTIONS = 4
QUESTION_LIMIT = 140
OPTION_LIMIT = 48
SUMMARY_LIMIT = 220
ANSWER_LIMIT = 200
CODES = 'ABCD'
NUMBERS = {1: 'one', 2: 'two', 3: 'three'}
LEADS = {'code': "I'll build", 'writing': "I'll write", 'research': "I'll find out", 'recipe': "I'll run"}
MARKDOWN = re.compile(r'^\s*(?:#{1,6}\s|[-*+]\s|\d+[.)]\s|>\s|```)|[`*_]{2,}', re.MULTILINE)

# Kel's own questions when its plan names none (kind -> questions; `best` is the best guess).
BANK = {
    'code': [
        {'prompt': 'How finished should the first version be?',
         'options': ['A quick working version', 'Polished and ready to use', 'Built to last, with tests'], 'best': 1},
        {'prompt': 'Who will use it?', 'options': ['Just me', 'A few people I know', 'Anyone, publicly'], 'best': 0},
        {'prompt': 'Which look?', 'options': ['Clean and simple', 'Bold and colorful', 'Match something I have'],
         'best': 0, 'user_facing': True},
    ],
    'writing': [
        {'prompt': 'Who is it for?', 'options': ['Just me', 'My team or colleagues', 'The public'], 'best': 1},
        {'prompt': 'How long should it be?',
         'options': ['Short, about a page', 'Two or three pages', 'Long and detailed'], 'best': 0},
        {'prompt': 'Which tone?', 'options': ['Plain and direct', 'Warm and friendly', 'Formal'], 'best': 0},
    ],
    'research': [
        {'prompt': 'How deep should I go?', 'options': ['A quick overview', 'A solid comparison', 'A deep dive'],
         'best': 1},
        {'prompt': 'How should I give it to you?', 'options': ['A short answer', 'A table to compare', 'A written report'],
         'best': 1},
    ],
}


def ensure_schema(store):
    with contextlib.closing(store.connect()) as db:
        db.executescript(DDL)


def _table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()


# ---- the threshold (one setting) ---------------------------------------------------------------

def threshold(store):
    """The smallest staffing tier scoped before it starts ('D2' until Nick sets one), or 'off'."""
    with contextlib.closing(store.connect()) as db:
        if not _table(db, 'scoping_prefs'):
            return DEFAULT_THRESHOLD
        row = db.execute("SELECT value FROM scoping_prefs WHERE key='threshold'").fetchone()
    value = row['value'] if row else DEFAULT_THRESHOLD
    return value if value in THRESHOLDS else DEFAULT_THRESHOLD


def set_threshold(store, value):
    if value not in THRESHOLDS:
        raise PolicyError('Choose D1, D2, D3, D4 or off.')
    ensure_schema(store)
    with store.transaction() as db:
        db.execute('INSERT INTO scoping_prefs(key,value,updated) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE '
                   'SET value=excluded.value, updated=excluded.updated', ('threshold', value, time.time()))
    return {'threshold': value}


# ---- the trigger -------------------------------------------------------------------------------

def _clean(text, limit):
    words = ' '.join(str(text or '').split()).strip()
    if not words or len(words) > limit or MARKDOWN.search(words) or '`' in words:
        return None
    return words


def clean_questions(raw):
    """Kel's proposed questions, bounded: 1–3 questions, 2–4 distinct short options each."""
    out = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        prompt = _clean(item.get('question') or item.get('prompt'), QUESTION_LIMIT)
        options = []
        for option in item.get('options') if isinstance(item.get('options'), list) else []:
            label = _clean(option.get('label') if isinstance(option, dict) else option, OPTION_LIMIT)
            if label and label.lower() not in {existing.lower() for existing in options}:
                options.append(label)
        if not prompt or len(options) < 2:
            continue
        options = options[:MAX_OPTIONS]
        best = _clean(item.get('best_guess') or item.get('default'), OPTION_LIMIT)
        index = next((i for i, label in enumerate(options) if best and label.lower() == best.lower()), 0)
        out.append({'prompt': prompt, 'options': options, 'best': index})
        if len(out) == MAX_QUESTIONS:
            break
    return out


def _bank(kind, text):
    from .staff import USER_FACING
    user_facing = bool(USER_FACING.search(text or ''))
    return [dict(q) for q in BANK.get(kind, BANK['writing']) if user_facing or not q.get('user_facing')][:MAX_QUESTIONS]


def estimate(store, text, kind):
    """The staffing tier Kel would choose for this request, estimated before anything is compiled.

    The same deterministic features and rule table as the real decision (`staff.features_for`,
    `staffing.resolve`) over the request alone — no model call, no contract, nothing written.
    """
    from . import staff, staffing
    contract = {'kind': 'coding' if kind == 'code' else ('research' if kind == 'research' else 'document'),
                'milestones': [{'id': 'm1'}], 'request': text,
                'required_capabilities': ['web_research'] if kind == 'research' else []}
    features, flags = staff.features_for(contract, text)
    decision = staffing.resolve(store, features, flags=tuple(flags))
    tier = decision['tier']
    if kind == 'code' and TIER_RANK.get(tier, 0) < 1:
        tier = 'D1'
    return {'tier': tier, 'features': features, 'flags': list(flags), 'reasons': list(decision.get('reasons') or [])}


def consider(store, text, kind, decision):
    """The scoping plan for one request, or None when it starts straight away.

    Scoped when the estimated tier reaches the threshold (a Builder + Verifier pod or larger by
    default), or when Kel's plan names open questions that change the result.
    """
    proposed = (decision or {}).get('scoping') if isinstance((decision or {}).get('scoping'), dict) else {}
    questions = clean_questions(proposed.get('questions'))
    limit = threshold(store)
    guess = estimate(store, text, kind)
    big = limit != 'off' and TIER_RANK.get(guess['tier'], 0) >= TIER_RANK[limit]
    if not big and not questions:
        return None
    if not questions:
        questions = _bank(kind, text)
    if not questions:
        return None
    summary = _clean(proposed.get('summary'), SUMMARY_LIMIT)
    why = 'size' if big else 'open_questions'
    return {'questions': questions, 'summary': summary, 'why': why, 'estimate': guess, 'threshold': limit}


def _work_kind(service, text, kind, packet):
    """'code' | 'research' | 'writing' — the same routing `_compile_work` will use."""
    from .research import needs_research
    from .service import CODING_VERBS
    lower = text.lower().strip()
    root = (packet.get('project') or {}).get('root')
    coding_verb = lower.startswith(CODING_VERBS) or service._code_in_project(text, packet)
    if kind == 'coding' or (root and coding_verb):
        return 'code'
    if kind == 'research' or needs_research(text):
        return 'research'
    return 'writing'


def maybe_ask(service, sid, cid, text, packet, kind, greenfield, decision, choice=None):
    """Called by `Service._plan` before a model-decided hand-off. True when Kel asked first."""
    from .router import file_action
    if packet.get('schedule') or packet.get('recipe_invocation') or packet.get('continuation'):
        return False
    if file_action(text) or kind == 'recipe':
        return False
    work_kind = _work_kind(service, text, kind, packet)
    try:
        plan = consider(service.store, text, work_kind, decision)
    except Exception:
        return False  # a trigger that cannot be read never blocks the work
    if not plan:
        return False
    return open_scope(service, sid, cid, text, packet, kind, greenfield, decision, choice, plan, work_kind) is not None


def _message(plan):
    count = len(plan['questions'])
    number = NUMBERS.get(count, str(count))
    noun = 'question' if count == 1 else 'questions'
    if plan['why'] == 'size':
        return "Happy to. It's a bigger job, so %s quick %s first; I'll decide the rest." % (number, noun)
    return "Happy to. %s quick %s first, since the answers change what I make; I'll decide the rest." % (
        number.capitalize(), noun)


def open_scope(service, sid, cid, text, packet, kind, greenfield, decision, choice, plan, work_kind):
    """Say Kel asks first, record the questions, settle the message. Nothing is started."""
    from .turn import title_for
    from .vetting import ensure_schema as ensure_vetting
    from .vetting_session import Vetting
    ensure_schema(service.store)
    ensure_vetting(service.store)
    title = title_for(text, (decision or {}).get('title'))
    questions = [{'id': 'Q%d' % index, 'prompt': question['prompt'],
                  'options': [{'code': CODES[i], 'label': label} for i, label in enumerate(question['options'])],
                  'best': CODES[question['best']]}
                 for index, question in enumerate(plan['questions'], 1)]
    summary = '%s: %s' % (LEADS.get(work_kind, "I'll do"), plan['summary'] or title[:1].lower() + title[1:])
    scoping_id = uid()
    project_id = (packet.get('project') or {}).get('id')
    vetting = Vetting(service.store, conversation=cid)  # its schema is checked outside the transaction
    with service.store.transaction() as db:
        if not service._still_planning(db, sid):
            return None  # stopped before Kel asked: nothing is said
        session_id = vetting.open_questions(
            db, project_id, cid, title, [{'id': q['id'], 'prompt': q['prompt'], 'options': q['options']}
                                         for q in questions])
        say, meta = service._with_choice(db, cid, _message(plan), choice)
        meta = dict(meta or {}, kind='scoping', scoping=scoping_id)
        seq = db.execute('INSERT INTO messages(conversation_id,role,text,at,meta) VALUES(?,?,?,?,?)',
                         (cid, 'assistant', say, time.time(), encode(meta))).lastrowid
        db.execute('INSERT INTO scopings(id,submission_id,conversation_id,project_id,title,request,kind,packet,'
                   'greenfield,questions,summary,why,estimate,session_id,message_seq,state,created) '
                   'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (scoping_id, sid, cid, project_id, title, text, kind, encode(packet), 1 if greenfield else 0,
                    encode(questions), summary, plan['why'],
                    encode({'tier': plan['estimate']['tier'], 'threshold': plan['threshold'],
                            'kind': work_kind, 'flags': plan['estimate']['flags']}),
                    session_id, seq, OPEN, time.time()))
        db.execute("UPDATE submissions SET state='SETTLED',job_id=NULL WHERE id=?", (sid,))
        _event(db, scoping_id, 'asked', {'project_id': project_id, 'questions': len(questions), 'title': title,
                                         'why': plan['why'], 'tier': plan['estimate']['tier']})
    return scoping_id


def _event(db, scoping_id, action, detail):
    aggregate = 'scoping:' + scoping_id
    revision = db.execute('SELECT COALESCE(MAX(revision),0)+1 FROM events WHERE aggregate_id=?',
                          (aggregate,)).fetchone()[0]
    db.execute('INSERT INTO events(id,aggregate_id,revision,type,at,payload) VALUES(?,?,?,?,?,?)',
               (uid(), aggregate, revision, 'scoping.' + action, time.time(),
                encode({'schema_version': 1, 'scoping': {'id': scoping_id, 'action': action}, 'detail': detail})))


# ---- reading ------------------------------------------------------------------------------------

def _row(store, scoping_id, db=None):
    def run(db):
        if not _table(db, 'scopings'):
            return None
        row = db.execute('SELECT * FROM scopings WHERE id=?', (str(scoping_id),)).fetchone()
        return dict(row) if row else None
    if db is not None:
        return run(db)
    with contextlib.closing(store.connect()) as db:
        return run(db)


def _chosen(question, answer):
    """The words of one answer: an option's label, or what Nick typed."""
    answer = answer or {}
    labels = [o['label'] for o in question['options'] if o['code'] in (answer.get('selected') or [])]
    custom = (answer.get('custom') or '').strip()
    return labels[0] if labels else (custom or None)


def view(store, scoping_id, conversation=None):
    """One scoping card: questions with their picks, the summary, and what happened."""
    row = _row(store, scoping_id)
    if not row or (conversation and row['conversation_id'] != conversation):
        raise PolicyError('Kel could not find those questions in this conversation.')
    questions = json.loads(row['questions'])
    answers = json.loads(row['answers']) if row.get('answers') else {}
    out_questions = []
    for question in questions:
        answer = answers.get(question['id'])
        out_questions.append({'id': question['id'], 'question': question['prompt'],
                              'options': [{'code': o['code'], 'label': o['label']} for o in question['options']],
                              'best': question.get('best'),
                              'answer': answer})
    return {'id': row['id'], 'title': row['title'], 'state': row['state'], 'conversation_id': row['conversation_id'],
            'project_id': row['project_id'], 'questions': out_questions, 'summary': row['summary'],
            'why': row['why'], 'created': row['created'], 'started_at': row.get('started_at'),
            'started_submission': row.get('started_submission'),
            'answer_line': _answer_line(questions, answers) if row['state'] != OPEN else None}


def _answer_line(questions, answers):
    return ' · '.join(filter(None, ((answers.get(q['id']) or {}).get('label') for q in questions)))


def office_items(store, *, conversation=None, project=None):
    """Open scopings as top cards in the "Scoping" state (D-70): chat icon, no bar, "N questions"."""
    from .projects import ALL
    with contextlib.closing(store.connect()) as db:
        if not _table(db, 'scopings'):
            return []
        rows = [dict(r) for r in db.execute("SELECT * FROM scopings WHERE state=? ORDER BY created DESC", (OPEN,))]
    out = []
    for row in rows:
        if conversation and row['conversation_id'] != conversation:
            continue
        if project and project != ALL and row['project_id'] != project:
            continue
        count = len(json.loads(row['questions']))
        kind = json.loads(row['estimate']).get('kind') or 'writing'
        out.append({'job_id': row['id'], 'scoping_id': row['id'], 'title': row['title'],
                    'project_id': row['project_id'], 'conversation_id': row['conversation_id'],
                    'submission_id': row['submission_id'], 'kind': kind, 'state': 'scoping', 'finished': False,
                    'status_line': 'Kel has %d question%s before it starts.' % (count, '' if count == 1 else 's'),
                    'needs_you': True, 'questions': count, 'progress': None, 'team': [], 'team_size': 0,
                    'started_at': row['created'], 'updated_at': row['created'], 'finished_at': None,
                    'message_seq': row['message_seq']})
    return out


# ---- starting ------------------------------------------------------------------------------------

def _ingest(store, row, answers):
    """Every answer through `VettingAnswerIngestion` (via the session's single ingestion path)."""
    from .vetting_session import Vetting
    questions = json.loads(row['questions'])
    lines = []
    for index, question in enumerate(questions, 1):
        answer = answers.get(question['id']) if isinstance(answers, dict) else None
        if not isinstance(answer, dict):
            continue
        code = str(answer.get('option') or '').strip().upper()
        typed = ' '.join(str(answer.get('text') or '').split())[:ANSWER_LIMIT]
        if code and any(o['code'] == code for o in question['options']):
            lines.append('%d: %s' % (index, code))
        elif typed:
            lines.append('%d: none of these: %s' % (index, typed))  # "Something else…": kept as typed
    if lines:
        Vetting(store, conversation=row['conversation_id']).ingest(row['session_id'], '\n'.join(lines),
                                                                  source='direct')
    from .vetting import ensure_schema as ensure_vetting
    ensure_vetting(store)
    with contextlib.closing(store.connect()) as db:
        recorded = {r['question_id']: {'selected': json.loads(r['selected'] or '[]'), 'custom': r['custom'] or ''}
                    for r in db.execute('SELECT question_id, selected, custom FROM vetting_answers WHERE session_id=?',
                                        (row['session_id'],))}
    return questions, recorded


def start(service, scoping_id, answers=None, best_guess=False, conversation=None, actor='user'):
    """Start the scoped work through the normal hand-off, with the answers in its contract.

    Idempotent: a second Start returns the first one's result. `best_guess` starts at once with
    Kel's own best guess for every question it was not told, recorded as assumptions.
    """
    if actor != 'user':
        raise PolicyError('Only you can start this work.')
    store = service.store
    ensure_schema(store)
    row = _row(store, scoping_id)
    if not row or (conversation and row['conversation_id'] != conversation):
        raise PolicyError('Kel could not find those questions in this conversation.')
    if row['state'] != OPEN:
        return dict(view(store, scoping_id), already=True)
    questions, recorded = _ingest(store, row, {} if best_guess else (answers or {}))
    decided, assumed = {}, []
    for question in questions:
        words = _chosen(question, recorded.get(question['id']))
        if words:
            decided[question['id']] = {'label': words, 'assumed': False}
        else:
            best = next((o['label'] for o in question['options'] if o['code'] == question.get('best')),
                        question['options'][0]['label'])
            decided[question['id']] = {'label': best, 'assumed': True}
            assumed.append(question['id'])
    lines = []
    for question in questions:
        entry = decided[question['id']]
        lines.append('- %s %s%s' % (question['prompt'], entry['label'],
                                    " (Kel's best guess)" if entry['assumed'] else ''))
    heading = ("Details agreed before starting:" if not best_guess else
               "You asked Kel to start with its best guess; Kel assumed:")
    request = row['request'].rstrip() + '\n\n' + heading + '\n' + '\n'.join(lines)
    packet = json.loads(row['packet'])
    packet['scoping'] = {'id': scoping_id, 'best_guess': bool(best_guess), 'why': row['why'],
                         'answers': [{'question': q['prompt'], 'answer': decided[q['id']]['label'],
                                      'assumed': decided[q['id']]['assumed']} for q in questions]}
    new_sid = secrets.token_hex(16)
    state = BEST_GUESS if best_guess else STARTED
    if best_guess:
        ack = ("Starting now with my best guess: %s. I'll post the result here once it's been checked."
               % '; '.join(decided[q['id']]['label'][:1].lower() + decided[q['id']]['label'][1:] for q in questions))
    else:
        ack = "Starting now with your answers. I'll post the result here once it's been checked."
    now = time.time()
    with service.handoff_lock:
        with store.transaction() as db:
            current = _row(store, scoping_id, db)
            if current['state'] != OPEN:
                return dict(view(store, scoping_id), already=True)
            db.execute('INSERT INTO submissions VALUES(?,?,?,?,?,?,?)',
                       (new_sid, row['conversation_id'], request, 'PLANNING', None, None, now))
            db.execute('INSERT INTO submission_packets VALUES(?,?,?)', (new_sid, encode(packet), row['kind']))
            seq = db.execute('INSERT INTO messages(conversation_id,role,text,at,meta) VALUES(?,?,?,?,?)',
                             (row['conversation_id'], 'assistant', ack, now,
                              encode({'kind': 'scoping_started', 'scoping': scoping_id}))).lastrowid
            db.execute('INSERT INTO submission_acks VALUES(?,?,?,?)', (new_sid, seq, row['title'], now))
            db.execute('UPDATE scopings SET state=?, answers=?, started_submission=?, started_at=? WHERE id=?',
                       (state, encode(decided), new_sid, now, scoping_id))
            _event(db, scoping_id, 'best_guess' if best_guess else 'started',
                   {'project_id': row['project_id'], 'title': row['title'], 'assumed': len(assumed),
                    'actor': actor})
    greenfield = bool(row['greenfield'])
    service.planning.submit(service._start_work, new_sid, row['conversation_id'], request, packet, row['kind'],
                            greenfield)
    service.wake.set()
    return dict(view(store, scoping_id), submission_id=new_sid)


def action(service, data):
    """POST /api/scoping: `start` (with answers) or `best_guess` for one open scoping card."""
    verb = data.get('action')
    scoping_id = str(data.get('id') or '')
    if not scoping_id:
        raise PolicyError('Pick the questions to answer first.')
    conversation = data.get('conversation') or None
    if verb == 'start':
        return start(service, scoping_id, answers=data.get('answers') or {}, conversation=conversation)
    if verb == 'best_guess':
        return start(service, scoping_id, best_guess=True, conversation=conversation)
    raise PolicyError('Choose Start or "Just start with your best guess".')
