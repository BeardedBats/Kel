# 05 — INVARIANT ATTACKS (Campaign B)

Rule: results below are limited to what the auditor actually executed or inspected. "NOT YET EXECUTED" is stated explicitly — no silent passes. `PROBE-1` = `probes/auditor_probe_1.py` (output `evidence/auditor-probe-1.log`). Suite = full engine suite re-run by the auditor at RC (`evidence/auditor-engine-suite.log`, 998 passed + 10 subtests, exit 0). Vitest = desktop suite re-run (`evidence/auditor-desktop-vitest.log`, 122/122, 12 files).

| family | invariants | attack executed | result | evidence |
|---|---|---|---|---|
| AUTH-DELEGATION (class/scope/effects/tools/boundaries) | INV-AUTH-DELEGATION / INV-AUTH-001 | PROBE-1 E1–E4: child with wider class; extra tool; scope escape; nested contract without delegator | REFUSED with correct messages ("Delegation may narrow authority but never create it: …") | probe log; contracts.py:201-209; tests/test_v16_r1_authority.py (suite re-run green) |
| AUTH-DELEGATION (budget dimension) | INV-AUTH-001 (budget) | PROBE-1 E5–E7: cost 1e9 refused; tokens=1e12 and wallclock=1e7 accepted; cumulative cost 1+8 accepted over an 8.0 envelope | PARTIAL — per-call cost check works; cumulative accounting does not (AUD-MINOR-002); token/wallclock caps disclosed-absent (R1 increment line 105) | probe log; assignment.py:598-615 |
| AUTH-DELEGATION (path tricks) | INV-AUTH-001 | child `src/../secrets` vs parent `src`; `.`/`..` roots (inline probes) | `src/../secrets` escape ACCEPTED by `authority_within`; `.` parent root = universal by design; `..` alone refused. Consumer analysis IN VERIFICATION | inline probe transcript; `_path_within` read pending |
| EVENT-IDEMPOTENCY | INV-EVENT-IDEMPOTENCY / INV-IDEM-001 | PROBE-1 C1–C2: operation identity reused with different target; identical receipt re-observed | REFUSED ("Operation identity reused…"); second identical observation = no-op | probe log; suite (R2 tests) green |
| EFFECT-REPLAY | INV-EFFECT-REPLAY / INV-EFFECT-001 | PROBE-1 C3: contradictory receipt after OBSERVED | REFUSED ("different receipt"); stored evidence kept | probe log; suite green |
| RETRY-DURABLE | INV-RETRY-DURABLE / INV-RETRY-001 | full-suite re-run incl. `test_v16_r3_retry_durability.py`; instrumented live restart harness NOT built | PARTIAL (suite green; independent restart attack NOT YET EXECUTED) | auditor-engine-suite.log |
| APPROVAL-EXACT | INV-APPROVAL-EXACT / INV-APPROVE-002 | PROBE-1 A1/A5 (declared foreign refused); B1 window expiry → EXPIRED; B3 second resolution refused | PASS for exact/scope/window/duplicate with declared callers; duplicate-resolution message reads "does not match this action" (cosmetic oddity) | probe log; suite R4 green |
| PERSIST-CANONICAL | INV-PERSIST-CANONICAL / INV-PERSIST-001 | PROBE-1 D: NaN / Infinity / bytes / set into `encode` | NaN/Infinity → PolicyError; bytes/set → TypeError (refused, non-Policy type) | probe log |
| COMPLETION-TRUTH | INV-STATE-001 | suite R6 tests re-run; independent idle/waiting simulation NOT YET EXECUTED | PARTIAL | auditor-engine-suite.log |
| LIVENESS-SEPARATION | INV-LIVENESS-002 | suite R6 tests re-run; independent stalled-process probe NOT YET EXECUTED | PARTIAL | auditor-engine-suite.log |
| RECOVERY-CLASSIFICATION | INV-RECOVERY-002 | suite R6 tests re-run; family interruption battery NOT YET EXECUTED | PARTIAL | auditor-engine-suite.log |
| MEMORY-PROVENANCE | INV-MEM-001/002/003 | NOT YET EXECUTED (queued; targets 10–13, 32–39) | — | — |
| CREDENTIAL-CONTAINMENT | INV-CRED-001 | PROBE-1 G1–G3: internal child env whitelist; redact masking | PASS for Kel-managed keys; G4 native CLI children inherit DEEPSEEK_API_KEY → AUD-MINOR-003 | probe log; suite R7 green |
| LIVE-AUTHORITY | INV-AUTH-002 | NOT YET EXECUTED (queued) | — | — |
| VERIFIER-INDEPENDENCE | INV-WF-002 / INV-AUDIT-001 | NOT YET EXECUTED (queued: assurance close-path read + builder==verifier attempt) | — | — |
| PACKAGE-IDENTITY | INV-PACKAGE-001 | frozen spot hashes (2/8 recomputed, both exact); packaged DB max migration 21 (fresh + upgrade); source==staged==packaged==installed engine-hash comparison PENDING; stale-dist attack PENDING | PARTIAL | evidence/frozen-hash-spotchecks.txt; probe H |
| FREEZE-IMMUTABLE | INV-FREEZE-001 | tags main/v1.5.0/v1.6.0-pre1 re-resolved; frozen Kel.exe hashes match manifests; remote exact | PASS (spot-level) | 01_REPOSITORY_INTEGRITY.md §3 |
| CAPABILITY-GRAMMAR | INV-CAP-001/002 / INV-CAPREC-001 | PROBE-1 F1 (unknown capability refused); clause attacks: quoted / inline code / fenced / nested / word-embedded / scheme-URL / unknown-cap / bad-state → inert; mixed-case + punctuation-adjacent recognized BY DESIGN (tests); bare-path/log-line token recognized → IN VERIFICATION (double-use foot-gun vs stated exclusion intent) | PARTIAL | probe log + inline clause probes; tests/test_capabilities.py:163-180, 215-219, 321-325 |
| APPROVAL-CANONICAL-RESOLUTION | INV-APPROVE-001 | PROBE-1 A2/A6: undeclared caller resolves foreign approval (state approved) while declared callers are refused | FAIL — AUD-MAJOR-001 recorded | probe log; chat_approvals.py:334; service.py:687 |
| ERROR-NON-MASKING | INV-ERROR-001 | suite + code read + R12 evidence; independent restore+snapshot failure injection NOT YET EXECUTED | PARTIAL | suite green |
| LEASE-EXACT | INV-LEASE-001 | NOT YET EXECUTED (queued) | — | — |
| IPC-SENDERFRAME | INV-IPC-001 | NOT YET EXECUTED (handler-set read pending; no Electron harness — read-only attack planned) | — | — |
| WF-COMMANDER | INV-WF-001 | NOT YET EXECUTED (queued) | — | — |
| WF-FLAGOFF | INV-WF-003 | NOT YET EXECUTED (queued) | — | — |
| WF-NEVERGATE | INV-WF-004 | NOT YET EXECUTED (queued) | — | — |
| WF-BOUND-EVIDENCE | INV-WF-005 | NOT YET EXECUTED (queued) | — | — |
| WF-APPENDONLY | INV-WF-006 | NOT YET EXECUTED (queued) | — | — |
| LINEAGE | INV-LINEAGE-001 | NOT YET EXECUTED (queued) | — | — |
| ROUTING | INV-ROUTE-001 | provider probes: claude real call "ok" (exit 0); codex re-confirmed environment block (HTTP 400 "gpt-6-astra … requires a newer version of Codex"); matrix reviewed | PARTIAL (FIXED/fallback runtime paths not yet attacked) | evidence/provider-*.txt; PROVIDER_VALIDATION_MATRIX.md |
| UI-RAW-ERRORS | INV-UI-001 | R10/R12 retained evidence reviewed (DOM leak scan clean in cited runs); r10 doc-precision check pending | PARTIAL | ux-audit/runs/*; visual digest |
| GIT-PUBLICATION | INV-GIT-001 | remote refs authoritative (`git ls-remote` = local = claimed); range re-scanned by the auditor; no-force-push statement cross-checked | PASS (spot) | 01_REPOSITORY_INTEGRITY.md; evidence/git-* |
| VISUAL-ISOLATION | INV-VISUAL-001 | merge topology verified (lane re-anchor `3050761`, R11 integration `7267630`) | PARTIAL (zero-overlap claim not independently diffed yet) | git-range log |

Pending list (explicitly not yet executed): memory probes; live-authority; verifier-independence; lease; IPC; WF families; lineage; retry restart harness; completion/liveness stunts; restore/snapshot injection; package rebuild + installed-engine identity; engine-hash table completion; r10 doc precision; memory-adjacent cross-scope battery; transcription/vetting batteries; Needs-Your-Attention attacks; journeys A–E; blind-spot pass. Plans are queued in `AUDIT_STATUS.md`.
