"""D-88: the deterministic slop scan for the Writer's prose (WRITER_ANIMATOR_ROLES.md §1.3 item 4).

A small script, not a model. It counts the patterns that mark machine-written prose, per 1,000
words, the way EQ-Bench's Slop Score does (human baseline about 7, most models 10-40): over-used
words, stock phrases, "not X but Y" contrasts, vague attribution, rule-of-three padding, formulaic
em dashes, and Nick's own banned words when his style sheet lists any. The Editor blocks on a score
over the threshold (D-88.4); everything else it finds is advisory.

Only the draft is scanned: code blocks, the notes after the `<!-- notes -->` marker (claim table,
open questions) and a page's copy keys are left out. Short texts are damped (scored over at least
250 words) so one stray word never fails a paragraph.
"""
import re

THRESHOLD = 12.0  # per 1,000 words; tuned later from Nick's reactions (D-88.4)
MIN_WORDS = 250
NOTES_MARKER = '<!-- notes -->'

# Words models over-use far beyond human rates (EQ-Bench slop list, Wikipedia "Signs of AI writing").
WORDS = (
    'delve', 'delves', 'delving', 'tapestry', 'testament', 'vibrant', 'bustling', 'intricate',
    'intricacies', 'meticulous', 'meticulously', 'seamless', 'seamlessly', 'leverage', 'leveraging',
    'elevate', 'elevates', 'embark', 'realm', 'pivotal', 'paramount', 'underscore', 'underscores',
    'underscoring', 'showcase', 'showcases', 'showcasing', 'foster', 'fosters', 'fostering', 'holistic',
    'synergy', 'unlock', 'unlocks', 'unleash', 'game-changer', 'game-changing', 'cutting-edge',
    'ever-evolving', 'multifaceted', 'transformative', 'groundbreaking', 'harness', 'harnessing',
    'empower', 'empowers', 'empowering', 'spearhead', 'streamline', 'bolster', 'myriad', 'plethora',
    'whimsical', 'enigmatic', 'beacon', 'symphony', 'labyrinth', 'interplay', 'captivating',
    'resonate', 'resonates', 'noteworthy', 'commendable', 'invaluable', 'nuanced', 'ethos',
    'furthermore', 'moreover', 'additionally', 'navigating', 'landscape', 'crucial', 'robust',
)
PHRASES = (
    "it's important to note", 'it is important to note', "it's worth noting", 'it is worth noting',
    'worth mentioning', "in today's fast-paced", "in today's digital", 'in the ever-changing',
    'in conclusion', 'in summary', 'to sum up', 'at the end of the day', 'plays a crucial role',
    'plays a vital role', 'plays a pivotal role', 'a testament to', 'stands as a', 'serves as a',
    "whether you're", 'look no further', 'dive into', "let's dive", 'deep dive', 'unlock the power',
    'the power of', 'in the realm of', 'navigate the complexities', 'rich tapestry',
    'embark on a journey', 'when it comes to', 'a myriad of', 'the world of', 'rest assured',
    'without further ado', 'buckle up', "here's the thing", 'the bottom line', 'last but not least',
    'first and foremost', 'a wide range of', 'an array of', 'nestled in', 'boasts a',
)
VAGUE_ATTRIBUTION = re.compile(
    r"\b(?:experts|studies|research|many|some|critics|observers|industry reports?) "
    r"(?:say|says|suggest|suggests|show|shows|believe|argue|agree|have found|note)\b", re.IGNORECASE)
CONTRAST = re.compile(
    r"\bnot (?:just|only|merely|simply) [^.!?]{1,80}?\b(?:but|it's|it is)\b"
    r"|\b(?:isn't|is not|aren't|are not|wasn't|was not) (?:just|only|merely|simply) (?:about )?[^.!?]{1,60}?[,;—-]"
    r"|\b(?:it's|it is|this is|that's|that is) not (?:about )?[^.!?,;]{1,60}[,;—]\s*(?:it's|it is|but)\b",
    re.IGNORECASE)
TRIAD = re.compile(r"\b[A-Za-z][\w-]*, [A-Za-z][\w-]*,? and [A-Za-z][\w-]*\b")
EM_DASH = re.compile(r"—| -- ")
CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")


def draft_part(text):
    """The prose to scan: before the notes marker, with code blocks removed."""
    text = str(text or '')
    if NOTES_MARKER in text:
        text = text.split(NOTES_MARKER, 1)[0]
    return CODE_BLOCK.sub(' ', text)


