"""Mission staffing policy v0: the deterministic rule table (Phase 5.0).

Design: `ux-audit/workforce-os/05_MISSION_STAFFING_ALGORITHM.md`. Staffing is a decision
with recorded reasons, never a spawn; this module ships the constitution-level data only
(tier ladder, feature vector, hard rules R1-R10, caps, score weights, budget classes).
The scoring and staffing-record functions land with the D1/D2 increments; nothing here
staffs anything.
"""
import contextlib
import json
import math
import time

from .core import PolicyError

TIERS = (
    {'id': 'D0', 'name': 'NO SUBAGENT', 'team': 'Kel answers or acts directly',
     'ceremony': 'none', 'assurance': 'builtin checks',
     'typical_use': 'questions, small reversible edits, formatting, lookups'},
    {'id': 'D1', 'name': 'ONE SPECIALIST', 'team': 'one worker plus standard checks',
     'ceremony': 'light', 'assurance': 'builtin checks + evidence',
     'typical_use': 'single-artifact tasks, one-file fixes, one-document drafts'},
    {'id': 'D2', 'name': 'SMALL POD', 'team': 'two or three workers, mostly sequential',
     'ceremony': 'standard', 'assurance': 'testing + maintainability floors',
     'typical_use': 'medium features, research summaries, design tasks'},
    {'id': 'D3', 'name': 'PARALLEL TEAM', 'team': 'three to six workers, up to three parallel streams',
     'ceremony': 'full', 'assurance': 'standard + integration checks; Oracle optional',
     'typical_use': 'large features, research fan-out, independent migrations'},
    {'id': 'D4', 'name': 'HIGH-ASSURANCE TEAM', 'team': 'D3 plus mandatory Sentinel + Oracle',
     'ceremony': 'full + gates', 'assurance': 'never-gate lenses + adversarial oracle',
     'typical_use': 'security-sensitive, release-critical, high-consequence work'},
)

FEATURES = (
    {'id': 'complexity', 'scale': '0-3',
     'computed_from': 'scope signals, file/domain count, dependencies'},
    {'id': 'decomposability', 'scale': '0-3',
     'computed_from': 'artifact boundaries, module seams, source-domain split'},
    {'id': 'sequentiality', 'scale': '0-3',
     'computed_from': 'dependency chains, shared interfaces, order-dependent state'},
    {'id': 'uncertainty', 'scale': '0-3',
     'computed_from': 'unknowns list, questions raised by Discovery'},
    {'id': 'novelty', 'scale': '0-3',
     'computed_from': 'first time in project, novel stack, no reusable playbook'},
    {'id': 'risk', 'scale': '0-3',
     'computed_from': 'risk classes: security boundary, data loss, money, externals'},
    {'id': 'domain_breadth', 'scale': '0-3', 'computed_from': 'required skill families'},
    {'id': 'tool_requirements', 'scale': '0-3', 'computed_from': 'capability requirement union'},
    {'id': 'consequence_of_failure', 'scale': '0-3',
     'computed_from': 'reversibility analysis, blast radius'},
    {'id': 'user_facing', 'scale': '0-1', 'computed_from': 'UI/product surface touched'},
    {'id': 'release_proximity', 'scale': '0-2',
     'computed_from': 'ship/deploy included or imminent'},
    {'id': 'budget_class', 'scale': 'tiny/standard/deep/high-assurance',
     'computed_from': 'user setting + project default'},
)

