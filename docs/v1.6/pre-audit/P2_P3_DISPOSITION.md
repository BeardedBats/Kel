# P2_P3_DISPOSITION — every finding, current disposition

updated: 2026-09-18T16:05Z (seed; completed during the P2/P3 sweep phase — sprint directive §40)
The full historic finding set lives in the audit records (`kel-v16-code-audit/docs/code-audit/`,
increments 1–24). This file carries the live disposition table and grows to cover every historic
P2/P3. Campaign B independently re-verifies every disposition; no finding disappears.

Allowed final dispositions: **FIXED · STALE · NOT_APPLICABLE · DEFERRED_NON_RELEASE ·
OPEN_RELEASE_BLOCKER**. Until the sweep sets a final value, rows read `OPEN (sweep pending)`.

## P2 — open at corpus open

| ID | Description (one line) | Severity | Source record | Current disposition | Fix commit | Test | Release relevance | Audit confirm |
|---|---|---|---|---|---|---|---|---|
| APR-01 | `/api/approvals` payload-actor rejection implicit; comment claims a guard that is absent | P2 | `13_PHASE3_DELTA_AUDIT.md`, `17_P1_REMEDIATION_REAUDIT.md` | OPEN (sweep pending) | — | add payload-actor test | TBD in sweep | pending |
| APR-02 | Approval resolution is not conversation-scoped while the read is | P2 | `13_PHASE3_DELTA_AUDIT.md` | OPEN (sweep pending) | — | cross-scope resolution test | TBD | pending |
| APR-03 | `_memory_check_queue` is instance state — queued memory checks lost on crash/restart between commit and flush (`vetting_session.py:95`) | P2 | `13_PHASE3_DELTA_AUDIT.md` | OPEN (sweep pending; Phase 6 reviewed — bounded crash-window only; durable-drain direction in REPAIR_HINTS) | — | durable drain + restart regression | TBD | pending |
| A1 | `engine_version` not validated on the detached-engine reuse path (`KelService.ts:43-52`) | P2 | `15_RUST_LEAD_VERIFICATION.md` | OPEN (sweep pending) | — | stale-descriptor boot test | TBD | pending |
| REL-01 | `freeze-release.ps1` engine staging is a no-op for the path the app loads and the manifest hashes | P2 | `15_RUST_LEAD_VERIFICATION.md`, `17_P1_REMEDIATION_REAUDIT.md` | OPEN (sweep pending) | — | freeze tooling test | TBD | pending |
| SEC-01 | Vetting session actions have no project/conversation ownership check (acceptance criteria recorded) | P2 | `11_FINDINGS.md`, `16_FINDING_STATUS.md` | OPEN (sweep pending) | — | cross-scope session attack | TBD | pending |
| PER-02 | A failed or partial restore is silent (`service.py` swallows `apply_pending_restore`) | P2 | `11_FINDINGS.md`, `16_FINDING_STATUS.md` (Rust-corroborated) | OPEN (sweep pending) | — | failure injection | TBD | pending |
| PER-03 | `.pre-restore-*` snapshots unbounded/never pruned; snapshot failure aborts restore silently | P2 | `11_FINDINGS.md`, `16_FINDING_STATUS.md` | OPEN (sweep pending) | — | retention test | TBD | pending |
| TR-01 | Transcription `_STREAMS` module-level stream sessions — shutdown/cleanup not reviewed | P2 | `02_FILE_REVIEW_LEDGER.md`, `06_RUNTIME_AND_PROCESS.md` | OPEN (sweep pending) | — | shutdown cleanup test | TBD | pending |
| TR-02 | Abandoned-stream UX in the transcription renderer (residual) | P2 | `02_FILE_REVIEW_LEDGER.md` | OPEN (sweep pending) | — | renderer state test | TBD | pending |

## P3 — open at corpus open

