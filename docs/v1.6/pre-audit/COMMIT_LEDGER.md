# COMMIT_LEDGER — production-affecting commits, audited point → PRE_AUDIT_V1_6_HEAD

updated: 2026-09-18T16:05Z
range opens at: `8a2b25d` (last independently audited production point; increment 24 CONTINUE)
range ends at: PRE_AUDIT_V1_6_HEAD (TBD; recorded at RC)
first intentionally unaudited production commit: `22f4a3e` (2026-09-18, Phase 6 bounded fixes)
rule: EVERY production-affecting commit in this range must appear here. Docs-only commits are
listed for completeness with `priority: LOW / docs-only`.

Columns: SHA | parent | date (local) | phase | increment | intent | production files | tests |
migrations | UI? | packaged impact? | sec/privacy? | persistence? | priority | evidence | known concerns

## Commits above the audited point at corpus open (docs-only, verified per-commit)

| SHA | parent | date | intent | class | priority | evidence |
|---|---|---|---|---|---|---|
| `c4ae724` | `8a2b25d` | 2026-09-18 | Phase 5.6 remediation record + delta re-audit request | docs-only | LOW | `git show --stat` = 3 docs files |
| `5127bac` | `c4ae724` | 2026-09-18 | Phase 5.6 accepted — audit 24 CONTINUE; 5.7/5.8 decisions deferred | docs-only | LOW | `git show --stat` = 5 docs files |
| `fd98cc4` | `5127bac` | 2026-09-18 | record published integration tip; visual slice complete | docs-only | LOW | `git show --stat` = MAIN_STATUS only |

## Campaign A production commits (the intentionally-unaudited range)

