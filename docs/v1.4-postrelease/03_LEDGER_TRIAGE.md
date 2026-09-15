# 03 — Ledger Triage (142 rows at triage, classified)

200 ledger rows = 58 `IMPLEMENTED` (each carries a delivered citation; skipped here) + **142 rows still at
triage** (85 `EXTEND`, 29 `NEW`, 28 `ALREADY_PRESENT`). Every triage row was classified against fresh
repository evidence — source scans, tests, the frozen package, and the 18 packaged capture manifests — and
never against the ledger's own text. Grouped rows list every ID; each ID is decided. UNVERIFIED count is 0.

**Category counts (sum = 142):**

| Category | Count |
|---|---|
| ALREADY_DELIVERED_ELSEWHERE | 72 |
| VALID_POST_RELEASE_WORK | 38 |
| INFORMATIONAL | 28 |
| ARCHITECTURAL_DRIFT | 4 (V14-150…153) |
| RELEASE_DEFECT | 0 |
| UNVERIFIED | 0 |
| NOT_V1_4_SCOPE / SUPERSEDED / DUPLICATE | 0 / 0 / 0 |

**Relevance:** 38 of 200 rows (19%) are genuinely unresolved post-release work; 72 rows (36%) were already
delivered but never advanced in the ledger (55 of them in the shell blocks J/K and work/review UX blocks C/F);
28 are verification-only observations of long-standing behavior.

| Row(s) | Status | Delivered? | Category | Evidence / note |
|---|---|---|---|---|
| V14-007 | NEW | NO | VALID_POST_RELEASE_WORK | Better-with-access card not located; engine opportunity classification exists (`solution.py`) |
| V14-011 | EXTEND | YES | ALREADY_DELIVERED_ELSEWHERE | Self-certification refused; approval needs independent OPTIMAL_ENOUGH review (`solution.py:278-279,300-302`) + tests |
| V14-020, V14-026 | NEW | YES | ALREADY_DELIVERED_ELSEWHERE | Office/Roster/Studio (`pages/kel/team`); assignment truth + staffing reasons (`team.py`); g4 captures |
| V14-029 | EXTEND | PARTIAL | VALID_POST_RELEASE_WORK | Artifact API + work-drawer viewer live; per-specialist drawer not located |
| V14-041, 042, 047, 048, 050, 053, 056, 057, 060 | EXTEND | YES | ALREADY_DELIVERED_ELSEWHERE | Work Center + verification panel + state copy + artifact viewer + background work (`pages/kel/work`, `KelWorkPanel`; `AUTO_RESUME.md`) |
| V14-046 | EXTEND | YES | ALREADY_DELIVERED_ELSEWHERE | Frozen accepted steps tested (`test_core.py` P07 / P20 / scope_change) |
| V14-045, 051 | ALREADY_PRESENT | EXISTS | INFORMATIONAL | Milestone list + inline controls verified since V1.3 |
| V14-043, 044, 049, 052, 054, 055, 058, 059, 061, 062 | EXTEND/NEW | NO | VALID_POST_RELEASE_WORK | Timeline, current-step emphasis, activity feed, filters, recovery banner, parent-child map, scope chip, budget meter, retry history, stall display not located in Kel surfaces |
| V14-063, 068, 069, 070, 071, 072, 076, 078, 079 | ALREADY_PRESENT | EXISTS | INFORMATIONAL | Knowledge panel, memory actions, map refresh verified in V1.3 |
| V14-064, 065, 066, 067 | EXTEND | YES | ALREADY_DELIVERED_ELSEWHERE | Knowledge tab shows type/trust/source (`KelWorkPanel:356-386`); composer sources/reasons |
| V14-077 | EXTEND | YES | ALREADY_DELIVERED_ELSEWHERE | Map freshness/stale/sources shown (`KelWorkPanel:36-37,419`) |
| V14-080, 081 | EXTEND | YES | ALREADY_DELIVERED_ELSEWHERE | Context tab + `sources[].reason` (`KelWorkPanel:258`) |
| V14-073, 074, 075, 082 | EXTEND | NO | VALID_POST_RELEASE_WORK | Superseded history, stale warning, isolation indicator, source-mix indicator surfaces not located |
| V14-083, 084, 086, 088, 089, 090, 091, 092, 093, 095 | ALREADY_PRESENT | EXISTS | INFORMATIONAL | CONT-01…11 verified in V1.3 (incl. approval survives restart) |
| V14-085 | EXTEND | YES | ALREADY_DELIVERED_ELSEWHERE | `continuation.explain()` + Continue tab (`KelWorkPanel:304`) |
| V14-087, 094, 096 | EXTEND | NO | VALID_POST_RELEASE_WORK | Session-resume display, continuation history view, recovered-work banner not located |
| V14-097, 098, 099, 100, 104, 106, 110, 116, 117, 118 | EXTEND | YES | ALREADY_DELIVERED_ELSEWHERE | Verification panel ("Worker reported … Kel verified", `pages/kel/work:212`), gated artifact viewer, apply/backup state, labels, digests, receipts (G5/G6) |
| V14-101, 108, 112, 115 | EXTEND | YES | ALREADY_DELIVERED_ELSEWHERE | Provenance (`test_b3_provenance`), review-recovery (`test_review_recovery`), pre-run checks, self-review refusal (engine) |
| V14-102, 103, 105, 107, 109, 111, 113 | EXTEND/NEW | NO | VALID_POST_RELEASE_WORK | Independence indicator, freshness warning, flaky indicator, why-uncertain surface, verification history, coverage matrix, rubric viewer not located |
| V14-119, 121, 129, 127, 130, 134, 136 | EXTEND/NEW | YES | ALREADY_DELIVERED_ELSEWHERE | Provider Setup + readiness/fallback reasons + capability selector (`pages/kel/providers:42-95`); quota_not_reported chip (:35); custody (`kelCredentials.ts`; `providers.py:199-213`); deepseek registry (`providers.py:42-46`) |
| V14-120, 122, 132, 135 | NEW/EXTEND | NO | VALID_POST_RELEASE_WORK | Subscription-vs-API copy, test-connection action, task budget meter, usage history not located |
| V14-144, 146, 147 | EXTEND | YES | ALREADY_DELIVERED_ELSEWHERE | Requests on Autonomy page with Allow once / Allow for project (:192-208); grants `once|project` (`autonomy.py:303-307`); lease expiry + revoke (:134, :165-171) |
| V14-145, 148, 149 | NEW | NO | VALID_POST_RELEASE_WORK | Plain-language expansion copy, outside-project warning, destructive warning UI not located (engine checker covers snapshot rule only) |
| V14-150, 151, 152, 153 | NEW | YES (checker) | ARCHITECTURAL_DRIFT | Details below |
| V14-154, 163, 166 | ALREADY_PRESENT | EXISTS | INFORMATIONAL | Library, versions, project scoping verified V1.3 |
| V14-155, 156, 157, 158, 159, 160, 161, 162, 164, 165 | EXTEND/NEW | YES | ALREADY_DELIVERED_ELSEWHERE | Preview/dry-run incl. required inputs + permission preview (`service.py:406`; G5 verify-actions), milestone-based step progress/freeze/retry, draft-from-settled-job (`recipes.py:704`), terminal states |
| V14-167, 168, 169 | EXTEND/NEW | YES | ALREADY_DELIVERED_ELSEWHERE | First-run onboarding (`Layout.tsx:138-161`; G7), palette search (`KelCommandPalette`) |
| V14-170, 171 | EXTEND | YES | ALREADY_DELIVERED_ELSEWHERE | Tray menu (`tray.ts:115-187`); web notifications hidden-tab + setting + turn/permission events (`useBrowserNotification.ts:23-66`) |
| V14-173, 174, 179, 180, 181, 183 | EXTEND | YES | ALREADY_DELIVERED_ELSEWHERE | Diagnostics startup spans; settings IA captures; `KelPrimitives` states; 30/30 focus rings; 0 contrast failures; unified panels (G7/G9) |
| V14-172, 175, 176, 177 | ALREADY_PRESENT | EXISTS | INFORMATIONAL | Pet, updater, WebUI/PWA, single-instance verified |
| V14-178, 182 | NEW/EXTEND | NO | VALID_POST_RELEASE_WORK | Local/private indicator, consolidated project switcher not located |
| V14-188, 189, 190, 191 | EXTEND/NEW | YES | ALREADY_DELIVERED_ELSEWHERE | Export sanitize/redact, process ownership view, retention controls, version details (`pages/kel/diagnostics`) |
| V14-198, 199 | EXTEND | YES | ALREADY_DELIVERED_ELSEWHERE | Orphan-candidate display; DB integrity + backup-first compaction |
| V14-195, 196, 197 | EXTEND/NEW | NO | VALID_POST_RELEASE_WORK | Context-composition, memory-retrieval, cost/time metric surfaces not located |

