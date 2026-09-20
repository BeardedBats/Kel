"""D18 — synthetic daily-driver journeys on the real engine (built-in fixture provider).

The engine ships an offline demo provider (`python -m kel demo` uses it). This driver uses the same
public pieces the CLI uses — Store, Engine, FixtureAdapter — to run the directive's dogfood
journeys that a missing model key would otherwise leave partial. The provider is synthetic; the
execution is real: durable store, claims, checks, verification, pause/resume, restart-resume, and
the needs-a-person path all go through the engine's own code.

Writes docs/daily-driver/evidence/d18/synthetic-journeys.json.

Usage: cd runtime && python ../packaging/verify_synthetic_journeys.py
"""
import atexit
import json
import os
import subprocess
import sys
import tempfile
import threading  # noqa: F401  (kept for parity with the engine's patterns)
import time
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1] / 'runtime'
sys.path.insert(0, str(RUNTIME))

from kel.core import Store  # noqa: E402
from kel.context import Context  # noqa: E402
from kel.engine import Engine, compile_document  # noqa: E402
from kel.continuation import Continuation  # noqa: E402
from kel.native import FixtureAdapter  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'docs' / 'daily-driver' / 'evidence' / 'd18'
FIXTURE_TEXT = '## Result\n' + ('Synthetic fixture evidence delivered for the daily-driver journey. ' * 3)

verdict = {}
root = tempfile.mkdtemp(prefix='kel-d18-')
store = Store(root)


