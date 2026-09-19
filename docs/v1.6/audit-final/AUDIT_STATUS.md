# AUDIT STATUS — Campaign B (living document)

Last updated: 2026-09-19 (Pass 1 starting; independent test runs in flight)

## Fixed audit target
- `08f56673ea93ed84568018937bb190e0a5acd71b` — PRE_AUDIT_V1_6_HEAD (verified; immutable; continuous re-checks clean)

## Audit branch / worktree
- Branch `audit/v16-final`; worktree `C:\Users\Nick\Desktop\Kel\kel-v16-final-audit`. Audit commits so far: `6efbbcb`, `4105fda`, `a03b90a` (+ current working set).

## Pass progress
| Pass | Scope | Status |
|---|---|---|
| 0 | Repository integrity & binding | MOSTLY COMPLETE — identity/range/frozen refs/ledger coverage/frozen spot-checks recorded (`01_REPOSITORY_INTEGRITY.md`). Remaining: 6 of 8 frozen hashes recompute; V1.4/V1.4.1 verification-report check |
| 1 | Commit-by-commit review (73 commits) | IN PROGRESS — classification 73/73 in `02_COMMIT_COVERAGE.md`; full-diff review of production commits in progress |
| 2 | Requirements traceability, both directions | NOT STARTED (corpus read pending for REQUIREMENTS_TRACEABILITY) |
| 3 | Constitutional invariants | STARTED — attack map seeded (`05_INVARIANT_ATTACKS.md`, 30 families); executions pending |
| 4 | Historical P2/P3 re-audit | STARTED — historical docket corroborated (P2 10 / P3 16; 27 = worklist arithmetic); per-row re-verification pending |
| 5 | Migrations & durable state | STARTED — MIGRATION_LEDGER read (chain 1..19 table + v17/v20/v21 additions in prose; max = 21); fresh/upgrade/interruption probes pending |
| 6 | Security / authority / isolation | STARTED (leads): fail-open `conversation` defaults on scoping contracts (APR-02/SEC-01/TR-01 additive pattern) — attack pending; IPC sender-frame parity pending |
| 7 | Workforce / orchestration | NOT STARTED |
| 8 | Memory | NOT STARTED |
| 9 | Approvals / capabilities | NOT STARTED |
| 10 | Recovery / liveness | NOT STARTED |
| 11 | Transcription / vetting | NOT STARTED |
| 12 | Desktop / UX truth | NOT STARTED |
| V | Visual automation review | IN PROGRESS — evidence cross-check digest in hand; `14_VISUAL_AUTOMATION.md` to create; human gate PENDING |
| P | Package / installer | IN PROGRESS — artifacts located; 2/8 frozen hashes verified; auditor rebuild + install/uninstall test pending |
| PR | Provider validation | NOT STARTED — matrix read; environment checks pending |
| BR | Brand / donor / dead-surface sweeps | IN PROGRESS (leads): `desktop/package.json` description+author email; `AionUI-LICENSE.txt` in package; `bundled-aioncore`; web-host `backend-launcher` spawning `aioncore` (test-observed); donor `Navigate` routes (DEAD-04 deferred) |
| J | Journeys + Needs-Your-Attention | NOT STARTED |
| BS | Blind-spot pass | NOT STARTED |

## Independent runs (auditor-executed)
- Engine full suite: RUNNING (background session `urky48ha`; log `evidence/auditor-engine-suite.log`; from the audit worktree at RC; compare to claimed 998 passed + 10 subtests).
- Desktop vitest: RUNNING (background session `ur6vyaxd`; log `evidence/auditor-desktop-vitest.log`; run against `kel-ux-v15/desktop` at RC commit; compare to claimed 122/122 / 12 files; observed so far: web-host backend-launcher tests (44) + static-server (8) etc.).
- Frozen hash spot-checks: 2/8 recomputed — both exact (`evidence/frozen-hash-spotchecks.txt`).

