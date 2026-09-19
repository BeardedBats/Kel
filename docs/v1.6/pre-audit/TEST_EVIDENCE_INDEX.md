# TEST_EVIDENCE_INDEX — test runs with command, commit, date, result

updated: 2026-09-18T16:05Z

Category column: `parent-executed` (run by the implementing thread — most rows) ·
`independent` (run/verified by a separate fresh-context reviewer) · `fresh-clone` · `packaged`
(points to PACKAGED_EVIDENCE_INDEX.md) · `human` (human-executed).

## Campaign A baseline

| # | Suite | Command | Commit | Date | Result | Count | Reqs | Invariants | Evidence | Category |
|---|---|---|---|---|---|---|---|---|---|---|
| A-1 | engine full suite | `cd runtime && python -m pytest tests -q` (Python 3.14.3) | `fd98cc4` | 2026-09-18 | PASS | **878 passed, 10 subtests passed** (251.55s) | all engine reqs | INV-CAP/MEM/WF | `evidence/campaign-a-baseline/engine-suite-20260918.txt` | parent-executed |
| A-2 | desktop typecheck + unit | `cd desktop && bunx tsc --noEmit && bun run test` | `22f4a3e` | 2026-09-18 | PASS | tsc 0 errors; **83 passed / 6 files** (was 76; +7 Phase-6 gating tests) | desktop reqs; REQ-MEM-6 | — | `increments/PHASE6-MEMORY-REALITY.md` | parent-executed |
| A-3 | engine focused memory suites | `cd runtime && python -m pytest tests/test_v13_memory.py tests/test_v15_memory_packets.py tests/test_v16_proposals.py tests/test_workforce_learning.py -q` | `22f4a3e` (engine unchanged since `fd98cc4`) | 2026-09-18 | PASS | **68 passed** | REQ-MEM-1/6; INV-MEM-001..003 | `increments/PHASE6-MEMORY-REALITY.md` | parent-executed |
| A-4 | engine focused capabilities suites (Phase 7) | `cd runtime && python -m pytest tests/test_capabilities.py tests/test_research.py tests/test_acp_host.py tests/test_v13_work_context.py tests/test_v15_completion.py -q` | `df87903` | 2026-09-18 | PASS | **83 passed** (26.03s) | REQ-CAPREC-7; INV-CAP-001/002, INV-CAPREC-001 | `increments/PHASE7-CAPABILITY-RECOMMENDATIONS.md` | parent-executed |
| A-5 | desktop typecheck + unit (Phase 7) | `cd desktop && bunx tsc --noEmit && bun run test` | `df87903` | 2026-09-18 | PASS | tsc 0 errors; **90 passed / 7 files** (was 83; +7 recommendation tests) | desktop reqs; REQ-CAPREC-7 | — | `increments/PHASE7-CAPABILITY-RECOMMENDATIONS.md` | parent-executed |
| A-6 | engine full suite (Phase 7) | `cd runtime && python -m pytest tests -q` | `df87903` | 2026-09-18 | PASS | **885 passed, 10 subtests passed** (249.57s; was 878 — +7 new tests, zero regressions) | all engine reqs | INV-CAP-001/002, INV-CAPREC-001 | `increments/PHASE7-CAPABILITY-RECOMMENDATIONS.md` | parent-executed |
| A-7 | provider/assignment focused (Phase 10) | `cd runtime && python -m pytest tests/test_v14_providers.py tests/test_workforce_assignment.py -q` | `df87903` (engine unchanged) | 2026-09-18 | PASS | **55 passed** (6.44s) | REQ-PROV-10 | — | `docs/v1.6/phase10/PROVIDER_VALIDATION.md` | parent-executed |
| A-8 | claude native CLI real call | `claude -p "Reply with exactly: ok"` (neutral cwd, 90s timeout) | `df87903` | 2026-09-18 | PASS | returned `ok` (exit 0); client `2.1.215` | REQ-PROV-10 | — | `docs/v1.6/phase10/PROVIDER_VALIDATION.md` | parent-executed (real call) |
| A-9 | codex native CLI real attempt | `codex exec --skip-git-repo-check "Reply with exactly: ok"` (120s timeout) | `df87903` | 2026-09-18 | FAIL (environment) | HTTP 400: `'gpt-6-astra' model requires a newer version of Codex`; client `0.142.5` | REQ-PROV-10 | — | `docs/v1.6/phase10/PROVIDER_VALIDATION.md` | parent-executed (real attempt — recorded as limitation, never a pass) |
| A-10 | desktop typecheck + unit (canonical logo) | `cd desktop && bunx tsc --noEmit && bun run test` | branding commit | 2026-09-18 | PASS | tsc 0 errors; **90 passed / 7 files** | REQ-LOGO-1 | — | `increments/LOGO-CANONICAL.md` | parent-executed |
| A-11 | brand-asset generation + determinism | `python scripts/make-brand-assets.py "…/Kel Logo.png"` then `--check` | branding commit | 2026-09-18 | PASS | 10 outputs; stable hashes; canonical sha256 guard (`7418a42f…`) | REQ-LOGO-1 | — | `docs/v1.6/branding/CANONICAL_LOGO.md` §2 | parent-executed |
| A-12 | packaged branding verification | `[System.Drawing.Icon]::ExtractAssociatedIcon` on `Kel.exe` + the NSIS installer, then `python scripts/verify-brand-render.py dist/logo-evidence/ux-audit --sizes 40,48,56,64,72,80` | branding commit | 2026-09-18 | PASS | exe icon = shipped `app.ico` frame (mad **0.0**), installer icon **0.0**, previous package not the K (73.2); About capture matches the canonical art at **0.960** masked NCC; harness `errors: []` | REQ-LOGO-1 | — | `docs/v1.6/branding/evidence/README.md` | parent-executed (packaged) |
| A-13 | engine full suite (REQ-RK resolution kinds) | `cd runtime && python -m pytest tests -q` | `a547936` | 2026-09-18 | PASS | **891 passed, 10 subtests passed** (250.14s; was 885 — +6 new tests, zero regressions) | REQ-RK | INV-RK-001 | `increments/REQ-RK-RESOLUTION-KIND.md` | parent-executed |
| A-14 | engine full suite (REQ-F4 real-artifact binding) | `cd runtime && python -m pytest tests -q` | `081a6ef` | 2026-09-18 | PASS | **895 passed, 10 subtests passed** (255.90s; was 891 — +4 new tests, zero regressions). First run of the new gate flagged 8 failures + 5 errors in fixture harnesses (`test_workforce_d2.py`, `test_workforce_parallel.py`) which now record their deliveries | REQ-F4 | INV-F4-001 | `increments/REQ-F4-REAL-ARTIFACT-BINDING.md` | parent-executed |
| A-15 | engine full suite (PER-02 restore visibility) | `cd runtime && python -m pytest tests -q` | `df1997a` | 2026-09-18 | PASS | **900 passed, 10 subtests passed** (253.45s; was 895 — +5 new tests, zero regressions); focused `test_v16_restore_visibility.py` + `test_backup.py` = 14 passed | PER-02 | INV-PER02-001 | `increments/PER-02-RESTORE-VISIBILITY.md` | parent-executed |
| A-16 | engine full suite + desktop typecheck (sweep batch 2) | `cd runtime && python -m pytest tests -q`; `cd desktop && bunx tsc --noEmit` | `0596211` | 2026-09-18 | PASS | **905 passed, 10 subtests passed** (251.00s; was 900 — +5 new tests, zero regressions); focused sweep-fix + backup + transcription = 41 passed; tsc 0 | INT-01, SEC-01-multipart, PER-04 | INV-SWEEP2-001 | `increments/P2P3-BATCH2-IPC-HEADER-BACKUP.md` | parent-executed (IPC guard by parity, no harness — §58) |
| A-17 | desktop typecheck + unit suite (A1 engine-version binding) | `cd desktop && bunx tsc --noEmit && bun run test` | `101d8c3` | 2026-09-18 | PASS | tsc 0 errors; **93 passed / 8 files** (was 90 — +3 new tests) | A1 / ENG-01 | INV-A1-001 | `increments/A1-ENGINE-VERSION-BINDING.md` | parent-executed (decision unit-tested; spawn wiring typecheck-only — §59) |
| A-18 | engine full suite (sweep batch 3: snapshots + actor guard) | `cd runtime && python -m pytest tests -q` | `84b5646` | 2026-09-18 | PASS | **909 passed, 10 subtests passed** (252.08s; was 905 — +4 new tests, zero regressions); focused sweep-fix + backup + transcription = 45 passed | PER-03, APR-01 | INV-PER03-001 | `increments/P2P3-BATCH3-SNAPSHOTS-SCOPE.md` | parent-executed |
| A-19 | engine full suite + desktop suite (R0 / APR-02 approval scope) | `cd runtime && python -m pytest tests -q`; `cd desktop && bunx tsc --noEmit && bun run test` | `8a677d0` | 2026-09-18 | PASS | **915 passed, 10 subtests passed** (264.24s; was 909 — +6 new tests, zero regressions); focused approvals + sweep-fix = 33 passed; desktop tsc 0, vitest 93 | APR-02 (R0) | INV-APPROVE-002 (partial) | `increments/R0-APR02-APPROVAL-SCOPE.md` | parent-executed |
| A-20 | engine full suite + desktop typecheck/suite (R0 sweep completion: SEC-01, TR-01, COR-06/ERR-01, APR-05, COR-03/APR-06/THM-01) | `cd runtime && python -m pytest tests -q`; `cd desktop && bunx tsc -p tsconfig.json --noEmit && bunx vitest run` | `594b8b4` | 2026-09-18 | PASS | **931 passed, 10 subtests passed** (258.82s; was 915 — +16 new tests, zero regressions); focused: `test_vetting.py` 36, `test_transcription.py` 31, `test_v16_sweep_fixes.py` 15, approvals + restore-visibility green; desktop tsc 0 errors, **vitest 93 passed (8 files)** | SEC-01, TR-01, TR-02 (deferred-binding), APR-05, APR-06, COR-03, COR-06, THM-01, ERR-01 | INV-SWEEP4-001 | `increments/R0-SWEEP.md` | parent-executed (renderer rows verified by tsc + code read only — §58) |
| A-21 | engine full suite (R1 delegation authority ceiling / AUTH-DELEGATION) | `cd runtime && python -m pytest tests -q`; focused `tests/test_v16_r1_authority.py` + the workforce family | `dc65fbc` | 2026-09-18 | PASS | **952 passed, 10 subtests passed** (287.14s; was 931 — +21 new tests, zero regressions); focused: R1 21, workforce family (schemas/assignment/d1/d2/learning/parallel/assurance) 269 together | REQ-R25-R1 | INV-AUTH-DELEGATION | `increments/R1-AUTHORITY-CEILING.md` | parent-executed |
| A-22 | engine full suite (R2 idempotency matrix + observed-effect receipt) | `cd runtime && python -m pytest tests -q` | `fde5bbb` | 2026-09-18 | PASS | **962 passed, 10 subtests passed** (264.89s; was 952 — +10 new tests, zero regressions) | REQ-R25-R2 | INV-EVENT-IDEMPOTENCY; INV-EFFECT-REPLAY | `increments/R2-IDEMPOTENCY-MATRIX.md` | parent-executed |
| A-23 | engine full suite (R3 retry durability + R4 approval window) | `cd runtime && python -m pytest tests -q`; focused recovery + authorization families | `8c899c8` | 2026-09-18 | PASS | **974 passed, 10 subtests passed** (269.43s; was 962 — +12 new tests (5 R3 + 7 R4), zero regressions); focused: recovery family 24, authorization family 96 | REQ-R25-R3; REQ-R25-R4 | INV-RETRY-DURABLE; INV-APPROVAL-EXACT | `increments/R3-RETRY-DURABILITY.md`; `increments/R4-APPROVAL-EXACT.md` | parent-executed |
| A-24 | engine full suite (R5 canonical persistence) | `cd runtime && python -m pytest tests -q`; focused R2–R5 + core | `b2ffed1` | 2026-09-18 | PASS | **981 passed, 10 subtests passed** (270.51s; was 974 — +7 new tests, zero regressions); focused: R2–R5 + `test_core` 84 passed | REQ-R25-R5 | INV-PERSIST-CANONICAL | `increments/R5-PERSISTENCE-INTEGRITY.md` | parent-executed |
| A-25 | focused suites (R6 truthful state / liveness) | `tests/test_v16_r6_liveness.py` + diagnostics/core families | `b2ffed1`+R6 tests | 2026-09-18 | PASS | R6 suite **5 passed**; the R6 increment adds no production change, so the next full-suite row (A-26, R7 boundary) carries the end-to-end count | REQ-R25-R6 | INV-LIVENESS-SEPARATION; INV-COMPLETION-TRUTH; INV-RECOVERY-CLASSIFICATION | `increments/R6-TRUTHFUL-STATE.md` | parent-executed |
| A-26 | engine full suite (R7 credential containment + R8 migrations/identity/REL-01) | `cd runtime && python -m pytest tests -q`; focused R7 + R8 suites; the freeze fixture and the packaged probe | `022f3ac` | 2026-09-18 | PASS | **998 passed, 10 subtests passed** (was 981 at `b2ffed1`); focused: R7 5, R8 migrations 4, R8 identity 3, boundaries 13 with the identity fix; plus the frozen load-path engine boot probe (`engine_version 1.6.0`, 4 providers, `connected`/`guardrails_ok`) and `scripts/validate-freeze.ps1` (positive + negative) | REQ-R25-R7; REQ-R25-R8; REL-01 | INV-CREDENTIAL-CONTAINMENT; INV-PACKAGE-IDENTITY; INV-FREEZE-IMMUTABLE | `increments/R7-CREDENTIAL-BOUNDARY.md`; `increments/R8-PACKAGE-ASSERTIONS.md` | parent-executed |
| A-27 | desktop typecheck + unit suite (R8.B engine identity) | `cd desktop && bunx tsc -p tsconfig.json --noEmit && bunx vitest run` | `022f3ac` | 2026-09-18 | PASS | tsc 0 errors; vitest **8 files / 93 tests passed**, including the new `engineVersion.test.ts` (verified separately: 1 file, 3 tests) | REQ-R25-R8 | INV-PACKAGE-IDENTITY | `increments/R8-PACKAGE-ASSERTIONS.md` | parent-executed (composition note for Campaign B: the pre-R8 runs also reported 8 files / 93 tests at A-20; the engine-version file is confirmed collected and green by a filtered run) |

