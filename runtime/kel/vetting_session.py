"""Design Vetting Sessions — session orchestration over the durable model.

This module owns: session lifecycle, batch materialization and adaptation, the single
ingestion flow used by every input source, synthesis, spec snapshots, greybox rounds,
and conflict surfacing. It never parses text itself — that lives in
`VettingAnswerIngestion` (kel/vetting.py), which is deliberately UI-free so the same
understanding path serves typed chat, pasted transcripts, future transcription, and the
direct/test harness. Input method is replaceable; answer understanding is not.

User Journey notes (rules JR-14/JR-16 apply): the batch is published as conversation
content, controls are conversational, and machinery words (batch ids, revision rows)
stay out of the primary copy.
"""
import contextlib
import json
import re
import time

from .core import PolicyError, uid
from . import vetting_bank as bank_mod
from . import vetting_spec as spec_mod
from .vetting import (VettingAnswerIngestion, ensure_schema, parse_control,
                       think_out_loud_buckets)

BATCH_TARGET = 12

START_RE = re.compile(
    r'(?i)(?:^|\s)(?:/vetting\s+start|start\s+(?:a\s+)?(?:new\s+)?(?:design\s+|product\s+ui\s+)?vetting(?:\s+session)?)'
    r'(?:\s*(?:for|on|about|:)\s*(?P<topic>.+))?$')

# Philosophy-level oppositions: choosing a value on one side after the other side is already
# chosen is a real contradiction, not a refinement. Surfaced, never silently overwritten.
OPPOSITIONS = (
    ('opening', ('summary', 'overview'), ('board', 'dense', 'working board', 'command center')),
    ('opening_reverse', ('board', 'dense', 'working board'), ('start/empty state', 'empty state', 'inbox')),
)


def _row(row):
    return dict(row) if row is not None else None


def _loads(raw, fallback):
    try:
        return json.loads(raw) if raw else fallback
    except (TypeError, ValueError):
        return fallback


def chosen_labels(questions, updates=None):
    """Question id -> chosen option labels (lowercased), with parsed updates overlaid.

    One implementation serves the recording conflict check and the read-only transcript preview,
    so the two scans cannot drift apart.
    """
    by_id = {q['id']: q for q in questions}
    selected = {}
    for question in questions:
        answer = question.get('answer') or {}
        selected[question['id']] = list(answer.get('selected') or [])
    for update in updates or []:
        selected[update['question_id']] = list(update.get('selected') or [])
    chosen = {}
    for qid, codes in selected.items():
        question = by_id.get(qid)
        if not question:
            continue
        labels = [o['label'].lower() for o in question['options'] if o['code'] in codes]
        if labels:
            chosen[qid] = ' '.join(labels)
    return chosen


def opposition_pairs(chosen):
    """(candidate_a, candidate_b) pairs whose labels oppose on a philosophy axis."""
    pairs = []
    for _axis, group_a, group_b in OPPOSITIONS:
        side_a = [qid for qid, text in chosen.items() if any(k in text for k in group_a)]
        side_b = [qid for qid, text in chosen.items() if any(k in text for k in group_b)]
        for qa in side_a:
            for qb in side_b:
                if qa != qb and (qa, qb) not in pairs and (qb, qa) not in pairs:
                    pairs.append((qa, qb))
    return pairs


