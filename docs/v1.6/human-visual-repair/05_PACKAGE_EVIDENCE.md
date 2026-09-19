# 05 — PACKAGE EVIDENCE (Kel V1.6 human visual repair)

Fresh build from the repair head; no reuse of old renderer output.

## Identity

- Production source head (HUMAN_VISUAL_REPAIR_HEAD): `6d957ee9aad7200fb2fcff9b505e0771e2dfdcda`
- Installer: `dist/package-r12/Kel-1.6.0-win-x64.exe`
  - sha256 `0dc5dc36010c2d355c874a04fd63f9d5db12059d9974c8369f0f85470fa46509` (213,608,723 bytes, build 2026-09-19 17:51)
- Engine binary (audited production engine, staged from the audited tree, hash-verified):
  `resources/kel-engine/KelEngine.exe` sha256 `f525b15bb77385831c0695fb02998ed6ea3dd21315926792052e4894021af5d8`
- App executable: ProductName **Kel**, ProductVersion 1.6.0.0, FileVersion 1.6.0

## Stale-artifact guards applied

- `dist/package-r12` removed before each build; final build (`build8`) clean
- Renderer/main rebuilt from the repair head (`out/renderer` from the build, no copied output)
- Engine staged once from `kel-v16-final-repair` and hash-verified (no substitution)
- Theme assets: donor cover deleted from the tree (see 02); packaged resources contain no donor artwork
- Icons: canonical Kel set (About logo + nav mark load from the package)

## Install (review candidate)

- Review install: `C:\Users\Nick\KelVisualFixInstall` (registered; engine `f525b15b…`; verified after final reinstall)
- Review data root: `C:\Users\Nick\KelVisualFixRuns\prepared` (fresh-seeded on a copy; audit roots untouched)
- Launcher for Nick: `C:\Users\Nick\KelVisualFixRuns\Launch Kel V1.6 Visual Fix Review.cmd`
- Installed validation: `kelvis-verify` all-gates PASS + `r12-installed-probe` GATE PASS (see 03)

## Preservation of the audit install (incident + restoration, recorded for transparency)

The first silent install accidentally updated the preserved audit install in place: the installer's
`customInit` heal reads `InstallLocation` from `HKCU\Software\9280710d-02b9-55d6-ba7a-2b7d6f91d60a` and
reinstalls to the registered directory; it also stops a running instance it finds (the audit app was open).
Recovery performed:

1. The audited build was restored to `C:\Users\Nick\KelV16ReviewInstall` with the audit campaign's own
   installer (`kel-v16-postrepair-audit/dist/package-r12/Kel-1.6.0-win-x64.exe`); its engine hash
   (`df4f0ee9…`) matches what the install held before the incident.
2. The registration keys were cleared once so the repair installer could land fresh at the dedicated review
   path; the review install now registers `KelVisualFixInstall`. Both installs verified side by side.

No audit branch, tag, corpus, or data root was modified at any point.
