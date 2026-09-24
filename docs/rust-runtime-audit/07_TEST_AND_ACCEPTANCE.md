# 07 — Test and acceptance criteria

The charter requires that any `MOVE_TO_RUST_NOW` name measurable acceptance criteria, and forbids
abstract benefit claims. **This audit makes no `MOVE_TO_RUST_NOW` recommendation**, so this document
serves two purposes:

1. **`A` — acceptance criteria for the recommended work** (`05` Plan A), which must pass to be
   called done.
2. **`T` — re-open triggers and acceptance criteria for the conditional native edge**, which are
   **inert** unless a trigger fires.

Every criterion below is written so it can be measured with tooling that already exists, or with
tooling `A4` adds.

---

## Part A — acceptance for the recommended work

### A1 — engine reuse is version-validated *(closes E7)*

| # | Criterion | How it is measured |
|---|---|---|
| A1.1 | Reuse happens **only** when `descriptor.engine_version` equals this build's expected engine version | unit test on the pure `reuse \| restart` decision function: matching, mismatching, absent, malformed |
| A1.2 | On mismatch the stale engine is stopped within a bounded window, then a fresh engine is spawned and becomes ready | packaged scenario: start build N, leave the engine detached, replace the engine artifact with build N+1, relaunch, assert the running engine reports N+1 |
| A1.3 | A stale engine is never terminated by bare PID | code review + test: termination path resolves an identity (creation time / handle), reusing the existing `process_identity` approach |
| A1.4 | `desktop-session.json` written by an unrelated process is not trusted | unit test: descriptor pointing at a foreign host or a live non-Kel port is rejected, not reused |
| A1.5 | Reuse still happens in the normal case, with no added boot latency | packaged smoke unchanged: `engineStopped: true`, `appExited: true`, `errors: []` |

**Exit metric:** zero scenarios in which a new build runs against an engine binary from an older
build. That is the whole point of A1 and it is binary, not statistical.

### A2 — restore failure is never silent

| # | Criterion | How it is measured |
|---|---|---|
| A2.1 | A failing `apply_pending_restore` leaves the pending marker in place | unit test: inject a failure, assert marker survives |
| A2.2 | The failure is recorded durably with its exception type | inspect the store after the injected failure |
| A2.3 | The next Work/Diagnostics read surfaces exactly one plain sentence naming the outcome | test asserting the user-visible string; no exception type, path, or stack trace in it |
| A2.4 | The staging design is unchanged — a failed restore still cannot half-apply | existing `test_backup.py` restore assertions still pass |

### A3 — shutdown handshake is measured, not assumed

| # | Criterion | How it is measured |
|---|---|---|
| A3.1 | Each packaged scenario records **which** path it took: clean drain vs forced kill | harness output field, asserted present |
| A3.2 | Zero scenarios report a forced kill in a run where no scenario overran its grace period | packaged battery report |
| A3.3 | The engine's own terminal state is asserted **before** any kill is attempted | harness assertion ordering |
| A3.4 | If a forced kill occurs, the reason is recorded with the elapsed time past the grace deadline | harness output |

**Honest note:** A3 does not promise zero forced kills. It promises that a forced kill is *visible
and attributed* rather than silently absorbed. Given the evidence in `02` E6, that is the defensible
target.

### A4 — footprint instrumentation exists

| # | Criterion | How it is measured |
|---|---|---|
| A4.1 | Working set and CPU are recorded for the daemon and for each worker run | new fields in `process_observations` / `startup_spans` |
| A4.2 | They are visible on the existing Diagnostics page, with units and a clear basis | page inspection |
| A4.3 | Retention follows the existing windows; no new unbounded table | retention test |
| A4.4 | The sanitized issue-report export still contains no credentials, paths or prompts | existing export assertions |

**This is the prerequisite for ever arguing Rust on footprint.** Without A4.1, any such argument is
opinion.

### A5 — freeze tooling produces exact candidate↔frozen identity

