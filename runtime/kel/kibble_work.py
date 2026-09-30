"""Kibble findings dispatched through Kel's durable coding pipeline.

Only the association is new state. Submission, worker, check and application facts
come from the existing pipeline; a finished job never marks a finding FIXED.
"""
import contextlib
import json
import os
from pathlib import Path
import secrets
import time

from .core import PolicyError


def ensure(store):
    with store.transaction() as db:
        db.execute('CREATE TABLE IF NOT EXISTS kibble_work('
                   'fix_id TEXT PRIMARY KEY, submission_id TEXT NOT NULL UNIQUE,'
                   'conversation TEXT NOT NULL, created REAL NOT NULL)')


def source_root(store):
    candidates = []
    if os.environ.get('KEL_SOURCE_DIR'):
        candidates.append(Path(os.environ['KEL_SOURCE_DIR']))
    # Installed layout: Kel/{App,Data,Kel}; development layout: Kel/runtime/kel.
    candidates.extend([Path(store.root).parent.parent / 'Kel', Path(__file__).resolve().parents[2]])
    from .containment import assert_usable_root
    for candidate in candidates:
        candidate = candidate.resolve()
        if ((candidate / '.git').exists() and (candidate / 'runtime/kel/service.py').is_file()
                and (candidate / 'desktop/package.json').is_file()):
            assert_usable_root(candidate, purpose='a Kel update', store=store)
            return candidate
    raise PolicyError('Kel could not find its source folder. Your finding is still saved.')


def stage_images(store, contract, run_id):
    """Copy verified Kibble attachments into the native worker's permitted run temp."""
    context = contract.get('context') or {}
    if not context.get('kibble'):
        return []
    from .core import digest
    from .containment import session_dir
    expected = store.root.resolve() / 'sessions' / str(run_id)
    run_temp = session_dir(store.root, run_id)
    folder = run_temp / 'kibble-inputs'
    if (run_temp.resolve() != expected or run_temp.is_symlink() or run_temp.is_junction()
            or folder.is_symlink() or folder.is_junction() or not folder.resolve().is_relative_to(expected)):
        raise PolicyError('The recorded screenshot input folder is linked.')
    paths = []
    for image in context.get('files') or []:
        if not image.get('image_path'):
            continue
        source = (store.root / image['image_path']).resolve()
        if not source.is_relative_to((store.root / 'attachments').resolve()):
            raise PolicyError('The recorded screenshot escaped attachment storage.')
        raw = source.read_bytes()
        if digest(raw) != image.get('sha256'):
            raise PolicyError('The recorded screenshot changed after it was sent.')
        name = str(image.get('name') or '')
        if Path(name).name != name or any(char in name for char in '/\\:') or not name:
            raise PolicyError('The recorded screenshot has an invalid name.')
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / name
        if target.is_symlink() or target.is_junction() or not target.resolve().is_relative_to(expected):
            raise PolicyError('The recorded screenshot input path is linked.')
        target.write_bytes(raw)
        paths.append(str(target))
    return paths


def progress(store, fix_id):
    # Read-only: listing captures must not create migrations during a write transaction.
    with contextlib.closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='kibble_work'").fetchone():
            return None
        row = db.execute('SELECT * FROM kibble_work WHERE fix_id=?', (fix_id,)).fetchone()
        if not row:
            return None
        submission = db.execute('SELECT * FROM submissions WHERE id=?', (row['submission_id'],)).fetchone()
        messages = [dict(m) for m in db.execute(
            "SELECT seq,role,text,at FROM messages WHERE conversation_id=? AND role!='user' "
            'ORDER BY seq DESC LIMIT 20', (row['conversation'],))][::-1]
        job_id = submission['job_id'] if submission else None
        events = [dict(e) for e in db.execute(
            'SELECT seq,type,at FROM events WHERE aggregate_id=? ORDER BY seq DESC LIMIT 30',
            (job_id,))][::-1] if job_id else []
    missing_job = False
    try:
        job = store.get(job_id) if job_id else None
    except KeyError:
        job = None
        missing_job = True
    from .auto_apply import describe
    application = describe(store, [job_id]).get(job_id) if job_id else None
    activity = []
    if job_id:
        with contextlib.closing(store.connect()) as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='native_progress'").fetchone():
                rows = db.execute('SELECT p.seq,p.method,p.data,p.at FROM native_progress p '
                                  'JOIN runs r ON r.id=p.run_id WHERE r.job_id=? '
                                  'ORDER BY p.seq DESC LIMIT 30', (job_id,)).fetchall()
                for entry in reversed(rows):
                    data = json.loads(entry['data'])
                    item = data.get('item') or {}
                    kind = item.get('type') or entry['method']
                    text = item.get('text') if kind in ('agentMessage', 'assistantMessage') else None
                    # Deliberately exclude reasoning, command arguments and command output.
                    labels = {'commandExecution': 'Running a command', 'fileChange': 'Changing files',
                              'mcpToolCall': 'Using a connected tool', 'webSearch': 'Searching the web',
                              'kel/session': 'Worker connected', 'turn/completed': 'Worker finished its turn'}
                    if text or kind in labels:
                        activity.append({'seq': entry['seq'], 'at': entry['at'], 'kind': kind,
                                         'text': str(text or labels[kind])[:2000],
                                         'state': 'completed' if entry['method'] in ('item/completed','turn/completed') else 'started'})
    milestones = [{'id': mid, 'state': m.get('state'), 'error': m.get('error')}
                  for mid, m in (job.get('milestones') or {}).items()] if job else []
    from .kibble_release import status as release_status
    release = release_status(store, fix_id)
    return {'submission_id': row['submission_id'], 'conversation': row['conversation'],
            'job_id': job_id, 'state': job['state'] if job else ('INTERRUPTED' if missing_job or not submission else submission['state']),
            'error': ('The saved work is no longer available.' if missing_job else
                      submission['error'] if submission else 'Kel closed before this request was saved.'),
            'updated': max([row['created']] + [e['at'] for e in events] + [m['at'] for m in messages]
                           + [a['at'] for a in activity] + ([release['updated']] if release else [])),
            'messages': messages, 'events': events, 'milestones': milestones, 'activity': activity,
            'verification': job.get('verdict') if job else None, 'application': application,
            'release': release, 'installed': bool(release and release.get('installed'))}


