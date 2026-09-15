# KEL V1.4 — AUTO-RESUME

Updated: 2026-09-15 ~13:50 ET · Session: #6 boundary (Gate 4 CLOSED via relay)

- **Current gate**: Gate 4 — **CLOSED** (reviewer relay: CONTINUE). Next: **Gate 5**
  (verification / continuation / memory / recipes UX).
- **Current phase**: G4→G5 boundary (no work in flight; no processes running; tree clean apart from
  the untracked `Agents.md`, which is intentionally left alone).
- **Branch / commit / remote**: `v1.4-dev` @ `3af1c02` · pushed to `origin`.
- **Gate 4 deliverables** (all committed): `kel-tokens.css`; `components/kel/{kelApi.ts,KelPrimitives.tsx}`;
  `pages/kel/team/index.tsx` (Office / Roster / Studio); `pages/kel/work/index.tsx` (Work Center);
  routes `/work`, `/team`, `/team/office|roster|studio`; Sider entries (`SiderNav/KelNavEntries.tsx`);
  route allowlist for `/api/brief` + `/api/team`; harness `--views`/`--routes` + dev-mode launch.
- **Gate 4 evidence**: `docs/v1.4/screenshots/g4/` (49 captures, five widths, 0 renderer errors,
  0 blank, app exit 0, 20 route views) and `docs/v1.4/screenshots/audit/v14/v13-a11y.json`
  (route contrast 1/1/1/1 — remainder is the donor sidebar label; 12px floor; 0 emoji; 30 focus stops).
  In-gate fixes: `/team/*` deep-link tab bug; table-header contrast 4.35 → ≥6:1.
- **PROVEN UI VERIFICATION LOOP** (use this for every UI gate from G5 on; it produced Gate 4's evidence):
  1. `cd desktop && bun x electron-vite build --config packages/desktop/electron.vite.config.ts`
  2. `rm -rf dev-tools/runs/v14/shell-stage/out && cp -r desktop/out dev-tools/runs/v14/shell-stage/out`
  3. `ASAR_MODULE=C:/Users/Nick/Desktop/Kel/dev-tools/asar/node_modules/@electron/asar node packaging/asar-dedup-pack.js dev-tools/runs/v14/shell-stage dev-tools/runs/v14/app.asar`
  4. `cp dev-tools/runs/v14/app.asar dev-tools/runs/v14/candidate/resources/app.asar`
  5. only when engine code changed: `powershell -ExecutionPolicy Bypass -File scripts/build-runtime.ps1`
     then `rm -rf dev-tools/runs/v14/candidate/resources/kel-engine && cp -r dist/runtime/KelEngine dev-tools/runs/v14/candidate/resources/kel-engine`
  6. capture: `node packaging/capture-screens.cjs dev-tools/runs/v14/candidate <dataDir> <outDir> --tag v14 --widths 1440x900,1280x720,1920x1080,2560x1440,1024x768 --views "work:/work,team-office:/team/office"`
  7. probe: `node packaging/a11y-probe.cjs dev-tools/runs/v14/candidate <dataDir> docs/v1.4/screenshots/audit/v14 --routes "work:/work,team-office:/team/office"`
  8. afterwards verify `(Get-Process | ? { $_.ProcessName -match 'Kel|electron' }).Count` is 0.
  Env needed: `PLAYWRIGHT_MODULE=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/node_modules/playwright`,
  `PLAYWRIGHT_BROWSERS_PATH=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/browsers`.
  Fixture data root: `dev-tools/runs/v13/data/fixture-team` (regenerate with
  `runtime/tools/seed_ui_fixture.py --data … --project-root …`).
- **Known notes (carried, not blocking)**: engine shutdown on app close needs the bounded kill
  (`engineStopped:false`, `closeOutcome: close-timeout`) → G7/G10; donor sidebar label contrast 2.92:1
  → G7; dev-mode launch exists in the harness but the shell's engine gate blocks dev boot → use the
  candidate; dense/dark states and before/after comparison images still to render.
- **Tests**: engine suite 296 passed + 10 subtests (unchanged); renderer build green; packaged
  capture + probe green.
- **Tests failing**: none. **Blocker**: none. **HARD STOP: no.**
- **Frozen-hash state**: 3/3 verified (re-checked after the candidate copy); `Kel Releases/` untouched.
- **Dogfood isolation**: intact (all runs under `dev-tools/`; offscreen windows; 0 leftover processes).
- **Exact next action** (Gate 5):
  1. Surface verification/evidence UX: worker-reported vs Kel-verified as two steps, evidence classes,
     failed/flaky/stale detail, coverage, receipt (engine endpoints already exist: `/api/work`,
     `/api/artifact`).
  2. Continuation UX: chooser (numbered), resume summary, exact-session status, bounded fallback
     message, wrong-project block, recovered-work banner.
  3. Memory/knowledge UX: type + trust badges, source links, confirm/edit/retract/forget, conflict
     resolver, supersession, stale warnings; context preview with why-included.
  4. Recipes UX: library, preview with required inputs + permission preview, dry run, progress with
     frozen steps, terminal states.
  5. Render + capture + probe each surface with the loop above; fill acceptance-matrix rows; commit,
     push, reviewer relay.
- **Continuation safety**: safe (clean tree; no running processes).