| ID | Description (one line) | Severity | Source record | Current disposition | Fix commit | Release relevance | Audit confirm |
|---|---|---|---|---|---|---|---|
| APR-04 | `approval_announcements` DDL defined twice, with no migration version | P3 | `13_PHASE3_DELTA_AUDIT.md` | OPEN (sweep pending) | — | TBD | pending |
| APR-05 | Approvals-arc minor (full text in `13_PHASE3_DELTA_AUDIT.md`; one-line completion during sweep) | P3 | `13_PHASE3_DELTA_AUDIT.md` | OPEN (sweep pending) | — | TBD | pending |
| APR-06 | Approvals-arc minor (full text in `13_PHASE3_DELTA_AUDIT.md`; one-line completion during sweep) | P3 | `13_PHASE3_DELTA_AUDIT.md` | OPEN (sweep pending) | — | TBD | pending |
| DEAD-06 | `packaging/ux-audit.cjs` unwired and misfiled (referenced by nothing outside docs) | P3 | `08_DEAD_CODE.md` | OPEN (sweep pending) | — | TBD | pending |
| CAP2-LONGTEXT | `directive_clauses()` returns `[]` above 2000 chars — reserved directives in long pastes silently ignored (fails safe) | P3 | `19_CAP2_RESIDUAL_REAUDIT.md` | OPEN (sweep pending) | — | TBD | pending |
| INT-01 | Inconsistent sender-frame validation (`kel:artifact-reveal` lacks the check) | P3 | `11_FINDINGS.md`, `16_FINDING_STATUS.md` | OPEN (sweep pending) | — | TBD | pending |
| PER-04 | `KEL_DATA_DIR` puts `kel-credentials.json` inside the backup root (override path only) | P3 | `16_FINDING_STATUS.md` | OPEN (sweep pending) | — | TBD | pending |
| COR-03 | `KelModelControl.setConversation` has no error path | P3 | `16_FINDING_STATUS.md` | OPEN (sweep pending) | — | TBD | pending |
| COR-04 | `set_conversation` accepts a non-existent conversation | P3 | `16_FINDING_STATUS.md` | OPEN (sweep pending) | — | TBD | pending |
| COR-05 | `search.py` bare `except` per section | P3 | `16_FINDING_STATUS.md` | OPEN (sweep pending) | — | TBD | pending |
| COR-06 | KeyError leaks from vetting/transcription dispatch | P3 | `11_FINDINGS.md` | OPEN (sweep pending) | — | TBD | pending |
| MDL-01 | `set_conversation` accepts a non-existent conversation (with COR-04) | P3 | `16_FINDING_STATUS.md` | OPEN (sweep pending) | — | TBD | pending |
| THM-01 | Theme overrides keyed by theme id survive theme deletion | P3 | `16_FINDING_STATUS.md` | OPEN (sweep pending) | — | TBD | pending |
| SEC-01-multipart | Caller-supplied filename interpolated into a multipart header unescaped (transcription) | P3 | `11_FINDINGS.md` | OPEN (sweep pending) | — | TBD | pending |
| DEAD-05 | `service.py` calls `Vetting` privates (`_questions`, `_format_resurface`) | P3 | `16_FINDING_STATUS.md` | OPEN (sweep pending) | — | TBD | pending |
| ERR-01 | KeyError leaks from dispatch (with COR-06) | P3 | `11_FINDINGS.md` | OPEN (sweep pending) | — | TBD | pending |

## Closed / retracted in the audited range (for completeness — do not re-open without cause)

- **CAP-01, CAP-02, CAP-03 (P1)** → FIXED (`75d1f68`, `327e5b2`, `631881a`; audits 3–5 CONTINUE).
- **CAP2-CLAUSE / CAP2-RESIDUAL (P1-adjacent)** → FIXED (bracketed clause → reserved `[kel:...]`
  namespace; negative-control discrimination recorded).
- **DEAD-01** superseded; **DEAD-07** superseded; **DEAD-08** FIXED with fail-closed regression.
- **I18N-01** — RETRACTED by the auditor (structurally unobservable; audit 7 self-correction).
- Per-increment F-findings (F1–F23 arcs): closure tables live in the numbered audit records
  `21`–`37`; none remain open except as carried in the rows above (F4/F16-3/F17-4/F18-5/R22-3 are
  carried items with their own dispositions in DEFERRED_ITEMS.md / REQUIREMENTS_TRACEABILITY.md).

## Sweep worklist (sprint §40)

1. Complete one-line descriptions for APR-05/06 from `13_PHASE3_DELTA_AUDIT.md`.
2. Decide per finding: release-relevant → fix in Campaign A; else DEFERRED_NON_RELEASE with a
   rationale.
3. Every fix gets a test + a CHANGE_LEDGER entry + an updated row here.
4. Campaign B re-verifies all rows; discrepancies are findings.