RULES = (
    {'id': 'R1', 'kind': 'hard',
     'statement': 'Sequentiality >= 2 with decomposability <= 1 caps the tier at D2; parallel streams are forbidden.'},
    {'id': 'R2', 'kind': 'hard',
     'statement': 'Parallel streams need no dependency path between subtasks, disjoint write scopes, and per-stream budgets.'},
    {'id': 'R3', 'kind': 'hard',
     'statement': 'A security boundary (auth, secrets, permissions, network exposure, supply chain) makes Sentinel mandatory; tier >= D2.'},
    {'id': 'R4', 'kind': 'hard',
     'statement': 'Production deploy or release scope engages Release; the release-integrity lens is mandatory; assurance >= D2.'},
    {'id': 'R5', 'kind': 'hard',
     'statement': 'An irreversible or externally visible effect needs an approval gate and independent review; tier >= D2.'},
    {'id': 'R6', 'kind': 'hard',
     'statement': 'Data deletion or migration requires the data-integrity lens; migrations execute sequentially by default.'},
    {'id': 'R7', 'kind': 'hard',
     'statement': 'A new third-party dependency gets a supply-chain check and a recorded decision in the packet.'},
    {'id': 'R8', 'kind': 'hard',
     'statement': 'Concurrent worker cap <= 6; spawn depth <= 2 (default 1); children per agent <= 4; grandchildren per mission <= 10; leaves lose spawn tools.'},
    {'id': 'R9', 'kind': 'hard',
     'statement': 'D3/D4 requires a decomposition statement: what runs in parallel, why it is independent, how outputs merge.'},
    {'id': 'R10', 'kind': 'hard',
     'statement': 'No tier upgrade as a stall remedy without new decomposition evidence.'},
)

CAPS = {'workers_max': 6, 'depth_default': 1, 'depth_max': 2, 'children_per_agent_max': 4,
        'grandchildren_per_mission_max': 10}

WEIGHTS = {'complexity': 1.0, 'decomposability': 0.8, 'sequentiality': 0.9, 'uncertainty': 0.6,
           'novelty': 0.5, 'risk': 1.2, 'domain_breadth': 0.5, 'tool_requirements': 0.4,
           'consequence_of_failure': 1.2, 'user_facing': 0.3, 'release_proximity': 0.5}

SCORE_BANDS = (
    {'tier': 'D0', 'condition': 'S <= 2 and all hard rules clear'},
    {'tier': 'D1', 'condition': '2 < S <= 5'},
    {'tier': 'D2', 'condition': '5 < S <= 9'},
    {'tier': 'D3', 'condition': '9 < S <= 14 and decomposability >= 2 and sequentiality <= 1'},
    {'tier': 'D4', 'condition': 'S > 14 or any risk/consequence >= 2 with an external effect'},
)

BUDGET_CLASSES = (
    {'id': 'tiny', 'envelope': '<= ~1 single-agent turn', 'typical_tiers': 'D0',
     'notes': 'no staffing'},
    {'id': 'standard', 'envelope': '~2-5x single-agent baseline', 'typical_tiers': 'D1-D2',
     'notes': 'default for features'},
    {'id': 'deep', 'envelope': '~5-12x baseline', 'typical_tiers': 'D2-D3',
     'notes': 'justified by decomposability or length'},
    {'id': 'high-assurance', 'envelope': '~10-20x baseline', 'typical_tiers': 'D3-D4',
     'notes': 'security/release/high-consequence'},
)


def rule(rule_id):
    """The rule-table entry for an id, or a refusal for an unknown rule."""
    for item in RULES:
        if item['id'] == rule_id:
            return item
    raise PolicyError('Unknown staffing rule: %s' % rule_id)


# ---- decision function v1 (Phase 5.2) ------------------------------------------------------

# The scored subset of the feature vector (budget_class is a label, not a score input).
SCORED_SCALES = {'complexity': 3, 'decomposability': 3, 'sequentiality': 3, 'uncertainty': 3,
                 'novelty': 3, 'risk': 3, 'domain_breadth': 3, 'tool_requirements': 3,
                 'consequence_of_failure': 3, 'user_facing': 1, 'release_proximity': 2}

# Mission flags that trip hard rules; the second element is the minimum tier the rule forces
# (None = recording only). Flags are conservative inputs, not scored features.
FLAG_RULES = {'security_boundary': ('R3', 'D2'), 'release': ('R4', 'D2'),
              'irreversible': ('R5', 'D2'), 'data_migration': ('R6', 'D2'),
              'new_dependency': ('R7', None)}

BAND_CEILINGS = (('D0', 2.0), ('D1', 5.0), ('D2', 9.0), ('D3', 14.0), ('D4', float('inf')))
TIER_ORDER = ('D0', 'D1', 'D2', 'D3', 'D4')


