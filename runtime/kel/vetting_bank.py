"""Design Vetting Sessions — question bank and adaptation rules (template: Product / UI design).

The bank is data: stable question ids (Q1…), a section, an optional design-space for visual
questions, options with explicit tags ("Recommended" only with a stated reason; alternative tags
where no single winner exists), a plain-language explanation for `Explain simply`, and trait axes
used by greybox generation and contradiction detection. Adaptation is deterministic rule functions
over answers so batches are cognitive clusters that respond to what the user already decided —
never a hardcoded phase list — and the same engine can serve future templates by swapping banks.

SECTION_ORDER drives default batch composition; ADAPT_RULES may add or drop questions when a
prior answer changes the design space. Batch sizes are heuristics (8-20), not limits.
"""

TEMPLATE_ID = 'product_ui_design'
TEMPLATE_NAME = 'Product / UI Design Vetting'

SECTIONS = {
    'goals': 'Product goals and constraints',
    'audience': 'Audience and jobs',
    'ia': 'Information architecture',
    'modules': 'Modules and widgets',
    'interaction': 'Interactions and density',
    'edges': 'Edge and failure states',
    'responsive': 'Responsive behavior',
    'visual': 'Visual direction',
    'handoff': 'Developer handoff',
}

SECTION_ORDER = ['goals', 'audience', 'ia', 'modules', 'interaction', 'edges', 'responsive',
                 'visual', 'handoff']

BATCH_SIZE = (10, 16)  # heuristic window; the session may exceed it when dependencies demand it


def _opt(code, label, desc='', tags=None):
    # Tolerate the shorthand `_opt(code, label, {'recommended': ...})`: a dict third
    # argument is tags, never a description (desc must stay text for previews/matching).
    if isinstance(desc, dict) and tags is None:
        desc, tags = '', desc
    return {'code': code, 'label': label, 'desc': desc, 'tags': tags or {}}


