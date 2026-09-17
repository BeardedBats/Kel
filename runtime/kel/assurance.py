"""Assurance lenses and review findings (Phase 5.0): the fixed lens catalog.

Design: `ux-audit/workforce-os/08_ASSURANCE_ARMY.md`. Fifteen constitution-level lenses
with deterministic gating classes; security, privacy, data-integrity, release-integrity
and the Oracle are never-gate insurance and are never learned away. Lens names are stable
identifiers (doc-08 spellings; `visual-design` stores the catalog's conservative `info`
floor — escalations are handled downstream). Dispatch, dedupe, confirmation and score
machinery arrives with the assurance increments; this module owns the catalog and the v1
finding schema.
"""
import contextlib
import json
import time

from .core import PolicyError, uid
from .evidence import write_evidence
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


def record_finding(store, finding, *, now=None):
    """Persist one review finding with doc-08 dedup + multi-lens confirmation (v1).

    Same fingerprint + same lens is refused as a duplicate (nothing silently dropped); the
    same fingerprint from a different lens upgrades the existing row (confirmations +
    confidence cap 10, tagged `confirmed_by_multi`).
    """
    finding = dict(finding)
    finding.setdefault('id', 'find_' + uid())
    stamp = time.time() if now is None else now
    finding.setdefault('created', stamp)
    finding['updated'] = stamp
    validate_finding(finding)
    with contextlib.closing(store.connect()) as db:
        existing = db.execute('SELECT * FROM findings WHERE fingerprint=?',
                              (finding['fingerprint'],)).fetchone()
        if existing is not None:
            record = dict(existing)
            if record['lens'] == finding['lens']:
                raise PolicyError('Duplicate finding rejected (same fingerprint and lens: %s)'
                                  % record['id'])
            confirmations = json.loads(record['confirmations'] or '[]')
            if finding['lens'] not in confirmations:
                confirmations.append(finding['lens'])
            confidence = max(int(record['confidence']), int(finding['confidence']))
            if confidence < 10:
                confidence += 1  # multi-specialist confirmed (doc 08 §5), capped at 10
            db.execute('UPDATE findings SET confirmations=?, confidence=?, updated=?, status=?'
                       ' WHERE id=?',
                       (json.dumps(confirmations), confidence, stamp, 'confirmed',
                        record['id']))
            updated = dict(db.execute('SELECT * FROM findings WHERE id=?',
                                      (record['id'],)).fetchone())
            updated['confirmed_by_multi'] = True
            return updated
        db.execute('INSERT INTO findings(id,schema_version,mission_id,task_id,lens,severity,'
                   'confidence,artifact,location,summary,evidence,fix,fingerprint,status,'
                   'advisory,reporter,confirmations,dismissal_reason,created,updated) '
                   'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (finding['id'], finding['schema_version'], finding['mission_id'],
                    finding['task_id'], finding['lens'], finding['severity'],
                    finding['confidence'], finding.get('artifact'), finding.get('location'),
                    finding['summary'], finding.get('evidence'), finding.get('fix'),
                    finding['fingerprint'], finding['status'],
                    1 if finding.get('advisory') else 0,
                    json.dumps(finding['by']), json.dumps(finding.get('confirmations') or []),
                    finding.get('dismissal_reason'), finding['created'], finding['updated']))
    return finding


