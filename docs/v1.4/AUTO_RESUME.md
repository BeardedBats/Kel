# KEL V1.4 — AUTO-RESUME

Updated: 2026-09-15 ~14:10 ET · Session: #6 (Gate 5 in progress; no blocker)

- **Current gate**: Gate 5 — **IN PROGRESS** (verification / continuation / memory / recipes UX).
  Gates 0–4 are CLOSED (each with a reviewer-relay CONTINUE).
- **Done in Gate 5 so far** (committed): the **Projects workspace**
  (`pages/kel/projects/index.tsx` — Knowledge · Map · Recipes) over `/api/work`, `/api/memory`,
  `/api/map`; `kelWork`/`kelMemoryAction`/`kelMapAction`/`kelRecipes` helpers in
  `components/kel/kelApi.ts`; routes `/projects`, `/projects/knowledge|map|recipes`; Sider “Projects”
  entry. Rendered evidence: `docs/v1.4/screenshots/g5/` (tag `g5`, 44 shots at five widths,
  0 renderer errors, 0 blank, app exit 0) + route a11y probe (`contrastFailures: 0/0/0`).
  Verified content: 3 knowledge records with trust 6/10 and 3/10, statuses, sources and
  Confirm · Retract · Forget; map empty state + Build action; 5 built-in recipes.
- **Remaining in Gate 5** (concrete):
  1. **Verification / evidence UX** on the Work Center: worker-reported vs Kel-verified as two distinct
     steps, evidence classes, failed/flaky/stale detail, coverage, and the receipt. Data source:
     `/api/state` → `jobs[]` (full job JSON: `id`, `conversation`, `state`, `verdict`,
     `contract.milestones` with `checks`, `milestones{state,attempts}`) and `submissions` / `approvals`
     (pending rows carry `action_summary`).
  2. **Continuation UX**: chooser (numbered), resume summary, exact-session status, bounded-fallback
     message, wrong-project block, recovered-work banner. Data source: `/api/state` → `continuation`
     (from `kel/continuation.py::Continuation.candidates(project_id)`).
  3. **Memory action round-trip verification**: `/api/memory` actions are `confirm`, `correct`,
     `retract`, `forget`, `resolve_conflict` (ownership checked by `_owned_memory`); the Knowledge
     panel wires Confirm · Retract · Forget — confirm the live round-trip and add Correct + conflict
     resolution.
  4. **Recipes UX**: preview with required inputs + permission preview, dry run, progress with frozen
     steps, terminal states (check `/api/recipes` actions before wiring).
- **PROVEN UI VERIFICATION LOOP** (unchanged; use for every UI increment):
  1. `cd desktop && bun x electron-vite build --config packages/desktop/electron.vite.config.ts`
  2. `rm -rf dev-tools/runs/v14/shell-stage/out && cp -r desktop/out dev-tools/runs/v14/shell-stage/out`
  3. `ASAR_MODULE=C:/Users/Nick/Desktop/Kel/dev-tools/asar/node_modules/@electron/asar node packaging/asar-dedup-pack.js dev-tools/runs/v14/shell-stage dev-tools/runs/v14/app.asar`
  4. `cp dev-tools/runs/v14/app.asar dev-tools/runs/v14/candidate/resources/app.asar`
  5. engine changes only: `powershell -ExecutionPolicy Bypass -File scripts/build-runtime.ps1` then
     `rm -rf dev-tools/runs/v14/candidate/resources/kel-engine && cp -r dist/runtime/KelEngine dev-tools/runs/v14/candidate/resources/kel-engine`
  6. capture: `node packaging/capture-screens.cjs dev-tools/runs/v14/candidate <dataDir> <outDir> --tag <tag> --widths 1440x900,1280x720,1920x1080,2560x1440,1024x768 --views "id:/hash,..."`
  7. probe: `node packaging/a11y-probe.cjs dev-tools/runs/v14/candidate <dataDir> docs/v1.4/screenshots/audit/v14 --routes "id:/hash,..."`
  8. confirm `(Get-Process | ? { $_.ProcessName -match 'Kel|electron' }).Count` is 0.
  Env: `PLAYWRIGHT_MODULE=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/node_modules/playwright`,
  `PLAYWRIGHT_BROWSERS_PATH=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/browsers`. Fixture root:
  `dev-tools/runs/v13/data/fixture-team`.
- **Known notes (carried)**: engine shutdown needs the bounded kill (G7/G10); donor sidebar label
  contrast 2.92:1 (G7); dev-mode harness launch exists but the shell's engine gate blocks dev boot;
  dark mode + dense states + before/after comparison images pending (G9).
- **Branch / commit / remote**: `v1.4-dev` @ the Gate 5 Projects commit · pushed to `origin`.
- **Tests**: engine suite 296 passed + 10 subtests (unchanged); renderer build green; packaged capture
  + probe green. **Tests failing**: none. **Blocker**: none. **HARD STOP: no.**
- **Frozen-hash state**: 3/3 verified; `Kel Releases/` untouched. **Dogfood isolation**: intact.
- **Continuation safety**: safe (clean tree; no running processes).