| SHA | parent | date | phase | intent | production files | tests | migrations | UI? | packaged | sec/priv | persistence | priority | evidence | concerns |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `785df71` | `fd98cc4` | 2026-09-18 | A-entry | pre-audit corpus + IMPLEMENTATION_SPRINT mode (docs/state) | docs only; `.gitignore` scratch ignore | — | none | no | — | no | no | LOW | `increments/INIT-CAMPAIGN-A.md`; corpus README | — |
| `22f4a3e` | `785df71` | 2026-09-18 | Phase 6 | Work-panel knowledge actions follow record state; forget asks first | `KelWorkPanel.tsx`; `memoryRecordActions.ts` (new) | +7 unit tests (vitest 76→83) | none | yes (renderer) | pending (RC battery) | no | no | MEDIUM | `increments/PHASE6-MEMORY-REALITY.md`; `docs/v1.6/phase6/MEMORY_REALITY_AUDIT.md` | MEMR-1/2/3 |
| `ac5e2a2` | `22f4a3e` | 2026-09-18 | Phase 6 | Phase 6 record + corpus updates (docs) | docs only | — | none | no | — | no | no | LOW | `increments/PHASE6-MEMORY-REALITY.md` | — |
| `df87903` | `ac5e2a2` | 2026-09-18 | Phase 7 | capability recommendations: engine vocabulary + refusal wiring + milestone retention + desktop card | `capabilities.py`; `research.py`; `coding.py`; `core.py`; `KelCapabilityCard.tsx` (new); `capabilityRecommendation.ts` (new); `KelWorkPanel.tsx` | +7 engine, +7 desktop tests (885; 90) | none | yes (Work panel) | pending (no provider; RC battery) | no | no | MEDIUM | `increments/PHASE7-CAPABILITY-RECOMMENDATIONS.md`; `docs/v1.6/phase7/` | coding-blocked discrimination (audit target 44) |
| `16de55f` | `df87903` | 2026-09-18 | Phase 7 | Phase 7 record + corpus updates (docs) | docs only | — | none | no | — | no | no | LOW | `increments/PHASE7-CAPABILITY-RECOMMENDATIONS.md` | — |
| `7b32217` | `16de55f` | 2026-09-18 | Phase 7 | published-tip record + packaged pending item (docs) | docs only | — | none | no | — | no | no | LOW | `docs/v1.6/status/MAIN_STATUS.md`; PACKAGED_EVIDENCE_INDEX | — |
| `006159a` | `7b32217` | 2026-09-18 | Phase 8 | Advanced Worker View decision — deferred beyond V1.6 (docs) | docs only | — | none | no | — | no | no | LOW | `docs/v1.6/phase8/ADVANCED_WORKER_VIEW_DECISION.md` | decision to verify in Campaign B |
| `fa31618` | `006159a` | 2026-09-18 | Phase 7/8 | commit ledger rows for Phase 7 docs + Phase 8 decision commits (docs) | docs only | — | none | no | — | no | no | LOW | COMMIT_LEDGER.md | — |
| `6ea68c2` | `fa31618` | 2026-09-18 | Phase 9 | Profiles vs Projects decision — no Profiles concept; Projects remain (docs) | docs only | — | none | no | — | no | no | LOW | `docs/v1.6/phase9/PROFILES_VS_PROJECTS_DECISION.md` | decision to verify in Campaign B |
| `fed59dd` | `6ea68c2` | 2026-09-18 | Phases 10-11 | provider validation + Rust freshness recheck; Phase 12 closed (docs) | docs only | — | none | no | — | no | no | LOW | `docs/v1.6/phase10/PROVIDER_VALIDATION.md`; `docs/v1.6/phase11/RUST_FRESHNESS_RECHECK.md` | real-call evidence recorded (claude PASS; codex env-blocked) |
| `24d775b` | `fed59dd` | 2026-09-18 | Phases 8-11 | ledger rows for Phase 8-11 docs + published-tip refresh + (this commit: missing Phase 6 docs row) | docs only | — | none | no | — | no | no | LOW | COMMIT_LEDGER.md; MAIN_STATUS.md | — |
| `71c78f0` | `edd50de` | 2026-09-18 | REQ-LOGO-1 | canonical Kel logo (Nick directive) on every production-reachable branding surface | `desktop/resources/*` icons + `branding/kel-logo.png`; `desktop/public/pwa/*`; renderer brand asset; `AboutModalContent.tsx`; `kel-builder.json`; `scripts/make-brand-assets.py`; `scripts/verify-brand-render.py` | tsc 0; vitest 90; packaged exe+installer icon extraction (mad 0.0); About render 0.960 NCC | none | yes (About mark; login mark asset) | `package-logo` (PASS) | no | no | MEDIUM | `docs/v1.6/branding/CANONICAL_LOGO.md`; `increments/LOGO-CANONICAL.md`; `docs/v1.6/branding/evidence/` | exe metadata `CompanyName=AionUi` (target 49); 16 px legibility human gate |
| `1894ef7` | `71c78f0` | 2026-09-18 | REQ-LOGO-1 | canonical-logo breadcrumbs (REQ + CHG-004 + indexes + evidence) | docs only | — | none | no | — | no | no | LOW | corpus rows REQ-LOGO-1 / CHG-004 / §47–52; AUTO_RESUME section | — |
| `a547936` | `1894ef7` | 2026-09-18 | REQ-RK | record-bound resolution kinds on findings + additive workforce migration v17 | `kel/assurance.py`; `kel/workforce.py`; `tests/test_v16_resolution_kind.py` (new); `tests/test_workforce_schemas.py` | +6 engine tests; full suite **891 passed** (+10 subtests) | v17 additive (`findings.resolution_kind`) | no (engine semantics) | n/a (RC battery re-runs the engine suite) | no | yes (additive) | MEDIUM | `increments/REQ-RK-RESOLUTION-KIND.md`; TEST_EVIDENCE_INDEX A-13 | prefixes kept in text (deliberate); no per-kind breakdown in `lens_stats` |
| `a7c7aa4` | `a547936` | 2026-09-18 | REQ-RK | REQ-RK breadcrumbs | docs only | — | none | no | — | no | no | LOW | corpus rows REQ-RK / CHG-005 / §53–54; AUTO_RESUME section | — |
| `081a6ef` | `a7c7aa4` | 2026-09-18 | REQ-F4 / WF-12 | real-artifact binding: closure verifies the artifact the assignment delivered | `kel/core.py`; `kel/delegation.py`; `kel/evaluation.py`; `tests/test_workforce_d1.py`; `tests/test_workforce_d2.py` | +4 engine tests; full suite **895 passed** (+10 subtests); D1+D2+parallel 126 | none (existing `assignment_artifacts` gains its first reader) | no (engine semantics) | n/a (RC battery re-runs the engine suite) | no | no | MEDIUM | `increments/REQ-F4-REAL-ARTIFACT-BINDING.md`; TEST_EVIDENCE_INDEX A-14 | on-disk check needs an `artifact_root` (`run_d1` does not pass one yet); non-content-bound contracts unchanged |
| `c1bb980` | `820ee3e` | 2026-09-18 | REQ-P2P3 | P2/P3 sweep first batch (6 rows dispositioned against the tree) | docs only | — | none | no | — | no | no | LOW | `P2_P3_DISPOSITION.md`; REQUIREMENTS_TRACEABILITY REQ-P2P3 | 21 rows still OPEN (sweep pending) |
| `df1997a` | `c1bb980` | 2026-09-18 | PER-02 (P2 sweep) | a failed or partial restore is recorded and surfaced | `kel/backup.py`; `kel/service.py`; `tests/test_v16_restore_visibility.py` | +5 engine tests; full suite **900 passed** (+10 subtests) | none (sidecar `restore-outcome.json`) | additive `state()['restore']`; renderer surface → REQ-ELOSS | n/a (RC battery can assert on a staged restore) | yes (additive payload key) | no | MEDIUM | `increments/PER-02-RESTORE-VISIBILITY.md`; TEST_EVIDENCE_INDEX A-15 | renderer does not show it yet (target 57); PER-03 shares the path |
| `cbd0430` | `df1997a` | 2026-09-18 | PER-02 | PER-02 breadcrumbs | docs only | — | none | no | — | no | no | LOW | corpus rows PER-02 / CHG-007 / §57; AUTO_RESUME section | — |
| `0596211` | `cbd0430` | 2026-09-18 | INT-01 / SEC-01-multipart / PER-04 | sweep batch 2: IPC frame guard, multipart header hygiene, credentials excluded from backups | `desktop/.../kel/KelService.ts`; `kel/transcription.py`; `kel/backup.py`; `tests/test_v16_sweep_fixes.py` | +5 engine tests; full suite **905 passed** (+10 subtests); desktop tsc 0 | none (`NEVER_BACKUP` guard) | no (hardening) | n/a | no | no | MEDIUM | `increments/P2P3-BATCH2-IPC-HEADER-BACKUP.md`; TEST_EVIDENCE_INDEX A-16 | IPC guard has no automated test (no harness) — §58 |
| `a3e272d` | `0596211` | 2026-09-18 | sweep batch 2 | sweep batch 2 breadcrumbs | docs only | — | none | no | — | no | no | LOW | corpus rows INT-01 / SEC-01-multipart / PER-04 / DEAD-05 / TR-01 / CHG-008 / §58; AUTO_RESUME section | — |
| `101d8c3` | `a3e272d` | 2026-09-18 | A1 / ENG-01 | detached-engine reuse validates `engine_version` (both trust sites) | `desktop/.../kel/engineVersion.ts` (new); `KelService.ts`; `tests/unit/kelEngineVersion.test.ts` (new) | +3 desktop tests; vitest **93 passed**; tsc 0 | none | no (upgrade correctness) | n/a | no | no | MEDIUM | `increments/A1-ENGINE-VERSION-BINDING.md`; TEST_EVIDENCE_INDEX A-17 | end-to-end spawn fallback has no Electron harness — §59 |
| `11e1525` | `101d8c3` | 2026-09-18 | A1 | A1 breadcrumbs + REL-01 flagged as a release blocker | docs only | — | none | no | — | no | no | LOW | corpus rows A1 / REL-01 / CHG-009 / §59; AUTO_RESUME section | REL-01 recorded OPEN_RELEASE_BLOCKER |
| `84b5646` | `11e1525` | 2026-09-18 | PER-03 / APR-01 | pre-restore snapshots pruned; actor guard pinned by tests | `kel/backup.py`; `tests/test_v16_sweep_fixes.py` | +4 engine tests; full suite **909 passed** (+10 subtests) | none (`SNAPSHOT_KEEP` retention) | no (bounded growth) | n/a | no | no | LOW | `increments/P2P3-BATCH3-SNAPSHOTS-SCOPE.md`; TEST_EVIDENCE_INDEX A-18 | APR-02 + SEC-01 verified OPEN with fix sketches |
| `9eab3c6` | `ae4c5b0` | 2026-09-18 | Round 2.5 | adopt the canonical roadmap (KEL_CANONICAL_ROADMAP_R2_5) + invariants, audit targets, risks, deferrals, R25 requirement rows | docs only | — | none | no | — | no | no | LOW | `KEL_CANONICAL_ROADMAP_R2_5.md`; corpus pointers | audit_mode stays PAUSED_UNTIL_PRE_AUDIT_RC |
| `8a677d0` | `9eab3c6` | 2026-09-18 | R0 / APR-02 | approval resolution is conversation-scoped (write path matches the read path) | `kel/chat_approvals.py`; `kel/service.py`; `tests/test_v16_approvals.py`; `desktop/.../KelApprovalCard.tsx`; `desktop/.../KelWorkPanel.tsx` | +6 engine tests; full suite **915 passed** (+10 subtests); tsc 0, vitest 93 | none | no (scope hardening) | n/a | no | no | MEDIUM | `increments/R0-APR02-APPROVAL-SCOPE.md`; TEST_EVIDENCE_INDEX A-19 | R4 makes the declaration mandatory + adds normalization/revalidation |
| `49e528e` | `756218e` | 2026-09-18 | R0 / SEC-01 | vetting actions enforce conversation ownership (acting-scope gate on the single session load point) | `kel/vetting_session.py`; `kel/service.py`; `tests/test_vetting.py` | +7 engine tests; `test_vetting.py` **36 passed** | none | no (scope hardening) | n/a | no | no | MEDIUM | `increments/R0-SWEEP.md`; TEST_EVIDENCE_INDEX A-20 | `panel()` intentionally stays a marked cross-conversation display surface (existing tests) |
| `8ab7699` | `49e528e` | 2026-09-18 | R0 / TR-01 | stream lifecycle releases sockets; optional conversation scope | `kel/transcription.py`; `kel/service.py`; `tests/test_transcription.py` | +4 engine tests; `test_transcription.py` **31 passed** | none | no (resource lifecycle) | n/a | no | no | MEDIUM | `increments/R0-SWEEP.md`; A-20 | undeclared callers keep the previous behaviour (desktop stream calls declare no conversation yet) |
| `5950efb` | `8ab7699` | 2026-09-18 | R0 / COR-06 + ERR-01 | dispatch layers answer missing request fields with plain sentences | `kel/service.py`; `tests/test_v16_sweep_fixes.py` | +3 engine tests; file **12 passed** | none | no (error-surface honesty) | n/a | no | no | LOW | `increments/R0-SWEEP.md`; A-20 | ERR-01 alias note recorded in the disposition table for Campaign B |
| `dd34ac2` | `5950efb` | 2026-09-18 | R0 / APR-05 | approval poll path stops running DDL once stamped | `kel/chat_approvals.py`; `tests/test_v16_sweep_fixes.py` | +3 engine tests; file **15 passed** | migration marker **v20** (additive; no table/column change) | no | n/a | no | yes (marker row) | LOW | `increments/R0-SWEEP.md`; A-20 | pre-marker stores run the idempotent body once and are stamped |
| `594b8b4` | `dd34ac2` | 2026-09-18 | R0 / COR-03 + APR-06 + THM-01 | failure surfaces tell the truth (model pill reports, approval card distinguishes unreachable vs settled, theme delete prunes overrides) | `desktop/.../kel/KelModelControl.tsx`; `desktop/.../kel/KelApprovalCard.tsx`; `desktop/.../AppearanceSettings/CssThemeSettings.tsx` | desktop tsc 0; vitest **93 passed** | none | yes (message copy + delete handler) | n/a | no | no | LOW | `increments/R0-SWEEP.md`; A-20 | no renderer component harness (§58) — packaged probes at R8/R12 are the gate |
| `dc65fbc` | `4440a90` | 2026-09-18 | R1 / AUTH-DELEGATION | delegation authority ceiling is executable (child ⊆ delegator on class/scope/boundaries/effects/tools + budget envelope) | `kel/workforce.py`; `kel/contracts.py`; `kel/delegation.py`; `kel/pods.py`; `kel/assignment.py`; `tests/test_v16_r1_authority.py` | +21 engine tests; workforce family 269 passed; full suite A-21 | none | no | n/a | no | no | HIGH | `increments/R1-AUTHORITY-CEILING.md`; INV-AUTH-DELEGATION; REQ-R25-R1 | token/wallclock caps lack a job-envelope primitive (R3); no nesting added by design |
| `HEAD` | `dc65fbc` | 2026-09-18 | R1 | R1 breadcrumbs (this commit) | docs only | engine full A-21 | none | no | — | no | no | LOW | corpus rows REQ-R25-R1 / INV-AUTH-DELEGATION / CHG-018 / A-21; `increments/R1-AUTHORITY-CEILING.md` | next: R2 idempotency matrix |

