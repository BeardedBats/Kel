# 00 — Rust runtime audit: status

**Verdict: `NO_MIGRATION_NEEDED_NOW`**

Status: **complete** — evidence-gathered and reviewed; no code changed anywhere.

| Field | Value |
|---|---|
| Audited commit | `ffeef73` — `ffeef73914da251750219452b6f927f38711b3c0` ("feat(lineage): every generated artifact can say where it came from (v1.6)") |
| Branch inspected | `ux/v15-journeys` |
| Active V1.6 worktree | `C:\Users\Nick\Desktop\Kel\kel-ux-v15` — **read only, never written** |
| V1.5 baseline | `5e76b21` (main) |
| This audit's worktree | `C:\Users\Nick\Desktop\Kel\kel-rust-audit` — branch `audit/rust-runtime`, pinned to `ffeef73` |
| Frozen checkpoints | Untouched. `v1.6.0-pre1` and all V1–V1.5 frozen releases were read, never modified |
| Merge | None. The V1.6 Integration Coordinator owns the decision and any merge |

## What this audit did

Read the engine, the Electron main process, the packaging tooling, the frozen release records, the
failure ledger, and the scratch probes the team wrote while debugging real incidents. Measured what
could be measured on this machine. Did not implement, prototype, or benchmark a Rust rewrite — none
is recommended.

## What was verified this session (first-hand)

| Check | Command | Result |
|---|---|---|
| Engine suite collects | `cd runtime && python -m pytest tests -q --collect-only` | **592 tests collected** in 0.16 s |
| Engine syntax | `py_compile` over all 47 `runtime/kel/*.py` | **0 failures** |
| Third-party surface | AST import scan over all 47 files | **`['websocket']` only** (transcription realtime socket); everything else stdlib |
| Python | `python --version` | 3.14.3 |
| Engine allowlist DB | `runtime/kel/../../basic-ux-sweep/14_FINDINGS_AND_FIXES.md` F11/F12 | read directly |

## What was NOT verified

- No Rust prototype was built, so every cost figure in `06_RISK_AND_ROLLBACK.md` is an
  order-of-magnitude estimate from scope, explicitly labelled as such.
- The engine test suite was **collected**, not fully executed, in this audit session. Pass counts
  (545 / 568 / 574 / 592) are quoted from the program's own frozen records
  (`docs/v1.6/00_CHECKPOINT_FREEZE.md`, `docs/v1.6/AUTO_RESUME.md`), not re-run here.
- Linux/WSL paths (`native_group.py`, `wsl_runtime.py`) were read, not exercised. This is a
  Windows-first product; conclusions there rest on code reading only.
- No cross-machine performance basis exists in the repository, and I did not create one.

## Post-audit re-verification against the moving branch

The instruction warned that the integration branch may move during this audit, and it did. Partway
through, `ux/v15-journeys` advanced from the audited `ffeef73` to **`70d68e4`** as the parallel V1.6
program landed Phase 3 (in-chat approvals) — two commits, `85e99fb` and `70d68e4`. That work is the
main program's, not this audit's; **this audit wrote nothing to `kel-ux-v15` and did not move its
HEAD.**

Because both of this audit's architectural findings are the basis of the recommendation, they were
re-checked against the live `70d68e4` rather than left resting on the pinned commit:

| Finding | Status at live `70d68e4` | How checked |
|---|---|---|
| **E7** — `engine_version` not validated on engine reuse | **Still open.** A repository-wide search for *any* `engine_version` / `engineVersion` comparison in `desktop/packages/desktop/src/` returns none. The descriptor is parsed at `KelService.ts:46` and `:112` and used only for `url` and `token` | `grep -rn` for all four comparison forms → no match |
| **E2/A2** — `apply_pending_restore` failure swallowed | **Still open.** `service.py:38-42` is unchanged: the call is still wrapped in `except Exception: pass` | direct read at live HEAD |

Both findings therefore hold on the newer commit, so the recommendation does not depend on the audit
having been pinned to a superseded revision. The architecture described in `01` also still holds:
the `ffeef73..70d68e4` delta touches `chat_approvals.py` (+314), `service.py` (+34), `authorize.py`
(+28), `core.py` (+8), `engine.py` (+4) and `KelService.ts` (+34) — it *adds* to the approval state
machine and the IPC route table without changing the process model, the transports, or the ownership
map.

## The short version

Rust is **not** justified now. The one genuinely architectural defect this audit found — the engine
is deliberately detached from Electron, but `engine_version` is never validated when an existing
engine is reused — is a **protocol gap, not a language problem**, and closes in roughly twenty lines
of the TypeScript and Python already present. Everything else in the pain ledger is an ordinary bug
that Rust would not have prevented.

Details, subsystem by subsystem, follow.
