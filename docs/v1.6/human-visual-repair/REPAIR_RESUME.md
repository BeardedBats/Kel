# REPAIR_RESUME — Kel V1.6 human visual repair

Resume point for this campaign. Update after every completed cluster.

## Where things are

- Repair worktree: `C:\Users\Nick\Desktop\Kel\kel-v16-human-visual-fix` (branch `repair/v16-human-visual`, base `eb4da52`)
- Durable state: `docs/v1.6/human-visual-repair/` (this directory)
- Preserved (do NOT touch): `audit/v16-postrepair-final`, `repair/v16-final`, `ux/v15-journeys`, `main`,
  `C:\Users\Nick\KelV16ReviewInstall`, `C:\Users\Nick\KelV16ReviewRuns\`

## Current state

- Findings + root causes: see `01_HUMAN_FINDINGS.md`
- Next actions:
  1. Implement fix clusters (starting: Permissions scroll owner; contrast theme boundary; Work→chat target)
  2. Run desktop typecheck + vitest; engine check per `04_REGRESSION.md`
  3. Screenshot matrix per `03_VISUAL_EVIDENCE.md`
  4. Package + review install per `05_PACKAGE_EVIDENCE.md`

## Key commands

- Typecheck: `cd desktop/packages/desktop && bunx tsc --noEmit`
- Tests: `cd desktop && bun run test`
- Build/package: `cd desktop && node scripts/build-with-builder.js auto --win`
- Git: commit per cluster with `fix(v1.6-visual): …`

## Constraints (unchanged)

No release/freeze/main-merge/tag/publish. No weakening of authorization, isolation, memory, recovery,
routing, Workforce execution, migrations, package identity. HUMAN_VISUAL_GATE stays PENDING_REVIEW.
