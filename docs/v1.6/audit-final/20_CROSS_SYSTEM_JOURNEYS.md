# 20 — CROSS-SYSTEM JOURNEYS A–E

Audit target `08f56673…`. Journeys defined by the Campaign B continuation brief; evidence composed from executed legs, with gaps recorded (no journey is claimed beyond its evidence).

## Journey A — request → capabilities → routing → execution → approval → effect → evidence → verification → completion → UI

| Leg | Evidence | Result |
|---|---|---|
| request→capabilities | probe-1 §F (grammar + refusal of unknown) + suite | PASS |
| routing | PROVIDER matrix + Claude real call + suite routing tests | PASS (codex env-blocked; both API-key providers unavailable) |
| execution→approval | probe-1 §A/B (exact/window/duplicate/actor) + suite | PASS with **MAJOR-001** caveat (undeclared caller) |
| approval→effect→evidence | probe-1 §C (identity reuse refused; contradictory receipt refused; receipt kept) | PASS |
| verification→completion | `test_v16_close_d1` + workforce suite (re-run green); close binding static | PASS (suite-level) |
| completion→UI | installed-package probe: Work/About surfaces render, 0 leaks/errors | PASS (presence-level) |

**Composition note:** no single continuous live run crossing all legs exists in this environment (same class of limitation the corpus records; advanced legs need in-flight approvals/effects). Seat results are per-leg executed evidence.

## Journey B — Project A (memory/approval/artifact/attention) → switch to Project B → leakage attempts

- Memory: cross-project record/proposal/conflict ops **all refused**; unknown conversation fail-closed; omitted context defaults to `main` (probe-2). PASS.
- Approvals: declared-foreign resolution refused; **undeclared caller resolved a foreign approval (MAJOR-001)**; UI call sites declare the conversation (code). FINDING.
- Artifacts/attention: attention presence verified (21); cross-project artifact reads ride conversation scoping and were exercised only at suite level. Recorded limit.
- Verdict: isolation holds on memory/vetting/transcription surfaces; approvals is the recorded outlier.

## Journey C — coding work → approval → engine loss → restart → reconciliation → completion

- **Executed live on the auditor-built installed package** (r10): healthy boot → kill #1 recovered → kill #2 recovered → kill #3 **unrecoverable** (attempts=2) → manual retry → recovered; conversations/project/durable folder preserved; honest notices; 0 raw leaks/console errors.
- Reconciliation semantics: expired run → ORPHANED + fresh epoch + UNCERTAIN; stale delivery discarded (probe-3 D). No fabricated completion; retries durable across restart (probe-3 E).
- Approval-during-loss leg: covered by suite (epoch fencing; no grant path on recovery) — not independently constructed live.
- **PASS at package level** with the noted compositional leg.

## Journey D — D2/D3 → builder → verifier → findings → artifact lineage → learning shadow

- Suite re-run covers assignment/verifier/never-gate/close semantics (green), negative controls discriminate R2/R4; close_d1 binding incl. artifact-owner binding reviewed statically; learning shadow path (record_learning→memory) verified in INV-MEM-002 pass.
- Live D2/D3 pod run not performed (corpus-acknowledged harness limitation). **Disposition: suite+static PASS; live run gap recorded.**

## Journey E — pre-V1.6 state → install auditor-built RC → migrate → open → continue → restart → verify

- Migrations: max 21 constants + Campaign A `r12-upgrade` store at 21 (re-verified in 06); fresh/upgrade/round-trip/downgrade-guard results in 06.
- Auditor install (fresh target): install→boot→journey PASS; reinstall-over exit 0; uninstall clean with data-root retention; restart durability shown by r10 (state survived two engine deaths + one unrecoverable/manual cycle).
- Auditor did not rebuild a pre-V1.6 DB fixture itself beyond reviewing the packaged upgrade store; recorded as review-based for that leg.
- **PASS (review + live legs), gap recorded.**

**Summary: 5/5 journeys dispositioned; Journey C fully live on the independent build; compositional gaps recorded per journey.**
