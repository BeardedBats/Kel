# DECISIONS — daily-driver marathon

- **D-001 — Lane.** New implementation lane `kel-daily-driver` / `dev/daily-driver`, based on
  `37b1f27` (newest verified corpus head; production tree equals `6d957ee9…`). Protected historical
  refs remain untouched; forward development only.
- **D-002 — Identity.** Development identity `1.7.0-dev` in `desktop/package.json` and
  `runtime/kel/__init__.py` (identity test pins both ends). No release tag; no publish.
- **D-003 — D0 placement.** The four final V1.6 residuals are repaired on the dev lane; audit IDs and
  commits recorded in `IMPLEMENTATION_STATUS.md`; no new audit campaign.
- **D-004 — Disk-first state.** `docs/daily-driver/` holds all durable marathon state;
  `MARATHON_STATE.md` is the canonical resume pointer.
- **D-005 — D0-001 approach.** Permissions joins `/api/state` jobs and shows the job's own request as
  the primary Work label (first line, ≤120 chars; fallback "Work item"); raw ids live only in a hover
  tooltip and an Advanced-only "Work references" table.
- **D-006 — D0-002 approach.** `desktop/package.json` `description` = `Kel` (builder derives the
  installer/uninstaller FileDescription from it); legal attribution untouched; packaged re-verify at
  package phase.
- **D-007 — D0-003 approach.** Donor ACP wiki link removed (not retargeted: no Kel help destination
  exists yet); unused i18n keys left in place to avoid generated-typing churn.
- **D-008 — D0-004 approach.** Duplicate-toast "finding" was a probe double-count artifact (Arco
  renders `.arco-message-content` inside `.arco-message`; the probe matched both). Behavior kept
  truthful; toast made idempotent with a stable message id.
- **D-009 — ENG-001 claims re-pin.** The v1.6 human-visual repair rewrote the permissions copy but the
  engine-side claim pin (`test_v141_claims`) was never updated, leaving the engine suite red since
  then (it had not been run on the repaired tree). The pin now follows the repaired shipped copy —
  same corrected claims, current wording.
- **D-010 — D1 approach.** Engine states are the truth; `providerStatus.ts` maps them to
  Available / Needs setup / Temporarily unavailable / Unavailable + reasons, and never upgrades a
  state. Per-card "Set up → Save + Verify" = OS-store write + engine credential metadata + read-back;
  it is not a live provider API call (no keys in this environment). The manual OS-store section is
  retained because `packaging/verify-credentials.cjs` drives it ("Store credential").
- **D-011 — D2 approach.** Kel ships with no update CDN: `updateFeed.buildCdnFeedOptions()` returns
  null and `autoUpdaterService` skips all electron-updater checks when no feed is configured (no
  donor infrastructure contact, no startup notification). The manual GitHub check
  (`BeardedBats/Kel`) remains the single source of truth and fails closed until Kel publishes release
  assets. Installer-based upgrades preserve user data by architecture; packaged upgrade verification
  is scheduled for the package phase. No cloud update service introduced.
- **D-012 — D3 course correction (wrong-layer gateway reverted).** The first D3a attempt (commit
  `33fbbeb`, reverted in `b13301a`) added a password/session gateway assuming the web-host proxies to
  the Kel engine with its bearer token. Repository truth: the shipped app bundles aioncore
  (`resources/bundled-aioncore/win32-x64`) and the web-host proxies to IT (`globalThis.__backendPort`);
  the Kel engine is reached only by the main process. The revert restored the donor auth stack
  untouched.
