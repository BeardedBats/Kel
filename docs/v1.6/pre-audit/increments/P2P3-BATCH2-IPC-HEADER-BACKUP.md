# Increment — P2/P3 sweep batch 2: IPC frame guard, multipart header hygiene, credentials excluded from backups

increment_id: V16-SWEEP-BATCH2
phase: Campaign A — P2/P3 sweep (audit docket) · INT-01, SEC-01-multipart, PER-04 (+ DEAD-05, TR-01 dispositions)
base_commit: cbd0430 (PER-02 docs)
target_commit: `0596211` (implementation) + this docs commit
status: complete

## Objective

Continue the sweep with the three findings the current tree still proves live and that are small
enough to fix correctly now, and record honest dispositions for two more.

## Requirement Sources

- `INT-01` — `11_FINDINGS.md`, `16_FINDING_STATUS.md` (P3): "Inconsistent sender-frame validation
  (`kel:artifact-reveal` lacks the check)".
- `SEC-01-multipart` — `11_FINDINGS.md` (P3): caller-supplied filename interpolated into a multipart
  header unescaped (transcription).
- `PER-04` — `16_FINDING_STATUS.md` (P3): `KEL_DATA_DIR` puts `kel-credentials.json` inside the
  backup root (override path only).
- `DEAD-05`, `TR-01` — `16_FINDING_STATUS.md`, `02_FILE_REVIEW_LEDGER.md` (P3): recorded here with
  the verification result; TR-01 stays OPEN because the finding's own claim ("shutdown/cleanup not
  reviewed") has not been discharged.

## Implementation Summary

1. **INT-01 (desktop main)** — `kel:artifact-reveal` was the only privileged IPC handler without the
   sender-frame guard used by its four siblings (`kel:request`, the credential handlers, the
   project/backup handlers). It now checks `event.senderFrame === event.sender.mainFrame` and a
   `file:` URL before touching the OS; the path-containment check it already had is unchanged.
2. **SEC-01-multipart (engine)** — `_multipart` interpolated the caller's filename raw into
   `Content-Disposition`. A new `_header_safe` folds CR/LF to spaces, quotes to apostrophes and
   backslashes to slashes, so a crafted filename can no longer end the header early or start a part
   of its own.
3. **PER-04 (engine)** — a backup now never captures the credentials sidecar: `NEVER_BACKUP =
   ('kel-credentials.json',)` is skipped in `Backup.create` and reported in the backup's `skipped`
   list and notes (the existing notes already promise credentials are excluded, and secrets inside
   the database were already stripped — this closes the sidecar gap the override creates).

## Files Changed

- `desktop/packages/desktop/src/process/services/kel/KelService.ts` (frame guard)
- `runtime/kel/transcription.py` (`_header_safe` + `_multipart`)
- `runtime/kel/backup.py` (`NEVER_BACKUP` + skip/report)
- `runtime/tests/test_v16_sweep_fixes.py` (new, 5 tests)

## Symbols Changed

`_header_safe`, `_multipart`, `backup.NEVER_BACKUP`, `Backup.create`, the `kel:artifact-reveal`
handler.

## Schema/Migrations

None.

## User-Facing Behavior

No intended change. A crafted upload filename no longer shapes the request headers, a backup no
longer contains the credentials sidecar, and the IPC surface is uniform.

## Internal Behavior

`_multipart` output is byte-identical for ordinary names (a clean filename round-trips — tested).
Backups add the credentials file to `skipped`/`notes` and omit it from the folder.

## Error Paths

Unchanged: a rejected IPC call throws `Unknown Kel window` exactly like its siblings.

## Lifecycle Considerations

None.

## Persistence / Isolation

Backup contents change (one fewer file) and its manifest reports it.

## Security / Privacy

Three hardening changes, all fail-closed: fewer privileged callers, no header injection, no
credential capture in a backup.

## Self-Review Findings

- The first multipart test asserted `count('Content-Disposition:') == 1`, which failed because the
  sanitised text legitimately survives *inline* in the filename parameter. The corrected test
  asserts what actually matters: the injected text cannot start a header **line** (lines starting
  with `Content-Disposition:` == 1) and the part count is unchanged. Recorded because the first
  version was wrong, not the product.
- The IPC frame guard has no automated test: this repository has no IPC/Electron harness, and
  inventing one for a five-line parity fix would be a bigger change than the fix. Verification is
  `tsc` 0 plus byte-level parity with the four sibling guards; recorded in AUDIT_TARGETS §58 so an
  auditor can challenge it.

## Tests Run

- `cd runtime && python -m pytest tests/test_v16_sweep_fixes.py tests/test_backup.py
  tests/test_transcription.py -q` → **41 passed** (5 new).
- `cd desktop && bunx tsc --noEmit` → 0 errors.
- Full engine suite: see TEST_EVIDENCE_INDEX A-16.

## Results

PASS.

## Packaged Verification

Not applicable to this increment (engine + main-process hardening); the RC packaged battery re-runs
the engine suite and the desktop typecheck.

## Known Weaknesses

- The IPC guard is verified by typecheck and parity, not by an automated test (no harness exists).
- TR-01 (`_STREAMS` module-level stream sessions) remains OPEN: the code is still module-level
  (`transcription.py:36`, `:528`) and the lifecycle review the finding asks for has not been done.

## Deferred Questions

- DEAD-05 (`service.py` calling `Vetting` privates) — deferred as cosmetic coupling; a public wrapper
  is possible but is not release-relevant.

## Audit Targets

AUDIT_TARGETS § 58.

## Repair Hints

`_header_safe` is the single place to extend if the multipart builder ever gains more parameters;
`NEVER_BACKUP` is the single place for files that must never travel in a backup.

## Evidence Paths

- `docs/v1.6/pre-audit/increments/P2P3-BATCH2-IPC-HEADER-BACKUP.md` (this file)
- corpus rows: P2_P3_DISPOSITION (INT-01, SEC-01-multipart, PER-04, DEAD-05, TR-01), CHANGE_LEDGER
  CHG-008, TEST_EVIDENCE_INDEX A-16
