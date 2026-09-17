# 06 — Risk and rollback

Migration cost is not hidden here, and the numbers are labelled by how they were obtained.

**Cost basis.** No Rust prototype was built for this audit. Every cost below is an
order-of-magnitude estimate from the scope actually read, not a measured figure. Where a number
would be needed to justify a migration, this document says so rather than inventing one.

Retained evidence worth repeating: the engine suite collects **592 tests** across 54 files and
**8,929 LOC** of test code. That is the asset a migration spends.

---

## 6.1 Raw cost by candidate — if it were attempted today

Estimates are engineering-weeks for one developer already fluent in both Kel and Rust.

| Candidate | Implementation | Schema | Packaging | Migration risk | Rollback | New toolchain | Debug burden | Windows risk | Test burden | Effect on Python reasoning code |
|---|---|---|---|---|---|---|---|---|---|---|
| **Process supervision** (TARGET-2) | 3–5 w | none | +1 artifact; +CI rust toolchain; +cross-compile win x64 | **Low–Med** — swap behind adapter (B0) | **Easy** — adapter revert | rustup, cargo, linker, signing path | Medium — new crash surface where failure is least tolerable | Medium — Job Objects, handle inheritance, console-less spawn | + new supervisor tests; existing smoke battery unchanged | **None** if the boundary is held |
| **Lifecycle** (part of TARGET-2) | 1–2 w | none | as above | **Med** — touches boot and quit | Medium | as above | High — boot regressions are immediately user-visible | Medium — detached spawn, drain on quit | reuse packaged acceptance | None |
| **IPC** | 2–4 w | none | as above | **High** — every route and payload contract | Hard once payloads move | as above | High | Low | + contract tests per route | Low |
| **SQLite coordination** | 4–8 w | **none — schema untouched** | as above | **Very high** — two writers, WAL, fencing, epochs, durable adoption, `BEGIN IMMEDIATE` contention | Very hard | as above | Very high — same libsqlite3, brand-new bugs | **High** — WAL mapping retention, file handles, antivirus, OneDrive | rewrite the reliability suite | **High** — engine state logic is shared |
| **Native OS integration** | 1–2 w | none | as above | **Low** | Easy | as above | Low | Medium | small | None |
| **Credential boundary** | 1 w | none | as above | **Low** | Easy | as above | Low | Low; DPAPI already used | small | None |
| **Runtime health** | 2–3 w | none | as above | Low | Easy | as above | Low | Low | moderate | None |
| **Whole proposed runtime as one unit** | **20–40 w** | none, but **dual-writer hazard** | full rebuild of the release path | **Very high** | **Very hard** | as above | Very high | **Very high** | full-suite rewrite + new soak | **High** |
| **Authorization / leases / approvals** | not recommended at any cost | — | — | — | — | — | — | — | 592 tests pin it | — |

Read the SQLite row and the last row against each other. The two most expensive candidates are also
the two where Rust delivers the **least**: premise P1 says the SQLite library is identical, and the
authorization runtime is a durable state machine whose correctness lives in tests, not in the
language.

---

## 6.2 Costs specific to Kel that are easy to miss

### 6.2.1 Schema compatibility — the good news

Schema compatibility is the one place a migration is genuinely cheap: **nothing has to change.**
`rusqlite` speaks the same file format, and `migration.py` already carries a versioned,
backup-first, WAL-checking upgrade path. A Rust component opening the same database would need no
schema migration at all.

This is also, precisely, why the SQLite row above is dangerous. Cheap to connect, expensive to be
*correct*, and no compatibility wall to slow an over-confident start.

### 6.2.2 Packaging

Adding Rust means a new build artifact, a new toolchain in the release path, new signing
requirements, and a new failure mode inside a release process that already contains real traps:
`EBUSY` when a packaged scenario overlaps a rebuild, a lingering `app.asar` handle found with the
Windows Restart Manager, and a freeze tool that nests an inert duplicate directory. Each is handled
today by documented process discipline. A second compiled artifact adds a second place for that
discipline to be forgotten at exactly the wrong moment: the final freeze.