- **D-013 — D3 enforcement lives in the web-host gateway.** aioncore runs in local mode ("auth
  disabled") and never gated business routes: an anonymous LAN client could read conversations/
  settings AND invoke `POST /api/webui/reset-password` (admin takeover). The gateway is the only
  network boundary we own, so it now validates every proxied request against aioncore's own
  `/api/auth/user` (5s positive / 2s negative cache per cookie; logout invalidates immediately;
  fail-closed on transport errors). Anonymous allowlist: `/login`, `/logout`, `/qr-login`,
  `/api/auth/user|status|refresh`. `/qr-login` is now proxied to the backend (previously it fell
  through to the SPA and never reached aioncore). WS upgrades carry the same gate (validated while
  the peek listener keeps collecting so cleanup+splice stay in one tick — the pattern the splice code
  documents). No donor binary changes; desktop/CLI callers that talk to aioncore directly are
  unaffected.
- **D-014 — D4 approach.** The engine already owned a complete transcription family
  (`/api/transcription`: record/upload/live stream/combine/exports/folders/key) with the honest
  credential-free "Practice mode" as the no-key default; the page was feature-complete too. D4 adds
  the missing spec piece — client-side search over the one library (recents + folder children, no
  second store) — plus policy pins (`transcription-policy.test.ts`: no spacebar handler ever binds,
  Escape-only cancel; action wiring; download/copy/share affordances) and a live HTTP fixture flow
  (`packaging/verify-transcription-e2e.cjs`) proving the real service end to end. Text export
  downloads the loaded transcript locally; the engine's `export_text` stays available for other
  clients.
- **D-015 — D5 approach.** The attention model stays derived-only: D5 adds a `connection` kind sourced
  from the engine's provider statuses (`not_installed` / `installed_not_authenticated` = the "Needs
  setup" states), copy kept in user language ("A connection needs setup") and a Project-unbound,
  timestamp-less item so it sorts below live asks and fails closed under project filters. The
  needs-attention vocabulary ban drops `provider` (the Providers page has been a user-facing surface
  since D1; the item intentionally routes there). Notifications are transition-driven via a pure core
  (`attentionNotificationCore.ts`): first snapshot silent, meaningful kinds only
  (approval/input/permission/failure/review/connection + cleanly-finished work), 30-min per-item
  cooldown, 3 events per tick, and delivery through the existing `ipcBridge.notification.show`
  (window-focus + setting gating stays in the main process). Snooze/Later is deliberately NOT
  implemented: it would require a second state store the derived-only surface must not grow.
  Update/restart items are omitted because no authoritative renderer-visible restart flag exists
  (the update channel is closed in D2) — invented items are worse than none.
- **D-016 — D6 approach.** The engine already owned durable continuation (`Continuation.candidates`
  over READY/PAUSED/WAITING_RESOURCE/AWAITING_USER jobs and open milestones, project-scoped) and the
  recorded restore outcome (`restore-outcome.json`, PER-02). D6 stays derived-only: a pure
  `resumptionBrief.ts` (sections: failed restore first, needs-you reusing the D5 attention
  aggregator, finished VERIFIED work, stopped work, continuation candidates as human-gated
  "reply continue" lines, still-running, and a fresh successful restore) rendered by a
  self-contained `KelResumptionBrief.tsx` on the landing page above the provider notice; cap 3 per
  section, quiet when empty, actions only to surfaces that already own the follow-up. The brief
  never claims a "since you left" diff (no invented client state) — it reports durable truth as it
  stands. The restore freshness check accepts epoch seconds or milliseconds so the engine's unit
  cannot make it lie. `kelState`'s type now includes the `restore` field the engine always returned.
  Restart verification plants the engine's OWN restore-outcome file on a throwaway data dir and
  asserts a fresh process restores durable truth and surfaces it (`evidence/d6/`).
- **D-017 — D7 approach.** The engine side of long-running autonomy was already complete and pinned:
  `recover_expired` fences expired runs (run ORPHANED, milestone UNCERTAIN + the reconcile reason,
  job WAITING_RESOURCE/UNCERTAIN) and `test_v16_r6_liveness.py` pins "reconcile first, never
  auto-retried" plus late-result discarding; `test_v16_r3_retry_durability.py` pins durable milestone
  attempt budgets, the provider failure counter/circuit, and the automatic-resume refusal once
  exhausted; `wait_for_route`/`retry_route` carry the route reason and resume by themselves; approvals
  are human-gated by construction. D7 therefore changed only the human-facing classification: an
  orphaned run (WAITING_RESOURCE without `route_block`, with a recorded milestone reason) is now a
  Needs-Your-Attention item carrying the engine's own sentence, while a route-blocked job is
  explicitly NOT an interruption (it auto-resumes). The landing brief's "stopped" section is now
  deliberately-paused-only, keeps the engine reason when recorded, never duplicates a needs-you job
  (id-based dedupe against the attention items), and its summary counts are computed from the emitted
  lines so it cannot overstate. `KelWorkJob` gained `route_block` and milestone `error` in the client
  types (both were always returned by the engine).
- **D-018 — D8 slice 1 approach.** The engine's staffing ladder was already complete and pinned
  (`staffing.py`: TIERS D0–D4, feature vector + band ceilings, hard rules R1–R10 — security boundary
  ⇒ Sentinel mandatory/tier ≥ D2, irreversible or externally visible effect ⇒ approval + independent
  review/tier ≥ D2, no tier upgrade as a stall remedy; `decide()` records reasons; team assignments
  carry dispatch_tier/authority_max/budget_class; eight workforce test files pin the behaviour). The
  actual gap was the SURFACE: the Work page rendered a specialist table with internals (role version,
  snapshot digest, provider/model, budget meter, raw derived state). Slice 1 replaces it with plain
  language — `staffingLanguage.ts` (`staffingSummary` → "Kel is using an independent review.";
  `assignmentLine` → "An independent review: in progress/finished/waiting/stopped and needs a look",
  "Extra help: …"), with the human role name + update time kept as the support line and four test
  cases pinning the language and banning internals (tiers, digests, budgets, assignment ids).
  Remaining D8 was closed in D-019.
- **D-019 — D8 closure: Kel manages its own roster + the Team page is a developer surface.** (1) The
  engine now seeds shipped roles on first use: `Team.resolve_role` catches the missing-template
  PolicyError, seeds the defaults when the id is one of `SEED_ROLES` (idempotent by construction),
  and re-resolves; any other id still fails closed. A person never has to manage rosters, and the
  explicit `seed` action stays available for developer use. Pinned by two new `test_v14_team` cases
  (first-use seeding; unknown id refused) — roster self-seeding is a product behaviour, not a UI
  trick. (2) The Team page became a developer surface: the Office is the default and speaks plain
  staffing language (`staffingSummary` + `assignmentLine`); the Roster/Studio tabs, the internals
  columns (role version, provider/model, budget meter, raw state), the activity timeline, and the
  roster seed action sit behind a page-local "Developer view" toggle (per-session, not persisted —
  internals disclosure is deliberate, not a stored preference). Deep links still land on Office in
  normal mode. Pinned by `team-surface.test.ts` (toggle gate, effective-view switch, plain-language
  lines, exactly one seed label and it sits after the clean office empty state, engine comment +
  guard substring). (3) D0–D3 selection/boundary evidence: `python -m unittest discover -s tests -p
  "test_workforce_*.py"` → **277 tests OK** plus `test_v14_team` 19 OK.
- **D-020 — D9 approach.** The engine's proposal pipeline was already complete and pinned (queue →
  defer/accept/reject; acceptance applies through the same trust model as corrections; the previous
  value survives as superseded history; a rejected proposal never re-asks until its evidence
  changes; `/api/work` already returned the open queue). The gap was the human side: the client type
  did not declare the queue and the Knowledge surface could not decide on it. D9 therefore (1) types
  the always-returned queue (`KelMemoryProposal`) and extends `kelMemoryAction` with the three
  decision actions, (2) renders a "Kel suggests" review card in the Knowledge view — quiet when
  empty, user language ("nothing here applies by itself."), the engine's own `why`, and exactly
  three honest choices (Use this / Not now / No thanks), capped at 5 visible with a count line, and
  (3) proves the loop live over the shipped HTTP surface
  (`packaging/verify-learning-proposals.cjs`: nothing applied before a decision; defer keeps it
  queued; accept applies + preserves superseded history; reject never applies). The journey also
  exposed a real contract bug: `/api/work` passes the stored JSON column through as a string, so
  the client's `value?: Record<string, unknown>` was wrong — now `string | Record<string, unknown>`.
  No global "learnings inbox" was created; the review lives where the knowledge lives (Projects).
