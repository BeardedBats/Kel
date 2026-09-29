"""The Verifier's lens review in a staffed pod (D-66, tiers D2 and up).

Design: `docs/v2/design/D-66_WORKFORCE_LIVE.md` §3; workforce-os doc 08 (lens catalog, finding
schema, "never a clean pass over open blockers"). The engine's existing reviewer runs the review;
this module only adds the lenses to its prompt and records what it found in the assurance ledger:

- findings land through `assurance.record_finding` (mission = job, task = `pod:<job>:<step>`,
  artifact = the reviewed digest), deduplicated by fingerprint;
- a VERIFIED verdict over a live blocker/critical finding is recorded as FAILED, so the Builder gets
  the step back with the findings (the engine's own repair loop);
- findings on a superseded artifact are closed `fixed` against the re-review's evidence row.
"""
import contextlib
import json

from .core import PolicyError, digest

SERIOUS = ('blocker', 'critical')
TASK_PREFIX = 'pod:'


def lenses_for(job, milestone_id=None):
    """The lenses the Verifier reviews one step through. D-88: a Writer's step is always read through
    the editorial lens and an Animator's through the motion lens, whenever the Verifier reviews it;
    other steps keep the pod's lenses (none below D2)."""
    from .staff import staffing_of
    record = staffing_of(job)
    review = (record or {}).get('review') or {}
    step = (review.get('step_lenses') or {}).get(milestone_id) if milestone_id else None
    if step:
        return [lens for lens in step if isinstance(lens, str)]
    if review.get('mode') != 'pod':
        return []
    return [lens for lens in review.get('lenses') or [] if isinstance(lens, str)]


def lens_prompt(lenses):
    from .assurance import lens as describe
    lines = []
    for name in lenses:
        try:
            lines.append('- %s: %s' % (name, describe(name)['reviews']))
        except PolicyError:
            continue
    prompt = ('\nThis is a pod review: check the work through each of these lenses.\n' + '\n'.join(lines) +
              '\nReturn every finding as an object instead of a string: {"lens":"<one of: %s>",'
              '"severity":"blocker|critical|info","summary":"<one sentence>","where":"<file or section, '
              'or null>"}. A blocker or critical finding means the work must not pass as it is.'
              % ', '.join(lenses))
    from .packs import lens_brief
    for name in lenses:
        prompt += lens_brief(name)
    return prompt


def task_id(job_id, milestone_id):
    return '%s%s:%s' % (TASK_PREFIX, job_id, milestone_id)


def _normalise(item, lenses):
    if isinstance(item, str):
        text = item.strip()
        return {'lens': lenses[0], 'severity': 'info', 'summary': text, 'where': None} if text else None
    if not isinstance(item, dict) or not str(item.get('summary') or '').strip():
        return None
    lens = item.get('lens') if item.get('lens') in lenses else lenses[0]
    severity = item.get('severity') if item.get('severity') in ('blocker', 'critical', 'info') else 'info'
    where = item.get('where')
    return {'lens': lens, 'severity': severity, 'summary': ' '.join(str(item['summary']).split())[:400],
            'where': str(where)[:200] if where else None}


def record(store, job, milestone_id, review_id, reviewer_provider, lenses, verdict, findings):
    """Record the pod's findings; return the (verdict, findings as sentences) the review keeps."""
    from . import assurance
    from .evidence import write_evidence
    from .role_models import family_of_adapter
    subject = job['milestones'][milestone_id]['artifact']['sha256']
    task = task_id(job['id'], milestone_id)
    items = [entry for entry in (_normalise(item, lenses) for item in (findings or [])) if entry]
    # A newer version under review retires what was found on the older one (re-reviewed now).
    stale = [row for row in assurance.findings(store, task_id=task)
             if row['status'] in assurance.LIVE_STATUSES and row.get('artifact') != subject]
    if stale:
        evidence = write_evidence(store, mission_id=job['id'], task_id=task, evidence_class='review_record',
                                  label='re-review of a newer version', produced_by=review_id,
                                  artifact_digest='sha256:' + subject,
                                  output='re-reviewed %s after findings on an earlier version' % subject)
        for row in stale:
            try:
                assurance.resolve_finding(store, row['id'], resolution='fixed', evidence_ref=evidence['id'])
            except PolicyError:
                pass  # already resolved elsewhere
    family = family_of_adapter(reviewer_provider) or 'unknown'
    with contextlib.closing(store.connect()) as db:
        seen = {(row['fingerprint'], row['lens']) for row in db.execute(
            'SELECT fingerprint, lens FROM findings WHERE task_id=?', (task,))}
    for item in items:
        fingerprint = '%s:%s:%s' % (subject[:16], item['lens'], digest(item['summary'])[:16])
        if (fingerprint, item['lens']) in seen:
            continue
        try:
            assurance.record_finding(store, {
                'schema_version': 1, 'mission_id': job['id'], 'task_id': task, 'lens': item['lens'],
                'severity': item['severity'], 'confidence': 7, 'artifact': subject,
                'location': item['where'], 'summary': item['summary'],
                'evidence': 'independent review %s' % review_id, 'fingerprint': fingerprint,
                'status': 'open', 'by': {'lens': item['lens'], 'model_family': family,
                                         'assignment': review_id}})
            seen.add((fingerprint, item['lens']))
        except PolicyError:
            continue  # a finding the ledger refuses (duplicate, unsafe text) is not recorded twice
    serious = [item for item in items if item['severity'] in SERIOUS]
    sentences = ['%s (%s): %s' % (item['severity'], item['lens'], item['summary']) for item in items]
    if verdict == 'VERIFIED' and serious:
        verdict = 'FAILED'
        sentences.append('Kel held this back: the review found %d blocking problem%s.'
                         % (len(serious), '' if len(serious) == 1 else 's'))
    if not sentences:
        sentences = ['No findings.']
    return verdict, sentences


def live_serious(store, job, milestone_id=None):
    """Live blocker/critical pod findings on the current artifact of a step (or of every step)."""
    from .assurance import LIVE_STATUSES, findings
    from .staff import staffing_of
    out = []
    if not staffing_of(job):
        return out  # only a staffed pod records lens findings
    with contextlib.closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='findings'").fetchone():
            return out
    for mid, milestone in (job.get('milestones') or {}).items():
        if milestone_id and mid != milestone_id:
            continue
        subject = (milestone.get('artifact') or {}).get('sha256')
        for row in findings(store, task_id=task_id(job['id'], mid)):
            if row['status'] in LIVE_STATUSES and row['severity'] in SERIOUS and row.get('artifact') == subject:
                out.append(row)
    return out
