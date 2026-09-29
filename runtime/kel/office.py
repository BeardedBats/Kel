"""The live state of Kel's staffed work (D-66) for the work cards at the top of the chat (D-68).

Read-only over what the engine already records — jobs and milestones, the frozen staffing decision,
`staff_calls` (who was asked for, what ran, why), review checks, pod and Oracle findings, D-65
applications — plus one durable, idempotent "remove this finished card" action. Plain words only:
no tiers, lease ids, run ids or event names. A model is only named once its runtime reported it.

Design: `docs/v2/design/D-66_WORKFORCE_LIVE.md` §4.
"""
import re
import contextlib
import json
import time

from .core import PolicyError

FINISHED = ('done', 'failed', 'stopped')
KIND_WORDS = {'code': 'code', 'research': 'research', 'recipe': 'recipe', 'writing': 'writing'}
RUNTIME_LABELS = {'claude': 'Claude Code', 'claude-code': 'Claude Code', 'codex': 'Codex',
                  'codex-code': 'Codex', 'internal': 'Anthropic API', 'research': 'Anthropic API',
                  'claude-web': 'Claude Code (web search)', 'codex-web': 'Codex (web search)'}
PROVIDER_LABELS = {'anthropic': 'Anthropic', 'openai': 'OpenAI', 'deepseek': 'DeepSeek'}
# LIVE-10: independence in words ("Independence: different" read as jargon).
INDEPENDENCE_WORDS = {'different': 'A different model family from the one that did the work',
                      'reduced': 'The same model family as the one that did the work, so less independent'}
AREA_WORDS = {'functional-testing': 'Tests', 'maintainability': 'Maintainability',
              'security': 'Security', 'privacy': 'Privacy', 'data-integrity': 'Data safety',
              'release-integrity': 'Release', 'requirements-coverage': 'Meets the request',
              'adversarial': 'Second opinion'}
# The independent review passes after the checks (kel/oracle.py), in the order they run.
PASS_VIEWS = ('sentinel', 'oracle', 'red_team')


def _table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()


def dismissed(store):
    with contextlib.closing(store.connect()) as db:
        if not _table(db, 'office_dismissals'):
            return set()
        return {row['job_id'] for row in db.execute('SELECT job_id FROM office_dismissals')}


def _short(text, limit=90):
    words = ' '.join(str(text or '').split())
    return words if len(words) <= limit else words[:limit - 1].rsplit(' ', 1)[0] + '…'


def _title(job):
    handoff = (job.get('contract') or {}).get('handoff') or {}
    return (handoff.get('title') or recipe_title(job.get('contract'))
            or _short((job.get('contract') or {}).get('request'), 60) or 'Your request')


# FN-12: a recipe run is named after its recipe ("Ran Weekly rankings"), never its version or id;
# runs from before the name travelled in the contract are read from their request line.
_OLD_RECIPE_LINE = re.compile(r'^Run recipe (.+?) v\d+\.\d+\.\d+ \([^)]*\)\.?')


def recipe_title(contract):
    contract = contract or {}
    name = ((contract.get('recipe') or {}).get('name') or '').strip()
    if not name:
        match = _OLD_RECIPE_LINE.match(str(contract.get('request') or '').strip())
        name = match.group(1).strip() if match else ''
    return ('Ran ' + _short(name, 56)) if name else None


# LIVE-12: what happens to finished work afterwards (applying, undoing, removing its card, Nick's
# answer on it) never moves its finish time or its place in the row.
AFTER_FINISH = ('changes.applied', 'changes.auto_applied', 'changes.undone', 'office.dismissed',
                'needs_you.answered', 'budget.raised')


def _events(store, job_ids):
    """job id -> (first event time, last event time, last work event time) — the real clock of each
    job; the third leaves out what happens to finished work afterwards (AFTER_FINISH)."""
    ids = list(job_ids)
    out = {}
    with contextlib.closing(store.connect()) as db:
        for start in range(0, len(ids), 400):
            part = ids[start:start + 400]
            marks = ','.join('?' * len(part))
            after = ','.join('?' * len(AFTER_FINISH))
            for row in db.execute('SELECT aggregate_id, MIN(at) AS first, MAX(at) AS last, '
                                  'MAX(CASE WHEN type NOT IN (%s) THEN at END) AS worked FROM events '
                                  'WHERE aggregate_id IN (%s) GROUP BY aggregate_id' % (after, marks),
                                  list(AFTER_FINISH) + part):
                out[row['aggregate_id']] = (row['first'], row['last'], row['worked'] or row['last'])
    return out


