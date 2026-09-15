# KEL V1.4 — AUTO-RESUME

Updated: 2026-09-15 ~15:35 ET · Session: #6 boundary (Gate 5 CLOSED via relay)

- **Current gate**: Gate 5 — **CLOSED** (reviewer relay: CONTINUE). Next: **Gate 6**
  (providers / credentials / autonomy).
- **Current phase**: G5→G6 boundary (no work in flight; no processes running; tree clean apart from the
  intentionally untracked `Agents.md`).
- **Branch / commit / remote**: `v1.4-dev` @ `0a35525` (+ this docs commit) · pushed to `origin`.
- **Gates closed so far**: G0 (baseline/verification), G1 (audit + directions + design system),
  G2 (architecture + safety design), G3 (solution-quality + Team engine), G4 (Team Office/Roster/Studio
  + Work Center), G5 (verification / continuation / memory / recipes UX). Each closed with a
  reviewer-relay CONTINUE and committed evidence.
- **Gate 5 deliverables**: Projects workspace (`pages/kel/projects/index.tsx` — Knowledge · Map ·
  Recipes), Work Center verification panel + continuation chooser, recipe dry-run preview,
  `packaging/verify-actions.cjs`, fixture that completes a milestone through the engine's real path, and
  the evidence bundles under `docs/v1.4/screenshots/g5/` and `docs/v1.4/screenshots/audit/v14/`.
- **PROVEN UI VERIFICATION LOOP** (unchanged; use for every UI gate):
  1. `cd desktop && bun x electron-vite build --config packages/desktop/electron.vite.config.ts`
  2. `rm -rf dev-tools/runs/v14/shell-stage/out && cp -r desktop/out dev-tools/runs/v14/shell-stage/out`
  3. `ASAR_MODULE=C:/Users/Nick/Desktop/Kel/dev-tools/asar/node_modules/@electron/asar node packaging/asar-dedup-pack.js dev-tools/runs/v14/shell-stage dev-tools/runs/v14/app.asar`
  4. `cp dev-tools/runs/v14/app.asar dev-tools/runs/v14/candidate/resources/app.asar`
  5. engine changes only: `powershell -ExecutionPolicy Bypass -File scripts/build-runtime.ps1` then
     `rm -rf dev-tools/runs/v14/candidate/resources/kel-engine && cp -r dist/runtime/KelEngine dev-tools/runs/v14/candidate/resources/kel-engine`
  6. fixture: `cd runtime && python tools/seed_ui_fixture.py --data C:/Users/Nick/Desktop/Kel/dev-tools/runs/v13/data/fixture-team --project-root C:/Users/Nick/Desktop/Kel/dev-tools/runs/v13/fixture-project`
  7. capture: `node packaging/capture-screens.cjs dev-tools/runs/v14/candidate <dataDir> <outDir> --tag <tag> --widths 1440x900,1280x720 --views "id:/hash,..."`
  8. probe: `node packaging/a11y-probe.cjs dev-tools/runs/v14/candidate <dataDir> docs/v1.4/screenshots/audit/v14 --routes "id:/hash,..."`
  9. interactions: `node packaging/verify-actions.cjs dev-tools/runs/v14/candidate <dataDir> docs/v1.4/screenshots/audit/v14/actions`
  10. confirm `(Get-Process | ? { $_.ProcessName -match 'Kel|electron' }).Count` is 0.
  Env: `PLAYWRIGHT_MODULE=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/node_modules/playwright`,
  `PLAYWRIGHT_BROWSERS_PATH=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/browsers`.
- **Exact next action** (Gate 6):
  1. **Provider registry + capability matrix**: `provider_definitions` (class native-cli | api, auth mode,
     per-model capabilities) and the engine's `providers` state row extended with the precise state model
     (not installed · installed-not-authenticated · authenticated · healthy · degraded `circuit_until` ·
     quota · **quota not reported** · unavailable). Readiness preflight before a job resolves the
     required capability + role preference + fallback chain.
  2. **Credential custody**: OS-backed store via the shell main process (Windows DPAPI/Credential
     Manager), namespaced `kel:provider:<id>:<field>`, engine keeps `credential_ref` metadata only,
     values injected per-run as env and scrubbed from grandchildren; test · store · replace · delete for
     Kel-owned entries only; never in logs/prompts/Git/screenshots/memory/diagnostics.
  3. **DeepSeek first-class card**: base `https://api.deepseek.com/v1`, models `deepseek-chat` /
     `deepseek-reasoner`, test connection, quota `Not reported`, request-path test + live-gated smoke.
  4. **Autonomy**: capability lease (`capability_leases` + roots/repos/domains/tools/external actions +
     `lease_events`), boundary-expansion requests (allow once / allow for project / deny), locked
     guardrail presentation (`kel/guardrails.py` `locked_block()`), and the **AUTO-*** enforcement tests
     (AUTO-ROOT, AUTO-REPO, AUTO-BROWSER, AUTO-BLOCK-REG/SYSTEM, AUTO-FROZEN, AUTO-GH-ADMIN, AUTO-CRED,
     AUTO-LEASE-EXPIRY, AUTO-ASK-ONCE, AUTO-GUARDRAIL-IMMUTABLE, AUTO-NO-PROMPT-AFTER-REVIEW).
  5. Render + capture + probe each surface with the loop above; acceptance rows; commit/push; relay.
- **Known notes (carried)**: engine shutdown needs the bounded kill (G7/G10); donor sidebar label
  contrast 2.92:1 (G7); dark mode, dense states, and before/after comparison images pending (G9);
  dev-mode harness launch exists but the shell's engine gate blocks dev boot — use the candidate.
- **Tests**: engine suite 296 passed + 10 subtests (unchanged); renderer build green; packaged captures,
  route probes, and interaction verification all green. **Tests failing**: none.
- **Blocker**: none. **HARD STOP: no.**
- **Frozen-hash state**: 3/3 verified; `Kel Releases/` untouched. **Dogfood isolation**: intact.
- **Continuation safety**: safe (clean tree; no running processes).