## ARCHITECTURAL_DRIFT detail entries (required fields)

**V14-150 — Frozen-release lock** · Intended: canonical frozen paths locked at execution time.
Actual: checker + AUTO-FROZEN exist (`autonomy.py`), but the only caller is `/api/autonomy`
(`service.py:582-583`); nothing on the execution path consults it. Evidence: caller grep; frozen-folder
immutability is currently enforced by process discipline only. Severity **P1** · Target **V1.4.1**
(wire enforcement or correct the docs).

**V14-151 — No-screen-takeover enforcement** · Intended: takeover/synthetic-input refused before execution.
Actual: refusal exists only inside the checker (AUTO-BLOCK-REG/SYSTEM); no runtime gate. Severity **P1** ·
Target **V1.4.1**.

**V14-152 — Firefox-only browser rule** · Intended: browser actions refused outside the Firefox rule.
Actual: checker-only; exposure is limited today because native adapters disable browser/web features
(`native.py` `--disable` list), but the coding host is ungated. Severity **P1** (same root cause) ·
Target **V1.4.1**.

**V14-153 — Locked-system-red-line status** · Intended: status shows what is actually locked.
Actual: the Autonomy page states the rules "are locked. No role, project, repository, or web content can
edit or weaken them" while enforcement is checker-level only — the display overstates runtime protection.
Severity **P1** (same root cause; fix by wiring enforcement or softening the copy). · Target **V1.4.1**.

## Rows where release docs claim delivery but evidence was missing

None. Every candidate flagged during triage (frozen steps V14-046; quota-unknown V14-127; fallback copy
V14-130; capability matrix V14-134; allow-once/project V14-146; expiry/revoke V14-147; permission preview
V14-157; dry-run V14-165; palette V14-169; tray V14-170; notifications V14-171; states V14-179; retention
V14-190; orphan detector V14-198; DB health V14-199) was resolved as *delivered* with concrete artifacts.
The genuine claim-vs-code gaps found by this audit are outside the ledger rows and are recorded as
P1/P2 findings in `06_V1_4_1_DEFECTS.md` (enforcement integration; credential-injection claim;
recursion-check claim).

**Reading:** the 142-row figure is overwhelmingly a *ledger-hygiene* backlog, not 142 missing features.
It contains zero release defects, 4 drifting rows (one root cause), 38 real post-release items, and 100
rows that are either already delivered elsewhere or merely informational.