def _undone(store, job_id):
    """LIVE-12: {at, files, folders} once Nick undid an applied change, else None."""
    with contextlib.closing(store.connect()) as db:
        row = db.execute("SELECT at, payload FROM events WHERE aggregate_id=? AND type='changes.undone' "
                         "ORDER BY revision DESC LIMIT 1", (job_id,)).fetchone()
    if not row:
        return None
    try:
        detail = (json.loads(row['payload']) or {}).get('detail') or {}
    except (TypeError, ValueError):
        detail = {}
    return {'at': row['at'], 'files': detail.get('files'), 'folders': detail.get('folders')}


def _application_state(store, job):
    """{'state'} of a coding change's application (APPLIED / UNDONE / WAITING…), else None."""
    if (job.get('contract') or {}).get('kind') != 'coding' or job.get('state') != 'CLOSED':
        return None
    try:
        from .auto_apply import describe
        entry = describe(store, [job['id']]).get(job['id']) or {}
    except Exception:
        return None
    return {'state': entry.get('state'), 'decision': entry.get('decision'),
            'waiting_reason': entry.get('waiting_reason')} if entry else None


def _restarted(store, job_id):
    """LIVE-11: True when Kel stopped this job to restart it with Nick's change (D-55)."""
    with contextlib.closing(store.connect()) as db:
        if not _table(db, 'handoff_restarts'):
            return False
        return db.execute('SELECT 1 FROM handoff_restarts WHERE replaced_job=?', (job_id,)).fetchone() is not None


def _published(store, job_id):
    with contextlib.closing(store.connect()) as db:
        row = db.execute('SELECT text, at FROM publications WHERE job_id=? ORDER BY at DESC LIMIT 1',
                         (job_id,)).fetchone()
    return dict(row) if row else None


def _pending_approvals(store, job_id):
    with contextlib.closing(store.connect()) as db:
        return db.execute("SELECT COUNT(*) FROM approvals WHERE job_id=? AND status='PENDING'",
                          (job_id,)).fetchone()[0]


def _reviewing(store, job):
    """True while a check or the second opinion is still running for this job."""
    with contextlib.closing(store.connect()) as db:
        if _table(db, 'staff_calls') and db.execute(
                "SELECT 1 FROM staff_calls WHERE job_id=? AND kind IN ('check','oracle','sentinel','red_team') "
                "AND state='running'",
                (job['id'],)).fetchone():
            return True
    for milestone in (job.get('milestones') or {}).values():
        if milestone.get('state') in ('CHECKING',):
            return True
        if milestone.get('state') == 'UNCERTAIN' and milestone.get('artifact') and any(
                c.get('kind') == 'manual_review' and not c.get('reviewer_id') for c in milestone.get('checks') or []):
            return True
    return False


