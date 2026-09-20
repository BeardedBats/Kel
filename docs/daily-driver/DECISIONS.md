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
  Remaining D8 (recorded, not silently dropped): the Kel Team page still exposes a Roster view with
  "Seed the default roster" — normal-user roster management is out of scope, so that view needs a
  decision (developer-only disclosure or removal), plus the D0/D1/D2/D3 selection/boundary evidence
  write-up.
- (append as work proceeds; every non-obvious choice gets a line)
