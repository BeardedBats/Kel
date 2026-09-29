"""D-88: the Animator's hard motion checks, computed from captured frames (WRITER_ANIMATOR_ROLES.md §3.7).

Pure and deterministic: a capture (`kel.motion_capture`) records, for each moment, every tracked
element's box, words and computed style on a stepped clock; this module turns those frames into the
moment's metrics (duration, settle, overshoot, properties) and the H1-H9 verdicts. Timing is judged
by these numbers, never by a model's eye (Animation2Code, source 18).

The layout rule is the same one `renderer/motion/layoutProbe.ts` checks for Kel's own UI (MOTION.md
§8.1): after settling nothing moves more than 1 px or re-words, and during the motion a frame-to-frame
move over 12 px and 4x its neighbours is a snap.

A frame: {'t': ms, 'boxes': {key: {x, y, w, h} | None}, 'text': {key: str}, 'style': {key: {opacity,
transform, filter, clipPath, layout: {width, height, top, left, margin...}}}}.
"""

TOLERANCE_PX = 1.0
JUMP_MIN_PX = 12.0
JUMP_RATIO = 4.0
QUIET_MS = 150          # a pause this long, then more movement, is "settled, then shifted"
TOTAL_MS = 650          # MOTION.md §2.1: a moment takes about this long
HANDOFF_MS = 900        # ... a hand-off up to this
LOOP_MS = 3000          # still moving at 3 s = an endless loop
OVERSHOOT_MAX = 1.5     # %: Kel UI 0.15-1.1 (D-78); pages keep to about 1.5 unless rules.md says otherwise
INSTANT_FADE = 0.8      # an opacity step this big within one frame is an instant swap
ALLOWED = ('transform', 'opacity', 'filter', 'clipPath')


def _dist(a, b):
    return max(abs(a['x'] - b['x']), abs(a['y'] - b['y']), abs(a['x'] + a['w'] - b['x'] - b['w']),
               abs(a['y'] + a['h'] - b['y'] - b['h']))


def _keys(frames, field):
    keys = []
    for frame in frames:
        for key in (frame.get(field) or {}):
            if key not in keys:
                keys.append(key)
    return keys


def _style(frame, key):
    return ((frame.get('style') or {}).get(key)) or {}


def changes(frames):
    """[(t, key, what)] for every frame-to-frame change (box > 0.5 px, words, or a style value)."""
    out = []
    keys = _keys(frames, 'boxes') or _keys(frames, 'style')
    for i in range(1, len(frames)):
        a, b = frames[i - 1], frames[i]
        for key in keys:
            ba, bb = (a.get('boxes') or {}).get(key), (b.get('boxes') or {}).get(key)
            if (ba is None) != (bb is None) or (ba and bb and _dist(ba, bb) > 0.5):
                out.append((b['t'], key, 'box'))
            if (a.get('text') or {}).get(key) != (b.get('text') or {}).get(key):
                out.append((b['t'], key, 'text'))
            sa, sb = _style(a, key), _style(b, key)
            for prop in ALLOWED:
                va, vb = sa.get(prop), sb.get(prop)
                if prop == 'opacity':
                    if va is not None and vb is not None and abs(float(va) - float(vb)) > 0.002:
                        out.append((b['t'], key, 'opacity'))
                elif va != vb:
                    out.append((b['t'], key, prop))
            if (sa.get('layout') or {}) != (sb.get('layout') or {}):
                out.append((b['t'], key, 'layout'))
    return out


def overshoot_pct(frames):
    """The largest travel past the final position, as % of the distance travelled (x, y, width)."""
    worst = 0.0
    for key in _keys(frames, 'boxes'):
        series = [f['boxes'].get(key) for f in frames if (f.get('boxes') or {}).get(key)]
        if len(series) < 3:
            continue
        for axis in ('x', 'y', 'w'):
            start, final = series[0][axis], series[-1][axis]
            distance = final - start
            if abs(distance) < 4:
                continue
            direction = 1 if distance > 0 else -1
            peak = max((b[axis] - final) * direction for b in series)
            if peak > 0:
                worst = max(worst, peak / abs(distance) * 100.0)
    return round(worst, 2)


def layout_violations(frames, settled_after):
    """The layoutProbe.ts rule: nothing moves or re-words after `settled_after`; no snaps during."""
    out = []
    for key in _keys(frames, 'boxes'):
        series = [(f['t'], (f.get('boxes') or {}).get(key), (f.get('text') or {}).get(key)) for f in frames]
        settled = [s for s in series if s[0] >= settled_after]
        anchor = next((s for s in settled if s[1]), None)
        if anchor:
            for t, box, _text in settled:
                if box and _dist(anchor[1], box) > TOLERANCE_PX:
                    out.append({'key': key, 't': t, 'kind': 'moved-after-settle',
                                'detail': '%.1f px from its settled box' % _dist(anchor[1], box)})
                    break
            words = next((s[2] for s in settled if s[2] is not None), None)
            for t, _box, text in settled:
                if text is not None and words is not None and text != words:
                    out.append({'key': key, 't': t, 'kind': 'text-after-settle', 'detail': '"%s" -> "%s"' % (words, text)})
                    break
        moves = []
        for i in range(1, len(series)):
            a, b = series[i - 1][1], series[i][1]
            # An element placed at its start while still invisible (an entrance set up at opacity 0)
            # did not visibly jump.
            hidden = any(float(_style(frames[j], key).get('opacity', 1) or 0) <= 0.05 for j in (i - 1, i))
            moves.append((series[i][0], _dist(a, b) if a and b and not hidden else 0.0))
        for i, (t, d) in enumerate(moves):
            if d < JUMP_MIN_PX:
                continue
            before = moves[i - 1][1] if i > 0 else 0.0
            after = moves[i + 1][1] if i + 1 < len(moves) else 0.0
            if d > JUMP_RATIO * max(before, after, 1.0):
                out.append({'key': key, 't': t, 'kind': 'jump',
                            'detail': '%.1f px in one frame (neighbours %.1f / %.1f)' % (d, before, after)})
    return out