def state_of(store, job, brief=None):
    """(state, status line, needs_you, why, next) in plain words from engine truth only."""
    from .continuation import Continuation
    from .oracle import attention, pending
    brief = brief or Continuation(store).resume_brief(job['id'])
    state = job.get('state')
    verdict = job.get('verdict')
    kind = (job.get('contract') or {}).get('kind')
    if state in ('CANCELLED', 'CANCELLING'):
        if _restarted(store, job['id']):
            # LIVE-11 / D-55: Kel stopped it to start again with Nick's change — not Nick's Stop.
            return 'stopped', 'Restarted with your change.', False, \
                'Kel stopped this version and started again with your change.', \
                'The new version has its own card.'
        return 'stopped', 'You stopped this work.', False, 'You stopped this work.', \
            'Its saved request is kept in this conversation.'
    if state == 'CLOSED':
        if verdict == 'VERIFIED':
            from .needs_answer import settled_line
            settled = settled_line(store, job)  # D-70: Nick answered Apply anyway / Leave it on the card
            if settled:
                return settled[0], settled[1], False, settled[1], None
            needed = attention(store, job)
            if needed:
                return 'needs_you', needed['why'], True, needed['why'], needed['next']
            if pending(store, job) or (kind == 'coding' and not _published(store, job['id'])):
                from .oracle import reviewing_line
                return ('in_review', reviewing_line(store, job) or 'Finishing up the checked change.',
                        False, None, None)
            line = 'Done and checked.'
            if kind == 'coding':
                from .auto_apply import describe
                application = describe(store, [job['id']]).get(job['id']) or {}
                if application.get('state') == 'APPLIED':
                    line = 'Done and checked — applied to your project.'
                elif application.get('state') == 'UNDONE':
                    line = 'Done and checked — you undid the change, so your files are as they were.'
                elif application.get('ask_first'):
                    ask = 'Checked and ready. %s, so it waits for you to apply it.' % application['waiting_reason']
                    return 'needs_you', ask, True, ask, 'Choose Apply when you are ready, or Leave it.'
                elif application.get('waiting_reason'):
                    return 'needs_you', 'Checked, but Kel did not apply it on its own: %s.' % \
                        application['waiting_reason'], True, application['waiting_reason'], \
                        'Choose Apply anyway when you are ready.'
            return 'done', line, False, brief.get('why'), brief.get('next')
        return 'failed', brief.get('why') or "It finished, but it didn't pass its checks.", False, \
            brief.get('why'), brief.get('next')
    if _pending_approvals(store, job['id']) or state == 'AWAITING_USER':
        return 'needs_you', 'Waiting for your decision on a gated step.', True, \
            'Waiting for your decision on a gated step.', 'Decide on the request card in this conversation.'
    if state == 'BLOCKED':
        from .core import explain_failure
        why = explain_failure(job) or 'A safety rule stopped this work before its next step.'
        return 'needs_you', _short(why.split('\n')[0], 160), True, why, 'Open the conversation to decide.'
    if brief.get('needs_you'):
        return 'needs_you', brief.get('why'), True, brief.get('why'), brief.get('next')
    if _reviewing(store, job):
        return 'in_review', 'The Verifier is checking the result.', False, brief.get('why'), brief.get('next')
    return 'working', None, False, brief.get('why'), brief.get('next')


def _run_states(store, job_id):
    with contextlib.closing(store.connect()) as db:
        return {row['id']: row['state'] for row in db.execute('SELECT id, state FROM runs WHERE job_id=?',
                                                               (job_id,))}


def _call_state(call, runs):
    if call['kind'] == 'work' and call['state'] == 'running':
        run = runs.get(call['id'])
        if run == 'WAITING_APPROVAL':
            return 'waiting'
        if run in ('ORPHANED', 'CANCELLED'):
            return 'stopped'
        if run in ('RESULT_RECORDED', 'EXITED'):
            return 'done'
    return {'running': 'working', 'done': 'done', 'failed': 'failed', 'stopped': 'stopped',
            'waiting': 'waiting'}.get(call['state'], 'working')


def _objective(job, milestone_id):
    spec = next((m for m in (job.get('contract') or {}).get('milestones') or [] if m.get('id') == milestone_id), {})
    if (job.get('contract') or {}).get('kind') == 'coding':
        from .code_streams import step_label
        return step_label(job.get('contract'), milestone_id) or 'the change'
    if milestone_id == (job.get('contract') or {}).get('final_milestone'):
        return 'combining the parts'
    text = str(spec.get('objective') or '')
    for marker in ('Complete this part of the source request: ', 'Research this part of the source request: '):
        if text.startswith(marker):
            text = text[len(marker):].split('\n')[0]
    return _short(text, 70) or 'its step'


def _doing(call, state, job):
    what = _objective(job, call.get('milestone_id'))
    if call['kind'] == 'work':
        if state == 'working':
            return 'Working on ' + what
        if state == 'waiting':
            return 'Waiting for your decision'
        if state == 'done':
            return 'Finished ' + what
        if state == 'failed':
            return 'Could not finish ' + what
        return 'Stopped'
    if call['kind'] == 'check':
        if state == 'working':
            return 'Checking the result'
        summary = call.get('summary') or ''
        return ('Checked the result — ' + summary) if summary.startswith('said') else (
            'Could not finish the check' if state == 'failed' else 'Checked the result')
    if call['kind'] == 'oracle':
        if state == 'working':
            return 'Giving an independent second opinion'
        return 'Second opinion: ' + (call.get('summary') or 'finished')
    if call['kind'] == 'sentinel':
        if state == 'working':
            return 'Checking it for security and data safety'
        return 'Security check: ' + (call.get('summary') or 'finished')
    if call['kind'] == 'red_team':
        if state == 'working':
            return 'Trying to break the accepted result'
        return 'Tried to break it: ' + (call.get('summary') or 'finished')
    return 'Planning'