def resolve_finding(store, finding_id, *, resolution, rationale=None, evidence_ref=None,
                    authority=None, now=None):
    """Arbitration ladder v1 (doc 07 §7 / doc 08 §5): a lower rung never overrides a higher
    one without new evidence.

    - `fixed`: requires a recorded evidence row; status `fixed`. This is remediation, not
      acceptance, so it stays available to Kel — bound to recorded evidence.
    - `accepted`: risk-accepted; requires rationale; blockers additionally need evidence.
    - `dismissed`: false positive; requires rationale; blockers additionally need evidence.

    Constitutional constant (doc 09 §10, doc 08 §6): a never-gate finding — security, privacy,
    data-integrity, release-integrity, adversarial — can only be **accepted or dismissed by the
    user**. `authority='kel'`, and the default `None` (Kel acting), is refused for those lenses,
    so `waive_gate` is not the only guarded door out of `open`.
    """
    if resolution not in ('fixed', 'accepted', 'dismissed'):
        raise PolicyError('Resolutions are fixed, accepted or dismissed')
    if authority is not None and authority not in ('user', 'kel'):
        raise PolicyError('Authority is user or kel')
    stamp = time.time() if now is None else now
    with contextlib.closing(store.connect()) as db:
        row = db.execute('SELECT * FROM findings WHERE id=?', (finding_id,)).fetchone()
        if row is None:
            raise PolicyError('Unknown finding: %s' % finding_id)
        record = dict(row)
        if record['status'] in ('fixed', 'dismissed'):
            raise PolicyError('Finding is already %s' % record['status'])
        if resolution != 'fixed' and record['lens'] in NEVER_GATE and authority != 'user':
            raise PolicyError('Never-gate findings (%s) can only be accepted by the user '
                              '(doc 09 §10); %s resolution of %s by %s authority is refused'
                              % (record['lens'], resolution, finding_id,
                                 authority or 'kel (default)'))

        def _require_recorded_evidence(what):
            require_text(evidence_ref, 'evidence_ref (%s needs recorded evidence)' % what)
            if db.execute('SELECT 1 FROM evidence_records WHERE id=?',
                          (evidence_ref,)).fetchone() is None:
                raise PolicyError('Evidence %s is not in the ledger' % evidence_ref)

        if resolution == 'fixed':
            _require_recorded_evidence('a fix')
            status, reason = 'fixed', None
        elif resolution == 'accepted':
            require_text(rationale, 'rationale (risk acceptance is recorded)')
            if record['severity'] == 'blocker':
                _require_recorded_evidence('accepting a blocker')
            status, reason = 'dismissed', 'risk-accepted: %s' % rationale
        else:
            require_text(rationale, 'rationale (dismissals are recorded)')
            if record['severity'] == 'blocker':
                _require_recorded_evidence('dismissing a blocker')
            status, reason = 'dismissed', rationale
        db.execute('UPDATE findings SET status=?, dismissal_reason=?, updated=? WHERE id=?',
                   (status, reason, stamp, finding_id))
        updated = dict(db.execute('SELECT * FROM findings WHERE id=?',
                                  (finding_id,)).fetchone())
    return updated


def findings(store, *, task_id=None, mission_id=None, status=None):
    """Read-only findings ledger (decoded reporters/confirmations)."""
    query = 'SELECT * FROM findings'
    clauses, args = [], []
    if task_id:
        clauses.append('task_id=?')
        args.append(task_id)
    if mission_id:
        clauses.append('mission_id=?')
        args.append(mission_id)
    if status:
        clauses.append('status=?')
        args.append(status)
    if clauses:
        query += ' WHERE ' + ' AND '.join(clauses)
    query += ' ORDER BY created'
    with contextlib.closing(store.connect()) as db:
        rows = [dict(row) for row in db.execute(query, tuple(args))]
    for row in rows:
        row['by'] = json.loads(row['reporter']) if row.get('reporter') else None
        row['confirmations'] = json.loads(row['confirmations'] or '[]')
        row['advisory'] = bool(row['advisory'])
    return rows


# ---- assurance army: dispatch, deterministic gating, Sentinel rules, Oracle (Phase 5.4) ----

# Deterministic scope gating (doc 08 §2-3): the tier selects the floors; mission flags trigger
# the rest; the never-gate class runs at D4. Every catalog lens not selected is returned with
# its skip reason (exit criterion: no silently skipped lens).
GATING_FLOORS = {
    'D0': (),
    'D1': ('functional-testing',),
    'D2': ('functional-testing', 'maintainability'),
    'D3': ('functional-testing', 'maintainability'),
    'D4': ('functional-testing', 'maintainability') + NEVER_GATE,
}

