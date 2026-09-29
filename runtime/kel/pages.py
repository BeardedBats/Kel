"""D-88: HTML pages and other mixed deliverables — the Writer writes the words, the Builder the code.

Design: `docs/v2/design/WRITER_ANIMATOR_ROLES.md` §2. A `page` is a web page or HTML file whose words
matter. Kel recognises one from the turn model's class or a floor regex (which can only add `page`,
never take work away), and compiles it into a fixed hand-off frozen in the contract:

    copy (Writer)  ||  design (Designer, only when needed)
            -> build (Builder, the copy locked)
            -> motion (Animator, only when motion is asked for)
            -> the review team (the engine's per-step review; the Editor reads the copy)

The step that finally changes the project is always named `code` (applying, the Oracle and the
result card read that step), so with no Animator the Builder's step is `code`, and with one the
Builder's step is `build` and the Animator's is `code` in the same project copy.

Copy lock: the Builder places the Writer's words and never retypes or edits them. A deterministic
check compares every string in `copy.md` with the built page's visible text; a string that is
missing or changed fails the Builder's step, with the strings named. A string that does not fit the
layout goes to `copy_requests.md` for the Writer, and the page keeps the Writer's words meanwhile.
"""
import html
import re
from html.parser import HTMLParser
from pathlib import Path

PAGE_FLOOR = re.compile(
    r"\.html?\b|\bhtml (?:page|file|document|email)\b|\bweb ?page\b|\blanding page\b|\bone[- ]pager\b"
    r"|\bmicrosite\b|\bnewsletter (?:page|site|template)\b|\bsplash page\b|\bproduct page\b|\babout page\b"
    r"|\b(?:a|an|the) page (?:for|about|that|to)\b",
    re.IGNORECASE)
# Not a page: an HTML file that is only a data dump or a tool's output (Utility or Builder work).
NOT_PAGE = re.compile(r"\b(?:export|convert|dump|save)\b[^.]{0,40}\b(?:as|to|into) html\b"
                      r"|\bhtml (?:table|report) of\b", re.IGNORECASE)
MOTION_WORDS = re.compile(
    r"\banimat\w*|\bmotion\b|\btransitions?\b|\bmicro-?interactions?\b|\bfeel alive\b|\bspring(?:y|s)?\b"
    r"|\bstagger\w*|\bfade[sd]? in\b|\bslides? in\b|\bparallax\b|\bhover effects?\b|\bscroll(?:-linked)? effects?\b",
    re.IGNORECASE)
DESIGN_WORDS = re.compile(r"\bdesign\w*|\blook(?: and feel)?\b|\bbrand\w*|\bstyle guide\b|\bvisual\w*|\baesthetic\b"
                          r"|\bpretty\b|\bbeautiful\b|\bpolished\b", re.IGNORECASE)
LOOK_FILES = ('*.css', '*.scss', 'tailwind.config.*', 'tokens.json', 'theme.*', 'DESIGN.md', 'design-system*')

COPY_FILE, BRIEF_FILE, COPY_REQUESTS = 'copy.md', 'brief.md', 'copy_requests.md'
# `key: text` lines of copy.md (the keys name where each string goes: hero.title, meta.description …).
COPY_LINE = re.compile(r'^\s*[-*]?\s*`?([A-Za-z][\w.\-\[\]]*)`?\s*:\s+(.+?)\s*$')
SKIP_TEXT_TAGS = ('script', 'style', 'noscript', 'template', 'svg')
TEXT_ATTRS = ('alt', 'title', 'aria-label', 'placeholder', 'value', 'content')


def is_page(text, task_class=None):
    """True for a page request: the turn model said `page`, or the floor matched (and it is not a
    plain HTML export)."""
    if task_class == 'page':
        return True
    value = str(text or '')
    return bool(PAGE_FLOOR.search(value)) and not NOT_PAGE.search(value)


# Strong motion words only (a code request about "state transitions" is not motion work).
MOTION_FLOOR = re.compile(r"\banimat\w*|\bmicro-?interactions?\b|\bfeel alive\b|\bmotion design\b", re.IGNORECASE)


def floor_class(text, task_class):
    """The class after the D-88 floors: `page` for a page request read as coding, design or writing;
    `motion` for animation work read as coding or design. Never changes research or utility."""
    if task_class in ('research', 'utility', 'page'):
        return task_class
    if task_class in ('coding', 'design', 'writing', None) and is_page(text):
        return 'page'
    if task_class in ('coding', 'design') and MOTION_FLOOR.search(str(text or '')):
        return 'motion'
    return task_class