def _member(call, runs, job):
    from .role_models import ADAPTER_FAMILIES, REASONING_LABELS, describe_model
    from .staff import ROLE_LABELS
    asked, ran = call.get('asked') or {}, call.get('ran') or {}
    state = _call_state(call, runs)
    confirmed = bool(ran.get('model_confirmed') and ran.get('model'))
    label, version = describe_model(raw=ran.get('model')) if confirmed else (None, None)
    adapter = ran.get('adapter')
    family = ADAPTER_FAMILIES.get(adapter)
    reasoning = ran.get('reasoning') if confirmed else None
    if confirmed and not reasoning and (asked.get('effort_arg') or asked.get('reasoning')) and state != 'working':
        reasoning = asked.get('effort_arg') or asked.get('reasoning')  # a tier's level (Routing 2) wins over Auto
    asked_label = asked.get('label')
    asked_view = None
    if asked_label and (not confirmed or label != asked_label):
        asked_view = {'model_label': asked_label,
                      'reasoning': REASONING_LABELS.get(asked.get('effort_arg') or asked.get('reasoning') or 'auto')}
    note = call.get('why')
    if "can't run here" in str(call.get('summary') or ''):
        note = call['summary']  # the runtime refused the model: its plain reason is the note
    if ran.get('independence') == 'reduced':
        note = note or 'This review is less independent: no model from another family could run it.'
    return {'id': call['id'], 'role': call['role'], 'role_label': ROLE_LABELS.get(call['role'], call['role']),
            'instance': call.get('instance'), 'doing': _doing(call, state, job), 'state': state,
            'model': ran.get('model') if confirmed else None, 'model_label': label, 'version': version,
            'model_confirmed': confirmed, 'provider': PROVIDER_LABELS.get(family), 'runtime': RUNTIME_LABELS.get(adapter),
            'runtime_version': ran.get('runtime_version'), 'reasoning': REASONING_LABELS.get(reasoning, reasoning) if reasoning else None,
            'asked': asked_view, 'note': note, 'independence': ran.get('independence'),
            'independence_label': INDEPENDENCE_WORDS.get(ran.get('independence')),
            'step': call.get('milestone_id'), 'step_label': _step_label(job, call.get('milestone_id')) if call['kind'] == 'work' else None,
            'started_at': call.get('started'), 'finished_at': call.get('finished')}


def _step_label(job, milestone_id):
    """The step a staff row works on, in words ("Part 2 of 3: …", "Combining the parts"), when the
    work has more than one step; None for one-step work (the row's `doing` already says it)."""
    if not milestone_id or len((job.get('contract') or {}).get('milestones') or []) < 2:
        return None
    what = _objective(job, milestone_id)
    return what[:1].upper() + what[1:] if what else None


def _standard_plan_note(job):
    """Coding and research always start from Kel's standard plan by design (the Builder or the research
    worker does the thinking); only other work falls back to it when no planning model answered."""
    compiler = ((job.get('contract') or {}).get('planner') or {}).get('compiler') or         (job.get('contract') or {}).get('compiler')
    if compiler == 'coding-contract-v2' or (job.get('contract') or {}).get('kind') == 'coding':
        return 'Kel used its standard coding plan.'
    if compiler == 'research-v1':
        return 'Kel used its standard research plan.'
    return 'Kel used its standard plan for this kind of work.'


def _kel_turn(store, job):
    """The model Kel's own turn for this work really ran on (usage, D-72 item 6), or {}."""
    submission = (job.get('contract') or {}).get('submission_id') or \
        ((job.get('contract') or {}).get('handoff') or {}).get('submission_id')
    if not store or not submission:
        return {}
    try:
        from .usage import KEL_KINDS, rows
        items = [i for i in rows(store, submission_id=str(submission)) if i.get('kind') in KEL_KINDS
                 and (i.get('raw_model') or i.get('model'))]
    except Exception:
        return {}
    return max(items, key=lambda i: i.get('at') or 0) if items else {}


