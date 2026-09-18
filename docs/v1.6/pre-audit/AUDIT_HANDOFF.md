# AUDIT_HANDOFF — Campaign B entry point

status: OPEN — this file is finalized at PRE-AUDIT RC
updated: 2026-09-18T16:05Z

When Campaign A closes, this file binds the exact range and points to everything else. Until then
it carries the current values; treat every `TBD` as not-yet-true.

## Bindings

| Field | Value |
|---|---|
| PRE_AUDIT_V1_6_HEAD | TBD (recorded at RC in `docs/v1.6/PRE_AUDIT_RELEASE_CANDIDATE.md`) |
| last_independently_audited_commit | `8a2b25d` (audit increment 24 CONTINUE; cumulative coverage `5e76b21..8a2b25d`) |
| unaudited production range | opens with the first Campaign A production commit (TBD); ends at PRE_AUDIT_V1_6_HEAD |
| integration branch | `ux/v15-journeys` (stable branch `main` holds the last frozen release, v1.5.0) |
| migration version at open | 19 applied (max); next free version = 20 |
| production commit count in range | TBD (see COMMIT_LEDGER.md) |
| major changed subsystems | TBD (filled per phase; seed: memory, capabilities/UX, providers, workforce wiring, engine-loss UX, visual integration) |
| high-risk commits | TBD (recorded per increment in COMMIT_LEDGER.md) |

## Index paths

- Requirements index: `docs/v1.6/pre-audit/REQUIREMENTS_TRACEABILITY.md`
- Commit ledger: `docs/v1.6/pre-audit/COMMIT_LEDGER.md`
- Change ledger: `docs/v1.6/pre-audit/CHANGE_LEDGER.md`
- Invariant ledger: `docs/v1.6/pre-audit/INVARIANT_LEDGER.md`
- Test evidence index: `docs/v1.6/pre-audit/TEST_EVIDENCE_INDEX.md`
- Packaged evidence index: `docs/v1.6/pre-audit/PACKAGED_EVIDENCE_INDEX.md`
- Migration ledger: `docs/v1.6/pre-audit/MIGRATION_LEDGER.md`
- Provider matrix: `docs/v1.6/pre-audit/PROVIDER_VALIDATION_MATRIX.md`
- Visual evidence index: `docs/v1.6/pre-audit/VISUAL_EVIDENCE_INDEX.md`
- P2/P3 disposition: `docs/v1.6/pre-audit/P2_P3_DISPOSITION.md`
- Risk register: `docs/v1.6/pre-audit/RISK_REGISTER.md`
- Known limitations: `docs/v1.6/pre-audit/KNOWN_LIMITATIONS.md`
- Deferred items: `docs/v1.6/pre-audit/DEFERRED_ITEMS.md`
- Audit targets (attack list): `docs/v1.6/pre-audit/AUDIT_TARGETS.md`
- Repair hints: `docs/v1.6/pre-audit/REPAIR_HINTS.md`
- Final state matrix: `docs/v1.6/pre-audit/FINAL_STATE_MATRIX.md`
- Increment records: `docs/v1.6/pre-audit/increments/`
- Raw evidence: `docs/v1.6/pre-audit/evidence/`
- Historic audit records (independent): `C:\Users\Nick\Desktop\Kel\kel-v16-code-audit\docs\code-audit\`
- Historic program records: `docs/v1.6/` (phase5 records, AUTO_RESUME, status) and
  `docs/session-tools/`, `docs/memory-proposals/`, `docs/artifact-lineage/`,
  `docs/in-chat-approvals/`, `docs/i18n-cleanup/`, `docs/release-hardening/`

## Suggested audit traversal order

1. `README.md` → this file (bind the range; verify `PRE_AUDIT_V1_6_HEAD` is an ancestor of the
   integration branch and the tree is clean).
2. `COMMIT_LEDGER.md` → for each production commit: increment record → evidence bundle.
3. `CHANGE_LEDGER.md` → for each CHG: read the primary files and attack the recorded failure paths.
4. `REQUIREMENTS_TRACEABILITY.md` → find requirements without implementation AND implementations
   without requirements.
5. `INVARIANT_LEDGER.md` + `AUDIT_TARGETS.md` → attack each invariant with the seed list first,
   then free-form adversarial testing.
6. `MIGRATION_LEDGER.md` → fresh and upgrade DB runs; packaged schema assertions.
7. `TEST_EVIDENCE_INDEX.md` / `PACKAGED_EVIDENCE_INDEX.md` → re-run the critical commands; confirm
   counts; verify packaged claims on a real build.
8. `P2_P3_DISPOSITION.md` → re-verify every disposition (including the historical F-findings).
9. `VISUAL_EVIDENCE_INDEX.md` → walk findings, screenshots, packaged acceptance; note the human
   pixel gate is separate.
10. `PROVIDER_VALIDATION_MATRIX.md` → disposition every provider row (mock vs real).
11. `RISK_REGISTER.md`, `KNOWN_LIMITATIONS.md`, `DEFERRED_ITEMS.md` → acknowledge each; challenge
    the ones that hide behind "deferred".
12. Produce the master findings ledger (stable ID scheme) — no fixes.

## Exact definition of audit completeness (for Campaign B)

100% of the declared V1.6 scope accounted for means the auditor can prove, with evidence:

- every production commit in the range reviewed (COMMIT_LEDGER.md rows closed);
- every changed production file reviewed (per-commit file lists);
- every migration reviewed and exercised (fresh + upgrade);
- every requirement dispositioned (both directions);
- every invariant challenged (attempt documented, result recorded);
- every P2/P3 disposition checked;
- every major user journey exercised or explicitly reviewed;
- every persistence/isolation expectation considered;
- failure injections considered (engine loss, provider loss, restore failure, lease failure,
  capability abuse);
- every provider path dispositioned (real / mock / unavailable — never blurred);
- every visual finding dispositioned (automated vs human separate);
- every release gate dispositioned;
- every known limitation acknowledged as accepted or escalated.

This does NOT mean a metaphysical guarantee that no bug exists. It means every declared item is
accounted for, with evidence, and nothing silently disappears.
