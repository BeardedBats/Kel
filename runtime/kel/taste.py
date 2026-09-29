"""D-88: Nick's taste library — motion now, writing voice as a small sibling.

Design: `docs/v2/design/WRITER_ANIMATOR_ROLES.md` §3. Plain files inside D-81's Memory folder, so
every staff member can read them:

    Memory\\Taste\\
      README.md                  how to add things (one screen)
      Motion\\
        inbox\\                   drop anything here (+ an optional same-name .txt note)
        refs\\<date-slug>\\        ref.md (front matter + Nick's note verbatim), media, strip.png
        anti\\                    "not this" references, same shape
        kit\\kel-motion.js        the house spring core pages use (seekable clock for capture)
        rules.md                 the distilled rules, each citing its references
        proposals\\               rule changes waiting for Nick
        index.json               generated: tags, measured numbers, note text
        CHANGELOG.md             what was added or changed, when, and why
      Writing\\                   created empty (D-88.3); Nick's samples and style sheet when he adds them

Principles kept here: Nick's note is kept verbatim and never rewritten; numbers are measured by a
tool or left empty, never guessed; intake is a mechanical pipeline (no curator agent); a rule quoted
straight from Nick's notes is added on its own, a rule that changes or contradicts another waits for
him (D-88.8). Kel's own 15 approved moments are seeded as loved references (D-88.10).
"""
import datetime
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

MOMENTS = ('enter', 'exit', 'morph', 'sheet', 'list-reorder', 'stagger', 'toast', 'loader', 'progress',
           'number-roll', 'text-change', 'hover', 'press', 'drag', 'page-transition', 'scroll-linked',
           'indicator')
MEDIA = ('.mp4', '.webm', '.mov', '.gif', '.mkv', '.m4v')
IMAGES = ('.png', '.jpg', '.jpeg', '.webp')
CODE = ('.html', '.htm', '.css', '.js', '.ts', '.tsx', '.jsx')
TEXT = ('.txt', '.md', '.url')
FRONT = '---'
STRIP_MS = 50  # contact sheets at 50 ms steps, like Tools\motion\keyframes
PROPOSE_EVERY = 5

# The closed-form presets of MOTION.md §1 (duration, settle at 0.2 %, overshoot %).
PRESETS = {'micro': (220, 229, 0.15), 'snappy': (340, 450, 1.1), 'morph': (480, 617, 0.6),
           'gentle': (620, 642, 0.15)}

# D-88.10: Kel's 15 approved moments (MOTION.md §10), seeded as loved references. Numbers come from
# the named preset's closed form (MOTION.md §1-2), which is how the prototype was captured.
KEL_MOMENTS = (
    ('10.1', 'send-thinking-reply', 'Sending a message, Thinking, the reply', ['press', 'morph', 'enter', 'text-change'], 'gentle', '01-send-thinking-reply.png'),
    ('10.2', 'handoff', 'The hand-off: the card lifts out of the line', ['morph', 'list-reorder', 'stagger'], 'gentle', '02-handoff.png'),
    ('10.3', 'card-to-detail', 'Work card grows into the detail panel', ['morph', 'sheet', 'stagger'], 'morph', '03-card-to-detail.png'),
    ('10.4', 'card-states', 'Card state changes: label rolls, check draws on', ['text-change', 'number-roll', 'progress'], 'snappy', '04-card-states.png'),
    ('10.5', 'progress-steps', 'Progress bars stretch; step ticks', ['progress', 'indicator', 'text-change'], 'gentle', '05-progress-steps.png'),
    ('10.6', 'needs-you-answer', 'A Needs-you answer morphs into the answered line', ['press', 'morph', 'list-reorder'], 'morph', '06-needs-you-answer.png'),
    ('10.7', 'scoping-start', 'Scoping card collapses; the top card starts', ['morph', 'stagger', 'progress'], 'morph', '07-scoping-start.png'),
    ('10.8', 'done-card', 'The done card unfolds from its top edge', ['enter', 'stagger', 'list-reorder'], 'morph', '08-result-done-card.png'),
    ('10.9', 'undo', 'Undo: the applied line rolls with the settling fade', ['text-change'], 'snappy', '09-undo.png'),
    ('10.10', 'overflow-menu', 'The "+N more" tile grows into its menu', ['morph', 'sheet', 'stagger'], 'gentle', '10-overflow-menu.png'),
    ('10.11', 'tab-indicators', 'Segmented controls: the indicator stretches edge by edge', ['indicator', 'page-transition'], 'snappy', '11b-model-picker-tabs.png'),
    ('10.12', 'project-switcher', 'Popover grows from its trigger; the check travels', ['sheet', 'enter', 'indicator'], 'snappy', '12-project-switcher.png'),
    ('10.13', 'toasts', 'Toasts rise out of a blur; the others FLIP', ['toast', 'enter', 'exit'], 'snappy', '13-toasts.png'),
    ('10.14', 'new-chat-sidebar', 'A new chat enters the sidebar; the selection travels', ['list-reorder', 'enter', 'indicator'], 'gentle', '14-new-chat-sidebar.png'),
    ('10.15', 'staff-fallback-note', 'The fallback note enters; rows below FLIP down', ['enter', 'list-reorder'], 'snappy', '15-staff-fallback-note.png'),
)

