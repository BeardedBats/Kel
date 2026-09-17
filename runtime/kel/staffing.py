"""Mission staffing policy v0: the deterministic rule table (Phase 5.0).

Design: `ux-audit/workforce-os/05_MISSION_STAFFING_ALGORITHM.md`. Staffing is a decision
with recorded reasons, never a spawn; this module ships the constitution-level data only
(tier ladder, feature vector, hard rules R1-R10, caps, score weights, budget classes).
The scoring and staffing-record functions land with the D1/D2 increments; nothing here
staffs anything.
"""
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
