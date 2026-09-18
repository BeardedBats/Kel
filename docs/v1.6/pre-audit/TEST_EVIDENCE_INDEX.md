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

## Discrimination log (regression fixes)

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