RULES_SEED = """# Nick's motion rules

Short and cited. Kel adds a rule quoted straight from your notes on its own and lists it in CHANGELOG.md;
a rule that changes or contradicts another waits in proposals\\ for you. Delete any line you disagree with.

## From Kel's approved motion language (MOTION.md, D-78)
- Springs, not tweens, for movement; overshoot never more than about 1%. (refs: kel-ui-*)
- Opacity and blur are timed fades: exit 110-130 ms ease-in, enter 180-220 ms ease-out. (refs: kel-ui-toasts, kel-ui-done-card)
- A final state that stays on screen settles with a soft fade: about 520 ms, 3 px blur to sharp. (refs: kel-ui-undo, kel-ui-card-states)
- Stagger siblings 25-40 ms, never more than 200 ms in total. (refs: kel-ui-done-card, kel-ui-card-to-detail)
- Nothing moves or re-words after the motion settles. (refs: kel-ui-card-to-detail, kel-ui-progress-steps)
- Shared elements morph from where they were; nothing just appears. (refs: kel-ui-card-to-detail, kel-ui-handoff)
- No decorative loops; only the Thinking indicator may loop. (refs: kel-ui-send-thinking-reply)
- Keyboard and 100+/day actions don't animate. (refs: MOTION.md §9)
- Reduced motion: cross-fades only (100 ms out, 140-150 ms in). (refs: kel-ui-*)

## From your notes
"""

README = """# Your taste library

Kel's Animator (and later the Writer) learns what you like from this folder.

## Add a motion you like
- Tell Kel in any chat: "Save to motion taste: <link or attached file>. I like how the panel lands with no bounce."
- Or drop a clip, GIF, link (.url), code or page into Motion\\inbox\\. Add a .txt with the same name saying why you
  like it (optional).
- Say "not this" or "save as a motion I don't like" for a reference the Animator should avoid.
- Say "keep this one private" to keep its media on this PC (only your note and the numbers are ever sent).

Kel files it, cuts a frame strip, measures its timing where it can, and keeps Motion\\rules.md short and cited.
Your own words are kept exactly as you wrote them.

## Writing
Writing\\ is empty for now. When you want, say "Save to my writing voice: <text or file>".
"""


# ---- where -------------------------------------------------------------------------------------

def memory_root(engine_root=None):
    """D-81's Memory folder (its own helper when present; the same rules otherwise)."""
    try:
        from .memory_folder import memory_root as helper
        return Path(helper(engine_root))
    except ImportError:
        pass
    override = (os.environ.get('KEL_MEMORY_ROOT') or '').strip()
    if override:
        return Path(os.path.abspath(os.path.expandvars(os.path.expanduser(override))))
    from .containment import app_roots
    for app in app_roots():
        return Path(app).parent / 'Memory'
    if engine_root:
        engine = Path(os.path.abspath(engine_root))
        data = engine.parent if engine.name.lower() == 'engine' else engine
        return data.parent / 'Memory'
    return Path(os.environ.get('USERPROFILE') or Path.home()) / 'Kel' / 'Memory'


def taste_root(engine_root=None):
    return memory_root(engine_root) / 'Taste'


def motion_dir(engine_root=None):
    return taste_root(engine_root) / 'Motion'


def writing_dir(engine_root=None):
    return taste_root(engine_root) / 'Writing'


def _kit_source():
    return Path(__file__).resolve().parent / 'motion_kit' / 'kel-motion.js'


def _keyframes_dir(engine_root=None):
    """Tools\\motion\\keyframes beside Memory (Kel's prototype sheets), when it exists."""
    override = os.environ.get('KEL_MOTION_KEYFRAMES')
    if override:
        return Path(override)
    return memory_root(engine_root).parent / 'Tools' / 'motion' / 'keyframes'


def _today():
    return datetime.date.today().isoformat()


def _slug(text, limit=40):
    words = re.sub(r'[^a-z0-9]+', '-', str(text or '').lower()).strip('-')
    return (words[:limit].rstrip('-') or 'reference')


def _log(motion, line):
    path = motion / 'CHANGELOG.md'
    if not path.exists():
        path.write_text('# Motion taste changes\n\n', encoding='utf-8')
    with path.open('a', encoding='utf-8') as handle:
        handle.write('- %s: %s\n' % (_today(), line))


# ---- the scaffold and the seed ------------------------------------------------------------------

