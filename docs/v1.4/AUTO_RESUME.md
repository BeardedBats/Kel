# KEL V1.4 — AUTO-RESUME

Updated: 2026-09-15 ~13:35 ET · Session: #6 (Gate 4 in progress; no blocker, path decided)

- **Current gate**: Gate 4 — **IN PROGRESS** (Team Office / Roster / Studio + unified Work Center).
- **Done in Gate 4 so far** (all pushed): desktop deps installed (frozen lockfile); renderer build
  green (three times); `/api/brief` + `/api/team` allowlisted; team/solution fixtures seeding verified;
  `kel-tokens.css` + `components/kel/*` + `pages/kel/team/index.tsx` + `pages/kel/work/index.tsx`
  routed at `/work`, `/team`, `/team/office|roster|studio`; Sider Work/Team navigation entries;
  harness + a11y probe extended with a dev-mode launch and `--views`/`--routes` sampling.
- **Remaining in Gate 4**: rendered verification (captures + a11y probe + acceptance rows) and the
  reviewer relay.
- **Diagnosis from this session (important)**:
  1. `packaging/capture-screens.cjs` now launches in **dev mode** when `appDir` has no `Kel.exe`
     (Electron from `desktop/node_modules` + the app directory as the first argument) and captures
     `--views id:hash` at every width. `packaging/a11y-probe.cjs` gained the same launch mode plus
     `--routes` sampling with per-route contrast counts.
  2. Dev-mode boot reaches the renderer, **but the shell does not bring the Kel engine up**: the engine
     command is resolved in `KelService.ts` as `process.resourcesPath/kel-engine/KelEngine.exe`
     (packaged layout), falling back to `python -m kel.service` with `cwd = KEL_SOURCE_ROOT ||
     <cwd>/../runtime`. With `KEL_PYTHON=C:\Python314\python.exe` and `KEL_SOURCE_ROOT` set, no
     `desktop-session.json` appeared within 120s, so the harness stalled before its first capture and
     was stopped deliberately (no orphans left; all Electron/KelEngine processes killed and verified 0).
  3. Likely cause: in dev mode the donor backend (AionCore) gate runs before the Kel engine spawn, so
     the engine never starts without the packaged AionCore/engine layout.
- **Decision (path forward)**: stop chasing dev-mode boot. Verify the V1.4 surfaces through a
  **candidate package** — the same evidence path the V1.3 baseline used:
  1. Engine: `scripts/build-runtime.ps1` (PyInstaller → `KelEngine.exe` + `_internal`).
  2. Shell: `bun install` (done) + electron-vite build (done) + the repo’s asar pipeline
     (`packaging/asar-dedup-pack.js`, `asar-inspect.js`) into an **isolated candidate folder** under
     `dev-tools/runs/v14/` (never touching `Kel Releases/`).
  3. Capture with `packaging/capture-screens.cjs <candidateDir> <data/fixture-team> docs/v1.4/screenshots/g4 --tag v14 --views "work:/work,team-office:/team/office,team-roster:/team/roster,team-studio:/team/studio"`;
     run `packaging/a11y-probe.cjs` with the same `--routes`.
  4. Fill the Team/Work rows in `KEL_V1.4_VISUAL_ACCEPTANCE_MATRIX.md`, commit, request the Gate 4 relay.
- **Branch / commit / remote**: `v1.4-dev` @ `995485c` + harness commit · pushed to `origin`.
- **Tests**: engine suite 296 passed + 10 subtests; renderer build green.
- **Tests failing**: none. **Blocker**: none. **HARD STOP: no.**
- **Running processes / ownership**: none (verified 0 Electron/KelEngine processes after cleanup).
- **Frozen-hash state**: 3/3 verified, unchanged; `Kel Releases/` untouched.
- **Dogfood isolation**: intact (all data under `dev-tools/`; windows parked offscreen).
- **Build recipe**: `bun x electron-vite build --config packages/desktop/electron.vite.config.ts` from
  `desktop/` (never `bun run build` — donor multi-arch mac wrapper needing `bunx` on PATH).
- **Continuation safety**: safe (tree clean except untracked `Agents.md`).
