# MARATHON_STATE — continuous Campaign A execution

MARATHON_MODE: ACTIVE

start_head: 756218e (published docs tip; production 8a677d0)
current_head: `05608e6` (docs: denominator reconciliation) + R9 visual lane `938dc9b`/`96979c7` (see `git log --oneline -20` in both worktrees)

completed_this_run:
- repository truth re-reconciled (branch/clean/remote/frozen refs/stash/watch) — sole writer confirmed
- **R0 COMPLETE** — P2/P3 sweep 100% dispositioned (26 rows in-table: P2 10, P3 16; directive's 27
  recorded for Campaign B). Commits: SEC-01 `49e528e`, TR-01 `8ab7699`, COR-06/ERR-01 `5950efb`,
  APR-05 `dd34ac2`, COR-03/APR-06/THM-01 `594b8b4`; TR-02 bound to R9.A/R10; REL-01 stays the only
  OPEN_RELEASE_BLOCKER (R8). Evidence: A-20 (**931 passed**), `increments/R0-SWEEP.md`.
- **R1 COMPLETE** — delegation authority ceiling executable (`dc65fbc`): `authority_within` +
  `validate_task_contract(parent_authority=…)` + D1/D2 wiring (verifier inside the mission envelope)
  + `reserve_budget` job-envelope check; 21 new tests; evidence A-21 (**952 passed + 10 subtests**),
  `increments/R1-AUTHORITY-CEILING.md`, INV-AUTH-DELEGATION, REQ-R25-R1 implemented.
- **R2–R6 COMPLETE** — R2 idempotency matrix + observed-effect receipt (`fde5bbb`), R3 retry
  durability inventory + restart tests (`1a9f538`), R4 APPROVAL-EXACT window check (`8c899c8`),
  R5 canonical persistence (`b2ffed1`), R6 truthful state/liveness (inventory + tests). Evidence:
  A-22..A-25, `increments/R2…`–`R6…`, CHG-019..021, INV-RETRY-DURABLE / INV-APPROVAL-EXACT /
  INV-PERSIST-CANONICAL / INV-LIVENESS-SEPARATION / INV-COMPLETION-TRUTH / INV-RECOVERY-CLASSIFICATION.
- breadcrumbs kept current for R0 through R6: P2_P3_DISPOSITION, COMMIT_LEDGER, CHANGE_LEDGER
  (CHG-012…018), REQUIREMENTS_TRACEABILITY (REQ-R25-R1), INVARIANT_LEDGER, TEST_EVIDENCE_INDEX,
  MAIN_STATUS, AUTO_RESUME

- **R9 COMPLETE on the visual lane** — lane reconciled (zero production-file overlap with Main
  since base `60b2322`; `0ff061d`), re-anchored on Main `05608e6` (pure-union merge `3050761`, the
  batch-1–5 files byte-identical), then batches 6 (engine loss / failure states + supervision;
  `2897207`), 7 (composer owns model/tools/memory; `0e7d21a`), 8 (normalization; `c911d81`),
  R9.D (**Needs Your Attention** derived-only + hostile project-isolation tests; `938dc9b`) and
  the R9 evidence index (`96979c7`). Acceptance: tsc 0, vitest **122/122**. Bookkeeping: the
  27-vs-26 P2/P3 denominator is RECONCILED (`05608e6`; every original finding ID mapped;
  no closed finding reopened; no repo gap found).
- **R10 IN PROGRESS** — packaged journey: `Kel-1.6.0` win-unpacked rebuilt from the re-anchored
  lane, bundling the frozen **1.6.0** engine (the visual worktree's `dist/runtime/KelEngine` was
  a stale 1.5.0 bundle — replaced from `kel-ux-v15/dist/runtime/KelEngine`, verified 1.6.0 in the
  package). The packaged engine-loss probe (kill → reconnecting → supervised restart → durable
  folder preserved → repeat loss → could-not-recover → manual retry; `desktop-link.log`
  transitions; screenshots; raw-leak scan) is running.
- breadcrumbs kept current for R0 through R6: P2_P3_DISPOSITION, COMMIT_LEDGER, CHANGE_LEDGER
  (CHG-012…018), REQUIREMENTS_TRACEABILITY (REQ-R25-R1), INVARIANT_LEDGER, TEST_EVIDENCE_INDEX,
  MAIN_STATUS, AUTO_RESUME

current_phase: R10 - engine-loss/recovery packaged journey
current_item: R10 - run + collect the packaged journey (session `51g2x4zf`), then write the R10 evidence record

next_queue:
1. R10 — finish the packaged engine-loss/recovery journey + record evidence (screenshots, link log)
2. R11 — Visual → Main integration (before-mutation checks; resolve KelService/transcription/
   KelWorkPanel overlaps on current semantics; tsc + vitest + packaged probes after)
3. R12 — final Campaign A regression: full engine suite, desktop suite, packaged/installed
   battery (installer, icons, About, console), failure injection, release integrity
4. PRE_AUDIT_V1_6_HEAD — finalize the pre-audit corpus + the Campaign B handoff

last_focused_tests: R9 lane: desktop vitest 122/122 (12 files) + tsc 0 (visual lane tip `938dc9b`)
last_full_engine: **981 passed + 10 subtests** (270.51s) at `b2ffed1` (was 974 at `8c899c8`)
last_desktop_tsc: 0 errors (visual lane, R9 batches 6-8 + R9.D; main lane 93-era still green)
last_desktop_vitest: **122 passed** (12 files, R9 lane)
last_packaged: `Kel-1.6.0` win-unpacked (visual lane, engine 1.6.0 verified) + R10 journey in flight

last_push: `93b99b5` -> origin/ux/v15-journeys (R7/R8 breadcrumbs follow)
last_scan: 0 real hits (R0/R1 commits — no secrets/private data)

blocker: NONE

return_allowed: NO
(gate: R0–R12 complete → PRE_AUDIT_V1_6_HEAD, or a genuine human stop condition
per the marathon directive §32. A clean checkpoint is never a stopping point.)