def ensure(engine_root=None):
    """Create the library (idempotent) and seed Kel's 15 moments; returns the Taste folder."""
    taste = taste_root(engine_root)
    motion = taste / 'Motion'
    for folder in (taste, motion, motion / 'inbox', motion / 'refs', motion / 'anti', motion / 'proposals',
                   motion / 'kit', taste / 'Writing'):
        folder.mkdir(parents=True, exist_ok=True)
    if not (taste / 'README.md').exists():
        (taste / 'README.md').write_text(README, encoding='utf-8')
    if not (motion / 'rules.md').exists():
        (motion / 'rules.md').write_text(RULES_SEED, encoding='utf-8')
    kit = motion / 'kit' / 'kel-motion.js'
    source = _kit_source()
    if source.exists() and (not kit.exists() or kit.read_bytes() != source.read_bytes()):
        shutil.copyfile(source, kit)
    if seed_kel_moments(engine_root):
        build_index(engine_root)
    elif not (motion / 'index.json').exists():
        build_index(engine_root)
    return taste


def seed_kel_moments(engine_root=None):
    """D-88.10: the 15 MOTION.md moments as loved references (skips any already there)."""
    motion = motion_dir(engine_root)
    sheets = _keyframes_dir(engine_root)
    added = 0
    for section, slug, title, moments, preset, sheet in KEL_MOMENTS:
        ref_id = 'kel-ui-' + slug
        folder = motion / 'refs' / ref_id
        if (folder / 'ref.md').exists():
            continue
        folder.mkdir(parents=True, exist_ok=True)
        duration, settle, overshoot = PRESETS[preset]
        meta = {'id': ref_id, 'title': 'Kel - ' + title, 'source': 'Kel UI: MOTION.md §%s' % section,
                'captured': _today(), 'kind': 'kel-ui', 'moments': moments, 'feel': ['calm', 'crisp'],
                'loved': True,
                'measured': {'duration_ms': duration, 'settle_ms': settle, 'overshoot_pct': overshoot,
                             'stagger_ms': None, 'properties': ['transform', 'opacity', 'filter'],
                             'basis': 'the %s preset, closed form (MOTION.md §1)' % preset},
                'local_only': False, 'status': 'active'}
        note = ('Approved by Nick as part of Kel\'s motion language (D-78). See MOTION.md §%s for the full '
                'choreography.' % section)
        if (sheets / sheet).exists():
            shutil.copyfile(sheets / sheet, folder / 'strip.png')
        write_ref(folder / 'ref.md', meta, note, 'Kel\'s own moment, built with the `%s` spring.' % preset)
        added += 1
    if added:
        _log(motion, 'seeded %d of Kel\'s approved moments as loved references (D-88.10)' % added)
    return added


# ---- ref.md --------------------------------------------------------------------------------------

def write_ref(path, meta, note, description=''):
    """Front matter (one JSON value per key, valid YAML) + Nick's note verbatim + Kel's description."""
    lines = [FRONT] + ['%s: %s' % (key, json.dumps(value, ensure_ascii=False)) for key, value in meta.items()]
    lines += [FRONT, '', "## Nick's note", '', note or '(no note yet)', '']
    if description:
        lines += ["## Kel's description", '', description, '']
    Path(path).write_text('\n'.join(lines), encoding='utf-8')


def read_ref(path):
    """(meta, note) of one ref.md; ({}, '') when unreadable."""
    try:
        text = Path(path).read_text(encoding='utf-8')
    except OSError:
        return {}, ''
    meta = {}
    parts = text.split(FRONT + '\n', 2)
    if len(parts) == 3 and parts[0] == '':
        for line in parts[1].splitlines():
            key, sep, value = line.partition(':')
            if not sep:
                continue
            try:
                meta[key.strip()] = json.loads(value.strip())
            except ValueError:
                meta[key.strip()] = value.strip()
        body = parts[2]
    else:
        body = text
    match = re.search(r"## Nick's note\s*\n(.*?)(?:\n## |\Z)", body, re.DOTALL)
    return meta, (match.group(1).strip() if match else '')


def _entries(engine_root=None):
    motion = motion_dir(engine_root)
    out = []
    for group in ('refs', 'anti'):
        base = motion / group
        if not base.is_dir():
            continue
        for folder in sorted(base.iterdir()):
            if not (folder / 'ref.md').exists():
                continue
            meta, note = read_ref(folder / 'ref.md')
            if meta.get('status', 'active') != 'active':
                continue
            out.append({'id': meta.get('id') or folder.name, 'anti': group == 'anti',
                        'folder': str(folder), 'title': meta.get('title') or folder.name,
                        'moments': list(meta.get('moments') or []), 'feel': list(meta.get('feel') or []),
                        'loved': bool(meta.get('loved')), 'measured': meta.get('measured') or {},
                        'local_only': bool(meta.get('local_only')), 'kind': meta.get('kind'),
                        'source': meta.get('source'), 'note': note,
                        'strip': str(folder / 'strip.png') if (folder / 'strip.png').exists() else None})
    return out


