# PACKAGE EVIDENCE — daily-driver candidate

Historical V1.6 candidate evidence lives in `docs/v1.6/…` and is untouched (not overwritten).

## Bind chain to record for the daily-driver candidate

source HEAD → renderer build → engine build → installer → installed candidate

- **Source HEAD at final build:** `cc3e859` (`docs(daily-driver): point the D19 friction entry at its
  commit`) plus the D19 fix commits it follows (`3e6b544` interrupted-run continuation) and the
  provider-language fix committed together with this record (see git log at the commit that carries
  this file update).
- **Engine build:** `scripts/build-runtime.ps1` → `dist/runtime/KelEngine/KelEngine.exe`
  sha256 `01c58bdfcdb94c34acb1bf811cbf1faf06a29f9068c06c53fd6a97a5058b2a9c` (3,330,256 bytes);
  `packaging/verify_engine_pyz.py` → matched 51, MISMATCH [], RESULT: OK. Unchanged between the two
  cuts — the engine source did not move, only the renderer did.
- **Package build:** `node scripts/build-with-builder.js x64 --win --x64 --config.win.signExecutable=false`
  (kel-builder.json; resource editing ON, signing skipped by config).
- **Installer (re-cut, installed):** `dist/package-r12/Kel-1.7.0-dev-win-x64.exe`
  sha256 `f5c8f2672ba3561270f5a906befa3f18c4167e76916025a373cba491d563a397` (213,633,457 bytes).
- **App executable (re-cut):** `dist/package-r12/win-unpacked/Kel.exe`
  sha256 `de1109c8a4094516472b9313ab78e9ff4ca0b3dbdb2ce4e0f76d90af7726326a`;
  ProductName **Kel**, FileDescription **Kel**, FileVersion **1.7.0-dev**.
- **Engine bundled:** `resources/kel-engine/KelEngine.exe`, installed hash verified == build hash
  (`01c58bdf…`).

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
- [x] Installed probe: Permissions Work column shows the work's request — **D0-001 live replay, PASS**.
      The column read "Summarise the Q3 customer feedback into a one-page brief" while the engine's own
      record (`capability_leases.job_id`) is `0482b75e-…`, which appears nowhere in the column
      (`labelEqualsTheRequest`, `labelIsNotAnIdentifier`, `identifiersHiddenFromTheColumn` all true).
- [x] Installed probe: Desktop-Pet enable refusal shows exactly ONE toast — **D0-004 live replay, PASS**.
      The distinct-toast count (outermost Arco nodes) is 1, the sentence is "The desktop pet is not
      available in this build, so it stays off.", and the switch settles OFF.
- [x] Installed probe: Providers page shows human statuses; Set up → Save + Verify — **D1 replay, PASS**.
      Statuses are Needs setup / Available (no raw engine enums); Set up opened the key field, Save +
      Verify was enabled and answered honestly: "Saved and verified **Anthropic API**: the key is in
      the OS store and recorded for the engine." The synthetic key was removed again afterwards and the
      two setup rows returned (2 × Needs setup). The card does not claim "Connected".
- [x] Update check fails closed truthfully in the installed app — **D2 replay, PASS**. Version shown
      `v1.7.0-dev`; the manual check answered `Update metadata request failed (404)` (no Kel release
      feed exists yet), no release card appeared, and no donor terms are on the page.
- [x] Installed pass over nine surfaces (Landing, Work, Projects, Recipes, Activity, Transcription,
      Team → chat redirect, Settings, Tools): **no raw error patterns, no horizontal overflow, zero
      donor terms**; navigation 3.0–4.3 s per surface, startup-to-window 11.5 s, **0 console errors**,
      and the forced close left **no orphaned `KelEngine` process**. Evidence:
      `docs/daily-driver/evidence/d19/installed-battery.json` (+ surface and probe screenshots).
- [x] Upgrade preservation (re-proven on the re-cut): the prepared engine root held 1 job
      ("Summarise the Q3 customer feedback into a one-page brief", CLOSED/VERIFIED) + 1 lease + 1
      publication + 2 runs + 2 messages before the install; the installer updated the candidate in
      place (correct update-mode target) and every one of those counts is identical afterwards. The
      only delta is the app's own chat surface creating an empty "New conversation" row at launch
      (9 → 12 rows across the battery runs) — app behaviour, not installer damage.
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
| build-02 (superseded) | `Kel-1.7.0-dev-win-x64.exe` | `364065d3…` | engine bundled + exe resource editing applied; donor-org sweep 0 hits; installed to the candidate and re-verified in place after the D19 residual rebuild |
| build-03 (re-cut, installed) | `Kel-1.7.0-dev-win-x64.exe` | `f5c8f267…` | re-cut after the D19 provider-language fix (renderer only; engine hash unchanged `01c58bdf…`); donor-org sweep 0 files / 0 occurrences; installed over the candidate in place and fully batteries |
| engine | `dist/runtime/KelEngine/KelEngine.exe` | `01c58bdf…` | PyInstaller from this lane's `runtime/`; structural check 51/51 OK; installed hash verified equal |

## Installed battery — final state

The four GUI-driven replays left open by the first pass are now done, on the installed re-cut build
(`install dir C:\Users\Nick\KelDailyDriverCandidate`, data root
`C:\Users\Nick\KelDailyDriverRuns\prepared`):

- **D0-001 PASS** — Permissions Work column shows the work's request; the engine's job id is not in it
  (cross-checked against the engine's own database).
- **D0-004 PASS** — exactly one refusal message, truthful OFF state.
- **D1 PASS** — human provider statuses; Set up → Save + Verify answers honestly and names the
  provider the person clicked (`Saved and verified Anthropic API: …`); the synthetic key was removed
  again, leaving the prepared state as found.
- **D2 PASS** — update check fails closed with the transport truth, no donor infrastructure.
- **Upgrade preservation PASS** — durable work identical before/after the install (see the checklist
  entry); the installed UI reads it live (finished job + active lease + resumption brief).
- **Surfaces PASS** — nine shipped surfaces with no raw errors, no overflow, no donor terms; startup
  11.5 s, 3.0–4.3 s per surface, no orphaned processes.

Replay: `node packaging/verify-installed-battery.cjs` (drives the installed app through its own
window; `--tour` and `--dump-providers` are the structural inspection modes). The engine-side
journeys that support this battery are re-runnable with
`cd runtime && python ../packaging/verify_synthetic_journeys.py`.