## Visual branch commits pending integration (NOT covered by any independent audit)

Branch `ux/v16-visual-fix` (worktree `kel-v16-visual-fix`). These carry production changes that
have automated (79/79 vitest, tsc 0) and packaged (`package-visual5` probes a/b/c) acceptance only.
When integrated into `ux/v15-journeys` they enter the Commit Ledger range above as NEW commits
(integration commit(s) + preserved lineage), and their original SHAs remain traceable.

| SHA | date | batch | intent | production files (summary) | evidence | concerns |
|---|---|---|---|---|---|---|
| `8dd21f9` | 2026-09-17 | Batch 1 | Kel design tokens (slate-navy foundation, compact density) | renderer styles/tokens | 39/39 contrast checks; tsc 0; 76/76 | human pixel gate open |
| `3d9202c` | 2026-09-17 | Batch 2 | Settings shell: `/team/*` stays in Settings; `/settings/tools` shows Tools | settings renderer | tsc 0; 76/76 | — |
| `04151c8` | 2026-09-17 | docs | visual plan docs onto the branch | docs | — | — |
| `83af16f` | 2026-09-18 | Batch 4 | Transcription standalone IA | transcription renderer | tsc 0; 76/76 | finding 2/3 baselines pending |
| `ac85eb3` | 2026-09-18 | Batch 5 | Sidebar rows: action gutter + leading-mark semantics | ConversationRow, tests | tsc 0; **79/79**; packaged probe c | human pixel gate open |

## Maintenance rules

- Append a row when a production commit lands; never rewrite history in this file.
- Priority definition: LOW (docs/tests-internal), MEDIUM (localized behavior), HIGH (user-journey
  or engine behavior), CRITICAL (security/privacy/persistence/lifecycle).
- `packaged` column: name the packaged evidence (see PACKAGED_EVIDENCE_INDEX.md) or `-`.
- Keep the count current: at RC, `production commit count in range` = number of rows in the
  Campaign A table + integration commits (cross-checked against `git log`).