def _tier_index(tier):
    if tier not in TIER_ORDER:
        raise PolicyError('Unknown tier: %s' % tier)
    return TIER_ORDER.index(tier)


def score(features):
    """Deterministic weighted score over the feature vector (doc 05 section 4).

    Every scored feature is required and must sit inside its declared scale; unknown keys
    are refused so a feature-vector change can never slip through silently. Decomposability
    contributes only when sequentiality <= 1 (doc 05 §4 — F1).
    """
    if not isinstance(features, dict):
        raise PolicyError('Staffing features must be an object')
    unknown = sorted(set(features) - set(SCORED_SCALES) - {'budget_class'})
    if unknown:
        raise PolicyError('Unknown staffing feature(s): %s' % ', '.join(unknown))
    total = 0.0
    sequential = features.get('sequentiality')
    for name, scale in SCORED_SCALES.items():
        value = features.get(name)
        if type(value) is not int or not 0 <= value <= scale:
            raise PolicyError('Feature %s must be an integer 0..%d' % (name, scale))
        if name == 'decomposability' and sequential > 1:
            # Doc 05 section 4: decomposability only counts when work is not sequential (F1).
            continue
        total += WEIGHTS[name] * value
    return total


def decide(features, *, flags=(), tier_max=None, budget_class=None):
    """Decide the staffing tier from mission features (doc 05; deterministic, recorded reasons).

    Returns the tier, the score, the rules that fired and the reasons behind every cap or
    raise. D0/D1 are the supported outcomes of this increment; higher tiers are returned so
    the caller can refuse them explicitly (pods arrive in 5.3+).
    """
    total = score(features)
    reasons = ['score %.1f over the feature vector' % total]
    rules_fired = []
    tier = 'D4'
    for band_tier, ceiling in BAND_CEILINGS:
        if total <= ceiling:
            tier = band_tier
            break
    reasons.append('band %s' % tier)
    if features.get('sequentiality', 0) >= 2 and features.get('decomposability', 0) <= 1:
        # Doc 05 R1 verbatim: sequentiality >= 2 with decomposability <= 1 caps the tier at D2.
        rules_fired.append({'id': 'R1', 'effect': 'cap D2 (sequential work with low decomposition)'})
        reasons.append('R1 fired (sequentiality >= 2 and decomposability <= 1); capped at D2')
        if _tier_index(tier) > _tier_index('D2'):
            tier = 'D2'
    if tier in ('D3', 'D4') and not (features.get('decomposability', 0) >= 2
                                     and features.get('sequentiality', 0) <= 1):
        reasons.append('D3+ band needs decomposability >= 2 and sequentiality <= 1; capped at D2')
        tier = 'D2'
    for flag in flags:
        if flag not in FLAG_RULES:
            raise PolicyError('Unknown mission flag: %s' % flag)
        rule_id, minimum = FLAG_RULES[flag]
        if minimum is None:
            rules_fired.append({'id': rule_id, 'effect': 'recorded for the packet'})
            reasons.append('%s noted (%s)' % (rule_id, flag))
            continue
        if _tier_index(tier) < _tier_index(minimum):
            rules_fired.append({'id': rule_id, 'effect': 'raise to %s' % minimum})
            reasons.append('%s fired: %s raises the tier to %s' % (rule_id, flag, minimum))
            tier = minimum
        else:
            rules_fired.append({'id': rule_id, 'effect': 'satisfied at %s' % tier})
            reasons.append('%s fired: %s already above %s' % (rule_id, flag, minimum))
    if tier_max is not None:
        if _tier_index(tier_max) < _tier_index(tier):
            reasons.append('tier_max %s applied' % tier_max)
            tier = tier_max
    chosen_budget = budget_class or features.get('budget_class') or 'standard'
    class_ids = tuple(item['id'] for item in BUDGET_CLASSES)
    if chosen_budget not in class_ids:
        raise PolicyError('Budget class is one of %s' % ', '.join(class_ids))
    workers = {'D0': 0, 'D1': 1}.get(tier)
    return {'tier': tier, 'score': round(total, 2), 'rules_fired': rules_fired,
            'reasons': reasons, 'budget_class': chosen_budget,
            'workers': workers if workers is not None else None,
            'supported': tier in ('D0', 'D1')}


