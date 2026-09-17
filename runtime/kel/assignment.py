"""Agent-to-model assignment (Phase 5.1): workforce role registry v2, routing modes,
capability grants, and budget reservations.

Design: `ux-audit/workforce-os/` docs 03 (roles vs skills), 04 (roster), 05 (staffing),
10 (model & provider routing), 14 (architecture map). This module is the Phase 5.1
deliverable: roles declare capability requirements and dispatch tiers; a worker is bound to
(provider, model, runtime) by AUTO / PREFERRED / FIXED resolution and the binding is frozen
into the assignment snapshot; tools are granted only inside the role's authority ceiling
(fail-closed); budget is reserved before a worker may start.

Boundaries kept deliberately:
- Nothing here runs automatically: no live path calls `assign_worker` until the D1
  increment (5.2). The `workforce.enabled` flag is recorded into snapshots and defaults off.
- The role registry reuses the V1.4 `role_templates`/`role_versions` storage; the v2
  fields are additive (`validate_role_fields_v2`). Commander is Kel itself and is never a
  template and never spawned.
- `long_context` and `structured_output` have no provider capability token yet: they are
  recorded as advisory requirements, never silently dropped. Requirements whose tokens
  exist are hard eligibility filters, and a requirement no provider declares fails closed
  with readable reasons instead of substituting anything.
- Overlays (doc 10 section 4) are subordinate behavior patches keyed by
  (provider, model) with a (provider, *) family fallback; v1 ships the mechanism with an
  empty registry so absence is a graceful no-op.
"""
import contextlib
import os
import time

from .core import PolicyError, uid
from .router import Candidate, select
from .staffing import BUDGET_CLASSES
from .team import TOOLS, Team
from .workforce import AUTHORITY_CLASSES, AUTHORITY_RANK

MIGRATION_VERSION = 17
MIGRATION_NAME = 'v16-budget-reservations'

DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations(
  version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT);
CREATE TABLE IF NOT EXISTS budget_reservations(
  reservation_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, milestone_id TEXT,
  assignment_id TEXT, budget_class TEXT NOT NULL, tokens INTEGER NOT NULL,
  wallclock INTEGER NOT NULL, cost REAL NOT NULL, state TEXT NOT NULL,
  note TEXT, created REAL NOT NULL, updated REAL NOT NULL);