def _kel_member(job, store=None):
    from .role_models import describe_model
    planner = (job.get('contract') or {}).get('planner') or {}
    model = planner.get('model')
    standard = not model  # LIVE-10: coding, research and template work start from Kel's standard plan
    runtime = RUNTIME_LABELS.get(planner.get('provider'))
    reasoning = None
    if not model:
        # Kel's own turn still ran on a real model: name it (only as the runtime reported it).
        turn = _kel_turn(store, job)
        model = turn.get('raw_model') or turn.get('model')
        runtime = RUNTIME_LABELS.get(turn.get('adapter')) or runtime
        reasoning = None  # usage keeps reasoning tokens, not the level; no level is claimed here
    label, version = describe_model(raw=model) if model else (None, None)
    return {'id': 'kel', 'role': 'kel', 'role_label': 'Kel', 'instance': 1,
            'doing': 'Planned this work and chose who does it', 'state': 'done',
            'model': model, 'model_label': label, 'version': version, 'model_confirmed': bool(model),
            'provider': None, 'runtime': runtime, 'runtime_version': None,
            'reasoning': reasoning, 'asked': None, 'standard_plan': standard,
            'note': _standard_plan_note(job) if standard else None,
            'independence': None, 'step': None, 'started_at': (job.get('contract') or {}).get('staffing', {}).get('decided_at'),
            'finished_at': None}


def _progress(job, state, brief):
    milestones = job.get('milestones') or {}
    total = len(milestones)
    done = sum(1 for m in milestones.values() if m.get('state') == 'ACCEPTED')
    if state == 'done':
        label = 'Done' if total <= 1 else 'All %d steps done' % total
    elif state == 'in_review':
        label = 'Checking the result'
    elif state == 'needs_you':
        label = 'Waiting for you'
    elif state == 'failed':
        # LIVE-10: an unconfirmed result is not a failed one.
        label = "Couldn't confirm it passed" if job.get('verdict') == 'UNCERTAIN' else "Didn't pass its checks"
    elif state == 'stopped':
        label = 'Stopped'
    elif total > 1:
        label = '%d of %d steps done' % (done, total)
    else:
        label = 'Working on it'
    return {'done': done, 'total': total, 'label': label}


def _working_line(job, members):
    live = [m for m in members if m['state'] == 'working' and m['role'] != 'kel']
    if not live:
        return 'Kel is getting this started.'
    first = live[0]
    if len(live) > 1:
        return '%s and %d more are working on it.' % (first['role_label'], len(live) - 1)
    return '%s is %s.' % (first['role_label'], first['doing'][0].lower() + first['doing'][1:])


def _item(store, job, conv_map, clock, calls_by_job, runs_by_job, brief):
    from .projects import primary_project
    from .staff import staffing_of
    record = staffing_of(job) or {}
    state, line, needs_you, _why, _next = state_of(store, job, brief)
    calls = calls_by_job.get(job['id'], [])
    members = [_member(call, runs_by_job.get(job['id'], {}), job) for call in calls]
    if state == 'working' or not line:
        line = line or _working_line(job, members)
    team = [{'role': 'kel', 'role_label': 'Kel', 'state': 'done'}]
    for member in members:
        # D3: each part's Builder is its own row, with the step it works on.
        entry = {'role': member['role'], 'role_label': member['role_label'], 'state': member['state']}
        if member.get('step_label'):
            entry.update(instance=member.get('instance'), step_label=member['step_label'])
        team.append(entry)
    first, last, worked = clock.get(job['id'], (job.get('created'), job.get('created'), job.get('created')))
    finished = state in FINISHED
    paused = job.get('state') in ('PAUSED', 'PAUSING')
    submission = ((job.get('contract') or {}).get('handoff') or {}).get('submission_id')
    return {'job_id': job['id'], 'title': _title(job), 'project_id': primary_project(job, conv_map),
            'conversation_id': job.get('conversation'), 'submission_id': submission,
            'kind': KIND_WORDS.get(record.get('kind'), 'writing'), 'state': state, 'finished': finished,
            'status_line': line, 'needs_you': needs_you, 'progress': _progress(job, state, brief),
            'team': team, 'team_size': len(team), 'started_at': job.get('created') or first,
            'updated_at': last, 'finished_at': worked if finished else None,
            # The row tells passed from unconfirmed/failed work itself (not only the detail).
            'verdict': job.get('verdict') if job.get('state') == 'CLOSED' else None,
            'application': _application_state(store, job),
            # VIS-6: paused work says so (its card shows a paused step, not "working").
            'paused': paused, 'undone': _undone(store, job['id']) if finished else None}


