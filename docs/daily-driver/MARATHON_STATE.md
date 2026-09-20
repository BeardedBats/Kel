# MARATHON_STATE — Kel Daily Driver Expansion Marathon

Last updated: 2026-09-20 (**D3–D9 landed and verified; D10 in progress**)

- MARATHON_MODE: ACTIVE — implementation marathon; no independent audit, no release, no freeze.
- LANE: branch `dev/daily-driver` · worktree `C:\Users\Nick\Desktop\Kel\kel-daily-driver`
- directive: `docs/daily-driver/MARATHON_DIRECTIVE.md` — the complete governing program (D3–D19, package, install). Read it before acting; it outranks chat history.
- BASE SHA: `37b1f27faf02dfa5feb96449fc3768c0ec4e9692` (production tree == `6d957ee9…`; diff was records/evidence only)
- CURRENT HEAD: the D9 commit (see `git log --oneline`; prior: `82ff501` (D8 closure), `daafd36` (D8 slice 1), `1374fcd` (D7), `43cf675` (D6), `a8c27ba` (directive), `dde6c1e` (D5), `e57d4a3` (D4), `78d8f1d` (D3), `b13301a`, `e4d4215`)
- COMPLETED:
  - intake + lane open `3f83be7` (`1.7.0-dev` identity + durable state)
  - **D0 closed** — `9bdf338` (HVRA-MINOR-001) · `777fefe` (HVRA-MINOR-002) · `cce55d0` (HVRA-SUG-001) · `f594282` (HVRA-SUG-002) · records `288a53c`
  - **ENG-001** — engine claims re-pin `80c4ba2` (pre-existing red since the v1.6 repair; full engine suite now green)
  - **D1 core** — providers speak user language + Set up → Save + Verify `0279a1d`
  - **D2 core** — donor CDN update feed severed; fail-closed Kel GitHub check `7c9df63`
  - **D3 wrong-layer correction** — `33fbbeb` (gateway built on a wrong assumption) reverted in `b13301a`
  - **D3 core** — gateway session enforcement in the web-host + `/qr-login` proxy + real-browser verification `78d8f1d`
  - **D4 core** — transcription verified live (practice mode) + searchable recents + policy pins `e57d4a3`
  - **D5 core** — connection setup needs in the attention surface + restrained transition-driven notifications `dde6c1e`
  - **D6 core** — "While you were away" resumption brief on the landing page + live restart/resume verification `43cf675`
  - **D7 core** — orphaned runs reach Needs Your Attention with the engine's own reason; route-blocked jobs stay auto-resuming; brief reasons preserved + dedupe `1374fcd`
  - **D8 slice 1** — Work page speaks staffing in user language; engine ladder verified complete + pinned `daafd36`
  - **D8 closure** — Kel manages its own roster (seed-on-first-use; unknown ids fail closed, pinned); Team page is a developer surface; D0–D3 evidence = 277 workforce tests OK `82ff501`
  - **D9 core** — controlled learning promotion: open proposal queue typed + "Kel suggests" review card (Use this / Not now / No thanks → accept/defer/reject) + live HTTP loop verdict all-true (`packaging/verify-learning-proposals.cjs`, `evidence/d9/`); fixed a real contract bug (`/api/work` record `value` is a JSON string) (this commit)
- COMPLETED PHASES: intake/lane-open · D0 · ENG-001 · D1 · D2 · D3 · D4 · D5 · D6 · D7 · D8 · D9 (all committed, tree clean).
- CURRENT PHASE: **D10 — Recipes** (`MARATHON_DIRECTIVE.md` §D10) — starting recon.
- CURRENT ITEM: D10 recon — map the recipe library (`runtime/kel/recipes.py`: capture/entries/preview/compile) and its human surface (`pages/kel/projects` Recipes tab), then close the smallest honest gap without inventing a second workflow engine.
- EXACT NEXT ACTION: `fast_context` (or precise greps) over `runtime/kel/recipes.py` + `/api/recipes` (`service.py`) + the Recipes tab + recipe tests; decide and implement the increment.
- REMAINING QUEUE: D10 Recipes → D11 cross-device → D12 provider routing → D13 failure recovery → D14 Advanced Activity → D15 security/containment → D16 live capability revision → D17 integration/dev surface → D18 dogfood journeys → D19 full regression → fresh package → installed candidate + final battery. (`ROADMAP.md` keeps the compact table.)
- LATEST TESTS: desktop tsc exit 0 · Vitest 25 files / 227 PASS · engine 1019 OK (full suite, last full run) + 277 workforce tests OK in isolation · D3 real-stack matrix green · D4 live transcription E2E green · D5 transition-core green · D6 live restart/resume all-true · D7 orphan/route-block classification green · D8 staffing-language + team-surface pins green · D9 learning-proposal pins 5 PASS + live HTTP loop all-true
- LATEST PACKAGE: none yet — package phase pending; checklist ready in `PACKAGE_EVIDENCE.md`
- BLOCKERS: none
- UNAVAILABLE EXTERNAL CREDENTIALS: no provider keys in this environment; live provider validation impossible (fixture/local validation documented)
- DAILY-DRIVER CANDIDATE STATUS: NOT STARTED (implementation ongoing; reserved install/data roots recorded in RESUME.md)

## Rules in force

- Disk is durable state; update this file at every checkpoint. Do not rely on chat history.
- Protected refs (do not modify): `main`, `repair/v16-human-visual`, `repair/v16-final`, `audit/v16-human-visual-final`, `audit/v16-postrepair-final`, `audit/v16-final`, `ux/v15-journeys`, protected tags (`v1.2.0`…`v1.6.0-pre1`).
- No publishing, no release tag, no history rewrites. Development identity: `1.7.0-dev`.
- One lane: `dev/daily-driver`. Per-phase loop: understand → narrow design → implement → self-review → test → realistic journey → record → commit → continue.
