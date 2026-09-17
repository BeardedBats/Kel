"""Assurance lenses and review findings (Phase 5.0): the fixed lens catalog.

Design: `ux-audit/workforce-os/08_ASSURANCE_ARMY.md`. Fifteen constitution-level lenses
with deterministic gating classes; security, privacy, data-integrity, release-integrity
and the Oracle are never-gate insurance and are never learned away. Lens names are stable
identifiers (doc-08 spellings; `visual-design` stores the catalog's conservative `info`
floor — escalations are handled downstream). Dispatch, dedupe, confirmation and score
machinery arrives with the assurance increments; this module owns the catalog and the v1
finding schema.
"""
from .core import PolicyError
from .workforce import assert_safe, require_integer, require_number, require_text

SCHEMA_VERSION = 1

LENSES = (
    {'name': 'functional-testing', 'blocking_class': 'blocker', 'gate_class': 'standard',
     'reviews': 'Do tests exist, run, and cover the acceptance criteria? Do they fail when the defect is present?'},
    {'name': 'maintainability', 'blocking_class': 'critical', 'gate_class': 'standard',
     'reviews': 'Complexity, duplication, dead code, naming, fit with local conventions'},
    {'name': 'security', 'blocking_class': 'blocker', 'gate_class': 'never_gate',
     'reviews': 'Injection, authz/authn, secrets, unsafe deserialization, supply chain, boundary violations'},
    {'name': 'privacy', 'blocking_class': 'blocker', 'gate_class': 'never_gate',
     'reviews': 'Data exposure, telemetry content, retention, consent, local-vs-cloud boundaries'},
    {'name': 'performance', 'blocking_class': 'critical', 'gate_class': 'standard',
     'reviews': 'Hot paths, N+1s, unbounded loops, memory, startup cost; measured where possible'},
    {'name': 'data-integrity', 'blocking_class': 'blocker', 'gate_class': 'never_gate',
     'reviews': 'Schema changes, backfills, idempotency, rollback, destructive ops, orphaned state'},
    {'name': 'api-contract', 'blocking_class': 'critical', 'gate_class': 'standard',
     'reviews': 'Interface changes, versioning, backward compatibility, error contracts'},
    {'name': 'ux', 'blocking_class': 'critical', 'gate_class': 'standard',
     'reviews': 'Journey coherence, states (empty/loading/error), copy honesty, flow friction'},
    {'name': 'visual-design', 'blocking_class': 'info', 'gate_class': 'standard',
     'reviews': 'Hierarchy, typography, spacing, palette, motion restraint, design-system fit'},
    {'name': 'accessibility', 'blocking_class': 'critical', 'gate_class': 'standard',
     'reviews': 'Keyboard, focus, contrast, semantics, screen-reader paths, reduced motion'},
    {'name': 'user-journey', 'blocking_class': 'blocker', 'gate_class': 'standard',
     'reviews': 'End-to-end task realism on the delivered artifact (does the real user succeed?)'},
    {'name': 'requirements-coverage', 'blocking_class': 'blocker', 'gate_class': 'standard',
     'reviews': 'Did the artifact satisfy every acceptance claim? Missing coverage = false, never clean'},
    {'name': 'release-integrity', 'blocking_class': 'blocker', 'gate_class': 'never_gate',
     'reviews': 'Versioning, manifests, hashes, frozen artifacts untouched, rollback plan present'},
    {'name': 'adversarial', 'blocking_class': 'blocker', 'gate_class': 'never_gate',
     'reviews': 'Deliberate break attempts: lies, edge cases, escape routes; different model family (Oracle)'},
    {'name': 'simplification', 'blocking_class': 'info', 'gate_class': 'standard', 'advisory': True,
     'reviews': 'Unrequested structure, hand-rolled stdlib, one-implementation abstractions, dependencies duplicating platform features'},
)

LENS_NAMES = tuple(item['name'] for item in LENSES)
NEVER_GATE = ('security', 'privacy', 'data-integrity', 'release-integrity', 'adversarial')
ORACLE_LENS = 'adversarial'
TIER_FLOORS = {'D2': ('functional-testing', 'maintainability')}
DOMAIN_LENSES = ('documentation', 'i18n/l10n', 'licensing', 'dev-experience', 'data-quality',
                 'model-quality', 'business-rules')
