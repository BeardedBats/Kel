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
  (D19 residual + package) → `9d6ce53` (boot probe + tooling) → `db46cf4` (candidate record) →
  `9cfb087` (upgrade preservation proven) → `3e6b544` (interrupted-run continuation fix) → `cc3e859`
  (record pointer) → and the provider-language fix committed with this record.
- Engine: `dist/runtime/KelEngine/KelEngine.exe`, sha256
  `01c58bdfcdb94c34acb1bf811cbf1faf06a29f9068c06c53fd6a97a5058b2a9c` (3,330,256 B),
  PyInstaller from this lane's `runtime/`, structural check 51/51 OK.
- Installer (final re-cut, installed): `dist/package-r12/Kel-1.7.0-dev-win-x64.exe`, sha256
  `0add7bc4d4e08dc16e744fec487951be923c6caf0bb40dbf22a96c8b7422dffb` (213,631,660 B).
- App executable (final re-cut): sha256 `e1d62c5fc4dddb78195081644eb92dcb836e072b34632ac299a403c6c59afdc6`;
  ProductName/FileDescription **Kel**, FileVersion **1.7.0-dev**; installed `Uninstall Kel.exe`
  carries the same metadata (HVRA-MINOR-002 closed at the artifact level).

## Installed copy

- Install dir: `C:\Users\Nick\KelDailyDriverCandidate` (registration points there).
- Data root: `C:\Users\Nick\KelDailyDriverRuns\prepared` (engine root `…\engine`).
- Preserved installs: `KelV16ReviewInstall` and `KelVisualReauditInstall` untouched;
  `KelVisualFixInstall` restored to its recorded V1.6 state after an NSIS update-mode incident
  (engine `f525b15b…` == its record; full procedure in `PACKAGE_EVIDENCE.md`).

## Verified against the installed copy

- Engine from the install ran live (`1.7.0-dev` answered `/api/state`).
- The installed app itself launched, started its bundled engine under its own supervision
  (`KEL_DATA_DIR` honored), and a forced close left **no orphaned `KelEngine` process** — re-verified
  on the re-cut, three launches in a row.
- **Installed GUI battery (re-cut build, `evidence/d19/installed-battery.json`):** nine shipped
  surfaces (Landing, Work, Projects, Recipes, Activity, Transcription, Team → chat redirect,
  Settings, Tools) with **no raw error patterns, no horizontal overflow, zero donor terms, 0 console
  errors**; startup-to-window 13.9 s and 3.0–4.3 s per surface. The four replays: D0-001 (Permissions
  Work column shows the job's request; the engine's job id `0482b75e-…` appears nowhere in it —
  cross-checked against the engine database), D0-004 (exactly one pet-refusal message, toggle settles
  OFF), D1 (human provider statuses; Set up → Save + Verify answers "Saved and verified **Anthropic
  API**: …", key removed again afterwards), D2 (update check fails closed: `Update metadata request
  failed (404)`, no release card). Automatic routing answered in the installed app too:
  `Chosen: Claude (Claude Code) · claude-native` with `Chain: Claude (Claude Code) → Codex → DeepSeek
  API → Anthropic API` — engine ids nowhere on the surface.
- The installed app's SPA serves the real sign-in surface (`Kel - Sign In`, `/#/login`) and the
  remote auth wall refuses unauthenticated backend calls — D3's session enforcement, visible in the
  production build.
- Donor-brand sweep over the re-cut shipped `app.asar`: **0 occurrences** of the donor org name, and
  **0 files** in the built renderer/main output. (`aionui`-family strings remain inside packed
  third-party metadata and internal identifiers — the tolerated remnants recorded in
  `KNOWN_LIMITATIONS.md`; nothing on a user surface.)
- Upgrade preservation: install-over-self kept the durable work byte-identical (1 job CLOSED/VERIFIED,
  1 lease, 1 publication, 2 runs, 2 messages); the installed UI reads it live (finished job, active
  lease, resumption brief).

## Suite state at this record

- Engine: **1029 tests OK** (`python -m unittest discover -s tests`).
- Desktop: tsc exit 0 · **36 files / 269 PASS** (`bunx vitest run`).
- Engine-side journeys with a synthetic provider turn (real kill/recover/continue):
  `python ../packaging/verify_synthetic_journeys.py` — **all green (16/16)**.
- Live journeys (re-run green on fresh data dirs): learning proposals, recipe loop, remote
  gateway (real webui + aioncore + login), route transparency, emergency stop, live revision,
  integrations overview; transcription E2E pass; workforce 277+ OK.

## Open items (honest)

- No provider credential exists on this machine, so no *live model turn* was ever run: journeys 1–3
  carry synthetic-provider evidence (real engine execution paths, fixture text) and the provider setup
  flow is verified to the OS-store + metadata level, not against a live provider API.
- The remote browser half of the paired surface still needs the desktop session's QR login (a phone),
  which this environment does not have; D3's enforcement is verified over the real gateway instead.
- Recorded debt, not fixed at the package gate: the engine's legacy provider id `internal` for the
  Anthropic API entry (user surfaces now name providers from the inventory labels); the update check's
  transport-level wording (`… failed (404)`) instead of a friendlier closed-channel sentence.
- The app creates an empty "New conversation" row when its chat surface initialises; the battery runs
  left three extra rows in the prepared data root. Cosmetic, app-side, and recorded — the durable work
  was untouched.

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
# installed candidate battery (drives the installed app itself)
node packaging/verify-installed-battery.cjs
# engine-side journeys 1–3 with a synthetic provider turn
cd runtime && python ../packaging/verify_synthetic_journeys.py
# rebuild the candidate
powershell -File scripts/build-runtime.ps1
cd desktop && node scripts/build-with-builder.js x64 --win --x64 --config.win.signExecutable=false
```
