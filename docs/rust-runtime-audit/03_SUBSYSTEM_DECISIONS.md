# 03 — Subsystem decisions

Every candidate area from the audit charter, classified, with the evidence that decided it.

Classification vocabulary (exactly as chartered): `KEEP_IN_PYTHON` · `MOVE_TO_RUST_NOW` ·
`MOVE_TO_RUST_LATER` · `ALREADY_NATIVE` · `NOT_APPLICABLE`.

**`MOVE_TO_RUST_NOW` is used zero times.** That is the verdict, not an omission.

---

## Process supervision

**`KEEP_IN_PYTHON`** — with one protocol gap (`TARGET-1`, see below).

The supervision machinery is real and works: a Win32 Job Object with kill-on-close for Windows
(`windows_job.py`), a cgroup with memory and PID caps for Linux (`native_group.py`), Win32 process
creation time as a non-reusable worker identity (`runner.py:19-38`, defending against PID reuse),
epochs and fencing on every run, and durable recovery that adopts `RUNNING` /
`WAITING_APPROVAL` / `CANCEL_REQUESTED` runs at startup with `UPDATE review_runs SET
status='INTERRUPTED'` (`engine.py:44-56`).

Rust would give a single static binary and a faster spawn. Neither is measured as a problem: worker
spawn cost is unmeasured but sits against provider call timeouts of 190 s and 420 s
(`engine.py:189`), where a sub-second boot is noise. The one real supervision defect (`E6`) is
measured by a test harness, and its architectural half (`E7`) is a validation gap, not a supervision
engine problem.

## Application startup / shutdown

**`KEEP_IN_PYTHON`**.

Startup: `engine-start` spans of 93–113 ms typical against a 45 s boot ceiling. There is no
bottleneck here for Rust to remove (see `01` §4). Shutdown: automated shutdown is green —
`docs/v1.6/00_CHECKPOINT_FREEZE.md` records packaged smoke `engineStopped: true`, `appExited: true`,
`errors: []`, re-checked from the frozen folder itself. The friction that does exist is on the
harness close path (`E6`) and in file-handle retention (`E3`, `E4`), both already fixed in Python.

## Engine supervision

**`KEEP_IN_PYTHON`**.

`Service` runs a supervisor thread ticking the engine every 200 ms (`service.py:129-133`), a
`ThreadPoolExecutor` bounded by SQLite-enforced global concurrency of 2 (`core.py:271-273`:
`SELECT count(*) FROM runs WHERE state IN (...) >= 2` → `PolicyError('Global worker concurrency
limit reached')`), and a separate single-thread review pool. Supervision state is durable, so a
supervisor restart re-derives everything from rows rather than from memory. This is the design that
makes crash recovery work; it is not a performance component.

## Process cleanup

**`KEEP_IN_PYTHON`** — `ALREADY_NATIVE` underneath.

Job Object on Windows and cgroup on Linux are already kernel-enforced; Python only makes the call.
`InstanceLock` is a genuine kernel lock (`msvcrt.locking` / `flock`) with no timeout, so a killed
process releases ownership immediately — `test_startup.py`:
`test_abrupt_exit_releases_kernel_lock_immediately`. There is no PID-file staleness class here to
eliminate.

## Crash recovery

**`KEEP_IN_PYTHON`**.

This is the most heavily tested subsystem in the product and the reason the ceiling on any migration
recommendation should be low. At V1.5 the reliability review mapped 22 charter cases to named tests,
including `test_broker_recovery`, `test_coding_recovery`, `test_isolated_recovery`,
`test_review_recovery`, `test_failure_surfacing`, and `test_apply_changes` —
`test_crash_after_first_replace_resumes_without_repeating_it`,
`test_crash_before_replace_recovers_staging_file`. Suite size is now 592 collected tests across
8,929 LOC of tests. **This is the trust core. A rewrite is the single highest-risk change available
to the program and removes no measured pain.**

## SQLite ownership

**`KEEP_IN_PYTHON`**.

Per premise **P1**: identical C library either side. More important, ownership is *already split and
documented* — engine state in `kel.sqlite3` owned by `Store`, host state in a second better-sqlite3
database owned by Electron main, with `legacyHandoffContract.ts` and
`repairLegacyHandoffSchema.ts` formalising the seam. There is no ownership race to fix; there is a
deliberate boundary. Rust in the middle would add a third writer, not remove one.

## SQLite WAL coordination

**`KEEP_IN_PYTHON`**.

