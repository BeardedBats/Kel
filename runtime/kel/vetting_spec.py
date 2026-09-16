"""Design Vetting Sessions — option expansion, challenge text, and greybox wireframes.

Everything here is deterministic and provider-free: it turns recorded decisions and the
question bank's design space into concrete text and SVG wireframes. An optional model hook
can enrich these later; nothing in this module depends on one being available.
"""
import json
import re

# ---- More options: genuinely new directions, not paraphrases ---------------------------------

_AXES = (
    ('presentation', ('table-first', 'card grid', 'split view', 'timeline')),
    ('density', ('comfortable', 'compact', 'progressive disclosure')),
    ('primary interaction', ('inline edit', 'detail side panel', 'context menu actions')),
    ('emphasis', ('status-first', 'category-first', 'search-first')),
)


def _option_fingerprint(question):
    text = ' '.join(
        (option.get('label', '') + ' ' + (option.get('desc') or '')).lower()
        for option in question.get('options', [])
    )
    return text


def new_option_drafts(question, limit=4):
    """Return drafts that combine axis values not already represented in the question."""
    existing = _option_fingerprint(question)
    drafts = []
    for name, values in _AXES:
        for value in values:
            if value.split()[0] in existing:
                continue
            drafts.append({
                'label': _draft_label(name, value),
                'desc': 'New direction: %s takes the %s role.' % (value, name),
                'why_distinct': 'The current options do not include a %s %s.' % (value, name),
            })
            if len(drafts) >= limit:
                return drafts
    # Fall back to recombining two axes so "more options" always produces something new.
    second = _AXES[1][1]
    for value in second:
        label = '%s with %s' % (question.get('options', [{}])[0].get('label', 'the lead view'), value)
        if label.lower() not in existing:
            drafts.append({'label': label, 'desc': 'New direction: lead view, %s.' % value,
                           'why_distinct': 'No current option pairs the lead view with %s.' % value})
        if len(drafts) >= limit:
            break
    return drafts


def _draft_label(name, value):
    if name == 'presentation':
        return value.capitalize() + ' as the primary shape'
    if name == 'density':
        return value.capitalize() + ' by default'
    if name == 'primary interaction':
        return value.capitalize() + ' for changes'
    return value.capitalize() + ' ordering'


# ---- Challenge this answer --------------------------------------------------------------------

def challenge_text(question, selected_codes):
    """Three honest parts: strongest downside, tradeoff, alternative — plus the follow-up actions."""
    options = question.get('options', [])
    selected = [option for option in options if option['code'] in selected_codes]
    chosen = selected[0] if selected else None
    alternatives = [option for option in options if option['code'] not in selected_codes]
    alternative = None
    if alternatives:
        alternative = sorted(
            alternatives,
            key=lambda option: (0 if option.get('tags') else 1, option['code']),
        )[0]
    lines = ['**Challenge for Q%s**' % question['id'].lstrip('Q')]
    if chosen:
        thesis = chosen.get('desc') or chosen.get('label')
        lines.append('Strongest downside: %s gets harder once the data stops being uniform — '
                     'the opposite case is where this choice shows its cost.' % thesis.rstrip('.'))
        lines.append('Tradeoff: %s pays for itself by making the other side of this '
                     'decision (the one it de-prioritizes) explicit instead of free.' % chosen['label'])
    else:
        lines.append('Strongest downside: no option is selected yet, so the downside cannot be named honestly.')
        lines.append('Tradeoff: the tradeoff appears once a choice is on the table.')
    if alternative:
        lines.append('Alternative worth weighing: **%s. %s** — %s'
                     % (alternative['code'], alternative['label'], alternative.get('desc') or 'a materially different direction.'))
    lines.append('Keep decision · Revise · Defer')
    return '\n'.join(lines)


# ---- Greybox directions -----------------------------------------------------------------------

