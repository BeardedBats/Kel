# MARATHON_STATE — continuous Campaign A execution

MARATHON_MODE: ACTIVE

start_head: 756218e (published docs tip; production 8a677d0)
current_head: `594b8b4` + R0 docs commit (see `git log --oneline -8`)

completed_this_run:
- repository truth re-reconciled (branch/clean/remote/frozen refs/stash/watch) — sole writer confirmed
- MARATHON_STATE created; engine suite re-run at the R0 boundary: **931 passed + 10 subtests**
- **R0 COMPLETE** — P2/P3 sweep 100% dispositioned (26 rows in-table: P2 10, P3 16; directive's 27
  recorded for Campaign B). Commits: SEC-01 `49e528e` (vetting acting scope), TR-01 `8ab7699`
  (stream lifecycle closes + optional scope), COR-06/ERR-01 `5950efb` (dispatch plain sentences),
  APR-05 `dd34ac2` (poll path DDL-free, migration v20), COR-03/APR-06/THM-01 `594b8b4` (truthful
  failure surfaces); TR-02 bound to R9.A/R10; REL-01 stays the only OPEN_RELEASE_BLOCKER (R8)
- breadcrumbs: P2_P3_DISPOSITION (26/26 + completion record), increments/R0-SWEEP.md, COMMIT_LEDGER,
  CHANGE_LEDGER (CHG-012..017), REQUIREMENTS_TRACEABILITY (7 REQ rows), TEST_EVIDENCE_INDEX (A-20),
  MAIN_STATUS, AUTO_RESUME

current_phase: R1 — delegation authority ceiling
current_item: R1.A — audit the real current issuance path (D1/D2/D3, assignment grants, role ceilings, leases, runtime/provider binding, tool filtering) before writing any narrowing check

next_queue:
1. R1 — narrowing function + discriminating widen-attempt tests (existing primitives only; no nesting)
2. R2 — logical-work/idempotency matrix + real gaps
3. R3 — durable retry/recovery budgets
4. R4 — canonical approval binding (APPROVAL-EXACT; absorbs declared-conversation hardening)
5. R5 — persistence integrity contract + adversarial tests
6. R6 — truthful state + liveness separation (+ RECOVERY-CLASSIFICATION)
7. R7 — credential/network boundary proof (CREDENTIAL-CONTAINMENT)
8. R8 — packaged/migration assertions + REL-01 (minimum marathon return gate)
9. R9 — Visual batches 6–8 + Needs Your Attention (derived-only)
10. R10 — engine-loss/recovery UX
11. R11 — Visual → Main integration
12. R12 — final Campaign A regression → PRE_AUDIT_V1_6_HEAD

last_focused_tests: R0 row-level suites — vetting 36, transcription 31, sweep-fixes 15, approvals + restore green
last_full_engine: **931 passed + 10 subtests** (258.82s) at `594b8b4` (was 915 at `8a677d0`)
last_desktop_tsc: 0 errors (`tsc -p tsconfig.json --noEmit`)
last_desktop_vitest: **93 passed** (8 files)
last_packaged: `package-logo` era (71c78f0); rebranding verified; R8 refreshes

last_push: `594b8b4` → origin/ux/v15-journeys (R0 docs commit follows)
last_scan: 0 real hits (R0 commits — no secrets/private data; docs-only additions)

blocker: NONE

return_allowed: NO
(gate: R0–R12 complete → PRE_AUDIT_V1_6_HEAD, or a genuine human stop condition
per the marathon directive §32. A clean checkpoint is never a stopping point.)
