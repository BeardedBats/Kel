# PACKAGE EVIDENCE — daily-driver candidate

Historical V1.6 candidate evidence lives in `docs/v1.6/…` and is untouched (not overwritten).

## Bind chain to record for the daily-driver candidate

source HEAD → renderer build → engine build → installer → installed candidate

- **Source HEAD at final build:** `b28e91b715b8e0adac7ac454b32a9ed6f278d8bb`
  (`test(daily-driver): D19 regression battery green — checkpoint before packaging`) plus the D19
  donor-residual fix commit (see git log at the commit that carries this file update).
- **Engine build:** `scripts/build-runtime.ps1` → `dist/runtime/KelEngine/KelEngine.exe`
  sha256 `17c08c57718afbf1af20010a6ef7bafb05e9db7e293628945785edcc306b1fc9` (3,329,912 bytes);
  `packaging/verify_engine_pyz.py` → matched 51, MISMATCH [], RESULT: OK.
- **Package build:** `node scripts/build-with-builder.js x64 --win --x64 --config.win.signExecutable=false`
  (kel-builder.json; resource editing ON, signing skipped by config).
- **Installer:** `dist/package-r12/Kel-1.7.0-dev-win-x64.exe`
  sha256 `364065d316d8837863d69a3a9b4d28487d91f58ae2c5cd9321745ac3a054d1b8` (213,622,841 bytes).
- **App executable:** `dist/package-r12/win-unpacked/Kel.exe`
  sha256 `019e4f47a4583af348e79dbca2a789732374aba7105cb2c3e7f7dad00576c649`;
  ProductName **Kel**, FileDescription **Kel**, FileVersion **1.7.0-dev**.
- **Engine bundled:** `resources/kel-engine/KelEngine.exe`, installed hash verified == build hash.

## Checklist (verified at this package phase)

- [x] Source HEAD recorded; renderer rebuilt from this lane's sources each build (no stale cache).
- [x] Engine built from this lane's `runtime/` (PyInstaller, structural check 51/51 OK) and bound
      into the package (`kel-engine`).
- [x] `desktop/package.json` version = `1.7.0-dev`; artifact name `Kel-1.7.0-dev-win-x64.exe`.
- [x] Installer metadata: **FileDescription = Kel**, ProductName Kel, FileVersion 1.7.0-dev — **D0-002**.
- [x] Uninstaller metadata: `Uninstall Kel.exe` → FileDescription **Kel**, FileVersion 1.7.0-dev.
- [x] No donor-org strings in the built output: asar sweep `iOfficeAI` → **0 files** (two shipped
      links — the Office preview install link and the AionHub PR link — were removed in the D19
      residual fix and pinned by `tests/unit/donor-org-references.test.ts`).
- [x] Installed probe (engine): the installed `resources/kel-engine/KelEngine.exe` ran against a
      throwaway data dir, published its descriptor and answered `/api/state` (version `1.7.0-dev`).
- [x] Installed probe (app boot): the **installed app itself** (`Kel.exe`, production build) launched
      against `KEL_DATA_DIR=C:\Users\Nick\KelDailyDriverRuns\prepared\engine`, started its bundled
      engine, and that engine answered `/api/state` live (`1.7.0-dev`); a forced close left **no
      orphaned KelEngine process** behind. Boot also revealed the app's agent-browser bridge
      (`[CDP] Agent browser control enabled`, single-target, ephemeral port) — located via `netstat`
      on the app's main PID and confirmed with a `/json/version` probe, and the app's local backend
      answered `GET /api/settings/client` on its ephemeral port (local trust, as designed). Both are
      the tooling for the GUI-pass probes below (`webui.desktop.enabled` can be flipped through the
      backend settings route, then a relaunch starts the web-host for browser-driven checks).
- [x] Installed candidate registration points at `C:\Users\Nick\KelDailyDriverCandidate`.
- [ ] Installed probe: Permissions Work column shows the work's request — **D0-001 live replay** (GUI).
- [ ] Installed probe: Desktop-Pet enable refusal shows exactly ONE toast — **D0-004 live replay** (GUI).
- [ ] Installed probe: Providers page shows human statuses; Set up → Save + Verify — **D1 replay** (GUI).
- [ ] Update check fails closed truthfully in the installed app — **D2 replay** (GUI).
- [ ] Upgrade preservation: install over a disposable populated prior install — **D2/Journey-7**.
- [x] Install dir: `C:\Users\Nick\KelDailyDriverCandidate`; data root prepared at
      `C:\Users\Nick\KelDailyDriverRuns\prepared`.
- [x] Preserved installs: `KelV16ReviewInstall` (Sep 19 17:17) and `KelVisualReauditInstall`
      (Sep 19 22:31) untouched; `KelVisualFixInstall` **incident + repair recorded below**.

## Install incident + repair (recorded for transparency)

The first silent install entered NSIS update mode (the app's `customInit` heal reads
`InstallLocation` from `HKCU\Software\9280710d-02b9-55d6-ba7a-2b7d6f91d60a` and reinstalls to the
registered directory), so it updated the preserved `KelVisualFixInstall` instead of landing at the
requested `/D` path — the same failure mode (and recovery) the V1.6 human-visual-repair records
describe. Recovery performed, mirroring the documented procedure:

1. Cleared `HKCU\Software\9280710d-…` + the matching Uninstall key so the next install was fresh.
2. Restored `KelVisualFixInstall` with its **own** V1.6 artifact
   (`kel-v16-human-visual-fix/dist/package-r12/Kel-1.6.0-win-x64.exe`, sha256 `0dc5dc36…` as recorded
   in `docs/v1.6/human-visual-repair/05_PACKAGE_EVIDENCE.md`); verified engine hash
   `f525b15bb77385831c0695fb02998ed6ea3dd21315926792052e4894021af5d8` — exactly the recorded V1.6
   visual-fix engine — and `Kel.exe` FileVersion 1.6.0.
3. Cleared the registration keys again, then installed the daily-driver candidate fresh to
   `C:\Users\Nick\KelDailyDriverCandidate`; verified files + engine hash + metadata + registration.
4. Re-ran the whole sequence after the final rebuild; preserved installs verified side by side
   (timestamps unchanged for the two untouched dirs; the restored V1.6 install matches its record).

## Records

| Phase | Artifact | SHA-256 | Notes |
| --- | --- | --- | --- |
| build-01 (superseded) | `Kel-1.7.0-dev-win-x64.exe` (fast build, no engine staged) | `50c107eb…` | proved the pipeline; superseded (engine missing, exe metadata skipped via fast flag) |
| build-02 (final) | `Kel-1.7.0-dev-win-x64.exe` | `364065d3…` | engine bundled + exe resource editing applied; donor-org sweep 0 hits; installed to the candidate and re-verified in place after the D19 residual rebuild |
| engine | `dist/runtime/KelEngine/KelEngine.exe` | `17c08c57…` | PyInstaller from this lane's `runtime/`; structural check 51/51 OK; installed hash verified equal |

## Installed battery status at this checkpoint

- Done (machine-verifiable): engine-from-install live smoke; installer + uninstaller metadata;
  donor-org sweep on the built bundle; install/registration/engine-hash verification; preserved
  installs verified side by side; V1.6 install restored to its recorded state.
- Remaining (GUI-driven, next pass): D0-001 (Work column), D0-004 (single pet toast), D1
  (providers Set up → Save + Verify), D2 (update fail-closed), upgrade preservation — run against
  the installed candidate at `C:\Users\Nick\KelDailyDriverCandidate` with the data root
  `C:\Users\Nick\KelDailyDriverRuns\prepared`.
