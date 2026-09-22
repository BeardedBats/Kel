"""Activity 2.0 (V2-08) — the historical timeline, read from what the engine already recorded.

One read surface over the durable `events` stream plus the jobs and conversations the line already
keeps. Every row is a plain sentence; the filters are Project, date, type and failure, plus search;
a row carries how to open its result/evidence and whether the work can be retried or recovered.

Deliberately absent: worker ids, leases, staffing graphs, cockpit controls, and any raw event payload
(a payload carries the contract and the request; the timeline quotes at most the person's own request
line for the row they started).
"""
import json
import time

from .core import PolicyError

# Event type → the person's kind. Types that are not listed here are reported as 'other' rather than
# hidden: an activity surface that quietly drops rows is worse than one that says "other".
KIND_BY_TYPE = {
    'job.created': 'work', 'job.cancel': 'work', 'job.paused': 'work', 'job.resumed': 'work',
    'run.claimed': 'work', 'worker.result_recorded': 'work', 'completion.assessed': 'work',
    'criterion.checked': 'work', 'review.recorded': 'work', 'run.fenced': 'recovery',
    'run.abandoned': 'recovery', 'run.recovered': 'recovery',
    'memory.created': 'learning', 'memory.proposed': 'learning', 'memory.superseded': 'learning',
    'memory.proposal_accepted': 'learning', 'memory.proposal_rejected': 'learning',
    'learning.suggested': 'learning', 'learning.toggled': 'learning',
    'recipe.installed': 'recipes', 'recipe.saved': 'recipes', 'recipe.ran': 'recipes',
    'connection.saved': 'connections', 'connection.removed': 'connections',
    'connection.called': 'connections', 'connection.denied': 'connections',
    'network.decided': 'network', 'network.requested': 'network',
    'staffing.decided': 'staffing', 'proposal.queued': 'staffing',
}
KINDS = ('work', 'attention', 'learning', 'recipes', 'connections', 'network', 'staffing',
         'recovery', 'other')
FAILED_VERDICTS = ('FAILED', 'UNCERTAIN')
FAILED_STATES = ('CANCELLED', 'CANCELLING', 'BLOCKED')


def _snippet(value, limit=90):
    text = ' '.join(str(value or '').split())
    return text[:limit]


def sentence_for(event_type, payload):
    """One plain sentence per event, built from a whitelist of safe fields — never the payload."""
    detail = {}
    if isinstance(payload, dict):
        detail = payload.get('detail') or {}
        if not isinstance(detail, dict):
            detail = {}
    job = (payload or {}).get('job') if isinstance(payload, dict) else None
    request = ''
    if isinstance(job, dict):
        request = _snippet((job.get('contract') or {}).get('request'))
    if event_type == 'job.created':
        return 'Work started: %s' % (request or 'a saved request')
    if event_type == 'job.cancel':
        return 'This work was stopped.'
    if event_type == 'job.paused':
        return 'This work was paused.'
    if event_type == 'job.resumed':
        return 'This work was resumed.'
    if event_type == 'run.claimed':
        provider = detail.get('provider')
        return 'Kel chose %s for this work.' % provider if provider else 'Kel chose a model.'
    if event_type == 'worker.result_recorded':
        outcome = str(detail.get('outcome') or '').lower()
        return 'A step finished%s.' % (' (%s)' % outcome if outcome else '')
    if event_type == 'completion.assessed':
        verdict = detail.get('verdict')
        return 'The result was assessed%s.' % (' — %s' % str(verdict).lower() if verdict else '')
    if event_type == 'criterion.checked':
        verdict = detail.get('verdict')
        return 'A completion check finished%s.' % (' — %s' % str(verdict).lower() if verdict else '')
    if event_type == 'review.recorded':
        verdict = detail.get('verdict')
        reviewer = detail.get('reviewer_provider')
        return 'A separate review said %s%s.' % (str(verdict or 'something').lower(),
                                                 ' (%s)' % reviewer if reviewer else '')
    if event_type == 'run.fenced':
        return 'An abandoned run was fenced; the saved work was not replayed.'
    if event_type == 'memory.created':
        return 'Kel saved a memory you confirmed.'
    if event_type == 'memory.proposed':
        return 'Kel proposed a memory for review.'
    if event_type == 'memory.superseded':
        return 'A memory was replaced by a newer one.'
    if event_type == 'memory.proposal_accepted':
        return 'You accepted a memory Kel proposed.'
    if event_type == 'memory.proposal_rejected':
        return 'You declined a memory Kel proposed.'
    if event_type.startswith('recipe.'):
        return 'A recipe %s.' % event_type.split('.', 1)[1].replace('_', ' ')
    if event_type.startswith('connection.'):
        return 'A connection was %s.' % event_type.split('.', 1)[1].replace('_', ' ')
    if event_type.startswith('network.'):
        return 'A network decision was recorded (%s).' % event_type.split('.', 1)[1]
    if event_type.startswith('staffing.'):
        return 'Kel adjusted who does the work.'
    if event_type.startswith('approval.'):
        return 'You were asked something about this work.'
    return 'Something was recorded (%s).' % event_type


