# 02 — COMMIT COVERAGE (8a2b25d..08f56673)

73 commits. Classification: DOCS 33 / PROD 37 / TEST 3. Sources: `evidence/commit-classification.tsv`, `evidence/ledger-vs-git.txt`.
Review depth filled by Pass 1 (full diff review / targeted review / docs-skim).

| # | commit | date | class | files | subject | ledger | review depth |
|---|---|---|---|---|---|---|---|
| 1 | `04151c8` | 2026-09-17 14:07 | DOCS (docs:18) | 18 | docs(v1.6-visual): carry the Visual UX plan set onto the implementation branch | MENTIONED | — |
| 2 | `8dd21f9` | 2026-09-17 14:07 | PROD (desktop:2) | 2 | feat(v1.6-visual): BATCH 1 â€” Kel design tokens (slate-navy foundation, compact density) | MENTIONED | — |
| 3 | `3d9202c` | 2026-09-17 14:09 | PROD (desktop:2) | 2 | fix(v1.6-visual): BATCH 2 â€” Settings shell no longer ejects on Team; Tools shows Tools | MENTIONED | — |
| 4 | `83af16f` | 2026-09-17 14:31 | PROD (desktop:2) | 2 | feat(v1.6-visual): BATCH 4 â€” transcription adopts the authoritative standalone IA | MENTIONED | — |
| 5 | `ac85eb3` | 2026-09-18 00:14 | PROD (desktop:2+test:1) | 3 | fix(v1.6-visual): BATCH 5 â€” sidebar rows reserve the action gutter; redundant leading mark hidden | MENTIONED | — |
| 6 | `c4ae724` | 2026-09-18 09:07 | DOCS (docs:3) | 3 | docs(v1.6): Phase 5.6 remediation record + delta re-audit request (ba52869..8a2b25d) | MENTIONED | — |
| 7 | `5127bac` | 2026-09-18 09:12 | DOCS (docs:5) | 5 | docs(v1.6): Phase 5.6 accepted - audit 24 CONTINUE; Phase 5.7/5.8 decisions deferred | MENTIONED | — |
| 8 | `fd98cc4` | 2026-09-18 09:14 | DOCS (docs:1) | 1 | docs(v1.6): record the published integration tip (5127bac); visual slice complete | MENTIONED | — |
| 9 | `785df71` | 2026-09-18 12:09 | PROD (docs:25+meta:1) | 26 | docs(v1.6): Campaign A entry â€” pre-audit corpus initialized, IMPLEMENTATION_SPRINT mode, baseline 878 green | MENTIONED | — |
| 10 | `22f4a3e` | 2026-09-18 12:15 | PROD (desktop:2+test:1) | 3 | fix(v1.6): Work-panel knowledge actions follow record state; forget asks first | MENTIONED | — |
| 11 | `ac5e2a2` | 2026-09-18 12:17 | DOCS (docs:14) | 14 | docs(v1.6): Phase 6 record + pre-audit corpus updates (memory reality audit) | MENTIONED | — |
| 12 | `df87903` | 2026-09-18 12:28 | PROD (desktop:3+engine:4+test:2) | 9 | feat(v1.6): capability recommendations â€” real capabilities, real actions, no nagging | MENTIONED | — |
| 13 | `16de55f` | 2026-09-18 12:29 | DOCS (docs:12) | 12 | docs(v1.6): Phase 7 record + pre-audit corpus updates (capability recommendations) | MENTIONED | — |
| 14 | `7b32217` | 2026-09-18 12:30 | DOCS (docs:2) | 2 | docs(v1.6): record the published Phase 6+7 tip (16de55f); packaged pending item for the capability card | MENTIONED | — |
| 15 | `006159a` | 2026-09-18 12:31 | DOCS (docs:6) | 6 | docs(v1.6): Phase 8/5.8 decision â€” Advanced Worker View deferred beyond V1.6 | MENTIONED | — |
| 16 | `fa31618` | 2026-09-18 12:32 | DOCS (docs:1) | 1 | docs(v1.6): commit ledger rows for Phase 7 docs + Phase 8 decision commits | MENTIONED | — |
| 17 | `6ea68c2` | 2026-09-18 12:32 | DOCS (docs:6) | 6 | docs(v1.6): Phase 9 decision â€” no Profiles concept; Projects remain the single isolation concept | MENTIONED | — |
| 18 | `fed59dd` | 2026-09-18 12:34 | DOCS (docs:8) | 8 | docs(v1.6): Phases 10-11 â€” provider validation + Rust freshness recheck (Phase 12 closed) | MENTIONED | — |
| 19 | `24d775b` | 2026-09-18 12:35 | DOCS (docs:2) | 2 | docs(v1.6): ledger rows for Phase 8-11 docs commits; published-tip refresh | MENTIONED | — |
| 20 | `edd50de` | 2026-09-18 12:35 | DOCS (docs:1) | 1 | docs(v1.6): commit ledger completeness â€” Phase 6 docs row + Phases 8-11 docs row | MENTIONED | — |
| 21 | `71c78f0` | 2026-09-18 13:00 | PROD (desktop:12+tooling:2) | 14 | branding(v1.6): canonical Kel logo across all production-reachable surfaces | MENTIONED | — |
| 22 | `1894ef7` | 2026-09-18 13:00 | DOCS (docs:18) | 18 | docs(v1.6): canonical-logo requirement recorded as REQ-LOGO-1 | MENTIONED | — |
| 23 | `a547936` | 2026-09-18 13:14 | PROD (engine:2+test:2) | 4 | assurance(v1.6): record-bound resolution kinds on findings (REQ-RK) | MENTIONED | — |
| 24 | `a7c7aa4` | 2026-09-18 13:15 | DOCS (docs:8) | 8 | docs(v1.6): REQ-RK resolution-kind breadcrumbs (carry-forward F18-5 closed) | MENTIONED | — |
| 25 | `081a6ef` | 2026-09-18 13:33 | PROD (engine:3+test:2) | 5 | assurance(v1.6): real-artifact binding â€” closure verifies the delivered artifact (REQ-F4 / WF-12) | MENTIONED | — |
| 26 | `820ee3e` | 2026-09-18 13:33 | DOCS (docs:8) | 8 | docs(v1.6): REQ-F4 real-artifact binding breadcrumbs (carry-forward F4 / WF-12 closed) | MENTIONED | — |
| 27 | `c1bb980` | 2026-09-18 13:41 | DOCS (docs:2) | 2 | docs(v1.6): P2/P3 sweep â€” first batch (6 rows dispositioned against the tree) | MENTIONED | — |
| 28 | `df1997a` | 2026-09-18 13:49 | PROD (engine:2+test:1) | 3 | engine(v1.6): a failed or partial restore is recorded and surfaced (PER-02) | MENTIONED | — |
| 29 | `cbd0430` | 2026-09-18 13:50 | DOCS (docs:9) | 9 | docs(v1.6): PER-02 breadcrumbs + P2/P3 sweep progress (7/27 rows dispositioned) | MENTIONED | — |
| 30 | `0596211` | 2026-09-18 13:59 | PROD (desktop:1+engine:2+test:1) | 4 | fix(v1.6): sweep batch 2 â€” IPC frame guard, multipart header hygiene, credentials out of backups | MENTIONED | — |
| 31 | `a3e272d` | 2026-09-18 14:00 | DOCS (docs:9) | 9 | docs(v1.6): sweep batch 2 breadcrumbs (11/27 rows dispositioned) | MENTIONED | — |
| 32 | `101d8c3` | 2026-09-18 14:02 | PROD (desktop:2+test:1) | 3 | fix(v1.6): detached-engine reuse validates engine_version (A1 / ENG-01) | MENTIONED | — |
| 33 | `11e1525` | 2026-09-18 14:04 | DOCS (docs:9) | 9 | docs(v1.6): A1 breadcrumbs + REL-01 flagged as a release blocker (13/27 rows decided) | MENTIONED | — |
| 34 | `84b5646` | 2026-09-18 14:12 | PROD (engine:1+test:1) | 2 | fix(v1.6): pre-restore snapshots are pruned; actor guard pinned (sweep batch 3) | MENTIONED | — |
| 35 | `ae4c5b0` | 2026-09-18 14:13 | DOCS (docs:9) | 9 | docs(v1.6): sweep batch 3 breadcrumbs (16/27 rows decided) | MENTIONED | — |
| 36 | `9eab3c6` | 2026-09-18 14:55 | DOCS (docs:9) | 9 | docs(v1.6): adopt Round 2.5 canonical roadmap (KEL_CANONICAL_ROADMAP_R2_5) | MENTIONED | — |
| 37 | `8a677d0` | 2026-09-18 15:06 | PROD (desktop:2+engine:2+test:1) | 5 | fix(v1.6): approval resolution is conversation-scoped (R0 / APR-02) | MENTIONED | — |
| 38 | `756218e` | 2026-09-18 15:07 | DOCS (docs:8) | 8 | docs(v1.6): R0/APR-02 breadcrumbs (17/27 sweep rows decided) | MENTIONED | — |
| 39 | `49e528e` | 2026-09-18 16:44 | PROD (engine:2+test:1) | 3 | fix(v1.6): vetting session actions enforce conversation ownership (R0 / SEC-01) | MENTIONED | — |
| 40 | `8ab7699` | 2026-09-18 16:49 | PROD (engine:2+test:1) | 3 | fix(v1.6): transcription stream lifecycle releases sockets; optional conversation scope (R0 / TR-01) | MENTIONED | — |
| 41 | `5950efb` | 2026-09-18 16:53 | PROD (engine:1+test:1) | 2 | fix(v1.6): dispatch layers answer missing request fields with plain sentences (R0 / COR-06 + ERR-01) | MENTIONED | — |
| 42 | `dd34ac2` | 2026-09-18 16:55 | PROD (engine:1+test:1) | 2 | perf(v1.6): approval poll path stops running DDL once stamped (R0 / APR-05) | MENTIONED | — |
| 43 | `594b8b4` | 2026-09-18 16:57 | PROD (desktop:3) | 3 | fix(v1.6): model/approval/theme failure surfaces tell the truth (R0 / COR-03 + APR-06 + THM-01) | MENTIONED | — |
| 44 | `4440a90` | 2026-09-18 17:04 | DOCS (docs:9) | 9 | docs(v1.6): R0 complete â€” the P2/P3 sweep is 100% dispositioned | MENTIONED | — |
| 45 | `dc65fbc` | 2026-09-18 17:14 | PROD (engine:5+test:1) | 6 | feat(v1.6): delegation authority ceiling is executable (R1 / AUTH-DELEGATION) | MENTIONED | — |
| 46 | `eea6503` | 2026-09-18 17:20 | DOCS (docs:9) | 9 | docs(v1.6): R1 complete â€” delegation authority ceiling breadcrumbs | MENTIONED | — |
| 47 | `fde5bbb` | 2026-09-18 17:24 | PROD (engine:1+test:1) | 2 | fix(v1.6): an observed external effect keeps its receipt (R2 / EFFECT-REPLAY) | MENTIONED | — |
| 48 | `1a9f538` | 2026-09-18 17:32 | TEST (docs:1+test:1) | 2 | test(v1.6): retry budgets are durable across restarts (R3 / RETRY-DURABLE) | MENTIONED | — |
| 49 | `8c899c8` | 2026-09-18 17:35 | PROD (engine:1+test:1) | 2 | fix(v1.6): an approval authorizes only inside its window and for its exact action (R4 / APPROVAL-EXACT) | MENTIONED | — |
| 50 | `b2ffed1` | 2026-09-18 17:41 | PROD (engine:2+test:1) | 3 | fix(v1.6): only canonical JSON reaches durable state (R5 / PERSIST-CANONICAL) | MENTIONED | — |
| 51 | `e8bbb05` | 2026-09-18 17:48 | TEST (docs:12+test:1) | 13 | docs(v1.6): R3â€“R6 breadcrumbs â€” retry durability, approval window, canonical persistence, liveness truth | MENTIONED | — |
| 52 | `b6c4eff` | 2026-09-18 17:51 | PROD (engine:3+test:1) | 4 | fix(v1.6): provider children receive only the credential they require (R7 / CREDENTIAL-CONTAINMENT) | MENTIONED | — |
| 53 | `2468b16` | 2026-09-18 17:57 | PROD (engine:1+test:1) | 2 | fix(v1.6): migration markers are unique; R8.A assertions (R8 / PACKAGE-IDENTITY prep) | MENTIONED | — |
| 54 | `93b99b5` | 2026-09-18 18:14 | PROD (desktop:2+engine:2+test:1+tooling:2) | 7 | fix(v1.6): REL-01 closed â€” the runtime that is hashed is the runtime that loads (R8.B/C/D) | MENTIONED | — |
| 55 | `022f3ac` | 2026-09-18 18:20 | TEST (test:1) | 1 | test(v1.6): engine-version assertion follows the single source (R8.B follow-up) | MISSING | — |
| 56 | `0aadd42` | 2026-09-18 18:27 | DOCS (docs:10) | 10 | docs(v1.6): R7â€“R8 breadcrumbs â€” credential containment, package identity, REL-01 CLOSED | MISSING | — |
| 57 | `05608e6` | 2026-09-18 19:14 | DOCS (docs:4) | 4 | docs(v1.6): R9 bookkeeping â€” the 27-vs-26 P2/P3 denominator is reconciled | MENTIONED | — |
| 58 | `0ff061d` | 2026-09-18 19:15 | DOCS (docs:1) | 1 | docs(v1.6-visual): R9.A lane reconciliation + integration map (zero-overlap, re-anchor decision) | MENTIONED | — |
| 59 | `3050761` | 2026-09-18 19:15 | PROD (desktop:31+docs:90+engine:27+meta:1+test:29+tooling:4) | 182 | Merge branch 'ux/v15-journeys' into ux/v16-visual-fix | MENTIONED | — |
| 60 | `2897207` | 2026-09-18 19:25 | PROD (desktop:18+test:2) | 20 | feat(v1.6-visual): BATCH 6 â€” engine loss and failure states become honest and human | MENTIONED | — |
| 61 | `0e7d21a` | 2026-09-18 19:27 | PROD (desktop:3) | 3 | feat(v1.6-visual): BATCH 7 â€” the composer owns its secondary controls | MENTIONED | — |
| 62 | `c911d81` | 2026-09-18 19:29 | PROD (desktop:2) | 2 | feat(v1.6-visual): BATCH 8 â€” final normalization pass (genuine inconsistencies only) | MENTIONED | — |
| 63 | `938dc9b` | 2026-09-18 19:32 | PROD (desktop:4+test:1) | 5 | feat(v1.6-visual): R9.D â€” "Needs your attention" derived-only view | MENTIONED | — |
| 64 | `96979c7` | 2026-09-18 19:32 | DOCS (docs:1) | 1 | docs(v1.6-visual): R9 evidence index â€” batches 6-8 + R9.D, commits, acceptance, R11 conflict surface | MENTIONED | — |
| 65 | `34947f0` | 2026-09-18 19:33 | PROD (desktop:1) | 1 | feat(v1.6-visual): R10 prep â€” [KEL-LINK] transition log beside the engine log (packaged evidence) | MISSING | — |
| 66 | `1972b68` | 2026-09-18 19:52 | DOCS (docs:2) | 2 | docs(v1.6): R9 complete on the visual lane; R10 packaged journey in flight (state breadcrumbs) | MENTIONED | — |
| 67 | `93b7074` | 2026-09-18 19:55 | DOCS (docs:1) | 1 | docs(v1.6): audit targets 86-90 (R9 supervision/loaded-gun/preview residue/packaging input hygiene) | MENTIONED | — |
| 68 | `645898a` | 2026-09-18 19:57 | PROD (desktop:1) | 1 | fix(v1.6-visual): batch 6 follow-up â€” fail fast when a supervised engine spawn dies outright | MENTIONED | — |
| 69 | `fa66f04` | 2026-09-18 20:03 | PROD (desktop:1) | 1 | fix(v1.6-visual): batch 6 follow-up 2 â€” ENOENT spawns fail fast (pid undefined check) | MENTIONED | — |
| 70 | `bc92f7f` | 2026-09-18 20:12 | DOCS (docs:1) | 1 | docs(v1.6-visual): R10 evidence â€” packaged engine-loss/recovery journey PASS (r10-f/r10-g on fa66f04) | MENTIONED | — |
| 71 | `7267630` | 2026-09-18 20:12 | PROD (desktop:30+docs:24+test:4) | 58 | merge(v1.6): R11 â€” integrate the visual lane into Main (batches 6-8 + R9.D + R10 supervision) | MENTIONED | — |
| 72 | `12f87a7` | 2026-09-18 20:16 | DOCS (docs:7) | 7 | docs(v1.6): R11 records â€” integration breadcrumb, ledgers, requirements, visual index, status | MISSING | — |
| 73 | `08f5667` | 2026-09-18 20:52 | PROD (desktop:2+docs:15) | 17 | docs(v1.6): PRE_AUDIT_V1_6_HEAD â€” Campaign A complete; pre-audit release candidate ready | MISSING | — |