def metrics(frames):
    """{duration_ms, settle_ms, overshoot_pct, properties} of one moment (trigger at t=0)."""
    found = changes(frames)
    if not found:
        return {'duration_ms': 0, 'settle_ms': 0, 'overshoot_pct': 0.0, 'properties': [], 'moved': False}
    first, last = found[0][0], found[-1][0]
    props = sorted({what for _t, _k, what in found if what not in ('box', 'text')})
    return {'duration_ms': int(round(last - first)), 'settle_ms': int(round(last)),
            'overshoot_pct': overshoot_pct(frames), 'properties': props, 'moved': True}


def settled_then_shifted(frames):
    """H1's second half: a pause of QUIET_MS or more, then a box moves again (settles, then shifts)."""
    moves = [(t, key) for t, key, what in changes(frames) if what == 'box']
    for (t0, _k0), (t1, key) in zip(moves, moves[1:]):
        if t1 - t0 >= QUIET_MS:
            return {'key': key, 't': t1, 'kind': 'moved-after-settle',
                    'detail': 'moved again %d ms after it had settled' % round(t1 - t0)}
    return None


def instant_swaps(frames):
    """H2: an element whose opacity jumps (nearly) all the way in one frame."""
    out = []
    for key in _keys(frames, 'style'):
        for i in range(1, len(frames)):
            a, b = _style(frames[i - 1], key).get('opacity'), _style(frames[i], key).get('opacity')
            if a is not None and b is not None and abs(float(b) - float(a)) >= INSTANT_FADE:
                out.append({'key': key, 't': frames[i]['t'], 'kind': 'instant-swap',
                            'detail': 'opacity %.2f -> %.2f in one frame' % (float(a), float(b))})
                break
    return out


def reduced_motion_moves(frames):
    """H5: under reduced motion nothing travels (cross-fades only)."""
    for key in _keys(frames, 'boxes'):
        series = [(f['t'], (f.get('boxes') or {}).get(key)) for f in frames]
        boxes = [(t, b) for t, b in series if b]
        for (t0, a), (t1, b) in zip(boxes, boxes[1:]):
            if abs(a['x'] - b['x']) > TOLERANCE_PX or abs(a['y'] - b['y']) > TOLERANCE_PX:
                return {'key': key, 't': t1, 'kind': 'moves-under-reduced-motion',
                        'detail': 'moved %.1f px with reduced motion on' % max(abs(a['x'] - b['x']), abs(a['y'] - b['y']))}
    return None


def check_moment(frames, reduced_frames=None, *, overshoot_max=OVERSHOOT_MAX, total_max=HANDOFF_MS,
                 window_ms=LOOP_MS):
    """{'metrics', 'checks': {H1..H9: {'ok', 'detail'}}, 'failures': [plain lines]} for one moment."""
    found = metrics(frames)
    checks, failures = {}, []

    def verdict(code, ok, detail):
        checks[code] = {'ok': ok, 'detail': detail}
        if ok is False:
            failures.append('%s %s' % (code, detail))

    layout = layout_violations(frames, found['settle_ms'] + 1)
    shifted = settled_then_shifted(frames)
    problems = layout + ([shifted] if shifted else [])
    verdict('H1', not problems, 'no layout shift after settling' if not problems else
            '%s: %s' % (problems[0]['key'], problems[0]['detail']))
    swaps = instant_swaps(frames)
    verdict('H2', not swaps, 'fades, never an instant swap' if not swaps else
            '%s: %s' % (swaps[0]['key'], swaps[0]['detail']))
    verdict('H3', found['overshoot_pct'] <= overshoot_max,
            'overshoot %.2f%% (limit %.1f%%)' % (found['overshoot_pct'], overshoot_max))
    looping = found['moved'] and found['settle_ms'] >= window_ms - 50
    verdict('H4', looping or found['settle_ms'] <= total_max,
            'settles at %d ms (limit %d ms%s)' % (found['settle_ms'], total_max,
                                                 '; over %d ms is long for one moment' % TOTAL_MS
                                                 if found['settle_ms'] > TOTAL_MS else ''))
    if reduced_frames is None:
        verdict('H5', None, 'reduced motion not captured')
    else:
        moved = reduced_motion_moves(reduced_frames)
        verdict('H5', not moved, 'cross-fades only under reduced motion' if not moved else
                '%s: %s' % (moved['key'], moved['detail']))
    layout_props = [(t, k) for t, k, what in changes(frames) if what == 'layout']
    verdict('H6', not layout_props, 'only transform, opacity, filter and clip-path change' if not layout_props
            else '%s: a layout property changed at %d ms' % (layout_props[0][1], layout_props[0][0]))
    verdict('H7', not looping, 'comes to rest' if not looping else 'still moving after %d ms (a loop)' % window_ms)
    verdict('H8', None, 'frame rate is not measured on a stepped clock')
    verdict('H9', None, 'replay on re-render is not measured')
    return {'metrics': found, 'checks': checks, 'failures': failures}
