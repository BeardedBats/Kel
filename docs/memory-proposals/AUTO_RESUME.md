# Memory proposals — auto-resume

Workstream: the memory proposal surface (release program Phase 1). Status at this writing:
implemented, engine-verified, packaged journey verified, docs written; the commit and the
post-implementation independent review are the remaining steps.

## Exact state to resume from

- Branch `ux/v15-journeys`; pre-program checkpoint frozen first (`v1.6.0-pre1`,
  `Kel-V1.6.0-Pre1-Frozen`, artifact source `0fb095f`). Nothing in this workstream mutates that
  freeze.
- Candidate for this workstream: `dist/package-final13/win-unpacked` (+ installer). `package-final12`
  is a superseded intermediate (contained a UI response-shape bug found by the packaged journey);
  never cite it as evidence.
- Evidence: `ux-audit/runs/mp/out/` (`ux-memoryprops.json`, `ux-memoryprops-db.json`,
  `ux-sweep-seed.json`, screenshots); engine `runtime/tests/test_v16_proposals.py`.
- Docs: this folder 00–07.

## Verify quickly

1. `cd runtime && python -m pytest tests -q` → 568 passed (+10 subtests).
2. `cd desktop && bunx tsc --noEmit` → 0; `bun run test` → 76.
3. `bash ux-audit/run-memoryprops.sh` → scenario all-true + `passed: true` probe (needs final13;
   edit `APPW` in the script if a newer package exists).

## Known sharp edges

- The chat header pills (model/tools/review) render on `#/conversation/<id>` pages; the `#/guid`
  live-chat surface shows none of them. The packaged scenario therefore opens the created
  conversation before asserting the pill.
- `/api/memory` `proposals` returns `{proposals: [...]}` (object), not a bare array — the UI bug fixed
  in final13 was exactly this.
- Proposal creation in the product flows through triggers (vetting flush, record() conflicts,
  revalidate()); there is no generic HTTP "create proposal" action by design.

## Next increments (in order)

1. Phase 2 of the release program: artifact lineage (`docs/product` + engine artifacts table).
2. Phase 6 (richer memory UX) revisits the knowledge surface; the queue + history built here are its
   foundation.
3. If semantic (near-match) proposal detection is wanted later, it needs a model-backed matcher and a
   new evidence signature design; do not stretch the exact-topic convention.