class Vetting:
    """Durable design-vetting sessions, scoped to a conversation."""

    def __init__(self, store):
        self.store = store
        ensure_schema(store)
        self._bank_cache = None

    # ---- sessions ---------------------------------------------------------------------------

    def bank(self):
        if self._bank_cache is None:
            self._bank_cache = bank_mod.default_bank()
        return self._bank_cache

    def active(self, conversation, db=None):
        def run(db):
            row = db.execute(
                "SELECT * FROM vetting_sessions WHERE conversation_id=? AND state IN ('ACTIVE','PAUSED')"
                " ORDER BY created DESC LIMIT 1", (conversation,)).fetchone()
            return _row(row)
        if db is not None:
            return run(db)
        with contextlib.closing(self.store.connect()) as db:
            return run(db)

    def session(self, session_id, db=None):
        def run(db):
            return _row(db.execute('SELECT * FROM vetting_sessions WHERE id=?', (session_id,)).fetchone())
        if db is not None:
            return run(db)
        with contextlib.closing(self.store.connect()) as db:
            return run(db)

    def start(self, project_id, conversation, topic, actor='user'):
        bank = self.bank()
        topic = (topic or '').strip() or 'Untitled design'
        session_id = uid()
        ids = [q['id'] for q in bank['questions']][:BATCH_TARGET]
        with self.store.transaction() as db:
            db.execute('INSERT INTO vetting_sessions(id,project_id,conversation_id,template,topic,state,'
                       'current_batch,created,updated) VALUES(?,?,?,?,?,?,?,?,?)',
                       (session_id, project_id, conversation, bank['template'], topic, 'ACTIVE', 1,
                        time.time(), time.time()))
            self._materialize(db, session_id, ids, 1)
            self._event(db, session_id, 'session_started', actor, {'topic': topic, 'template': bank['template']})
            questions = self._questions(db, session_id)
            batch = _row(db.execute('SELECT * FROM vetting_batches WHERE session_id=? AND ordinal=1',
                                    (session_id,)).fetchone())
        message = self._format_batch(topic, bank['name'], batch, questions)
        return {'session_id': session_id, 'topic': topic, 'batch': batch['ordinal'],
                'question_ids': ids, 'message': message}

    def _materialize(self, db, session_id, ids, ordinal):
        bank = self.bank()
        batch_id = uid()
        db.execute('INSERT INTO vetting_batches(id,session_id,ordinal,title,question_ids,created)'
                   ' VALUES(?,?,?,?,?,?)',
                   (batch_id, session_id, ordinal, 'Batch %d' % ordinal, json.dumps(ids), time.time()))
        for qid in ids:
            source = bank_mod.question_by_id(bank, qid)
            if not source:
                continue
            db.execute(
                'INSERT OR IGNORE INTO vetting_questions(id,session_id,bank_id,section,ordinal,prompt,explain,'
                'visual,open,options,created) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (qid, session_id, qid, source.get('section', ''), len(ids), source['prompt'],
                 source.get('explain', ''), 1 if source.get('visual') else 0, 1 if source.get('open') else 0,
                 json.dumps(source.get('options', [])), time.time()))
        return batch_id

    def _questions(self, db, session_id):
        rows = db.execute('SELECT * FROM vetting_questions WHERE session_id=? ORDER BY rowid',
                          (session_id,)).fetchall()
        answers = {r['question_id']: _row(r) for r in
                   db.execute('SELECT * FROM vetting_answers WHERE session_id=?', (session_id,)).fetchall()}
        questions = []
        for row in rows:
            question = _row(row)
            question['options'] = _loads(question['options'], [])
            question['traits'] = {}
            answer = answers.get(question['id'])
            if answer:
                question['answer'] = {'status': answer['status'],
                                      'selected': _loads(answer['selected'], []),
                                      'custom': answer['custom'] or '',
                                      'notes': answer['notes'] or '',
                                      'confidence': answer['confidence'],
                                      'source': answer['source'],
                                      'feedback': _loads(answer['feedback'], {})}
            questions.append(question)
        return questions

    def _answers_map(self, questions):
        answers = {}
        for question in questions:
            answer = question.get('answer')
            if not answer:
                continue
            answers[question['id']] = {'status': answer['status'], 'selected': answer['selected'],
                                       'selected_options': answer['selected'], 'custom': answer['custom'],
                                       'custom_answer': answer['custom'], 'notes': answer['notes'],
                                       'confidence': answer['confidence'],
                                       'feedback': answer.get('feedback') or {}}
        return answers

    # ---- batch messages ---------------------------------------------------------------------

    def _format_batch(self, topic, template_name, batch, questions):
        ids = _loads(batch['question_ids'], [])
        by_id = {q['id']: q for q in questions}
        lines = ['**Design vetting — %s** · %s · %s' % (topic, template_name, batch['title']), '',
                 'Answer as many as you like in any order — reply with numbers, e.g. `12: F`, '
                 '`13: D`, `14: C`. No need to wait between answers; say **process answers** when done, '
                 'or **finish spec now** at any point.', '']
        for qid in ids:
            question = by_id.get(qid)
            if not question:
                continue
            lines.append('**%s — %s**' % (qid, question['prompt']))
            if question.get('open'):
                lines.append('  (open answer — write it in your own words)')
            for option in question['options']:
                tags = option.get('tags') or {}
                suffix = ''
                if tags.get('recommended'):
                    suffix = ' — **Recommended**: %s' % tags['recommended']
                elif tags.get('label_alt'):
                    suffix = ' — _%s_' % tags['label_alt']
                lines.append('  %s. %s%s' % (option['code'], option['label'], suffix))
            lines.append('')
        lines.append('_Also available: `show unanswered only` · `view decisions` · `preview spec` · '
                     '`pause vetting` · `show greyboxes` · `explain 12` · `more options for 12` · '
                     '`challenge 12`._')
        return '\n'.join(lines)

    HANDLED_STATUSES = ('ANSWERED', 'PARTIALLY_ANSWERED', 'SKIPPED', 'DEFERRED', 'UNSURE',
                        'NEEDS_EXAMPLES', 'NEEDS_GREYBOX', 'AWAITING_VISUAL_SELECTION', 'CONFLICTING')

    def _progress(self, questions):
        ids = [q['id'] for q in questions]
        answered = [q for q in questions if (q.get('answer') or {}).get('status') in
                    ('ANSWERED', 'PARTIALLY_ANSWERED')]
        handled = [q for q in questions if (q.get('answer') or {}).get('status') in self.HANDLED_STATUSES]
        return {'answered': len(answered), 'handled': len(handled), 'total': len(ids),
                'open': [q['id'] for q in questions if not q.get('answer') or
                         (q.get('answer') or {}).get('status') not in self.HANDLED_STATUSES]}

    def _format_resurface(self, questions):
        progress = self._progress(questions)
        if not progress['open']:
            return 'Every question in this batch has an answer. Say **process answers** for the next batch.'
        sample = ', '.join('`%s`' % qid for qid in progress['open'][:8])
        return ('Still waiting on %d answer(s): %s. Reply with numbers like `%s: B`, or say '
                '**process answers** / **finish spec now**.' %
                (len(progress['open']), sample, progress['open'][0].lstrip('Q')))

    # ---- chat routing (start / controls / answers) -------------------------------------------

    def ingest_chat(self, conversation, text, project_id=None, source='chat'):
        """The chat path: start intents, controls, then answers. Returns kind + message."""
        text = (text or '').strip()
        if not text:
            return {'kind': 'none'}
        session = self.active(conversation)
        if not session:
            match = START_RE.search(text)
            if match:
                topic = (match.groupdict().get('topic') or '').strip()
                result = self.start(project_id or self._project_of(conversation), conversation, topic)
                return {'kind': 'started', 'session_id': result['session_id'],
                        'progress': {'answered': 0, 'total': len(result['question_ids']),
                                     'open': result['question_ids']},
                        'message': result['message']}
            return {'kind': 'none'}
        verb, arg = parse_control(text)
        if verb:
            return self._control(session, verb, arg, source)
        result = self.ingest(session['id'], text, source)
        if result['applied']['applied'] or result['conflicts_open']:
            message = 'Recorded: %d of %d recorded.' % (result['progress']['handled'],
                                                        result['progress']['total'])
            if result['conflicts_open']:
                latest = result['conflicts_open'][-1]
                message += (' A conflict is open: ' + latest['statement'] +
                            ' Reply: keep earlier / use newer / show tradeoff / resolve later.')
            elif result['progress']['open']:
                if result['progress']['answered'] >= result['progress']['total'] - 2:
                    message += ' Almost done — say “process answers” when ready.'
            else:
                message += ' All questions in this batch answered — say “process answers”.'
            return {'kind': 'ingested', 'session_id': session['id'], 'progress': result['progress'],
                    'message': message, 'applied': result['applied']['applied']}
        if result['pending_proposals']:
            picks = ', '.join('%s → %s' % (p['question_id'], p['option'])
                              for p in result['pending_proposals'])
            return {'kind': 'proposal', 'session_id': session['id'], 'progress': result['progress'],
                    'proposals': result['pending_proposals'],
                    'message': 'Possible match: %s. Say “yes” to confirm, or correct it (e.g. “13: D”).'
                               % picks}
        if result['unmatched']:
            # Neither answers nor a control: let normal chat serve it; the host resurfaces the
            # open prompts when that reply finishes.
            return {'kind': 'none', 'unparsed': True, 'progress': result['progress']}
        return {'kind': 'none'}

    def _project_of(self, conversation):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT project_id FROM conversations WHERE id=?', (conversation,)).fetchone()
        return (row['project_id'] if row else None) or 'default'

    def _control(self, session, verb, arg, source):
        sid = session['id']
        if verb == 'process':
            result = self.process(sid)
            return {'kind': 'control', 'verb': verb, 'session_id': sid,
                    'message': result['message'], 'progress': result['progress']}
        if verb == 'finish_spec':
            result = self.finish(sid)
            return {'kind': 'control', 'verb': verb, 'session_id': sid, 'spec_id': result['spec_id'],
                    'message': result['message']}
        if verb == 'pause':
            with self.store.transaction() as db:
                db.execute("UPDATE vetting_sessions SET state='PAUSED', updated=? WHERE id=?",
                           (time.time(), sid))
                self._event(db, sid, 'paused', source)
            return {'kind': 'control', 'verb': verb,
                    'message': 'Vetting is paused. Say “continue this vetting session” to pick it back up.'}
        if verb in ('resume', 'show_unanswered', 'open_questions', 'preview_spec', 'decisions'):
            with self.store.transaction() as db:
                if verb == 'resume':
                    db.execute("UPDATE vetting_sessions SET state='ACTIVE', updated=? WHERE id=?",
                               (time.time(), sid))
                    self._event(db, sid, 'resumed', source)
                questions = self._questions(db, sid)
            if verb == 'show_unanswered':
                progress = self._progress(questions)
                listing = ', '.join('`%s`' % q for q in progress['open']) or 'none'
                return {'kind': 'control', 'verb': verb,
                        'message': 'Unanswered: %s.' % listing}
            if verb == 'open_questions':
                return {'kind': 'control', 'verb': verb, 'message': self._open_text(questions, sid)}
            if verb == 'preview_spec':
                markdown = self.preview(sid)
                head = '\n'.join(markdown.splitlines()[:40])
                return {'kind': 'control', 'verb': verb,
                        'message': 'Spec preview (first part; the full spec is in the Vetting panel):\n\n' + head}
            if verb == 'decisions':
                return {'kind': 'control', 'verb': verb, 'message': self._decisions_text(sid)}
            return {'kind': 'control', 'verb': verb, 'message': self._format_resurface(questions)}
        if verb == 'greybox' or verb in ('help_explain', 'help_more', 'help_challenge'):
            qid = ('Q' + arg) if arg else ''
            if not qid or not self._question_exists(sid, qid):
                return {'kind': 'control', 'verb': verb,
                        'message': 'Which question? For example: “show greyboxes 19”, “explain 12”, '
                                   '“more options for 12”, “challenge 12”.'}
            if verb == 'greybox':
                payload = self.greybox(sid, qid, action='design')
                with self.store.transaction() as db:
                    self._apply_updates(db, self.session(sid, db), [{
                        'question_id': qid, 'status': 'AWAITING_VISUAL_SELECTION', 'selected': [],
                        'custom': '', 'notes': 'greyboxes requested', 'confidence': 'EXPLICIT',
                        'source': source, 'feedback': {'greybox_request': True}}])
                return {'kind': 'control', 'verb': verb, 'greybox': payload,
                        'message': 'Generated %d greybox direction(s) for %s — open the Vetting panel and '
                                   'compare them (%s stays open until you pick).'
                                   % (len(payload['directions']), qid, qid)}
            kind = {'help_explain': 'explain', 'help_more': 'more_options',
                    'help_challenge': 'challenge'}[verb]
            return {'kind': 'control', 'verb': verb, 'message': self.help(sid, qid, kind)['text']}
        if verb in ('confirm', 'reject'):
            result = self.apply_pending(sid, accept=(verb == 'confirm'), source=source)
            return {'kind': 'control', 'verb': verb, 'message': result['message'],
                    'applied': result.get('applied', [])}
        return {'kind': 'control', 'verb': verb,
                'message': 'Controls: process answers · finish spec now · preview spec · view decisions · '
                           'show unanswered · pause vetting · show greyboxes 19.'}

    def _question_exists(self, session_id, qid):
        with contextlib.closing(self.store.connect()) as db:
            return db.execute('SELECT 1 FROM vetting_questions WHERE session_id=? AND id=?',
                              (session_id, qid)).fetchone() is not None

    def _open_text(self, questions, session_id):
        lines = ['Open questions:']
        for question in questions:
            answer = question.get('answer') or {}
            if answer.get('status') in ('ANSWERED', 'PARTIALLY_ANSWERED', 'SKIPPED', 'DEFERRED'):
                continue
            lines.append('- %s — %s (%s)' % (question['id'], question['prompt'],
                                              answer.get('status') or 'UNANSWERED'))
        pending = self._pending(session_id)
        if pending:
            lines.append('Waiting for your confirmation: ' +
                         ', '.join('%s → %s' % (p['question_id'], p['option']) for p in pending))
        conflicts = []
        with contextlib.closing(self.store.connect()) as db:
            conflicts = [_row(r) for r in db.execute(
                "SELECT * FROM vetting_conflicts WHERE session_id=? AND state='OPEN'", (session_id,)).fetchall()]
        for conflict in conflicts:
            lines.append('- CONFLICT: ' + conflict['statement'])
        return '\n'.join(lines) if len(lines) > 1 else 'No open questions — everything has an answer.'

    def _decisions_text(self, session_id):
        with contextlib.closing(self.store.connect()) as db:
            rows = [_row(r) for r in db.execute(
                "SELECT * FROM vetting_decisions WHERE session_id=? AND status='CONFIRMED' ORDER BY created",
                (session_id,)).fetchall()]
        if not rows:
            return 'No decisions recorded yet.'
        return 'Decisions so far:\n' + '\n'.join('- %s' % row['statement'] for row in rows)

    # ---- synthesis, spec, panel, help, greybox -----------------------------------------------

    def _synthesis(self, db, questions, session_id):
        decisions = [_row(r) for r in db.execute(
            "SELECT * FROM vetting_decisions WHERE session_id=? AND status='CONFIRMED' ORDER BY created",
            (session_id,)).fetchall()]
        conflicts = [_row(r) for r in db.execute(
            "SELECT * FROM vetting_conflicts WHERE session_id=? AND state='OPEN'", (session_id,)).fetchall()]
        progress = self._progress(questions)
        open_status = [q for q in questions if (q.get('answer') or {}).get('status') in
                       ('UNSURE', 'NEEDS_EXAMPLES', 'NEEDS_GREYBOX', 'AWAITING_VISUAL_SELECTION',
                        'CONFLICTING', 'DEFERRED')]
        lines = ['**Synthesis** — %d of %d answered.' % (progress['answered'], progress['total'])]
        if decisions:
            lines.append('Resolved:')
            lines += ['- %s' % d['statement'] for d in decisions[-8:]]
        if open_status:
            lines.append('Needs you:')
            for question in open_status[:8]:
                lines.append('- %s — %s (%s)' % (question['id'], question['prompt'],
                                                 question['answer']['status']))
        if conflicts:
            lines.append('Conflicts to resolve: ' + ' | '.join(c['statement'] for c in conflicts[:3]))
        return '\n'.join(lines)

    def process(self, session_id):
        with self.store.transaction() as db:
            session = self.session(session_id, db)
            if not session:
                raise PolicyError('Vetting session not found')
            questions = self._questions(db, session_id)
            used = set()
            for batch in db.execute('SELECT question_ids FROM vetting_batches WHERE session_id=?',
                                    (session_id,)).fetchall():
                used.update(_loads(batch['question_ids'], []))
            answered_ids = [q['id'] for q in questions if (q.get('answer') or {}).get('status') in
                            ('ANSWERED', 'PARTIALLY_ANSWERED')]
            next_ids = bank_mod.adapt(self.bank(), answered_ids, self._answers_map(questions),
                                      used)[:BATCH_TARGET]
            synthesis = self._synthesis(db, questions, session_id)
            if next_ids:
                ordinal = int(session['current_batch'] or 1) + 1
                self._materialize(db, session_id, next_ids, ordinal)
                db.execute('UPDATE vetting_sessions SET current_batch=?, updated=? WHERE id=?',
                           (ordinal, time.time(), session_id))
                self._event(db, session_id, 'batch_processed', 'user',
                            {'ordinal': ordinal, 'next': next_ids})
            else:
                self._event(db, session_id, 'batch_processed', 'user', {'next': []})
            questions = self._questions(db, session_id)
            progress = self._progress(questions)
            batch = _row(db.execute('SELECT * FROM vetting_batches WHERE session_id=?'
                                    ' ORDER BY ordinal DESC LIMIT 1', (session_id,)).fetchone())
            batch_questions = [q for q in questions if q['id'] in _loads(batch['question_ids'], [])]
        if next_ids:
            body = self._format_batch(session['topic'], self.bank()['name'], batch, batch_questions)
            message = synthesis + '\n\n' + body
        else:
            message = (synthesis + '\n\nEvery question in this template now has an answer — '
                       'say **finish spec now** to generate the specification.')
        return {'message': message, 'progress': progress, 'batch': batch['ordinal'],
                'question_ids': next_ids}

    def finish(self, session_id):
        with self.store.transaction() as db:
            session = self.session(session_id, db)
            if not session:
                raise PolicyError('Vetting session not found')
            questions = self._questions(db, session_id)
            decisions = [_row(r) for r in db.execute('SELECT * FROM vetting_decisions WHERE session_id=?',
                                                     (session_id,)).fetchall()]
            conflicts = [_row(r) for r in db.execute('SELECT * FROM vetting_conflicts WHERE session_id=?',
                                                     (session_id,)).fetchall()]
            greyboxes = [_row(r) for r in db.execute('SELECT * FROM vetting_greyboxes WHERE session_id=?',
                                                     (session_id,)).fetchall()]
            markdown = spec_mod.build_spec_markdown(session['topic'], self.bank()['name'], questions,
                                                    decisions, conflicts, greyboxes, 'FINISHED')
            coverage = spec_mod.coverage_summary(questions)
            spec_id = uid()
            db.execute('INSERT INTO vetting_specs(id,session_id,markdown,coverage,created)'
                       ' VALUES(?,?,?,?,?)',
                       (spec_id, session_id, markdown, json.dumps(coverage), time.time()))
            db.execute("UPDATE vetting_sessions SET state='FINISHED', updated=? WHERE id=?",
                       (time.time(), session_id))
            self._event(db, session_id, 'spec_snapshot', 'user',
                        {'spec_id': spec_id, 'coverage': coverage})
        message = ('**Spec snapshot saved** — coverage %d/%d. Open questions: %d · deferred/skipped: %d.'
                   ' Say “preview spec”, or open the Vetting panel to read it.' %
                   (coverage['answered'], coverage['total'], coverage['open'],
                    coverage['deferred'] + coverage['skipped']))
        return {'spec_id': spec_id, 'coverage': coverage, 'message': message}

    def preview(self, session_id):
        with contextlib.closing(self.store.connect()) as db:
            spec = _row(db.execute('SELECT * FROM vetting_specs WHERE session_id=?'
                                   ' ORDER BY created DESC LIMIT 1', (session_id,)).fetchone())
            if spec:
                return spec['markdown']
            session = self.session(session_id, db)
            if not session:
                raise PolicyError('Vetting session not found')
            questions = self._questions(db, session_id)
            decisions = [_row(r) for r in db.execute('SELECT * FROM vetting_decisions WHERE session_id=?',
                                                     (session_id,)).fetchall()]
            conflicts = [_row(r) for r in db.execute('SELECT * FROM vetting_conflicts WHERE session_id=?',
                                                     (session_id,)).fetchall()]
            greyboxes = [_row(r) for r in db.execute('SELECT * FROM vetting_greyboxes WHERE session_id=?',
                                                     (session_id,)).fetchall()]
        return spec_mod.build_spec_markdown(session['topic'], self.bank()['name'], questions, decisions,
                                            conflicts, greyboxes, session['state'])

    def panel(self, conversation=None, session_id=None):
        with contextlib.closing(self.store.connect()) as db:
            session = self.session(session_id, db) if session_id else self.active(conversation, db)
            cross = False
            if not session and conversation:
                # A finished or paused session stays reachable: the panel keeps showing its
                # decisions, open questions, greyboxes and the spec snapshot after the run ends.
                session = _row(db.execute(
                    'SELECT * FROM vetting_sessions WHERE conversation_id=? ORDER BY created DESC LIMIT 1',
                    (conversation,)).fetchone())
            if not session:
                # The drawer may be pointed at a different conversation than the one the session
                # lives in (or a fresh conversation after a reload). Showing the latest session
                # with its topic beats showing nothing; the payload marks the cross-conversation
                # case so a surface can say where it came from.
                session = _row(db.execute(
                    "SELECT * FROM vetting_sessions WHERE state IN ('ACTIVE','PAUSED')"
                    ' ORDER BY created DESC LIMIT 1').fetchone())
                if session:
                    cross = session['conversation_id'] != conversation
            if not session:
                session = _row(db.execute(
                    'SELECT * FROM vetting_sessions ORDER BY created DESC LIMIT 1').fetchone())
                if session:
                    cross = session['conversation_id'] != conversation
            if not session:
                return {'session': None}
            questions = self._questions(db, session['id'])
            progress = self._progress(questions)
            decisions = [_row(r) for r in db.execute(
                "SELECT * FROM vetting_decisions WHERE session_id=? AND status='CONFIRMED' ORDER BY created",
                (session['id'],)).fetchall()]
            conflicts = [_row(r) for r in db.execute(
                "SELECT * FROM vetting_conflicts WHERE session_id=? AND state='OPEN'",
                (session['id'],)).fetchall()]
            specs = [_row(r) for r in db.execute(
                'SELECT id, coverage, created FROM vetting_specs WHERE session_id=?'
                ' ORDER BY created DESC LIMIT 1', (session['id'],)).fetchall()]
            batches = [_row(r) for r in db.execute(
                'SELECT ordinal, question_ids FROM vetting_batches WHERE session_id=? ORDER BY ordinal',
                (session['id'],)).fetchall()]
            greyboxes = [_row(r) for r in db.execute(
                'SELECT id, question_id, name, description, svg, is_base FROM vetting_greyboxes'
                ' WHERE session_id=? ORDER BY created DESC LIMIT 12', (session['id'],)).fetchall()]
        pending = self._pending(session['id'])
        return {'session': session, 'cross_conversation': cross, 'progress': progress,
                'questions': [{'id': q['id'], 'section': q['section'], 'prompt': q['prompt'],
                               'visual': q['visual'], 'open': q['open'], 'options': q['options'],
                               'answer': q.get('answer')} for q in questions],
                'unanswered': [q['id'] for q in questions if not q.get('answer') or
                               (q.get('answer') or {}).get('status') not in
                               ('ANSWERED', 'PARTIALLY_ANSWERED', 'SKIPPED', 'DEFERRED')],
                'decisions': decisions, 'conflicts': conflicts, 'spec': specs[0] if specs else None,
                'batches': batches, 'greyboxes': greyboxes, 'pending': pending}

    def help(self, session_id, question_id, kind):
        with self.store.transaction() as db:
            session = self.session(session_id, db)
            questions = {q['id']: q for q in self._questions(db, session_id)}
            question = questions.get(question_id)
            if not session or not question:
                raise PolicyError('Question not found in this session')
            source = bank_mod.question_by_id(self.bank(), question['bank_id']) or {}
            answer = question.get('answer') or {}
            if kind == 'explain':
                plain = source.get('explain') or 'This question pins down one design decision.'
                why = source.get('rationale') or 'it constrains later choices.'
                text = ('**%s — %s**\n\nIn plain words: %s\n\nWhy it matters: %s\n\nStill yours to decide: '
                        'answer with a letter (`%s: A`), “none of these …”, “skip”, or “I am not sure”.'
                        % (question['id'], question['prompt'], plain, why, question['id'].lstrip('Q')))
            elif kind == 'more_options':
                drafts = spec_mod.new_option_drafts(question)
                lines = ['**%s — more directions** (genuinely new, not rephrased):' % question['id']]
                lines += ['- %s — %s (%s)' % (d['label'], d['desc'], d['why_distinct']) for d in drafts]
                lines.append('Answer with a letter from a next batch, or write your own direction.')
                text = '\n'.join(lines)
            elif kind == 'challenge':
                text = spec_mod.challenge_text(question, answer.get('selected') or [])
            else:
                text = 'Nothing to add — your call stands.'
            db.execute('INSERT INTO vetting_help(session_id,question_id,kind,detail,at) VALUES(?,?,?,?,?)',
                       (session_id, question_id, kind, text[:4000], time.time()))
            self._event(db, session_id, 'help_' + kind, 'user', {'question_id': question_id})
        return {'question_id': question_id, 'kind': kind, 'text': text}

    def conflict_action(self, session_id, conflict_id, choice):
        with self.store.transaction() as db:
            conflict = _row(db.execute('SELECT * FROM vetting_conflicts WHERE id=? AND session_id=?',
                                       (conflict_id, session_id)).fetchone())
            if not conflict:
                raise PolicyError('Conflict not found')
            if choice == 'show_tradeoff':
                return {'message': self._tradeoff(conflict), 'state': conflict['state']}
            if choice == 'resolve_later':
                self._event(db, session_id, 'conflict_deferred', 'user', {'conflict': conflict_id})
                return {'message': 'Left open — it stays in Open questions until you decide.',
                        'state': conflict['state']}
            if choice == 'keep_earlier':
                revision = db.execute('SELECT * FROM vetting_answer_revisions WHERE session_id=?'
                                      ' AND question_id=? ORDER BY seq DESC LIMIT 1',
                                      (session_id, conflict['question_b'])).fetchone()
                if revision:
                    previous = _loads(revision['previous'], {})
                    db.execute('UPDATE vetting_answers SET status=?, selected=?, custom=?, updated=?'
                               ' WHERE question_id=? AND session_id=?',
                               (previous.get('status', 'ANSWERED'),
                                json.dumps(previous.get('selected', [])), previous.get('custom', ''),
                                time.time(), conflict['question_b'], session_id))
                    message = ('Kept the earlier choice; %s reads its previous answer again.'
                               % conflict['question_b'])
                else:
                    # The newer answer was the first one; it is parked, not silently dropped.
                    db.execute('UPDATE vetting_answers SET status=?, custom=?, updated=?'
                               ' WHERE question_id=? AND session_id=?',
                               ('DEFERRED', 'parked until a choice compatible with the earlier decision',
                                time.time(), conflict['question_b'], session_id))
                    message = ('Kept the earlier choice; %s is parked as deferred — answer it again with '
                               'the earlier choice in mind.' % conflict['question_b'])
                resolution = 'keep_earlier'
            elif choice == 'use_newer':
                db.execute("UPDATE vetting_decisions SET status='SUPERSEDED', updated=?"
                           " WHERE question_id=? AND session_id=? AND status='CONFIRMED'",
                           (time.time(), conflict['question_a'], session_id))
                db.execute("UPDATE vetting_answers SET status='ANSWERED', updated=?"
                           ' WHERE question_id=? AND session_id=?',
                           (time.time(), conflict['question_b'], session_id))
                resolution = 'use_newer'
                message = 'Using the newer choice; the earlier decision is superseded.'
            else:
                raise PolicyError('Resolution must be keep_earlier, use_newer, show_tradeoff,'
                                  ' or resolve_later')
            db.execute("UPDATE vetting_conflicts SET state='RESOLVED', resolution=?, resolved_at=?"
                       ' WHERE id=?', (resolution, time.time(), conflict_id))
            self._event(db, session_id, 'conflict_resolved', 'user',
                        {'conflict': conflict_id, 'resolution': resolution})
        return {'message': message, 'state': 'RESOLVED'}

    def _tradeoff(self, conflict):
        return ('Tradeoff: “%s” was chosen earlier; “%s” came later. Keeping the earlier choice keeps '
                'consistency with what was already decided; the newer choice reflects what you now know. '
                'Nothing is applied silently — pick keep earlier / use newer / resolve later.'
                % (conflict['question_a'], conflict['question_b']))

    def greybox(self, session_id, question_id, action='design', feedback_kind='', greybox_id='', note=''):
        with self.store.transaction() as db:
            session = self.session(session_id, db)
            questions = {q['id']: q for q in self._questions(db, session_id)}
            question = questions.get(question_id)
            if not session or not question:
                raise PolicyError('Question not found in this session')
            if action == 'design':
                traits = self._traits_from_answers(list(questions.values()))
                directions = spec_mod.greybox_directions(question, traits)
                rows = []
                for direction in directions:
                    box_id = uid()
                    svg = spec_mod.greybox_svg(direction)
                    db.execute('INSERT INTO vetting_greyboxes(id,session_id,question_id,name,description,'
                               'traits,svg,is_base,composite_of,created) VALUES(?,?,?,?,?,?,?,?,?,?)',
                               (box_id, session_id, question_id, direction['name'],
                                direction['description'], json.dumps(direction['traits']), svg, 0, '[]',
                                time.time()))
                    rows.append({'id': box_id, 'name': direction['name'],
                                 'description': direction['description'], 'svg': svg})
                self._event(db, session_id, 'greybox_design', 'user',
                            {'question_id': question_id, 'count': len(rows)})
                return {'question_id': question_id, 'directions': rows}
            if action == 'feedback':
                if not greybox_id:
                    raise PolicyError('Choose a direction first')
                db.execute('INSERT INTO vetting_greybox_feedback(greybox_id,session_id,kind,note,at)'
                           ' VALUES(?,?,?,?,?)',
                           (greybox_id, session_id, feedback_kind or 'compare', note[:500], time.time()))
                if feedback_kind == 'choose_base':
                    db.execute('UPDATE vetting_greyboxes SET is_base=0 WHERE session_id=? AND question_id=?',
                               (session_id, question_id))
                    db.execute('UPDATE vetting_greyboxes SET is_base=1 WHERE id=?', (greybox_id,))
                    name = db.execute('SELECT name FROM vetting_greyboxes WHERE id=?',
                                      (greybox_id,)).fetchone()['name']
                    self._apply_updates(db, session, [{
                        'question_id': question_id, 'status': 'ANSWERED', 'selected': [],
                        'custom': 'Greybox direction chosen: ' + name, 'notes': '',
                        'confidence': 'EXPLICIT', 'source': 'api',
                        'feedback': {'greybox_choice': greybox_id}}])
                    self._event(db, session_id, 'greybox_chosen', 'user',
                                {'question_id': question_id, 'greybox': greybox_id})
                    return {'question_id': question_id, 'chosen': greybox_id, 'name': name}
                self._event(db, session_id, 'greybox_feedback', 'user',
                            {'question_id': question_id, 'kind': feedback_kind})
                return {'question_id': question_id, 'recorded': feedback_kind}
            if action == 'combine':
                roles = spec_mod.parse_combine(note)
                if not roles:
                    raise PolicyError('Describe the combination like “Direction 4 -> base”')
                rows = [_row(r) for r in db.execute(
                    'SELECT * FROM vetting_greyboxes WHERE session_id=? AND question_id=? ORDER BY created',
                    (session_id, question_id)).fetchall()]
                if not rows:
                    raise PolicyError('Generate greyboxes for this question first')
                composite = spec_mod.combine_directions(rows, roles)
                box_id = uid()
                svg = spec_mod.greybox_svg(composite)
                db.execute('INSERT INTO vetting_greyboxes(id,session_id,question_id,name,description,traits,'
                           'svg,is_base,composite_of,created) VALUES(?,?,?,?,?,?,?,?,?,?)',
                           (box_id, session_id, question_id, composite['name'],
                            composite['description'], json.dumps(composite['traits']), svg, 0,
                            json.dumps(composite.get('composite_of') or []), time.time()))
                self._event(db, session_id, 'greybox_combined', 'user',
                            {'question_id': question_id, 'sources': composite.get('composite_of')})
                return {'question_id': question_id,
                        'composite': {'id': box_id, 'name': composite['name'],
                                      'description': composite['description'], 'svg': svg}}
        raise PolicyError('Unknown greybox action')

    def _traits_from_answers(self, questions):
        traits = {}
        for question in questions:
            answer = question.get('answer') or {}
            labels = ' '.join(o['label'].lower() for o in question['options']
                              if o['code'] in (answer.get('selected') or []))
            if question['id'] == 'Q6':
                traits['nav'] = ('left rail' if 'sidebar' in labels else
                                 'top bar' if 'top bar' in labels else
                                 'none' if 'no nav' in labels else 'left rail')
            elif question['id'] == 'Q13':
                traits['density'] = ('progressive' if 'progressive' in labels else
                                     'compact rows' if 'compact' in labels else 'comfortable rows')
            elif question['id'] == 'Q7':
                traits['hero'] = ('summary strip' if 'summary' in labels or 'overview' in labels else
                                  'inbox' if 'inbox' in labels else
                                  'feed' if 'start' in labels or 'empty' in labels else 'board')
        return traits

    # ---- ingestion (the single path every source uses) ---------------------------------------

    def _event(self, db, session_id, action, actor='user', detail=None):
        db.execute('INSERT INTO vetting_events(id,session_id,action,actor,detail,at) VALUES(?,?,?,?,?,?)',
                   (uid(), session_id, action, actor, json.dumps(detail or {}), time.time()))

    def ingest(self, session_id, text, source='chat'):
        """Understand `text` and update the session. Identical for every input source."""
        with self.store.transaction() as db:
            session = self.session(session_id, db)
            if not session:
                raise PolicyError('Vetting session not found')
            questions = self._questions(db, session_id)
            answers = self._answers_map(questions)
            parse = VettingAnswerIngestion(questions, answers).parse(text, source)
            applied = self._apply_updates(db, session, parse['updates'])
            pending = None
            if parse['proposals']:
                pending = parse['proposals']
                self._event(db, session_id, 'proposals_pending', source, {'proposals': pending})
            self._event(db, session_id, 'ingest', source,
                        {'applied': applied['applied'], 'conflicts': applied['conflicts'],
                         'proposals': len(parse['proposals']), 'control': parse['control']})
            questions = self._questions(db, session_id)
            progress = self._progress(questions)
            conflicts = [_row(r) for r in db.execute(
                "SELECT * FROM vetting_conflicts WHERE session_id=? AND state='OPEN'", (session_id,)).fetchall()]
            revisions = [_row(r) for r in db.execute(
                'SELECT seq, id, question_id, reason, source, at FROM vetting_answer_revisions'
                ' WHERE session_id=? ORDER BY seq DESC LIMIT 5', (session_id,)).fetchall()]
        parse['applied'] = applied
        parse['progress'] = progress
        parse['conflicts_open'] = conflicts
        parse['revisions_recent'] = revisions
        parse['pending_proposals'] = pending
        return parse

    def apply_pending(self, session_id, accept=True, source='chat', correction=''):
        """Confirm or reject proposed (low-confidence) mappings. Never auto-applied."""
        with self.store.transaction() as db:
            row = db.execute("SELECT detail FROM vetting_events WHERE session_id=? AND action='proposals_pending'"
                             ' ORDER BY seq DESC LIMIT 1', (session_id,)).fetchone()
            if not row:
                return {'applied': [], 'message': 'Nothing is waiting for a confirmation.'}
            proposals = _loads(row['detail'], {}).get('proposals', [])
            updates = []
            if accept:
                for proposal in proposals:
                    updates.append({'question_id': proposal['question_id'], 'status': 'ANSWERED',
                                    'selected': [proposal['option']], 'custom': '', 'notes': '',
                                    'confidence': 'INFERRED_HIGH_CONFIRMED', 'source': source,
                                    'feedback': {'confirmed_proposal': True}})
            if correction:
                return self.ingest(session_id, correction, source)
            applied = self._apply_updates(db, self.session(session_id, db), updates) if updates else {'applied': []}
            self._event(db, session_id, 'proposals_resolved', source,
                        {'accepted': bool(accept), 'ids': applied.get('applied', [])})
        message = ('Confirmed: ' + ', '.join(applied.get('applied', []))) if accept and applied.get('applied') \
            else 'Left as-is; nothing was applied.'
        return {'applied': applied.get('applied', []), 'message': message}

    def _pending(self, session_id):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute("SELECT detail FROM vetting_events WHERE session_id=? AND action='proposals_pending'"
                             ' ORDER BY seq DESC LIMIT 1', (session_id,)).fetchone()
            resolved = db.execute("SELECT 1 FROM vetting_events WHERE session_id=? AND action='proposals_resolved'"
                                  ' AND seq > (SELECT COALESCE(MAX(seq),0) FROM vetting_events'
                                  "  WHERE session_id=? AND action='proposals_pending' LIMIT 1)",
                                  (session_id, session_id)).fetchone()
        if not row or resolved:
            return []
        return _loads(row['detail'], {}).get('proposals', [])

    def _apply_updates(self, db, session, updates):
        questions = {q['id']: q for q in self._questions(db, session['id'])}
        applied = []
        for update in updates:
            question = questions.get(update['question_id'])
            if not question:
                continue
            previous = _row(db.execute('SELECT * FROM vetting_answers WHERE question_id=? AND session_id=?',
                                       (update['question_id'], session['id'])).fetchone())
            db.execute('INSERT OR REPLACE INTO vetting_answers(question_id,session_id,status,selected,custom,'
                       'notes,confidence,source,feedback,updated) VALUES(?,?,?,?,?,?,?,?,?,?)',
                       (update['question_id'], session['id'], update['status'],
                        json.dumps(update['selected']), update['custom'], update['notes'],
                        update['confidence'], update['source'], json.dumps(update['feedback'] or {}),
                        time.time()))
            if previous and (previous['status'] != update['status'] or
                             _loads(previous['selected'], []) != list(update['selected']) or
                             (previous['custom'] or '') != update['custom']):
                db.execute('INSERT INTO vetting_answer_revisions(id,session_id,question_id,previous,next,reason,'
                           'source,at) VALUES(?,?,?,?,?,?,?,?)',
                           (uid(), session['id'], update['question_id'],
                            json.dumps({'status': previous['status'],
                                        'selected': _loads(previous['selected'], []),
                                        'custom': previous['custom'] or ''}),
                            json.dumps({'status': update['status'], 'selected': update['selected'],
                                        'custom': update['custom']}),
                            update.get('reason') or ('user revised this answer' if update.get('is_revision')
                                                     else 'answer updated'),
                            update['source'], time.time()))
            if update['status'] in ('ANSWERED', 'PARTIALLY_ANSWERED') and (update['selected'] or update['custom'].strip()):
                self._decision_for(db, session, question, update)
            applied.append(update['question_id'])
        conflicts = self._conflict_check(db, session)
        return {'applied': applied, 'conflicts': conflicts}

    def _decision_for(self, db, session, question, update):
        labels, rationales = [], []
        for code in update['selected']:
            option = next((o for o in question['options'] if o['code'] == code), None)
            if not option:
                continue
            labels.append('%s. %s' % (option['code'], option['label']))
            tags = option.get('tags') or {}
            if tags.get('recommended'):
                rationales.append('%s (recommended: %s)' % (option['label'], tags['recommended']))
            elif option.get('desc'):
                rationales.append('%s — %s' % (option['label'], option['desc']))
            elif tags.get('label_alt'):
                rationales.append('%s (%s)' % (option['label'], tags['label_alt']))
        if update['custom'].strip():
            labels.append('Custom: ' + update['custom'].strip())
            rationales.append('User-provided answer')
        if not labels:
            return
        statement = '%s → %s' % (question['prompt'], '; '.join(labels))
        note = update.get('notes') or ''
        rationale = ' · '.join(rationales) + ((' · note: ' + note) if note else '')
        now = time.time()
        db.execute("UPDATE vetting_decisions SET status='SUPERSEDED', updated=?"
                   " WHERE question_id=? AND session_id=? AND status='CONFIRMED'",
                   (now, question['id'], session['id']))
        db.execute('INSERT INTO vetting_decisions(id,session_id,question_id,statement,rationale,status,created,'
                   'updated) VALUES(?,?,?,?,?,?,?,?)',
                   (uid(), session['id'], question['id'], statement, rationale, 'CONFIRMED', now, now))

    def _conflict_check(self, db, session):
        """Surface contradictions between philosophy-level choices. Never overwrite silently."""
        rows = self._questions(db, session['id'])
        chosen = chosen_labels(rows)
        conflicts = []
        for qa, qb in opposition_pairs(chosen):
            existing = db.execute(
                "SELECT 1 FROM vetting_conflicts WHERE session_id=? AND state='OPEN' AND "
                '((question_a=? AND question_b=?) OR (question_a=? AND question_b=?))',
                (session['id'], qa, qb, qb, qa)).fetchone()
            if existing:
                continue
            times = {}
            for qid in (qa, qb):
                row = db.execute('SELECT updated FROM vetting_answers'
                                 ' WHERE question_id=? AND session_id=?',
                                 (qid, session['id'])).fetchone()
                times[qid] = row['updated'] if row else 0
            newer = qa if times.get(qa, 0) >= times.get(qb, 0) else qb
            older = qb if newer == qa else qa
            label_a = chosen.get(older, '')[:80]
            label_b = chosen.get(newer, '')[:80]
            statement = ('Earlier you chose “%s” (%s), but later chose “%s” (%s).'
                         % (label_a, older, label_b, newer))
            db.execute('INSERT INTO vetting_conflicts(id,session_id,question_a,question_b,statement,'
                       'state,created) VALUES(?,?,?,?,?,?,?)',
                       (uid(), session['id'], older, newer, statement, 'OPEN', time.time()))
            db.execute("UPDATE vetting_answers SET status='CONFLICTING' WHERE question_id=? AND session_id=?",
                       (newer, session['id']))
            conflicts.append({'question_a': older, 'question_b': newer, 'statement': statement})
        return conflicts


    # ---- transcripts as an input source (Think Out Loud included) ----------------------------

    def _active_session_any(self, conversation):
        """Transcript actions may arrive from the Transcription tool without a conversation id."""
        session = self.active(conversation) if conversation else None
        if session:
            return session
        with contextlib.closing(self.store.connect()) as db:
            return _row(db.execute(
                "SELECT * FROM vetting_sessions WHERE state IN ('ACTIVE','PAUSED')"
                ' ORDER BY created DESC LIMIT 1').fetchone())

    def preview_transcript(self, conversation, text, mode='answers'):
        """Pure extraction preview: nothing is written; low-confidence stays a proposal.

        The transcript is understood by the SAME VettingAnswerIngestion service that serves typed
        and pasted answers — voice is an input source, never a second parser or engine.
        """
        session = self._active_session_any(conversation)
        if not session:
            raise PolicyError('No vetting session is open. Start one in a chat with '
                              '“start design vetting: …” and speak again.')
        with contextlib.closing(self.store.connect()) as db:
            questions = self._questions(db, session['id'])
            answers = self._answers_map(questions)
            parse = VettingAnswerIngestion(questions, answers).parse(text, 'transcript')
            conflicts = self._preview_conflicts(questions, parse['updates'])
        by_id = {q['id']: q for q in questions}
        preview = []
        for update in parse['updates']:
            question = by_id.get(update['question_id']) or {}
            labels = [o['label'] for o in question.get('options', [])
                      if o['code'] in (update.get('selected') or [])]
            preview.append({'question_id': update['question_id'], 'status': update['status'],
                            'answer': ', '.join(labels) or (update.get('custom') or '').strip()
                                      or '(see note)',
                            'note': (update.get('notes') or update.get('custom') or '').strip(),
                            'confidence': update['confidence']})
        payload = {'session_id': session['id'], 'mode': mode, 'preview': preview,
                   'proposals': parse['proposals'], 'unmatched': parse['unmatched'],
                   'confidence_summary': parse['confidence_summary'],
                   'potential_conflicts': conflicts}
        if mode == 'freethink':
            payload['buckets'] = think_out_loud_buckets(text)
        return payload

    def apply_transcript(self, conversation, text, mode='answers', accept_all=False,
                         then_process=False):
        """Apply a transcript through the normal ingestion; proposals stay proposals unless asked."""
        session = self._active_session_any(conversation)
        if not session:
            raise PolicyError('No vetting session is open. Start one in a chat with '
                              '“start design vetting: …” and speak again.')
        result = self.ingest(session['id'], text, source='transcript')
        accepted = None
        if accept_all:
            accepted = self.apply_pending(session['id'], accept=True, source='transcript')
        result['accepted'] = accepted
        result['mode'] = mode
        if then_process:
            processed = self.process(session['id'])
            result['processed'] = {'message': processed['message'], 'batch': processed['batch'],
                                   'question_ids': processed['question_ids']}
        return result

    def _preview_conflicts(self, questions, updates):
        """Read-only contradiction scan over current answers plus the parsed updates."""
        chosen = chosen_labels(questions, updates)
        found = []
        for qa, qb in opposition_pairs(chosen):
            found.append({'question_a': qa, 'question_b': qb,
                          'statement': 'Earlier answer leans “%s”; this transcript '
                                       'leans “%s”.' % (chosen[qa][:70], chosen[qb][:70])})
        return found[:4]

