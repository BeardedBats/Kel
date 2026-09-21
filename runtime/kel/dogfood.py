"""Fix Capture (V2.0 preflight): durable dogfood findings, captured inside the app.

One small store, deliberately not an issue tracker: a fix is what Nick said plus the context Kel can
capture by itself (route, element, window, screenshot reference, build). Statuses are exactly
OPEN / BATCHED / FIXED / DISMISSED — no assignees, labels, priorities or workflow states.

Files live under the engine data root (never the source repo):

    <data-root>/dogfood/screenshots/FIX-0001.png     committed screenshots (named by fix id)
    <data-root>/dogfood/tmp/<uuid>.png              in-flight captures (swept when stale)
    <data-root>/dogfood/prompts/<prompt-id>.md      generated fix prompts

The desktop main process writes a capture into `dogfood/tmp/`, and `save` moves it into place under
the fix id — so a screenshot either belongs to a saved fix or is a stale temporary file, never a
half-recorded one. `prepare_prompt` writes the prompt file first and only then marks the included
fixes BATCHED: a failed generation leaves the queue untouched.
"""
import contextlib
import json
import os
import re
import time
from pathlib import Path

from .core import PolicyError

MIGRATION_VERSION = 22
MIGRATION_NAME = 'v20-fix-capture'

STATUSES = ('OPEN', 'BATCHED', 'FIXED', 'DISMISSED')
FIX_ID_RE = re.compile(r'^FIX-(\d{4,})$')
MAX_TRANSCRIPT = 8000
LIST_LIMIT = 500
TMP_MAX_AGE_SECONDS = 24 * 60 * 60

DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations(
    version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT);
CREATE TABLE IF NOT EXISTS dogfood_fixes(
    id TEXT PRIMARY KEY,
    created REAL NOT NULL,
    updated REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN',
    transcript TEXT NOT NULL DEFAULT '',
    screenshot TEXT,
    route TEXT,
    page_title TEXT,
    element TEXT,
    window TEXT,
    diagnostics TEXT,
    project_id TEXT,
    conversation TEXT,
    version TEXT,
    prompt_id TEXT);