_LAYOUT_AXES = {
    'nav': ('left rail', 'top bar', 'no nav'),
    'density': ('comfortable rows', 'compact rows', 'progressive rows'),
    'hero': ('summary strip', 'working board', 'inbox of needs', 'feed'),
    'rail': ('right rail', 'no rail'),
}


def greybox_directions(question, session_traits=None, limit=8):
    """Deterministic direction set. Session traits bias which directions appear first."""
    session_traits = session_traits or {}
    nav = session_traits.get('nav') or _LAYOUT_AXES['nav'][0]
    density = session_traits.get('density') or _LAYOUT_AXES['density'][0]
    hero = session_traits.get('hero') or _LAYOUT_AXES['hero'][1]
    directions = []
    seen = set()

    def push(name, traits, description, theme):
        key = tuple(sorted(traits.items()))
        if key in seen:
            return
        seen.add(key)
        directions.append({'name': name, 'traits': traits, 'description': description, 'theme': theme})

    # Directed variations around the session's own traits first (they descend from the answers).
    push('Keep the answered shape', {'nav': nav, 'density': density, 'hero': hero, 'rail': 'right rail'},
         'Continuation of the choices already recorded.', 'baseline')
    push('Calm summary', {'nav': nav, 'density': 'comfortable rows', 'hero': 'summary strip', 'rail': 'no rail'},
         'One quiet screen that answers "how are we doing" before anything else.', 'calm')
    push('Working board', {'nav': nav, 'density': 'compact rows', 'hero': 'working board', 'rail': 'right rail'},
         'The board is the product; summary is a strip inside it.', 'working')
    push('Attention inbox', {'nav': nav, 'density': 'comfortable rows', 'hero': 'inbox of needs', 'rail': 'no rail'},
         'Opens on what needs you; everything else is one step away.', 'inbox')
    push('Dense command center', {'nav': 'top bar', 'density': 'compact rows', 'hero': 'working board', 'rail': 'right rail'},
         'Maximum data per screen; alerts live inline, no banners.', 'dense')
    push('Progressive reader', {'nav': 'left rail', 'density': 'progressive rows', 'hero': 'feed', 'rail': 'no rail'},
         'Rows reveal depth on demand; the surface stays calm.', 'progressive')
    push('Split cockpit', {'nav': 'left rail', 'density': 'comfortable rows', 'hero': 'working board', 'rail': 'right rail'},
         'Board left, detail right — decisions never leave the screen.', 'split')
    push('Single page, no nav', {'nav': 'no nav', 'density': 'compact rows', 'hero': 'summary strip', 'rail': 'no rail'},
         'Everything stacks on one page; navigation is scrolling.', 'minimal')
    theme_order = {'baseline': 0, 'progressive': 1, 'calm': 2, 'working': 3, 'inbox': 4, 'split': 5, 'dense': 6, 'minimal': 7}
    directions.sort(key=lambda direction: theme_order.get(direction['theme'], 9))
    return directions[:limit]


def combine_directions(directions, roles):
    """roles: {'base': 4, 'header': 2, ...} — 1-based direction numbers from parse_combine.

    `directions` is the ordered list of greybox rows/dicts for the question (each with
    'name' and 'traits'; 'traits' may be a JSON string when it comes straight from the DB).
    """
    def trait_of(entry):
        raw = entry.get('traits') if isinstance(entry, dict) else None
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except ValueError:
                raw = {}
        return dict(raw or {})

    def pick(number):
        if not directions:
            return None
        index = max(0, min(len(directions) - 1, int(number) - 1))
        return directions[index]

    base_number = roles.get('base') or 1
    base_entry = pick(base_number)
    traits = trait_of(base_entry or {})
    trait_for_role = {'header': 'hero', 'hero': 'hero', 'nav': 'nav', 'rows': 'density',
                      'density': 'density', 'rail': 'rail', 'rails': 'rail', 'emphasis': 'hero'}
    parts, sources = [], [{'direction': base_number, 'role': 'base',
                           'name': (base_entry or {}).get('name')}]
    for role, number in roles.items():
        if role == 'base':
            continue
        entry = pick(number)
        if not entry:
            continue
        trait = trait_for_role.get(role)
        if trait:
            traits[trait] = trait_of(entry).get(trait, traits.get(trait))
        parts.append('%s from Direction %s' % (role, number))
        sources.append({'direction': number, 'role': role, 'name': entry.get('name')})
    base_name = (base_entry or {}).get('name') or ('Direction %s' % base_number)
    description = 'Composite: base %s' % base_name
    if parts:
        description += ', ' + ', '.join(parts)
    return {'name': 'Composite — %s' % base_name,
            'traits': traits, 'description': description, 'theme': 'composite',
            'composite_of': sources}


