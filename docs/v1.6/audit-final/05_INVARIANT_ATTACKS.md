# 05 — INVARIANT ATTACKS (final)

Rule: results are limited to what the auditor actually executed or inspected. This file is the execution log; the 42-row disposition map lives in `04_REQUIREMENTS_COVERAGE.md`.

## Executed attack batteries

1. **PROBE-1** (`probes/auditor_probe_1.py` → `evidence/auditor-probe-1.log`): approvals scope/omission (→**AUD-MAJOR-001**), window/duplicate-exact, effect identity reuse + contradictory receipt, canonical encode (NaN/Infinity/bytes/set), delegation widening ×4 (all refused), budget envelope (→**AUD-MINOR-002**), capability grammar + negative controls (→**AUD-SUG-001**), credential sentinels (→**AUD-MINOR-003**), packaged DB receipts.
2. **PROBE-2** (memory → `evidence/auditor-probe-2-memory.log`): provenance/trust/preference/decision rules, synthetic secret refusal, correction/supersession/retraction, forget/tombstone/history, proposals dedupe+lifecycle, full service-layer cross-project battery (records, proposals, conflicts; fail-closed defaults). **No new findings.**
3. **PROBE-3** (workforce/liveness → `evidence/auditor-probe-3-workforce.log`): commander control (inconclusive control; suite stands), flag-off zero writes (PASS), retry budget across fresh `Store` + third-claim refusal (PASS), expired-run classification → ORPHANED + fresh epoch + UNCERTAIN (PASS), stale delivery discarded (PASS, no fabricated completion).
4. **PROBE-4** (transcription/vetting → `evidence/auditor-probe-4-vetting-transcription.log`): vetting cross-conversation ingest/process/finish refused; panel display-read recorded (documented surface); TR-01 lifecycle re-verified; TR-02 semantics unchanged; key workflow presence-only.
5. **Negative controls** (17): pre-APR-02 → 6F+1E; pre-R2 → 1F; pre-R4 → 1F. Discriminating.
6. **Package stunts** (15): independent rebuild; silent install; reinstall-over; uninstall/retention; installed-package journey; **engine-loss ladder on the installed auditor build** (kill→recover ×2, third kill → unrecoverable, manual retry → recovered; work preserved; 0 leaks/errors) — `evidence/auditor-r10*`.
7. **Suite re-runs at RC**: engine 998+10 pass exit 0; desktop vitest 122/122. Brand check PASS; frozen refs verification.

## Coverage adjustments since the mid-audit revision

Every family previously marked "NOT YET EXECUTED" is now executed, suite-covered, statically reviewed, or carries its recorded finding: memory ✔ (probe-2), live-authority ✔ (probe-1 A + suite), verifier-independence ✔ (static + suite + controls), lease ✔ (static reclaim read), IPC ✔ (**AUD-MAJOR-002**), WF families ✔ (probe-3 + static + suite), lineage ✔ (close_d1 static + suite), retry-restart ✔ (probe-3 E), completion/liveness ✔ (probe-3 D + r10), restore/snapshot ✔ (suite + MINOR-005), package rebuild/installed identity ✔ (15), engine-hash table ✔ (source==staged==packaged==installed, exact), r10 precision ✔ (MINOR-004 d), transcription/vetting ✔ (12), attention ✔ (21), journeys ✔ (20), blind spot ✔ (18).

**Completeness: 42/42 invariants dispositioned; no silent passes; no `TBD`.**