def build_index(engine_root=None):
    """Regenerate index.json (tags, numbers, note text) from the reference folders."""
    motion = motion_dir(engine_root)
    motion.mkdir(parents=True, exist_ok=True)
    entries = _entries(engine_root)
    (motion / 'index.json').write_text(json.dumps({'generated': _today(), 'refs': entries}, indent=1,
                                                  ensure_ascii=False), encoding='utf-8')
    return entries


# ---- retrieval: tag filter + BM25 over the notes (§3.4 step 5, §3.5) -------------------------------

TOKEN = re.compile(r'[a-z0-9]+')
STOP = {'the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'on', 'it', 'is', 'this', 'that', 'with', 'for',
        'i', 'my', 'me', 'how', 'like', 'make', 'please', 'nice', 'nicely', 'page', 'kel'}


def _tokens(text):
    return [t for t in TOKEN.findall(str(text or '').lower()) if t not in STOP]


def moments_in(text):
    """The fixed moment types a brief mentions (plus a few everyday words for them)."""
    lower = str(text or '').lower()
    aliases = {'enter': ('enter', 'arrive', 'appear', 'fade in', 'slide in', 'reveal'),
               'exit': ('exit', 'leave', 'disappear', 'dismiss'), 'sheet': ('sheet', 'panel', 'drawer', 'modal', 'popover', 'dropdown', 'menu'),
               'stagger': ('stagger', 'one after', 'cascade', 'cards'), 'list-reorder': ('reorder', 'list', 'sort'),
               'toast': ('toast', 'notification'), 'loader': ('loader', 'loading', 'spinner'),
               'progress': ('progress',), 'number-roll': ('counter', 'number', 'count up'),
               'text-change': ('label', 'text change', 'headline'), 'hover': ('hover',), 'press': ('press', 'click', 'tap', 'button'),
               'drag': ('drag', 'swipe'), 'page-transition': ('page transition', 'route', 'navigation'),
               'scroll-linked': ('scroll', 'parallax'), 'indicator': ('tab', 'indicator', 'segmented'),
               'morph': ('morph', 'expand', 'grow into', 'shared element')}
    return [moment for moment in MOMENTS if any(word in lower for word in aliases.get(moment, (moment,)))]


def retrieve(engine_root, brief, *, k=5, anti_k=2, moments=None):
    """(refs, anti): the closest references for a brief — moment type, then feel words, then loved,
    then note similarity (BM25) — and 1-2 anti-references for the same moment types."""
    entries = _entries(engine_root)
    wanted = list(moments) if moments is not None else moments_in(brief)
    query = _tokens(brief)
    docs = [_tokens(' '.join([e['title'], e['note'], ' '.join(e['moments']), ' '.join(e['feel'])])) for e in entries]
    n = len(docs) or 1
    avg = sum(len(d) for d in docs) / n if docs else 1
    df = {}
    for doc in docs:
        for term in set(doc):
            df[term] = df.get(term, 0) + 1

    def bm25(doc):
        score = 0.0
        for term in query:
            tf = doc.count(term)
            if not tf:
                continue
            idf = math.log(1 + (n - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5))
            score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * len(doc) / (avg or 1)))
        return score

    scored = []
    for entry, doc in zip(entries, docs):
        overlap = len(set(wanted) & set(entry['moments']))
        feel = len(set(query) & {f.lower() for f in entry['feel']})
        scored.append(((overlap, feel, entry['loved'], round(bm25(doc), 4)), entry))
    scored.sort(key=lambda item: item[0], reverse=True)
    refs = [e for key, e in scored if not e['anti'] and (key[0] or key[3] or not wanted)][:k]
    if len(refs) < min(k, 3):
        refs += [e for _key, e in scored if not e['anti'] and e not in refs][:min(k, 3) - len(refs)]
    anti = [e for key, e in scored if e['anti']][:anti_k]
    return refs, anti


def _numbers(measured):
    parts = []
    for key, label in (('duration_ms', 'duration %s ms'), ('settle_ms', 'settles %s ms'),
                       ('overshoot_pct', 'overshoot %s%%'), ('stagger_ms', 'stagger %s ms')):
        if measured.get(key) is not None:
            parts.append(label % measured[key])
    return ', '.join(parts) if parts else 'not measured (use for look only)'


