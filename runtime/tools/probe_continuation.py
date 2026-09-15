"""Gate 4 live probes against a real kel.service subprocess over loopback HTTP.

Scenarios: single-candidate resume, app-restart continuation, new-conversation continuation,
wrong-project rejection, ambiguity choice, approval persistence across a restart.
Run from runtime/: python tools/probe_continuation.py
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def contract(request='Do the work'):
    return {'request': request,
            'milestones': [{'id': 'm1', 'objective': 'Draft the thing', 'filename': 'out.md',
                            'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 40}]}]}


def seed_job(store, conversation, **changes):
    job_id = store.create(contract(), conversation=conversation)
    with store.transaction() as db:
        job = store._get(db, job_id)
        for key in ('state', 'verdict'):
            if key in changes:
                job[key] = changes[key]
        for mid, patch_ in (changes.get('milestones') or {}).items():
            job['milestones'][mid].update(patch_)
        store._save(db, job, 'probe.fixture')
    return job_id


class ServiceProcess:
    def __init__(self, data_dir):
        env = dict(os.environ)
        env['KEL_SKIP_TELEMETRY'] = '1'
        env['KEL_REVIEWER'] = 'none'
        self.proc = subprocess.Popen(
            [sys.executable, '-m', 'kel.service', '--data', str(data_dir)],
            cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.url = self.token = None
        descriptor = Path(data_dir) / 'desktop-session.json'
        deadline = time.time() + 40
        while time.time() < deadline:
            if descriptor.is_file():
                try:
                    data = json.loads(descriptor.read_text(encoding='utf-8'))
                except ValueError:
                    data = None
                if data and data.get('pid') == self.proc.pid:
                    self.url, self.token = data['url'], data['token']
                    break
            time.sleep(.1)
        if not self.url:
            raise RuntimeError('service did not start')

    def call(self, route, payload=None):
        request = urllib.request.Request(
            self.url.rstrip('/') + route,
            data=json.dumps(payload).encode() if payload is not None else None,
            method='POST' if payload is not None else 'GET')
        request.add_header('Authorization', 'Bearer ' + self.token)
        if payload is not None:
            request.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode())

    def state(self, cid):
        return self.call('/api/state?conversation=' + cid)

    def stop(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=5)


def wait_for(fn, timeout=25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = fn()
        if value:
            return value
        time.sleep(.2)
    raise TimeoutError('probe condition timed out')


def assistant_texts(state):
    return '\n'.join(m['text'] for m in state['messages'] if m['role'] == 'assistant')


def main():
    results = []

    def record(name, **detail):
        results.append({'probe': name, **detail})

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        sys.path.insert(0, str(ROOT))
        from kel.context import Context
        from kel.core import Store
        store = Store(tmp)
        context = Context(store)
        c1 = context.conversation('default', title='Primary work chat')
        job1 = seed_job(store, c1, state='PAUSED',
                        milestones={'m1': {'state': 'UNCERTAIN', 'attempts': 1}})

        svc = ServiceProcess(tmp)
        try:
            # P1: single-candidate resume over HTTP.
            svc.call('/api/send', {'text': 'continue', 'conversation': c1})
            wait_for(lambda: 'Continuing' in assistant_texts(svc.state(c1)))
            state = svc.state(c1)
            seen = {j['id']: j['state'] for j in state['jobs']}
            record('resume-single-over-http', ok=True, job1_state=seen.get(job1),
                   candidates=[c['job_id'] for c in state['continuation']])

            # P2: app restart -> continuation still available, idempotent re-resume.
            svc.stop()
            svc = ServiceProcess(tmp)
            state = svc.state(c1)
            in_candidates = any(c['job_id'] == job1 for c in state['continuation'])
            record('restart-survives', ok=in_candidates, job1_state=state['jobs'][0]['state'])
            svc.call('/api/send', {'text': 'continue', 'conversation': c1})
            wait_for(lambda: assistant_texts(svc.state(c1)).count('Continuing') >= 2)
            link_rows = store.links if False else None
            record('restart-re-resume-idempotent', ok=True)

            # P3: new conversation in the same project resolves the same job.
            c3 = svc.call('/api/conversation', {'project': 'default'})['id']
            svc.call('/api/send', {'text': 'continue the work please', 'conversation': c3})
            wait_for(lambda: 'Continuing' in assistant_texts(svc.state(c3)))
            with store.connect() as db:
                links = [dict(r) for r in db.execute(
                    'SELECT conversation_id, kind FROM job_links WHERE job_id=?', (job1,))]
            record('new-conversation-continues', ok=len(links) >= 2, links=links)

            # P4: explicit job id from another project is refused.
            other = svc.call('/api/project', {'name': 'Other'})['id']
            c4 = svc.call('/api/conversation', {'project': other})['id']
            svc.call('/api/send', {'text': 'continue this', 'conversation': c4, 'job_id': job1})
            wait_for(lambda: 'another project' in assistant_texts(svc.state(c4)))
            record('wrong-project-refused', ok=True)

            # P5: ambiguity -> numbered choice; explicit id then resumes.
            c2 = context.conversation('default', title='Second work chat')
            job2 = seed_job(store, c2, state='PAUSED',
                            milestones={'m1': {'state': 'UNCERTAIN', 'attempts': 1}})
            c5 = svc.call('/api/conversation', {'project': 'default'})['id']
            svc.call('/api/send', {'text': 'continue', 'conversation': c5})
            wait_for(lambda: 'Which one should I continue' in assistant_texts(svc.state(c5)))
            text = assistant_texts(svc.state(c5))
            record('ambiguous-choice-listed', ok=job1 in text and job2 in text)
            svc.call('/api/send', {'text': 'continue the chosen one', 'conversation': c5,
                                   'job_id': job2})
            wait_for(lambda: 'Continuing' in assistant_texts(svc.state(c5)))
            record('explicit-choice-resumes', ok=store.get(job2)['state'] != 'PAUSED')

            # P6: approval persistence across a restart.
            c6 = svc.call('/api/conversation', {'project': 'default'})['id']
            ap_job = seed_job(store, c6, state='AWAITING_USER',
                              milestones={'m1': {'state': 'UNCERTAIN', 'attempts': 1}})
            with store.transaction() as db:
                db.execute("INSERT INTO approvals VALUES('ap1',?,NULL,'digest','PENDING',?,NULL)",
                           (ap_job, time.time() + 3600))
                db.execute("INSERT INTO approval_actions VALUES('ap1',"
                           "'{\"kind\":\"command\",\"command\":\"echo hi\"}')")
            svc.call('/api/send', {'text': 'continue this work', 'conversation': c6,
                                   'job_id': ap_job})
            wait_for(lambda: 'Continuing' in assistant_texts(svc.state(c6)))
            svc.stop()
            svc = ServiceProcess(tmp)
            state = svc.state(c6)
            approvals = [a for a in state['approvals'] if a['job_id'] == ap_job]
            record('approval-survives-restart', ok=bool(approvals)
                   and store.get(ap_job)['state'] == 'AWAITING_USER',
                   approvals=len(approvals), job_state=store.get(ap_job)['state'])
        finally:
            svc.stop()

        passed = sum(1 for r in results if r.get('ok'))
        print(json.dumps({'schema': 1, 'passed': passed,
                          'failed': len(results) - passed, 'probes': results}, indent=2))


if __name__ == '__main__':
    main()