GROUP = {'scoping': 0, 'needs_you': 0, 'working': 1, 'in_review': 1, 'done': 2, 'failed': 2, 'stopped': 2}


def _order_key(item):
    group = GROUP.get(item['state'], 1)
    when = item['finished_at'] if group == 2 else item['started_at']
    return (group, -(when or 0), item['job_id'])


def items(store, *, conversation=None, project=None):
    """Every staffed job that is open, and every finished one Nick has not removed (D-68)."""
    from .continuation import Continuation
    from .projects import ALL, job_projects
    from .staff import calls, staffing_of
    removed = dismissed(store)
    with contextlib.closing(store.connect()) as db:
        conv_map = {row['id']: row['project_id'] for row in db.execute('SELECT id, project_id FROM conversations')} \
            if _table(db, 'conversations') else {}
    chosen = []
    for job in store.list_jobs():
        if not staffing_of(job) or job['id'] in removed:
            continue
        if conversation and job.get('conversation') != conversation:
            continue
        if project and project != ALL and project not in job_projects(job, conv_map):
            continue
        chosen.append(job)
    clock = _events(store, [job['id'] for job in chosen])
    cont = Continuation(store)
    out = []
    for job in chosen:
        out.append(_item(store, job, conv_map, clock, {job['id']: calls(store, job['id'])},
                         {job['id']: _run_states(store, job['id'])}, cont.resume_brief(job['id'])))
    from .scoping import office_items
    out.extend(office_items(store, conversation=conversation, project=project))  # D-70: "Scoping" cards
    out.sort(key=_order_key)
    for index, item in enumerate(out):
        item['order'] = index
    return {'generated': time.time(), 'scope': {'conversation': conversation, 'project': project},
            'items': out}


def _findings_view(rows):
    out = []
    for row in rows:
        severity = row.get('severity')
        out.append({'severity': 'note' if severity == 'info' else severity,
                    'area': AREA_WORDS.get(row.get('lens'), str(row.get('lens') or '').replace('-', ' ').capitalize()),
                    'summary': row.get('summary'), 'where': row.get('location'),
                    'status': 'open' if row.get('status') in ('open', 'confirmed') else 'resolved'})
    return out


