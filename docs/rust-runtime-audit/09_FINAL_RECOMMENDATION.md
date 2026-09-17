# 09 — Final recommendation

## Verdict

> ## `NO_MIGRATION_NEEDED_NOW`

Exactly one architectural verdict, stated once. No Rust migration is recommended for Kel, and none
should be scheduled into the V1.6 program.

One caveat, stated as plainly as the verdict itself, because it is the honest shape of the finding:
the audit found **one real architectural defect** and **one unresolved shutdown tail**. Neither is a
Rust problem, both are recorded, and both are fixable in the languages Kel is already written in.

---

## 1. What moves

**Nothing moves to Rust now.**

The recommended work is not a migration. It is five local changes in the TypeScript and Python
already present (`05` Plan A):

| | Change | Closes |
|---|---|---|
| `A1` | Validate `descriptor.engine_version` on the engine-reuse path; restart rather than reuse an unrecognised engine | the audit's one **architectural** finding (`02` E7) |
| `A2` | Stop swallowing restore failure twice (`backup.py:296` returns `False`; `service.py:38-42` passes) | a silent-failure path (`02` E2) |
| `A3` | Assert the engine reached its own terminal state before any bounded kill; record which path each run took | the unresolved shutdown tail (`02` E6) |
| `A4` | Record working set and CPU for the daemon and each worker run | the missing precondition for *any* future footprint claim |
| `A5` | Fix `freeze-release.ps1` nesting an inert `resources/kel-engine/kel-engine/` | a live release-record trap for the final freeze |

`A5` should be done **before the final freeze**. `A1` and `A2` should be done if the program has
room. `A3` and `A4` are lower urgency. All five are days of work, with no new toolchain, no new
language, and no stopped feature work.

**The one conditional exception:** if a re-open trigger in `07` ever fires, a **tiny** native
supervisor (`TARGET-2`) becomes justified — owning exactly four verbs: `spawn`, `stop`, `status`,
`version-handshake`. That is not a migration, it is an edge, and it is not recommended now because
no trigger has fired.

---

## 2. What stays Python

**All of it — and specifically the parts that matter most:**

- **the durable engine** — `kel.sqlite3`, WAL, transactions, fencing, epochs, durable adoption of
  interrupted runs, deadline enforcement;
- **the authorization runtime** — capability leases, scope checks, effect-point enforcement, role
  snapshots;
- **approvals and grants** — in-chat approval cards, one-shot grant spending at the effect, expiry,
  double-resolution refusal, `resume_after_grant`;
- **reasoning and orchestration** — routing, model preferences, completion claims, review,
  assessments;
- **product surfaces** — memory, vetting, transcription, project map, artifact lineage;
- **process supervision as it exists** — Job Object and cgroup containment, Win32 process identity,
  broker monitoring and restart;
- **IPC payloads and the engine's route contracts.**

That is roughly 15,000 lines of engine code and 8,929 lines of tests. It is the product's trust core
and its durable intelligence, and it earns nothing from a language change.

## 2b. What is already native — and stays that way

Not "Python", not "Rust": already the operating system, reached correctly.

- Credential custody — Electron `safeStorage` = **DPAPI** on Windows, main process only
- Sleep inhibition — Electron `powerSaveBlocker('prevent-app-suspension')`
- Single-instance guarantee — **kernel lock** (`msvcrt.locking` / `flock`), released on process death
- Worker lifetime group — Win32 **Job Object** / Linux **cgroup v2**
- Worker identity — Win32 `GetProcessTimes` creation time / `/proc/<pid>/stat`
- SQLite itself — the **C library**, on both sides of the question
- `aioncore.exe` — vendor native binary

Seven of the eight candidate "native integration" concerns were already native before this audit
began.

---

## 3. Why

Five reasons, each from evidence rather than preference.

### 3.1 There is no dependency surface to remove

An AST scan of all 47 `runtime/kel/*.py` finds **one** third-party import: `websocket-client`, used
solely for the transcription realtime socket. `KelEngine.spec` declares `binaries=[]`,
`hiddenimports=[]`. The engine is stdlib plus one WebSocket client.

The usual strongest argument for Rust on a Python desktop app — escaping native-module ABI churn,
wheel fragility, and heavy dependency trees — **does not exist here.** There is no ABI surface.

### 3.2 Startup is not a bottleneck, and it is measured

`engine-start` spans: **93–113 ms typical**, with 243–486 ms outliers. `import kel.service` ≈ 60 ms.
Against a **45-second** Electron boot ceiling, behind a Chromium startup nobody has even
instrumented yet (`12_PERFORMANCE.md`: *"No renderer startup / first-paint timing yet"*).

Rust would shave a fraction of the interpreter's ~60 ms import. That is invisible.

### 3.3 SQLite pain is language-neutral