`E5` is the one genuinely nasty Windows behaviour in the codebase: a killed process can briefly
retain a WAL mapping, surfacing as `disk I/O error` on the *next* open. The current handling is a
bounded, well-commented retry in `connect()` — 11 attempts, 100 ms apart, and only around opening a
connection, before any application transaction is submitted. **This constraint is inherited by any
language.** `rusqlite` opening the same file on the same Windows build meets the same mapping
retention. Moving to Rust does not delete this code; it re-implements it.

## Live backup / restore coordination

**`KEEP_IN_PYTHON`** — the defect here (`E2`, F12) is already fixed, in Python.

Worth being explicit about what the fix actually was, because it reads like an argument for Rust and
isn't. "Back up now" failed with `WinError 32` on `controller.lock` and on Chromium's
`host/Network/Cookies`. The root cause was **a policy error: the backup copied files the running app
holds open.** The fix was to stop copying runtime state, hot-copy databases through SQLite's own
backup API, and *name* anything still unreadable in `skipped`/`notes` instead of failing the whole
copy (`backup.py:20-33, 72-81, 140-190`). No amount of Rust changes which files a backup chooses to
copy. The design that emerged — staged restore applied at next engine start, previous data kept
beside it as `.pre-restore-*` — is good and should be preserved regardless of language.

## Concurrency-sensitive persistence

**`KEEP_IN_PYTHON`**.

`BEGIN IMMEDIATE` + `busy_timeout` + `synchronous=FULL` + `secure_delete=ON`, with the lock
contention behaviour **probed, not assumed**: `test_v15_reliability.py` ·
`test_write_waits_for_a_competing_writer_then_succeeds` and
`test_a_held_lock_surfaces_a_clean_bounded_error_then_recovers` (wait, bounded 10 s failure, clean
error, recovery, integrity `ok`). Real concurrency is bounded at 2 workers so contention is
structurally low. Same C library, same answers, in Rust.

## Authorization runtime

**`KEEP_IN_PYTHON`** — and this is the recommendation to defend hardest.

`authorize.py` is a decision engine (`Authorizer._decide`, `_lease_by_id`, `_approval_ok`,
`_expansion`, `_record`) with a versioned policy identity (`kel-authz-1.5`), durable
`guardrail_decisions` receipts, and — critically — enforcement at the **effect point**, not at the
gate: the comment at the coding call site says the per-tool role policy is enforced where each of
git/run_tests/write is checked against the frozen role snapshot. Actor identity is bound by the
authenticated session and payload-supplied identity is **rejected**
(`service.py::_action`: `'Actor identity comes from the authenticated Kel session, not from the
request payload'`).

Measured cost is ~30 ms per decision, and the docs are honest that this is deliberate: fsync'd
audit rows. Rust would make that *faster in a way nobody asked for* while putting a rewrite of the
authorization core on the critical path of a release. **Wrong trade at any time; unthinkable before
a freeze.**

## Leases

**`KEEP_IN_PYTHON`**. Leases live in SQLite, are bound to a compiled contract digest
(`review_ref='kel-contract:' + digest(contract)`), are issued only for eligible roots, and ineligible
roots "stay unleased and therefore fail closed" (`core.py:281-292`). Failure direction is correct.
Not a language question.

## Approvals

**`KEEP_IN_PYTHON`**. V1.6 Phase 3 shipped in-chat approvals at `ffeef73` with anchors in
`approval_announcements` and a documented rule that chat resolution must always delegate to
`Autonomy.resolve_expansion` / `Store.resolve_approval` — one durable record, two surfaces. This is
active, freshly-verified work. Moving the approval runtime to Rust would mean rewriting the exact
feature that was verified days ago.

## Provider health

**`KEEP_IN_PYTHON`**. Circuit breaker with `circuit_until`, quota, latency and quality in
`providers.py`; health survives restart (`test_provider_health_survives_restart`); degraded and
absent providers are named in plain language at the surface. Pure logic over rows.

## Reconnect / event handling

**`KEEP_IN_PYTHON`**. Reconnect is handled by *reconciliation*, not by a persistent socket: the ACP
stream is not trusted to stay up. `emit`s `kel/connectionClosed` on stream end
(`appserver.py:65`), and `KelService.reconcile()` re-projects engine verdicts onto stale donor
`acp_tool_call` rows (CLOSED→completed/failed, CANCELLED→failed, PAUSED/AWAITING_USER/
WAITING_RESOURCE→pending) so a disconnected stream cannot leave a permanently "in progress" row. The
recovery model is durable-state-first; that is the right shape and it does not depend on language.

