# Increment — R6: truthful runtime state + liveness (LIVENESS-SEPARATION · COMPLETION-TRUTH · RECOVERY-CLASSIFICATION)

increment_id: V16-R6-TRUTHFUL-STATE
invariants: **LIVENESS-SEPARATION** (process liveness, execution liveness and mission progress are
separate facts), **COMPLETION-TRUTH** (completion requires an evidence-backed assessment),
**RECOVERY-CLASSIFICATION** (interrupted work resolves to safely resumable / safely retryable /
reconcile-first / user-blocked / failed)
requirement: `REQ-R25-R6` (roadmap R2.5 §R6; marathon directive §14)
phase: Campaign A — R6
base_commit: `b2ffed1`
production_commit: none — the layers and invariants were verified in code; the increment adds the
discriminating tests and this inventory (the honest outcome when the design is already truthful)
status: complete

## The three layers (what the repository actually models)

| Layer | Facts | Where they live | Never implies |
|---|---|---|---|
| Process liveness | does the process exist; does the recorded PID still match its identity; native child alive; past deadline | `native_processes(run_id, pid, identity, stdout_path, deadline)` (created by `kel/runner.py:46`), observed by `diagnostics._pid_alive` + `snapshot()['processes']`; `native_group`/`coding_transport` process handles | completion, retryability, or a stalled *mission* |
| Execution / supervisor liveness | controller lease, broker alive, heartbeat, run inside its fence, mission lease valid, transport alive, provider usable | `runs.state` + `runs.expires` + `runs.epoch`; `brokers`; `mission_leases` (+ heartbeats, `reclaim_stale_leases`); `capability_leases`; provider `circuit_until`/`quota`; `coding_transport` receipts | completion; a lapsed lease is *reclaimed*, never resurrected (`parallel.py`) |
| Mission progress | meaningful transition, milestone advanced, evidence emitted, assignment activity, legitimately waiting | `jobs(data).state` + `milestones[].state` + `verdict`; `runs.state`; `inbox.handled`; `review_runs`; `workforce_messages`/`findings` | completion without the evidence-backed assessment (job CLOSED only via `close` with a verified assessment) |

## Required invariants — verified in code

| Invariant | Code evidence |
|---|---|
| `process_alive != mission_progressing` | a live PID with no inbox/event activity changes nothing (`snapshot` reports; no state writer reads liveness) |
| `process_dead != automatically safe_to_retry` | a dead process is reported (`'N recorded process(es) are no longer alive'`) and nothing else; a run past its fence is **ORPHANED with a fresh epoch** and the milestone goes **UNCERTAIN** with 'Expired run; native state requires reconciliation' (reconcile-first) |
| `idle != completed` | only `close(...)` with the evidence-backed assessment sets CLOSED; idle states leave the milestone untouched |
| `waiting != completed` / `waiting != failed` | `AWAITING_USER` / `WAITING_RESOURCE` / `WAITING_APPROVAL` are distinct job/milestone states with their own verdicts; `waiting` never writes COMPLETE or FAILED |
| `no_new_event != automatically stalled` | `recover_expired` acts on `expires`, not on event silence; the pod stall detector reads lease/heartbeat state, not quiet |
| `completion == evidence-backed assessment` | job closure path verifies the milestone checks and the assessment; reviews/assurance gate independent certification (INV-AUDIT-001) |

## Tests added

`tests/test_v16_r6_liveness.py` — **5 new**:

1. An expired run is ORPHANED in a fresh epoch, the milestone is UNCERTAIN with the reconciliation
   sentence, the job is `WAITING_RESOURCE`/`UNCERTAIN`, and nothing retries it automatically.
2. A late result from the orphaned epoch is discarded by `consume()` — the job stays UNCERTAIN (the
   fence, not the delivery, is authoritative).
3. No new events alone never orphans a live run (`recover_expired` before the fence does nothing).
4. A dead recorded native process is reported in `database.problems` and never completes work.
5. Waiting (`AWAITING_USER` after an approval request) is neither completion nor failure.

Focused: R6 suite 5 passed (diagnostics + core families green in the full runs A-24/A-25).

## Limitations / audit questions / repair hints

- The Compact derived health status (progressing / waiting-for-user / recovering / stalled / lost /
  reconciling / completed / failed) was **not** added here: R9.D's "Needs Your Attention" is the
  product surface that consumes these facts, and deriving it twice would create competing state.
  Recorded as a binding rather than duplicated work.
- `snapshot()` reports but never *acts* — by design; the acting paths are `recover_expired`,
  `reclaim_stale_leases`, the monitor and `orphan` handling.
- Audit questions: (a) does any UI surface show raw `runs.state` without the milestone/job context
  (would read as "completed" for a paused job)? (b) is `expires` always set before a run can be
  observed (claim sets it; an externally inserted row is the only way to miss it)? (c) does the pod
  stall detector have a test for a *legitimately long* operation (yes: `test_workforce_parallel`).
- Repair hints: none open from this increment.
