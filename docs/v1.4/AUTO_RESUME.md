# KEL V1.4 — AUTO-RESUME

Updated: 2026-09-15 ~14:30 ET · Session: #6 (Gate 5 in progress; no blocker)

- **Current gate**: Gate 5 — **IN PROGRESS** (verification / continuation / memory / recipes UX).
  Gates 0–4 are CLOSED (each with a reviewer-relay CONTINUE).
- **Done in Gate 5** (all committed and rendered from the packaged candidate):
  1. **Projects workspace** (`pages/kel/projects/index.tsx`): Knowledge (memory records with trust/status/
     source + Confirm · Retract · Forget over `/api/memory`), Map (sections with trust/freshness/digest/
     sources + honest empty state and Build over `/api/map`), Recipes (library over `/api/work`).
     Routes `/projects`, `/projects/knowledge|map|recipes`; Sider “Projects” entry. Evidence:
     `docs/v1.4/screenshots/g5/` tag `g5` (44 shots, 0 errors, 0 blank; route contrast **0/0/0**).
  2. **Work Center verification panel**: two-step “Worker reported: X of Y milestones accepted ·
     Kel verified: <verdict>”, milestone table (state · attempts · checks · filename), artifact viewer
     gated on acceptance (`/api/artifact` refuses unverified milestones), Pause · Resume · Cancel via
     `/api/control`. Rendered text evidence: `… · Kel verified: UNCERTAIN`, row
     `UNCERTAIN · 1 attempt · 1 checks · out.md · not verified — checks have not passed`.
  3. **Continuation chooser**: `/api/state.continuation` rendered as a numbered list with recorded
     verdict/reasons and the explicit rule that Kel never resumes in the background.
     Evidence: tag `g5b` (34 shots, 0 errors, 0 blank; app exit 0).
- **Remaining in Gate 5** (concrete, in order):
  1. **Memory action round-trip**: click Confirm / Retract / Forget against a live engine and capture the
     resulting state (the endpoints exist: `/api/memory` actions `confirm`, `correct`, `retract`,
     `forget`, `resolve_conflict`, ownership-checked).
  2. **Accepted-milestone fixture** so the artifact viewer is exercised end-to-end: extend
     `runtime/tools/seed_ui_fixture.py` to claim + complete one milestone with the fixture provider so a
     milestone reaches `ACCEPTED` with an artifact (engine paths: `Store.claim`, runner, `artifact_text`).
  3. **Recipes UX**: preview with required inputs + permission preview, dry run, progress with frozen
     steps, terminal states — check `/api/recipes` actions first (`_recipes_action` in `service.py`).
  4. Then: captures + probe for the new states, acceptance-matrix rows, commit/push, **Gate 5 reviewer
     relay checkpoint**.
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
- **Engine payload facts (verified this session)**: `/api/state` → jobs (full JSON: `id`, `conversation`,
  `state`, `verdict`, `contract.milestones[]` with `checks`/`filename`, `milestones{state,attempts}`),
  `submissions`, `approvals` (pending, with `action_summary`), `continuation`
  (`Continuation.candidates(project_id)`), `providers`, `engine_version`, `draining`;
  `/api/work` → `{project_id, memory{records,conflicts}, map{version,fingerprint,updated,note,sections},
  recipes{entries}}`; `/api/memory` actions as above; `/api/control` → `(job, action)` for pause/resume/
  cancel; `/api/artifact?job=&milestone=` returns markdown **only for ACCEPTED milestones**;
  `/api/retry` retries FAILED/INTERRUPTED submissions.
- **Known notes (carried)**: engine shutdown needs the bounded kill (G7/G10); donor sidebar label
  contrast 2.92:1 (G7); dark mode + dense states + before/after comparisons pending (G9).
- **Branch / commit / remote**: `v1.4-dev` @ the Gate 5 second-increment commit · pushed to `origin`.
- **Tests**: engine suite 296 passed + 10 subtests (unchanged); renderer build green; packaged capture +
  probe green. **Tests failing**: none. **Blocker**: none. **HARD STOP: no.**
- **Frozen-hash state**: 3/3 verified; `Kel Releases/` untouched. **Dogfood isolation**: intact.
- **Continuation safety**: safe (clean tree; no running processes).
