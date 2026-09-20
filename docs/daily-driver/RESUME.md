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
- **D8 slice 1 landed (this commit); D8 continues.** The engine's staffing ladder was already
  complete and pinned (`staffing.py` TIERS D0–D4 + hard rules + band ceilings + reasons; assignments
  carry dispatch_tier/authority_max/budget_class; eight workforce test files). The gap was the
  surface: the Work page showed a specialist table with role versions, digests, provider/model and
  budget meters. It now speaks user language via `staffingLanguage.ts` ("Kel is using an independent
  review." / "An independent review: in progress|finished|waiting|stopped and needs a look" /
  "Extra help: …"), pins in `staffing-language.test.ts`.
- **D8 remaining (exact next action):** (a) the Kel Team page still exposes a Roster view with "Seed
  the default roster" — normal-user roster management is out of scope, so decide developer-only
  disclosure vs removal (`pages/kel/team/index.tsx` view switch + seeding action); (b) write the
  D0/D1/D2/D3 selection/boundary evidence against `staffing.py` + the workforce test files. Then D9
  (learning promotion).

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
