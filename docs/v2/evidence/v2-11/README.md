# V2-11 — Long-running work 2.0 (2026-09-21)

Increment: runtime recovery, the Work brief, and the resume brief — built on the V1.6 liveness truths
and the existing engine/job/continuation paths. No second task database, no new scheduler.

## What was already true (measured, not assumed)

- The V1.6 liveness layer (R6) pins the floor: an expired run is fenced and **never auto-replayed**;
  a late result from an orphaned epoch is discarded; a dead process is reported, never completed;
  waiting is neither completion nor failure.
- `recover_expired()` existed but was reachable only from the CLI (`python -m kel recover`) and tests.
  A run killed without a durable broker stayed `RUNNING` forever until a person ran that command.
- Durable broker-backed runs are adopted and monitored across restarts by `Engine.__init__` — that
  path already worked and stays untouched.
- Continuation verbs already resolved to unfinished work (`kel/continuation.py`), and `execute_resume`
  already re-armed a fenced job — *as the person's decision*.
- `publish()` already produced the plain completion text when a job closes.

## What this increment added

| Piece | Where | What it does now |
|---|---|---|
| Runtime fencing | `Store.recover_abandoned(now=None, exclude=())` | Fences only runs **without** a broker row (nothing durable can carry them), not active in this process, with an expired lease. Same truth-preserving effect as `recover_expired` (ORPHANED + fresh epoch, milestone UNCERTAIN with the reconciliation sentence, job WAITING_RESOURCE, verdict UNCERTAIN) and the same refusal to re-arm anything. |
| The runtime call | `Engine.tick()` | Every tick fences abandoned runs, excluding the runs this engine is executing right now. A recovery failure is conservative: if the broker question cannot be answered, nothing is fenced. |
| The Work brief | `Continuation.resume_brief(job_id)` + `Service._work(cid)['work']` | Live facts per job: title, state, verdict, accepted/open counts, whether it was fenced, the full supersede-free brief — **shipped**, **open** (with states/attempts/errors), **why it stopped**, **next**, and `needs_you` (true only when no automatic step can move it). |
| The person's actions | (existing) | Fenced → “Say *continue* to re-arm it”; route-blocked → “Kel retries automatically” (not the person); AWAITING_USER / pending approvals → “Decide on the request card”; running/queued → “Nothing needed right now”; closed → done with the verdict in plain words. |

## Rules the increment pins

- **No automatic replay**: fencing re-arms nothing; continuing is only ever the person's `execute_resume`.
- **Nothing durable is fenced**: broker-backed runs are left for adoption (proved live against the real
  data root: 7 broker-backed runs survived startup, `orphaned` total stayed 0).
- **A live lease is a live run**: a fresh lease and an in-process active run are never fenced.
- **The brief never guesses**: every field comes from persisted state (the plan, the milestones, the
  error the fence itself wrote).
- **`recover_expired` semantics are unchanged**: the deliberate CLI path still fences every expired
  lease, broker-backed or not.

## Verification (on the final code of this increment)

Bounded group, one stack at a time — no monolithic run:

- `tests.test_v2_longrun` (new, 11 tests) + `test_v16_r6_liveness` + `test_v13_continuation` +
  `test_v13_continuation_service` + `test_core` + `test_review_recovery` + `test_failure_surfacing` +
  `test_v15_reliability` + `test_service_routing` → **119 OK**.
- The new suite pins: fencing + idempotence + never-READY; broker-backed runs untouched; fresh leases
  and active runs untouched; the engine tick fences; continuing re-arms and a fresh attempt starts;
  `recover_expired` unchanged; the brief for fenced / route-blocked / running / queued / done states;
  and the Work-surface payload (`needs_you` counts only person-action jobs, sorts first, and says the
  exact next step).

Live observations (engine restarted on this code, `C:\Users\Nick\KelV2Runs\prepared\engine`):

```
pre-start live runs: []
broker rows: ['3b586f1c','65f2c3c9','70db63ba','8bd582d7','904d7bf2','ad2e0819','ef3706f6']
engine pid=9656 ready=True
broker-backed runs after startup: all RESULT_RECORDED/EXITED — none ORPHANED
orphaned total: 0
work.needs_you=0 jobs=1
  job a4241bd5 state=CLOSED needs_you=False fenced=False why=Settled: uncertain.
```

The probe job is the leftover from the V2-09 live probe (killed mid-run then, settled by that engine’s
shutdown); the new Work brief reads it back in plain words on the real service. The probe engine was
stopped by its own pid after checking the listener owner; no listeners were left.