Note: A-1 ran on the Main worktree at `fd98cc4` (no renderer changes involved). A-2/A-3 ran at
`22f4a3e` (Phase 6). The last visual-branch desktop numbers remain `ac85eb3`: tsc 0, **79/79**.

## Historical runs in the audited range (from AUTO_RESUME.md / phase records)

| # | Suite | Commit | Date | Result | Count | Evidence | Category |
|---|---|---|---|---|---|---|---|
| H-1 | engine full after 5.6 remediation | `8a2b25d` | 2026-09-18 | PASS | 878 (+10 subtests; baseline 853) | 5.6_IMPLEMENTATION_RECORD.md; audit increment 24 | parent-executed; artifacts reviewed by independent audit 24 |
| H-2 | engine focused 5.6 remediation | `8a2b25d` | 2026-09-18 | PASS | 25 | idem; discriminating for F23-1..F23-10 | parent-executed |
| H-3 | engine full 5.6 | `ba52869` | 2026-09-18 | PASS | 876 (+10; baseline 853) | 5.6 record | parent-executed |
| H-4 | engine full 5.5 arc | `5f77f42` → `d8880f3` | 2026-09-17 | PASS | 842 → 851 → 853 | 5.5 record; audits 20–22 | parent-executed |
| H-5 | engine full 5.4 arc | `932db33` → `f25a4bf` | 2026-09-17 | PASS | 791 → 805 (+3 +3) | 5.4 record; audits 16–19 | parent-executed |
| H-6 | engine full 5.3 arc | `48dacb3` → `5747567` | 2026-09-17 | PASS | 765 → 767 | 5.3 record; audits 14/15 | parent-executed |
| H-7 | engine full 5.2 arc | `894be5b` → `f9cf3ea` | 2026-09-17 | PASS | 717 → 724 | 5.2 record; audits 12/13 | parent-executed |
| H-8 | engine full 5.1 arc | `9d6ed55` → `5b83f0e` | 2026-09-17 | PASS | 689 → 693 | 5.1 record; audits 10/11 | parent-executed |
| H-9 | engine full 5.0 arc | `9085335` → `cc909b9` | 2026-09-17 | PASS | 658 | 5.0 record; audits 8/9 | parent-executed |
| H-10 | engine full Phase 4 | `fd04c00` | 2026-09-17 | PASS | 613 | i18n record; audit 7 | parent-executed |
| H-11 | desktop after Phase 4 | `fd04c00` | 2026-09-17 | PASS | tsc 0; vitest 76 | i18n record; audit 7 | parent-executed |
| H-12 | engine 545-suite (session-tools closure) | pre-1.6 arc | 2026-09-17 | PASS | 545 | docs/session-tools/ | parent-executed |
| H-13 | clone-clean runs (v1.5 gates) | `6f65ef0`, `9841395` era | 2026-09-16 | PASS | — | docs/v1.5/ | fresh-clone |

