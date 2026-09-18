# Increment — P2/P3 sweep batch 3: snapshot retention fixed, actor guard pinned, three rows verified-open

increment_id: V16-SWEEP-BATCH3
phase: Campaign A — P2/P3 sweep (audit docket) · PER-03, APR-01, APR-02, APR-03, SEC-01, TR-02
base_commit: 11e1525 (A1 docs)
target_commit: the implementation commit + this docs commit
status: complete

## Objective

Continue the sweep over the remaining P2s: fix what is bounded and provable, pin with a test what the
docket explicitly asks to be tested, and record exactly what is still open (with the code evidence)
rather than quietly deferring it.

## Requirement Sources

- `PER-03` — `11_FINDINGS.md`, `16_FINDING_STATUS.md` (P2): "`.pre-restore-*` snapshots
  unbounded/never pruned; snapshot failure aborts restore silently".
- `APR-01` — `13_PHASE3_DELTA_AUDIT.md`, `17_P1_REMEDIATION_REAUDIT.md` (P2): "`/api/approvals`
  payload-actor rejection implicit; comment claims a guard that is absent" with the requested
  remedy "add payload-actor test".
- `APR-02` — `13_PHASE3_DELTA_AUDIT.md` (P2): "Approval resolution is not conversation-scoped while
  the read is".
- `APR-03` — `13_PHASE3_DELTA_AUDIT.md` (P2): `_memory_check_queue` is instance state.
- `SEC-01` — `11_FINDINGS.md`, `16_FINDING_STATUS.md` (P2): vetting session actions lack
  project/conversation ownership checks.
- `TR-02` — `02_FILE_REVIEW_LEDGER.md` (P2): abandoned-stream UX residual.

## Verification (current tree, 2026-09-18)

| Row | What the code says today |
|---|---|
| PER-03 | `backup.py:296` creates `root.name + '.pre-restore-<stamp>'` on every applied **or attempted** restore; nothing pruned them. The "silently aborts" half was already closed by CHG-007 (the failure is now recorded and surfaced). |
| APR-01 | The guard **is present and explicit**: `service._action` raises `PolicyError('Actor identity comes from the authenticated Kel session, not from the request payload')` for a payload `actor`, on the generic path *and* again on `/api/approval`. The docket's requested remedy was a **test** — that was genuinely missing. |
| APR-02 | Still open: `/api/approval` resolves by `data['id']` alone (`self.store.resolve_approval(id, action, allow)`), while the *read* path is conversation-scoped (`chat_approvals._job_ids_for`). |
| APR-03 | Unchanged (`vetting_session.py` instance queue); Phase 6 already recorded it as a bounded crash-window only. |
| SEC-01 | Still open: `Vetting.session(session_id)` loads `WHERE id=?` with no project/conversation check, and the action methods take only the session id. |
| TR-02 | Not re-reviewed in this increment (renderer UX; needs a visual pass). |

## Implementation Summary

1. **PER-03 fixed** (`kel/backup.py`): `SNAPSHOT_KEEP = 2` and `_prune_snapshots(root)` keep only the
   newest snapshots — called on the success path *and* the failure path, so repeated failed attempts
   cannot accumulate either. Only directories matching the exact `<root>.pre-restore-` prefix are
   touched, the newest ones always survive (including the one the current attempt wrote), and pruning
   is best-effort so it can never fail a restore.
2. **APR-01 pinned** (`tests/test_v16_sweep_fixes.py`): two tests assert the payload-actor guard on
   `/api/approval` and on other action families. The finding's own remedy was the test, not the guard.
3. **APR-02, SEC-01 recorded OPEN with the exact code evidence and a fix sketch** — deliberately not
   marked fixed: both need an ownership/scope decision that touches API signatures, and the
   desktop payload contract must be checked first.
4. **APR-03** → `DEFERRED_NON_RELEASE` (bounded crash window; the durable-drain direction is a
   feature, not a release condition).

## Files Changed

- `runtime/kel/backup.py` (`SNAPSHOT_KEEP`, `_prune_snapshots`, both call sites)
- `runtime/tests/test_v16_sweep_fixes.py` (+5 tests: 2 snapshot retention, 3 actor-guard/action-family)

## Symbols Changed

`backup.SNAPSHOT_KEEP`, `backup._prune_snapshots`, `apply_pending_restore` (prunes on both paths).

## Schema/Migrations

None.

## User-Facing Behavior

Indirect: repeated restores no longer leave an unbounded pile of `.pre-restore-*` copies beside the
data (each one is a full copy of the replaced content).

## Internal Behavior

Pruning runs after the merge (success) or after the failure is captured; the snapshot a user would
want for a failed restore is always the newest one and is kept.

## Error Paths

Pruning swallows its own errors by design; a prune failure cannot turn a good restore into a failure.

## Lifecycle Considerations

Retention is 2 snapshots. Recorded as a product-visible default in the row (a user who wants more can
copy them out; there is no setting today).

## Persistence / Isolation

Fewer files beside the data root; nothing inside the data root changes.

## Security / Privacy

None. (Fixing SEC-01 is what would be security work, and it is explicitly *not* claimed here.)

## Self-Review Findings

- The first version of the failed-restore test used `backup._restore_entry` without importing the
  module object → `NameError`; fixed by importing `kel.backup as backup`. Test bug, not product.
- Checked that pruning cannot delete the snapshot a *failed* restore needs: the current attempt's
  directory is always the newest (timestamped), so `keep=2` preserves it plus the previous one.

## Tests Run

- `cd runtime && python -m pytest tests/test_v16_sweep_fixes.py tests/test_backup.py
  tests/test_transcription.py -q` → **45 passed** (5 new).
- Full engine suite: see TEST_EVIDENCE_INDEX A-18.

## Results

PASS (PER-03 fixed; APR-01 pinned; three rows verified-open with evidence).

## Packaged Verification

Not applicable to this increment (engine-internal retention); the RC packaged battery re-runs the
engine suite.

## Known Weaknesses

- APR-02 and SEC-01 stay OPEN; the sweep must close them with a real fix (both need the API-signature
  and desktop-payload decision), and TR-02 needs a renderer review.
- Snapshot retention (2) is a hard-coded default with no setting.

## Deferred Questions

- Should the retained snapshot count be configurable, and should a failed restore prevent the app's
  write surfaces until acknowledged? (Ties into REQ-ELOSS.)

## Audit Targets

AUDIT_TARGETS § 60.

## Repair Hints

`_prune_snapshots` is the single place for retention; the scope fixes for APR-02/SEC-01 should add an
ownership parameter to the session/approval lookups rather than re-checking in each route.

## Evidence Paths

- `docs/v1.6/pre-audit/increments/P2P3-BATCH3-SNAPSHOTS-SCOPE.md` (this file)
- corpus rows: P2_P3_DISPOSITION (PER-03, APR-01, APR-02, APR-03, SEC-01, TR-02), CHANGE_LEDGER
  CHG-010, TEST_EVIDENCE_INDEX A-18
