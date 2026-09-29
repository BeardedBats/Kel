"""D-88: Kel captures the Animator's motion and checks it (WRITER_ANIMATOR_ROLES.md §3.7, step 9).

For a standalone page the Animator ships the house spring core (`Memory\\Taste\\Motion\\kit\\
kel-motion.js`, from Kel's prototype), which exposes a seekable clock and the page's moments:

    window.__motion = {manual(on), advance(ms), moments: {name: {run(), targets: [css selectors]}}}

Kel opens the page in headless Chromium, stops the clock, runs each moment, and steps the clock one
60 fps frame at a time, recording every target's box, words and computed style; a 50 ms frame strip
is cut alongside. It repeats each moment with reduced motion on. `kel.motion_checks` turns the frames
into metrics and the H1-H9 verdicts. Kel's own UI is captured with `Tools\\motion\\capture-app.ts`
(the packaged app, off-screen), which runs the same layout rule; the engine does not launch the app.

The capture runs on its own thread before the step is verified (never inside a store transaction);
its result is cached by the step's artifact digest under `<Data>\\engine\\motion\\`.
"""
import json
import threading
import time
from pathlib import Path

STEP_MS = 1000.0 / 60
STRIP_EVERY = 3            # every third 60 fps frame = 50 ms
WINDOW_MS = 3000
MAX_PAGES = 3
MAX_TARGETS = 12
_RUNNING = {}
_LOCK = threading.Lock()

SAMPLE_JS = """(targets) => {
  const out = {boxes: {}, text: {}, style: {}};
  let n = 0;
  for (const sel of targets) {
    const found = Array.from(document.querySelectorAll(sel)).slice(0, 4);
    found.forEach((el, i) => {
      if (n >= %d) return;
      n += 1;
      const key = found.length > 1 ? sel + '#' + i : sel;
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      out.boxes[key] = (r.width || r.height) ? {x: r.left, y: r.top, w: r.width, h: r.height} : null;
      out.text[key] = (el.textContent || '').trim().slice(0, 200);
      out.style[key] = {opacity: parseFloat(cs.opacity), transform: cs.transform, filter: cs.filter,
        clipPath: cs.clipPath, layout: {width: cs.width, height: cs.height, top: cs.top, left: cs.left,
        margin: cs.margin, padding: cs.padding, fontSize: cs.fontSize}};
    });
  }
  return out;
}""" % MAX_TARGETS


def available():
    """(True, None) when a headless browser can run here, else (False, plain reason)."""
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return False, "the motion capture needs Playwright's headless Chromium, which isn't installed here"
    return True, None


def motion_pages(workspace):
    """HTML files in the project copy that expose Kel's capture hook (window.__motion)."""
    base = Path(workspace)
    skip = {'node_modules', '.git', 'dist', 'build', '.venv'}
    out = []
    for path in sorted(base.rglob('*.htm*')):
        if path.suffix.lower() not in ('.html', '.htm') or (skip & set(path.relative_to(base).parts)):
            continue
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        if '__motion' in text or 'kel-motion.js' in text:
            out.append(path)
    return out[:MAX_PAGES]


def _run_moment(page, name, targets, strip_dir=None):
    page.evaluate('window.__motion.manual(true)')
    page.evaluate('(n) => { void Promise.resolve(window.__motion.moments[n].run()); }', name)
    frames, shots = [], []
    t = 0.0
    quiet = 0
    last = None
    step = 0
    while t <= WINDOW_MS:
        sample = page.evaluate(SAMPLE_JS, targets)
        sample['t'] = round(t, 1)
        frames.append(sample)
        if strip_dir is not None and step % STRIP_EVERY == 0:
            shots.append(page.screenshot(type='png'))
        key = json.dumps([sample['boxes'], sample['style'], sample['text']], sort_keys=True)
        quiet = quiet + 1 if key == last else 0
        last = key
        if quiet * STEP_MS >= 400 and t >= 300:
            break  # at rest for 400 ms: the moment is over
        page.evaluate('(ms) => window.__motion.advance(ms)', STEP_MS)
        t += STEP_MS
        step += 1
    return frames, shots