def detail(store, job_id):
    """One piece of work in full: team, steps, review, second opinion, files, verification, links."""
    from .continuation import Continuation
    from .core import interrupted, verification_lines
    from .oracle import findings_for, status as oracle_status
    from .pod_review import task_id as pod_task
    from .role_models import describe_model
    from .staff import calls, staffing_of
    try:
        job = store.get(job_id)
    except KeyError:
        raise PolicyError('Kel could not find that work.') from None
    if not staffing_of(job):
        raise PolicyError('That work has no live team to show.')
    with contextlib.closing(store.connect()) as db:
        conv_map = {row['id']: row['project_id'] for row in db.execute('SELECT id, project_id FROM conversations')} \
            if _table(db, 'conversations') else {}
    brief = Continuation(store).resume_brief(job_id)
    job_calls = calls(store, job_id)
    runs = _run_states(store, job_id)
    base = _item(store, job, conv_map, _events(store, [job_id]), {job_id: job_calls}, {job_id: runs}, brief)
    state, _line, _needs, why, nxt = state_of(store, job, brief)
    staff_view = [_kel_member(job, store)] + [_member(call, runs, job) for call in job_calls]
    milestones = job.get('milestones') or {}
    steps = []
    for spec in (job.get('contract') or {}).get('milestones') or []:
        milestone = milestones.get(spec['id']) or {}
        raw = milestone.get('state')
        step_state = {'ACCEPTED': 'done', 'RUNNING': 'working', 'CHECKING': 'in_review',
                      'UNCERTAIN': 'in_review' if job.get('state') != 'CLOSED' else 'failed',
                      'NEEDS_REPAIR': 'working' if job.get('state') != 'CLOSED' else 'failed',
                      'EXHAUSTED': 'failed',
                      'CANCELLED': 'stopped'}.get(raw, 'waiting')
        at = max([c.get('finished') or c.get('started') or 0 for c in job_calls
                  if c.get('milestone_id') == spec['id']] or [0]) or None
        if job.get('state') in ('PAUSED', 'PAUSING') and step_state in ('waiting', 'working'):
            step_state = 'paused'  # VIS-6: a paused job's open step is paused, not waiting or working
        steps.append({'id': spec['id'], 'label': _objective(job, spec['id'])[:1].upper() + _objective(job, spec['id'])[1:],
                      'state': step_state, 'at': at, 'attempts': milestone.get('attempts'),
                      'interrupted': bool(interrupted(milestone))})
    from .assurance import findings as ledger
    pod_rows = []
    try:
        for mid, milestone in milestones.items():
            subject = (milestone.get('artifact') or {}).get('sha256')
            pod_rows += [row for row in ledger(store, task_id=pod_task(job_id, mid))
                         if row.get('artifact') == subject]
    except Exception:
        pod_rows = []
    checks = [c for m in milestones.values() for c in m.get('checks') or [] if c.get('kind') == 'manual_review']
    last_check = next((c for c in reversed(job_calls) if c['kind'] == 'check'), None)
    checker = _member(last_check, runs, job) if last_check else None
    review = {'verdict': (checks[-1].get('verdict') or '').lower() or None if checks else None,
              'checked_by': (checker or {}).get('model_label') or (
                  describe_model(raw=checks[-1].get('reviewer_model'))[0] if checks and checks[-1].get('reviewer_model')
                  else None),
              'independence': (checker or {}).get('independence'),
              'independence_label': INDEPENDENCE_WORDS.get((checker or {}).get('independence')),
              'findings': _findings_view(pod_rows)}
    # D-84: which existing tests Kel changed, why, and who approved each (the Review Team's view too).
    test_changes = []
    if (job.get('contract') or {}).get('kind') == 'coding':
        try:
            from .coding import test_changes_line, test_changes_view
            run_id = ((milestones.get('code') or {}).get('artifact') or {}).get('run_id')
            test_changes = test_changes_view(store, run_id) if run_id else []
        except Exception:
            test_changes = []
    review['test_changes'] = test_changes
    # D-85: the review check was settled without an independent reviewer (small, reversible work).
    skipped = next((c for c in checks if c.get('proportional')), None)
    review['not_needed'] = (skipped.get('findings') or [None])[0] if skipped else None
    passes = {kind: _pass_view(store, job, job_calls, runs, kind, oracle_status, findings_for)
              for kind in PASS_VIEWS}
    files, application = None, None
    if (job.get('contract') or {}).get('kind') == 'coding':
        from .auto_apply import changed_paths, describe
        try:
            files = changed_paths(store, job)
        except Exception:
            files = None
        application = describe(store, [job_id]).get(job_id)
    summary = verification_lines(job)
    result_word = None
    if job.get('state') == 'CLOSED':
        result_word = {'VERIFIED': 'passed', 'FAILED': 'failed'}.get(job.get('verdict'), 'not_confirmed')
    published = _published(store, job_id)
    handoff = (job.get('contract') or {}).get('handoff') or {}
    out = dict(base)
    if state == 'needs_you':
        from .needs_answer import question
        try:
            out['question'] = question(store, job, why, nxt)  # D-70: answer "Needs you" inside the card
        except Exception:
            out['question'] = None
    try:
        from .budget import BUDGET_WAIT, view as budget_view
        budget = budget_view(store, job)
        budget['stopped'] = str(job.get('route_block') or '').startswith(BUDGET_WAIT)
        budget['can_raise'] = budget['stopped'] and budget['class'] != 'high-assurance'
        from .budget import CEILINGS, ORDER
        index = ORDER.index(budget['class']) if budget['class'] in ORDER else -1
        budget['next'] = ORDER[index + 1] if 0 <= index < len(ORDER) - 1 else None
        budget['next_ceilings'] = CEILINGS.get(budget['next']) if budget['next'] else None
    except Exception:
        budget = None  # the budget view is additive; the detail never fails on it
    out['budget'] = budget
    try:
        from .usage import job_usage
        out['usage'] = job_usage(store, job)  # D-72: cost and time for the detail header
    except Exception:
        out['usage'] = None
    out.update({'why': why, 'next': nxt, 'staff': staff_view, 'steps': steps, 'review': review,
                'oracle': passes['oracle'], 'sentinel': passes['sentinel'], 'red_team': passes['red_team'],
                'files_changed': files, 'application': application, 'test_changes': test_changes,
                'test_changes_line': test_changes_line([c for c in test_changes if c.get('ruling') == 'approved'])
                if test_changes else None,
                'verification': {'result': result_word, 'summary': summary},
                'result': _short(published['text'], 600) if published else None,
                'links': {'conversation_id': job.get('conversation'),
                          'submission_id': handoff.get('submission_id'), 'message_seq': handoff.get('ack_seq')}})
    return out


