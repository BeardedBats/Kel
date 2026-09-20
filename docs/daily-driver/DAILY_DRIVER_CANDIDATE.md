# DAILY_DRIVER_CANDIDATE — Kel 1.7.0-dev

The installed candidate this marathon produced. Everything below is verified against the artifacts and
the installed copy on this machine; incomplete items are stated as incomplete.

## Identity and bind chain

- Product identity: **Kel**, version **1.7.0-dev** (development identity; no release tag, no publish).
- Lane: branch `dev/daily-driver`, worktree `C:\Users\Nick\Desktop\Kel\kel-daily-driver`.
- Base: `37b1f27…` (production tree == the v1.6 repaired line; diff was records/evidence only).
- Phase commits: `3f83be7` (lane open) → `9bdf338` `777fefe` `cce55d0` `f594282` `288a53c` (D0) →
  `80c4ba2` (ENG-001) → `0279a1d` (D1) → `7c9df63` (D2) → `78d8f1d` (D3; `b13301a` wrong-layer
  revert) → `e57d4a3` (D4) → `dde6c1e` (D5) → `43cf675` (D6) → `1374fcd` (D7) → `daafd36` `82ff501`
  (D8) → `6493275` (D9) → `9c35f66` (D10) → `242f4b8` (D11) → `879804e` (D12+D13) → `1ca5eb7` (D14)
  → `8b67cdf` (D15) → `8216e48` (D16+D17) → `5ae5bd0` (D18) → `b28e91b` (D19 gate) → `89f2f23`
  (D19 residual + package) → `9d6ce53` (boot probe + tooling) → this commit (candidate record).
- Engine: `dist/runtime/KelEngine/KelEngine.exe`, sha256
  `17c08c57718afbf1af20010a6ef7bafb05e9db7e293628945785edcc306b1fc9` (3,329,912 B),
  PyInstaller from this lane's `runtime/`, structural check 51/51 OK.
- Installer: `dist/package-r12/Kel-1.7.0-dev-win-x64.exe`, sha256
  `364065d316d8837863d69a3a9b4d28487d91f58ae2c5cd9321745ac3a054d1b8` (213,622,841 B).
- App executable: sha256 `019e4f47a4583af348e79dbca2a789732374aba7105cb2c3e7f7dad00576c649`;
  ProductName/FileDescription **Kel**, FileVersion **1.7.0-dev**; uninstaller carries the same
  metadata (HVRA-MINOR-002 closed at the artifact level).

## Installed copy

- Install dir: `C:\Users\Nick\KelDailyDriverCandidate` (registration points there).
- Data root: `C:\Users\Nick\KelDailyDriverRuns\prepared` (engine root `…\engine`).
- Preserved installs: `KelV16ReviewInstall` and `KelVisualReauditInstall` untouched;
  `KelVisualFixInstall` restored to its recorded V1.6 state after an NSIS update-mode incident
  (engine `f525b15b…` == its record; full procedure in `PACKAGE_EVIDENCE.md`).

## Verified against the installed copy

- Engine from the install ran live (`1.7.0-dev` answered `/api/state`).
- The installed app itself launched, started its bundled engine under its own supervision
  (`KEL_DATA_DIR` honored), and a forced close left **no orphaned `KelEngine` process**.
- The installed app's SPA serves the real sign-in surface (`Kel - Sign In`, `/#/login`) and the
  remote auth wall refuses unauthenticated backend calls — D3's session enforcement, visible in the
  production build.
- Donor-org sweep over the shipped `app.asar`: **0 hits** (two donor links removed in D19; pinned by
  `tests/unit/donor-org-references.test.ts`).

## Suite state at this record

- Engine: **1025 tests OK** (`python -m unittest discover -s tests`).
- Desktop: tsc exit 0 · **34 files / 260 PASS** (`bunx vitest run`).
- Live journeys (re-run green on fresh data dirs): learning proposals, recipe loop, remote
  gateway (real webui + aioncore + login), route transparency, emergency stop, live revision,
  integrations overview; transcription E2E pass; workforce 277+ OK.

## Open items (honest)

- Installed GUI replays that need the desktop session's login (the browser path is login-walled by
  design): D0-001 (Permissions Work column), D0-004 (single pet toast), D1 (providers Set up →
  Save + Verify), D2 (update fails closed), upgrade preservation. Tooling for the pass is recorded:
  flip `webui.desktop.enabled` through the local backend settings route, relaunch, then drive the
  web UI with the browser tools (or the app's own CDP bridge).
- Dogfood journeys 1–3 remain partial by design: this machine has no provider key, so the model turn
  is the missing piece (everything around it is verified).

## Replay

```bash
# suites
cd runtime && python -m unittest discover -s tests
cd desktop && bunx tsc --noEmit && bunx vitest run
# live journeys
node packaging/verify-learning-proposals.cjs && node packaging/verify-recipe-loop.cjs && \
node packaging/verify-remote-kel.cjs && node packaging/verify-route-transparency.cjs && \
node packaging/verify-emergency-stop.cjs && node packaging/verify-live-revision.cjs && \
node packaging/verify-integrations-overview.cjs
# rebuild the candidate
powershell -File scripts/build-runtime.ps1
cd desktop && node scripts/build-with-builder.js x64 --win --x64 --config.win.signExecutable=false
```