| # | Criterion | How it is measured |
|---|---|---|
| A5.1 | `freeze-release.ps1` does not emit a nested `resources/kel-engine/kel-engine/` | inspect the frozen tree |
| A5.2 | The freeze verifies 3/3 without a manual post-assembly cleanup step | `scripts/verify-release.ps1` at the frozen location |
| A5.3 | No frozen release from V1–V1.5 or `v1.6.0-pre1` is modified by any of this work | git: frozen paths untouched; hashes unchanged |

### Plan A regression gate

Plan A must not reduce current coverage:

- engine suite: **≥ 592 tests collected**, all passing (matches the `ffeef73` baseline);
- desktop typecheck: **0 errors**;
- desktop unit tests: **76 passing** (login/onboarding suites);
- packaged battery on the current candidate: 0 scenario errors and 0 console errors, as on
  `package-final16`.

---

## Part B — re-open triggers for the native edge (`TARGET-2`)

**None of these has fired.** Until one does, `TARGET-2` stays unbuilt. These are the only grounds on
which the audit would revisit its verdict.

| Trigger | Threshold | Why this number |
|---|---|---|
| **T1 — worker spawn cost becomes material** | measured median worker-run startup exceeds **10%** of the shortest provider timeout for that job class (shortest class timeout in the code is 190 s, so ≈ **19 s**) | below 10% the spawn cost is invisible against the work itself; there is no measurement of this today, so `A4` must land first |
| **T2 — stale-runtime escapes A1** | after `A1` ships, **any** observed instance of a new build driving an old engine, or of a user dead-ended on "Kel engine did not start" with a live but unresponsive engine | A1 is the cheap fix; if it provably fails, supervision moves up the list |
| **T3 — forced-kill rate is structural** | after `A3` ships, forced kill required in **>5%** of packaged scenarios across two consecutive full batteries, with the cause traced to engine-side drain rather than harness timing | distinguishes a real lifecycle defect from a harness measurement artifact |
| **T4 — process count causes observable harm** | a reproducible, user-visible failure attributable to process count (not to a specific bug) | process count alone is not harm; the current tree is wide but the packaged battery is green |
| **T5 — footprint is materially worse than an equivalent native shell** | `A4` data shows daemon + workers consuming a working set that materially degrades a stated product requirement on the supported minimum hardware | requires a stated requirement and `A4` data; neither exists today |

### Acceptance criteria, if a trigger fires and `TARGET-2` is built

| # | Criterion | How it is measured |
|---|---|---|
| T-1 | Supervisor implements exactly four verbs: `spawn`, `stop`, `status`, `version-handshake` | interface review; no other exported surface |
| T-2 | Supervisor never opens `kel.sqlite3` | dependency/code check |
| T-3 | **Deletion test:** removing the supervisor restores the TypeScript implementation with a diff confined to the supervisor module | revert and inspect the diff |
| T-4 | Engine Python source is byte-identical before and after the swap | diff `runtime/kel/**` |
| T-5 | Engine suite unchanged and green (≥ 592 passing) | `python -m pytest tests -q` |
| T-6 | Packaged battery: 0 scenario errors, 0 console errors; `engineStopped: true` and `appExited: true` | same harness, same thresholds as today |
| T-7 | Stale-runtime scenarios from A1.2 still pass | packaged scenario |
| T-8 | Rollback rehearsed before ship, not after | recorded rehearsal with elapsed time |

**T-3 and T-4 are the load-bearing criteria.** They are what stop `TARGET-2` from quietly becoming
the migration this audit declines to recommend.

---

## What would NOT count as acceptance evidence

Recorded so nobody can argue a benefit abstractly:

- "Rust is faster" without an `A4` measurement and a T1/T5 comparison against a defined threshold.
- "It feels more robust" — not measurable.
- A microbenchmark of a rewritten hot loop that does not exist at `ffeef73`. The measured hot path
  is an authorization decision at ~30 ms, **~30 ms of which is a deliberate fsync'd audit row**,
  not interpreter overhead.
- "Fewer processes" on its own. Process count is not a user-visible requirement; T4 exists to force
  that distinction.
- Any criterion that requires changing engine state logic to observe. If the test needs the engine to
  change, the boundary is already wrong.
