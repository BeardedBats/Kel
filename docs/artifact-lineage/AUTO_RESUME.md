# Artifact lineage — auto-resume

Workstream: artifact lineage (release program Phase 2). Status: engine + desktop implemented and
tested; packaged probe runs on `dist/package-final15`; commit + independent review pending.

## Verify quickly

1. `cd runtime && python -m pytest tests -q` → 574 passed (+10 subtests).
2. `cd desktop && bunx tsc --noEmit` → 0.
3. `bash ux-audit/run-lineage-probe.sh` → probe JSON in `ux-audit/runs/lin/out/`.

## Sharp edges

- `artifact_lineage` is created by core's schema init (unversioned, like `runs`/`inbox`): older user
  stores pick it up automatically on the next engine open. Do NOT give it a `schema_migrations`
  version — the v13/v14 upgrade tests pin those lists.
- The lineage write happens inside `consume()`'s transaction and must stay there (atomic with the
  artifact write; a crash can't leave provenance pointing at a missing file).
- The whitelist in `KelService.ts` governs which kelAPI routes the renderer may call:
  `lineage?job=…[&milestone=…]` and `artifact?lineage=…` were added; keep it that tight.
- Probe seeding drives engine internals (claim/enqueue/consume/verify) — that is the same path the
  tests use; if milestone states change, update `seed-lineage.py` (checks: the first draft must
  FAIL its check, or there is only one version).

## Next increments

1. "Open source conversation" action: needs an engine-conversation → desktop-route resolver in the
   main process; add when the artifact surface graduates out of the Work panel.
2. Non-text artifact types (when the engine produces them): extend `media_type` + preview.