## IPC

**`KEEP_IN_PYTHON`**. Three transports, all boring on purpose: loopback HTTP + bearer token for the
daemon, stdio JSON-RPC for providers, `ipcMain.handle` behind a route allowlist regex for the
renderer. Cost is negligible and the observed failures (`E8` envelope leak, `E9` providers contract)
were **contract and impedance bugs**, not throughput problems. Rust does not fix a missing field in a
JSON payload.

## Electron ↔ engine boundary

**`KEEP_IN_PYTHON`** — with `TARGET-1` as the one genuine gap.

The boundary is a descriptor file plus a loopback HTTP call. It is defensive already: the URL must
be `http:` and `127.0.0.1` or the request is refused; the renderer route is allowlisted; artifact
reveal resolves against the engine root and refuses escapes. The lifecycle around it is careful — the
`before-quit` drain hook is registered *first*, before anything that can fail, with the comment that
this is so "a failed startup never orphans KelEngine", and the drain blocks quit briefly so the HTTP
drain cannot race process exit.

And then the hole: **`Descriptor` declares `engine_version`, and the reuse path never checks it.**

## Native OS integration

**`ALREADY_NATIVE`**. Win32 Job Object, process creation time, DPAPI, cgroup, `shell.showItemInFolder`,
`powerSaveBlocker`. All already reach the OS. The Python `ctypes` boundary is the only non-native
part, and it is small, contained, and proven.

## Power management

**`ALREADY_NATIVE`**. `powerSaveBlocker.start('prevent-app-suspension')` via Electron
(`keepAwake.ts`). The module's own reasoning is the correct design and worth preserving: the blocker
id lives in the process, so quitting *or crashing* releases the inhibition — "there is no on-disk
state that could leave a machine awake after Kel is gone." The donor-derived keep-awake pass is
recorded green in the frozen checkpoint (full cycle Off → Active → restart → Active → disable → Off).

## Credential boundary

**`ALREADY_NATIVE` / `KEEP_IN_TS`**. Electron `safeStorage` → DPAPI on Windows, main process only;
values injected into the engine child's environment at spawn; never in the renderer, the engine
database, exports or logs; native children strip them again (`native.py::child_env` also refuses to
forward one provider's key to the other provider's child). The honest limitation is documented: new
or changed credentials apply at the next engine start. **Rust cannot improve on the OS key store.**

## Filesystem / native helpers

**`KEEP_IN_PYTHON`**. `backup.py`, `migration.py`, `projectmap.py` (git), `wsl_runtime.py`.
The pain here is Windows file-handle semantics (`E2`, `E3`, `E4`), which is an OS constraint
encountered identically from any language.

## Packaging / native binary behaviour

**`KEEP_IN_PYTHON`** — with real, honestly-recorded friction that is *tooling*, not architecture.

The genuine issues: `freeze-release.ps1` nests an inert duplicate at
`resources/kel-engine/kel-engine/` and the V1.6.0-pre1 freeze had to strip it by hand ("or fix
`freeze-release.ps1` first"); the engine must be staged into a space-free data directory because
AionCore validates the ACP agent's CLI by whitespace-splitting `binary_name` and reports
`cli_not_found` on any spaced path; and a lingering host handle held `app.asar`, producing an EBUSY
that electron-builder could not replace in place (identified with the Windows Restart Manager).

None of those are Python's fault, and the PyInstaller burden is unusually *small* here because the
dependency surface is one library (`01` §5). Fixing the freeze script and the path staging is
ordinary work with known shapes.

## Not applicable

**`NOT_APPLICABLE`**: `browser` and `external` action kinds have no calling runtime today, and
`no-screen-takeover` / `firefox-only` remain checker-level rules with no synthesizing action family.
There is nothing to port.

---

## Where the whole thing lands

| Decision | Count | Subsystems |
|---|---|---|
| `ALREADY_NATIVE` | 5 | native OS integration, power management, credential boundary, process cleanup (underneath), native binary behaviour for `aioncore.exe` |
| `KEEP_IN_PYTHON` | 17 | everything else in the charter |
| `MOVE_TO_RUST_LATER` | **2 targets, gated** | `TARGET-1` engine-version validation + forced recovery; `TARGET-2` a small native supervisor *only if* measured triggers fire |
| `MOVE_TO_RUST_NOW` | **0** | — |
| `NOT_APPLICABLE` | 1 | browser/external action kinds |
