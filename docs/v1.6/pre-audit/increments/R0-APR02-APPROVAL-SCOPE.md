# Increment — R0 / APR-02: approval resolution is conversation-scoped (round 2.5 APPROVAL-EXACT groundwork)

increment_id: V16-R0-APR02-APPROVAL-SCOPE
phase: Campaign A — roadmap R0 (finish the P2/P3 sweep) · APR-02
base_commit: 9eab3c6 (round 2.5 roadmap checkpoint)
target_commit: the implementation commit + this docs commit
status: complete

## Objective

Close APR-02 — "approval resolution is not conversation-scoped while the read is" — inside the
existing approval system, with no second approval path and no contract break. Round 2.5 §D
(APPROVAL-EXACT) absorbs this row into R4's exact-binding work; R0 closes the scoping half now.

## Verification before the change (current tree)

- `chat_approvals.items()` (the READ path) is conversation-scoped through `_job_ids_for(db,
  conversation)` — jobs by their `conversation` field plus continuation `job_links`.
- `chat_approvals.resolve()` (the WRITE path) took only `kind` + `ref_id`; the id alone decided
  which approval row settled, so an id from another conversation could settle work the caller was
  not looking at. `Store.resolve_approval` already re-validates actor, status and the action
  **digest** — but not scope.
- The desktop sent `{kind, id, allow}` with no conversation on both call sites (Work panel and the
  in-chat approval card).

## Implementation Summary

1. **Engine scope gate** (`kel/chat_approvals.py`): new `_require_owned(store, kind, ref_id,
   conversation)` resolves the record's owning job (`approvals.job_id`, or
   `boundary_expansion_requests → capability_leases.job_id`) and refuses when that job is not in
   `_job_ids_for(conversation)` — the *same* ownership set the read path uses, so the two paths
   cannot drift. `resolve(..., conversation=None)` applies it only when the caller declares a
   conversation, keeping the HTTP contract additive (callers that declare nothing behave exactly as
   before).
2. **Route** (`kel/service.py`): `_approvals_action` passes `conversation=data.get('conversation')`.
3. **Desktop declares its conversation**: the in-chat card sends the engine conversation it resolved
   (`engineCid || conversationId`); the Work panel sends its `cid`. Both already fetched their
   items with the same conversation id, so list and resolve now agree by construction.
4. **Latent read-path bug fixed**: `_job_ids_for` assumed `job_links` exists; bare stores (engine
   tests, very early boots) have no such table, which broke the shared helper once the write path
   started using it. It is now guarded, which also protects `items()` on those stores.

## Files Changed

- `runtime/kel/chat_approvals.py` (`_require_owned`, `resolve(..., conversation)`, guarded
  `_job_ids_for`)
- `runtime/kel/service.py` (`_approvals_action` passes the declared conversation)
- `runtime/tests/test_v16_approvals.py` (6 new scope tests)
- `desktop/packages/desktop/src/renderer/components/kel/KelApprovalCard.tsx`,
  `desktop/packages/desktop/src/renderer/components/chat/KelWorkPanel.tsx` (send the conversation)

## Symbols Changed

`chat_approvals._require_owned` (new), `chat_approvals.resolve`, `chat_approvals._job_ids_for`,
`Service._approvals_action`, `KelApprovalCard.act`, `KelWorkPanel.approvalAct`.

## Schema/Migrations

None.

## User-Facing Behavior

No visible change. A resolution can no longer settle an item the user is not looking at.

## Internal Behavior

`/api/approvals` (resolve) now refuses with `That request belongs to another conversation` when a
declared conversation does not own the record; an unknown id still refuses with
`Approval request missing`.

## Error Paths

Refusals are `PolicyError`s on the existing route; the item stays pending and resolvable from its own
conversation (asserted by the first test).

## Lifecycle Considerations

None (no new state).

## Persistence / Isolation

None beyond the scope check; isolation *improves* (cross-conversation settlement impossible when the
caller declares its conversation).

## Security / Privacy

This is the release-relevant half of a systemic pattern (RISK-003: bare-id addressing). The digest
binding from V1.5 stays untouched; Round 2.5's full APPROVAL-EXACT work (target normalization,
preconditions, revalidation immediately before execution) remains **R4**.

## Self-Review Findings

- The first version of the service-level test used `self.service`, which `ApprovalBase` does not
  define; the test now constructs its own `Service` over the same data root. Test bug, not product.
- The `job_links` guard was found *because* the write path started sharing the read helper — a real
  latent fragility in the read path, now covered by the same tests that exercise both.

## Tests Run

- `cd runtime && python -m pytest tests/test_v16_approvals.py tests/test_v16_sweep_fixes.py -q`
  → **33 passed** (6 new: other-conversation refusal for a step approval and for a boundary grant, a
  foreign-conversation job, unknown id, additive no-conversation behaviour, and the service route).
- `cd desktop && bunx tsc --noEmit` → 0; `bun run test` → **93 passed**.
- Full engine suite: see TEST_EVIDENCE_INDEX A-19.

## Results

PASS.

## Packaged Verification

Not applicable to this increment (engine + renderer payload change); the RC packaged battery
re-runs the engine suite and the packaged journeys.

## Known Weaknesses

- The scope gate only applies when the caller declares a conversation; a hypothetical future caller
  could omit it (the desktop never does). Round 2.5's R4 work should make the declaration mandatory
  for the in-app routes rather than optional — recorded as an R4 input.
- The remaining R0 rows (SEC-01, TR-01, TR-02, 7 P3s) stay OPEN until their own increments.

## Deferred Questions

- Should the engine *require* `conversation` on `/api/approvals` once no legacy caller exists?
  (R4 decision; the additive path keeps old clients working meanwhile.)

## Audit Targets

AUDIT_TARGETS §75 (approval from the wrong conversation must be refused) — now covered by tests;
§73–§74 (normalization/mutation invalidation) remain R4.

## Repair Hints

`_require_owned` is the single scope gate; `_job_ids_for` is the single ownership set. R4 should
extend both rather than adding a parallel check.

## Evidence Paths

- `docs/v1.6/pre-audit/increments/R0-APR02-APPROVAL-SCOPE.md` (this file)
- corpus rows: P2_P3_DISPOSITION (APR-02), CHANGE_LEDGER CHG-011, TEST_EVIDENCE_INDEX A-19
