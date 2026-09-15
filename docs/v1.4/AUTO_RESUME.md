# KEL V1.4 — AUTO-RESUME

Updated: 2026-09-15 ~18:30 ET · Session: #6 (Gate 7 in progress; no blocker)

- **Current gate**: Gate 7 — **IN PROGRESS** (desktop productization). Gates 0–6 are CLOSED
  (reviewer-relay CONTINUE each).
- **Done in Gate 7** (commits `deeec99`, `bcdaf72`, `4ca8172`, `5efc1de`, `e03e46e`, `10b66e2`, `cf4b7a1`, `32155be`, `9dcf3ea`, `7fbb9af`):
  1. **Dead navigation repaired** — donor settings routes now land on real Kel surfaces.
  2. **Contrast 6 → 0** at the source; **focus rings 0/30 → 30/30**; skip link proven as the first tab
     stop on a fresh load.
  3. **Command palette** (`Ctrl+K`, `/`) with 24 engine-derived results, keyboard-only verified.
  4. **Pet surface tokenized + audited** for the first time (muted tone, 12px floor, reduced-motion).
  5. **First-run onboarding flow** implemented and rendered (`#/onboarding`: “Set up Kel · Step 1 of 5 ·
     Welcome”, providers from `/api/providers`, project from `/api/state`, locked guardrails from
     `/api/autonomy`, Skip setup, completion flag `kel.onboardingCompleted_v1`), with the **automatic
     trigger verified end-to-end** (`verify-onboarding.cjs` exit 0: fresh → onboarding → finish →
     `/work`; second launch skipped).
- **Open Gate 7 items** (precise):
  1. **Pet live capture** (optional): needs `app.windows()` handling in the harness.
  2. **Recorded deviation — migrated profiles see onboarding once**: the gate is flag-only because the
     donor keeps a default conversation on a brand-new profile, so a conversation count cannot detect a
     fresh install. A stricter rule needs a renderer-readable “previous install” signal (e.g. the
     migration's local config file) exposed to the renderer; the flow is dismissible in one click
     (“Skip setup”), so the impact is small and bounded.
  3. **G9 carry-overs**: donor drawer `DIV`-tabs, unused lazy imports in `Router.tsx`, donor CSS
     gradient/cream findings from the design review.
- **Resolved in Gate 7**: Sider duplicate label (donor `conversation.projectsSection`
  `Projects` → `Project conversations`; rendered text now holds exactly one “Projects” token) and the
  notification restraint question (verified in code: turn-finish only, main process decides, suppressed
  while focused, setting respected, click navigates back).
- **PROVEN UI VERIFICATION LOOP**: build (`bun x electron-vite build --config
  packages/desktop/electron.vite.config.ts`) → overlay `desktop/out` into
  `dev-tools/runs/v14/shell-stage/out` → `asar-dedup-pack.js` → copy the asar into
  `dev-tools/runs/v14/candidate/resources/app.asar` → engine changes: `scripts/build-runtime.ps1` +
  `verify_engine_pyz.py` (`RESULT: OK`) + replace `resources/kel-engine` → `seed_ui_fixture.py` →
  capture (`capture-screens.cjs --views`) → probe (`a11y-probe.cjs --routes`) → interactions
  (`verify-actions.cjs`, `verify-credentials.cjs`, `verify-palette.cjs`, `probe-skip-link.cjs`) →
  confirm 0 leftover `Kel`/`electron` processes.
  Env: `PLAYWRIGHT_MODULE=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/node_modules/playwright`,
  `PLAYWRIGHT_BROWSERS_PATH=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/browsers`. Fixture root
  `dev-tools/runs/v13/data/fixture-team`.
- **Known notes (carried)**: engine shutdown needs the bounded kill (G7/G10); dark mode, dense states and
  before/after comparison images pending (G9); provider live calls rely on donor code.
- **Branch / commit / remote**: `v1.4-dev` @ `10b66e2` (+ this docs commit) · pushed to `origin`.
- **Tests**: engine **346 passed + 10 subtests**; renderer build green; packaged captures/probes/
  interactions green. **Tests failing**: none.
- **Blocker**: none. **HARD STOP: no.**
- **Frozen-hash state**: 3/3 verified; `Kel Releases/` untouched. **Dogfood isolation**: intact.
- **Continuation safety**: safe (clean tree apart from untracked `Agents.md`; no running processes).
