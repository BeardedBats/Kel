# Increment — A1 / ENG-01: detached-engine reuse validates `engine_version`

increment_id: V16-A1-ENGINE-VERSION
phase: Campaign A — P2/P3 sweep (audit docket) · A1 / ENG-01 (P2)
base_commit: a3e272d (sweep batch 2 docs)
target_commit: `101d8c3` (implementation) + this docs commit
status: complete

## Objective

Close the P2 finding recorded in the audit's final verdict: the desktop reused whatever engine
answered `/api/state`, without comparing `engine_version`, so an upgrade could leave the new build
talking to the previous version's engine.

## Requirement Sources

- `docs/code-audit/12_FINAL_VERDICT.md:101` — "`ENG-01` | P2 | Detached-engine reuse does not validate
  `engine_version` (A1) | NEW, verified".
- `docs/code-audit/15_RUST_LEAD_VERIFICATION.md` — the source of the A1 row in
  `pre-audit/P2_P3_DISPOSITION.md`.
- `desktop/kel-builder.json` — declares the bundled engine (`../dist/runtime/KelEngine` →
  `kel-engine`), i.e. an upgrade replaces the engine the app loads.

## Implementation Summary

1. **The decision, as data** (`process/services/kel/engineVersion.ts`): `engineVersionAccepted(live,
   expected)` — exact match required (trimmed); a missing/non-string live version refuses; an empty
   `expected` means the caller cannot know the build's engine version and is **not enforced**
   (documented escape for unpackaged dev runs, where `app.getVersion()` reports Electron's own
   version).
2. **Both trust sites** (`KelService.ts:initializeKel`): the check now guards the reuse path (a
   descriptor whose engine does not match is no longer "a live engine") **and** the spawn-wait loop —
   a leftover engine can keep rewriting the shared `desktop-session.json`, so the loop keeps waiting
   for the engine this build expects instead of connecting to whatever answers first.
3. **No port risk:** each engine picks its own port, so refusing a stale engine cannot strand the app
   without an engine.

## Files Changed

- `desktop/packages/desktop/src/process/services/kel/engineVersion.ts` (new)
- `desktop/packages/desktop/src/process/services/kel/KelService.ts`
- `desktop/tests/unit/kelEngineVersion.test.ts` (new)

## Symbols Changed

`engineVersionAccepted` (new), `initializeKel` (reuse path + spawn-wait loop).

## Schema/Migrations

None.

## User-Facing Behavior

Indirect: after an upgrade the app spawns its own engine instead of reusing a stale one.

## Internal Behavior

`expectedEngineVersion = process.env.KEL_ENGINE_VERSION || (app.isPackaged ? app.getVersion() : '')`.

## Error Paths

A stale engine is treated exactly like "no live engine": the app spawns. If the expected engine
never answers within 45 s it still throws `Kel engine did not start. See desktop.log.`.

## Lifecycle Considerations

The drain hook is unchanged: it addresses `descriptor`, which the spawn path overwrites.

## Persistence / Isolation

None (the descriptor file's format is untouched).

## Security / Privacy

None.

## Self-Review Findings

- The first design compared only the descriptor's own claim (written by the engine itself), which
  would have been circular; the check compares the **live** `/api/state` version against the version
  the *build* expects. Recorded because the naive version would have looked like a fix and proved
  nothing.
- Enforcing in dev would have broken every unpackaged start (`app.getVersion()` is Electron's), so
  the empty-expected escape is explicit and tested rather than implied.

## Tests Run

- `cd desktop && bunx tsc --noEmit` → 0 errors.
- `cd desktop && bun run test` → **93 passed / 8 files** (was 90; +3 new).
- Engine suite untouched by this change (no engine files modified).

## Results

PASS.

## Packaged Verification

Not applicable here (startup behaviour); the RC packaged battery starts the packaged app, which
exercises the reuse path against the real `resources/kel-engine`.

## Known Weaknesses

- The end-to-end spawn fallback has no automated test: this repository has no Electron/IPC harness,
  so the decision is unit-tested and the wiring is typecheck-verified (audit target §59).
- **REL-01 remains `OPEN_RELEASE_BLOCKER`** (freeze staging is a no-op for the load path): it is the
  same subsystem (which engine a build actually ships) but its only honest verification is a real
  freeze, which Campaign A is forbidden to perform. The fix plan is recorded in the row; the
  decision belongs to the RC gate/human.

## Deferred Questions

- Should a mismatched engine be asked to shut down (instead of idling out) when the app spawns a
  replacement? Recorded for the RC gate; behaviour today is unchanged.

## Audit Targets

AUDIT_TARGETS § 59.

## Repair Hints

`engineVersionAccepted` is the single decision point; both call sites of `expectedEngineAnswered()`
must stay in sync if a third trust site is ever added.

## Evidence Paths

- `docs/v1.6/pre-audit/increments/A1-ENGINE-VERSION-BINDING.md` (this file)
- corpus rows: P2_P3_DISPOSITION (A1 fixed; REL-01 blocker), CHANGE_LEDGER CHG-009,
  TEST_EVIDENCE_INDEX A-17, COMMIT_LEDGER
