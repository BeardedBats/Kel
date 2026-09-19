# 15 — PACKAGE / INSTALLER

Audit target `08f56673…`. The auditor built and exercised its OWN package; Campaign A's package was used only for comparison.

## Independent rebuild (from the RC SHA)

- Renderer rebuild: `bunx electron-vite build` → **VITE_OK** (fresh output; catches stale-Vite class).
- Packaging: `bunx electron-builder --config kel-builder.json --win --x64 -c.win.target=nsis …` → **BUILDER_OK**; outputs in the audit tree (`build-output/package-audit/`):
  `Kel-1.6.0-win-x64.exe` (202,142,547 B) + `win-unpacked/` (`Kel.exe` 204,575,232 B) + `builder-debug.yml`.
- Log (kept): `evidence/auditor-package-build.log`. Key observations recorded there: electron-builder loads **`kel-builder.json` plus the donor `packages/desktop/electron-builder.yml` as *parent configuration*** (inheritance/merging — relates to **AUD-MINOR-009**); dependency handling notes (bun traversal; optional-dep skips are cross-platform ones).
- Engine: independent PyInstaller rebuild succeeded (`evidence/auditor-engine-rebuild.log`; fresh `KelEngine.exe` same 3,326,709 B, different SHA-256 — expected PyInstaller non-reproducibility). The packaged pipeline bundles the **staged verified bundle** `69123af0…`; the auditor-built package's `resources/kel-engine/KelEngine.exe` hash was verified **identical** to the staged and to the RC-packaged engine.
- exe metadata (auditor build): `ProductName=Kel · FileVersion=1.6.0`; icon present via `signAndEditExecutable` path.

## Install / lifecycle (auditor-built package)

- Silent install to a controlled path (`C:\Users\Nick\KelAuditInstall`): exit 0; files + `Uninstall Kel.exe` + engine + asar present; **installed engine sha256 = `69123AF0…`**; both shortcuts created; ARP entry `Kel · 1.6.0 · Publisher Kel` with a correct `UninstallString` (`evidence/auditor-install.log`).
  - Invocation note: a first attempt passed `/D=` with forward slashes and NSIS mangled the path (no files findable; ARP entry written). With the canonical backslash `/D=` form the install is correct. Recorded as auditor method nuance, not a product finding (Campaign A used the backslash form).
- Reinstall over existing: exit 0, app intact (upgrade path exercised at installer level).
- **Installed-package journey (auditor probe):** healthy boot, engine 1.6.0, attention section present, About K renders, 0 console errors / raw leaks / overflow — `evidence/auditor-installed-probe*` (screenshots `r12-work.png`, `r12-about.png`).
- Uninstall: exit 0; install dir removed; both shortcuts removed; ARP entry removed; the isolated data root (auditor-provided `KEL_DATA_DIR`) is retained — user-data retention semantics observed (`evidence/auditor-reinstall-uninstall.log`).
- **Engine-loss journey on the installed auditor build — PASS** (evidence: `evidence/auditor-r10/` + `auditor-r10.log`): kill #1 → recovered (fresh pid 29640); kill #2 → recovered (fresh pid 15940, attempts=2); kill #3 → **unrecoverable** (attempts=2; no blind restart); manual retry → recovered (fresh pid 44980); conversations, project, and the seeded durable folder preserved; `consoleErrors: []`, `rawLeaks: []`; 4 screenshots retained.

## Byte-level note (recorded, not a finding)

- `app.asar` hash differs between the auditor rebuild and the RC package (expected for independent builds: asar layout/ordering and any build-varying payloads; the RC's own chain hash-exact parts — engine binary, metadata — were verified). A structural asar content comparison was attempted but `@electron/asar` was not resolvable from the shell; recorded as a method limitation.

## Donor/build-config notes

- **AUD-MINOR-009:** donor `electron-builder.yml` (appId `com.aionui.app`, productName `AionUi`) is the DEFAULT script path and the PARENT config for Kel builds; Kel identity comes from `kel-builder.json` overrides.
- **AUD-MINOR-007/004(e):** no build log/command record was retained for the RC `package-r12`; the exact invocation is unreconstructable from evidence.
