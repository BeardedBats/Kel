# REPAIR_RESUME — Kel V1.6 human visual repair

Resume point for this campaign. Final state recorded; update only if new work lands.

## Where things are

- Repair worktree: `C:\Users\Nick\Desktop\Kel\kel-v16-human-visual-fix` (branch `repair/v16-human-visual`)
- Production source head: `6d957ee9aad7200fb2fcff9b505e0771e2dfdcda` (`HUMAN_VISUAL_REPAIR_HEAD`)
- Durable state: `docs/v1.6/human-visual-repair/` (this directory; evidence under `evidence/`)
- Review install: `C:\Users\Nick\KelVisualFixInstall` (registered; engine `f525b15b…`)
- Review data root: `C:\Users\Nick\KelVisualFixRuns\prepared` (fresh-seeded; appdata + kelwork)
- Launcher for Nick: `C:\Users\Nick\KelVisualFixRuns\Launch Kel V1.6 Visual Fix Review.cmd`
- Preserved (untouched): `audit/v16-postrepair-final`, `repair/v16-final`, `ux/v15-journeys`, `main`,
  `C:\Users\Nick\KelV16ReviewInstall` (audit build restored; engine `df4f0ee9…`),
  `C:\Users\Nick\KelV16ReviewRuns\`

## Status

- Source repair: complete (HV-01…HV-13 fixed; HV-14 polish applied)
- Regression: desktop tsc + full vitest + focused suites PASS; installer smokes PASS; engine unaffected
- Visual battery: source matrix + installed battery + audit R12 battery all PASS (see 03/04)
- Package: `Kel-1.6.0-win-x64.exe` built from the repair head (see 05 for the exact hash)
- `HUMAN_VISUAL_GATE = PENDING_REVIEW` — Nick owns the final visual approval; release NOT started

## If more work is needed

1. Make changes in `kel-v16-human-visual-fix`; run `cd desktop && bunx tsc --noEmit && bun run test`.
2. Rebuild: `cd desktop && node scripts/build-with-builder.js auto --win` (engine stays staged at
   `../dist/runtime/KelEngine`, sha `f525b15b…` — do not substitute).
3. Reinstall: stop all Kel processes first; the registered install updates in place at `KelVisualFixInstall`.
   (A manual `/D=` is ignored while a previous install is registered; clear
   `HKCU\Software\9280710d-02b9-55d6-ba7a-2b7d6f91d60a` + the matching Uninstall key first for a fresh path.)
4. Re-verify: `ux-audit/kelvis-verify.cjs <appDir> <rootDir> <outDir>` + `ux-audit/r12-installed-probe.cjs`.
5. Update 03/04/05 + `HUMAN_VISUAL_REPAIR_CANDIDATE.md`, then commit.

## Constraints (unchanged)

No release/freeze/main-merge/tag/publish. No weakening of authorization, isolation, memory, recovery, routing,
Workforce execution, migrations, package identity. `HUMAN_VISUAL_GATE` stays PENDING_REVIEW until Nick inspects.
