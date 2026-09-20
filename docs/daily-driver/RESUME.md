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
- **NEXT: D4 — Transcription first-class workflow** (§11). Start with the transcription page and
  the engine's transcription routes; preserve "NO spacebar start/stop shortcut".

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