# ---- V2-12: learn from outcome history (directive section 17) --------------------------------
#
# "Learn from outcome history: when solo succeeds; when specialists help; when independent review
# helps; when parallelism helps; when high assurance is unnecessary." The rule table above decides
# from the mission's own shape; this reads what actually HAPPENED on comparable missions (same
# decided tier, settled) and offers exactly one bounded step of advice, always explainable, never
# through a hard rule's floor and never past the caps. Thin history is not evidence: below the
# minimum nothing changes and the reasons say so.

ADVICE_MIN_MISSIONS = 3
BLOCKER_SEVERITIES = ('blocker', 'critical')


def _flag_floor(flags):
    """The lowest tier the hard flags allow (R3-R6 minimums); D0 when none fire."""
    floor = 'D0'
    for flag in flags or ():
        entry = FLAG_RULES.get(flag)
        if entry and entry[1] is not None:
            if _tier_index(entry[1]) > _tier_index(floor):
                floor = entry[1]
    return floor


def _mission_tiers(store):
    """mission_id -> decided tier, joined through staffing.decided / contract.issued (as doc 11 §3)."""
    with contextlib.closing(store.connect()) as db:
        try:
            task_to_mission = {row['task_id']: row['mission_id']
                               for row in db.execute('SELECT mission_id, task_id FROM task_contracts')}
            events = [dict(row) for row in db.execute('SELECT * FROM team_events ORDER BY seq')]
            findings = [dict(row) for row in db.execute('SELECT mission_id, severity, status FROM findings')]
        except Exception as exc:
            if 'no such table' in str(exc).lower():
                return {}, {}
            raise
    issued, assigned = {}, {}
    for row in events:
        if row['kind'] == 'staffing.decided' and row['assignment_id'] and row['detail']:
            try:
                detail = json.loads(row['detail'])
            except (TypeError, ValueError):
                detail = {}
            if detail.get('tier'):
                assigned[row['assignment_id']] = detail['tier']
    settled = set()
    for row in events:
        if row['kind'] == 'contract.issued' and row['assignment_id'] and row['detail']:
            try:
                detail = json.loads(row['detail'])
            except (TypeError, ValueError):
                detail = {}
            if detail.get('task_id'):
                issued[row['assignment_id']] = detail['task_id']
        elif row['kind'] == 'task.closed' and row['detail']:
            try:
                detail = json.loads(row['detail'])
            except (TypeError, ValueError):
                detail = {}
            if detail.get('task_id'):
                settled.add(detail['task_id'])
    tiers = {}
    for assignment_id, task_id in issued.items():
        mission_id = task_to_mission.get(task_id)
        tier = assigned.get(assignment_id)
        if mission_id and tier:
            tiers.setdefault(mission_id, tier)
    blockers = {}
    for row in findings:
        mission_id = row.get('mission_id')
        if not mission_id:
            continue
        slot = blockers.setdefault(mission_id, False)
        if row.get('status') != 'dismissed' and row.get('severity') in BLOCKER_SEVERITIES:
            slot = blockers[mission_id] = True
    settled_missions = {task_to_mission[task_id] for task_id in settled
                        if task_id in task_to_mission}
    return ({mission: tier for mission, tier in tiers.items() if mission in settled_missions},
            {mission: blockers.get(mission, False) for mission in tiers})