QUESTIONS = [
    # ---- goals ---------------------------------------------------------------------------
    {
        'id': 'Q1', 'section': 'goals', 'prompt': 'What is the single outcome this product must produce?',
        'explain': 'In one sentence, what is different for the user after they use this?',
        'rationale': 'Every later decision is judged against this outcome.',
        'options': [
            _opt('A', 'Answer a specific question fast', 'Speed of one decision wins.'),
            _opt('B', 'Monitor a changing situation', 'State awareness over time wins.'),
            _opt('C', 'Decide between options', 'Comparison and tradeoffs win.',
                 {'recommended': 'Dashboards are usually decided between visible options; this keeps comparison first.'}),
            _opt('D', 'Produce a deliverable artifact', 'The output file/report is the product.'),
            _opt('E', 'Coordinate people', 'Assignment and progress visibility win.'),
        ],
        'traits': {'goal': 'decide'},
    },
    {
        'id': 'Q2', 'section': 'goals', 'prompt': 'What is explicitly out of scope for v1?',
        'explain': 'What should this product refuse to try, so it stays good at one thing?',
        'rationale': 'Stated non-goals prevent later scope conflicts.',
        'options': [
            _opt('A', 'Nothing is out of scope yet — decide later'),
            _opt('B', 'No collaboration/multi-user'),
            _opt('C', 'No mobile app (responsive web only)'),
            _opt('D', 'No data ingestion from external APIs'),
            _opt('E', 'No notifications/alerts'),
            _opt('F', 'Custom: describe below'),
        ],
        'traits': {},
    },
    {
        'id': 'Q3', 'section': 'goals', 'prompt': 'What is the primary constraint?',
        'explain': 'What limits the solution more than anything else?',
        'rationale': 'The constraint decides which tradeoffs are acceptable.',
        'options': [
            _opt('A', 'Time — ship something usable soon'),
            _opt('B', 'Data quality — only trustworthy numbers'),
            _opt('C', 'Performance — large data, fast interactions'),
            _opt('D', 'Simplicity — one screen, one job'),
            _opt('E', 'Extensibility — more modules will come'),
        ],
        'traits': {},
    },
    # ---- audience ------------------------------------------------------------------------
    {
        'id': 'Q4', 'section': 'audience', 'prompt': 'Who is the primary user?',
        'explain': 'Whose workflow should the layout match first?',
        'rationale': 'Density, jargon, and defaults follow the primary audience.',
        'options': [
            _opt('A', 'Me, personally (single power user)', 'One workflow, optimized for one person.',
                 {'label_alt': 'Best for power users'}),
            _opt('B', 'Analysts who live in spreadsheets', 'Dense data, familiar tables.'),
            _opt('C', 'Casual visitors who check quickly', 'Glanceable, low jargon.',
                 {'label_alt': 'Best for new users'}),
            _opt('D', 'Mixed: me daily, others occasionally',
                 {'recommended': 'Mixed use is the common dashboard reality; it forces honest defaults.'}),
        ],
        'traits': {'audience': 'mixed'},
    },
    {
        'id': 'Q5', 'section': 'audience', 'prompt': 'How often will the primary user open this?',
        'explain': 'Daily-driver products can be denser; occasional ones must re-explain themselves.',
        'rationale': 'Frequency decides how much affordance can be implicit.',
        'options': [
            _opt('A', 'Many times a day', {}),
            _opt('B', 'Daily'),
            _opt('C', 'Weekly'),
            _opt('D', 'Rarely / seasonally'),
        ],
        'traits': {},
    },
    # ---- information architecture --------------------------------------------------------
    {
        'id': 'Q6', 'section': 'ia', 'prompt': 'What is the top-level navigation shape?',
        'explain': 'Where do users go to move between the major areas?',
        'rationale': 'Navigation is the product\u2019s skeleton; it is expensive to change later.',
        'options': [
            _opt('A', 'Left sidebar (sections visible at once)',
                 {'recommended': 'Dashboards with 4+ areas keep orientation better with a persistent sidebar.'}),
            _opt('B', 'Top bar tabs (horizontal sections)'),
            _opt('C', 'Single page, sections stack (no nav)'),
            _opt('D', 'Sidebar + contextual sub-tabs'),
            _opt('E', 'Command palette first (keyboard-driven)', {'label_alt': 'Best for power users'}),
        ],
        'traits': {'nav': 'sidebar'},
    },
    {
        'id': 'Q7', 'section': 'ia', 'prompt': 'What opens first when the product loads?',
        'explain': 'Is the landing view the question list, the big picture, or the last thing I touched?',
        'rationale': 'The default view defines the product\u2019s personality.',
        'options': [
            _opt('A', 'A summary/overview of current state'),
            _opt('B', 'The main working board (dense)'),
            _opt('C', 'The last view I had open', {'label_alt': 'Strong alternative'}),
            _opt('D', 'An inbox of things needing me'),
            _opt('E', 'A start/empty state with actions'),
        ],
        'traits': {'hero': 'summary'},
    },
    {
        'id': 'Q8', 'section': 'ia', 'prompt': 'How deep can drill-down go before it must come back?',
        'explain': 'How many clicks deep is acceptable before a user loses the thread?',
        'rationale': 'Depth budget constrains module design.',
        'options': [
            _opt('A', 'One level (list \u2192 detail)'),
            _opt('B', 'Two levels (list \u2192 detail \u2192 sub-detail)'),
            _opt('C', 'Unlimited, with breadcrumbs'),
            _opt('D', 'Details always in a side panel, never a new page',
                 {'recommended': 'Side-panel detail keeps context and matches dashboard scanning.'}),
        ],
        'traits': {},
    },
    {
        'id': 'Q9', 'section': 'ia', 'prompt': 'Where does search live?',
        'explain': 'Can I find a thing by name from anywhere?',
        'rationale': 'Search changes navigation pressure.',
        'options': [
            _opt('A', 'Global search in the header'),
            _opt('B', 'Per-section filters only'),
            _opt('C', 'Command palette (Ctrl+K)'),
            _opt('D', 'No search in v1'),
            _opt('E', 'A + C (both)',
                 {'recommended': 'Both covers casual typing and keyboard speed without extra chrome.'}),
        ],
        'traits': {},
    },
    # ---- modules -------------------------------------------------------------------------
    {
        'id': 'Q10', 'section': 'modules', 'prompt': 'Which modules must be visible on the main board at once?',
        'explain': 'What must I be able to see without scrolling or clicking?',
        'rationale': 'Visible modules define the main board grid.',
        'options': [
            _opt('A', 'Primary list/table'),
            _opt('B', 'Summary metrics strip'),
            _opt('C', 'Status/activity feed'),
            _opt('D', 'Charts or sparklines'),
            _opt('E', 'Filters/controls'),
            _opt('F', 'Alerts/attention items'),
            _opt('G', 'Calendar/time view'),
            _opt('H', 'Notes or annotations'),
            _opt('I', 'Custom: list them below'),
        ],
        'traits': {},
    },
    {
        'id': 'Q11', 'section': 'modules', 'prompt': 'What is the main list/table\u2019s row shape?',
        'explain': 'What does one row represent, and how much does it show?',
        'rationale': 'Row anatomy is the most reused module.',
        'options': [
            _opt('A', 'One entity per row, few columns (name + 2-3 facts)'),
            _opt('B', 'One entity per row, many columns (analyst table)'),
            _opt('C', 'Card per entity (media-rich)'),
            _opt('D', 'Grouped rows (by category/day)'),
            _opt('E', 'Cards with an expandable detail'),
        ],
        'traits': {'row': 'rows'},
    },
    {
        'id': 'Q12', 'section': 'modules', 'prompt': 'How should entity state (good/bad/pending) be shown?',
        'explain': 'Color, icon, text — how does a row say \u201csomething is wrong\u201d?',
        'rationale': 'State encoding must survive colorblindness and scannability.',
        'options': [
            _opt('A', 'Text label only'),
            _opt('B', 'Icon + color'),
            _opt('C', 'Color bar/dot only'),
            _opt('D', 'Text + icon + color (redundant)',
                 {'recommended': 'Redundant encoding is the only one that works for every viewer.'}),
            _opt('E', 'Full border/tint of the row'),
        ],
        'traits': {},
    },
    # ---- interaction ---------------------------------------------------------------------
    {
        'id': 'Q13', 'section': 'interaction', 'prompt': 'How dense should the default view be?',
        'explain': 'Comfortable spacing (fewer things, easier) or compact (more things, faster)?',
        'rationale': 'Density is the strongest personality lever.',
        'options': [
            _opt('A', 'Comfortable — generous spacing'),
            _opt('B', 'Compact — information first'),
            _opt('C', 'Progressive — comfortable, with a density toggle',
                 {'recommended': 'A toggle lets daily users go dense without punishing first-time readers.'}),
            _opt('D', 'Adaptive — remembers my density per view'),
        ],
        'traits': {'density': 'progressive'},
    },
    {
        'id': 'Q14', 'section': 'interaction', 'prompt': 'What is the primary row action?',
        'explain': 'What happens when I click a row?',
        'rationale': 'The primary action sets interaction expectations.',
        'options': [
            _opt('A', 'Open detail panel'),
            _opt('B', 'Open full page'),
            _opt('C', 'Inline edit'),
            _opt('D', 'Navigate to a related board'),
            _opt('E', 'No row action (read-only display)'),
        ],
        'traits': {},
    },
    # ---- edges ---------------------------------------------------------------------------
    {
        'id': 'Q15', 'section': 'edges', 'prompt': 'What should an empty board say?',
        'explain': 'What is on screen when there is nothing to show yet?',
        'rationale': 'Empty states teach the model faster than docs.',
        'options': [
            _opt('A', 'One sentence explaining what will appear here'),
            _opt('B', 'Explanation + the action that creates content'),
            _opt('C', 'Sample/example data'),
            _opt('D', 'Explanation + sample toggle'),
            _opt('E', 'Custom: describe below'),
        ],
        'traits': {},
    },
    {
        'id': 'Q16', 'section': 'edges', 'prompt': 'How should a data failure appear?',
        'explain': 'When a number cannot be trusted, what replaces it?',
        'rationale': 'Trust failure is a design state, not an exception.',
        'options': [
            _opt('A', 'Hide the module'),
            _opt('B', 'Show last-known value with a stale badge'),
            _opt('C', 'Show an inline error in the module'),
            _opt('D', 'B + C (stale value and a reason)',
                 {'recommended': 'Stale-with-reason keeps the decision usable while staying honest.'}),
            _opt('E', 'Global banner for all failures'),
        ],
        'traits': {},
    },
    # ---- responsive ----------------------------------------------------------------------
    {
        'id': 'Q17', 'section': 'responsive', 'prompt': 'What must work at phone width?',
        'explain': 'If this page is opened on a phone, what is the one thing it must still do?',
        'rationale': 'Responsive scope decides layout count.',
        'options': [
            _opt('A', 'Viewing key numbers only'),
            _opt('B', 'Viewing + one primary action'),
            _opt('C', 'Full parity with desktop'),
            _opt('D', 'Not supported — desktop only', {'label_alt': 'Strong alternative'}),
        ],
        'traits': {},
    },
    {
        'id': 'Q18', 'section': 'responsive', 'prompt': 'How do side panels behave on narrow screens?',
        'explain': 'Does the detail panel stack below, become a drawer, or disappear?',
        'rationale': 'Panel behavior is the first thing to break at width.',
        'options': [
            _opt('A', 'Stack below the list'),
            _opt('B', 'Slide-over drawer'),
            _opt('C', 'Full-screen page'),
            _opt('D', 'Hidden until requested'),
        ],
        'traits': {},
    },
    # ---- visual --------------------------------------------------------------------------
    {
        'id': 'Q19', 'section': 'visual', 'prompt': 'What should the visual personality be?',
        'explain': 'If the product were a room: a calm study, a trading floor, or a workshop?',
        'rationale': 'Personality decides color, type, and motion budgets.',
        'options': [
            _opt('A', 'Calm and minimal — quiet surfaces',
                 {'label_alt': 'Best for new users'}),
            _opt('B', 'Dense command center — everything visible',
                 {'label_alt': 'Best for power users'}),
            _opt('C', 'Editorial — typography-led, generous'),
            _opt('D', 'Playful — rounded, expressive'),
            _opt('E', 'Technical — monochrome, grid-heavy'),
        ],
        'traits': {'philosophy': 'calm'},
        'visual': True,
        'space': [
            {'name': 'Calm board', 'desc': 'Sidebar, summary strip, one table, generous spacing.',
             'traits': {'nav': 'sidebar', 'hero': 'summary', 'density': 'comfortable', 'row': 'rows'}},
            {'name': 'Command center', 'desc': 'Sidebar, metrics + charts + feed visible at once, compact.',
             'traits': {'nav': 'sidebar', 'hero': 'board', 'density': 'compact', 'row': 'rows'}},
            {'name': 'Focus list', 'desc': 'No sidebar; a single strong list with inline filters.',
             'traits': {'nav': 'none', 'hero': 'feed', 'density': 'comfortable', 'row': 'rows'}},
            {'name': 'Card gallery', 'desc': 'Top tabs; entities as cards with expandable detail.',
             'traits': {'nav': 'topbar', 'hero': 'summary', 'density': 'comfortable', 'row': 'cards'}},
            {'name': 'Analyst grid', 'desc': 'Sidebar + many columns, monochrome, tiny row heights.',
             'traits': {'nav': 'sidebar', 'hero': 'board', 'density': 'compact', 'row': 'grid'}},
            {'name': 'Inbox driven', 'desc': 'Attention items first; everything else secondary.',
             'traits': {'nav': 'topbar', 'hero': 'inbox', 'density': 'comfortable', 'row': 'rows'}},
        ],
    },
    {
        'id': 'Q20', 'section': 'visual', 'prompt': 'Which accent strategy?',
        'explain': 'Where is the one color that means \u201clook here\u201d spent?',
        'rationale': 'Accent discipline keeps attention meaningful.',
        'options': [
            _opt('A', 'Single accent for actions only'),
            _opt('B', 'Accent per status (green/amber/red)'),
            _opt('C', 'Accent per section (color-coded areas)'),
            _opt('D', 'No accent — weight and size only'),
            _opt('E', 'A + B',
                 {'recommended': 'Actions plus status covers both \u201cdo\u201d and \u201cknow\u201d without decoration.'}),
        ],
        'traits': {},
    },
    # ---- handoff -------------------------------------------------------------------------
    {
        'id': 'Q21', 'section': 'handoff', 'prompt': 'Who builds this, and from what?',
        'explain': 'Will a developer build it from this spec, from a Figma file, or from generated code?',
        'rationale': 'Handoff format decides spec depth.',
        'options': [
            _opt('A', 'Me, from this spec (vibe-coding)'),
            _opt('B', 'A developer, from this spec + greyboxes'),
            _opt('C', 'A developer, from a Figma file I will make later'),
            _opt('D', 'Existing design system components apply'),
        ],
        'traits': {},
    },
    {
        'id': 'Q22', 'section': 'handoff', 'prompt': 'What must the spec include above all?',
        'explain': 'If the spec could be great at one thing, what should it be?',
        'rationale': 'Spec emphasis mirrors the risk.',
        'options': [
            _opt('A', 'Exact component behavior and states'),
            _opt('B', 'Data requirements and sources'),
            _opt('C', 'Layout geometry and responsive rules'),
            _opt('D', 'Copy and content model'),
            _opt('E', 'Decision rationale and rejected alternatives',
                 {'recommended': 'Rationale is what prevents re-litigating decisions after handoff.'}),
        ],
        'traits': {},
    },
]

