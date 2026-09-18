# Increment — PHASE7-CAPABILITY-RECOMMENDATIONS

increment_id: PHASE7-CAPABILITY-RECOMMENDATIONS
phase: 7 — smart capability recommendations (sprint §32)
base_commit: ac5e2a2 (Phase 6 record; published checkpoint)
target_commit: the Phase 7 implementation commit + this docs commit
status: complete (code) / packaged evidence deferred (documented)

## Objective

Turn capability refusals into real, actionable recommendations — only real capabilities, only real
actions, no nagging, no no-op surfaces — reusing the session-tools policy unchanged.

## Requirement Sources

- Sprint directive §32.
- `docs/session-tools/08_KNOWN_LIMITATIONS.md` #2 (the docketed next increment).
- `docs/basic-ux-sweep/17…` §8 / `18…` §4 (decision trail: no detector, no nagging).

## Implementation Summary

- `runtime/kel/capabilities.py`: new `recommendation(capability, decision)` (the single vocabulary).
- `runtime/kel/research.py` + `runtime/kel/coding.py`: blocked outcomes carry `capability` +
  `recommendation` (same helper).
- `runtime/kel/core.py`: milestone retains the recommendation on blocked settles; cleared on success.
- Desktop: `renderer/components/kel/capabilityRecommendation.ts` (mapping/request/confirmation
  helpers), `renderer/components/kel/KelCapabilityCard.tsx` (fail-closed action rendering; real
  endpoints; keep-it-off dismisses without state change), mounted in `KelWorkPanel` job section
  with per-job/milestone dismissal.

## Files Changed

- `runtime/kel/capabilities.py`, `runtime/kel/research.py`, `runtime/kel/coding.py`,
  `runtime/kel/core.py`
- `runtime/tests/test_capabilities.py` (+7 tests)
- `desktop/packages/desktop/src/renderer/components/kel/capabilityRecommendation.ts` (new)
- `desktop/packages/desktop/src/renderer/components/kel/KelCapabilityCard.tsx` (new)
- `desktop/packages/desktop/src/renderer/components/chat/KelWorkPanel.tsx`
- `desktop/tests/unit/capability-recommendation.test.ts` (new, 7 tests)

## Symbols Changed

`recommendation()` (new); ResearchAdapter.execute / coding execute blocked returns; Store.consume
milestone settle; `KelCapabilityCard`; `capabilityCardActions` / `capabilityActionRequest` /
`capabilityConfirmation` (new).

## Schema/Migrations

None (max applied migration remains 19).

## User-Facing Behavior

A blocked capability now carries a card in the Work panel: "Kel paused something that needs Web."
+ reason + Allow once / Enable for this chat / Keep it off. Acting uses the existing machinery;
keeping it off changes nothing and dismisses.

## Internal Behavior

Blocked run results gain machine-readable `capability` + `recommendation`; job milestones retain
them so `/api/state` consumers can render them; success clears them.

## Error Paths

Unknown action ids drop (fail-closed); failed `/api/capabilities` call shows one plain sentence
("Kel could not change that just now."); unavailable capabilities get no card (None).

## Lifecycle Considerations

None (no lifecycle surface touched).

## Persistence / Isolation

None changed — same tables, same scoping; recommendations are data on the milestone only.

## Security / Privacy

No widening: recommendations never change state; grants stay single-use + TTL; overrides stay
conversation-scoped; lease/approval gates still run after.

## Self-Review Findings

- Coding-refusal attachment is mechanically identical to research but has no dedicated
  blocked-run discrimination test (fixture cost) — recorded as an audit target.
- Work-panel placement chosen over transcript-inline: the transcript variant needs a live-run
  refusal this environment cannot produce (recorded DEF-014 + LIM-14).

## Tests Run

- `cd runtime && python -m pytest tests/test_capabilities.py tests/test_research.py tests/test_acp_host.py tests/test_v13_work_context.py tests/test_v15_completion.py -q` → **83 passed**.
- `cd runtime && python -m pytest tests -q` → see TEST_EVIDENCE_INDEX (full-suite row A-6).
- `cd desktop && bunx tsc --noEmit` → **0 errors**; `bun run test` → **90 passed** (was 83).

## Results

PASS (source + focused). Packaged evidence deferred (no provider; see bound above).

## Packaged Verification

Not run for this increment; recorded in PACKAGED_EVIDENCE_INDEX as the next battery's item.

## Known Weaknesses

- Card packaged rendering unproven in this environment (recorded).
- No dedicated coding-blocked discrimination test (recorded).

## Deferred Questions

- Should the transcript-inline placement reuse this payload via a chat notice once live refusals
  exist? Recorded as DEF-014.

## Audit Targets

See AUDIT_TARGETS.md §"Capability recommendations (Phase 7)".

## Repair Hints

See REPAIR_HINTS.md rows for guard drift and the card.

## Evidence Paths

- `docs/v1.6/phase7/CAPABILITY_RECOMMENDATIONS.md`
- `docs/v1.6/pre-audit/` corpus rows (COMMIT_LEDGER, CHANGE_LEDGER CHG-003, TEST_EVIDENCE_INDEX,
  REQUIREMENTS_TRACEABILITY, INVARIANT_LEDGER INV-CAP-002, KNOWN_LIMITATIONS, DEFERRED_ITEMS,
  AUDIT_TARGETS)

## Commit Chain

`ac5e2a2` → Phase 7 implementation commit → this docs commit.