def snapshot(store, session_id):
    """Canonical session state used for equality checks across input paths and by tests.

    Path A (typed chat through the host/service) and Path B (direct ingestion) must produce
    identical snapshots — that is the abstraction contract of the ingestion service.
    """
    with contextlib.closing(store.connect()) as db:
        answers = {}
        for row in db.execute('SELECT * FROM vetting_answers WHERE session_id=? ORDER BY question_id',
                              (session_id,)).fetchall():
            answers[row['question_id']] = {'status': row['status'],
                                           'selected': _loads(row['selected'], []),
                                           'custom': row['custom'], 'confidence': row['confidence']}
        revisions = [(row['question_id'], _loads(row['previous'], {}).get('status'),
                      _loads(row['next'], {}).get('status'), row['reason'])
                     for row in db.execute('SELECT * FROM vetting_answer_revisions WHERE session_id=?'
                                           ' ORDER BY seq', (session_id,)).fetchall()]
        decisions = [(row['question_id'], row['statement'], row['status'])
                     for row in db.execute('SELECT * FROM vetting_decisions WHERE session_id=?'
                                           ' ORDER BY created', (session_id,)).fetchall()]
        conflicts = [(row['question_a'], row['question_b'], row['state'], row['statement'])
                     for row in db.execute('SELECT * FROM vetting_conflicts WHERE session_id=?'
                                           ' ORDER BY created', (session_id,)).fetchall()]
        unresolved = [row['id'] for row in db.execute(
            'SELECT q.id FROM vetting_questions q WHERE q.session_id=? AND NOT EXISTS ('
            "SELECT 1 FROM vetting_answers a WHERE a.question_id=q.id AND a.status IN "
            "('ANSWERED','PARTIALLY_ANSWERED','SKIPPED','DEFERRED')) ORDER BY q.rowid",
            (session_id,)).fetchall()]
    return {'answers': answers, 'revisions': revisions, 'decisions': decisions,
            'conflicts': conflicts, 'unresolved': unresolved}
