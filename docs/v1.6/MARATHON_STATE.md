# MARATHON_STATE — continuous Campaign A execution

MARATHON_MODE: ACTIVE

start_head: 756218e (published docs tip; production 8a677d0)
current_head: `b2ffed1` (R5) + R6 tests/breadcrumbs (see `git log --oneline -14`)

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

current_phase: R7 — credential / network boundary (CREDENTIAL-CONTAINMENT)
current_item: R7.A — inventory every place a credential could become prompt text, ambient env, artifact, packet, log or export; then sentinel tests

next_queue:
1. R2 — matrix + repair only demonstrated duplicate-execution gaps + hostile duplicate tests
2. R3 — durable retry/recovery budgets
3. R4 — canonical approval binding (APPROVAL-EXACT; absorbs declared-conversation hardening)
4. R5 — persistence integrity contract + adversarial tests
5. R6 — truthful state + liveness separation (+ RECOVERY-CLASSIFICATION)
6. R7 — credential/network boundary proof (CREDENTIAL-CONTAINMENT)
7. R8 — packaged/migration assertions + REL-01 (minimum marathon return gate)
8. R9 — Visual batches 6–8 + Needs Your Attention (derived-only)
9. R10 — engine-loss/recovery UX
10. R11 — Visual → Main integration
11. R12 — final Campaign A regression → PRE_AUDIT_V1_6_HEAD

last_focused_tests: R6 liveness 5; R2–R5 + core 84 together
last_full_engine: **981 passed + 10 subtests** (270.51s) at `b2ffed1` (was 974 at `8c899c8`)
last_desktop_tsc: 0 errors (`tsc -p tsconfig.json --noEmit`, R0 batch)
last_desktop_vitest: **93 passed** (8 files, R0 batch)
last_packaged: `package-logo` era (71c78f0); rebranding verified; R8 refreshes

last_push: `b2ffed1` → origin/ux/v15-journeys (R6 breadcrumbs follow)
last_scan: 0 real hits (R0/R1 commits — no secrets/private data)

blocker: NONE

return_allowed: NO
(gate: R0–R12 complete → PRE_AUDIT_V1_6_HEAD, or a genuine human stop condition
per the marathon directive §32. A clean checkpoint is never a stopping point.)
