# Increment — R3: durable retry / recovery budgets (RETRY-DURABLE)

increment_id: V16-R3-RETRY-DURABILITY
invariant: **RETRY-DURABLE** — restarting Kel, the runtime, a worker, a broker or the machine must
not restore spent automatic retry budget
requirement: `REQ-R25-R3` (roadmap R2.5 §R3; marathon directive §11)
phase: Campaign A — R3
base_commit: `fde5bbb`
production_commit: none — the inventory found every automatic retry family already durable; this
increment adds the discriminating tests and the inventory record (the honest outcome the directive
asks for when a family is already safe)
status: complete

## Inventory (code-verified, before any change)

| Automatic retry / recovery domain | Where the budget lives | Durable? | Terminal honest state | Evidence |
|---|---|---|---|---|
| Milestone attempts | `job['milestones'][mid]['attempts']` on the job row; claims cap at `max_attempts=4` (`core.py:297, 806-817`) | **yes** (job row) | `EXHAUSTED`; `reopen` refuses with 'No retryable milestones to resume' | new tests; `test_core.py` |
| TaskContract attempt ceiling | `contract.budget.attempts_max` (schema-validated 1..4, `contracts.py`) | yes (frozen contract row) | contract refuses a larger budget | `test_workforce_schemas.py` |
| Provider failure / circuit | `providers` row `data` JSON: `failures`, `circuit_until` (`core.provider_outcome`, `core.py:879-890`) | **yes** (DB row) | circuit open after 3 failures (or one auth failure for a day); a success clears it | new tests |
| Route retry | `retry_route(job_id)` persists `route.retry` and a fresh route on the job row (`core.py:908-913`; `engine.py:201`) | yes (job row + event) | job continues on the next route or the milestone exhausts | `test_engine*.py` |
| Reviewer recovery | `review_runs.attempts` (persisted); after *two* interrupted reviews the engine records an UNCERTAIN verdict with 'Review was interrupted twice; automatic review recovery is exhausted.' (`engine.py:98-161`) | **yes** (review_runs + review record) | explicit exhausted verdict, no silent loop | `test_review_recovery.py` ('recovery budget does not repeat forever') |
| Planning retry | planner failures settle the submission honestly (no unbounded loop); no automatic planner retry counter exists to restore | n/a | submission error surfaced to the user | `test_core.py` |
| Broker restart / recovery | `brokers` rows joined to runs; recovery adopts an existing result and never re-dispatches (`engine.py:50`; `coding.py:286-298`) | yes (rows) | recover-or-honest-failure | `test_broker_recovery.py` |
| Native transport recovery | receipts; 'dispatched work cannot be replayed' / 'do not replay it' (`coding_transport.py:81, 101`) | **yes** (receipts) | fail-closed with a plain sentence | `test_coding_recovery.py` |
| Coding check recovery | `recover_checked_code` / `recover_pending_checks` re-verify recorded checks (`coding.py:273-298`) | yes (records) | recovered or honest failure | `test_coding_recovery.py` |
| Mission lease recovery | `mission_leases` rows; a lapsed lease is `EXPIRED` and *reclaimed, never resurrected*; `reclaim_stale_leases` (`parallel.py:289-338, 708`) | **yes** (lease rows) | reclaimed lease; no second live holder | `test_workforce_parallel.py` |
| Stream / supervisor recovery | session state rows (`parallel.py` streams; `engine` monitor); no automatic retry counter to restore | n/a | state transition or honest stop | `test_workforce_parallel.py` |
| Restore/recovery attempts | `backup.py` restore outcome recorded durably (`restore-outcome.json` + `state()['restore']`, PER-02) | yes (record) | restore failure surfaces as boot-time status | `test_v16_restore_visibility.py` |
| Tool-level automatic retries | none exist (each tool call is one attempt; the worker/engine layer owns retries) | n/a | n/a | code read |

## Why no production change

Every automatic retry budget is already stored on the entity that owns it — the job row (milestone
attempts, route), the provider row (failure/circuit), the review record, the lease row, the receipt
or the backup record. A restart re-reads those rows, so the spent budget cannot come back. The
directive's R3.C preference ("retry state on the authoritative entity that owns the retry", "do not
create a generic retry framework") is exactly what the repository already does; adding a framework
would have been the wrong change.

## Tests added (the discriminating restart evidence R3.E asks for)

`tests/test_v16_r3_retry_durability.py` — **5 new**:

1. The milestone attempt budget survives a restart (`claim` → attempts 1; spend to 4; reopen the
   store; the next `claim` refuses and the counter still reads 4).
2. A spent budget is not restored by a second restart (two reopen cycles, still 4).
3. `reopen()` refuses once every milestone is exhausted ('No retryable milestones to resume').
4. The provider failure counter survives a restart (three failures → `failures: 3`, status
   `degraded`, circuit set).
5. Only a success clears the provider circuit (a reopened store's success resets `failures` to 0).

Focused suites green: `test_review_recovery` + `test_broker_recovery` + `test_coding_recovery` +
R3 = **24 passed**.

## Limitations / audit questions / repair hints

- Token/wallclock reservation caps still have no job-envelope primitive (carried from R1); the
  cost envelope is enforced (`reserve_budget`). R3 did not invent caps the repository does not have.
- The provider circuit is *time-based* (60 s after 3 failures; 24 h after an auth failure) — an
  audit question is whether a restart should also *extend* or *shorten* that window (it does not
  change it today, which is the conservative reading).
- Audit questions: (a) does any path reset `attempts` other than `reopen` (which only resets state,
  not the counter) and a brand-new contract? (b) is the 2-interruption review budget persisted
  across restarts (yes: review_runs.attempts + the recorded verdict)? (c) can a *new* run epoch for
  the same milestone legitimately count as a fresh attempt (yes — `claim` increments attempt and
  issues a new epoch, which is the explicit new-attempt identity the invariant allows)?
- Repair hints: none open from this increment.
