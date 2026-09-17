# 04 — Migration boundaries

## 4.1 The candidate architecture, evaluated

The charter proposed this shape, to be evaluated rather than assumed:

```
Electron / React
        ↓
Kel Native Runtime — Rust
        ├ process supervision
        ├ lifecycle
        ├ IPC
        ├ SQLite coordination
        ├ native OS integration
        ├ credential boundary
        └ runtime health
        ↓
Python Kel reasoning/orchestration
        ↓
workers/providers
```

**Assessment: rejected as drawn.** It fails on four counts, each evidenced.

### Failure 1 — it moves the wrong layer down

The proposed Rust runtime would sit *below* Electron and *above* Python, owning supervision,
lifecycle, IPC, SQLite coordination, native integration, credentials and health. That is a large new
process between two existing ones, and every item in its ownership list is **currently correct or
already native**:

| Proposed Rust ownership | Actual current state | Evidence |
|---|---|---|
| process supervision | works; Job Object + cgroup + epochs + fencing + durable adoption | `windows_job.py`, `native_group.py`, `runner.py:19-38`, `engine.py:44-56` |
| lifecycle | works; drain hook registered first, structured shutdown | `KelService.ts:28-44`, `service.py:117-127` |
| IPC | works; 3 deliberately boring transports | `01` §3 |
| SQLite coordination | split-and-documented ownership, already correct | `legacyHandoffContract.ts`, `repairLegacyHandoffSchema.ts` |
| native OS integration | already native via ctypes | `windows_job.py`, `runner.py`, `keepAwake.ts` |
| credential boundary | already the OS key store (DPAPI) | `kelCredentials.ts:65,89` |
| runtime health | works, and is *measured* and surfaced | `diagnostics.py`, live Diagnostics page |

Rewriting six working subsystems to gain one missing field check is not a boundary. It is a
rebuild.

### Failure 2 — it puts a new process on the critical path before a freeze

The V1.6 program has an immutable `v1.6.0-pre1` checkpoint and a live Phase 4 ahead. The proposed
runtime would own startup, shutdown, IPC, credentials and the engine boundary — meaning every one of
those would be new code on the path the release depends on. The blast radius is the entire product.

### Failure 3 — "SQLite coordination" is a phantom

The charter lists SQLite coordination as a Rust responsibility. But **per premise P1**
(`01` §6), `rusqlite` and Python `sqlite3` are the same C library. Moving SQLite "ownership" to Rust
moves nothing: the same file, the same WAL, the same SHM, the same `BEGIN IMMEDIATE`, the same
Windows mapping-retention behaviour on a killed process. The only thing that changes is which
language writes the retry loop that `core.py:188-204` already writes correctly.

### Failure 4 — it does not address either of the two real architectural findings

`E7` (unvalidated engine reuse) is a missing comparison. `E6` (harness close force-kill) is a
missing handshake. Neither is fixed by relocating supervision to Rust; both would still need
writing.

## 4.2 The smaller boundary that is actually justified

Six of the seven proposed responsibilities are struck. What remains is not a runtime — it is a
**narrow, optional native edge**, and even that is not recommended now:

```
Electron / React                        (unchanged)
        ↓   loopback HTTP + bearer, descriptor, + version check   ← TARGET-1 lands HERE (TS + Python)
Kel engine daemon  — Python             (unchanged: all state, authz, leases, approvals,
        ↓                                 supervision, durability, reasoning, orchestration)
ACP host + workers + providers           (unchanged)
```

`TARGET-1` — the one change the evidence supports — is **not a Rust change at all**. It is:

1. compare `descriptor.engine_version` against this build's expected engine version on the reuse
   path;
2. on mismatch, do not reuse: terminate the stale engine (Job-Object/handle-based, bounded), then
   spawn;
3. if a live engine refuses the instance lock while unresponsive, do not dead-end at
   *"Kel engine did not start. See desktop.log."* — offer one bounded, explicit recovery action.

That closes the Windows "no stale runtime" gap inside the existing TypeScript and Python.

`TARGET-2` — a small native supervisor — is **`MOVE_TO_RUST_LATER`, and only if measured triggers
fire.** Its scope is deliberately tiny: *Supervisor* would own process spawn/kill/lifetime and
version handshake, and nothing else. It would **not** own SQLite, authorization, approvals, leases,
IPC payloads, credentials, or reasoning. If it is ever built, its acceptance criterion is that
deleting it must be possible without touching a single line of engine state logic.

## 4.3 Why not "MicroSupervisor in Rust" right now anyway?

Because there is no measured problem it solves. The candidate benefits were checked one by one:

| Claimed benefit | Measured reality at `ffeef73` | Verdict |
|---|---|---|
| deterministic shutdown | packaged smoke green: `engineStopped: true`, `appExited: true`, `errors: []`, incl. from the frozen folder | already met |
| fewer processes | true — but no evidence process *count* causes failures. The one count-adjacent symptom is orphan candidates in process *history*, which the Diagnostics page reports honestly and which 7-day retention clears | no benefit demonstrated |
| no stale runtime | **not delivered by Rust.** It is delivered by validating `engine_version` | fixed by `TARGET-1`, in TS |
| no DB ownership race | there is no race; ownership is split by design and documented | already met |
| simpler backup coordination | F12 root cause was file *selection policy* and is fixed in Python | already met |
| safer credential boundary | already DPAPI, main-process-only, env-injected, child-stripped | already met |
| reduced IPC failure surface | 3 boring transports; observed failures were payload contract bugs | no benefit demonstrated |
| simpler native integration | Job Object / cgroup / Win32 identity already reached via ctypes | already met |
| fewer packaging failure modes | real friction exists (nested duplicate, space-free staging, EBUSY) — none of it caused by Python's presence, and the PyInstaller surface is one dependency | not addressed by Rust |
| measurable memory/CPU improvement | **no memory or CPU measurement exists anywhere in the repository.** `12_PERFORMANCE.md` contains no memory series and no CPU series | cannot be claimed; would need new instrumentation first |

That last row is the audit's discipline line. A migration cannot be justified by a memory or CPU
improvement that nobody has ever measured. If someone wants to argue Rust on footprint, the
precondition is not a prototype — it is **instrumentation**.

## 4.4 Where a native edge would genuinely belong, if it ever does

Stated narrowly so a future reader cannot inflate it:

- **Process spawn / kill / lifetime / version handshake** — the only area with real friction
  (`E6`, `E7`) and the only area where a single static binary with no interpreter boot is a
  structural, not cosmetic, difference.
- **Nothing else.** In particular: not SQLite; not authorization, leases or approvals; not IPC
  payloads or contracts; not credentials; not reasoning, routing, memory, vetting or orchestration.

The engine's Python layer is the product's durable intelligence and its trust core. 592 tests pin
it. Moving any of it is a separate, much larger decision that this audit does **not** recommend and
the evidence does **not** support.
