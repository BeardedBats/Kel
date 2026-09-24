# 02 — Failure evidence

Every entry below is a defect that actually happened, with its source. The **Class** column is the
part that matters: it separates an architectural problem from an ordinary bug that Rust would not
have prevented.

Class key:

- **ARCH** — structural; the current boundary or protocol is wrong, and a different process model
  could remove the class of failure.
- **BUG** — ordinary defect. Rust would not have prevented it; the fix is local.
- **TOOL** — build/harness/measurement problem. Language is irrelevant.
- **THIRD-PARTY** — the blocker lives in external software. Not addressable by rewriting Kel.

---

## E1 — SQLite lock error masked by a bad rollback — **BUG**

`Store.transaction()` ran an unconditional `ROLLBACK` when `BEGIN IMMEDIATE` itself failed. The real
error (`database is locked`, after the 10 s busy timeout under a competing writer) was replaced with
`cannot rollback - no transaction is active`. Diagnosis became misleading; the surfaced message was
wrong.

Fixed by guarding on `db.in_transaction` (`core.py:206-224`). Proven by
`test_v15_reliability.py` · `test_a_held_lock_surfaces_a_clean_bounded_error_then_recovers`.
Source: `docs/v1.5/10_RELIABILITY_REVIEW.md` "Defects this sweep found and fixed" #1.

**Not a Rust argument.** `rusqlite` would raise the identical SQLite error and would need the
identical guard.

## E2 — Telemetry thread outliving shutdown held a file handle — **BUG**

`Service.shutdown()` never joined the telemetry thread, so an in-flight provider call kept
`appserver.stderr` open past shutdown. On Windows this presented as an **undeletable data root** —
a confusing symptom a long way from its cause.

Fixed by joining with a 30 s bound (`service.py:117-127`). The probe failed before the fix.
Source: `docs/v1.5/10_RELIABILITY_REVIEW.md` #2.

**Not a Rust argument.** This is a "who joins whom" discipline bug. Rust has the same obligation and
no mechanism that discharges it for you.

## E3 — Backup failed while Kel was running (`WinError 32`) — **BUG** *and the highest-value entry*

Recorded verbatim in `docs/basic-ux-sweep/14_FINDINGS_AND_FIXES.md`:

> **F12 | Backup failed while Kel was running: `WinError 32` on `controller.lock` and on Chromium's
> `host/Network/Cookies`, so "Back up now" answered "could not finish that just now" | UX-P1**

A scratch probe was written to find it — `ux-audit/backup-probe.py`, whose docstring states its whole
purpose:

> "Reproduce `Backup.create` verbosely against a real engine data root … **prints the exact failing
> entry + traceback instead of the plain `PolicyError` the UI shows.**"

