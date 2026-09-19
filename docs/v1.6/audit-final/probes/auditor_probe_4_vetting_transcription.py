"""Campaign B auditor probe #4 - transcription + vetting batteries (read-only on product code).
Run: cd runtime && python ../docs/v1.6/audit-final/probes/auditor_probe_4_vetting_transcription.py
"""
import base64
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))

from kel.core import Store, PolicyError  # noqa: E402
from kel.context import Context  # noqa: E402
from kel.service import Service  # noqa: E402
from kel.transcription import Transcription  # noqa: E402


def log(s):
    print(s, flush=True)


def section(t):
    log('\n== %s ==' % t)


def attempt(label, fn):
    try:
        r = fn()
        log('RESULT %s -> NO ERROR (%r)' % (label, r if not isinstance(r, dict) else {k: r.get(k) for k in list(r)[:7]}))
        return r
    except PolicyError as e:
        log('RESULT %s -> PolicyError: %s' % (label, str(e)[:170]))
    except Exception as e:
        log('RESULT %s -> %s: %s' % (label, type(e).__name__, str(e)[:170]))


tmp = tempfile.TemporaryDirectory()
svc = Service(str(Path(tmp.name) / 'kel.sqlite3'))
ctx = Context(svc.store)
p1 = ctx.project('P1', project_id='p1')
p2 = ctx.project('P2', project_id='p2')
c1 = ctx.conversation('p1')
c2 = ctx.conversation('p2')

# ---------------- V. vetting session ownership ----------------
section('V. vetting session ownership (SEC-01 through the service layer)')
started = attempt('V1 start session in c1', lambda: svc._vetting_action({'conversation': c1, 'action': 'start', 'topic': 'audit topic'}))
sid = None
if isinstance(started, dict):
    sid = started.get('session') or started.get('session_id') or (started.get('panel') or {}).get('session')
    log('V1b session id: %r (keys=%r)' % (sid, list(started)[:12]))
if not sid:
    log('V1c falling back to active() to discover the session id')
    try:
        from kel.vetting_session import Vetting
        v = Vetting(svc.store, conversation=c1)
        sid = v.active() if hasattr(v, 'active') else None
        log('V1d active() -> %r' % (sid,))
    except Exception as e:
        log('V1d failed: %s: %s' % (type(e).__name__, str(e)[:140]))

if sid:
    attempt('V2a foreign conversation ingests into c1 session', lambda: svc._vetting_action({'conversation': c2, 'action': 'ingest', 'session': sid, 'text': 'audit foreign ingest'}))
    attempt('V2b foreign conversation processes c1 session', lambda: svc._vetting_action({'conversation': c2, 'action': 'process', 'session': sid}))
    attempt('V2c foreign conversation finishes c1 session', lambda: svc._vetting_action({'conversation': c2, 'action': 'finish', 'session': sid}))
    attempt('V2d foreign conversation panels c1 session', lambda: svc._vetting_action({'conversation': c2, 'action': 'panel', 'session': sid}))
    attempt('V3 same conversation process works (control)', lambda: svc._vetting_action({'conversation': c1, 'action': 'process', 'session': sid}))
    attempt('V4 unknown session id from c1', lambda: svc._vetting_action({'conversation': c1, 'action': 'process', 'session': 'vs-does-not-exist'}))
else:
    log('V2-V4 skipped: no session id discovered')

attempt('V5 missing session field sentence', lambda: svc._vetting_action({'conversation': c1, 'action': 'process'}))
attempt('V6 omitted conversation defaults to main', lambda: svc._vetting_action({'action': 'panel'}))
log('V7 panel(c2) session ids: %r' % (
    [s.get('id') or s.get('session') for s in ((svc._vetting_action({'conversation': c2, 'action': 'panel'}) or {}).get('sessions') or [])][:6]
    if isinstance(svc._vetting_action({'conversation': c2, 'action': 'panel'}), dict) else 'n/a'))

# ---------------- T. transcription stream lifecycle (TR-01) ----------------
section('T. transcription stream lifecycle (TR-01)')
t = Transcription(svc.store)


class _FakeStream:
    def __init__(self):
        self.closed = 0
        self.finished = 0
        self.audio_ms = 1000

    def feed(self, data):
        return None

    def status(self):
        return {'text': '', 'state': 'live', 'error': ''}

    def finish(self):
        self.finished += 1
        return {'text': 'done', 'final': True}

    def close(self):
        self.closed += 1


def install(sid, age, conversation='main'):
    h = _FakeStream()
    t._streams[sid] = {'handle': h, 'provider': 'fixture', 'started': time.time() - age, 'conversation': conversation}
    return h


stale = install('audit-fake-stale', age=3 * 60 * 60)
fresh = install('audit-fake-fresh', age=0)
t._gc_streams()
log('T1 reaped stale: closed=%d removed=%r ; fresh kept=%r closed=%d' % (
    stale.closed, 'audit-fake-stale' not in t._streams, 'audit-fake-fresh' in t._streams, fresh.closed))

h2 = install('audit-fake-finish', age=0)
fin = attempt('T2 stream_finish releases handle', lambda: t.stream_finish('audit-fake-finish'))
log('T3 finish: finished=%d closed=%d removed=%r' % (h2.finished, h2.closed, 'audit-fake-finish' not in t._streams))

install('audit-fake-scope', age=0, conversation='main')
attempt('T4 foreign-declared chunk refused', lambda: t.stream_chunk('audit-fake-scope', base64.b64encode(b'\x00\x00' * 8).decode(), conversation='elsewhere'))
attempt('T5 foreign-declared status refused', lambda: t.stream_status('audit-fake-scope', conversation='elsewhere'))
attempt('T6 foreign-declared finish refused', lambda: t.stream_finish('audit-fake-scope', conversation='elsewhere'))
attempt('T7 undeclared chunk still accepted (documented additive)', lambda: t.stream_chunk('audit-fake-scope', base64.b64encode(b'\x00\x00' * 8).decode()))
attempt('T8 unknown stream sentence', lambda: t.stream_chunk('ts-missing', base64.b64encode(b'\x00\x00').decode()))

section('U. transcription service actions')
attempt('U1 library', lambda: svc._transcription_action({'action': 'library'}) and 'ok')
attempt('U2 unknown action', lambda: svc._transcription_action({'action': 'explode'}))
attempt('U3 status mode', lambda: {k: svc._transcription_action({'action': 'status'}).get(k) for k in ('mode', 'has_key', 'label')})

log('\nPROBE-4-END')
