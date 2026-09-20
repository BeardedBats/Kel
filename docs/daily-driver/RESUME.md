# RESUME — how to continue this marathon (disk-first)

**Restore the entire marathon by reading exactly three files, in this order:**

1. `MARATHON_DIRECTIVE.md` — the complete governing program (D3–D19, package, install, durable-state and
   testing rules, out-of-scope list, return/end-state rules, final response format).
2. `MARATHON_STATE.md` — the live checkpoint: HEAD, current phase, current item, exact next action,
   completed phases, latest test state, remaining queue.
3. `RESUME.md` (this file) — how to run it: commands, package/install roots, crash discipline, never-rules.

Deeper records (read only when auditing a specific phase): `IMPLEMENTATION_STATUS.md`, `FEATURE_LEDGER.md`,
`DECISIONS.md`, `TEST_EVIDENCE.md`, `PACKAGE_EVIDENCE.md`, `KNOWN_LIMITATIONS.md`, `DOGFOOD_JOURNEYS.md`,
`ROADMAP.md`.

## Checkpoint (2026-09-20)

- D0 residuals CLOSED (`9bdf338`, `777fefe`, `cce55d0`, `f594282`; records `288a53c`).
- Engine claims re-pin done (`80c4ba2`) — full engine suite green (1019 OK).
- D1 providers core done (`0279a1d`) — tsc 0, Vitest 18/177.
- D2 update path done (`7c9df63`) — donor CDN severed, fail-closed Kel GitHub check.
- **D3 Remote/WebUI done (this commit).** Architecture truth: the desktop app runs BOTH aioncore
  (the UI/conversation backend the web-host proxies to — its own cookie auth is the browser
  boundary) and the Kel engine (main-process only, per-process bearer token). The shipped remote
  surface's hole: aioncore runs in local mode and never gated business routes, so any LAN client
  could read data AND call `POST /api/webui/reset-password` anonymously. Fix = session enforcement
  inside the web-host gateway (validate against `/api/auth/user`; 5s positive / 2s negative cache;
  invalidate on logout; anonymous allowlist only: /login /logout /qr-login /api/auth/*;
  `/qr-login` now proxied; WS upgrades validated). Verified against the real stack: anon → 401
  (loopback + LAN + reset-password), authed → 200, revoked replay → 401, browser login → app,
  phone 390 no overflow. Evidence: `evidence/d3/` + TEST_EVIDENCE rows.
- **D4 Transcription done (this commit).** The engine family (`/api/transcription`) and the page were
  already complete; D4 added searchable recents (client-side, one library), policy pins
  (`transcription-policy.test.ts` — no spacebar handler, Escape-only cancel, action wiring,
  affordances) and a live HTTP fixture flow (`packaging/verify-transcription-e2e.cjs`, practice
  mode): stream 4.6s → text; upload → combine (8.8s, source consumed); exports (485 chars / 403 KB);
  folders create/rename/assign/unassign; key set → `muse` / clear → `fixture`; plain-language errors.
- **D5 Needs-Your-Attention + notifications done (this commit).** Added the `connection` kind
  (provider setup needs, user language, routed to Providers, project-unbound) and a transition-only
  notification core + hook (`attentionNotificationCore.ts`, `useKelAttentionNotification`) wired into
  the shell: silent first snapshot, meaningful kinds only, 30-min per-item cooldown, 3 events/tick,
  delivery via the existing notification bridge (focus + setting gating unchanged). Snooze/Later
  intentionally absent (would grow a second state store).
- **D6 Continuation / resumability done (this commit).** The engine already owned durable
  continuation (`Continuation.candidates` over job states READY/PAUSED/WAITING_RESOURCE/
  AWAITING_USER + open milestones, project-scoped) and the recorded restore outcome
  (`restore-outcome.json`, audit PER-02). D6 adds the human side: a derived-only "While you were
  away" brief on the landing page (`resumptionBrief.ts` + `KelResumptionBrief.tsx`, above the
  provider notice) covering failed restores, what needs you (reusing the attention aggregator),
  what finished, what stopped, what waits for your go-ahead (continuation candidates, reply
  "continue" — Kel never auto-resumes), what is still running, and a fresh successful restore.
  Cap 3 per section, quiet when empty, real actions only. Verified live: engine restart on the same
  data dir → fresh pid, stable version, durable counts stable, planted restore-outcome surfaced
  (`evidence/d6/continuation-restart.json`, verdict all true).
- **D7 Long-running autonomy done (this commit).** The engine basis was already complete and pinned
  (orphan fencing with reconcile-first/never-auto-retry, durable attempt budgets, provider circuit,
  automatic-resume refusal when exhausted, route blocks that clear themselves). D7 changed the
  human-facing classification: an orphaned run (WAITING_RESOURCE without `route_block`, with a
  recorded milestone reason) is now a Needs-Your-Attention item carrying the engine's own sentence,
  while a route-blocked job is explicitly not an interruption. The landing brief's "stopped"
  section is paused-only, keeps engine reasons, dedupes against needs-you items, and its summary
  counts come from the emitted lines. `KelWorkJob` gained `route_block` + milestone `error` in the
  client types (always returned by the engine).
- **D8 done (this commit).** Adaptive staffing: the engine ladder (D0–D4 tiers, hard rules, band
  ceilings; eight workforce files) was verified complete and pinned. Slice 1 put the Work page in
  user language (`staffingLanguage.ts` — "Kel is using an independent review."). Slice 2 closed the
  remaining items: **Kel now manages its own roster** — `Team.resolve_role` seeds shipped roles on
  first use (idempotent; unknown ids still fail closed; pinned in `test_v14_team`), so no normal
  surface ever asks a person to seed roles — and the **Team page became a developer surface**
  (Office in plain language by default; Roster/Studio tabs, internals columns, and the roster seed
  action sit behind a "Developer view" toggle; `team-surface.test.ts` pins the gate, the language,
  and the seed-leak ban). D0–D3 selection/boundary evidence recorded: **277 workforce tests OK**
  (`python -m unittest discover -s tests -p "test_workforce_*.py"`) + 19 team tests OK.
- **D9 done (this commit).** Controlled learning promotion: the engine's proposal pipeline was already
  complete; the human side was missing. The open queue is now typed and the Knowledge view renders a
  "Kel suggests" review card ("nothing here applies by itself.", Use this / Not now / No thanks →
  accept/defer/reject_proposal, 5-visible cap). Live HTTP journey all-true
  (`packaging/verify-learning-proposals.cjs` + `evidence/d9/`); found + fixed a real contract bug
  (`/api/work` returns record `value` as a JSON string — the client type now matches).
- **D10 done (this commit).** Recipes: `propose_from_job` (draft from a settled job, preview only)
  and the confirmation-gated `save` are now HTTP actions; Run on the Recipes tab (submit → follow on
  the Work page); Save as a recipe on the Work page (draft → explicit confirm). Fixed a real engine
  bug the dead primitive had: short milestone ids (`m1`) failed recipe-slug validation — now mapped
  (depends_on included) + pinned. Live HTTP journey all-true (`packaging/verify-recipe-loop.cjs` +
  `evidence/d10/`).
- **D11 done (this commit).** Cross-device continuity: the web-host gained a session-gated `/kel`
  gateway to the Kel engine (bearer stays server-side; browser cookie stripped; 503/502 fail-closed);
  the renderer falls back from the missing preload bridge to it, so one UI works remotely; desktop
  app + dev CLI wire the engine data root in. Real-stack journey all-green
  (`packaging/verify-remote-kel.cjs` + `evidence/d11/`).
- **D12 done (this commit).** Smarter provider routing: the chosen route is now visible — `/api/state`
  exposes the engine's `run.claimed` decision per active job, and the Work page renders one plain
  sentence (cheapest-eligible reasoning, fallback offer, up to 3 skipped providers with translated
  reasons, honest unknowns). Fixed a real D11 gap found here: bodyless reads over the remote
  gateway now GET (bridge semantics). Live journey all-green
  (`packaging/verify-route-transparency.cjs` + `evidence/d12/`).
- **D13 done (D12+D13 commit).** Failure recovery polish: the remote gateway's machine codes are now
  sentences (`KEL_ENGINE_UNAVAILABLE` / `KEL_ENGINE_UNREACHABLE`), a browser-level network drop
  reads as a device problem, unknown codes fall back to the engine's message — no raw code as UI
  copy. Codes live-verified in D11; language layer source-pinned. Engine suite re-run green
  (1023 OK).
- **D14 done (this commit).** Optional Activity view: new `/activity` page (sider entry) composed from
  existing state only — Happening now (routing sentence included), Waiting on you (Open Work),
  Recently finished (plain verdicts), provider count; internals banned by pin. Shared
  `workLanguage.ts` keeps Work and Activity sentences identical. tsc 0 · Vitest 30 files / 249 PASS.
- **D15 done (this commit).** Security/containment verified end to end (existing suites, ~20 pinned
  behaviours) and the emergency stop made deliberate: arm → confirm ("Yes — stop everything") with
  the effect spelled out; the engine call exists only in the confirmed branch. Live journey
  all-green: lease ACTIVE → stop → REVOKED (`reason: emergency stop`), work PAUSED, forged `actor`
  refused by the engine itself (`packaging/verify-emergency-stop.cjs` + `evidence/d15/`).
- **Next: D16 — live capability revision** (directive §32).

## Where

- Worktree: `C:\Users\Nick\Desktop\Kel\kel-daily-driver` · branch `dev/daily-driver`.
- Current HEAD is recorded in `MARATHON_STATE.md`.

## How to continue

1. `cd /c/Users/Nick/Desktop/Kel/kel-daily-driver` and `git status` + `git log --oneline -10`
   (confirm clean tree and the latest checkpoint).
2. Open `MARATHON_DIRECTIVE.md` (the program), then `MARATHON_STATE.md`; continue from
   **CURRENT PHASE** / **CURRENT ITEM** / **EXACT NEXT ACTION**.
3. Follow the per-phase loop; record evidence; commit; continue.

## Commands

- Install deps (once per worktree): `cd desktop && bun install`
- Full unit suite: `cd desktop && bunx vitest run`
- Typecheck: `cd desktop && bunx tsc --noEmit`
- Engine tests: `cd runtime && python -m unittest discover -s tests`
- Web-host tests are part of the desktop vitest run (`packages/web-host/src/*.test.ts`).

## Package / install (final phases)

- Candidate install: `C:\Users\Nick\KelDailyDriverCandidate`
- Candidate data root: `C:\Users\Nick\KelDailyDriverRuns\prepared`
- Do **not** overwrite preserved audit/release-candidate installations.

## Never

- Touch protected refs (`main`, `repair/*`, `audit/*`, `ux/v15-journeys`, tags).
- Publish, tag a release, rewrite history, or start another audit campaign.
- Stop after one feature/suite/package — continue the queue.
