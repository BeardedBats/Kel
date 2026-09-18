# REQUIREMENTS_TRACEABILITY — requirement → implementation → evidence

updated: 2026-09-18T16:05Z
purpose: let Campaign B ask BOTH directions — "which requirement has no implementation?" and
"which implementation has no requirement?" — across the whole V1.6 surface.

Requirement sources live in: `docs/v1.6/` (program records), `docs/session-tools/`,
`docs/memory-proposals/`, `docs/artifact-lineage/`, `docs/in-chat-approvals/`,
`docs/i18n-cleanup/`, `docs/release-hardening/`, `docs/product/`, `docs/basic-ux-sweep/`,
`docs/transcription/`, `docs/vetting/`, `docs/v1.6-visual-ux/` (in the visual worktrees), and the
Workforce OS library at `C:\Users\Nick\Desktop\Kel\ux-audit\workforce-os\` (00–15 + role charters
at `ux-audit\workforce-role-charters`). Campaign A work follows the sprint directive dated
2026-09-18 (KEL V1.6 FULL-SPEED IMPLEMENTATION SPRINT).

Audit status column: `covered` = inside an independent audit increment; `pending` = in the
unaudited range; `deferred` = explicitly deferred with a decision record.

## Delivered arcs (audited coverage through `8a2b25d`)

| Req ID | Source | Section | Status | Commit(s) | Primary code | Tests | Evidence | Limitations | Audit |
|---|---|---|---|---|---|---|---|---|---|
| REQ-ST-1 | docs/session-tools | closure plan | implemented | (pre-1.6 arc) | `runtime/kel/*` session tools | fresh 545-suite + packaged sessiontools 24/24 | docs/session-tools/ | — | covered |
| REQ-MEMP-1 | docs/memory-proposals (01–07) | all | implemented | `a8c3511` | `memory.py` proposals; `KelMemoryProposal.tsx` | `test_v16_proposals.py`; packaged memoryprops | docs/memory-proposals/ | — | covered |
| REQ-LIN-1 | docs/artifact-lineage | all | implemented | `ffeef73` | lineage store + `/api/lineage` | engine 574; packaged lineage probe | docs/artifact-lineage/ | F4 binding open | covered |
| REQ-APR-1 | docs/in-chat-approvals | all | implemented | `85e99fb` | `chat_approvals.py`, anchors | engine 592; packaged approvals journey | docs/in-chat-approvals/ | APR-01..03 P2 open | covered |
| REQ-CAP-1 | audit 1.6 CAP-01/02/03 | remediation | implemented | `75d1f68`, `327e5b2`, `631881a` | `capabilities.py`, `research.py`, `acp_host.py` | engine 604→613 (+10 subtests each); packaged probes | docs/session-tools/03; ux-audit/run-cap2-residual.sh | CAP2-LONGTEXT P3 | covered |
| REQ-I18N-1 | docs/i18n-cleanup | 00_STATUS | implemented | `fd04c00` | desktop locales (12 translated + en-US) | tsc 0; 76/76; copy-scan probe | docs/i18n-cleanup/00_STATUS.md | dormant boundaries kept | covered |
| REQ-WF-5.0 | workforce-os 15 §5.0; docs 03/06/07/08 | — | implemented | `9085335`, `cc909b9` | `workforce.py` (migration 16) | +45; audits 8/9 | docs/v1.6/phase5/5.0_IMPLEMENTATION_RECORD.md | lens partial-coverage carry | covered |
| REQ-WF-5.1 | 15 §5.1; doc 10 | — | implemented | `9d6ed55`, `5b83f0e` | `assignment.py` (migration 17) | +31; audits 10/11 | 5.1_IMPLEMENTATION_RECORD.md | N7 etc. recorded | covered |
| REQ-WF-5.2 | 15 §5.2; doc 05 | — | implemented | `894be5b`, `f9cf3ea` | `staffing.py`, `delegation.py` (migration 18) | +24; audits 12/13 | 5.2_IMPLEMENTATION_RECORD.md | F4 open | covered |
| REQ-WF-5.3 | 15 §5.3; docs 05/08 | — | implemented | `48dacb3`, `5747567` | `pods.py`, `messages.py`, `assurance.py` | +41; audits 14/15 | 5.3_IMPLEMENTATION_RECORD.md | F4 open | covered |
| REQ-WF-5.4 | 15 §5.4; doc 08 | — | implemented | `932db33` + 3 patches `f25a4bf` | `assurance.py` (gating/Sentinel/Oracle) | +24; audits 16–19 | 5.4_IMPLEMENTATION_RECORD.md | — | covered |
| REQ-WF-5.5 | 15 §5.5 | — | implemented | `5f77f42`, `b1141c4`, `2a12b77`, `d8880f3` | `parallel.py` (migration 19) | 842→853; audits 20–22 | 5.5_IMPLEMENTATION_RECORD.md | F20-6/F20-14/N21-5/R22-3 | covered |
| REQ-WF-5.6 | 15 §5.6; doc 11 | — | implemented | `ba52869`, `8a2b25d` | `learning.py`; memory/team/assignment hooks | 853→878; audits 23/24 | 5.6_IMPLEMENTATION_RECORD.md | 5.6 limitation set | covered |
| REQ-WF-5.7 | 15 §5.7; doc 11 §5 | deferral | deferred (decision) | — | — | — | 5.7_DECISION_DEFERRED.md | entry unmet | deferred |
| REQ-WF-5.8 | 15 §5.8; doc 12 | deferral | deferred (decision made) | — | — | — | `docs/v1.6/phase8/ADVANCED_WORKER_VIEW_DECISION.md` | decision 2026-09-18: deferred beyond V1.6 | deferred |
| REQ-VIS-1..5 | visual plan set (worktrees) | batches 1–5 | implemented on visual branch | `8dd21f9`, `3d9202c`, `83af16f`, `ac85eb3` | renderer surfaces | tsc 0; 76→79; packaged visual5 probes | VISUAL_EVIDENCE_INDEX.md | human gate open | pending (never audited) |

## Campaign A arcs (unaudited range; updated as increments land)

| Req ID | Source | Section | Status | Commit(s) | Tests | Evidence | Audit |
|---|---|---|---|---|---|---|---|
| REQ-MEM-6 | sprint directive §31 (bootstrap §28) | memory reality audit + bounded fixes | implemented (audit + bounded fixes) | `22f4a3e` | `KelWorkPanel.tsx`; `memoryRecordActions.ts` | 7 unit tests; engine focused 68 | `docs/v1.6/phase6/MEMORY_REALITY_AUDIT.md`; `increments/PHASE6-MEMORY-REALITY.md` | MEMR-4/5/6/7 deferred with records | pending |
| REQ-CAPREC-7 | sprint directive §32 | smart capability recommendations | implemented | `df87903` | focused 83 / full 885 / desktop 90 | `docs/v1.6/phase7/CAPABILITY_RECOMMENDATIONS.md`; `increments/PHASE7-CAPABILITY-RECOMMENDATIONS.md` | packaged card evidence deferred (LIM-14) | pending |
| REQ-AWV-8 | sprint directive §33 | Advanced Worker View decision | decided — deferred beyond V1.6 | docs commit (2026-09-18) | — | `docs/v1.6/phase8/ADVANCED_WORKER_VIEW_DECISION.md` | pending (decision review) |
| REQ-PP-9 | sprint directive §35 | Profiles vs Projects decision | decided — no Profiles concept; Projects remain the single isolation concept | docs commit (2026-09-18) | — | `docs/v1.6/phase9/PROFILES_VS_PROJECTS_DECISION.md` | pending (decision review) |
| REQ-PROV-10 | sprint directive §36 | real provider validation | implemented (as access allows) | docs commit (2026-09-18) | 55 focused; claude real call PASS | `docs/v1.6/phase10/PROVIDER_VALIDATION.md`; `PROVIDER_VALIDATION_MATRIX.md` | codex blocked (CLI version); internal/deepseek no credentials (DEF-005) | pending |
| REQ-RUST-11 | sprint directive §37 | Rust freshness recheck | verified — verdict upheld; Phase 12 closed | docs commit (2026-09-18) | A1/PER-02/REL-01 re-verified open | `docs/v1.6/phase11/RUST_FRESHNESS_RECHECK.md` | none new | pending |
| REQ-F4 | audit carry-forward (F4 / WF-12) | real-artifact binding wiring | implemented | implementation commit (2026-09-18) | 4 focused (new); full suite see A-14 | `increments/REQ-F4-REAL-ARTIFACT-BINDING.md` | on-disk check needs an `artifact_root`, which `run_d1` does not pass yet; non-content-bound contracts unchanged | pending |
| REQ-RK | audit carry-forward (F18-5 / WF-13) | resolution-kind semantics | implemented | implementation commit (2026-09-18) | 6 focused (new); full suite see A-13 | `increments/REQ-RK-RESOLUTION-KIND.md` | reason prefixes retained for readability; `lens_stats` has no per-kind breakdown yet | pending |
| REQ-P2P3 | audit docket + sprint §40 | P2/P3 sweep (roadmap R0) | in progress — 16/27 rows carry a final disposition (P2 6/10: PER-02, A1, APR-01, PER-03 fixed; APR-03 `DEFERRED_NON_RELEASE`; REL-01 `OPEN_RELEASE_BLOCKER` — P3 10/17); 11 rows stay `OPEN (sweep pending)` | PER-02 `df1997a`; batch 2 `0596211`; A1 `101d8c3`; batch 3 `84b5646` | — | P2_P3_DISPOSITION.md | pending |
| REQ-R25-R1 | roadmap R2.5 (Round 2.5 A; invariant AUTH-DELEGATION) | delegation authority ceiling (`child ⊆ delegator`) | PENDING | — | — | `docs/v1.6/KEL_CANONICAL_ROADMAP_R2_5.md` §R1 | — | pending |
| REQ-R25-R2 | roadmap R2.5 (Round 2.5 B; EVENT-IDEMPOTENCY / EFFECT-REPLAY) | logical-work/idempotency matrix + real gaps only | PENDING | — | — | roadmap §R2 | — | pending |
| REQ-R25-R3 | roadmap R2.5 (Round 2.5 C; RETRY-DURABLE) | durable retry/recovery budgets | PENDING | — | — | roadmap §R3 | — | pending |
| REQ-R25-R4 | roadmap R2.5 (Round 2.5 D; APPROVAL-EXACT) | canonical approval binding (absorbs APR-02) | PENDING | — | — | roadmap §R4 | — | pending |
| REQ-R25-R5 | roadmap R2.5 (Round 2.5 E; PERSIST-CANONICAL) | persistence integrity contract + adversarial tests | PENDING | — | — | roadmap §R5 | — | pending |
| REQ-R25-R6 | roadmap R2.5 (Round 2.5 F/G; COMPLETION-TRUTH / LIVENESS-SEPARATION / RECOVERY-CLASSIFICATION) | truthful state + liveness separation | PENDING | — | — | roadmap §R6 | — | pending |
| REQ-R25-R7 | roadmap R2.5 (Round 2.5 H/I; CREDENTIAL-CONTAINMENT) | credential/network boundary confirmation | PENDING | — | — | roadmap §R7 | — | pending |
| REQ-R25-R8 | roadmap R2.5 §15 (= REQ-PKG-ASSERT + REL-01) | packaged/migration assertions | PENDING | — | — | roadmap §R8 | — | pending |
| REQ-R25-R9 | roadmap R2.5 (Round 2.5 N) | Visual batches 6–8 + Needs Your Attention (derived-only) | PENDING | — | — | roadmap §R9 | — | pending |
| REQ-R25-R10 | roadmap R2.5 §17 (= REQ-ELOSS) | engine-loss/recovery UX | PENDING | — | — | roadmap §R10 | — | pending |
| REQ-R25-R11 | roadmap R2.5 §18 | Visual → Main integration | PENDING | — | — | roadmap §R11 | — | pending |
| REQ-R25-R12 | roadmap R2.5 §19 | final Campaign A regression | PENDING | — | — | roadmap §R12 | — | pending |
| REQ-VIS-6..8 | visual plan set | batches 6–8 + integration | PENDING | — | — | VISUAL_EVIDENCE_INDEX.md | pending |
| REQ-ELOSS | sprint directive §43; findings 16/17 | engine loss + recovery UX | PENDING | — | — | — | pending |
| REQ-WFWIRE | sprint §30 "provider/Workforce real wiring"; F16-3 | wiring increment | PENDING | — | — | — | pending |
| REQ-PKG-ASSERT | carry-forward | packaged battery assertions 16–19 | PENDING | — | — | PACKAGED_EVIDENCE_INDEX.md | pending |
| REQ-RC | sprint directive §45/§46 | pre-audit regression + RC | PENDING | — | — | docs/v1.6/PRE_AUDIT_RELEASE_CANDIDATE.md | pending |
| REQ-LOGO-1 | Nick directive 2026-09-18 (canonical logo) | branding surfaces | implemented | branding commit (2026-09-18) | `scripts/make-brand-assets.py`; tsc 0; vitest 90 | `docs/v1.6/branding/CANONICAL_LOGO.md`; `increments/LOGO-CANONICAL.md` | dormant NSIS text + dead donor svg + metadata attribution = audit targets 47–52 | pending |

Stable requirement statement (verbatim): **"The exact Nick-supplied folded-ribbon K is the canonical
Kel logo and appears consistently across all production-reachable Kel branding surfaces."**
Canonical source sha256 `7418a42fc06267707c1e1aa4ab0d8822e8d636a687a81f200788a7b3e50ec71f`.

## Maintenance rules

- Every increment record must add/adjust its rows here; no implementation without a requirement
  row, and no requirement row left without a disposition.
- When Campaign B finds "implementation without requirement", the row is added with
  `source: UNDECLARED` so Campaign C can decide scope.