def outcome_advice(store, features, *, flags=(), tier_max=None, budget_class=None,
                   minimum=ADVICE_MIN_MISSIONS, now=None):
    """One bounded, explained step of advice from settled missions at the same tier.

    Returns `base_tier`, `advised_tier` (identical when nothing changed), `direction`
    ('raise' / 'lower' / 'none'), `applied` (true only when the step is legal against the
    module's own floors and caps) and the plain reasons behind it — including the numbers
    the history showed. It never decides anything by itself: callers record it and apply it
    only where their path can honour it.
    """
    base = decide(features, flags=tuple(flags), tier_max=tier_max, budget_class=budget_class)
    tiers, blockers = _mission_tiers(store)
    base_tier = base['tier']
    history = {'tier': base_tier, 'settled': 0, 'with_blockers': 0, 'clean': 0}
    same_tier = [mission for mission, tier in tiers.items() if tier == base_tier]
    history['settled'] = len(same_tier)
    history['with_blockers'] = sum(1 for mission in same_tier if blockers.get(mission))
    history['clean'] = len(same_tier) - history['with_blockers']
    advice = {'base_tier': base_tier, 'advised_tier': base_tier, 'direction': 'none',
              'applied': False, 'history': history, 'minimum': minimum,
              'reasons': ['no history advice: %d settled missions at %s (minimum %d)'
                          % (len(same_tier), base_tier, minimum)]}
    if len(same_tier) < minimum:
        return advice
    index = _tier_index(base_tier)
    flag_floor = _flag_floor(flags)
    r1_fired = bool(features.get('sequentiality', 0) >= 2
                    and features.get('decomposability', 0) <= 1)
    low_decomp = not (features.get('decomposability', 0) >= 2
                      and features.get('sequentiality', 0) <= 1)
    direction = None
    if history['with_blockers'] >= max(minimum, math.ceil(len(same_tier) / 2)):
        direction = 'raise'
        candidate = TIER_ORDER[min(index + 1, len(TIER_ORDER) - 1)]
    elif history['clean'] == len(same_tier):
        direction = 'lower'
        candidate = TIER_ORDER[max(index - 1, 0)]
    if direction == 'raise':
        reasons = ['%d of %d settled missions at %s recorded blocker-class findings; one step up'
                   % (history['with_blockers'], len(same_tier), base_tier)]
        ceiling = tier_max or 'D4'
        if _tier_index(ceiling) < _tier_index(candidate):
            reasons.append('held at %s: tier_max is %s' % (base_tier, ceiling))
            candidate = base_tier
        elif r1_fired and _tier_index(candidate) > _tier_index('D2'):
            reasons.append('held at %s: R1 caps sequential, low-decomposition work at D2' % base_tier)
            candidate = base_tier
        elif low_decomp and _tier_index(candidate) > _tier_index('D2'):
            reasons.append('held at %s: D3+ needs decomposability >= 2 and sequentiality <= 1' % base_tier)
            candidate = base_tier
        advice.update(advised_tier=candidate, direction='raise' if candidate != base_tier else 'none',
                      applied=candidate != base_tier, reasons=reasons)
        return advice
    if direction == 'lower':
        reasons = ['%d settled missions at %s passed without blocker-class findings; one step down'
                   % (len(same_tier), base_tier)]
        if _tier_index(candidate) < _tier_index(flag_floor):
            reasons.append('held at %s: a hard rule requires at least %s' % (base_tier, flag_floor))
            candidate = base_tier
        advice.update(advised_tier=candidate, direction='lower' if candidate != base_tier else 'none',
                      applied=candidate != base_tier, reasons=reasons)
        return advice
    advice['reasons'] = ['mixed history at %s (%d with blockers, %d clean); no advice'
                         % (base_tier, history['with_blockers'], history['clean'])]
    return advice


def resolve(store, features, *, flags=(), tier_max=None, budget_class=None, advice=True,
            minimum=ADVICE_MIN_MISSIONS):
    """`decide` plus the outcome advice the callers record beside it.

    When history advice applies, the returned tier already reflects it — but only inside the
    rule table's own floors and caps. With no comparable history this is exactly `decide`.
    """
    decision = decide(features, flags=tuple(flags), tier_max=tier_max, budget_class=budget_class)
    if advice and store is not None:
        item = outcome_advice(store, features, flags=tuple(flags), tier_max=tier_max,
                              budget_class=budget_class, minimum=minimum)
        decision['advice'] = item
        if item['applied'] and item['advised_tier'] != decision['tier']:
            decision['tier'] = item['advised_tier']
            decision['reasons'] = list(decision['reasons']) + list(item['reasons'])
            decision['workers'] = {'D0': 0, 'D1': 1}.get(decision['tier'])
    return decision
