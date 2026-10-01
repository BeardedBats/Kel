"""Whole-task observations, separate from verification and route-selection authority.

Only explicit feedback marks usefulness. Missing feedback, spending or duration stays unknown.
This module never changes routing, permissions, verification, or application state.
"""
import contextlib
import math
import time

from .core import PolicyError, digest


def _ensure(db):
    db.execute('CREATE TABLE IF NOT EXISTS task_feedback('
               'job_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, response TEXT NOT NULL,'
               'at REAL NOT NULL, revision_requests INTEGER NOT NULL DEFAULT 0)')
    if 'subject' not in {row[1] for row in db.execute('PRAGMA table_info(task_feedback)')}:
        db.execute('ALTER TABLE task_feedback ADD COLUMN subject TEXT')


def _number(value):
    return (float(value) if isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value >= 0 else None)


class TaskOutcomes:
    def __init__(self, store):
        self.store = store
        with store.transaction() as db:
            _ensure(db)

    def _job(self, job_id, project_id):
        try:
            job = self.store.get(str(job_id))
        except KeyError:
            raise PolicyError('That work is missing.') from None
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT project_id FROM conversations WHERE id=?',
                             (job.get('conversation'),)).fetchone()
            actual = row['project_id'] if row else job.get('contract', {}).get('project_id')
            if actual != project_id:
                raise PolicyError('That work belongs to another project.')
            from .chat_state import read_states
            if any(state.get('deleted_at') and state.get('conversation_id') == job.get('conversation')
                   for state in read_states(db).values()):
                raise PolicyError('That conversation was deleted.')
        return job

    @staticmethod
    def _subject(job):
        return digest({'contract': job['contract'], 'contract_version': job.get('contract_version'),
                       'assessment': job.get('assessment'), 'verdict': job.get('verdict'),
                       'outputs': {mid: step.get('artifact') for mid, step in job['milestones'].items()}})

    def feedback(self, job_id, project_id, response):
        job = self._job(job_id, project_id)
        if response not in ('useful', 'revision_requested'):
            raise PolicyError('Choose Useful or Needs changes.')
        if job.get('state') != 'CLOSED':
            raise PolicyError('Wait for the work to finish before rating the result.')
        if response == 'useful':
            if job.get('verdict') != 'VERIFIED' or self.store.assess(job['id']) != 'VERIFIED':
                raise PolicyError('This result has not passed its current checks. Its checks remain incomplete.')
            job = self._job(job_id, project_id)
        subject = self._subject(job)
        with self.store.transaction() as db:
            previous = db.execute('SELECT * FROM task_feedback WHERE job_id=?', (job['id'],)).fetchone()
            if not previous or previous['response'] != response or previous['subject'] != subject:
                revisions = (previous['revision_requests'] if previous else 0) + int(response == 'revision_requested')
                db.execute('INSERT INTO task_feedback(job_id,project_id,response,at,revision_requests,subject) '
                           'VALUES(?,?,?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET '
                           'project_id=excluded.project_id,response=excluded.response,at=excluded.at,'
                           'revision_requests=excluded.revision_requests,subject=excluded.subject',
                           (job['id'], project_id, response, time.time(), revisions, subject))
        return self.view(job['id'], project_id)

    def view(self, job_id, project_id):
        job = self._job(job_id, project_id)
        with contextlib.closing(self.store.connect()) as db:
            feedback = db.execute('SELECT * FROM task_feedback WHERE job_id=?', (job['id'],)).fetchone()
            times = db.execute('SELECT MIN(at), MAX(at) FROM events WHERE aggregate_id=?',
                               (job['id'],)).fetchone()
            has_submissions = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='submissions'").fetchone()
            sid_rows = (db.execute('SELECT id FROM submissions WHERE job_id=?', (job['id'],)).fetchall()
                        if has_submissions else [])
        from .usage import rows
        calls = rows(self.store, job_id=job['id'])
        for sid in sid_rows:
            calls.extend(rows(self.store, submission_id=sid['id']))
        unique = {row['call_id']: row for row in calls if row.get('call_id')}
        spending = {'reported': 0.0, 'estimated': 0.0, 'subscription_equivalent': 0.0}
        unknown = 0
        known = {key: 0 for key in spending}
        wall = []
        for call in unique.values():
            value = _number(call.get('cost_usd'))
            basis = call.get('cost_basis')
            category = ('subscription_equivalent' if call.get('subscription') else
                        basis if basis in ('reported', 'estimated') else None)
            if value is None or category is None:
                unknown += 1
            else:
                spending[category] += value
                known[category] += 1
            measured = _number(call.get('wall_ms'))
            if measured is not None:
                wall.append(measured)
        amounts = {key: round(value, 6) if known[key] else None for key, value in spending.items()}
        terminal = job.get('state') in ('CLOSED', 'CANCELLED')
        elapsed = (round(max(0, times[1] - times[0]) * 1000)
                   if terminal and times[0] is not None and times[1] is not None else None)
        milestones = job.get('milestones') or {}
        retries = sum(max(0, int(step.get('attempts') or 0) - 1) for step in milestones.values())
        feedback_current = bool(feedback and feedback['subject'] == self._subject(job) and terminal)
        if feedback_current and feedback['response'] == 'useful':
            try:
                from .output_contracts import image_check
                for mid, step in milestones.items():
                    checked = image_check(self.store, job, mid)
                    if checked:
                        if checked['verdict'] != 'VERIFIED':
                            raise PolicyError('The generated image is no longer valid.')
                    else:
                        self.store.artifact_text(step['artifact'])
            except (OSError, PolicyError, UnicodeError, KeyError, TypeError):
                feedback_current = False
        return {'job_id': job['id'], 'project_id': project_id, 'state': job['state'],
                'verdict': job.get('verdict'), 'feedback': dict(feedback) if feedback else None,
                'feedback_current': feedback_current,
                'accepted_by_user': bool(feedback_current and feedback['response'] == 'useful' and job.get('verdict') == 'VERIFIED'),
                'worker_retries': retries, 'elapsed_ms': elapsed,
                'elapsed_basis': 'durable_job_events_including_waits' if elapsed is not None else 'unknown',
                'model_call_ms': round(sum(wall)) if wall else None,
                'call_count': len(unique), 'duration_unknown_calls': len(unique) - len(wall),
                'costs': {**amounts, 'unknown_calls': unknown, 'complete': bool(unique) and unknown == 0},
                'selection_changed': False,
                'why': 'Kel is collecting whole-task evidence. Model selection stays unchanged.'}

    def summary(self, project_id):
        views = []
        for job in self.store.list_jobs():
            try:
                views.append(self.view(job['id'], project_id))
            except PolicyError:
                continue
            if len(views) >= 100:
                break
        return {'project_id': project_id, 'tasks': views,
                'accepted_tasks': sum(view['accepted_by_user'] for view in views),
                'rated_tasks': sum(view['feedback'] is not None for view in views),
                'selection_changed': False,
                'comparison': 'Not established. These observations do not prove routing gains.'}
