"""Activity 2.0 (V2-08) — the historical timeline, read from what the engine already recorded.

One read surface over the durable `events` stream plus the jobs and conversations the line already
keeps. Every row is a plain sentence; the filters are Project, date, type and failure, plus search;
a row carries how to open its result/evidence and whether the work can be retried or recovered.

Deliberately absent: worker ids, leases, staffing graphs, cockpit controls, and any raw event payload
(a payload carries the contract and the request; the timeline quotes at most the person's own request
line for the row they started).
"""
import contextlib
import json
import time

from .core import PolicyError
from .projects import job_projects, primary_project

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
    # D-64 Full access: what Kel went ahead with (or refused) instead of asking.
    'approval.auto_granted': 'work', 'approval.refused': 'work',
    'authorization.auto_granted': 'work', 'authority.changed': 'other',
    # D-65: a verified change written into the project (on its own under Full access), and its undo.
    'changes.auto_applied': 'work', 'changes.applied': 'work', 'changes.undone': 'work',
}
KINDS = ('work', 'attention', 'learning', 'recipes', 'connections', 'network', 'staffing',
         'recovery', 'scheduled', 'other')
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
    if event_type == 'approval.auto_granted':
        summary = _snippet(detail.get('summary'), 120)
        return ('Full access: Kel went ahead to %s.' % summary if summary
                else 'Full access: Kel went ahead without asking.')
    if event_type == 'approval.refused':
        summary = _snippet(detail.get('summary'), 120)
        return ('Kel did not %s: it would have touched %s.' % (summary or 'take that step',
                                                               _snippet(detail.get('reason'), 60)
                                                               or 'a protected folder'))
    if event_type == 'authorization.auto_granted':
        summary = _snippet(detail.get('summary'), 120)
        return 'Full access: Kel went ahead to %s.' % (summary or 'continue')
    if event_type == 'changes.auto_applied':
        summary = _snippet(detail.get('summary'), 120)
        return 'Full access: Kel went ahead to %s.' % (summary or 'apply the checked change')
    if event_type == 'changes.applied':
        return 'The checked change was applied to your project.'
    if event_type == 'changes.undone':
        return 'The applied change was undone; the earlier files are back.'
    if event_type == 'authority.changed':
        return ('Full access is on: Kel acts without asking.' if detail.get('mode') == 'full'
                else 'Ask first is on: Kel asks before it acts.')
    if event_type.startswith('schedule.'):
        return _schedule_sentence(event_type.split('.', 1)[1], detail)
    if event_type.startswith('approval.'):
        return 'You were asked something about this work.'
    return 'Something was recorded (%s).' % event_type


def _schedule_sentence(action, detail):
    """D-57: one plain sentence per scheduled-task event."""
    name = '\u201c%s\u201d' % (_snippet(detail.get('name'), 80) or 'a scheduled task')
    late = detail.get('late_by') or 0
    if action == 'created':
        return 'You scheduled %s.' % name
    if action == 'updated':
        return 'You changed the scheduled task %s.' % name
    if action == 'paused':
        if detail.get('problem'):
            return 'Kel paused %s: %s' % (name, _snippet(detail.get('problem'), 160))
        return 'You paused %s.' % name
    if action == 'resumed':
        return 'You resumed %s.' % name
    if action == 'deleted':
        return 'You deleted the scheduled task %s.' % name
    if action == 'imported':
        return 'Kel brought %s over from your earlier scheduled tasks.' % name
    if action == 'fired':
        if detail.get('manual'):
            return 'You ran %s now.' % name
        if late >= 60:
            return 'A scheduled run of %s started, %d minutes late.' % (name, int(late // 60))
        return 'A scheduled run of %s started.' % name
    if action == 'skipped':
        return 'A run of %s was skipped: the last one was still going.' % name
    if action == 'queued':
        return 'A run of %s will start when the last one finishes.' % name
    if action == 'missed':
        count = int(detail.get('count') or 1)
        return 'Missed %d run%s of %s while Kel was closed.' % (count, '' if count == 1 else 's', name)
    if action == 'not_started':
        cause = _snippet(detail.get('cause'), 160)
        return "A run of %s didn't start%s" % (name, ': ' + cause if cause else '.')
    if action == 'imported_run':
        return 'An earlier run of %s.' % name
    return 'Something happened to %s.' % name


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
    with contextlib.closing(store.connect()) as db:  # the sqlite context manager never closes
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
        if event_type.startswith('schedule.'):
            row_kind = 'scheduled'  # D-57
        if row_kind == 'other' and event_type.startswith('approval.'):
            row_kind = 'attention'
        if kind and row_kind != kind:
            continue
        aggregate = event.get('aggregate_id') or ''
        job = jobs.get(aggregate)
        row_project = None
        row_projects = set()
        schedule_detail = None
        if job:
            # D-54: a job belongs to its chat's project and to the project its contract names — the
            # same rule Work uses, so both pages count the same jobs for a project.
            row_projects = job_projects(job, conversations)
            row_project = project_id if project_id in row_projects else primary_project(job, conversations)
        if row_kind == 'scheduled':
            # D-57: a scheduled-task event belongs to the project its schedule names.
            try:
                raw = event.get('payload')
                schedule_detail = (json.loads(raw) if isinstance(raw, str) else raw or {}).get('detail') or {}
            except (TypeError, ValueError, AttributeError):
                schedule_detail = {}
            if schedule_detail.get('project_id'):
                row_projects = {schedule_detail['project_id']}
                row_project = schedule_detail['project_id']
        if project_id and project_id not in row_projects:
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
        if event_type == 'schedule.not_started':
            failed = True
        if failures_only and not failed:
            continue
        if needle and needle not in what.lower():
            continue
        counts[row_kind] = counts.get(row_kind, 0) + 1
        for counted in (row_projects or ({row_project} if row_project else set())):
            projects[counted] = projects.get(counted, 0) + 1
        entries.append({'at': at, 'kind': row_kind, 'type': event_type, 'what': what,
                        'project_id': row_project, 'job_id': aggregate if job else None,
                        'state': state, 'verdict': verdict, 'failed': failed,
                        'result': artifact, 'evidence': digest, 'can_retry': can_retry})
        if row_kind == 'scheduled':
            entries[-1]['schedule_id'] = aggregate.split(':', 1)[1] if ':' in aggregate else None
    entries.sort(key=lambda item: item.get('at') or 0, reverse=True)
    return {'entries': entries[:limit], 'total': len(entries), 'counts': counts,
            'kinds': list(KINDS), 'projects': [{'project_id': key, 'count': projects[key]}
                                               for key in sorted(projects)],
            'generated': time.time()}