## Packaged journeys (summaries; full detail in PACKAGED_EVIDENCE_INDEX.md)

| # | Journey | Package | Result | Evidence | Category |
|---|---|---|---|---|---|
| P-1 | sessiontools + engine capability probe | `package-p1cap` | PASS | ux-audit/run-p1-capabilities.sh | packaged |
| P-2 | sessiontools + CAP2-clause probes + engine probe | `package-p1cap2` | PASS | ux-audit/run-cap2-clause.sh | packaged |
| P-3 | sessiontools reserved/residual + db probes + engine probe | `package-p1cap3` | PASS | ux-audit/run-cap2-residual.sh | packaged |
| P-4 | approvals journey + lineage probe | `package-final16` | PASS | ux-audit/run-approvals.sh; run-lineage-probe.sh | packaged |
| P-5 | memory proposals journey | `package-final13` | PASS | ux-audit/run-memoryprops.sh | packaged |
| P-6 | Phase 4 copy-scan + standing journeys | `package-final17` | PASS | ux-audit/run-phase4.sh | packaged |
| P-7 | visual5 probes a/b/c | `package-visual5` | PASS (probe b reproduces engine-loss findings 16/17 — recorded, not a regression) | ux-audit/visual/runs/visual5-{a,b,c} | packaged |
| P-8 | R10 engine-loss/recovery journeys (kill → reconnecting → supervised restart → durable preserved → repeat → could-not-recover → manual retry) | `package-r12` era (lane package, engine 1.6.0) | PASS — r10-g full (5 screenshots), r10-f fast-fail focused (2 screenshots); DOM leak scan clean; console 0 | ux-audit/runs/r10-{f,g}/ | packaged |
| P-9 | R12 installed probes: fresh + upgrade-DB (installer → silent install → launch → Work/attention/About → uninstall) | `package-r12` (installed) | PASS — exit-0 install; healthy 1.6.0; attention section present; About K renders; 0 leaks; 0 console errors; 0 horizontal overflow (5 routes) | ux-audit/runs/r12-{fresh2,upgrade,upgrade-out,r12-installed}; r12-install-result.json | packaged |

