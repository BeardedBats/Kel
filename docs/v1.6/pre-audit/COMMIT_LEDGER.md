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
| `HEAD` | `a547936` | 2026-09-18 | REQ-RK | REQ-RK breadcrumbs (this commit) | docs only | — | none | no | — | no | no | LOW | corpus rows REQ-RK / CHG-005 / §53–54; AUTO_RESUME section | — |

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