def banned_from_style(style_text):
    """Nick's banned words and phrases from `Memory\\Taste\\Writing\\style.md`: the bullet lines under a
    heading containing "banned" (case-insensitive). Empty when he has written none."""
    out, inside = [], False
    for line in str(style_text or '').splitlines():
        stripped = line.strip()
        if stripped.startswith('#'):
            inside = 'banned' in stripped.lower()
            continue
        if inside and stripped[:1] in ('-', '*'):
            phrase = stripped[1:].strip().strip('"“”\'').strip()
            if phrase:
                out.append(phrase.lower())
    return out


def scan(text, *, banned=(), threshold=THRESHOLD):
    """{'words', 'hits': [{kind, text, count}], 'total', 'score', 'threshold', 'over'} for one draft."""
    prose = draft_part(text)
    lower = prose.lower().replace('’', "'")
    words = WORD.findall(prose)
    counts = {}

    def hit(kind, what, n=1):
        if n > 0:
            key = (kind, what)
            counts[key] = counts.get(key, 0) + n

    tokens = [w.lower().replace('’', "'") for w in words]
    wordset = set(WORDS)
    for token in tokens:
        if token in wordset:
            hit('word', token)
    for phrase in PHRASES:
        n = len(re.findall(r'(?<![\w])' + re.escape(phrase) + r'(?![\w])', lower))
        hit('phrase', phrase, n)
    for phrase in banned or ():
        phrase = str(phrase).lower().strip()
        if phrase:
            hit('banned', phrase, len(re.findall(r'(?<![\w])' + re.escape(phrase) + r'(?![\w])', lower)))
    for match in CONTRAST.finditer(prose):
        hit('contrast', ' '.join(match.group(0).split())[:60])
    for match in VAGUE_ATTRIBUTION.finditer(prose):
        hit('vague attribution', match.group(0).lower())
    triads = TRIAD.findall(prose)
    # One list of three is ordinary writing; a habit of them is padding.
    if len(triads) > 1 + len(tokens) // 400:
        hit('rule of three', 'lists of three', len(triads) - 1 - len(tokens) // 400)
    dashes = len(EM_DASH.findall(prose))
    allowed = 1 + len(tokens) // 150
    if dashes > allowed:
        hit('em dash', 'formulaic em dashes', dashes - allowed)
    hits = [{'kind': kind, 'text': what, 'count': n} for (kind, what), n in
            sorted(counts.items(), key=lambda item: (-item[1], item[0]))]
    total = sum(item['count'] for item in hits)
    score = round(total * 1000.0 / max(len(tokens), MIN_WORDS), 1)
    return {'words': len(tokens), 'hits': hits, 'total': total, 'score': score,
            'threshold': threshold, 'over': score > threshold}


def summary(result, limit=6):
    """One plain line for a check, a finding or the Writer's retry: the score and the worst hits."""
    top = ', '.join('"%s"%s' % (item['text'], ' x%d' % item['count'] if item['count'] > 1 else '')
                    for item in result['hits'][:limit])
    line = 'Slop score %.1f per 1,000 words (limit %.0f)' % (result['score'], result['threshold'])
    return line + (': ' + top if top else '')


def check(store, job, milestone_id, text):
    """The slop check on a Writer's step, as one verify check (None for every other step).

    Over the threshold it fails the step (D-88.4: slop over the threshold is one of the Editor's four
    blocking conditions), naming the worst hits, so the Writer's next draft is told exactly what to
    cut. A page's copy is scanned on its strings only (the `key:` labels are not prose).
    """
    from .staff import step_role
    if step_role(job, milestone_id) != 'writer':
        return None
    try:
        from .taste import writing_style
        banned = banned_from_style(writing_style(getattr(store, 'root', None)))
    except Exception:
        banned = []
    spec = next((m for m in (job.get('contract') or {}).get('milestones') or []
                 if m.get('id') == milestone_id), {})
    prose = text
    if spec.get('filename') == 'copy.md':
        from .pages import copy_strings
        strings = copy_strings(text)
        if strings:
            prose = '\n'.join(value for _key, value in strings)
    result = scan(prose, banned=banned)
    line = summary(result)
    if result['over']:
        return dict(kind='slop', verdict='FAILED', failure='slop', score=result['score'],
                    threshold=result['threshold'], findings=[line + '. Cut these and redraft.'])
    return dict(kind='slop', verdict='VERIFIED', score=result['score'], threshold=result['threshold'],
                findings=[line])
