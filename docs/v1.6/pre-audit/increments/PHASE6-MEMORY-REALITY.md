# Increment — PHASE6-MEMORY-REALITY

increment_id: PHASE6-MEMORY-REALITY
phase: 6 — memory reality audit (bootstrap §28) + bounded fixes
base_commit: 785df71 (Campaign A entry)
target_commit: `22f4a3e` (production fixes) + this docs commit (record + corpus updates)
status: complete

## Objective

Audit the memory subsystem's reality end-to-end (controls, reachable UX, persistence, isolation,
provenance, edits/corrections, forget semantics, hidden/no-op behavior, backend/UI mismatch) and
apply bounded fixes where the reality diverged from the design.

## Requirement Sources

- Sprint directive (2026-09-18) §31; bootstrap §28.
- `docs/v1.3/KEL_V1.3_MEMORY_MODEL.md` (trust model).
- `docs/memory-proposals/01..07` (v1.6 proposal surface spec: triggers, UI/copy).

## Implementation Summary

Full audit in `docs/v1.6/phase6/MEMORY_REALITY_AUDIT.md`. Bounded fixes (commit `22f4a3e`):

1. Work-panel knowledge actions now follow the record's state (the panel previously offered
   confirm/edit/retract on records the engine refuses, and re-purge on tombstones). The matrix
   lives in a small pure helper `memoryRecordActions` mirroring the engine guards.
2. Forget (irreversible content purge) now asks for confirmation.
3. Forgotten tombstones render "Content removed." instead of a blank line.

## Files Changed

- `desktop/packages/desktop/src/renderer/components/chat/KelWorkPanel.tsx`
- `desktop/packages/desktop/src/renderer/components/kel/memoryRecordActions.ts` (new)
- `desktop/tests/unit/memory-record-actions.test.ts` (new)

## Symbols Changed

- `memoryRecordActions()` (new); KelWorkPanel records-list render block; `Popconfirm` import.

## Schema/Migrations

None (no engine change; max applied migration remains 19).

## User-Facing Behavior

- Actions that the engine would refuse no longer appear on a record.
- Forgetting a record requires confirmation; the dialog states the content cannot be recovered.
- Forgotten records read "Content removed.".

## Internal Behavior

- UI guard parity with `Memory.confirm/correct/retract/forget` is now explicit and unit-tested.

## Error Paths

- Removed the reachable UI path that produced refused-action errors (`Only an active memory can be
  corrected/confirmed/retracted`). Engine-side refusals remain as defense in depth.

## Lifecycle Considerations

- None (renderer-only). No engine lifecycle surface touched.

## Persistence / Isolation

- None changed; INV-MEM-001 preserved (engine untouched; all API actions unchanged).

## Security / Privacy

- None changed. Forget confirmation reduces accidental destructive purge.

## Self-Review Findings

- Verified the gating matrix against the engine guards line-by-line (memory.py confirm/correct/
  retract/forget) before writing the helper.
- Noted that `user_change`/`repo_state`/`correction` proposal kinds and `Memory.revalidate()` have
  no production callers — documented (MEMR-4/MEMR-5) rather than "fixed".

## Tests Run

- `cd runtime && python -m pytest tests/test_v13_memory.py tests/test_v15_memory_packets.py tests/test_v16_proposals.py tests/test_workforce_learning.py -q` → **68 passed** (pre-change baseline; engine untouched).
- `cd desktop && bunx tsc --noEmit` → **0 errors**.
- `cd desktop && bun run test` → **83 passed** (was 76; +7 new gating tests).

## Results

PASS (source-level). Packaged verification deferred to the RC battery (renderer-only change; the
Knowledge tab has no packaged journey yet — recorded as an RC-battery gap).

## Packaged Verification

Not run for this increment (see above). No regression surface for existing packaged probes
(memoryprops exercises the chat pill + proposal actions, which are unchanged).

## Known Weaknesses

- The action matrix is UI-side mirroring; if engine guards change, the helper must follow
  (audit target recorded).
- APR-03 (vetting→memory queue durability) reviewed and carried to the P2/P3 sweep.
- MEMR-4 stale wiring and MEMR-7 locale pass are deferred with records.

## Deferred Questions

- Should the Knowledge tab list keep showing superseded/retracted records (currently yes, with
  status labels)? Disposition: keep — history is honest and forget now purges explicitly.

## Audit Targets

- See AUDIT_TARGETS.md §"Memory reality (Phase 6 additions)".

## Repair Hints

- UI/engine guard drift: `memoryRecordActions.ts` vs `memory.py` guards.

## Evidence Paths

- `docs/v1.6/phase6/MEMORY_REALITY_AUDIT.md`
- `docs/v1.6/pre-audit/` (corpus rows updated: COMMIT_LEDGER, CHANGE_LEDGER CHG-001/002,
  TEST_EVIDENCE_INDEX, REQUIREMENTS_TRACEABILITY, KNOWN_LIMITATIONS, DEFERRED_ITEMS, AUDIT_TARGETS)

## Commit Chain

`785df71` → `22f4a3e` (fixes) → this docs commit.