# ---- adaptation ---------------------------------------------------------------------------

def _answer_label(bank, qid, answers):
    q = question_by_id(bank, qid)
    a = answers.get(qid)
    if not q or not a:
        return None
    for code in a.get('selected_options') or []:
        for opt in q['options']:
            if opt['code'] == code:
                return opt['label']
    return a.get('custom_answer') or None


def adapt(bank, answered_ids, answers, used_ids):
    """Return the next batch's question ids: remaining questions, dependency-ordered.

    Rules are deliberately explicit and small. They only *add* or *drop* questions based on
    stated answers — never reorder into mandatory phases. Unknown answers keep the default order.
    """
    remaining = [q['id'] for q in bank['questions']
                 if q['id'] not in used_ids and q['id'] not in answered_ids]
    density = _answer_label(bank, 'Q13', answers)
    nav = _answer_label(bank, 'Q6', answers)
    philosophy = _answer_label(bank, 'Q19', answers)
    freq = _answer_label(bank, 'Q5', answers)

    def add_first(qid):
        if qid in remaining:
            remaining.remove(qid)
            remaining.insert(0, qid)

    # Progressive density chosen -> progressive-disclosure details become first-class topics.
    if density and 'progressive' in density.lower():
        for qid in ('Q23', 'Q24'):
            add_first(qid)
    # Desktop-only responsive choice -> drop the narrow-screen panel question.
    phone = _answer_label(bank, 'Q17', answers)
    if phone and 'desktop only' in phone.lower() and 'Q18' in remaining:
        remaining.remove('Q18')
    # Dense command center -> status taxonomy and alert budget matter earlier.
    if philosophy and 'command center' in philosophy.lower():
        for qid in ('Q25', 'Q26'):
            add_first(qid)
    # Rare use -> re-explanation affordances matter earlier.
    if freq and 'rarely' in freq.lower():
        add_first('Q27')
    return remaining


