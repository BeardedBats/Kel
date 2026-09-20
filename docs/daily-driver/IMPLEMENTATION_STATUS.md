# IMPLEMENTATION STATUS — `dev/daily-driver`

Updated: 2026-09-20 (D0–D10 complete; D11 starting)

## Lane

- Worktree: `C:\Users\Nick\Desktop\Kel\kel-daily-driver` — branch `dev/daily-driver`.
- Base: `37b1f27faf02dfa5feb96449fc3768c0ec4e9692`; lane open `3f83be7` (`1.7.0-dev` identity + durable records).
- Protected refs untouched; no release tag; no publish.

## FINAL_V16_RESIDUAL_CLEANUP

Source audit: `audit/v16-human-visual-final` @ `554f79987399dae10e3b03ecf2a9b2c975c33961`
(production target `6d957ee9aad7200fb2fcff9b505e0771e2dfdcda`; 0 BLOCK / 0 MAJOR / 2 MINOR / 2 SUG).

| Audit ID | Item | Repair commit | Evidence |
| --- | --- | --- | --- |
| HVRA-MINOR-001 | Permissions Work column: raw engine job id shown | `9bdf338` | new `jobLabels.ts` + `job-labels.test.ts` (5 tests incl. page wiring pin); raw id moved to tooltip + Advanced "Work references" |
| HVRA-MINOR-002 | Installer/uninstaller FileDescription donor phrase | `777fefe` | `desktop/package.json` description → `Kel` (builder source of FileDescription); `donor-policy.test.ts` pin. Packaged Properties re-check deferred to package phase (PACKAGE_EVIDENCE checklist) |
| HVRA-SUG-001 | ACP setup help link → donor wiki | `cce55d0` | donor constant + "Setup guide" button removed from `LocalAgents.tsx`; no Kel help destination exists to retarget (repo home is not a setup guide) |
| HVRA-SUG-002 | Duplicate pet-refusal toast | `f594282` | Root cause: audit probe double-count artifact — `.arco-message, .arco-message-content` both match ONE toast (Arco Notice renders both nodes; campaign harness saw a single message). Refusal toast made idempotent via stable message id; truthful OFF-state sync untouched. Pin in `donor-policy.test.ts` |

## Environment notes

- External provider credentials: probed in D1 (recorded in KNOWN_LIMITATIONS.md when known).
- No public DNS / no external notification delivery assumed; fixtures + local validation where honest.

## Completed lanes since (summary)

- **D1** `0279a1d` — truthful provider states (Available / Needs setup / Temporarily unavailable /
  Unavailable), Set up → Save + Verify.
- **D2** `7c9df63` — donor update CDN severed; manual Kel GitHub check fails closed.
- **D3** (this commit) — Remote/WebUI: the shipped surface had no session enforcement on business APIs
  (anonymous LAN reads + anonymous `POST /api/webui/reset-password`); the web-host gateway now
  validate-gates everything against aioncore's `/api/auth/user` (allowlist: login/logout/qr-login/
  api-auth), proxies `/qr-login`, and gates WS upgrades. Verified with the real stack (raw boundary
  matrix + Playwright browser, `evidence/d3/`). Wrong first attempt reverted (`b13301a`).
- **D4** (this commit) — transcription verified live in practice mode
  (`packaging/verify-transcription-e2e.cjs` + `evidence/d4/`); searchable recents added client-side
  (one library, no second store); policy pins for the no-spacebar rule, action wiring, and
  downloads/copy/share affordances.
- **D5** (this commit) — Needs-Your-Attention gained the `connection` kind (provider setup needs,
  user language, routed to Providers, project-unbound, sorted below live asks) and the shell gained
  restrained transition-driven desktop notifications (silent first snapshot, meaningful kinds only,
  30-min cooldown, 3/tick, existing focus/setting gating). Snooze/Later omitted by design.
- **D6** (this commit) — "While you were away": a derived-only resumption brief on the landing page
  (failed restore first, needs-you, finished, stopped, go-ahead continuation lines, still-running,
  fresh restore) with 8 unit pins and a live restart/resume verification whose verdict is all-true
  (`evidence/d6/continuation-restart.json`). Continuation stays human-gated.
- **D7** (this commit) — long-running autonomy: the engine's orphan fencing / durable budgets /
  provider circuit / self-clearing route blocks were verified as already complete and pinned; the
  human side now classifies an orphaned run as needs-you (with the engine's own reason) while a
  route-blocked job stays auto-resuming, and the landing brief preserves reasons, dedupes, and
  reports counts from what it actually shows.
- **D8 complete** (slice 1 `daafd36`, closure this commit) — adaptive staffing: the engine ladder
  (D0–D4, hard rules, ceilings, 8 workforce files) was verified complete; the Work page's internals
  table was replaced with user language (`staffingLanguage.ts`, 4 pins); **the engine now seeds
  shipped roles on first use** (`Team.resolve_role`; idempotent; unknown ids fail closed; 2 new
  `test_v14_team` pins) so nobody manages rosters; **the Team page is a developer surface**
  (plain-language Office by default; Roster/Studio + internals + the seed action behind "Developer
  view"; `team-surface.test.ts` 3 pins). D0–D3 selection/boundary evidence: **277 workforce tests
  OK** + 19 team tests OK.
- **D9 complete** (this commit) — controlled learning promotion: the engine's proposal pipeline
  (queue → defer/accept/reject, trust-model application, superseded history) was already complete
  and pinned; the human surface was the gap, so `KelWork` now types the always-returned open queue,
  the Knowledge view renders a "Kel suggests" review card ("nothing here applies by itself.") with
  Use this / Not now / No thanks wired to `accept_proposal` / `defer_proposal` / `reject_proposal`,
  and a live HTTP journey proves the whole loop (`packaging/verify-learning-proposals.cjs`, verdict
  all-true, `evidence/d9/`). Found + fixed a real contract bug along the way: `/api/work` returns a
  record's `value` as a JSON string; the client type now matches reality.
- **D10 complete** (this commit) — recipes: the engine shipped `propose_from_job` (draft from a
  settled job) and a confirmation-gated `save`, but neither had a caller and `/api/recipes` exposed
  only list/get/preview. They are now real actions; the Recipes tab gained Run (submit → follow on
  the Work page); the Work page gained Save as a recipe (draft first, save on explicit confirm).
  Running the dead primitive exposed a real engine bug — short milestone ids (`m1`) are not valid
  recipe slugs — fixed by slug-mapping ids (depends_on included) with an engine regression test.
  Live HTTP journey all-true (`packaging/verify-recipe-loop.cjs`, `evidence/d10/`).
- **D11 complete** (this commit) — cross-device continuity: the web-host now proxies `/kel/*` to the
  Kel engine, session-gated by the same authority as everything else, with the engine bearer
  server-side only (descriptor read per request; no engine → 503, dead → 502; browser cookie
  stripped). The renderer falls back from the missing preload bridge to that gateway, so the same UI
  works away from the desktop; desktop app + dev CLI both wire the engine data root in. Real-stack
  journey all-green: real engine + real `bun run webui` (shipped aioncore) + login → a
  desktop-seeded job is visible to the remote session; the token never reaches the browser
  (`packaging/verify-remote-kel.cjs`, `evidence/d11/`).

## Next item

- **D12 — Smarter provider routing** (§26–27): verify what the engine already decides (task fit,
  health, cost where known, honest fallbacks) and close the smallest honest gap in the user's view.