**Diagnosis:** the backup walked the *entire* data tree, including files the running app holds open
by design (the controller lock, Chromium's `Network/Cookies` inside `host/`). The failure was not
"Python cannot copy a live file". It was **"the copy set was wrong"**.

**Fix (in Python, shipped):** declare runtime state out of scope (`VOLATILE_ENTRIES`), restrict the
`host` tree to `config` + `aionui`, copy databases through SQLite's own `Connection.backup()` hot-copy
API, never copy `-wal`/`-shm`/`-journal`, retry plain files, and **name anything still unreadable
under `skipped`/`notes` instead of failing the whole backup** (`backup.py:29-33, 72-81, 116-137,
140-197`).

**Why this is not a Rust argument:** the root cause was a policy decision about *which files belong
in a backup*. A Rust implementation walking the same tree with the same policy fails identically —
`WinError 32` is the OS refusing a shared-mode violation, which has nothing to do with the calling
language. The shipped fix is the correct fix, and it is already in the product.

## E4 — `apply_pending_restore` fails silently — **BUG, STILL OPEN**

Two layers of silence:

```python
# runtime/kel/backup.py:294-296
    except Exception:
        return False
```

```python
# runtime/kel/service.py:38-42
        try:
            from .backup import apply_pending_restore
            apply_pending_restore(self.store)
        except Exception:
            pass
```

The second probe written during this incident says exactly what the team was fighting —
`ux-audit/restore-probe.py`:

> "Reproduce `apply_pending_restore` against a LIVE app root … **Prints the exact step that fails
> instead of the silent `False` the engine returns.**"

So: a user stages a restore, the restore fails, the engine returns `False`, the caller discards it,
and **the user is told nothing**. The staged copy and the pending marker simply remain.

To be fair about what is right here: the *design* around it is good. Restore is staged into
`.restore-staging/` and applied at the next engine start **before any connection opens**, and the
previous data is kept as `.pre-restore-<timestamp>`. The staging design means a failed copy cannot
half-restore the database. The defect is purely that the final outcome is never reported.

**Not a Rust argument.** This is a missing `raise` and a missing user-facing message. Rust would not
make a swallowed exception loud.

**Recommended fix, and it is three lines:** stop returning `False`; let the marker's presence and the
exception reach a surface the user can see.

## E5 — Windows retains a WAL mapping after a killed process — **ARCH-ADJACENT, ALREADY MITIGATED**

`core.py:188-204` opens every connection through a retry loop whose own comment states the problem:

> "A killed Windows process can briefly retain a WAL mapping. Retry only opening a connection, before
> any application transaction is submitted."

Eleven attempts at 100 ms, guarded to the exact condition (`os.name == 'nt'` **and**
`'disk I/O error'` in the message), and only around *opening*, never around an application
transaction.

This is the single most Rust-looking item in the codebase, and it still is not a Rust argument.
The mapping is retained by **Windows** for a dead process's file object; the next opener fails
regardless of what language it is written in. `rusqlite` would hit the same `disk I/O error` and
would need the same retry. What actually fixes this class is not a language — it is **not killing the
engine** and **letting the kernel release handles deterministically**, which is the lifecycle work in
`03` and `05`.

## E6 — Two packaged runs needed a force-kill of the engine — **ARCH**

`docs/release-hardening/09_PACKAGED_ACCEPTANCE.md`, note 5:

> "Two runs (`vetting`, `sider`) end with `engineKilled: true` — the engine was force-stopped after
> the scenario overran its close grace period. No stray process remained in either case."

And the harness has a first-class flag for it: `packaging/capture-screens.cjs:385-396` sets
`engineKilled` from `process.kill(ENGINE_PID)`, reporting `engineStopped: engineStopped && !engineKilled`.

The program already knew this was a gap and listed it as deferred work, in
`docs/v1.4.1/06_V1_5_DEFERRED_WORK.md` item 10:

> "**Harness determinism** — deterministic pet-enable step (wait/retry/assert) and **a close handshake
> so capture runs stop via the engine instead of the bounded kill**."

**This is genuine architectural friction** and it is the strongest pro-Rust item in the whole ledger.
It says: *the engine does not always acknowledge shutdown inside its grace period, so the harness
escalates to a kill.*

Against it, three honest counterweights:

1. It is a **test-harness** measurement, not a user-visible one. The user path is different and it
   works: the freeze record shows packaged smoke `engineStopped: true`, `appExited: true`,
   `errors: []` — including a smoke run executed **from the frozen folder itself**
   (`docs/v1.6/00_CHECKPOINT_FREEZE.md`).
2. The user path has a real mechanism: the `before-quit` drain hook calls `/api/shutdown-idle`,
   `event.preventDefault()`s the quit, and only then quits after 50 ms (`KelService.ts:28-44`).
   `/api/shutdown-idle` refuses to drain while work is open, which is *correct* behaviour and is
   probably why the harness runs overran — they had open work, by design, and had to be killed.
3. A graceful-shutdown bug in a *rewrite* is more likely, not less, until proven by the same battery.

Classified **ARCH** but with the trigger conditions in `05` — see the honest discussion there.

## E7 — `engine_version` is never validated when an existing engine is reused — **ARCH, STILL OPEN, and the real find**

The engine is detached from Electron on purpose (`detached: true`, `child.unref()`), so an Electron
crash leaves the engine running. The next launch then finds it:

```ts
// KelService.ts:46-52
  try {
    descriptor = JSON.parse(fs.readFileSync(descriptorPath, 'utf8'));
    await kelRequest('/api/state');          // ← liveness only
    connected = true;
    console.log('[KEL-BOOT] initializeKel reused running engine');
  } catch { … }
```

The descriptor genuinely carries the version — `service.py:946` writes
`{'url', 'token', 'pid', 'engine_version'}`, and the TypeScript type declares it
(`Descriptor = { url: string; token: string; engine_version: string }`, `KelService.ts:8`). **It is
read into a variable and never compared to anything.** A grep for `engine_version` across
`desktop/packages/desktop/src/**` returns only *display* sites (diagnostics page, onboarding,
`kelApi.ts` type) — no comparison, no gate.

The consequence, concretely: install an update that replaces `KelEngine.exe`; if a detached engine
from the previous build survived an Electron crash, the new main and renderer talk to the old engine.
The product then runs **layer N against engine N−1** with no check, no warning, and no log line.

The failure mode compounds when the surviving engine is *hung* rather than healthy:

```
/api/state times out (30 s AbortSignal, KelService.ts:15)
  → catch → treat as "no live engine" → spawn a new engine
  → new engine hits InstanceLock on controller.lock → Conflict → exit code 2
  → initializeKel throws: "Kel engine did not start. See desktop.log."
```

Recovery then requires the user to find and kill a process they did not know existed. The engine
prints the real reason (`'Kel is already open for this data folder…'`) to `desktop.log`, so the
information exists — it just never reaches a surface. `docs/v1.5/12_PERFORMANCE.md` and the
reliability review both flag the reporting half of this (case 21, "stale engine package") as
*reported*, and reporting is not validating.

**Why this is ARCH:** it is a **protocol/ownership gap**. The system's own invariant — "the engine
that serves this app is the engine that shipped with this app" — is unstated, unenforced, and
unenforceable by the current handshake. The engine is right to be detached; the reuse path is wrong
to trust liveness alone.

**Why this still is not a Rust argument:** the invariant is enforced by comparing one string that is
*already being read from a file*. The fix is a version gate on the reuse path plus a bounded
"ask it to exit, and if it will not, tell the user which process to end" fallback. That is small,
testable, and belongs in the TypeScript that already owns the spawn.

## E8 — Rung-1 contract break blanked the entire app (P0) — **BUG**

`docs/basic-ux-sweep/14_FINDINGS_AND_FIXES.md` F11:

> "**The whole app could blank** (Settings · Model and any Kel chat): `action=get` answered without
> `providers`, `KelModelControl` crashed on `state.providers.map(...)`, React unmounted the page |
> **UX-P0**"

Fixed by making `get`/`list` answer one payload and by having the control paint an unavailable state.

**Not a Rust argument.** This is a schema/contract mismatch across a JSON boundary. A typed Rust
responder would *move* the problem, not remove it, unless the contract itself became typed on both
sides.

## E9 — Electron's IPC error envelope leaked into the UI — **BUG**

> "Electron wraps handler failures as `Error invoking remote method 'kel:request': Error: <message>`.
> The preload bridge now strips that envelope before any surface sees the message."
> — `docs/release-hardening/08_ERROR_AND_RECOVERY.md`

**Not a Rust argument.** A serialization envelope leaking is a bridge hygiene bug.

## E10 — Engine staging to dodge a whitespace bug in the host — **TOOL / THIRD-PARTY**

`KelService.ts:59-92` stages the packed engine into a space-free application-data directory, with the
reason in the comment:

> "AionCore validates the ACP agent's CLI via its whitespace-split `binary_name` (`cli_not_found` on
> any spaced path). Stage the bundled engine into the space-free application-data directory so agent
> registration and ACP spawn never depend on the install path."