### 6.2.3 Windows-specific risk

This is a Windows-first product, and Windows is where the evidence shows the hard problems live:
WAL mapping retention after a killed process (retried 11 times in `core.py:188-204`), `WinError 32`
on open files, `EBUSY` on rebuild, handles that outlive their owner. Rust removes none of those
constraints. A migration would move a team with accumulated, documented Windows scar tissue onto a
surface where it has none.

### 6.2.4 Debugging burden

Today a failure is diagnosable in one language with a stack trace, an allowlist-built issue report,
a Diagnostics page that reports integrity, WAL size and orphan candidates honestly, and scratch
probes the team already wrote and reused (`ux-audit/backup-probe.py`, `ux-audit/restore-probe.py`).
A compiled supervisor means process-level failures can originate in a binary with no equivalent of
those affordances unless equivalent tooling is built first.

### 6.2.5 Test burden

**8,929 LOC / 592 tests** is the concrete number. A supervisor swap can plausibly keep nearly all of
it, because the engine's own logic is untouched. Anything that moves SQLite ownership, IPC payloads,
or authorization invalidates large parts of it — and those are exactly the parts that protect the
user's trust.

### 6.2.6 Effect on the Python reasoning/orchestration layer

Bounded if and only if the boundary is held. The engine's Python layer is where the product thinks:
routing, completion claims, memory, vetting, transcription, review, lineage, and the whole
authorization machine. Keeping the native edge to four verbs (`spawn`, `stop`, `status`,
`version-handshake`) leaves that layer untouched. Widening the edge changes it, and the reasoning
layer is the last thing that should move.

---

## 6.3 Rollback strategy

### For Plan A (recommended) — trivial

Every change in `05` Plan A is local and reversible: a version comparison, an error that stops being
swallowed, a test assertion, instrumentation fields, a PowerShell fix. Rollback is a revert commit.
No schema change, no artifact change, no new dependency.

### For the native edge (TARGET-2) — designed to be trivial

Rollback works only because of the **adapter seam (B0)**:

1. `spawn` / `stop` / `status` / `version-handshake` are defined and implemented in TypeScript before
   any Rust exists.
2. The Rust implementation is swapped in behind that seam.
3. Rollback = revert to the TypeScript implementation. No engine change, no schema change, no data
   migration, no re-index.

**The deletion test is the rollback proof.** Phase B2 (`05`) requires removing the supervisor and
confirming the diff touches nothing outside the supervisor module. If the revert reaches into engine
code, the boundary was breached and that is the signal to abandon `TARGET-2` entirely.

### For anything that moved SQLite, IPC payloads, or authorization — no credible rollback

Once durable state is written by a second implementation, rollback is no longer a revert; it is a
second migration, on user data, under time pressure. **This is the strongest single argument against
the candidate architecture**, and it is why the audit draws the boundary at four verbs.

---

## 6.4 Residual risks this audit accepts

Recorded so they are not mistaken for oversights:

- **S1 — the `engine_version` gap stays open until someone schedules `A1`.** This audit documents it
  and does not fix it. It is a real defect in the shipped line, and the audit must not be read as
  having closed it.
- **S2 — E6's close-grace overrun may be more than a harness artifact.** Two packaged runs overran.
  Packaged smoke is green, which is evidence the common path is fine, not proof that the tail is.
  `A3` is written to *measure* that tail rather than assume it away.
- **S3 — no footprint baseline exists**, so the "measurable memory/CPU improvement" category in the
  audit charter is currently unanswerable in either direction. `A4` creates the precondition for
  ever answering it.
- **S4 — Linux/WSL paths were read, not exercised.** Conclusions about `native_group.py` and
  `wsl_runtime.py` rest on code reading only.
