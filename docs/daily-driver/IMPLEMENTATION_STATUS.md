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
- **D12 complete** (this commit) — smarter provider routing: `router.select` was verified complete
  (eligible-cost-v1: hard filters with reasons, fallbacks, unknown cost/quota flags). The chosen
  route was invisible, so `/api/state` now exposes the `run.claimed` decision per active job and
  the Work page renders one plain sentence ("Running on X — the cheapest eligible option", a
  fallback offer, up to 3 skipped providers with translated reasons, honest unknowns). Also fixed a
  real D11 gap found here: the remote fallback always POSTed, so bodyless reads now GET like the
  preload bridge (pinned). Live journey all-green (`packaging/verify-route-transparency.cjs`,
  `evidence/d12/`).
- **D13 complete** (this commit) — failure recovery polish: the remote gateway's machine codes are
  now sentences in the user's view (`KEL_ENGINE_UNAVAILABLE` → "Kel isn't running on the computer
  that serves this page right now…"; `KEL_ENGINE_UNREACHABLE` → "Kel stopped answering on that
  computer. Your work is kept — try again in a moment."), a browser-level network drop reads as a
  device problem, and unknown codes fall back to the engine's own message — a raw code can no
  longer appear as UI copy. Engine full suite re-run green (1023 OK) after the D12 change.
- **D14 complete** (this commit) — the optional Activity view: a quiet `/activity` page composed
  entirely from existing state (Happening now with the routing sentence, Waiting on you with an Open
  Work link, Recently finished with plain verdicts, provider count). No internals — pinned. Work and
  Activity now share their sentences through `workLanguage.ts`, so they can never drift.
- **D15 complete** (this commit) — containment verified end to end (autonomy + boundary suites,
  ~20 pinned behaviours) and the one human-risk gap closed: the emergency stop is now two-step
  (arm → "Yes — stop everything" / "Keep going") with its effect spelled out, and the engine call
  exists only in the confirmed branch. Live journey all-green: lease ACTIVE → stop → REVOKED
  (`reason: emergency stop`), work PAUSED, forged `actor` refused by the engine itself
  (`packaging/verify-emergency-stop.cjs`, `evidence/d15/`).
- **D16 complete** (this commit) — live capability revision verified over HTTP, 9/9: revocation
  narrows the very next check (`lease-revoked`); a pending boundary request changes nothing; a user
  grant widens for one use only and does not stick. Real fix: an unknown boundary scope is now
  refused (`Unknown boundary scope`) instead of silently filing a grant that can never match
  (autonomy suite 32 OK; engine full suite 1025 OK). Permissions page states the rule in user
  language. Evidence `evidence/d16/live-revision.json`.
- **D17 complete** (this commit) — integrations overview: an Integrations card on the Providers page
  reads the engine's own capability inventory (`/api/capabilities`) and says Connected / Needs setup /
  Unavailable with the engine's reason, `In use`/`Off`, and Set up → Settings → Tools only where
  setup helps. Live journey all-green (`evidence/d17/integrations-overview.json`).

## Next item

- **Daily Driver marathon closed** (D19 · fresh package · installed candidate — see
  `DAILY_DRIVER_CANDIDATE.md`), then **V2.0 preflight: Fix Capture** (separate tranche) — shipped; see
  `FIX_CAPTURE.md`. The rest of V2.0 is deliberately not started.

## V2.0 preflight — Fix Capture (complete)

- **Engine** (`8ce902b`): `runtime/kel/dogfood.py` (migration 22) owns the fix store and the files
  under the engine data root (`dogfood/screenshots/FIX-0001.png`, `dogfood/tmp/`, `dogfood/prompts/`),
  and `/api/dogfood` (list/get/save/set_status/prepare_prompt) follows the family contract — plain
  sentences, a GET read for the list. `prepare_prompt` writes the prompt file first and only then
  marks the included OPEN fixes BATCHED. 21 engine tests.
- **Desktop** (`5bd820e`): Ctrl+Shift+F opens a transparent selection overlay (hit-testing finds the
  real element, the click is swallowed), the target is captured with its context and a window
  screenshot from the main process, and Kel's own transcription family drives the live transcript.
  The floating panel records, reviews, records again or saves beside the target; Esc, click-outside
  and a second hotkey press behave exactly as promised in `fixCaptureMachine.ts`. `/dogfood` reviews
  the fixes, changes status, and prepares/copies/reveals the fix prompt. 32 desktop tests.
- **Installed journeys A–E** ran against the packaged candidate with Chromium's synthetic microphone
  (this machine has none) and the engine's practice transcription provider: save → restart → still
  there; Record Again; click-outside cancel; three fixes → one prompt → Batched; screenshot + target
  box verified against the real element. Evidence `evidence/fix-capture/installed-journeys.json`.
- **Not an issue tracker, by construction**: four statuses and a schema pin that there are no
  tracking fields (engine test) plus a desktop pin on the tracking vocabulary.