`rusqlite` and Python `sqlite3` wrap the same libsqlite3. WAL, SHM, `BEGIN IMMEDIATE`, busy
timeouts, and the Windows killed-process WAL-mapping retention that `core.py:188-204` already
retries eleven times against — **all identical in Rust.** A Rust store would meet the same
constraints, with none of the accumulated Windows scar tissue.

### 3.4 The pain ledger is not architectural

Of fourteen evidenced defects: **seven are ordinary bugs**, two are tooling, two are other people's
software, one is already mitigated, and only **two are architectural** — one closing in ~20 lines of
TypeScript, the other measured by a test harness whose user-facing counterpart is green.

The hardest Windows issues (`WinError 32` on live backup, `EBUSY` on rebuild, a lingering `app.asar`
handle) were diagnosed and fixed competently in Python and TypeScript.

### 3.5 The migration would spend the trust core

592 collected tests across 8,929 LOC pin the lease, approval, fencing, grant and recovery behaviour
that users depend on. The two most expensive candidates — SQLite coordination and authorization —
are also the two where Rust delivers **least**. Rewriting them does not make them more correct; it
makes them new, and it removes the rollback path for durable user state.

**A migration justified by a memory or CPU improvement cannot even be evaluated**, because no memory
or CPU measurement exists anywhere in the repository. `A4` exists to fix that before anyone argues
from it.

---

## 4. Before or after the V1.6 final freeze

**After — for anything Rust. Before — only for `A5`.**

| | Timing |
|---|---|
| `A5` freeze-tool fix | **Before** the final freeze (the freeze tool is used by the final release) |
| `A1`, `A2` | In-window if the program has room; otherwise first patch after |
| `A3`, `A4` | Before the freeze if convenient; equally fine after |
| `B0` adapter seam | After V1.6, or now if the team wants the seam regardless — it is pure TypeScript refactor |
| `B1` native supervisor | **After V1.6, only on a fired trigger** |
| `B2` deletion test | Immediately after any `B1` |
| SQLite / IPC / authorization moves | **Never recommended** |

`v1.6.0-pre1` and every frozen V1–V1.5 release were read and never modified.

---

## 5. Acceptance criteria

### 5.1 For the recommended work (`A1`–`A5`) — pass/fail

- **`A1`** — Reusing an engine whose `engine_version` differs from this build's expected version is
  impossible: the reuse branch refuses, stops the stale engine within a bounded window, and spawns
  fresh. Unit test over `{match, mismatch, descriptor-live, descriptor-dead}`; packaged boot shows
  no reuse across a version change.
- **`A2`** — A failing staged restore leaves the pending marker in place, records the reason, and
  surfaces one plain sentence. No silent `False` reaches a caller that swallows it.
- **`A3`** — Every packaged scenario reports *which* shutdown path it took (engine-reached-terminal
  vs bounded-kill), and `engineStopped: true` / `appExited: true` / `errors: []` still hold.
- **`A4`** — Working set and CPU are visible for the daemon and per worker run on the existing
  Diagnostics surface.
- **`A5`** — A fresh freeze produces no nested `resources/kel-engine/kel-engine/`; candidate↔frozen
  byte identity holds without manual correction.
- **Global** — engine suite ≥ 592 passed; desktop typecheck 0 errors; desktop tests ≥ 76; packaged
  acceptance battery unchanged from the frozen baseline.

### 5.2 For the conditional native edge (`TARGET-2`) — inert unless a trigger fires

- engine source **byte-identical** across the swap;
- `kel.sqlite3` byte-comparable after identical workloads;
- zero stale `Kel*` processes after 50 consecutive boot/quit cycles;
- descriptors never reused across a version mismatch;
- shutdown reaches the engine's own terminal state before any kill, in 100 % of cycles;
- **deletion test passes** — removing the supervisor touches nothing outside its module;
- packaged acceptance + engine suite unchanged.

---

## 6. Rollback strategy

**For everything recommended: a revert commit.** No schema change, no artifact change, no new
dependency. Every item in §1 is local and reversible.

**For the conditional native edge: the adapter seam is the rollback.** `B0` defines and implements
`spawn` / `stop` / `status` / `version-handshake` in TypeScript *first*. The Rust implementation is
swapped in behind that seam; rollback is reverting to the TypeScript implementation. No engine
change, no schema change, no data migration, no re-index. `B2`'s deletion test *is* the rollback
proof.

**For anything that moved SQLite, IPC payloads, or authorization: there is no credible rollback.**
Once durable state is written by a second implementation, rollback becomes a second migration — on
user data, under time pressure. That asymmetry is the single strongest argument against the
candidate architecture, and the reason the boundary is drawn at four verbs.

---

## 7. The one-sentence summary for the Integration Coordinator

Rust is not the right answer to Kel's actual problems; the actual problems are one unvalidated
version check, one swallowed error, one unmeasured shutdown tail, one missing instrumentation
baseline and one freeze-tool bug — **five small changes, none of which need a new language.**

**Do not implement the migration.**