So: **Kel ships copy/staging logic purely to work around someone else's string-splitting bug.**
`C:\Program Files\…` is the normal install location and contains a space.

**Not a Rust argument at all** — this is the clearest THIRD-PARTY entry in the ledger. A Rust
`KelRuntime.exe` in `C:\Program Files\Kel\` would hit the identical `cli_not_found`. The only real
fixes are (a) the host stops whitespace-splitting, or (b) Kel keeps staging.

## E11 — Packaging: lingering `app.asar` handle blocked the build — **TOOL**

> "`dist/package` is one renderer edit behind: its `app.asar` is held by a **lingering handle from
> the host environment (identified with the Windows Restart Manager: the GUI host process)**, so
> electron-builder cannot replace it in place."
> — `docs/release-hardening/AUTO_RESUME.md`

Plus a real adjacent incident: `docs/release-hardening/09_PACKAGED_ACCEPTANCE.md` note 2 —

> "One collision, resolved: an earlier re-run overlapped a rebuild with a live scenario (**EBUSY**,
> builder aborted, the vetting leg timed out against a half-removed app)."

**Not a Rust argument.** Both are Windows file-sharing collisions between a build tool and a running
process. The mitigation is procedural and already written down ("never rebuild while a packaged
scenario is running"; build with an output override).

## E12 — Freeze tooling nests an inert duplicate runtime — **TOOL, STILL OPEN**

> "Freeze tooling nests an inert runtime duplicate (`resources/kel-engine/kel-engine/`); the
> V1.6.0-pre1 freeze removed it after assembly for exact candidate↔frozen identity — do the same at
> the final release (**or fix `freeze-release.ps1` first**)."
> — `docs/v1.6/AUTO_RESUME.md`

A packaging-script bug, manually worked around at the freeze. Language-independent.

## E13 — Orphan-candidate process records — **BUG (cosmetic / reporting)**

The diagnostics surface honestly reports:

> "Problems: 2 recorded process(es) are no longer alive — database health is reported, not guessed."
> "Process ownership: Run `29804a1c-4da` PID 31600 — no — **orphan candidate** — past deadline"

The same two records recur across many archived runs (`b2-maintext`, `final-standing`, `fixed3`,
`seeded`), retained under the 7-day `process_observations` window. The fencing itself works — every
run also reports "Runs past their fence: 0 — none waiting".

This is the diagnostics surface being honest about worker processes that ended without their
observation being closed out. Given E6 (harness force-kills), that is expected, and the product
already tracks it correctly.

## E14 — No OS-level sandbox for native hosts — **THIRD-PARTY**

`docs/v1.5/16_KNOWN_LIMITATIONS.md`:

> "No OS-level sandboxing for native hosts: the documented user-authorized trust model applies
> (`docs/v1.4.1/02_RUNTIME_TRUST_BOUNDARY.md`); **Codex Windows sandbox modes remain the blocker.**"

Restated in `docs/v1.4.1/06_V1_5_DEFERRED_WORK.md` item 5: "Codex sandbox modes on Windows are the
blocker that kept D-02 at Option B."

**Explicitly not a Rust argument**, and worth stating loudly because "security boundary → Rust" is an
easy reflex. The blocker is a third-party CLI's Windows sandbox support. Kel already has real
containment where it can: a Win32 Job Object for worker lifetime (`windows_job.py`) and a cgroup on
Linux (`native_group.py`). A Rust supervisor would inherit the identical Codex limitation.

---

## Tally

| Class | Entries | Count |
|---|---|---|
| **ARCH** | E6 (shutdown grace force-kill), E7 (unvalidated engine reuse) | **2** |
| BUG | E1, E2, E3, E4, E8, E9, E13 | 7 |
| TOOL | E11, E12 | 2 |
| THIRD-PARTY | E10, E14 | 2 |
| ARCH-ADJACENT, mitigated | E5 (Windows WAL mapping retention) | 1 |

**Seven of fourteen are ordinary bugs. Two are tooling. Two are other people's software.** Only two
are architectural — and of those, one (E7) closes in about twenty lines in the language it is already
written in, and the other (E6) is measured by a *test harness* on a path whose user-facing
counterpart is green.

That distribution is the audit's central finding: **Kel's pain has not been architectural. It has
been ordinary engineering on a genuinely hard Windows surface, done competently and recorded
honestly.**