def wants_motion(text, task_class=None):
    return task_class == 'motion' or bool(MOTION_WORDS.search(str(text or '')))


def has_look(root):
    """True when the project already has a look to follow (stylesheets, tokens or a design note)."""
    if not root:
        return False
    base = Path(root)
    if not base.is_dir():
        return False
    skip = {'node_modules', '.git', 'dist', 'build', '.venv'}
    for pattern in LOOK_FILES:
        for found in base.rglob(pattern):
            if not (skip & set(found.relative_to(base).parts)):
                return True
    return False


def wants_designer(text, root):
    """D-88.11: the Designer joins a page only when there's no existing look or Nick asks for design."""
    if DESIGN_WORDS.search(str(text or '')):
        return True, 'the request asks for design'
    if not has_look(root):
        return True, 'the project has no existing look to follow'
    return False, 'the project already has a look, and the request does not ask for design'


def page_contract(contract, text, *, task_class=None):
    """Expand a compiled one-step coding contract into the page hand-off (same request, root, tests)."""
    from .core import validate_contract
    root = contract.get('root')
    designer, designer_why = wants_designer(text, root)
    animator = wants_motion(text, task_class)
    build_id = 'build' if animator else 'code'
    code = next(m for m in contract['milestones'] if m['id'] == 'code')
    copy_step = {
        'id': 'copy', 'kind': 'text', 'role': 'writer', 'filename': COPY_FILE, 'depends_on': [],
        'objective': ('Write every visible string of this page as copy.md (the page copy only, no code): '
                      + text),
        'checks': [{'kind': 'min_chars', 'value': 40},
                   {'kind': 'manual_review',
                    'rubric': 'Does the copy serve the reader and purpose of the request, with every string the '
                              'page needs and no unsupported claims?'}]}
    milestones = [copy_step]
    build_deps = ['copy']
    if designer:
        milestones.append({
            'id': 'design', 'kind': 'text', 'role': 'designer', 'filename': BRIEF_FILE, 'depends_on': [],
            'objective': ('Write brief.md, the design direction for this page (no copy, no code): layout per '
                          'breakpoint (360, 768, 1440), type scale, colour tokens, and the list of motion '
                          'moments if any. Request: ' + text),
            'checks': [{'kind': 'min_chars', 'value': 40}]})
        build_deps.append('design')
    milestones.append(dict(code, id=build_id, role='builder', depends_on=build_deps, copy_lock='copy',
                           filename='build.md' if animator else code.get('filename', 'changes.md'),
                           objective=('Build the page with the copy locked: ' + code['objective'])))
    if animator:
        milestones.append(dict(code, id='code', role='animator', depends_on=[build_id], copy_lock='copy',
                               objective=('Add the motion this page asks for to the built page, from '
                                          "Nick's motion taste and Kel's motion rules: " + text)))
    out = dict(contract, milestones=milestones, compiler='page-plan-v1',
               page={'designer': designer, 'designer_why': designer_why, 'animator': animator,
                     'copy': 'copy', 'build': build_id})
    return validate_contract(out)


def staffing_parallel(contract):
    """The Writer and the Designer run at the same time (disjoint outputs, one combine step), or None."""
    page = contract.get('page') or {}
    if not page.get('designer'):
        return None
    from .parallel import plan_streams
    plan = plan_streams({'streams': [{'name': 'copy', 'objective': 'the page copy', 'write_paths': [COPY_FILE]},
                                     {'name': 'design', 'objective': 'the design brief',
                                      'write_paths': [BRIEF_FILE]}],
                         'merge_strategy': 'the Builder combines the copy and the design brief'})
    plan.update(kind='page', integration=page.get('build') or 'code')
    return plan


def is_text_step(contract, milestone_id):
    """True for a step that writes text inside a coding job (a page's copy or design brief)."""
    spec = next((m for m in contract.get('milestones') or [] if m.get('id') == milestone_id), None)
    return bool(spec and spec.get('kind') == 'text')


# ---- the copy ---------------------------------------------------------------------------------

def copy_strings(copy_text):
    """[(key, text)] from copy.md: every `key: text` line before the notes marker."""
    from .slop import NOTES_MARKER
    body = str(copy_text or '').split(NOTES_MARKER, 1)[0]
    out = []
    in_code = False
    for line in body.splitlines():
        if line.strip().startswith('```'):
            in_code = not in_code
            continue
        if in_code:
            continue
        match = COPY_LINE.match(line)
        if match and match.group(2).strip():
            out.append((match.group(1), match.group(2).strip()))
    return out