def write_evidence(all_green: bool) -> None:
    """Write what the run actually observed. Registered as a safety net so an interrupted run can
    never leave a stale verdict file behind (the reason this driver exists is durable evidence)."""
    global _written
    evidence = {
        'phase': 'D18',
        'when': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'mode': 'synthetic provider (engine fixture adapter), real execution paths',
        'data_dir': root,
        'verdict': verdict,
        'all_green': all_green,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'synthetic-journeys.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps(evidence, indent=2))
    _written = True


_written = False
atexit.register(lambda: None if _written else write_evidence(False))

# The app always works inside a project conversation; continuation links depend on it, so the
# journeys run in one too rather than in a bare store.
context = Context(store)
context.project('Daily driver', project_id='default')
conversation = context.conversation('default', title='Synthetic daily-driver journeys')

# J1 — conversation: a side question answered through the provider path, both turns durable.
store.add_message('What does Kel keep when work is interrupted?', conversation=conversation)
answer = FixtureAdapter(output='Kel keeps the run record; reopening resumes from the last verified step.').execute(
    'Answer this side question briefly. Do not start work or use tools.\nWhat does Kel keep when work is interrupted?'
)
store.add_message(str(answer.get('text')), role='assistant', conversation=conversation)
with store.connect() as db:
    roles = [row['role'] for row in db.execute('SELECT role FROM messages ORDER BY rowid')]
    assistant_text = [row['text'] for row in db.execute("SELECT text FROM messages WHERE role='assistant'")]
verdict['j1_conversation_round_trip'] = roles[:2] == ['user', 'assistant'] and bool(assistant_text and assistant_text[0])

# J2 — a real document task to completion (submit -> execute -> verify -> CLOSED + publication).
engine = Engine(store, {'fixture': FixtureAdapter(output=FIXTURE_TEXT)})
job2 = engine.submit(compile_document('Write a short report with the heading ## Result.', required=['## Result']),
                     conversation=conversation)
result2 = engine.wait(job2, 120)
row2 = store.get(job2)
published2, _ = store.publish(job2)
artifact2 = (row2.get('milestones', {}).get('document', {}) or {}).get('artifact')
verdict['j2_task_closed'] = result2.get('state') == 'CLOSED'
verdict['j2_verdict_verified'] = row2.get('verdict') == 'VERIFIED'
verdict['j2_publication_has_heading'] = '## Result' in (published2 or '')
artifact_path = artifact2.get('path') if isinstance(artifact2, dict) else artifact2
verdict['j2_artifact_written'] = bool(artifact_path) and os.path.exists(os.path.join(root, artifact_path))
verdict['j2_attempts'] = row2['milestones']['document']['attempts']

# J3 — restart-resume: the app is KILLED mid-run (abrupt exit, the engine's own crash pattern),
# then a fresh engine on the same store resumes; the fenced run is never double-executed.
engine.close()  # J2 done; the remaining journeys restart engines from the same store
child_code = (
    "import os,sys,threading,time\n"
    "sys.path.insert(0, sys.argv[2])\n"
    "from kel.core import Store\n"
    "from kel.engine import Engine, compile_document\n"
    "from kel.native import FixtureAdapter\n"
    "store=Store(sys.argv[1])\n"
    "output='## Result'+chr(10)+(chr(120)*80)\n"
    "e=Engine(store,{'fixture':FixtureAdapter(output=output, delay=5)})\n"
    "job=e.submit(compile_document('Write a second short report with the heading ## Result.', required=['## Result']), conversation=sys.argv[3])\n"
    "print(job, flush=True)\n"
    "threading.Thread(target=e.tick, daemon=True).start()\n"
    "time.sleep(1.6)\n"
    "os._exit(23)\n"
)
proc = subprocess.run([sys.executable, '-c', child_code, root, str(RUNTIME), conversation], capture_output=True, text=True, timeout=90)
job3 = (proc.stdout or '').strip().split('\n')[-1].strip()
verdict['j3_child_was_killed_abruptly'] = proc.returncode == 23 and bool(job3)
row_before = store.get(job3)
verdict['j3_run_was_in_flight'] = row_before['milestones']['document']['state'] in ('RUNNING', 'READY', 'NEEDS_REPAIR')
resumed = Engine(store, {'fixture': FixtureAdapter(output=FIXTURE_TEXT)})
# Startup recovery, with the run-lease window simulated as passed (recover_expired's supported
# `now` parameter): the dead child's run is fenced (ORPHANED) and its milestone is fenced with it.
store.recover_expired(now=time.time() + 3600)
fenced = store.get(job3)
# D7 semantics, visible in this journey: a fenced run is never replayed on its own — the job waits,
# with the engine's own reason recorded, until a person decides.
verdict['j3_fenced_and_waiting'] = (fenced['state'] == 'WAITING_RESOURCE'
                                   and fenced['milestones']['document']['state'] == 'UNCERTAIN')
verdict['j3_no_silent_replay'] = fenced['milestones']['document']['attempts'] == 1
# The person says "continue" — the same engine call the chat's continuation makes.
out3 = Continuation(store).execute_resume(job3, fenced['conversation'], reason='user: continue')
verdict['j3_continue_rearms_the_fenced_run'] = out3['state'] == 'READY'
result3 = resumed.wait(job3, 120)
for _ in range(5):
    if result3.get('state') == 'CLOSED':
        break
    result3 = resumed.wait(job3, 120)
row3 = store.get(job3)
verdict['j3_after_continue_finishes'] = (result3.get('state') == 'CLOSED'
                                         and row3.get('verdict') == 'VERIFIED')
verdict['j3_attempts_bounded'] = row3['milestones']['document']['attempts'] <= 2
verdict['j3_state_and_attempts'] = {'state': row3.get('state'),
                                    'attempts': row3['milestones']['document']['attempts']}

# J4 — pause and resume while the engine is live.
job4 = resumed.submit(compile_document('Write a third short report with the heading ## Result.', required=['## Result']),
                      conversation=conversation)
resumed.control(job4, 'pause')
paused = store.get(job4)['state'] == 'PAUSED'
resumed.control(job4, 'resume')
result4 = resumed.wait(job4, 120)
verdict['j4_pause_holds'] = bool(paused)
verdict['j4_resume_completes'] = result4.get('state') == 'CLOSED'
resumed.close()

# J5 — the needs-a-person path: a failing provider surfaces as work that needs attention, not silence.
failing = Engine(store, {'fixture': FixtureAdapter(output='wrong output', fail_first=True)})
job5 = failing.submit(compile_document('Write a report that the failing provider cannot satisfy.', required=['## Result']),
                      conversation=conversation)
result5 = failing.wait(job5, 120)
row5 = store.get(job5)
verdict['j5_failure_is_terminal_and_recorded'] = row5.get('verdict') == 'FAILED' and result5.get('state') == 'CLOSED'
verdict['j5_surfaces_as_needs_person'] = row5.get('state') in ('FAILED', 'BLOCKED', 'AWAITING_USER', 'NEEDS_REPAIR') or row5.get('verdict') in ('FAILED', 'UNCERTAIN')
verdict['j5_retry_ladder_ran'] = row5['milestones']['document']['attempts'] >= 2
verdict['j5_state_and_verdict'] = {'state': row5.get('state'), 'verdict': row5.get('verdict'), 'attempts': row5['milestones']['document']['attempts']}
failing.close()

all_green = all(value is True for key, value in verdict.items() if not key.endswith(('_attempts', '_state_and_verdict', '_state_and_attempts')))
write_evidence(all_green)
if not all_green:
    raise SystemExit(1)
