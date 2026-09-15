# KEL V1.4 — AUTO-RESUME

Updated: 2026-09-15 ~15:00 ET · Session: #6 (Gate 5 in progress; no blocker)

- **Current gate**: Gate 5 — **IN PROGRESS**. Gates 0–4 are CLOSED (each with a reviewer-relay
  CONTINUE). Remaining in Gate 5: **memory action round-trip**, **recipes preview/dry-run**, then the
  **Gate 5 reviewer relay** and the gate close-out.
- **Done in Gate 5** (all committed; every item rendered from the packaged candidate):
  1. **Projects workspace** (`pages/kel/projects/index.tsx`): Knowledge (memory records with
     type/trust/status/source + Confirm · Retract · Forget), Map (trust/freshness/digest/sources +
     honest empty state and Build), Recipes (library). Routes `/projects`,
     `/projects/knowledge|map|recipes`; Sider entry. Evidence: tag `g5` (44 shots, route contrast 0/0/0).
  2. **Work Center verification panel**: two-step “Worker reported: X of Y milestones accepted ·
     Kel verified: <verdict>”, milestone table (state · attempts · checks · filename), Pause · Resume ·
     Cancel via `/api/control`. Evidence: tag `g5b`.
  3. **Continuation chooser** from `/api/state.continuation` — numbered candidates with recorded
     verdicts and the explicit “never resumes in the background” rule. Evidence: tag `g5b`.
  4. **End-to-end receipt**: `runtime/tools/seed_ui_fixture.py` now runs a milestone through the engine's
     real path — `claim` → fixture worker result (`enqueue_result` + `consume`) → `verify` (checks
     `artifact_digest` + `min_chars`) → `assess` → `publish` — **seeded into the `main` conversation**
     the shell renders. Seed reports `{"verify": "VERIFIED", "verdict": "VERIFIED"}`; the UI shows
     “Worker reported: 1 of 1 milestones accepted · Kel verified: VERIFIED”, row
     `ACCEPTED · 1 attempt · 1 checks · out.md · View artifact`, and the auto-loaded **Receipt — m1**.
     Evidence: tag `g5d` (0 renderer errors, 0 blank, app exit 0).
- **Exact next actions (finish Gate 5)**:
  1. **Memory action round-trip**: click Confirm / Retract / Forget against a live engine and capture the
     resulting state change (endpoints: `/api/memory` actions `confirm`, `correct`, `retract`, `forget`,
     `resolve_conflict`; ownership-checked). A harness click pass or a small scripted route is fine —
     recording the before/after text is the evidence.
  2. **Recipes preview/dry-run**: read `_recipes_action` in `service.py` for the exact action vocabulary,
     then add a preview sheet (steps, required inputs, permission preview) and a dry-run affordance.
  3. Captures + probe for the new states; acceptance-matrix rows; commit + push; **Gate 5 relay**;
     then close the gate and update the ledger with the V14 item IDs that Gate 5 verifies.
- **PROVEN UI VERIFICATION LOOP** (unchanged):
  1. `cd desktop && bun x electron-vite build --config packages/desktop/electron.vite.config.ts`
  2. `rm -rf dev-tools/runs/v14/shell-stage/out && cp -r desktop/out dev-tools/runs/v14/shell-stage/out`
  3. `ASAR_MODULE=C:/Users/Nick/Desktop/Kel/dev-tools/asar/node_modules/@electron/asar node packaging/asar-dedup-pack.js dev-tools/runs/v14/shell-stage dev-tools/runs/v14/app.asar`
  4. `cp dev-tools/runs/v14/app.asar dev-tools/runs/v14/candidate/resources/app.asar`
  5. engine changes only: `powershell -ExecutionPolicy Bypass -File scripts/build-runtime.ps1` then
     `rm -rf dev-tools/runs/v14/candidate/resources/kel-engine && cp -r dist/runtime/KelEngine dev-tools/runs/v14/candidate/resources/kel-engine`
  6. fixture: `cd runtime && python tools/seed_ui_fixture.py --data C:/Users/Nick/Desktop/Kel/dev-tools/runs/v13/data/fixture-team --project-root C:/Users/Nick/Desktop/Kel/dev-tools/runs/v13/fixture-project`
  7. capture: `node packaging/capture-screens.cjs dev-tools/runs/v14/candidate <dataDir> <outDir> --tag <tag> --widths 1440x900,1280x720 --views "id:/hash,..."`
  8. probe: `node packaging/a11y-probe.cjs dev-tools/runs/v14/candidate <dataDir> docs/v1.4/screenshots/audit/v14 --routes "id:/hash,..."`
  9. confirm `(Get-Process | ? { $_.ProcessName -match 'Kel|electron' }).Count` is 0.
  Env: `PLAYWRIGHT_MODULE=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/node_modules/playwright`,
  `PLAYWRIGHT_BROWSERS_PATH=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/browsers`.
- **Engine facts confirmed this session** (useful for the remaining work): the shell renders conversation
  id `main`, so **fixtures must be seeded into `main`** to be visible; the engine's real completion path
  is `store.claim(job, milestone)` → `store.enqueue_result(event, run_id, epoch, payload)` →
  `store.consume()` → `store.verify(job, milestone)` → `store.assess(job)` → `store.publish(job)`;
  `/api/artifact?job=&milestone=` returns markdown **only for ACCEPTED milestones**; `/api/control`
  takes `(job, action)`; `/api/state` exposes jobs (full JSON), submissions, approvals, continuation,
  providers, engine_version, draining; `/api/work` exposes memory/map/recipes.
- **Known notes (carried)**: engine shutdown needs the bounded kill (G7/G10); donor sidebar label
  contrast 2.92:1 (G7); dark mode + dense states + before/after comparisons pending (G9).
- **Branch / commit / remote**: `v1.4-dev` @ the Gate 5 third-increment commit · pushed to `origin`.
- **Tests**: engine suite 296 passed + 10 subtests (unchanged); renderer build green; packaged capture +
  probe green. **Tests failing**: none. **Blocker**: none. **HARD STOP: no.**
- **Frozen-hash state**: 3/3 verified; `Kel Releases/` untouched. **Dogfood isolation**: intact.
- **Continuation safety**: safe (clean tree apart from untracked `Agents.md`; no running processes).