CREATE INDEX IF NOT EXISTS dogfood_fixes_by_created ON dogfood_fixes(created DESC);
CREATE INDEX IF NOT EXISTS dogfood_fixes_by_status ON dogfood_fixes(status);
"""


def _table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def ensure_schema(store):
    with store.transaction() as db:
        db.execute('CREATE TABLE IF NOT EXISTS schema_migrations('
                   'version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT)')
        if db.execute('SELECT 1 FROM schema_migrations WHERE version=?', (MIGRATION_VERSION,)).fetchone():
            return False
        fresh = not _table(db, 'jobs')
        for statement in filter(None, (part.strip() for part in DDL.split(';'))):
            db.execute(statement)
        db.execute('INSERT OR IGNORE INTO schema_migrations(version, name, applied, note) VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(),
                    'fresh database' if fresh else 'pre-existing database'))
        return True


def _json(value):
    if value in (None, '', {}):
        return None
    if isinstance(value, str):
        return value[:4000]
    try:
        return json.dumps(value, ensure_ascii=False)[:4000]
    except (TypeError, ValueError):
        return None


def _loads(raw):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def _is_practice_text(value):
    """True when this text is the archived local practice copy (never a person's own words)."""
    from .transcription import FIXTURE_SENTENCES
    probe = ' '.join(str(value or '').split())[:120]
    for sentence in FIXTURE_SENTENCES:
        head = ' '.join(sentence.split())[:40]
        if head and head in probe:
            return True
    return False


class Dogfood:
    """The fix store. Every path it touches is resolved inside the engine data root."""

    def __init__(self, store):
        self.store = store
        ensure_schema(store)
        self.root = Path(store.root)
        self.dogfood = self.root / 'dogfood'
        self.screenshots = self.dogfood / 'screenshots'
        self.tmp = self.dogfood / 'tmp'
        self.prompts = self.dogfood / 'prompts'
        for folder in (self.screenshots, self.tmp, self.prompts):
            folder.mkdir(parents=True, exist_ok=True)

    # -- paths ------------------------------------------------------------------------------------
    def _inside(self, path, folder):
        """Resolve `path` (absolute or data-root-relative) and require it to sit in `folder`."""
        candidate = Path(str(path))
        if not candidate.is_absolute():
            candidate = self.root / candidate
        resolved = candidate.resolve()
        base = folder.resolve()
        if resolved != base and base not in resolved.parents:
            raise PolicyError('That screenshot is not inside Kel data.')
        return resolved

    def relative(self, path):
        return os.path.relpath(str(path), str(self.root)).replace('\\', '/')

    def _sweep_tmp(self, now=None):
        """A capture that never became a fix must not accumulate: drop stale temporaries."""
        now = time.time() if now is None else now
        for entry in self.tmp.glob('*.png'):
            try:
                if now - entry.stat().st_mtime > TMP_MAX_AGE_SECONDS:
                    entry.unlink()
            except OSError:
                continue

    # -- reads ------------------------------------------------------------------------------------
    def _row(self, row):
        item = {
            'id': row['id'],
            'created': row['created'],
            'updated': row['updated'],
            'status': row['status'],
            'transcript': row['transcript'],
            'screenshot': row['screenshot'],
            'route': row['route'],
            'page_title': row['page_title'],
            'element': _loads(row['element']),
            'window': _loads(row['window']),
            'diagnostics': _loads(row['diagnostics']),
            'project_id': row['project_id'],
            'conversation': row['conversation'],
            'version': row['version'],
            'prompt_id': row['prompt_id'],
        }
        item['has_screenshot'] = bool(item['screenshot']) and (self.root / item['screenshot']).is_file()
        return item

    def list(self, status=None):
        self._sweep_tmp()
        clause = ''
        params = ()
        if status:
            if status not in STATUSES:
                raise PolicyError('Unknown fix status')
            clause = ' WHERE status=?'
            params = (status,)
        with contextlib.closing(self.store.connect()) as db:
            rows = db.execute(
                'SELECT * FROM dogfood_fixes' + clause + ' ORDER BY created DESC LIMIT ?',
                params + (LIST_LIMIT,)).fetchall()
            counts = {name: 0 for name in STATUSES}
            for row in db.execute('SELECT status, COUNT(*) AS n FROM dogfood_fixes GROUP BY status'):
                if row['status'] in counts:
                    counts[row['status']] = row['n']
        return {'fixes': [self._row(row) for row in rows], 'counts': counts, 'statuses': list(STATUSES)}

    def get(self, fix_id):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM dogfood_fixes WHERE id=?', (str(fix_id),)).fetchone()
        if not row:
            raise PolicyError('That fix was not found.')
        return self._row(row)

    # -- writes -----------------------------------------------------------------------------------
    def _next_id(self, db):
        current = 0
        for row in db.execute('SELECT id FROM dogfood_fixes'):
            match = FIX_ID_RE.match(str(row['id']))
            if match:
                current = max(current, int(match.group(1)))
        return 'FIX-%04d' % (current + 1)

    def save(self, transcript, *, screenshot=None, route=None, page_title=None, element=None,
             window=None, diagnostics=None, version=None, conversation=None):
        """Store exactly one fix. The screenshot is committed under the fix id, or not at all."""
        text = str(transcript or '').strip()
        if not text:
            raise PolicyError('Record or type what went wrong first.')
        # A fix is Nick's own words. Practice/demo text is never saved as if it were his feedback —
        # not even when a debug build leaves practice mode switched on by accident.
        from .transcription import Transcription
        if not Transcription(self.store).practice_mode() and _is_practice_text(text):
            raise PolicyError("That is Kel's practice text, not your words — record again.")
        if len(text) > MAX_TRANSCRIPT:
            text = text[:MAX_TRANSCRIPT]
        now = time.time()
        project_id = None
        with self.store.transaction() as db:
            fix_id = self._next_id(db)
            stored_screenshot = None
            if screenshot:
                source = self._inside(screenshot, self.tmp)
                if source.is_file():
                    target = self.screenshots / (fix_id + '.png')
                    try:
                        os.replace(str(source), str(target))
                    except OSError:
                        stored_screenshot = None
                    else:
                        stored_screenshot = self.relative(target)
                else:
                    # The capture vanished (or was swept): the fix is still worth saving, and it says
                    # so honestly instead of pointing at a file that is not there.
                    stored_screenshot = None
            if conversation:
                row = db.execute('SELECT project_id FROM conversations WHERE id=?', (str(conversation),)).fetchone()
                project_id = row['project_id'] if row else None
            db.execute(
                'INSERT INTO dogfood_fixes(id, created, updated, status, transcript, screenshot, route,'
                ' page_title, element, window, diagnostics, project_id, conversation, version, prompt_id)'
                ' VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)',
                (fix_id, now, now, 'OPEN', text, stored_screenshot, _short(route, 400), _short(page_title, 200),
                 _json(element), _json(window), _json(diagnostics), project_id,
                 _short(conversation, 120), _short(version, 80)))
        return self.get(fix_id)

    def discard_tmp(self, relpath):
        """Throw away one in-flight capture.

        A cancelled capture must not leave a screenshot behind, and neither may a capture whose fix
        was never saved. Only files inside `dogfood/tmp` can be reached this way.
        """
        if not relpath:
            return {'discarded': False}
        target = self._inside(relpath, self.tmp)
        if not target.is_file():
            return {'discarded': False}
        try:
            target.unlink()
        except OSError:
            return {'discarded': False}
        return {'discarded': True}

    def set_status(self, fix_id, status):
        value = str(status or '').upper()
        if value not in STATUSES:
            raise PolicyError('Unknown fix status')
        with self.store.transaction() as db:
            row = db.execute('SELECT id FROM dogfood_fixes WHERE id=?', (str(fix_id),)).fetchone()
            if not row:
                raise PolicyError('That fix was not found.')
            db.execute('UPDATE dogfood_fixes SET status=?, updated=? WHERE id=?', (value, time.time(), str(fix_id)))
        return self.get(fix_id)

    # -- prompts ----------------------------------------------------------------------------------
    def _prompt_id(self, now):
        stamp = time.strftime('%Y%m%d-%H%M%S', time.localtime(now))
        base = 'PROMPT-' + stamp
        candidate = base
        suffix = 2
        while (self.prompts / (candidate + '.md')).exists():
            candidate = '%s-%d' % (base, suffix)
            suffix += 1
        return candidate

    def _render_prompt(self, prompt_id, fixes):
        lines = [
            '# Kel Fix Prompt — ' + prompt_id,
            '',
            'Kel Fix Capture recorded these findings while Nick used the app. Each one is a real '
            'moment, not a feature request: treat it as evidence and verify it yourself.',
            '',
            '## What to do',
            '',
            '1. Reconcile git and the current product state before changing anything; the findings may '
            'already be fixed or the surrounding code may have moved.',
            '2. Reproduce each finding before editing where practical; if you cannot reproduce one, say '
            'so plainly and say what you saw instead.',
            '3. Group findings that share a root cause and fix the cause once.',
            '4. Do not treat duplicate symptoms as unrelated bugs; say when two findings are one bug.',
            '5. Implement the smallest coherent fixes that satisfy the product intent — no speculative '
            'features, no unrelated refactors.',
            "6. Preserve Kel's product north star: one capable assistant with hidden orchestration; "
            'plain language on every surface a person reads.',
            '7. Add or update regression coverage for each fixed finding (engine and desktop as '
            'applicable), including a pin for any user-visible sentence you change.',
            '8. Verify the affected UI directly — build the app, drive the real surface, and confirm '
            'the fix with your own eyes, not only with tests.',
            '9. Do not mark a fix resolved merely because code changed: a fix counts only when the '
            'reported behaviour is verified gone.',
            '10. Return the exact Fix ids you verified as repaired, and the ids you could not verify, '
            'with one sentence each.',
            '',
            'Screenshots are stored in the Kel data root under `dogfood/screenshots/<FIX-ID>.png` '
            '(never in the repository); each finding below names its file and the selected target '
            'rectangle relative to that image.',
            '',
            '## Findings (' + str(len(fixes)) + ')',
            '',
        ]
        for item in fixes:
            element = item.get('element') or {}
            window = item.get('window') or {}
            lines += [
                '### ' + item['id'] + ' — ' + _short(element.get('text') or item.get('route') or 'Kel', 90),
                '',
                '- Nick said: "' + ' '.join(str(item['transcript']).split()) + '"',
                '- Captured: ' + _iso(item['created']) + ' (Kel ' + str(item.get('version') or 'unknown') + ')',
                '- Route: ' + str(item.get('route') or 'unknown') +
                ((' — ' + str(item.get('page_title'))) if item.get('page_title') else ''),
                '- Selected target: ' + _target_sentence(element),
            ]
            if element.get('selector'):
                lines.append('- Locator: `' + str(element['selector']) + '`')
            if element.get('rect'):
                rect = element['rect']
                lines.append('- Target box (relative to the screenshot): x=%s y=%s w=%s h=%s' % (
                    rect.get('x'), rect.get('y'), rect.get('width'), rect.get('height')))
            if window:
                lines.append('- Window: %sx%s at scale %s' % (
                    window.get('width'), window.get('height'), window.get('scale', 1)))
            if item.get('has_screenshot'):
                lines.append('- Screenshot: `' + str(item['screenshot']) + '`')
            else:
                lines.append('- Screenshot: none (the capture did not survive; reproduce from the description)')
            if item.get('project_id'):
                lines.append('- Project: ' + str(item['project_id']) +
                             ((' · conversation ' + str(item['conversation'])) if item.get('conversation') else ''))
            lines.append('')
        lines += [
            '## Recording (for your report)',
            '',
            '- Status of each finding after your work: repaired / not reproducible / deferred, with the '
            'Fix id and one sentence.',
            '- If a finding turns out to be a duplicate of another, name both ids.',
            '',
        ]
        return '\n'.join(lines)

    def prepare_prompt(self, fix_ids=None):
        """Generate one prompt for the selected OPEN fixes; mark them BATCHED only after it is written."""
        with contextlib.closing(self.store.connect()) as db:
            rows = db.execute("SELECT * FROM dogfood_fixes WHERE status='OPEN' ORDER BY id").fetchall()
        available = [self._row(row) for row in rows]
        if fix_ids:
            wanted = [str(item) for item in fix_ids]
            available = [item for item in available if item['id'] in wanted]
        if not available:
            raise PolicyError('No open fixes to include — capture one first.')
        now = time.time()
        prompt_id = self._prompt_id(now)
        text = self._render_prompt(prompt_id, available)
        target = self.prompts / (prompt_id + '.md')
        try:
            target.write_text(text, encoding='utf-8')
        except OSError as exc:
            raise PolicyError('Kel could not write the fix prompt: ' + str(exc)) from None
        ids = [item['id'] for item in available]
        with self.store.transaction() as db:
            for fix_id in ids:
                db.execute('UPDATE dogfood_fixes SET status=?, updated=?, prompt_id=? WHERE id=?',
                           ('BATCHED', now, prompt_id, fix_id))
        return {'prompt': text, 'prompt_id': prompt_id, 'path': self.relative(target), 'fix_ids': ids,
                'marked': 'BATCHED'}


def _short(value, limit):
    if value in (None, ''):
        return None
    text = ' '.join(str(value).split())
    return text[:limit] if len(text) > limit else text


def _iso(seconds):
    try:
        return time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime(float(seconds)))
    except (TypeError, ValueError):
        return 'unknown'


def _target_sentence(element):
    if not element:
        return 'not recorded'
    bits = []
    if element.get('tag'):
        bits.append('<%s%s>' % (element['tag'], (' role=' + str(element['role'])) if element.get('role') else ''))
    if element.get('text'):
        bits.append('text "' + _short(element['text'], 90) + '"')
    if element.get('label'):
        bits.append('labelled "' + _short(element['label'], 60) + '"')
    return ' '.join(bits) or 'not recorded'
