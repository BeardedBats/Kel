# Increment — REQ-RK (record-bound resolution kinds) + additive workforce migration v17

increment_id: V16-RK-RESOLUTION-KIND
phase: Campaign A — assurance learning-loop semantics (audit carry-forward F18-5 / WF-13)
base_commit: 1894ef7 (canonical-logo docs)
target_commit: `a547936` (implementation) + this docs commit
status: complete

## Objective

Close the audit carry-forward that said `_is_acceptance` "is prefix-based, not record-bound":
record *how* a finding was resolved as data, so the learning loop and any review surface reads a
recorded kind instead of parsing free-text reasons.

## Requirement Sources

- Audit finding **F18-5** (N18-5): "`_is_acceptance` is prefix-based, not record-bound | info |
  carried forward (needs a resolution-kind column)" — `docs/v1.6/phase5/5.4_IMPLEMENTATION_RECORD.md`.
- `REQ-RK` row (`pre-audit/REQUIREMENTS_TRACEABILITY.md`), `CHANGE_LEDGER` mapping row
  "resolution-kind semantics".
- `AUDIT_SCOPE.md` WF-13: "Evidence-bound review rows + resolution-kind (F17-4/F18-5)".

## Implementation Summary

1. **Vocabulary** (`kel/assurance.py`): `RESOLUTION_KINDS = ('fixed', 'risk-accepted',
   'gate-waived', 'false-positive')` and `ACCEPTANCE_KINDS = ('risk-accepted', 'gate-waived')`.
2. **Schema** (`kel/workforce.py`): additive `findings.resolution_kind TEXT`; migration
   bumped to **v17** (`v17-finding-resolution-kind`); `ensure_schema` adds the column in place for
   databases created before it (PRAGMA-guarded, no row rewritten) and records the migration once.
3. **Writers**: `resolve_finding` writes `fixed` / `risk-accepted` / `false-positive` alongside the
   human-readable reason; `waive_gate` writes `gate-waived`. The guarded reason markers stay (they
   are the F17-2 anti-impersonation guarantee), but they are no longer the authority.
4. **Reader**: `lens_stats` counts by the record field; a NULL kind (pre-v17 row) is derived once
   from the guarded marker. Free text is never parsed for new rows.
5. **Validation**: `validate_finding` accepts and validates `resolution_kind` when present
   (`FINDING_FIELDS` extended); an unknown kind is refused.

## Files Changed

- `runtime/kel/assurance.py` (vocabulary, validation, both writers, `lens_stats`, docstrings)
- `runtime/kel/workforce.py` (DDL column, v17 migration, additive ALTER)
- `runtime/tests/test_v16_resolution_kind.py` (new, 6 tests)
- `runtime/tests/test_workforce_schemas.py` (migration-name assertion moved to v17)

## Symbols Changed

`RESOLUTION_KINDS`, `ACCEPTANCE_KINDS`, `FINDING_FIELDS`, `validate_finding`, `resolve_finding`,
`waive_gate`, `_is_acceptance` (legacy-only), `lens_stats`, `workforce.ensure_schema`,
`workforce.MIGRATION_VERSION/MIGRATION_NAME`.

## Schema/Migrations

Additive: `findings.resolution_kind` + migration v17. Existing rows keep NULL and are derived once;
no data is rewritten, no contract changes. The desktop HTTP/SSE surface is untouched (the engine
payload gains one optional field on finding rows if a client reads the row directly).

## User-Facing Behavior

None directly (learning-loop semantics). A finding's resolution is now auditable as data.

## Internal Behavior

`lens_stats` no longer infers acceptance from a string prefix:
a hand-written `dismissal_reason` cannot impersonate an acceptance when the record says otherwise
(test `test_the_column_wins_over_the_reason_text`).

## Error Paths

Unknown `resolution_kind` → `PolicyError`. Pre-v17 rows → derived, never an error.

## Lifecycle Considerations

Migration is idempotent across reopens (test) and additive for existing stores.

## Persistence / Isolation

Same store; no new files, no new paths.

## Security / Privacy

None. The F17-2 guarantee (a caller-supplied rationale cannot impersonate an acceptance) is
preserved and now backed by the record.

## Self-Review Findings

- The prefix test was load-bearing for a real statistic (`fp_rate`), so the change had to keep the
  legacy rows' meaning while making new rows record-bound — hence the explicit one-time derivation
  path instead of a silent behavior change.
- Adding a column to a table with append-only *sibling* tables required no trigger changes
  (`findings` is mutable by design; only its guarded paths write statuses).

## Tests Run

- `cd runtime && python -m pytest tests/test_v16_resolution_kind.py -q` → **6 passed**.
- `cd runtime && python -m pytest tests/test_v16_resolution_kind.py tests/test_workforce_assurance.py
  tests/test_workforce_schemas.py tests/test_workforce_d2.py -q` → **136 passed**.
- Full engine suite: see TEST_EVIDENCE_INDEX A-13.

## Results

PASS (engine). No desktop change was required: no desktop code consumes `dismissal_reason` or
`lens_stats` (verified by grep).

## Packaged Verification

Not applicable to this increment (engine-internal semantics; the RC packaged battery re-runs the
engine suite on the packaged runtime).

## Known Weaknesses

- The reason prefixes remain in the stored text (kept deliberately for the F17-2 guarantee and for
  human readability); a reader that *wanted* to could still parse them — the point is that nothing
  has to.
- `lens_stats` exposes `accepted`/`false_positive` but not yet a per-kind breakdown; a review surface
  that wants kinds can read `findings()['resolution_kind']` directly.

## Deferred Questions

- F4 real-artifact binding wiring (the paired carry-forward) — next increment.
- Whether the desktop assurance UI should display the kind (no surface reads it today).

## Audit Targets

AUDIT_TARGETS § 53–54.

## Repair Hints

Vocabulary lives in `kel/assurance.py`; adding a kind means extending `RESOLUTION_KINDS`, the
writers, and the migration note.

## Evidence Paths

- `docs/v1.6/pre-audit/increments/REQ-RK-RESOLUTION-KIND.md` (this file)
- corpus rows: REQUIREMENTS_TRACEABILITY REQ-RK, CHANGE_LEDGER CHG-005, TEST_EVIDENCE_INDEX A-13,
  COMMIT_LEDGER