def motion_context(engine_root, brief):
    """The `taste-motion` pack for one Animator step: rules.md, the closest references and the
    anti-references, each as Nick's note + measured numbers + strip path."""
    try:
        ensure(engine_root)
        scan_inbox(engine_root)
    except OSError:
        pass
    motion = motion_dir(engine_root)
    try:
        rules = (motion / 'rules.md').read_text(encoding='utf-8')
    except OSError:
        rules = ''
    refs, anti = retrieve(engine_root, brief)
    out = ["\nNick's motion taste (Memory\\Taste\\Motion). His rules:\n" + rules.strip()]

    def block(entry, label):
        lines = ['- %s "%s" (%s; moments: %s)' % (label, entry['title'], entry['id'], ', '.join(entry['moments']) or 'none'),
                 '  Nick\'s note: ' + (entry['note'] or '(none)'),
                 '  Measured: ' + _numbers(entry['measured'])]
        if entry['strip'] and not entry['local_only']:
            lines.append('  Frame strip (50 ms steps): ' + entry['strip'])
        return '\n'.join(lines)

    if refs:
        out.append('References to follow (by their numbers, not their look):\n' +
                   '\n'.join(block(e, 'Loved' if e['loved'] else 'Reference') for e in refs))
    if anti:
        out.append('Not this:\n' + '\n'.join(block(e, 'Anti-reference') for e in anti))
    out.append('Kit: a seekable spring core for standalone pages is at %s (copy it into the page; it exposes '
               'window.__motion). Propose rule changes as a file in %s; never edit rules.md or the references.'
               % (motion / 'kit' / 'kel-motion.js', motion / 'proposals'))
    return '\n'.join(out) + '\n'


# ---- intake (§3.4) -------------------------------------------------------------------------------

def _ffmpeg():
    return shutil.which('ffmpeg')


