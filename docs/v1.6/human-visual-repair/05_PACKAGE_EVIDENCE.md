# 05 — PACKAGE EVIDENCE (Kel V1.6 human visual repair)

Built only after source repairs + regression are green. Fresh build; no reuse of old renderer output.

## Stale-artifact guards

- [ ] `desktop/dist` (Vite/electron-vite output) cleaned before build
- [ ] engine binary provenance verified against audited production (hash match; no silent replacement)
- [ ] electron-builder cache/config not reused stale (compression/config per repo scripts)
- [ ] theme assets regenerated/checked (no donor artwork in package)
- [ ] icons: canonical Kel assets only

## Identity

- Package identity bound to exact repair head SHA (recorded below once built)
- Artifact hashes recorded (sha256) for installer + key bundles

## Build commands (canonical, from prior campaigns — confirmed against `desktop/justfile`)

- Renderer/app: `cd desktop && node scripts/build-with-builder.js auto --win`
- Engine (only if needed): PyInstaller per prior campaign, staged to `desktop/dist/runtime/KelEngine`
- Installer output: `Kel-1.6.0-win-x64.exe` (verify actual output path)

## Install

- Review install: `C:\Users\Nick\KelVisualFixInstall`
- Separate data root: `C:\Users\Nick\KelVisualFixRuns\prepared`
- Preserved audit install/roots untouched: `C:\Users\Nick\KelV16ReviewInstall`, `C:\Users\Nick\KelV16ReviewRuns\`

(Results appended when executed.)