## A-28 — R10 packaged engine-loss/recovery journey (2026-09-18)

Command: `node ux-audit/r10-engine-loss-probe.cjs <appDir> <root> <out>` + `r10-d-cannot-restart.cjs`.
Result: **PASS** (r10-f/r10-g on the final lane package with the frozen 1.6.0 engine; the full
journey required sequence mapped in `docs/v1.6-visual-ux/19_R10_ENGINE_LOSS_EVIDENCE.md`;
`[KEL-LINK]` transitions: connected → reconnecting → recovered ×2 → unrecoverable → manual
retry → recovered). Category: packaged/journey. Note: engine variants not constructible in the
isolated profile (approval-wait loss, effect reconciliation) are covered at engine level (A-29).

## A-29 — R12 final Campaign A battery (2026-09-19)

- Engine full suite on the merged tree: **998 passed + 10 subtests** (284.53s) — log
  `ux-audit/r12-engine-suite.log` (`ENGINE_EXIT=0`). Includes the failure-injection families:
  `test_v16_r2_idempotency` (duplicate submission/result), `test_v16_r4_approval_exact`
  (approval misuse/mutation/window), `test_v16_r5_persistence` (malformed payloads),
  `test_v16_r6_liveness` (stale run/liveness separation), `test_v16_r7_credentials`,
  `test_v16_r8_identity`/`test_v16_r8_migrations` (runtime identity mismatch, fresh/upgrade DB,
  all V1.6 migrations), `test_v16_restore_visibility` (restore failure), `test_v16_r1_authority`
  + `test_v16_r3_retry_durability` (authority widening, retry exhaustion), `test_v16_approvals`
  + `test_v16_sweep_fixes` (cross-scope ids, leases), workforce D1–D3 suites (verification
  failure, evidence binding), provider tests (`test_v14_providers.py`).