def timeline(store, *, project_id=None, since=None, until=None, kind=None, failures_only=False,
             query=None, limit=200):
    """The person's own history, newest first, with the filters the directive names."""
    if kind and kind not in KINDS:
        raise PolicyError('Unknown activity type: %s' % kind)
    try:
        limit = max(1, min(int(limit or 200), 500))
    except (TypeError, ValueError):
        raise PolicyError('How many entries?') from None
    jobs = {job['id']: job for job in store.list_jobs()}
    conversations = {}
    with store.connect() as db:
        for row in db.execute('SELECT id,project_id FROM conversations'):
            conversations[row['id']] = row['project_id']
    needle = str(query or '').strip().lower()
    entries = []
    counts = {name: 0 for name in KINDS}
    projects = {}
    for event in store.events():
        event_type = str(event.get('type') or '')
        at = event.get('at') or 0
        if since and at < since:
            continue
        if until and at > until:
            continue
        row_kind = KIND_BY_TYPE.get(event_type, 'other')
        if row_kind == 'other' and event_type.startswith('approval.'):
            row_kind = 'attention'
        if kind and row_kind != kind:
            continue
        aggregate = event.get('aggregate_id') or ''
        job = jobs.get(aggregate)
        row_project = None
        if job:
            row_project = conversations.get(job.get('conversation'))
        if project_id and row_project != project_id:
            continue
        payload = event.get('payload')
        if isinstance(payload, str):
            try:
                payload = json.loads(payload or '{}')
            except (TypeError, ValueError):
                payload = {}
        what = sentence_for(event_type, payload if isinstance(payload, dict) else {})
        failed = False
        state = verdict = artifact = digest = None
        can_retry = False
        if job:
            state = job.get('state')
            verdict = job.get('verdict')
            failed = bool((verdict in FAILED_VERDICTS) or (state in FAILED_STATES))
            for milestone in (job.get('milestones') or {}).values():
                if (milestone or {}).get('artifact'):
                    artifact = milestone['artifact'].get('path')
                    digest = milestone['artifact'].get('sha256')
                    break
            can_retry = state in ('CLOSED', 'CANCELLED') or bool(job.get('error'))
        if event_type in ('completion.assessed', 'review.recorded', 'criterion.checked'):
            recorded = None
            if isinstance(payload, dict):
                recorded = (payload.get('detail') or {}).get('verdict')
            if recorded in FAILED_VERDICTS:
                failed = True
        if failures_only and not failed:
            continue
        if needle and needle not in what.lower():
            continue
        counts[row_kind] = counts.get(row_kind, 0) + 1
        if row_project:
            projects[row_project] = projects.get(row_project, 0) + 1
        entries.append({'at': at, 'kind': row_kind, 'type': event_type, 'what': what,
                        'project_id': row_project, 'job_id': aggregate if job else None,
                        'state': state, 'verdict': verdict, 'failed': failed,
                        'result': artifact, 'evidence': digest, 'can_retry': can_retry})
    entries.sort(key=lambda item: item.get('at') or 0, reverse=True)
    return {'entries': entries[:limit], 'total': len(entries), 'counts': counts,
            'kinds': list(KINDS), 'projects': [{'project_id': key, 'count': projects[key]}
                                               for key in sorted(projects)],
            'generated': time.time()}