## Pass-1 review-depth record (added 2026-09-19 cont.)

- **Full-diff/hunk review + attack:** `8a677d0` (APR-02, negative-control run), `49e528e` (probe-4), `8ab7699` (probe-4), `dc65fbc` (probe-1/3), `fde5bbb` (probe-1 low-level + negative control), `8c899c8` (probe-1 + negative control), `b6c4eff` (probe-1 sentinels), `d101d8c3`-class A1 verified both sites, `93b99b5`/`2468b16` (freeze/identity scripts + engine hash chain), `08f5667` (full diff incl. packaging edits), `938dc9b`/`2897207`/`0e7d21a`/`c911d81`/`645898a`/`fa66f04` (visual lane: diff stats + evidence digests + r10 artifacts), `22f4a3e`/`df87903` (change-ledger + unit tests + probe context).
- **Targeted (stat + symbol/test/evidence checks, suite re-run):** all remaining production commits (ledger rows, increments digests `art_d8cf6e02…`/`art_322d2725…`, and the full-suite re-run at RC: 998+10).
- **Docs/test-only commits:** skimmed via corpus digests and doc diffs (classification in the table above).
- Method limitation (recorded): full per-commit line-by-line reading was performed for the high-risk set above; the remainder received targeted review as defined. No commit was left unreviewed at the classification/evidence level.