- Desktop on the merged tree: `tsc` 0; vitest **122/122** (12 files).
- R12 installed battery: see P-9 row. Installed package metadata: `Kel · Kel · 1.6.0`;
  Add/Remove `DisplayName=Kel · Publisher=Kel · DisplayVersion=1.6.0`; engine SHA-256
  `69123AF0…` equals the frozen runtime; install → uninstall lifecycle clean (dir, registry,
  desktop + start-menu links removed).
- Release integrity: `ux-audit/runs/r12-integrity.txt` (remote exact; frozen refs unchanged;
  secret scan 0 actionable; no force push).
- Packaged upgrade-DB boot: populated 1.6.0 data root booted on the installed app with all
  conversations preserved, zero console errors (`ux-audit/runs/r12-upgrade/`).

## Discrimination log (regression fixes)

- R9/R10 supervision: r10-d/r10-e (pre-fail-fast) vs r10-f (post-fail-fast): could-not-recover
  arrives in ~5 s instead of ~95 s — the 45 s-per-attempt burn was measured, fixed (`fa66f04`),
  and re-measured.

Per §14 of the sprint directive, record discrimination where practical. `FAILS_PRE_FIX` /
`PASSES_POST_FIX` pairs are recorded in the phase records; entries:

- 5.0 F1-F3: focused 45 post-fix; discrimination in `22_PHASE5_0_REAUDIT.md` closure table.
- 5.1 N1-N6: focused 35 post-fix (`5b83f0e`).
- 5.5 N21-1..5: 853 post-fix; discriminating tests recorded in `2a12b77` message + record.
- 5.6 F23-1..F23-10: focused 25; two new discriminating regressions + boundary assertions
  (`8a2b25d`).
- CAP2-CLAUSE: negative control executes the pre-fix parser from git (`85cf0f1`) proving it
  rewrote text; post-fix corpus byte-identity. `test_capabilities.py`.
- CAP2-RESIDUAL: same negative-control pattern vs `4f6535a`. `test_capabilities.py`.

## Maintenance rules

- Add a row per meaningful run; never edit a historical row (append corrections).
- Counts must be the literal pytest/vitest line; evidence paths must exist.
