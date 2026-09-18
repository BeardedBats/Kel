# Increment — PER-02: a failed or partial restore is recorded and surfaced, never silent

increment_id: V16-PER02-RESTORE-VISIBILITY
phase: Campaign A — P2/P3 sweep (audit docket) · PER-02
base_commit: c1bb980 (P2/P3 first batch docs)
target_commit: the implementation commit + this docs commit
status: complete (engine half; renderer surfacing linked to REQ-ELOSS)

## Objective

Close the P2 finding recorded in `docs/code-audit/03_CORRECTNESS.md:48-54` and
`05_PERSISTENCE_AND_MIGRATIONS.md:66`: `service.py` wrapped `apply_pending_restore(self.store)` in
`try/except Exception: pass` and discarded the boolean, so a restore that could not start, or that
failed halfway, left no trace anyone could see (a Rust-corroborated finding).

## Requirement Sources

- `03_CORRECTNESS.md:48-54` — "`service.py` wraps `apply_pending_restore(self.store)` in
  `try/except Exception: pass` and discards the boolean… See `PER-02`."
- `05_PERSISTENCE_AND_MIGRATIONS.md:66-71` — "**`PER-02` (P2):** failure is silent" (+ PER-03's
  snapshot-abort case sharing the path).
- `pre-audit/P2_P3_DISPOSITION.md` — PER-02 row (P2).

## Implementation Summary

1. **Durable, database-independent record** (`kel/backup.py`): `OUTCOME = 'restore-outcome.json'`
   and `_record_outcome(root, ok, detail)` write `{ok, detail, at}` **beside the data** — the record
   cannot live in the database, because the database is what a restore replaces. Recording never
   raises, so a failed restore still returns its verdict.
2. **Both decisive paths recorded**: success writes `ok=True`; the failure path now catches
   `Exception as exc`, records `ok=False, detail=<exception type>`, and returns `False` with the
   pending marker still in place (a half-applied restore must stay pending).
3. **Boot safety + surfacing** (`kel/service.py`): the caller records a failure itself when the
   restore cannot even start (never aborting boot), and `Service.state()` now carries
   `restore: {ok, detail, at} | null` alongside `connected`/`engine_version`, so the app can say
   what happened. Payload change is additive; no client breaks.

## Files Changed

- `runtime/kel/backup.py` (`OUTCOME`, `_record_outcome`, both restore paths)
- `runtime/kel/service.py` (`_restore_outcome`, caller-side recording, `state()['restore']`)
- `runtime/tests/test_v16_restore_visibility.py` (new, 5 tests)

## Symbols Changed

`backup.OUTCOME`, `backup._record_outcome`, `backup.apply_pending_restore` (outcome recording),
`service._restore_outcome`, `Service.__init__`, `Service.state`.

## Schema/Migrations

None.

## User-Facing Behavior

Indirect: the engine now reports a restore failure instead of losing it. The renderer banner that
would show it belongs to **REQ-ELOSS** (engine-loss/recovery UX) and is recorded as audit target 57 —
this increment deliberately does not invent a UI surface.

## Internal Behavior

`state()['restore']` is `null` when no restore was ever attempted, `{ok: true, …}` after a clean
apply, and `{ok: false, detail: '<ExceptionType>'}` after a failure.

## Error Paths

A failing `apply_pending_restore` still returns `False` (contract unchanged for existing callers and
tests) and still leaves `restore-pending.json` in place.

## Lifecycle Considerations

The sidecar is written before/after the restore attempt and is not part of a backup
(`SKIP_ENTRIES` covers the staging dir and the marker; the outcome file is a plain sidecar like
`BACKUP-INFO.json`).

## Persistence / Isolation

One new sidecar file inside the data root.

## Security / Privacy

None: the detail is an exception *type name*, never a message body (no paths, no content).

## Self-Review Findings

- The first test run failed for a self-inflicted reason worth recording: a helper named `_outcome`
  collided with `unittest.TestCase._outcome`, so the test file now uses `_recorded_outcome` with a
  comment. No product defect behind it.
- `False` from `apply_pending_restore` means both "nothing pending" and "failed"; rather than change
  the return type (and break callers), the *outcome file* disambiguates, and "nothing pending"
  records nothing at all — which is exactly what `state()['restore'] is None` means.

## Tests Run

- `cd runtime && python -m pytest tests/test_v16_restore_visibility.py tests/test_backup.py -q`
  → **14 passed** (5 new + 9 existing backup tests).
- Full engine suite: see TEST_EVIDENCE_INDEX A-15.

## Results

PASS (engine half).

## Packaged Verification

Not applicable (engine-side behaviour; the RC packaged battery re-runs the engine suite and can
assert `state()['restore']` on a staged restore).

## Known Weaknesses

- The renderer does not yet display the outcome (queued with REQ-ELOSS; audit target 57).
- PER-03 (unbounded `.pre-restore-*` snapshots; snapshot failure aborting a restore silently) shares
  this path and stays open in the sweep.

## Deferred Questions

- Should a failed restore block the app's *write* surfaces until acknowledged? (Product decision;
  recorded for the sweep/REQ-ELOSS.)

## Audit Targets

AUDIT_TARGETS § 57.

## Repair Hints

Recording lives in `kel/backup.py`; surfacing in `kel/service.py:state()`. A renderer banner should
read the existing `/api/state` payload, not add a new endpoint.

## Evidence Paths

- `docs/v1.6/pre-audit/increments/PER-02-RESTORE-VISIBILITY.md` (this file)
- corpus rows: P2_P3_DISPOSITION (PER-02), CHANGE_LEDGER CHG-007, TEST_EVIDENCE_INDEX A-15