GATE_TRIGGERS = {
    'security_boundary': ('security', 'adversarial'),
    'privacy': ('privacy',),
    'data_migration': ('data-integrity',),
    'release': ('release-integrity',),
    'user_facing': ('ux', 'accessibility', 'visual-design'),
    'api_change': ('api-contract',),
    'performance': ('performance',),
    'journey': ('user-journey',),
    # doc 08 §2 (fail-safe): a positive signal may never dispatch nothing. Destructive /
    # irreversible change is a data-integrity concern, and that lens is never-gate (doc 08 §3).
    'irreversible': ('data-integrity',),
    'new_dependency': ('security',),
}


def lenses_for(tier, flags=()):
    """The deterministic lens set for a mission (doc 08 §2-3).

    Floors by tier + flag-triggered lenses + the never-gate class at D4; every non-selected
    catalog lens comes back with its skip reason, and unknown flags/tiers are refused.
    """
    if tier not in GATING_FLOORS:
        raise PolicyError('Gating tiers are %s' % ', '.join(GATING_FLOORS))
    selected, reasons = [], {}
    for lens_name in GATING_FLOORS[tier]:
        selected.append(lens_name)
        reasons[lens_name] = 'tier floor (%s)' % tier
    for flag in flags:
        if flag not in GATE_TRIGGERS:
            raise PolicyError('Unknown gating flag: %s' % flag)
        for lens_name in GATE_TRIGGERS[flag]:
            if lens_name not in selected:
                selected.append(lens_name)
            reasons[lens_name] = 'triggered by %s' % flag
    skipped = {}
    for item in LENSES:
        name = item['name']
        if name not in selected:
            triggers = [flag for flag, mapped in GATE_TRIGGERS.items() if name in mapped]
            skipped[name] = ('not triggered at %s (would run for: %s)'
                             % (tier, ', '.join(triggers) if triggers else 'tier floor only'))
    return {'tier': tier, 'flags': list(flags), 'lenses': selected, 'reasons': reasons,
            'skipped': skipped}


def dispatch_assurance(store, *, task_id, artifact, runner, tier, mission_id, flags=(),
                       lenses=None, now=None):
    """Run the selected lenses as fresh-context reviews of the artifact.

    `runner(lens_name, payload)` returns `{'findings': [...], 'coverage_statement': str}`;
    findings land through the standard pipeline (fingerprint dedupe + multi-lens confirmation).
    The payload carries ONLY the artifact reference, the lens name and the rubric requirement —
    never the builder's packet or claims (anti-anchoring, doc 08 §4). Sentinel rule: a
    security boundary cannot skip the security lens. `lenses` may *add* lenses (domain
    extensions) but may never drop one the tier floor or a flag mandates (doc 08 §2-3, §6).
    Every dispatched lens must state its coverage explicitly, and each accepted statement is
    written to the evidence ledger so coverage stays auditable after the call (docs 06/07).
    """
    plan = lenses_for(tier, flags)
    selected = list(lenses if lenses is not None else plan['lenses'])
    unknown = sorted(set(selected) - set(LENS_NAMES) - set(DOMAIN_LENSES))
    if unknown:
        raise PolicyError('Unknown lens(es): %s' % ', '.join(unknown))
    missing = [name for name in plan['lenses'] if name not in selected]
    if missing:
        raise PolicyError('The gating plan for tier %s + flags %s mandates %s; `lenses` may '
                          'add lenses but never drop a mandated one (doc 08 §2-3, §6)'
                          % (tier, list(flags), ', '.join(missing)))
    if 'security_boundary' in flags and 'security' not in selected:
        raise PolicyError('The security lens is mandatory for security boundaries (Sentinel); '
                          'it cannot be skipped')
    require_text(mission_id, 'mission_id (coverage statements are recorded)')
    stamp = time.time() if now is None else now
    results, records = {}, []
    for lens_name in selected:
        payload = {'lens': lens_name, 'artifact': artifact,
                   'requirement': 'review the artifact and state your coverage explicitly'}
        outcome = runner(lens_name, payload)
        coverage = outcome.get('coverage_statement')
        require_text(coverage, 'coverage statement for lens %s' % lens_name)
        recorded = write_evidence(store, mission_id=mission_id, task_id=task_id,
                                  evidence_class='review_record',
                                  label='lens coverage: %s' % lens_name,
                                  produced_by=lens_name, output=coverage, ran_at=stamp)
        lens_findings = []
        for item in outcome.get('findings', []):
            record = record_finding(store, item, now=stamp)
            lens_findings.append(record)
            records.append(record)
        results[lens_name] = {'coverage_statement': coverage,
                              'coverage_evidence': recorded['id'],
                              'findings': [item['id'] for item in lens_findings]}
    unique = {item['id']: item for item in records}
    quality = quality_score(
        criticals=sum(1 for item in unique.values()
                      if item['severity'] == 'critical' and item['status'] == 'open'),
        infos=sum(1 for item in unique.values() if item['severity'] == 'info'))
    return {'tier': tier, 'flags': list(flags), 'dispatched': selected, 'results': results,
            'findings': list(unique.values()), 'quality_score': quality, 'plan': plan}


