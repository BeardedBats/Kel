# 05 — Incremental plan

Two plans, kept strictly separate. The first is the only one recommended for action. The second is
conditional, gated, and must not be started without the triggers in `07` firing first.

---

## Plan A — the recommended work (no Rust)

This is the whole of what the evidence supports. It closes the only two architectural findings in
`02` and removes the "stale runtime" class of failure.

### A1 — Validate the engine on reuse  *(closes E7)*

**Where:** `desktop/packages/desktop/src/process/services/kel/KelService.ts`, reuse branch
(lines 46–52). The version is *already* on the wire in `descriptor.engine_version` (`service.py:945`)
and *already* typed in `Descriptor` (`KelService.ts:8`); nothing reads it.

**What:**

1. Compare `descriptor.engine_version` with the engine version this build expects.
2. On match → reuse exactly as today.
3. On mismatch → treat as a stale runtime: ask it to drain; if it does not stop within a bounded
   window, terminate it by handle/Job-Object (a PID is not an identity — `runner.py:19-38` already
   shows the project knows this); then spawn fresh.
4. Never reuse an engine whose version this build does not recognise.

**Behind an adapter:** yes. Keep the decision in one small pure function — given
`{descriptorVersion, expectedVersion, descriptorIsLive}` return `reuse | restart` — so it is
directly unit-testable without spawning a process, and so the decision is visible in one place.

**Cost:** small. Two call sites, one helper, one test file.

### A2 — Make restore failure visible *(closes the silent path in `02` E2)*

`apply_pending_restore` returns `False` on any exception (`backup.py:296`), and
`Service.__init__` wraps the call in `except Exception: pass` (`service.py:38-42`). A restore that
fails is silent twice.

**What:** capture the exception, record it durably on the store, leave the pending marker in place,
and surface one plain sentence on the next Work/Diagnostics read — *"The restore could not be
finished. Your previous data is still in place."* Do not change the staging design; it is good.

**Why not Rust:** it is an error-reporting omission. There is no language dimension.

### A3 — Make the shutdown handshake deterministic and *tested* *(addresses E6)*

The packaged smoke path is already green (`engineStopped: true`, `appExited: true`, `errors: []`,
verified from the frozen folder itself). Two harness runs nonetheless ended `engineKilled: true`
after overrunning a close grace period, and `docs/v1.4.1/06` records the desire for "a close
handshake so capture runs stop via the engine instead of the bounded kill."

**What:** keep the kill as the last resort, but add a positive assertion that the engine reached
its own terminal state *before* any kill, and record which path each run took. The goal is not to
remove the kill; it is to stop the kill masking whether the handshake worked.

### A4 — Instrument memory and CPU *(precondition, not a fix)*

No memory or CPU measurement exists in the repository. Until it does, no footprint claim about Rust
— in either direction — can be honestly made.

**What:** extend the existing `startup_spans` / `process_observations` machinery to record working
set and CPU for the daemon and for each worker run, and surface it on the Diagnostics page that
already exists. This is the *precondition* for ever reopening the Rust question on performance
grounds.

### A5 — Fix `freeze-release.ps1` nesting an inert duplicate

`docs/v1.6/AUTO_RESUME.md` records that the freeze tool nests an inert
`resources/kel-engine/kel-engine/`, and that the V1.6.0-pre1 freeze had to remove it by hand after
assembly, with the instruction to *"fix `freeze-release.ps1` first"* for the final release. That is
a live packaging trap for the final freeze. Fixing it removes a manual step that, if forgotten,
silently breaks candidate↔frozen byte identity.

**Total Plan A cost:** days, not weeks. No new toolchain. No new language. No stopped feature work.

---

## Plan B — the conditional native edge  *(not recommended now; gated)*

Read this only if a trigger in `07` has actually fired. If none has, this plan is inert.

### Phase B0 — Adapter seam first (safe even if nothing follows)

Define the supervisor interface **in TypeScript, implemented in TypeScript**, covering exactly:
`spawn`, `stop`, `status`, `version-handshake`. Route `initializeKel`'s spawn/reuse/drain through
it. Ship it. This is pure refactor, verifiable against the existing 76 desktop tests + typecheck,
and it is **useful even if Rust never arrives** — it is where A1 belongs anyway.

*Exit criterion:* existing packaged smoke and acceptance behave identically.

### Phase B1 — Only if a trigger fired: a tiny native supervisor

Implement the same interface in Rust. Scope, and no more:

- spawn the engine, hold a Job Object-style lifetime handle
- stop it deterministically, bounded, by handle
- own the version handshake
- expose exactly the four verbs above

**It must not** own SQLite, authorization, leases, approvals, IPC payloads, credentials, or any
engine state logic. If it needs to read `kel.sqlite3`, the scope is wrong.

*Entry criterion:* B0 shipped and green; a trigger from `07` measured and recorded.

*Exit criterion:* every `07` acceptance criterion passes, and the Python engine's source is
**unchanged** by the swap.

### Phase B2 — Delete test (mandatory)

Remove the native supervisor and restore the TypeScript implementation. If anything outside the
supervisor module had to change to do that, Phase B1 exceeded its boundary and must be reverted.

This test exists specifically so that `TARGET-2` can never quietly become a migration.

### Never in Plan B

Relocating any of: reasoning, routing, completion claims, memory, vetting, transcription,
authorization, capability leases, approvals, grants, fencing, review, or artifact lineage. Those are
the trust core, they are pinned by 592 tests, and they earn nothing from a language change.

---

## Sequencing relative to the V1.6 program

| Work | Timing |
|---|---|
| A1, A2 | **Now** — small, high value, independent of the freeze |
| A3, A4 | Before final V1.6 freeze if the program has room |
| A5 | **Before the final freeze** — the freeze tool is used by the final release |
| B0 | After V1.6 final, or now if the team wants the seam regardless |
| B1 | **After V1.6 final**, and only on a fired trigger |
| B2 | Immediately after any B1 |
