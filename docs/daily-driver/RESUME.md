# RESUME — how to continue this marathon (disk-first)

Read order: `MARATHON_STATE.md` → this file → `IMPLEMENTATION_STATUS.md` → `FEATURE_LEDGER.md`.

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
- **NEXT: D6 — Continuation / resumability** (§14–15). Start from `state.continuation` and the
  existing resume/retry touch points (Work/GUID/Needs-Attention actions); make reopening Kel
  effortless with real actions only; test restart during active work.

## Where

- Worktree: `C:\Users\Nick\Desktop\Kel\kel-daily-driver` · branch `dev/daily-driver`.
- Current HEAD is recorded in `MARATHON_STATE.md`.

## How to continue

1. `cd /c/Users/Nick/Desktop/Kel/kel-daily-driver` and `git status` + `git log --oneline -10`
   (confirm clean tree and the latest checkpoint).
2. Open `MARATHON_STATE.md`; continue from **CURRENT PHASE** / **NEXT QUEUE**.
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
