# 04 — PACKAGE IDENTITY (final re-audit)

Fresh, independent build of the fixed production tree (`7cf6030`; production tree == `05a076b`)
in the dedicated audit worktree. Campaign C's package was NOT used as primary proof.

## Build chain (this audit)

1. Engine: `python -m PyInstaller KelEngine.spec --noconfirm` from `runtime/`
   (`evidence/ra-engine-build-log.txt`).
2. Stage: `runtime/dist/KelEngine` copied to `desktop/dist/runtime/KelEngine` and
   `<root>/dist/runtime/KelEngine`.
3. Package: `node scripts/build-with-builder.js auto --win` from `desktop/`
   (`evidence/ra-package-build-log.txt`) — fresh Vite SSR/main/renderer build (virgin worktree,
   no cache), MCP bundle export, aioncore prep (GitHub download, provenance written), then
   electron-builder. The log shows the assert line
   `Build identity: Kel -> com.kel.kel.desktop (kel-builder.json)` and the final NSIS step
   `building target=nsis file=...Kel-1.6.0-win-x64.exe` — i.e. the documented command DOES
   produce the installer (observed; the same observable as Campaign C's v3 log).
4. Install: `ux-audit/r12-install.ps1` executed by THIS audit against
   `C:\Users\Nick\KelFinalAuditInstall` (`evidence/ra-install-fresh/install.log`).

## SHA-256 chain (byte-identical through the chain)

| Stage | Artifact | SHA-256 |
|---|---|---|
| built | `runtime/dist/KelEngine/KelEngine.exe` | `df4f0ee991dfd5c0d74e54fffc9510ebf4948dd3d9050088f39561a33ea7e01f` |
| staged (desktop copy) | `desktop/dist/runtime/KelEngine/KelEngine.exe` | `df4f0ee9…e01f` (same) |
| staged (root copy) | `dist/runtime/KelEngine/KelEngine.exe` | `df4f0ee9…e01f` (same) |
| packaged | `dist/package-r12/win-unpacked/resources/kel-engine/KelEngine.exe` | `df4f0ee9…e01f` (same) |
| **installed** | `C:\Users\Nick\KelFinalAuditInstall\resources\kel-engine\KelEngine.exe` | `df4f0ee9…e01f` (same) |
| app main | `win-unpacked/Kel.exe` | `f65b430a…` (installed copy identical) |
| installer | `dist/package-r12/Kel-1.6.0-win-x64.exe` | `034e2c18…` |
| aioncore provenance | `win-unpacked/resources/bundled-aioncore/win32-x64/provenance.json` | `sha256 67eb0277…` = reference value; bytes 99,193,856 |

Source → renderer build → staged engine → packaged engine → installer → installed engine is bound
by hashes; the engine bytes never change across the chain. Full values:
`evidence/ra-package-identity.txt`.

## Version identity (1.6.0 on every surface checked)

| Surface | Value |
|---|---|
| `Kel.exe` FileVersion / ProductVersion | `1.6.0` / `1.6.0.0` (ProductName `Kel`, CompanyName `Kel`) |
| Installer exe metadata | `Kel` / `1.6.0` |
| ARP (HKCU Uninstall) | `DisplayName Kel`, `DisplayVersion 1.6.0`, `Publisher Kel`, `UninstallString …\Uninstall Kel.exe /currentuser`, DisplayIcon present |
| engine `/api/state` | `engine_version 1.6.0` (fresh + continuity probes) |
| About surface (probe) | `aboutText` reads Kel; canonical K logo loaded (`aboutLogoLoaded=true`) |

## Divergence classes explicitly re-tested

| Prior divergence class | Result |
|---|---|
| stale Vite output | virgin worktree; fresh SSR/main/renderer compile observed in log |
| stale engine | chain hash equality (above) |
| nested runtime directory | packaged path `resources/kel-engine/KelEngine.exe`; bootstrap finds it (app boots, engine 1.6.0) |
| old build cache | none existed in this worktree; full compile |
| wrong builder config | identity assert line; `productName/appId` Kel; installer produced |
| donor metadata | `ProductName/CompanyName = Kel` on exe + installer; donor strings remain only where recorded (RA-MINOR-002 / RA-SUG-002, error-path dialogs) |
| donor executable assumption | C-DISC-001 fixed at HEAD; install exit 0 (was E1010 pre-fix — campaign prefix evidence retained in `repair-final`) |
| stale installer script | installer compiled from HEAD nsh set; fresh install + reinstall-over both exit 0 |

## Non-reproducibility nuance (identity methodology)

PyInstaller 6.19 output is not byte-reproducible: two consecutive builds here differ in 4 bytes
and vs Campaign C's build in 6 bytes, all inside the PE build-stamp region (`0x101/0x151/0x3DAC5`).
Identity is therefore enforced *within one build chain*, which this audit verified end-to-end
(built -> staged -> packaged -> installed all equal). See `03_REGRESSION.md` for the byte offsets.