def gate(store, *, task_id):
    """Deterministic gate over recorded findings (doc 08 §3; doc 09 §10).

    Blockers block, always; criticals block while open; findings from the never-gate class can
    never be waived by Kel — only an explicit user decision can accept them. The quality score
    is advisory only.
    """
    rows = findings(store, task_id=task_id)
    open_items = [item for item in rows if item['status'] == 'open']
    blockers = [item for item in open_items if item['severity'] == 'blocker']
    criticals = [item for item in open_items if item['severity'] == 'critical']
    never_gate_hits = [item for item in open_items if item['lens'] in NEVER_GATE]
    reasons = ['%s finding %s open (%s)' % (item['severity'], item['id'], item['lens'])
               for item in blockers + criticals]
    blocked = bool(blockers or criticals)
    return {'blocked': blocked, 'waivable': bool(blocked) and not never_gate_hits,
            'reasons': reasons,
            'never_gate_hits': [item['id'] for item in never_gate_hits],
            'quality_score': quality_score(
                criticals=len(criticals),
                infos=len([item for item in open_items if item['severity'] == 'info']))}


def waive_gate(store, *, task_id, authority, rationale, now=None):
    """Accept open blocker/critical findings (constitutional constants, doc 09 §2/§10).

    The user is the only authority that can accept never-gate findings; Kel's own waiver is
    refused when they are open. The waiver is recorded on each accepted finding.
    """
    result = gate(store, task_id=task_id)
    if not result['blocked']:
        raise PolicyError('The gate is not blocked; nothing to waive')
    require_text(rationale, 'waiver rationale')
    if authority not in ('user', 'kel'):
        raise PolicyError('Waiver authority is user or kel')
    if result['never_gate_hits'] and authority != 'user':
        raise PolicyError('Never-gate findings can only be accepted by the user '
                          '(open: %s)' % ', '.join(result['never_gate_hits']))
    stamp = time.time() if now is None else now
    with contextlib.closing(store.connect()) as db:
        db.execute('UPDATE findings SET status=?, dismissal_reason=?, updated=? WHERE task_id=? '
                   'AND status=? AND severity IN (?, ?)',
                   ('dismissed', 'gate-waived (%s): %s' % (authority, rationale), stamp,
                    task_id, 'open', 'blocker', 'critical'))
    return {'waived': True, 'authority': authority, 'task_id': task_id,
            'accepted': result['reasons']}