# ---- Greybox wireframes (SVG) -----------------------------------------------------------------

_PALETTE = {'bg': '#f6f7f9', 'panel': '#ffffff', 'line': '#d5dae1', 'ink': '#4a5262',
            'accent': '#c9d4e3', 'strong': '#8d9bb0'}


def _box(x, y, w, h, fill, stroke=None, radius=4):
    stroke = stroke or _PALETTE['line']
    return ('<rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="%s" stroke="%s"/>'
            % (x, y, w, h, radius, fill, stroke))


def greybox_svg(direction, width=480, height=300):
    """A decision-support skeleton: blocks only, readable at a glance, no polish claimed."""
    traits = direction.get('traits') or {}
    nav = traits.get('nav', 'left rail')
    density = traits.get('density', 'comfortable rows')
    hero = traits.get('hero', 'working board')
    rail = traits.get('rail', 'no rail')
    parts = [_box(0, 0, width, height, _PALETTE['bg'], _PALETTE['bg'], 0)]
    top = 0
    # top bar
    if nav == 'top bar':
        parts.append(_box(8, 8, width - 16, 26, _PALETTE['panel']))
        parts.append('<text x="18" y="25" font-size="10" fill="%s">nav</text>' % _PALETTE['ink'])
        top = 42
    elif nav == 'left rail':
        parts.append(_box(8, 8, 84, height - 16, _PALETTE['panel']))
        parts.append('<text x="18" y="24" font-size="10" fill="%s">nav</text>' % _PALETTE['ink'])
        top = 8
    content_x = 100 if nav == 'left rail' else 8
    content_w = width - content_x - (92 if rail == 'right rail' else 8)
    y = top + 6
    # hero
    hero_h = {'summary strip': 26, 'working board': 44, 'inbox of needs': 60, 'feed': 34}.get(hero, 40)
    if hero in ('summary strip', 'working board'):
        parts.append(_box(content_x, y, content_w, hero_h, _PALETTE['accent']))
        parts.append('<text x="%d" y="%d" font-size="10" fill="%s">%s</text>'
                     % (content_x + 8, y + hero_h - 6, _PALETTE['ink'], hero))
    else:
        label = hero.replace(' rows', '')
        for index in range(3 if hero == 'feed' else 4):
            row_y = y + index * 16
            parts.append(_box(content_x, row_y, content_w, 13, _PALETTE['panel']))
        parts.append('<text x="%d" y="%d" font-size="10" fill="%s">%s</text>'
                     % (content_x + 8, y + 12, _PALETTE['strong'], label))
    y += hero_h + 8
    # rows
    row_h = {'comfortable rows': 22, 'compact rows': 14, 'progressive rows': 18}.get(density, 18)
    row_gap = {'comfortable rows': 6, 'compact rows': 3, 'progressive rows': 5}.get(density, 5)
    made = 0
    while y + row_h < height - 22 and made < 12:
        inset = 10 if density == 'progressive rows' and made % 3 == 1 else 0
        parts.append(_box(content_x + inset, y, content_w - inset, row_h, _PALETTE['panel']))
        if density == 'progressive rows' and made % 3 == 1:
            parts.append(_box(content_x + 6, y + 4, max(20, content_w // 3), row_h - 8, _PALETTE['accent']))
        made += 1
        y += row_h + row_gap
    # rail
    if rail == 'right rail':
        parts.append(_box(width - 92, top + 6, 84, height - top - 22, _PALETTE['panel']))
        parts.append(_box(width - 88, top + 14, 76, 30, _PALETTE['accent']))
        parts.append('<text x="%d" y="%d" font-size="10" fill="%s">detail</text>'
                     % (width - 82, top + 34, _PALETTE['ink']))
    parts.append('<text x="8" y="%d" font-size="10" fill="%s">%s</text>'
                 % (height - 8, _PALETTE['strong'], (direction.get('name') or '')[:60]))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
            'role="img" aria-label="greybox wireframe">%s</svg>' % (width, height, width, height, ''.join(parts)))


def parse_combine(note):
    """Parse \"Direction 4 -> base, Direction 2 -> header\" into role → direction-number pairs."""
    roles = {}
    for match in re.finditer(r'(?i)direction\s*(\d+)\s*(?:→|->|=|:|\bto\b)\s*([a-z \-]{2,20})', note or ''):
        roles[match.group(2).strip().lower()] = int(match.group(1))
    return roles


def _answer_line(question):
    answer = question.get('answer') or {}
    labels = []
    for code in answer.get('selected') or []:
        for option in question.get('options') or []:
            if option['code'] == code:
                labels.append('%s. %s' % (code, option['label']))
    if not labels and answer.get('custom'):
        labels.append('Custom: ' + answer['custom'])
    return '; '.join(labels) or None


def coverage_summary(questions):
    answered = [q for q in questions if (q.get('answer') or {}).get('status') in ('ANSWERED', 'PARTIALLY_ANSWERED')]
    open_ = [q for q in questions if (q.get('answer') or {}).get('status') not in
             ('ANSWERED', 'PARTIALLY_ANSWERED', 'SKIPPED', 'DEFERRED')]
    deferred = [q for q in questions if (q.get('answer') or {}).get('status') == 'DEFERRED']
    skipped = [q for q in questions if (q.get('answer') or {}).get('status') == 'SKIPPED']
    return {'answered': len(answered), 'open': len(open_), 'deferred': len(deferred),
            'skipped': len(skipped), 'total': len(questions)}


def build_spec_markdown(topic, template_name, questions, decisions, conflicts, greyboxes,
                        session_state='ACTIVE'):
    """Developer-ready spec, honest about what is not decided yet.

    Never invents an answer. Unresolved material appears under Open / Deferred / Assumptions
    with an explicit label; resolved material becomes decisions with their rationale.
    """
    by_section = {}
    for question in questions:
        by_section.setdefault(question.get('section') or 'other', []).append(question)

    def section_lines(section, fallback='Not covered by this template.'):
        rows = by_section.get(section) or []
        lines = []
        for question in rows:
            answer = question.get('answer') or {}
            if answer.get('status') in ('ANSWERED', 'PARTIALLY_ANSWERED'):
                lines.append('- **%s** — %s' % (question['prompt'], _answer_line(question)))
        return lines or [fallback]

    coverage = coverage_summary(questions)
    resolved = [d for d in decisions if d.get('status') == 'CONFIRMED']
    open_conflicts = [c for c in conflicts if c.get('state') == 'OPEN']
    chosen_boxes = [g for g in greyboxes if g.get('chosen')]

    lines = ['# Design specification — %s' % topic, '',
             '_Template: %s · Session state: %s · Decision coverage: %d/%d answered_' %
             (template_name, session_state, coverage['answered'], coverage['total']), '']

    lines += ['## Product objective'] + section_lines('goals', 'Open — the product objective is not decided yet.') + ['']
    lines += ['## Audience and jobs-to-be-done'] + section_lines('audience', 'Open — audience not decided yet.') + ['']
    definition = [q for q in by_section.get('visual', []) if (q.get('answer') or {}).get('status') in ('ANSWERED', 'PARTIALLY_ANSWERED')]
    lines += ['## Design principles']
    if definition:
        lines += ['- Visual direction: %s' % _answer_line(definition[0])]
    else:
        lines += ['- Open — no visual direction recorded yet.']
    lines += ['']
    lines += ['## Information architecture and navigation'] + section_lines('ia') + ['']
    lines += ['## Pages and modules'] + section_lines('modules') + ['']
    lines += ['## Behavior and interactions'] + section_lines('interaction') + ['']
    lines += ['## Loading, empty and error states'] + section_lines('edges') + ['']
    lines += ['## Responsive behavior'] + section_lines('responsive') + ['']
    lines += ['## Visual decisions']
    if chosen_boxes:
        for box in chosen_boxes:
            lines.append('- **%s** — %s' % (box.get('name'), box.get('description') or ''))
    else:
        lines.append('- No greybox direction has been chosen yet.')
    if greyboxes:
        lines.append('- Directions generated for comparison: %d.' % len(greyboxes))
    lines.append('')

    lines += ['## Rejected alternatives']
    rejected = []
    for question in questions:
        answer = question.get('answer') or {}
        if answer.get('status') not in ('ANSWERED', 'PARTIALLY_ANSWERED'):
            continue
        selected = set(answer.get('selected') or [])
        for option in question.get('options') or []:
            if option['code'] not in selected:
                rejected.append('- %s — %s (considered, not chosen)' % (question['prompt'], option['label']))
    lines += rejected[:24] or ['- None recorded yet.']
    lines.append('')

    lines += ['## Decision rationale']
    if resolved:
        for decision in resolved:
            lines.append('- **%s** — %s' % (decision.get('statement'), decision.get('rationale') or 'no rationale recorded'))
    else:
        lines.append('- No decisions confirmed yet.')
    lines.append('')

    lines += ['## Open decisions']
    if open_conflicts or coverage['open']:
        for conflict in open_conflicts:
            lines.append('- CONFLICT (unresolved): %s' % conflict.get('statement'))
        for question in by_section and questions:
            answer = question.get('answer') or {}
            if answer.get('status') in ('UNSURE', 'NEEDS_EXAMPLES', 'NEEDS_GREYBOX', 'AWAITING_VISUAL_SELECTION', 'CONFLICTING', 'PARTIALLY_ANSWERED'):
                lines.append('- %s (%s)' % (question['prompt'], answer.get('status')))
        if len(lines) and lines[-1] == '## Open decisions':
            lines.append('- None.')
    else:
        lines.append('- None — every question has a recorded answer.')
    lines.append('')

    lines += ['## Deferred and skipped']
    pending = [q for q in questions if (q.get('answer') or {}).get('status') in ('DEFERRED', 'SKIPPED')]
    lines += ['- %s (%s)' % (q['prompt'], (q.get('answer') or {}).get('status')) for q in pending] or ['- None.']
    lines.append('')

    lines += ['## Recommended assumptions (explicit, replaceable)']
    assumed = []
    for question in questions:
        answer = question.get('answer') or {}
        if answer.get('status') not in ('UNSURE', 'DEFERRED', 'SKIPPED'):
            continue
        recommended = next((o for o in (question.get('options') or []) if (o.get('tags') or {}).get('recommended')), None)
        if recommended:
            assumed.append('- If %s stays open: use %s. %s' % (question['prompt'], recommended['label'],
                                                              recommended.get('tags', {}).get('recommended')))
    lines += assumed or ['- None — no open question carries a recommended default.']
    lines.append('')

    lines += ['## Implementation notes'] + section_lines('handoff') + ['']

    lines += ['## Acceptance criteria']
    if resolved:
        for decision in resolved[:12]:
            lines.append('- When built, the product must satisfy: %s' % decision.get('statement'))
    else:
        lines.append('- Pending: no confirmed decisions yet.')
    lines.append('')
    return '\n'.join(lines)