def send(service, dogfood, fix_id):
    ensure(service.store)
    with service.handoff_lock:
        item = dogfood.get(fix_id)
        existing = progress(service.store, fix_id)
        if existing:
            return item
        if item['status'] in ('FIXED', 'DISMISSED'):
            raise PolicyError('Open this finding before sending it to Kel.')
        if not item['transcript'].strip():
            raise PolicyError('Add what went wrong before sending this finding to Kel.')
        root = source_root(service.store)
        project_id = 'kel-self-update'
        with contextlib.closing(service.store.connect()) as db:
            project = db.execute('SELECT root FROM projects WHERE id=?', (project_id,)).fetchone()
        if project and Path(project['root'] or '').resolve() != root:
            raise PolicyError('The Kel update project points to a different folder. Check Projects first.')
        if not project:
            # The engine suite imports from runtime. Argument arrays avoid shell interpolation.
            checks = ['python', 'runtime/tools/check_kibble_update.py']
            service.projects.create('Kel updates', root=str(root), test_command=checks,
                                    project_id=project_id, context='Keep saved appearance and user data unchanged.')
        cid = service.context.conversation(project_id, title='Kibble ' + fix_id)
        sid = secrets.token_hex(16)
        attachments = []
        if item['has_screenshot']:
            attachments.append(service.context.attach(cid, fix_id + '.png',
                (dogfood.root / item['screenshot']).read_bytes(), 'image/png'))
        prompt = dogfood._render_prompt('KIBBLE-' + fix_id, [item])
        request = ('Fix this recorded Kel finding in the assigned repository copy.\n'
                   'This request authorizes this isolated self-update and supersedes D-86 for this finding.\n'
                   'Keep the installed app, user data, credentials and saved appearance unchanged.\n'
                   'Do not install or publish. Return the checked changes and any checks that never ran.\n'
                   'The screenshot, when present, is attached. Its original data path is not a work target.\n\n' + prompt)
        with service.store.transaction() as db:
            db.execute('INSERT INTO kibble_work VALUES(?,?,?,?)', (fix_id, sid, cid, time.time()))
        try:
            service.submit({'id': sid, 'conversation': cid, 'text': request,
                            'attachments': attachments, 'kind': 'coding'})
        except Exception:
            with service.store.transaction() as db:
                db.execute('DELETE FROM kibble_work WHERE fix_id=? AND submission_id=?', (fix_id, sid))
            raise
        return dogfood.get(fix_id)


def apply_work(service, dogfood, fix_id):
    """The Kibble Apply control: existing exact-evidence, conflict and backup gates."""
    item = dogfood.get(fix_id)
    work = item.get('work')
    if not work or not work.get('job_id'):
        raise PolicyError('Kel has no checked change for this finding yet.')
    job = service.store.get(work['job_id'])
    if (job.get('contract', {}).get('context', {}).get('kibble') or {}).get('fix_id') != fix_id:
        raise PolicyError('This change does not belong to this finding.')
    if job.get('verdict') != 'VERIFIED':
        raise PolicyError('Kel has not verified this change. Review its work first.')
    from .apply_changes import apply_checked
    apply_checked(service.store, work['job_id'], actor='user')
    # Applying source is not installing or verifying the observed UI symptom.
    return dogfood.get(fix_id)