- **D-021 — D10 approach.** The recipe engine was complete *and unreachable*: `RecipeLibrary.save`
  (confirmation-gated) and `propose_from_job` (draft from a settled job) had no callers, and
  `/api/recipes` exposed only list/get/preview — the desktop Recipes tab could dry-run but never
  run. D10 therefore closed the loop with the existing primitives instead of new machinery:
  `propose_from_job` and `save` are now real HTTP actions (save passes `confirm` straight to the
  library, so the refusal message is the engine's own), the Recipes tab gained Run (submitting a
  normal job and pointing at the Work page), and the Work page gained Save as a recipe — draft
  first, save only on the explicit second click. Executing the previously-dead primitive exposed a
  real bug: `propose_from_job` copied milestone ids straight into step ids, but milestone ids are
  engine-internal and often shorter than the 3-char recipe slug floor (`m1`), so the draft failed
  its own validator for the engine's documented contract shape. Fixed by mapping ids to slugs and
  carrying the mapping through `depends_on`, with an engine regression test. Verified live over
  HTTP (`packaging/verify-recipe-loop.cjs`): nothing stored by the draft; save without confirmation
  refused; confirm persists; re-save idempotent; run + run-again accepted; the first run is a real
  job. No second workflow engine, no recipe marketplace, no scheduler.
