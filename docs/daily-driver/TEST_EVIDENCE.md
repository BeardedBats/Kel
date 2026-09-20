# TEST EVIDENCE — `dev/daily-driver`

## Commands used (fill in the exact invocation when first run)

- Desktop unit (vitest): `cd desktop && bunx vitest run`
- Desktop focused: `cd desktop && bunx vitest run <files>`
- Desktop typecheck: `cd desktop && bunx tsc --noEmit` (confirm exact flags on first run)
- Engine (python unittest): `cd runtime && python -m unittest discover -s tests`

## Baseline (source: final re-audit of the V1.6 repair, `audit/v16-human-visual-final`)

- Desktop tsc PASS; Vitest 15 files / 156 PASS; focused (donor-policy + needs-attention) 17 PASS.
- Installed battery 25/25; engine probe healthy; 0 console/page errors.
- These are the audit's numbers for `6d957ee9…`, recorded here only as the starting baseline.

## Runs (this lane)

| When | Scope | Command | Result | Notes |
| --- | --- | --- | --- | --- |
| — | lane open | (no runs yet) | — | deps installed (`bun install`, 1591 packages, 36.6s) |