def _pass_view(store, job, job_calls, runs, kind, pass_status, pass_findings):
    """One independent pass for the detail, in the Oracle's shape: {state, why, conclusion, coverage,
    independence, independence_label, model_label, reasoning, findings}."""
    current = pass_status(store, job, kind)
    call = next((c for c in reversed(job_calls) if c['kind'] == kind), None)
    member = _member(call, runs, job) if call else {}
    try:
        rows = pass_findings(store, job, kind=kind) if current['state'] != 'not_needed' else []
    except Exception:
        rows = []
    why = current.get('why') or ('; '.join(current.get('reasons') or []) or None)
    if kind == 'sentinel' and current['state'] == 'not_needed' and not why:
        record = (job.get('contract') or {}).get('staffing') or {}
        note = (record.get('sentinel') or {}).get('not_needed')
        why = (note[:1].upper() + note[1:] + '.') if note else None
    return {'state': current['state'], 'why': why,
            'independence': current.get('independence'), 'model_label': member.get('model_label'),
            'independence_label': INDEPENDENCE_WORDS.get(current.get('independence')),
            'reasoning': member.get('reasoning'), 'findings': _findings_view(rows),
            # LIVE-10: what the pass concluded (not only why it was asked).
            'conclusion': _oracle_conclusion(current, rows),
            'coverage': current.get('coverage')}


def _oracle_conclusion(current, rows):
    """One plain sentence: what the independent second opinion concluded, or None while it runs."""
    state = current.get('state')
    if state == 'could_not_run':
        return "It couldn't run: %s." % (current.get('why') or 'no reason was recorded')
    if state == 'not_needed' and current.get('skipped'):
        return current.get('why')
    if state != 'done':
        return None
    live = [r for r in rows if r.get('status') in ('open', 'confirmed')]
    serious = [r for r in live if r.get('severity') in ('blocker', 'critical')]
    notes = [r for r in live if r.get('severity') not in ('blocker', 'critical')]
    if serious:
        return 'It found %s: %s' % ('a serious problem' if len(serious) == 1 else '%d serious problems' % len(serious),
                                    ' '.join(str(serious[0].get('summary') or '').split()))
    if notes:
        return 'It found nothing that should stop this, and left %s.' % (
            'one note' if len(notes) == 1 else '%d notes' % len(notes))
    return 'It found nothing that should stop this.'


def dismiss(store, job_id, actor='user', service=None):
    """Remove one finished card (D-68). Durable, idempotent, one Activity line; nothing is deleted."""
    from .staff import ensure_schema, staffing_of
    if not isinstance(job_id, str) or not job_id.strip():
        raise PolicyError('Pick the finished work to remove first.')
    try:
        job = store.get(job_id)
    except KeyError:
        job = None
    if job is None:
        # D-74.3 / LIVE-8: an open scoping card is dismissed with "Not now" (cancels the scoping;
        # nothing starts). Its id is the card's `scoping_id`.
        from . import scoping
        if scoping._row(store, job_id) and service is not None:
            out = scoping.dismiss(service, job_id, actor=actor)
            return {'dismissed': True, 'already': bool(out.get('already')), 'job_id': job_id, 'scoping': True}
        raise PolicyError('Kel could not find that work.')
    ensure_schema(store)
    with contextlib.closing(store.connect()) as db:
        if db.execute('SELECT 1 FROM office_dismissals WHERE job_id=?', (job_id,)).fetchone():
            return {'dismissed': True, 'already': True, 'job_id': job_id}
    if staffing_of(job):
        state = state_of(store, job)[0]
        if state not in FINISHED:
            raise PolicyError('This work is still going. Stop it first, then remove it.')
    with store.transaction() as db:
        inserted = db.execute('INSERT OR IGNORE INTO office_dismissals(job_id, at, actor) VALUES(?,?,?)',
                              (job_id, time.time(), actor)).rowcount
        if inserted:
            record = store._get(db, job_id)
            store._save(db, record, 'office.dismissed', {'actor': actor})
    return {'dismissed': True, 'already': not bool(inserted), 'job_id': job_id}