- **D-022 — D11 approach.** Cross-device continuity needed the remote browser to reach Kel's own
  durable state — but the Kel engine is process-local to the desktop (per-process bearer token) and
  the remote browser only had the aioncore SPA + gateway. Rather than build a second state store or
  expose the engine on the network, the **desktop's own web-host became the Kel gateway**: `/kel/*`
  is session-gated by the same authority as every other gated route, the engine descriptor
  (`desktop-session.json`) is read per request from the app's data root, and the bearer token is
  attached server-side — the browser never sees it; the browser's aionui cookie is stripped before
  forwarding. The renderer's `call()` keeps one implementation for both worlds: preload bridge when
  present, otherwise `fetch('/kel' + route)`. Failure modes are honest (no engine → 503, dead →
  502). The real-stack journey proved the loop (anonymous refused → login → desktop-created work
  visible remotely → dead engine fails closed) and caught one nuance worth recording: the engine's
  state/work reads are GET-with-query (what the renderer actually uses), not POST actions, so the
  "Unknown action" 400 was the journey's mistake, not a gateway bug. Known limit: live Kel updates
  do not stream over the gateway yet (pages refresh on load; no second WebSocket path was
  invented).
- **D-023 — D12 approach.** The routing engine was already complete and honest: `router.select`
  applies deterministic hard filters (install/auth/capability/quota/circuit/privacy/quality floor),
  orders by known cost then latency then quota, and returns the selected provider, the ordered
  fallbacks, per-provider exclusion reasons, and explicit `unknown_cost`/`unknown_quota` flags.
  The gap was visibility: a *chosen* route was invisible to the user (only blocked routes surfaced,
  via D7). D12 therefore reuses what the engine already records — the `run.claimed` event carries
  the decision — and exposes it as a `routes` map on `/api/state` for **active** jobs only, which
  the Work page renders as one plain sentence: "Running on X — the cheapest eligible option", an
  honest fallback offer, and up to three skipped providers with reasons translated into user words
  ("its quota is used up", "its key is not set", …). Unknowns stay in the sentence ("its cost is not
  known yet") rather than being silently omitted; there is no new routing logic and no per-user
  tuning UI. The live journey also settled an honest rule: a cancel-pending job keeps advertising
  its route until it reaches a terminal state (the journey asserts exactly that rule, not blind
  disappearance). Working this phase surfaced a real bug in the D11 remote fallback — it POSTed
  every call, so bodyless reads (state/work/artifact) would have failed remotely with "Unknown
  action"; the fallback now GETs bodyless calls exactly like the preload bridge
  (`method: hasBody ? 'POST' : 'GET'`, pinned).
- **D-024 — D13 approach.** Failure recovery was already broad (D5 attention, D6 restart/resume, D7
  orphans/route blocks, D2 update path, D4 bounded transcription failures), but D11 introduced a new
  failure surface with no human voice: the remote gateway's machine codes. D13 therefore stays
  narrow and finishes the language: `kelApi.call` maps `KEL_ENGINE_UNAVAILABLE` ("Kel isn't running
  on the computer that serves this page right now…") and `KEL_ENGINE_UNREACHABLE` ("Kel stopped
  answering on that computer. Your work is kept — try again in a moment.") to sentences, treats a
  browser-level fetch failure as a device/network problem rather than an engine fault, and falls
  back to the engine's own message for unknown codes — a raw code can no longer surface as UI copy.
  The codes themselves are live-verified by the D11 journey (502/503 on a dead/missing engine); the
  translation layer is source-pinned. No new recovery machinery was invented; retry/reconciliation/
  resumability stay exactly where the earlier phases verified them.
- (append as work proceeds; every non-obvious choice gets a line)