def oracle_check(store, *, task_id, artifact, runner, producer_provider, oracle_provider,
                mission_id, now=None, allow_same_family=False):
    """Run the adversarial (Oracle) lens under family independence (doc 08 §8).

    The oracle must be a different provider family than the producer; the same-family fallback
    is allowed only with `allow_same_family=True`, is reported in `family_diversity`, and is
    **written to the evidence ledger** so it stays visible to a later auditor. Findings land
    through the standard pipeline; the coverage statement is required (parity with dispatched
    lenses) and recorded the same way.
    """
    from .pods import family_of  # local import: pods imports this module (no load-time cycle)
    producer_family = family_of(producer_provider)
    oracle_family = family_of(oracle_provider)
    if oracle_family == producer_family and not allow_same_family:
        raise PolicyError('The Oracle must be a different model family than the producer '
                          '(got %s for both); pass allow_same_family=True to record the '
                          'fallback' % producer_family)
    require_text(mission_id, 'mission_id (review records are recorded)')
    payload = {'lens': ORACLE_LENS, 'artifact': artifact,
               'requirement': 'attack the artifact and state your coverage explicitly'}
    outcome = runner(ORACLE_LENS, payload)
    coverage = outcome.get('coverage_statement')
    require_text(coverage, 'coverage statement for the Oracle')
    stamp = time.time() if now is None else now
    fallback = None
    if oracle_family == producer_family:
        fallback = write_evidence(store, mission_id=mission_id, task_id=task_id,
                                  evidence_class='review_record',
                                  label='oracle same-family fallback',
                                  produced_by=oracle_provider,
                                  output='producer family %s == oracle family %s '
                                         '(allow_same_family=True)' % (producer_family,
                                                                       oracle_family),
                                  ran_at=stamp)['id']
    coverage_evidence = write_evidence(store, mission_id=mission_id, task_id=task_id,
                                       evidence_class='review_record',
                                       label='lens coverage: %s' % ORACLE_LENS,
                                       produced_by=oracle_provider, output=coverage,
                                       ran_at=stamp)['id']
    records = [record_finding(store, item, now=stamp) for item in outcome.get('findings', [])]
    return {'lens': ORACLE_LENS, 'coverage_statement': coverage,
            'coverage_evidence': coverage_evidence, 'findings': records,
            'family_diversity': ('different' if oracle_family != producer_family
                                 else 'unavailable (recorded fallback)'),
            'fallback_evidence': fallback,
            'oracle_provider': oracle_provider, 'producer_provider': producer_provider}


ACCEPTANCE_REASON_PREFIXES = ('risk-accepted:', 'gate-waived')


def _is_acceptance(reason):
    """True when a dismissal records accepted risk (a waiver or a risk acceptance)."""
    return bool(reason) and str(reason).startswith(ACCEPTANCE_REASON_PREFIXES)


def lens_stats(store):
    """Per-lens review statistics for the learning loop (doc 08 §9, read-only).

    A risk acceptance or a waived finding is not a reviewer false positive, and the never-gate
    insurance lenses never earn gating credit from a false-positive rate (doc 08 §3/§7): their
    `fp_rate` stays None and `learnable` is False.
    """
    stats = {}
    for item in findings(store):
        entry = stats.setdefault(item['lens'], {'total': 0, 'open': 0, 'confirmed': 0,
                                                'fixed': 0, 'dismissed': 0, 'accepted': 0,
                                                'false_positive': 0})
        entry['total'] += 1
        entry[item['status']] = entry.get(item['status'], 0) + 1
        if item['status'] == 'dismissed':
            if _is_acceptance(item.get('dismissal_reason')):
                entry['accepted'] += 1
            else:
                entry['false_positive'] += 1
    for name, entry in stats.items():
        closed = entry['fixed'] + entry['dismissed']
        entry['learnable'] = name not in NEVER_GATE
        entry['fp_rate'] = (round(entry['false_positive'] / closed, 2)
                            if closed and entry['learnable'] else None)
    return stats