def _strip(shots, target):
    """Tile the 50 ms screenshots into one contact sheet (needs Pillow; skipped without it)."""
    try:
        from PIL import Image
        import io
    except ImportError:
        return False
    if not shots:
        return False
    images = [Image.open(io.BytesIO(raw)).convert('RGB') for raw in shots[:40]]
    width = 360
    scaled = [img.resize((width, int(img.height * width / img.width))) for img in images]
    cols = 8
    rows = (len(scaled) + cols - 1) // cols
    h = scaled[0].height
    sheet = Image.new('RGB', (cols * (width + 4), rows * (h + 4)), (11, 26, 61))
    for i, img in enumerate(scaled):
        sheet.paste(img, ((i % cols) * (width + 4), (i // cols) * (h + 4)))
    sheet.save(target)
    return True


def capture_page(html_path, out_dir=None):
    """{'page', 'moments': {name: {metrics, checks, failures, strip}}} or {'error': plain reason}."""
    from .motion_checks import check_moment
    ok, why = available()
    if not ok:
        return {'page': str(html_path), 'error': why}
    from playwright.sync_api import sync_playwright
    uri = Path(html_path).resolve().as_uri()
    result = {'page': str(html_path), 'moments': {}}
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:  # the browser binary is missing or can't start here
            return {'page': str(html_path), 'error': "the headless browser couldn't start: %s" % str(exc)[:160]}
        try:
            names = None
            for reduced in (False, True):
                context = browser.new_context(viewport={'width': 1440, 'height': 900},
                                              reduced_motion='reduce' if reduced else 'no-preference')
                page = context.new_page()
                page.goto(uri)
                page.wait_for_load_state('load')
                if names is None:
                    names = page.evaluate('Object.keys(((window.__motion || {}).moments) || {})') or []
                    if not names:
                        return {'page': str(html_path), 'error': 'the page registers no moments in window.__motion.moments'}
                for name in names:
                    page.goto(uri)
                    page.wait_for_load_state('load')
                    targets = page.evaluate('(n) => (window.__motion.moments[n].targets || [])', name) or ['body *']
                    strip_dir = None if reduced or out_dir is None else Path(out_dir)
                    frames, shots = _run_moment(page, name, targets, strip_dir)
                    slot = result['moments'].setdefault(name, {})
                    slot['reduced_frames' if reduced else 'frames'] = frames
                    if strip_dir is not None:
                        strip_dir.mkdir(parents=True, exist_ok=True)
                        target = strip_dir / ('%s-%s.png' % (Path(html_path).stem, _safe(name)))
                        slot['strip'] = str(target) if _strip(shots, target) else None
                context.close()
        finally:
            browser.close()
    for name, slot in result['moments'].items():
        checked = check_moment(slot.get('frames') or [], slot.get('reduced_frames'))
        slot.update(metrics=checked['metrics'], checks=checked['checks'], failures=checked['failures'])
        slot.pop('frames', None)
        slot.pop('reduced_frames', None)
    return result


def _safe(name):
    return ''.join(c if c.isalnum() or c in '-_' else '-' for c in str(name))[:40]


# ---- the engine's hook --------------------------------------------------------------------------

def _cache(store, job_id, milestone_id, digest):
    return Path(store.root) / 'motion' / job_id / ('%s-%s.json' % (milestone_id, digest[:16]))


def _workspace(store, job_id):
    import contextlib
    with contextlib.closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='code_workspaces'").fetchone():
            return None
        row = db.execute('SELECT path FROM code_workspaces WHERE job_id=?', (job_id,)).fetchone()
    return row['path'] if row else None


def _animator_step(job, milestone_id):
    from .engine import code_step
    from .staff import step_role
    spec = next((m for m in (job.get('contract') or {}).get('milestones') or [] if m.get('id') == milestone_id), None)
    return bool(spec) and code_step(job, spec) and step_role(job, milestone_id) == 'animator'


def run_capture(store, job, milestone_id):
    """Capture every motion page of an Animator's step and cache the result (runs on its own thread)."""
    digest = ((job['milestones'][milestone_id] or {}).get('artifact') or {}).get('sha256') or 'none'
    cache = _cache(store, job['id'], milestone_id, digest)
    cache.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    workspace = _workspace(store, job['id'])
    if not workspace:
        out = {'status': 'not_verified', 'why': "the Animator's project copy could not be found"}
    else:
        pages = motion_pages(workspace)
        if not pages:
            out = {'status': 'not_verified', 'why': 'no page exposes window.__motion, so its moments could not be captured'}
        else:
            captured = []
            for page in pages:
                try:
                    captured.append(capture_page(page, cache.parent / 'strips'))
                except Exception as exc:  # a broken page must never stop the engine
                    captured.append({'page': str(page), 'error': 'the capture failed: %s' % str(exc)[:160]})
            errors = [c['error'] for c in captured if c.get('error')]
            ran = [c for c in captured if not c.get('error')]
            out = {'status': 'captured' if ran else 'not_verified', 'pages': captured,
                   'why': '; '.join(errors) if errors and not ran else None}
    out['seconds'] = round(time.time() - started, 1)
    cache.write_text(json.dumps(out, indent=1), encoding='utf-8')
    return out


def capture_pending(store, job, milestone_id):
    """True while an Animator's step still needs its capture (started here on its own thread); the
    engine verifies the step once the capture is cached. False for every other step."""
    if not _animator_step(job, milestone_id):
        return False
    digest = ((job['milestones'][milestone_id] or {}).get('artifact') or {}).get('sha256') or 'none'
    cache = _cache(store, job['id'], milestone_id, digest)
    if cache.exists():
        return False
    key = str(cache)
    with _LOCK:
        thread = _RUNNING.get(key)
        if thread and thread.is_alive():
            return True
        thread = threading.Thread(target=_safe_run, args=(store, job, milestone_id), daemon=True,
                                  name='kel-motion-capture')
        _RUNNING[key] = thread
        thread.start()
    return True


def _safe_run(store, job, milestone_id):
    try:
        run_capture(store, job, milestone_id)
    except Exception as exc:
        digest = ((job['milestones'][milestone_id] or {}).get('artifact') or {}).get('sha256') or 'none'
        cache = _cache(store, job['id'], milestone_id, digest)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({'status': 'not_verified', 'why': 'the capture failed: %s' % str(exc)[:200]}),
                         encoding='utf-8')


def check(store, job, milestone_id):
    """The motion verify check for an Animator's step (None for every other step).

    Hard-check failures fail the step with the moments and checks named (the Animator gets it back);
    a capture that could not run is said plainly and does not block (D-85: Nick sees the motion when he
    uses it)."""
    if not _animator_step(job, milestone_id):
        return None
    digest = ((job['milestones'][milestone_id] or {}).get('artifact') or {}).get('sha256') or 'none'
    cache = _cache(store, job['id'], milestone_id, digest)
    try:
        found = json.loads(cache.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return dict(kind='motion', verdict='VERIFIED', advisory=True,
                    findings=['Motion not verified: it was not captured.'])
    if found.get('status') != 'captured':
        return dict(kind='motion', verdict='VERIFIED', advisory=True,
                    findings=['Motion not verified: %s.' % (found.get('why') or 'it could not be captured')])
    failures, summary = [], []
    for page in found.get('pages') or []:
        for name, moment in (page.get('moments') or {}).items():
            m = moment.get('metrics') or {}
            summary.append('%s: settles %s ms, overshoot %s%%' % (name, m.get('settle_ms'), m.get('overshoot_pct')))
            failures += ['%s: %s' % (name, line) for line in moment.get('failures') or []]
    if failures:
        return dict(kind='motion', verdict='FAILED', failure='motion', evidence=str(cache),
                    findings=['The motion checks failed: ' + '; '.join(failures[:6])])
    return dict(kind='motion', verdict='VERIFIED', evidence=str(cache),
                findings=['Motion captured and checked: ' + ('; '.join(summary[:6]) or 'no moments')])


def review_images(store, job, milestone_id, limit=3):
    """(images, note) for the motion lens: the captured strips of this step, then the strips of the
    closest references from Nick's taste library (never a private one's media)."""
    import base64
    digest = ((job['milestones'][milestone_id] or {}).get('artifact') or {}).get('sha256') or 'none'
    try:
        found = json.loads(_cache(store, job['id'], milestone_id, digest).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        found = {}
    ours = [moment.get('strip') for page in found.get('pages') or []
            for moment in (page.get('moments') or {}).values() if moment.get('strip')][:limit]
    try:
        from .taste import retrieve
        refs, _anti = retrieve(store.root, (job.get('contract') or {}).get('request') or '', k=limit)
        theirs = [e['strip'] for e in refs if e.get('strip') and not e.get('local_only')][:limit]
    except Exception:
        theirs = []
    images = []
    for path in ours + theirs:
        try:
            images.append({'mime': 'image/png', 'data': base64.b64encode(Path(path).read_bytes()).decode()})
        except OSError:
            continue
    if not images:
        return [], ''
    return images, ('Images: the first %d are this work\'s frame strips (50 ms steps); the rest are strips of '
                    "the references from Nick's motion taste it should feel like." % len([p for p in ours if Path(p).exists()]))
