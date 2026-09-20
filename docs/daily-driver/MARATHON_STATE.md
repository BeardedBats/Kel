# MARATHON_STATE — Kel Daily Driver Expansion Marathon

Last updated: 2026-09-20 (**D3 landed and verified; D4 next**)

- MARATHON_MODE: ACTIVE — implementation marathon; no independent audit, no release, no freeze.
- LANE: branch `dev/daily-driver` · worktree `C:\Users\Nick\Desktop\Kel\kel-daily-driver`
- BASE SHA: `37b1f27faf02dfa5feb96449fc3768c0ec4e9692` (production tree == `6d957ee9…`; diff was records/evidence only)
- CURRENT HEAD: the D3 commit (see `git log --oneline`; prior checkpoints: `e4d4215`, wrong-layer revert `b13301a`)
- COMPLETED:
  - intake + lane open `3f83be7` (`1.7.0-dev` identity + durable state)
  - **D0 closed** — `9bdf338` (HVRA-MINOR-001) · `777fefe` (HVRA-MINOR-002) · `cce55d0` (HVRA-SUG-001) · `f594282` (HVRA-SUG-002) · records `288a53c`
  - **ENG-001** — engine claims re-pin `80c4ba2` (pre-existing red since the v1.6 repair; full engine suite now green)
  - **D1 core** — providers speak user language + Set up → Save + Verify `0279a1d`
  - **D2 core** — donor CDN update feed severed; fail-closed Kel GitHub check `7c9df63`
  - **D3 wrong-layer correction** — `33fbbeb` (gateway built on a wrong assumption) reverted in `b13301a`
  - **D3 core** — gateway session enforcement in the web-host + `/qr-login` proxy + real-browser verification (this commit)
- CURRENT PHASE: **D4 — Transcription first-class workflow**
  - Key truth (recorded so nobody re-learns it): the desktop app runs BOTH aioncore (UI/conversation backend the web-host proxies to; owns browser auth) and the Kel engine (main-process only, per-process bearer token). Remote enforcement belongs in the web-host gateway.
- NEXT QUEUE: D4 → D5 attention/notifications → D6 continuation → … → D19 (see `ROADMAP.md`)
- LATEST TESTS: desktop tsc exit 0 · Vitest 19 files / 187 PASS (10 new gateway tests) · engine 1019 OK (275.5s, unchanged) · D3 real-stack matrix green (anon 401 loopback+LAN+reset-password; authed 200; revoked replay 401; browser login→app; phone 390 overflow 0)
- LATEST PACKAGE: none yet — package phase pending; checklist ready in `PACKAGE_EVIDENCE.md`
- BLOCKERS: none
- UNAVAILABLE EXTERNAL CREDENTIALS: no provider keys in this environment; live provider validation impossible (fixture/local validation documented)
- DAILY-DRIVER CANDIDATE STATUS: NOT STARTED (implementation ongoing; reserved install/data roots recorded in RESUME.md)

## Rules in force

- Disk is durable state; update this file at every checkpoint. Do not rely on chat history.
- Protected refs (do not modify): `main`, `repair/v16-human-visual`, `repair/v16-final`, `audit/v16-human-visual-final`, `audit/v16-postrepair-final`, `audit/v16-final`, `ux/v15-journeys`, protected tags (`v1.2.0`…`v1.6.0-pre1`).
- No publishing, no release tag, no history rewrites. Development identity: `1.7.0-dev`.
- One lane: `dev/daily-driver`. Per-phase loop: understand → narrow design → implement → self-review → test → realistic journey → record → commit → continue.