CREATE INDEX IF NOT EXISTS budget_reservations_by_job ON budget_reservations(job_id, state);
"""

RESERVATION_STATES = ('reserved', 'consumed', 'released')
ROUTING_MODES = ('AUTO', 'PREFERRED', 'FIXED')
DISPATCH_TIERS = ('fast', 'standard', 'deep', 'assurance')

# Doc 10 section 1 requirement vocabulary. The tuples hold provider capability tokens
# (providers.py); an empty tuple marks the requirement advisory in v1: recorded and
# resolved as metadata, not an eligibility filter (no provider declares a token for it).
REQUIREMENTS = ('repository_edit', 'web_research', 'image', 'vision', 'long_context',
                'structured_output', 'tool_calling', 'code_execution', 'audio', 'local_only')
REQUIREMENT_CAPABILITIES = {
    'repository_edit': ('edit',),
    'web_research': ('web',),
    'image': ('image',),
    'vision': ('vision',),
    'tool_calling': ('tools',),
    'code_execution': ('shell',),
    'audio': ('audio',),
    'long_context': (),
    'structured_output': (),
    'local_only': (),
}

# Tool -> the authority class a worker must hold at least to use it. Product-effect
# semantics: reading (including browsers and research APIs) and running checks in scratch
# do not modify the product; writes/commits need workspace authority; installs and shells
# need a lease. This matrix is the fail-closed grant rule for workforce roles.
TOOL_AUTHORITY = {
    'read': 'read-only', 'browser': 'read-only', 'external_api': 'read-only',
    'run_tests': 'read-only',
    'write': 'workspace-write', 'git': 'workspace-write',
    'install': 'leased-write', 'shell': 'leased-write',
}

# Overlay registry (doc 10 section 4): keyed 'provider:model' or 'provider:*' (family
# fallback). Empty in v1 by design; lookups are graceful no-ops when absent.
OVERLAYS = {}


def flags_snapshot(env=None):
    """The flags recorded into every assignment snapshot (doc 15 section 3).

    Per-project flag storage arrives with the first live consumer (5.2/D1); until then the
    switch is the documented environment variable and defaults to off.
    """
    env = os.environ if env is None else env
    enabled = str(env.get('KEL_WORKFORCE', '')).strip().lower() in ('1', 'true', 'yes', 'on')
    return {'workforce.enabled': enabled}


# ---- role registry v2 ----------------------------------------------------------------------

ROLE_V2_FIELDS = ('authority_max', 'capability_requirements', 'dispatch_tier', 'budget_class',
                  'default_skill_packs', 'independence', 'anti_patterns')
REVIEWER_FAMILY_RULES = ('different_family_if_available', 'any_but_executor')


def validate_role_fields_v2(fields):
    """Refuse malformed workforce role data (doc 03 section 7: the v2 additions)."""
    if not isinstance(fields, dict):
        raise PolicyError('Role fields must be an object')
    missing = [key for key in ROLE_V2_FIELDS if key not in fields]
    if missing:
        raise PolicyError('Workforce role is missing v2 field(s): %s' % ', '.join(missing))
    if fields['authority_max'] not in AUTHORITY_CLASSES:
        raise PolicyError('authority_max is one of %s' % ', '.join(AUTHORITY_CLASSES))
    reqs = fields['capability_requirements']
    if not isinstance(reqs, list) or any(req not in REQUIREMENTS for req in reqs):
        raise PolicyError('capability_requirements are drawn from %s' % ', '.join(REQUIREMENTS))
    if fields['dispatch_tier'] not in DISPATCH_TIERS:
        raise PolicyError('dispatch_tier is one of %s' % ', '.join(DISPATCH_TIERS))
    class_ids = tuple(item['id'] for item in BUDGET_CLASSES)
    if fields['budget_class'] not in class_ids:
        raise PolicyError('budget_class is one of %s' % ', '.join(class_ids))
    packs = fields['default_skill_packs']
    if not isinstance(packs, list) or any(not isinstance(p, str) or not p.strip() for p in packs):
        raise PolicyError('default_skill_packs are pack names (strings) in v1')
    independence = fields['independence']
    if not isinstance(independence, dict):
        raise PolicyError('independence is an object')
    if not isinstance(independence.get('may_not_review_own'), bool):
        raise PolicyError('independence.may_not_review_own is a boolean')
    if independence.get('reviewer_family') not in REVIEWER_FAMILY_RULES:
        raise PolicyError('independence.reviewer_family is one of %s'
                          % ', '.join(REVIEWER_FAMILY_RULES))
    patterns = fields['anti_patterns']
    if not isinstance(patterns, list) or any(not isinstance(p, str) or not p.strip()
                                             for p in patterns):
        raise PolicyError('anti_patterns are nonempty strings')
    policy = fields.get('tool_policy')
    if not isinstance(policy, dict):
        raise PolicyError('tool_policy is required')
    for side in ('allow', 'deny'):
        if not isinstance(policy.get(side), list) or any(t not in TOOLS for t in policy[side]):
            raise PolicyError('tool_policy %s lists known tools only' % side)
    return fields


COMMANDER_NOTE = ('Commander is Kel itself: never stored as a template, never spawned; '
                  'reassignment modes apply to worker roles only.')

ARCHETYPES = (
    ('discovery', 'Discovery', 'Strategy', {
        'goal': 'Turn a vague objective into a frameable problem with evidence and acceptance criteria.',
        'inputs': 'objective, project context, memory, research tools',
        'outputs': 'problem frame, typed findings, requirements, acceptance-criteria proposals, open questions',
        'quality_bar': 'sources cited; uncertainty explicit; no fabricated facts',
        'boundaries': 'no product-write authority',
        'escalation': 'contradictory evidence; unresolvable scope ambiguity; budget-overrun prediction',
        'evidence_expectations': 'artifact digests + source refs',
        'tool_policy': {'allow': ['read', 'browser', 'external_api'],
                        'deny': ['write', 'install', 'shell', 'run_tests', 'git']},
        'budget': 14,
        'authority_max': 'read-only',
        'capability_requirements': ['web_research', 'long_context', 'structured_output'],
        'dispatch_tier': 'standard',
        'budget_class': 'standard',
        'default_skill_packs': ['research-methods', 'source-eval', 'synthesis'],
        'independence': {'may_not_review_own': True, 'reviewer_family': 'any_but_executor'},
        'anti_patterns': ['research spam', 'silently narrowing scope',
                          'inference presented as fact']}),
    ('architect', 'Architect', 'Engineering', {
        'goal': 'Design a solution that is buildable, testable, risk-aware.',
        'inputs': 'frame, requirements, codebase/context',
        'outputs': 'architecture note (structure, interfaces, data flow, risks, test strategy), task decomposition proposal',
        'quality_bar': 'hidden assumptions surfaced; alternatives considered; smallest sufficient design',
        'boundaries': 'design artifacts only',
        'escalation': 'one-way-door architecture choices; unverifiable constraints',
        'evidence_expectations': 'design artifact + rationale + risk register',
        'tool_policy': {'allow': ['read', 'browser', 'external_api'],
                        'deny': ['write', 'install', 'shell', 'run_tests', 'git']},
        'budget': 20,
        'authority_max': 'read-only',
        'capability_requirements': ['long_context', 'structured_output'],
        'dispatch_tier': 'deep',
        'budget_class': 'deep',
        'default_skill_packs': ['design-docs', 'architecture-notes', 'risk-register'],
        'independence': {'may_not_review_own': True, 'reviewer_family': 'any_but_executor'},
        'anti_patterns': ['speculative abstraction', 'designing for imagined futures',
                          'ignoring the reuse ladder']}),
    ('designer', 'Designer', 'Product', {
        'goal': 'User-facing quality: journey, visual system, interaction honesty.',
        'inputs': 'requirements, product context, design system',
        'outputs': 'UX spec, visual directions, prototype, accessibility notes',
        'quality_bar': 'states covered (empty/loading/error); a11y baseline; taste rationale recorded',
        'boundaries': 'design artifacts; may not alter requirements silently',
        'escalation': 'taste pivots not covered by recorded principles',
        'evidence_expectations': 'design artifacts + before/after captures where applicable',
        'tool_policy': {'allow': ['read', 'browser'],
                        'deny': ['write', 'install', 'shell', 'run_tests', 'git', 'external_api']},
        'budget': 16,
        'authority_max': 'read-only',
        'capability_requirements': ['vision', 'structured_output'],
        'dispatch_tier': 'standard',
        'budget_class': 'standard',
        'default_skill_packs': ['ux-research', 'visual-design', 'accessibility', 'prototyping'],
        'independence': {'may_not_review_own': True, 'reviewer_family': 'any_but_executor'},
        'anti_patterns': ['decoration without function', 'ignoring the existing design system']}),
    ('builder', 'Builder', 'Engineering', {
        'goal': 'Produce the artifact to spec, with tests.',
        'inputs': 'contract, frame, design, leases',
        'outputs': 'code/docs/data + tests + completion packet',
        'quality_bar': 'acceptance criteria met; no scope creep; repairs preserve accepted work',
        'boundaries': 'leased write scope only; no external effects; no spawning beyond policy',
        'escalation': 'blockers; contract defects; predicted budget exhaustion',
        'evidence_expectations': 'diffs/commits + command-bound test runs + artifact digests',
        'tool_policy': {'allow': ['read', 'write', 'run_tests', 'install', 'git'],
                        'deny': ['shell', 'browser', 'external_api']},
        'budget': 26,
        'authority_max': 'leased-write',
        'capability_requirements': ['repository_edit', 'code_execution', 'tool_calling'],
        'dispatch_tier': 'standard',
        'budget_class': 'standard',
        'default_skill_packs': ['language-framework', 'testing', 'migrations', 'ci'],
        'independence': {'may_not_review_own': True, 'reviewer_family': 'any_but_executor'},
        'anti_patterns': ['gold-plating beyond spec', 'touching files outside the lease',
                          'silent interface changes']}),
    ('verifier', 'Verifier', 'Verification', {
        'goal': 'Independently establish acceptance or failure - never rubber-stamp.',
        'inputs': 'source request, contract, artifact text/digests, rubric',
        'outputs': 'verification findings, claim coverage, verdicts (VERIFIED/FAILED/UNCERTAIN), regression checks',
        'quality_bar': 'artifact-first (never creator narrative); executor can never be reviewer; missing coverage is false, never clean',
        'boundaries': 'no product writes; may add checks, not edit artifacts',
        'escalation': 'UNCERTAIN beyond threshold; contested findings',
        'evidence_expectations': 'check outputs + reviewer records',
        'tool_policy': {'allow': ['read', 'run_tests'],
                        'deny': ['write', 'install', 'shell', 'git', 'browser', 'external_api']},
        'budget': 18,
        'authority_max': 'read-only',
        'capability_requirements': ['long_context', 'structured_output'],
        'dispatch_tier': 'assurance',
        'budget_class': 'deep',
        'default_skill_packs': ['verification', 'test-quality'],
        'independence': {'may_not_review_own': True, 'reviewer_family': 'different_family_if_available'},
        'anti_patterns': ['reviewing style instead of requirements',
                          'flagging only correctness/requirement gaps, not nitpicks']}),
    ('sentinel', 'Sentinel', 'Verification', {
        'goal': 'Bound security, privacy and risk; block what must be blocked.',
        'inputs': 'change surface, threat context, boundary map',
        'outputs': 'findings with attacker/boundary/impact, required mitigations, verdicts',
        'quality_bar': 'honest proof labels (static vs runtime-tested vs reserved tested); untrusted content treated as evidence only',
        'boundaries': 'cannot be overruled by schedule pressure; only by the user explicitly',
        'escalation': 'any critical finding; boundary changes; suspicious artifacts',
        'evidence_expectations': 'scanner reports + reasoning trail (no raw chain-of-thought)',
        'tool_policy': {'allow': ['read', 'external_api', 'run_tests'],
                        'deny': ['write', 'install', 'shell', 'git', 'browser']},
        'budget': 18,
        'authority_max': 'read-only',
        'capability_requirements': ['code_execution', 'structured_output'],
        'dispatch_tier': 'assurance',
        'budget_class': 'high-assurance',
        'default_skill_packs': ['threat-modeling', 'secure-code', 'audit'],
        'independence': {'may_not_review_own': True, 'reviewer_family': 'different_family_if_available'},
        'anti_patterns': ['security theater', 'blocking on unevidenced hypotheticals',
                          'shipping with unresolved criticals']}),
    ('release', 'Release', 'Delivery', {
        'goal': 'Ship safely, verify in production, own rollback.',
        'inputs': 'verified artifacts, release plan, gates',
        'outputs': 'release record, deploy evidence, health checks, rollback plan',
        'quality_bar': 'fresh command-bound evidence; canary/post-release check before done; frozen artifacts untouched',
        'boundaries': 'deployment tooling per project grants; never self-certifies the final product decision alone',
        'escalation': 'any deploy anomaly; freeze violations',
        'evidence_expectations': 'release manifest + hashes + health results',
        'tool_policy': {'allow': ['read', 'run_tests', 'git', 'shell', 'external_api'],
                        'deny': ['write', 'install', 'browser']},
        'budget': 18,
        'authority_max': 'external-effect',
        'capability_requirements': ['tool_calling', 'structured_output'],
        'dispatch_tier': 'standard',
        'budget_class': 'deep',
        'default_skill_packs': ['release', 'rollback', 'monitoring'],
        'independence': {'may_not_review_own': True, 'reviewer_family': 'any_but_executor'},
        'anti_patterns': ['declaring success from CI green alone', 'skipping rollback planning']}),
)


def ensure_archetypes(store, author='kel'):
    """Seed the 7 spawnable archetypes as role templates (idempotent, append-only)."""
    team = Team(store)
    created = []
    for template_id, name, department, fields in ARCHETYPES:
        validate_role_fields_v2(fields)
        try:
            team.define_role(template_id, name, department, fields, author=author)
            created.append(template_id)
        except PolicyError:
            continue  # already present; seeding is idempotent
    return created


def registry_ceilings(store, project_id='', task_id=''):
    """Authority ceilings declared by the seeded archetype registry.

    Resolved through `Team.resolve_role` for the given project/task so overrides are honored
    (N7, audit increment 11); with the default empty scope this equals the global latest
    versions.
    """
    team = Team(store)
    out = {}
    for template_id, _name, _department, _fields in ARCHETYPES:
        try:
            fields = team.resolve_role(template_id, project_id, task_id)['fields']
        except PolicyError:
            continue
        if fields.get('authority_max') in AUTHORITY_CLASSES:
            out[template_id] = fields['authority_max']
    return out


# ---- candidates, runtimes, overlays --------------------------------------------------------

def provider_runtime(provider):
    """The runtime binding implied by the provider registry class."""
    try:
        from .providers import definition
        klass = definition(provider).get('class', '')
    except PolicyError:
        return 'unknown'
    return {'native-cli': 'native-cli', 'api': 'internal'}.get(klass, klass or 'unknown')


def candidates_from_providers(store):
    """Runtime candidates from the provider registry; cost/quality stay unknown here.

    Privacy stays 'cloud' for registry providers (mirrors the engine's live semantics), so
    `local_only` requirements fail closed against these candidates until a local provider
    exists (S5, audit 11 — intentional).
    """
    from .providers import Providers
    out = []
    for status in Providers(store).all_status():
        out.append(Candidate(name=status['provider'],
                             capabilities=set(status['capabilities']),
                             installed=status['installed'],
                             authenticated=status['authenticated'],
                             quota=status.get('quota'),
                             circuit_until=float(status.get('circuit_until') or 0),
                             quality=None, cost=None, latency=None, privacy='cloud'))
    return out


def _model_ids(provider, caps):
    """Model ids of a provider declaring every required capability token (may be empty)."""
    try:
        from .providers import models
        return [m['id'] for m in models(provider)
                if set(caps).issubset(set(m['capabilities']))]
    except PolicyError:
        return []


def model_for(provider, caps):
    """First model of a provider declaring every required capability token, or None."""
    ids = _model_ids(provider, caps)
    return ids[0] if ids else None


def overlay_for(provider, model=None, *, registry=None):
    """The subordinate behavior overlay for a binding, or None (graceful no-op).

    Lookup order: exact 'provider:model', then family fallback 'provider:*'. Overlays never
    override role instructions, gates or safety rules; they are recorded with the routing
    decision so an overlay change mid-mission is visible.
    """
    table = OVERLAYS if registry is None else registry
    for key in ('%s:%s' % (provider, model), '%s:*' % provider):
        if key in table:
            entry = dict(table[key])
            entry['key'] = key
            return entry
    return None


# ---- binding resolution --------------------------------------------------------------------

def resolve_binding(candidates, *, mode='AUTO', requirements=(), preferred=None, fixed=None,
                    local_only=None, quality_floor=None, runtimes=None):
    """Resolve one worker binding: role requirement profile -> (provider, model, runtime).

    AUTO uses the existing deterministic eligibility + cost policy (`router.select`).
    PREFERRED tries the caller's ordered candidates first and refuses if none of them is
    eligible (it never silently switches to an unpinned provider). FIXED validates the
    pinned binding and never substitutes. Requirements whose provider capability tokens
    exist are hard filters; advisory requirements are recorded; a requirement no provider
    declares fails closed with readable exclusion reasons.
    """
    if mode not in ROUTING_MODES:
        raise PolicyError('Routing mode is one of %s' % ', '.join(ROUTING_MODES))
    if mode == 'AUTO' and (preferred or fixed):
        raise PolicyError('AUTO takes no preferred or fixed binding')
    if mode == 'PREFERRED':
        if not preferred:
            raise PolicyError('PREFERRED needs an ordered candidate list')
        if fixed:
            raise PolicyError('PREFERRED takes no fixed binding')
    if mode == 'FIXED':
        if not fixed:
            raise PolicyError('FIXED needs a pinned provider (and optional model)')
        if preferred:
            raise PolicyError('FIXED takes no preferred list')
    requirements = tuple(requirements)
    unknown = [req for req in requirements if req not in REQUIREMENTS]
    if unknown:
        raise PolicyError('Unknown requirement(s): %s' % ', '.join(unknown))
    caps, advisory = set(), []
    privacy_enforced = 'local_only' in requirements
    for req in requirements:
        if req == 'local_only':
            continue  # enforced through the privacy filter (recorded under privacy_enforced)
        tokens = REQUIREMENT_CAPABILITIES[req]
        if tokens:
            caps.update(tokens)
        else:
            advisory.append(req)
    enforced = [req for req in requirements
                if req != 'local_only' and REQUIREMENT_CAPABILITIES[req]]
    if local_only is None:
        local_only = privacy_enforced
    elif local_only is False and privacy_enforced:
        raise PolicyError('local_only is a requirement here; it cannot be overridden off')
    required = set(caps) | {'text'}
    runtimes = runtimes or {}

    def runtime_of(name):
        return runtimes.get(name) or provider_runtime(name)

    if mode == 'AUTO':
        result = select(candidates, required=required, local_only=local_only,
                        quality_floor=quality_floor)
        order = [result['selected']] + result['fallbacks']
        chosen = order[0]
        note = 'Cheapest sufficient eligible binding under the deterministic policy'
    elif mode == 'PREFERRED':
        result = select(candidates, required=required, local_only=local_only,
                        quality_floor=quality_floor)
        eligible = [result['selected']] + result['fallbacks']
        ranked = [name for name in preferred if name in eligible]
        if not ranked:
            raise PolicyError('No preferred candidate is eligible; excluded: %s'
                              % result['excluded'])
        order = ranked + [name for name in eligible if name not in ranked]
        chosen = order[0]
        note = ('Preferred order honored' if chosen == preferred[0]
                else 'First preferred entry is not eligible; next preferred entry used')
    else:  # FIXED
        name = fixed.get('provider')
        pinned = [c for c in candidates if c.name == name]
        if not pinned:
            raise PolicyError('Fixed provider is not among the candidates: %s' % name)
        try:
            select(pinned, required=required, local_only=local_only, quality_floor=quality_floor)
        except PolicyError as exc:
            raise PolicyError('Fixed binding is not eligible: %s' % exc)
        pinned_model = fixed.get('model')
        if pinned_model is not None and caps:
            allowed = _model_ids(name, caps)
            if not allowed:
                raise PolicyError('Provider %s has no model declaring the required capabilities: %s'
                                  % (name, ', '.join(sorted(caps))))
            if pinned_model not in allowed:
                raise PolicyError(
                    'Fixed model %s does not declare the required capabilities' % pinned_model)
        result = select(candidates, required=required, local_only=local_only,
                        quality_floor=quality_floor)
        order = [name] + [n for n in ([result['selected']] + result['fallbacks']) if n != name]
        chosen = name
        note = 'Pinned binding validated for eligibility; no substitution performed'

    selected = {'provider': chosen,
                'model': (fixed.get('model') if mode == 'FIXED' and fixed.get('model')
                          else model_for(chosen, caps)),
                'runtime': runtime_of(chosen)}
    if not selected['model'] and caps:
        raise PolicyError('No model of %s declares the required capabilities: %s'
                          % (chosen, ', '.join(sorted(caps))))
    fallbacks = [{'provider': n, 'model': model_for(n, caps), 'runtime': runtime_of(n)}
                 for n in order[1:]]
    if caps:
        # Sug1 (audit 11): an enforced requirement set means a reroute target must have a
        # model we can verify; entries without one are not usable as fallbacks.
        fallbacks = [item for item in fallbacks if item['model']]
    return {
        'mode': mode,
        'selected': selected,
        'fallbacks': fallbacks,
        'fallback_basis': {'AUTO': 'eligible-cost-order',
                           'PREFERRED': 'preferred-order-then-cost',
                           'FIXED': 'eligible-cost-order-excluding-pin'}[mode],
        'excluded': dict(result['excluded']),
        'requirements': {'enforced': enforced, 'advisory': advisory,
                         'capabilities': sorted(caps),
                         'privacy_enforced': ['local_only'] if privacy_enforced else []},
        'local_only': bool(local_only),
        'policy': {'AUTO': 'eligible-cost-v1', 'PREFERRED': 'preferred-order-v1',
                   'FIXED': 'fixed-pin-v1'}[mode],
        'note': note,
        'overlay': overlay_for(selected['provider'], selected['model']),
    }


# ---- capability grants ---------------------------------------------------------------------

def grants_for(authority_max, tool_policy):
    """The tool grants implied by an authority ceiling, with every denial named."""
    if authority_max not in AUTHORITY_CLASSES:
        raise PolicyError('Unknown authority class: %s' % authority_max)
    ceiling = AUTHORITY_RANK[authority_max]
    policy = tool_policy or {}
    allowed, denied = [], {}
    for tool in policy.get('allow', ()):
        needed = TOOL_AUTHORITY.get(tool)
        if needed is None:
            denied[tool] = 'no authority mapping for this tool'
        elif AUTHORITY_RANK[needed] > ceiling:
            denied[tool] = '%s needs %s authority (ceiling %s)' % (tool, needed, authority_max)
        else:
            allowed.append(tool)
    return {'allowed': sorted(allowed), 'denied': denied, 'authority_max': authority_max}


def require_grants(authority_max, tool_policy):
    """Fail closed: a worker may never hold a tool outside its authority ceiling."""
    grants = grants_for(authority_max, tool_policy)
    if grants['denied']:
        raise PolicyError('Capability grants denied: %s'
                          % '; '.join('%s (%s)' % (tool, why)
                                      for tool, why in sorted(grants['denied'].items())))
    return grants


# ---- budget reservations (doc 10 section 5) ------------------------------------------------

def ensure_schema(store):
    """Create the budget-reservation table (additive and idempotent; no data touched)."""
    with contextlib.closing(store.connect()) as db:
        db.executescript(DDL)
        if not db.execute('SELECT 1 FROM schema_migrations WHERE version=?',
                          (MIGRATION_VERSION,)).fetchone():
            db.execute('INSERT INTO schema_migrations(version,name,applied,note) VALUES(?,?,?,?)',
                       (MIGRATION_VERSION, MIGRATION_NAME, time.time(),
                        'workforce budget reservations (doc 10 section 5)'))
    return True


def reserve_budget(store, job_id, *, budget_class, tokens, wallclock, cost, milestone_id=None,
                   note=None, now=None):
    """Reserve estimated budget before a worker may start (never spawn without reserve)."""
    try:
        store.get(job_id)
    except KeyError:
        raise PolicyError('Unknown job for a budget reservation: %s' % job_id)
    class_ids = tuple(item['id'] for item in BUDGET_CLASSES)
    if budget_class not in class_ids:
        raise PolicyError('Budget class is one of %s' % ', '.join(class_ids))
    if type(tokens) is not int or tokens < 1:
        raise PolicyError('Reserved tokens must be a positive integer')
    if type(wallclock) is not int or wallclock < 1:
        raise PolicyError('Reserved wallclock must be a positive integer')
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or cost < 0:
        raise PolicyError('Reserved cost must be a non-negative number')
    stamp = time.time() if now is None else now
    reservation = {'reservation_id': uid(), 'job_id': job_id, 'milestone_id': milestone_id,
                   'assignment_id': None, 'budget_class': budget_class, 'tokens': tokens,
                   'wallclock': wallclock, 'cost': float(cost), 'state': 'reserved',
                   'note': note, 'created': stamp, 'updated': stamp}
    with contextlib.closing(store.connect()) as db:
        db.execute('INSERT INTO budget_reservations VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                   (reservation['reservation_id'], job_id, milestone_id, None, budget_class,
                    tokens, wallclock, float(cost), 'reserved', note, stamp, stamp))
    return reservation


def get_reservation(store, reservation_id):
    with contextlib.closing(store.connect()) as db:
        row = db.execute('SELECT * FROM budget_reservations WHERE reservation_id=?',
                         (reservation_id,)).fetchone()
    if row is None:
        raise PolicyError('Unknown budget reservation: %s' % reservation_id)
    return dict(row)


def link_reservation(store, reservation_id, assignment_id):
    row = get_reservation(store, reservation_id)
    if row['state'] != 'reserved':
        raise PolicyError('Reservation is already %s' % row['state'])
    if row['assignment_id'] is not None:
        raise PolicyError('Reservation is already linked to %s' % row['assignment_id'])
    with contextlib.closing(store.connect()) as db:
        # Conditional update (Sug2, audit 11): a second concurrent link cannot re-point it.
        cursor = db.execute('UPDATE budget_reservations SET assignment_id=?, updated=?'
                            ' WHERE reservation_id=? AND assignment_id IS NULL',
                            (assignment_id, time.time(), reservation_id))
        if cursor.rowcount != 1:
            raise PolicyError('Reservation was linked concurrently; refusing to re-point it')
    return get_reservation(store, reservation_id)


def release_budget(store, reservation_id, *, consumed=False, now=None):
    """Close a reservation: 'consumed' when the estimate was used, 'released' otherwise."""
    row = get_reservation(store, reservation_id)
    if row['state'] != 'reserved':
        raise PolicyError('Reservation is already %s' % row['state'])
    state = 'consumed' if consumed else 'released'
    with contextlib.closing(store.connect()) as db:
        db.execute('UPDATE budget_reservations SET state=?, updated=? WHERE reservation_id=?',
                   (state, time.time() if now is None else now, reservation_id))
    return get_reservation(store, reservation_id)


def reservations(store, *, job_id=None, state=None):
    if state is not None and state not in RESERVATION_STATES:
        raise PolicyError('Reservation states are %s' % ', '.join(RESERVATION_STATES))
    query = 'SELECT * FROM budget_reservations'
    clauses, args = [], []
    if job_id:
        clauses.append('job_id=?')
        args.append(job_id)
    if state:
        clauses.append('state=?')
        args.append(state)
    if clauses:
        query += ' WHERE ' + ' AND '.join(clauses)
    query += ' ORDER BY created'
    with contextlib.closing(store.connect()) as db:
        return [dict(row) for row in db.execute(query, tuple(args))]


# ---- the assignment path -------------------------------------------------------------------

def assign_worker(store, job_id, milestone_id, template_id, *, mode='AUTO', preferred=None,
                  fixed=None, project_id='', task_id='', candidates=None, runtimes=None,
                  reservation=None, run_id=None):
    """Resolve one worker role to a frozen binding and record the assignment.

    This is the Phase 5.1 registry/demo path; no live flow calls it yet (D1 wiring arrives
    with 5.2). The assignment snapshot freezes the mode, binding, grants, requirements,
    budget class and reservation reference; later role edits and re-resolutions never
    rewrite a recorded assignment.
    """
    team = Team(store)
    resolved = team.resolve_role(template_id, project_id, task_id)
    fields = resolved['fields']
    validate_role_fields_v2(fields)
    grants = require_grants(fields['authority_max'], fields.get('tool_policy'))
    if candidates is None:
        candidates = candidates_from_providers(store)
    binding = resolve_binding(candidates, mode=mode,
                              requirements=fields['capability_requirements'],
                              preferred=preferred, fixed=fixed, runtimes=runtimes)
    reservation_row = None
    if reservation is not None:
        reservation_row = get_reservation(store, reservation)
        if reservation_row['job_id'] != job_id:
            raise PolicyError('Reservation belongs to a different job')
        if reservation_row['milestone_id'] and reservation_row['milestone_id'] != milestone_id:
            raise PolicyError('Reservation belongs to a different milestone')
        if reservation_row['state'] != 'reserved':
            raise PolicyError('Reservation is already %s' % reservation_row['state'])
    extra = {'workforce': {
        'mode': binding['mode'], 'binding': binding, 'grants': grants,
        'budget_class': fields['budget_class'], 'dispatch_tier': fields['dispatch_tier'],
        'role_authority_max': fields['authority_max'],
        'reservation_id': reservation_row['reservation_id'] if reservation_row else None,
        'flags': flags_snapshot()}}
    created = team.create_assignment(job_id, milestone_id, template_id, project_id=project_id,
                                     task_id=task_id, run_id=run_id,
                                     provider=binding['selected']['provider'],
                                     model=binding['selected']['model'], extra=extra)
    if reservation_row is not None:
        try:
            link_reservation(store, reservation_row['reservation_id'], created['assignment_id'])
        except PolicyError as exc:
            raise PolicyError('Assignment %s was created, but its reservation %s could not be '
                              'linked (%s); release or repair the reservation explicitly'
                              % (created['assignment_id'], reservation_row['reservation_id'],
                                 exc))
    return {'assignment_id': created['assignment_id'], 'binding': binding, 'grants': grants,
            'reservation': reservation_row}