def _norm(text):
    text = html.unescape(str(text or ''))
    text = re.sub(r'\*\*|__|(?<!\w)[*_](?!\s)|(?<!\s)[*_](?!\w)|`', '', text)  # markdown emphasis
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # markdown links keep their words
    for a, b in (('‘', "'"), ('’', "'"), ('“', '"'), ('”', '"'), ('–', '-'),
                 ('—', '-'), (' ', ' '), ('…', '...')):
        text = text.replace(a, b)
    text = text.strip().strip('"').strip()
    return ' '.join(text.split()).lower()


class _Visible(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TEXT_TAGS:
            self.skip += 1
        for name, value in attrs:
            if name in TEXT_ATTRS and value:
                self.parts.append(value)

    def handle_startendtag(self, tag, attrs):
        for name, value in attrs:
            if name in TEXT_ATTRS and value:
                self.parts.append(value)

    def handle_endtag(self, tag):
        if tag in SKIP_TEXT_TAGS and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def visible_text(markup):
    """The words a reader (or a screen reader, or a search result) gets from one HTML file."""
    parser = _Visible()
    parser.feed(str(markup or ''))
    parser.close()
    return ' '.join(parser.parts)


def copy_fidelity(copy_text, pages):
    """{'verdict', 'checked', 'missing': [(key, text)], 'summary'} comparing copy.md with the built
    pages' visible text (whitespace, quotes and markdown emphasis normalised)."""
    strings = copy_strings(copy_text)
    if not strings:
        return {'verdict': 'UNCERTAIN', 'checked': 0, 'missing': [],
                'summary': 'The copy has no "key: text" lines to check the page against.'}
    if not pages:
        return {'verdict': 'FAILED', 'checked': len(strings), 'missing': strings[:5],
                'summary': 'No HTML page was built to place the copy in.'}
    haystack = ' '.join(_norm(visible_text(markup)) for markup in pages)
    haystack_compact = ' '.join(haystack.split())
    missing = [(key, value) for key, value in strings if _norm(value) not in haystack_compact]
    if missing:
        named = '; '.join('%s: "%s"' % (key, value[:80]) for key, value in missing[:5])
        return {'verdict': 'FAILED', 'checked': len(strings), 'missing': missing,
                'summary': ('%d of %d strings from copy.md are missing or changed on the page (the copy is '
                            'locked: place the Writer\'s words exactly, or add a copy request to %s): %s'
                            % (len(missing), len(strings), COPY_REQUESTS, named))}
    return {'verdict': 'VERIFIED', 'checked': len(strings), 'missing': [],
            'summary': 'All %d strings from copy.md are on the page as written.' % len(strings)}


def built_pages(workspace):
    """The text of every HTML file in the project copy (skipping dependencies and build output)."""
    base = Path(workspace)
    skip = {'node_modules', '.git', 'dist', 'build', '.venv'}
    out = []
    for path in sorted(base.rglob('*.htm*')):
        if path.suffix.lower() not in ('.html', '.htm') or (skip & set(path.relative_to(base).parts)):
            continue
        try:
            out.append(path.read_text(encoding='utf-8', errors='replace'))
        except OSError:
            continue
    return out


def copy_check(store, job, milestone_id):
    """The copy-lock check for a page's build (or motion) step, as a verify check dict, or None."""
    import contextlib
    contract = job.get('contract') or {}
    spec = next((m for m in contract.get('milestones') or [] if m.get('id') == milestone_id), {})
    source = spec.get('copy_lock')
    if not source:
        return None
    copy_artifact = ((job.get('milestones') or {}).get(source) or {}).get('artifact')
    if not copy_artifact:
        return dict(kind='copy_lock', verdict='UNCERTAIN', reason='The Writer\'s copy is not available.')
    copy_text = store.artifact_text(copy_artifact)
    with contextlib.closing(store.connect()) as db:
        row = db.execute("SELECT path FROM code_workspaces WHERE job_id=?", (job['id'],)).fetchone() \
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='code_workspaces'").fetchone() else None
    if not row:
        return dict(kind='copy_lock', verdict='UNCERTAIN', reason='The built page could not be found.')
    result = copy_fidelity(copy_text, built_pages(row['path']))
    if result['verdict'] == 'UNCERTAIN':
        # A copy with no key lines can't be compared: said plainly, never a block on the Builder.
        return dict(kind='copy_lock', verdict='VERIFIED', findings=[result['summary']], advisory=True)
    return dict(kind='copy_lock', verdict=result['verdict'], findings=[result['summary']],
                checked=result['checked'])