SEVERITIES = ('blocker', 'critical', 'info')
FINDING_STATUSES = ('open', 'confirmed', 'dismissed', 'fixed')
CONFIDENCE_GATES = ((2, 'suppressed'), (4, 'appendix'), (6, 'caveat'), (10, 'normal'))
FINDING_FIELDS = ('id', 'schema_version', 'mission_id', 'task_id', 'lens', 'severity',
                  'confidence', 'artifact', 'location', 'summary', 'evidence', 'fix',
                  'fingerprint', 'status', 'advisory', 'by', 'confirmations',
                  'dismissal_reason', 'created', 'updated')


def lens(name):
    """The catalog entry for a lens name (fixed lenses or a project domain lens)."""
    for item in LENSES:
        if item['name'] == name:
            return item
    if name in DOMAIN_LENSES:
        return {'name': name, 'blocking_class': 'info', 'gate_class': 'standard',
                'reviews': 'Project overlay lens'}
    raise PolicyError('Unknown assurance lens: %s' % name)


def validate_finding(finding):
    """Refuse a malformed review finding (doc 08 §5, schema v1)."""
    if not isinstance(finding, dict):
        raise PolicyError('A finding is an object')
    unknown = sorted(set(finding) - set(FINDING_FIELDS))
    if unknown:
        raise PolicyError('A finding has unknown fields: %s' % ', '.join(unknown))
    if finding.get('schema_version') != SCHEMA_VERSION:
        raise PolicyError('Finding schema_version must be %d' % SCHEMA_VERSION)
    require_text(finding.get('id'), 'finding id')
    require_text(finding.get('mission_id'), 'mission_id')
    require_text(finding.get('task_id'), 'task_id')
    name = require_text(finding.get('lens'), 'lens')
    lens(name)  # refuses unknown lenses
    severity = finding.get('severity')
    if severity not in SEVERITIES:
        raise PolicyError('Finding severities are %s' % ', '.join(SEVERITIES))
    require_integer(finding.get('confidence'), 'confidence', lo=0, hi=10)
    for field in ('artifact', 'location', 'evidence'):
        if finding.get(field) is not None:
            require_text(finding[field], field)
    if finding.get('fix') is not None:
        require_text(finding['fix'], 'fix', allow_empty=True)
    require_text(finding.get('summary'), 'finding summary', max_len=400)
    require_text(finding.get('fingerprint'), 'fingerprint (the dedup key)')
    status = finding.get('status')
    if status not in FINDING_STATUSES:
        raise PolicyError('Finding statuses are %s' % ', '.join(FINDING_STATUSES))
    advisory = finding.get('advisory', False)
    if not isinstance(advisory, bool):
        raise PolicyError('advisory is a boolean')
    if advisory and severity != 'info':
        raise PolicyError('Advisory findings are info severity')
    reporter = finding.get('by')
    if not isinstance(reporter, dict):
        raise PolicyError('A finding carries its reporter (by: lens, model_family, assignment)')
    require_text(reporter.get('model_family'), 'finding by.model_family')
    require_text(reporter.get('assignment'), 'finding by.assignment')
    if reporter.get('lens') is not None:
        require_text(reporter['lens'], 'finding by.lens')
    confirmations = finding.get('confirmations', [])
    if not isinstance(confirmations, list):
        raise PolicyError('finding confirmations must be a list')
    for item in confirmations:
        require_text(item, 'finding confirmation')
    if status == 'dismissed':
        require_text(finding.get('dismissal_reason'), 'dismissal_reason (required when dismissed)')
    elif finding.get('dismissal_reason') is not None:
        require_text(finding['dismissal_reason'], 'dismissal_reason')
    if finding.get('created') is not None:
        require_number(finding['created'], 'finding created')
    if finding.get('updated') is not None:
        require_number(finding['updated'], 'finding updated')
    assert_safe(finding, path='finding')
    return finding


def quality_score(*, criticals=0, infos=0):
    """Review quality score (doc 08 §5): max(0, 10 - (critical*2 + info*0.5)).

    Advisory findings are excluded by the caller. Used for ceremony and trends only —
    never shown as a standalone user-facing judgment.
    """
    return max(0, 10 - (criticals * 2 + infos * 0.5))