def default_bank():
    """The template as a plain dict (questions referenced by id)."""
    return {'template': TEMPLATE_ID,
            'name': TEMPLATE_NAME,
            'sections': SECTIONS,
            'section_order': SECTION_ORDER,
            'questions': QUESTIONS,
            'batch_size': BATCH_SIZE,
            'next_id': len(QUESTIONS) + 1}


# ---- follow-up questions injected by adaptation (kept separate so ids stay stable) --------

FOLLOWUPS = [
    {
        'id': 'Q23', 'section': 'interaction',
        'prompt': 'What does progressive disclosure expand, and by what trigger?',
        'explain': 'Which details stay hidden until asked for, and what asks for them?',
        'rationale': 'Progressive density needs explicit expand rules or it degrades to hiding.',
        'options': [
            _opt('A', 'Hover reveals extra columns'),
            _opt('B', 'Row click expands inline detail'),
            _opt('C', '\u201cShow more\u201d reveals hidden columns'),
            _opt('D', 'Side panel only (table never expands)'),
            _opt('E', 'Memory: views remember my expansion choices',
                 {'recommended': 'Remembered expansion is what makes density toggles actually stick.'}),
        ],
        'traits': {},
    },
    {
        'id': 'Q24', 'section': 'interaction',
        'prompt': 'Where is the density toggle itself?',
        'explain': 'How do I switch comfortable/compact?',
        'rationale': 'Toggle placement decides whether it is ever used.',
        'options': [
            _opt('A', 'Global, in the header'),
            _opt('B', 'Per board, near filters'),
            _opt('C', 'Keyboard shortcut only'),
            _opt('D', 'Settings page only'),
        ],
        'traits': {},
    },
    {
        'id': 'Q25', 'section': 'visual',
        'prompt': 'How many simultaneous status levels can a row carry?',
        'explain': 'Can one row be both \u201cwarning\u201d and \u201cin progress\u201d? What wins visually?',
        'rationale': 'Density without a status hierarchy becomes noise.',
        'options': [
            _opt('A', 'One status per row (mutually exclusive)'),
            _opt('B', 'Two (primary + secondary badge)'),
            _opt('C', 'Unlimited, all shown'),
            _opt('D', 'One primary; the rest behind hover'),
        ],
        'traits': {},
    },
    {
        'id': 'Q26', 'section': 'modules',
        'prompt': 'What is the alert/attention budget on screen?',
        'explain': 'How many things are allowed to shout at once?',
        'rationale': 'Alert budgets keep a command center readable.',
        'options': [
            _opt('A', 'At most one banner, ever'),
            _opt('B', 'A dedicated attention strip (max ~5)'),
            _opt('C', 'Inline per-row markers, no banners'),
            _opt('D', 'B + C'),
        ],
        'traits': {},
    },
    {
        'id': 'Q27', 'section': 'edges',
        'prompt': 'How does the product re-orient a returning-a-month-later user?',
        'explain': 'What tells someone what changed since they last looked?',
        'rationale': 'Rare-frequency use requires change summaries.',
        'options': [
            _opt('A', '\u201cSince you last looked\u201d summary strip'),
            _opt('B', 'New-activity dots on changed rows'),
            _opt('C', 'A digest view per week'),
            _opt('D', 'Nothing — assume they remember'),
        ],
        'traits': {},
    },
    {
        'id': 'Q28', 'section': 'goals', 'open': True,
        'prompt': 'Anything that would make this design a failure — constraints, deal-breakers, or a feeling to avoid?',
        'explain': 'Free text: what must never be true about the result?',
        'rationale': 'Deal-breakers beat preferences: they remove options before aesthetics matter.',
        'options': [],
        'traits': {},
    },
]
QUESTIONS.extend(FOLLOWUPS)


def question_by_id(bank, qid):
    for q in bank.get('questions', []):
        if q['id'] == qid:
            return q
    return None