def cut_strip(media, target, *, max_frames=32, width=240):
    """A contact sheet of the clip at 50 ms steps (ffmpeg); False when ffmpeg can't run here."""
    ffmpeg = _ffmpeg()
    if not ffmpeg:
        return False
    rows = max(1, math.ceil(max_frames / 8))
    command = [ffmpeg, '-y', '-loglevel', 'error', '-i', str(media), '-frames:v', '1', '-vf',
               'fps=%d,scale=%d:-1,tile=8x%d:padding=4:color=0x0b1a3d' % (1000 // STRIP_MS, width, rows),
               str(target)]
    try:
        return subprocess.run(command, capture_output=True, timeout=120).returncode == 0 and Path(target).exists()
    except (OSError, subprocess.SubprocessError):
        return False


def measure_clip(media, *, fps=60):
    """Measured timing of a clip by frame differences: {duration_ms, settle_ms, basis} or {} when it
    can't be measured here (no ffmpeg or no image library). Overshoot and stagger need an element to
    track, so they stay empty (never guessed)."""
    ffmpeg = _ffmpeg()
    try:
        from PIL import Image, ImageChops, ImageStat
    except ImportError:
        return {}
    if not ffmpeg:
        return {}
    with tempfile.TemporaryDirectory() as scratch:
        pattern = os.path.join(scratch, 'f%05d.png')
        try:
            done = subprocess.run([ffmpeg, '-loglevel', 'error', '-i', str(media), '-t', '10', '-vf',
                                   'fps=%d,scale=160:-1,format=gray' % fps, pattern],
                                  capture_output=True, timeout=180)
        except (OSError, subprocess.SubprocessError):
            return {}
        frames = sorted(Path(scratch).glob('f*.png'))
        if done.returncode != 0 or len(frames) < 3:
            return {}
        diffs, previous = [], None
        for frame in frames:
            with Image.open(frame) as image:
                current = image.convert('L').copy()
            if previous is not None:
                diffs.append(ImageStat.Stat(ImageChops.difference(current, previous)).mean[0] / 255.0)
            previous = current
    peak = max(diffs) if diffs else 0
    if peak <= 0.002:
        return {}
    moving = [i for i, value in enumerate(diffs) if value > max(0.002, peak * 0.02)]
    start, end = moving[0], moving[-1]
    step = 1000.0 / fps
    settle_band = [i for i, value in enumerate(diffs) if value > max(0.002, peak * 0.002)]
    return {'duration_ms': int(round((end - start + 1) * step)),
            'settle_ms': int(round((settle_band[-1] - start + 1) * step)),
            'overshoot_pct': None, 'stagger_ms': None,
            'basis': 'frame differences at %d fps (whole-frame, no element tracked)' % fps}


def _unique(folder):
    candidate, n = folder, 2
    while candidate.exists():
        candidate = folder.with_name('%s-%d' % (folder.name, n))
        n += 1
    return candidate


def add_reference(engine_root, *, source=None, note='', title=None, anti=False, private=False,
                  feel=None, moments=None, file_path=None, loved=False):
    """File one reference (§3.4 steps 1-5): folder, media, strip, measurement, tags, index, CHANGELOG.

    `note` is Nick's words, kept verbatim. Returns the entry as indexed."""
    ensure(engine_root)
    motion = motion_dir(engine_root)
    title = title or (Path(file_path).stem.replace('-', ' ').replace('_', ' ') if file_path else None) or \
        _title_from(source) or 'Motion reference'
    folder = _unique(motion / ('anti' if anti else 'refs') / ('%s-%s' % (_today(), _slug(title))))
    folder.mkdir(parents=True)
    kind, measured, media = 'link' if source else 'note', {}, None
    if file_path:
        path = Path(file_path)
        suffix = path.suffix.lower()
        kind = ('gif' if suffix == '.gif' else 'clip') if suffix in MEDIA else \
            ('code' if suffix in CODE else ('image' if suffix in IMAGES else 'file'))
        media = folder / (('clip' if suffix in MEDIA else 'source') + suffix)
        shutil.copyfile(path, media)
        if suffix in MEDIA:
            cut_strip(media, folder / 'strip.png')
            measured = measure_clip(media)
        elif suffix in IMAGES:
            shutil.copyfile(media, folder / 'strip.png')
    found = list(moments) if moments else moments_in(' '.join([note or '', title]))
    meta = {'id': folder.name, 'title': title,
            'source': source or ('file: %s' % Path(file_path).name if file_path else 'told to Kel'),
            'captured': _today(), 'kind': kind, 'moments': found,
            'feel': list(feel or []) or _feel_words(note), 'loved': bool(loved or re.search(r'\blove', note or '', re.I)),
            'measured': measured or None, 'local_only': bool(private), 'status': 'active'}
    write_ref(folder / 'ref.md', meta, note)
    _log(motion, 'added %s "%s"%s' % ('anti-reference' if anti else 'reference', title,
                                     ' (kept on this PC)' if private else ''))
    build_index(engine_root)
    if not anti:
        rules_from_notes(engine_root)
    return next((e for e in _entries(engine_root) if e['id'] == folder.name), meta)


FEEL = ('crisp', 'calm', 'snappy', 'soft', 'weighty', 'light', 'smooth', 'bouncy', 'springy', 'subtle',
        'playful', 'quick', 'slow', 'gentle', 'physical', 'fluid', 'tight', 'elastic', 'restrained')


def _feel_words(note):
    lower = str(note or '').lower()
    return [word for word in FEEL if re.search(r'\b%s\b' % word, lower)]


def _title_from(source):
    if not source:
        return None
    match = re.match(r'https?://(?:www\.)?([^/]+)(/[^?#]*)?', source)
    if not match:
        return None
    path = [p for p in (match.group(2) or '').split('/') if p][-1:] or []
    return ('%s %s' % (match.group(1), path[0] if path else '')).strip()


def scan_inbox(engine_root=None):
    """File everything dropped into Motion\\inbox\\ (an optional same-name .txt is Nick's note)."""
    motion = motion_dir(engine_root)
    inbox = motion / 'inbox'
    if not inbox.is_dir():
        return []
    done = []
    items = sorted(p for p in inbox.iterdir() if not p.name.startswith('.'))
    notes = {p.stem.lower(): p for p in items if p.is_file() and p.suffix.lower() == '.txt'}
    for item in items:
        if not item.exists() or (item.suffix.lower() == '.txt' and any(
                other.stem.lower() == item.stem.lower() and other != item for other in items)):
            continue
        note_file = notes.get(item.stem.lower()) if item.suffix.lower() != '.txt' else None
        note = note_file.read_text(encoding='utf-8', errors='replace').strip() if note_file else ''
        try:
            if item.is_dir():
                entry = add_reference(engine_root, note=note, title=item.name, source='folder: ' + item.name)
                shutil.copytree(item, Path(entry['folder']) / 'files', dirs_exist_ok=True)
                shutil.rmtree(item)
            elif item.suffix.lower() == '.url':
                url = re.search(r'URL=(\S+)', item.read_text(encoding='utf-8', errors='replace'))
                entry = add_reference(engine_root, note=note, title=item.stem,
                                      source=url.group(1) if url else item.name)
                item.unlink()
            elif item.suffix.lower() in ('.txt', '.md') and not note_file:
                text = item.read_text(encoding='utf-8', errors='replace').strip()
                link = re.search(r'https?://\S+', text)
                entry = add_reference(engine_root, note=text, title=item.stem,
                                      source=link.group(0) if link else None)
                item.unlink()
            else:
                entry = add_reference(engine_root, note=note, file_path=item)
                item.unlink()
            if note_file and note_file.exists():
                note_file.unlink()
            done.append(entry)
        except OSError:
            continue
    return done


def retire(engine_root, words):
    """"Forget the Linear one": retire the best-matching reference (its folder stays; Nick may delete it)."""
    wanted = set(_tokens(words))
    best, score = None, 0
    for entry in _entries(engine_root):
        if entry['kind'] == 'kel-ui':
            continue
        overlap = len(wanted & set(_tokens(entry['title'] + ' ' + (entry['source'] or ''))))
        if overlap > score:
            best, score = entry, overlap
    if not best:
        return None
    path = Path(best['folder']) / 'ref.md'
    meta, note = read_ref(path)
    text = path.read_text(encoding='utf-8')
    meta['status'] = 'retired'
    description = text.split("## Kel's description", 1)[1].strip() if "## Kel's description" in text else ''
    write_ref(path, meta, note, description)
    _log(motion_dir(engine_root), 'retired "%s" at Nick\'s request' % best['title'])
    build_index(engine_root)
    return best


# ---- rules (§3.4 step 6, D-88.8) -----------------------------------------------------------------

RULE_SENTENCE = re.compile(r"(?:^|(?<=[.!?]\s))((?:never|always|no|don't|do not|keep|avoid|prefer|only|nothing)\b[^.!?]{3,140}[.!?]?)",
                           re.IGNORECASE)
TOPICS = ('bounce', 'overshoot', 'blur', 'stagger', 'fade', 'loop', 'spring', 'delay', 'slide', 'scale',
          'duration', 'fast', 'slow', 'easing', 'shadow', 'parallax')
NEGATIVE = re.compile(r"\b(?:never|no|don't|do not|avoid|nothing|less|without)\b", re.IGNORECASE)


def _topics(text):
    lower = text.lower()
    return {topic for topic in TOPICS if topic in lower}


def rules_from_notes(engine_root=None, *, every=PROPOSE_EVERY, force=False):
    """After every `every` new references: add each rule sentence quoted from Nick's notes on its own
    (listed in CHANGELOG.md); one that contradicts an existing rule becomes a proposal for Nick."""
    motion = motion_dir(engine_root)
    state_file = motion / '.rules-state.json'
    try:
        state = json.loads(state_file.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        state = {'seen': []}
    fresh = [e for e in _entries(engine_root) if not e['anti'] and e['kind'] != 'kel-ui' and e['id'] not in state['seen']]
    if not fresh or (len(fresh) < every and not force):
        return {'added': [], 'proposed': []}
    rules_path = motion / 'rules.md'
    rules = rules_path.read_text(encoding='utf-8') if rules_path.exists() else RULES_SEED
    existing = [line[2:] for line in rules.splitlines() if line.startswith('- ')]
    added, proposed = [], []
    for entry in fresh:
        for match in RULE_SENTENCE.finditer(entry['note'] or ''):
            quote = match.group(1).strip()
            if any(quote.lower() in line.lower() for line in existing):
                continue
            clash = next((line for line in existing if _topics(line) & _topics(quote)
                          and bool(NEGATIVE.search(line)) != bool(NEGATIVE.search(quote))), None)
            if clash:
                path = motion / 'proposals' / ('%s-%s.md' % (_today(), _slug(quote, 30)))
                path.write_text('# A rule change waiting for Nick\n\nYour note on "%s" says:\n\n> %s\n\nIt '
                                'conflicts with this rule:\n\n> %s\n\nSay "use the new motion rule" or "keep '
                                'the old one" to Kel, or edit rules.md yourself.\n'
                                % (entry['title'], quote, clash), encoding='utf-8')
                proposed.append(quote)
            else:
                line = '"%s" (ref: %s)' % (quote, entry['id'])
                rules = rules.rstrip('\n') + '\n- ' + line + '\n'
                existing.append(line)
                added.append(quote)
                _log(motion, 'added to your motion rules: "%s" (from %s)' % (quote, entry['title']))
    rules_path.write_text(rules, encoding='utf-8')
    state['seen'] = sorted(set(state['seen']) | {e['id'] for e in fresh})
    state_file.write_text(json.dumps(state), encoding='utf-8')
    return {'added': added, 'proposed': proposed}


def pending_proposals(engine_root=None):
    folder = motion_dir(engine_root) / 'proposals'
    return sorted(p.name for p in folder.glob('*.md')) if folder.is_dir() else []


# ---- writing voice (§3.6; D-88.3) ----------------------------------------------------------------

REGISTERS = ('post', 'doc', 'note')
SAMPLES_PER_REGISTER = 5


def writing_style(engine_root=None):
    try:
        return (writing_dir(engine_root) / 'style.md').read_text(encoding='utf-8')
    except OSError:
        return ''


def writing_voice(engine_root=None):
    """{'style', 'samples': [{register, text}]} from Writing\\, or None while it is empty (D-88.3)."""
    base = writing_dir(engine_root)
    samples = []
    for register in REGISTERS:
        folder = base / 'samples' / register
        if not folder.is_dir():
            continue
        files = sorted(folder.glob('*.md'), key=lambda p: p.stat().st_mtime, reverse=True)[:SAMPLES_PER_REGISTER]
        for path in files:
            try:
                samples.append({'register': register, 'text': path.read_text(encoding='utf-8')})
            except OSError:
                continue
    style = writing_style(engine_root)
    if not samples and not style.strip():
        return None
    return {'style': style, 'samples': samples}


def save_writing_sample(engine_root, text, register=None):
    """"Save to my writing voice": one sample, newest kept, at most 5 per register."""
    register = register if register in REGISTERS else ('post' if len(text.split()) > 250 else 'note')
    folder = writing_dir(engine_root) / 'samples' / register
    folder.mkdir(parents=True, exist_ok=True)
    words = ' '.join(text.split()[:6])
    path = _unique(folder / ('%s-%s.md' % (_today(), _slug(words, 30))))
    path.write_text(text.strip() + '\n', encoding='utf-8')
    for old in sorted(folder.glob('*.md'), key=lambda p: p.stat().st_mtime, reverse=True)[SAMPLES_PER_REGISTER:]:
        old.unlink()
    return path


# ---- "tell Kel" (§3.3 route 1) -------------------------------------------------------------------

# "Save to motion taste: …", "Add this to my motion library — …", "Save this motion: …", "Motion taste: …".
# The prefix must name the taste library (or "save this motion") and end in a colon or dash, so a
# request like "add motion to the sidebar" is never taken for it.
MOTION_INTENT = re.compile(r"^\s*(?:please\s+)?(?:(?:save|add|file)\b[^:\n]{0,40}?\bmotion (?:taste|library|references?)\b"
                           r"|save (?:this|that) (?:as )?(?:good )?motion\b|motion taste|good motion)"
                           r"[^:\n]{0,40}?(?:[:—]|\s-\s)", re.IGNORECASE)
ANTI_INTENT = re.compile(r"\b(?:not this|don't like|do not like|hate|avoid)\b", re.IGNORECASE)
PRIVATE_INTENT = re.compile(r"\b(?:keep (?:this|it)(?: one)? private|private)\b", re.IGNORECASE)
RETIRE_INTENT = re.compile(r"^\s*(?:forget|remove|drop)\s+(?:the\s+)?(.+?)\s+(?:one\s+)?from (?:my )?motion taste\s*\.?$", re.IGNORECASE)
VOICE_INTENT = re.compile(r"^\s*(?:please\s+)?(?:save|add)\b[^:\n]{0,30}?\bwriting voice\b\s*[:\-—]?\s*", re.IGNORECASE)
URL = re.compile(r'https?://[^\s)>\]]+')


def chat_intent(engine_root, text, packet=None):
    """One plain reply line when the message is a taste intent (files the reference), else None."""
    text = str(text or '').strip()
    files = [f for f in (packet or {}).get('files') or [] if isinstance(f, dict)]
    retire_match = RETIRE_INTENT.match(text)
    if retire_match:
        gone = retire(engine_root, retire_match.group(1))
        return ('Removed "%s" from your motion taste.' % gone['title']) if gone else \
            "I couldn't find that one in your motion taste."
    voice = VOICE_INTENT.match(text)
    if voice:
        body = text[voice.end():].strip()
        attached = _attached_text(engine_root, files)
        body = '\n\n'.join(part for part in (body, attached) if part)
        if not body:
            return 'Paste the text (or attach the file) after "Save to my writing voice:" and I\'ll keep it.'
        save_writing_sample(engine_root, body)
        return 'Saved to your writing voice.'
    match = MOTION_INTENT.match(text)
    if not match:
        return None
    rest = text[match.end():].strip()
    links = URL.findall(rest)
    note = URL.sub('', rest).strip().lstrip('.,-—: ').strip()  # Nick's words, otherwise as written
    anti = bool(ANTI_INTENT.search(text))
    private = bool(PRIVATE_INTENT.search(text))
    saved = []
    for item in files:
        path = _attachment_path(engine_root, item)
        if path:
            saved.append(add_reference(engine_root, note=note, file_path=path, anti=anti,
                                       private=private or bool(item.get('screen_capture'))))
    for link in links:
        saved.append(add_reference(engine_root, note=note, source=link, anti=anti, private=private))
    if not saved:
        if not note:
            return 'Add a link, a file or a sentence after "Save to motion taste:" and I\'ll file it.'
        saved.append(add_reference(engine_root, note=note, anti=anti, private=private))
    where = 'as a motion you don\'t like' if anti else 'to your motion taste'
    names = ', '.join('"%s"' % e['title'] for e in saved)
    line = 'Saved %s %s.' % (names, where)
    waiting = pending_proposals(engine_root)
    if waiting:
        line += ' One motion rule change is waiting for you in Memory\\Taste\\Motion\\proposals.' if len(waiting) == 1 else \
            ' %d motion rule changes are waiting for you in Memory\\Taste\\Motion\\proposals.' % len(waiting)
    return line


def _attachment_path(engine_root, item):
    for key in ('path', 'image_path', 'file_path'):
        value = item.get(key)
        if not value:
            continue
        path = Path(value)
        if not path.is_absolute() and engine_root:
            path = Path(engine_root) / value
        if path.is_file():
            return path
    return None


def _attached_text(engine_root, files):
    out = []
    for item in files:
        if item.get('text'):
            out.append(str(item['text']))
            continue
        path = _attachment_path(engine_root, item)
        if path and path.suffix.lower() in ('.md', '.txt'):
            out.append(path.read_text(encoding='utf-8', errors='replace'))
    return '\n\n'.join(out).strip()