## Delegated digests (read-only children; artifacts are thread-local but referenced)
- Increments digest A (INIT..R2): artifact `art_d8cf6e02ea01dcd3985d54b3` (86,428 B) — key result: every claimed production file/test exists at RC; discrepancies: blank SHAs in some records, stale OPEN labels inside older increments, missing in-tree `docs/code-audit/` path, RC-vs-record migration-max staleness (19 vs 20/21).
- Increments digest B (R3..A1): artifact `art_322d272573a8507b04086abf` (79,222 B) — key result: all claimed files/tests exist; high-risk fixes present with quoted sentences; unverified: all pass-counts (must be re-run).
- Historical audit digest: full text in thread; docket corroboration (P2 10/P3 16 IDs enumerated), final coverage `5e76b21..8a2b25d`, program verdict REVISE/OPEN carried until later phases; open leftovers (F4 must not be described as fixed — now claimed closed via CHG-006 to re-verify; audit-15 sug3; static-only reviewer).
- Visual/package digest: full text in thread; contradictions list (r12-fresh boolean false-but-exit-0; screenshot-count arithmetic; missing uninstall evidence; visual5 path rename; stale 00_STATUS; NCC report not retained).
- Program-docs digest: on disk (`evidence/corpus-digest-program-docs.md`).

## Findings (see MASTER_FINDINGS.md)
- AUD-BLOCK: 0
- AUD-MAJOR: 0 recorded (candidates under verification — see queue)
- AUD-MINOR: 1 recorded (AUD-MINOR-001 COMMIT_LEDGER completeness)
- AUD-SUG: 0

## Under-verification queue (candidate findings — NOT yet filed)
1. r12-fresh probe: `attentionVisible:false` + `aboutLogoLoaded:false` yet exit 0; probe script exits 0 regardless of boolean results (test-quality / evidence integrity).
2. Uninstall lifecycle claim has no retained evidence (script asserts nothing about uninstall; `r12-installed` empty).
3. `r12-integrity.txt` captured with `M desktop/kel-builder.json` + `M desktop/package.json` present ("expect empty" violated); script never fails on unexpected state.
4. Fail-open `conversation` defaults in scoping contracts (APR-02/SEC-01/TR-01 "additive" behavior) — can a non-declaring caller bypass scope?
5. RC commit `08f5667` bundles packaging edits under a `docs(v1.6)` subject; also `COMMIT_LEDGER` gaps (folded into AUD-MINOR-001).
6. Corpus state drift: INVARIANT_LEDGER statuses (PLANNED/stale for INV-AUTH-001/IDEM-001/EFFECT-001/RETRY-001/APPROVE-001/002, ERROR-001, WF-005, IPC-001, UI-001, CRED-001, MEM-001); MIGRATION_LEDGER "next free version 20" + unchecked RC checklist; roadmap "27/27" text; AUDIT_HANDOFF TBD rows; `docs/v1.6-visual-ux/00_STATUS.md` stale copy.
7. Donor residuals: `desktop/package.json` `"Kel with the AionUI interface"` + `service@aionui.com`; `AionUI-LICENSE.txt` (legal-attribution class TBD); `bundled-aioncore`; web-host `backend-launcher` spawns `aioncore`; `aion-history`/`aionui` data-dir names in probe roots.
8. Screenshot-count arithmetic (R10 "7" vs 16 PNGs; 35-capture index) + r10-d/e/f timing wording ("2 ms" vs measured ~5s/95s discrimination) — visual evidence precision.
9. `ux-audit/visual/runs/visual5-*` path does not exist (actual `ux-audit/runs/visual5-*`) — evidence path drift (also in PACKAGED_EVIDENCE_INDEX row).
10. Pre1 frozen folder lacks `KEL_VERIFICATION_REPORT.md` (V1–V1.3 have it); check V1.4/V1.4.1.
11. NCC/contrast/tsc/vitest raw transcripts not retained anywhere (claims reproducible only by re-run — which this audit is doing).

## Next action
- Read `AUDIT_TARGETS.md` + `PROVIDER_VALIDATION_MATRIX.md`; then Pass 1 diffs (production commits) + first attack probes (conversation-scope fail-open; approval window; effect receipt; credential sentinel); build `03_FILE_COVERAGE.md`.

## Blockers to audit execution
- None (delegated child runs are flaky for large reads — workaround: auditor reads directly; noted).
