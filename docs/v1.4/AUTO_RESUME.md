# KEL V1.4 — AUTO-RESUME

Updated: 2026-09-15 ~19:10 ET · Session: #6 boundary (Gate 8 CLOSED via relay)

- **Current gate**: Gate 8 — **CLOSED** (reviewer relay: CONTINUE). Next: **Gate 9**
  (full-app visual redesign / polish). Gates 0–8 are CLOSED, each with a relay CONTINUE.
- **Current phase**: G8→G9 boundary (no work in flight; no processes running; tree clean apart from the
  intentionally untracked `Agents.md`).
- **Branch / commit / remote**: `v1.4-dev` @ `7c8253e` (+ this docs commit) · pushed to `origin`.
- **Gate 8 outcome**: `kel/diagnostics.py` (migration 009) — startup spans, performance measurements and
  health/process observations from real sources (integrity check, main/WAL sizes, page accounting, runs
  past their fence, provider states, worker pids with a Windows-safe liveness check); `/api/diagnostics`
  (snapshot · observe · performance · retention · set_retention · purge · compact · export · report);
  **12 DIAG-*** tests, suite **358 passed + 10 subtests**; the service records a **measured**
  `engine-start` span (420.24 ms in the captured run). Safety enforced and tested: allowlist-only export
  with a receipt (a planted `sk-live-…` marker in a job request and a worker identity never appears),
  note redaction in the local issue report, retention refuses `jobs`, purge touches observations only,
  compaction backs up then vacuums and closes its handles. UI `/diagnostics` rendered from the packaged
  candidate (tag `g8`: 25 shots, 0 renderer errors, 0 blank, route contrast 0, engine rebuilt +
  PYZ `RESULT: OK`).
- **Defects caught by the evidence loop in Gate 8** (all fixed in-gate): a wrong columnar assumption
  about `jobs` (its state lives in the JSON payload), a lazily-created `native_processes` table that
  crashed snapshots on other store states, a leaked SQLite handle in `compact()` that kept the database
  locked on Windows, and an un-sanitized user note in the shareable report.
- **PROVEN UI VERIFICATION LOOP** (unchanged): renderer build (`bun x electron-vite build --config
  packages/desktop/electron.vite.config.ts`) → overlay `desktop/out` into
  `dev-tools/runs/v14/shell-stage/out` → `asar-dedup-pack.js` → copy the asar into
  `dev-tools/runs/v14/candidate/resources/app.asar` → **engine changes**: `scripts/build-runtime.ps1` +
  `verify_engine_pyz.py` (`RESULT: OK`) + replace `resources/kel-engine` → `seed_ui_fixture.py` → capture
  (`capture-screens.cjs --views`) → probe (`a11y-probe.cjs --routes`) → interactions
  (`verify-actions.cjs`, `verify-credentials.cjs`, `verify-palette.cjs`, `verify-onboarding.cjs`,
  `probe-skip-link.cjs`) → confirm 0 leftover `Kel`/`electron` processes.
  Env: `PLAYWRIGHT_MODULE=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/node_modules/playwright`,
  `PLAYWRIGHT_BROWSERS_PATH=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/browsers`.
  Fixture root `dev-tools/runs/v13/data/fixture-team`; fresh-install root `dev-tools/runs/v14/data/fresh`.
- **Exact next action (Gate 9 — full visual redesign / polish)**:
  1. ~~Before/after comparisons~~ **DONE** (commit `4f692e7`): `packaging/make-comparisons.cjs` produced
     **23 sheets** in `docs/v1.4/screenshots/comparisons/` (boot, work drawer + tabs, all eleven settings
     pages, 1280 repeats) with `index.json` recording per-pair byte deltas; only true pairs are listed,
     and V1.4-only surfaces are covered by their own gate captures instead of a fake baseline.
  2. ~~Dark mode~~ **DONE** (commit `ad80168`) — the harness now applies the donor's full theme **pair**
     (`html[data-theme]` + `body[arco-theme]`; the root alone left Arco components on light rules), and the
     muted-text layer is corrected **per theme** (light `#5c6470`, dark `#9aa4b2`) with
     `packaging/probe-tokens.cjs` reporting the resolved values instead of assuming them. Also repaired
     from the G9 design review: the reduced-motion fallback is now global (donor transitions were
     uncovered) and six gradient/cream toast fills became flat semantic fills. **Open (3 labels)**: the
     dark audit still fails on `sider-section-label` (2.53:1), the Arco text button “Work & context”
     (2.13:1) and the workspace footnote “Work in a project” (2.46:1) — all three keep **hardcoded donor
     colours** (`rgb(92,100,112)` / `rgb(78,89,105)`) that no token reaches, so they need direct
     component-level fixes. Light remains at 0 failures.
     **CLOSED (commits `63537d6`, `c605be2`)**: the blocker was the *switch*, not the tokens. Dark mode is
     now driven through the app's own Appearance setting (`#/settings/appearance` → the “Dark” theme card),
     which is how the donor applies a theme (it injects the token styles and sets both
     `html[data-theme]` and `body[arco-theme]`); with that, the three labels cleared and the only
     remaining failures were white text on the dark accent (3.16:1) in primary buttons and selected tabs,
     now fixed with a per-theme **accent ink** token (`#ffffff` light / `#101418` dark). Final audits:
     **0 contrast failures in BOTH themes** — boot 0 · drawer 0 · 0 on all eleven routes.
  3. ~~Dense states~~ **DONE** (commit `d77b4b2`): the compact density mode was defined in tokens but never
     applied; the Work Center now sets `data-density` from its row count (`jobs + assignments > 10`) and compact
     visibly tightens rows/cards instead of shrinking type. `seed_ui_fixture.py --dense` seeds twelve varied
     jobs, and the harness dismisses first-run setup on a freshly seeded root (found while running this check).
     Verified: **`density: compact`, 19 rows**, contrast 0.
  4. **Donor-surface repairs carried forward**: work-drawer tabs as semantic buttons, unused lazy imports
     in `Router.tsx`, donor CSS gradient/cream findings from the design review, live pet-window capture
     (`app.windows()` support in the harness).
  5. **Provider/process populated states** (G8 capture gaps): a fixture with an authenticated provider
     (metadata only) and a recorded worker process, so those sections render with data.
  6. Rendered evidence per surface, acceptance-matrix verdicts, commit/push, **Gate 9 relay**.
- **Known notes (carried)**: engine shutdown still needs the bounded kill (G10); a V1.3-migrated profile
  sees onboarding once (documented deviation); provider live calls rely on donor code.
- **Tests**: engine **358 passed + 10 subtests**; renderer build green; all packaged harnesses green.
  **Tests failing**: none. **Blocker**: none. **HARD STOP: no.**
- **Frozen-hash state**: 3/3 verified; `Kel Releases/` untouched. **Dogfood isolation**: intact.
- **Continuation safety**: safe (clean tree; no running processes).
