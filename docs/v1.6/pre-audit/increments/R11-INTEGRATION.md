# R11 — Visual → Main integration record (2026-09-18)

Directive §12. This is the semantic integration of the visual lane into Main.

## Before mutation (recorded facts)

- Main worktree `kel-ux-v15`, branch `ux/v15-journeys` — clean; tip **`93b7074`**.
- Visual worktree `kel-v16-visual-fix`, branch `ux/v16-visual-fix` — clean; tip **`bc92f7f`**
  (code tip `fa66f04`).
- Merge base of the two branches: **`05608e6`** (the R9 re-anchor point).
- Main-only changes since the base (3 files, docs only): `docs/v1.6/MARATHON_STATE.md`,
  `docs/v1.6/status/MAIN_STATUS.md`, `docs/v1.6/pre-audit/AUDIT_TARGETS.md`.
- Visual-only changes since the base (55 files): `desktop/**` (batches 1–8, R9.D, supervision +
  follow-ups, tests) and `docs/v1.6-visual-ux/**` (plan set + `17–19` records).
- **Overlapping files: NONE.** No conflict resolutions were required; per §12, no branch was
  preferred by age — the merge is a pure union of behavior.
- No competing writer (single Program Director; Main quiescent during R9/R10).

## Mutation

- `git merge ux/v16-visual-fix --no-ff` in the Main worktree → merge commit **`7267630`**
  ("merge(v1.6): R11 — integrate the visual lane into Main"). Conflict count: 0.

## After mutation (verification)

- `bunx tsc --noEmit` → **0 errors** (Main worktree).
- `bun run test` → **122 passed / 122** (12 files).
- Engine suite: not re-run here (no engine/runtime file changed by this merge); the R12 battery
  re-runs the full engine suite + the packaged battery on the post-merge build.
- Preserved by construction: all Campaign A runtime/API behavior (Main side untouched by the
  lane), and all accepted visual behavior (lane deltas merged verbatim; batches 1–5 files were
  proven byte-identical at the re-anchor and are untouched since).
- No force updates; lineage preserved (the lane's original SHAs remain reachable; recorded in
  `COMMIT_LEDGER.md`).

## Durable records updated with this record

`COMMIT_LEDGER.md` (integration rows), `CHANGE_LEDGER.md` (CHG-024…028 + mapping),
`REQUIREMENTS_TRACEABILITY.md` (REQ-R25-R10 / REQ-VIS-6..8 / REQ-ELOSS),
`VISUAL_EVIDENCE_INDEX.md` (integration status), `MAIN_STATUS.md` / `MARATHON_STATE.md`
(breadcrumbs), and the visual authority `VISUAL_STATUS.md` (`integrated_main_head: 7267630`).

## Carried into R12

- Full engine suite + desktop suite on the merged tree.
- Packaged/installed battery rebuilt **from the merged Main** (fresh package incl. installer
  path), failure injection, release integrity, and the pre-audit corpus finalization.
