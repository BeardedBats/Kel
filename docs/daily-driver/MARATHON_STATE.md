# MARATHON_STATE — Kel Daily Driver Expansion Marathon

Last updated: 2026-09-20 (**D3–D17 landed and verified; D18 in progress**)

- MARATHON_MODE: ACTIVE — implementation marathon; no independent audit, no release, no freeze.
- LANE: branch `dev/daily-driver` · worktree `C:\Users\Nick\Desktop\Kel\kel-daily-driver`
- directive: `docs/daily-driver/MARATHON_DIRECTIVE.md` — the complete governing program (D3–D19, package, install). Read it before acting; it outranks chat history.
- BASE SHA: `37b1f27faf02dfa5feb96449fc3768c0ec4e9692` (production tree == `6d957ee9…`; diff was records/evidence only)
- CURRENT HEAD: the D16+D17 commit (see `git log --oneline`; prior: `8b67cdf` (D15), `1ca5eb7` (D14), `879804e` (D12+D13), `242f4b8` (D11), `9c35f66` (D10), `6493275` (D9), `82ff501` (D8 closure), `daafd36` (D8 slice 1), `1374fcd` (D7), `43cf675` (D6), `a8c27ba` (directive), `dde6c1e` (D5), `e57d4a3` (D4), `78d8f1d` (D3))
- COMPLETED:
  - intake + lane open `3f83be7` (`1.7.0-dev` identity + durable state)
  - **D0 closed** — `9bdf338` · `777fefe` · `cce55d0` · `f594282` · records `288a53c` (all four V1.6 residuals)
  - **ENG-001** — engine claims re-pin `80c4ba2`
  - **D1 core** — providers speak user language + Set up → Save + Verify `0279a1d`
  - **D2 core** — donor CDN update feed severed; fail-closed Kel GitHub check `7c9df63`
  - **D3 core** — gateway session enforcement in the web-host + `/qr-login` proxy + real-browser verification `78d8f1d` (wrong-layer attempt `33fbbeb` reverted in `b13301a`)
  - **D4 core** — transcription verified live + searchable recents + policy pins `e57d4a3`
  - **D5 core** — connection setup needs in attention + restrained transition-driven notifications `dde6c1e`
  - **D6 core** — "While you were away" resumption brief + live restart/resume verification `43cf675`
  - **D7 core** — orphaned runs reach Needs Your Attention with the engine's reason; route-blocked jobs stay auto-resuming `1374fcd`
  - **D8** — Work page speaks plain staffing language (`daafd36`); Kel manages its own roster (seed-on-first-use + pins) and the Team page became a developer surface (`82ff501`); D0–D3 evidence 277 workforce tests OK
  - **D9 core** — controlled learning promotion: typed proposal queue + "Kel suggests" review (accept/not now/no) + live HTTP loop all-true; fixed the record `value` contract bug `6493275`
  - **D10 core** — recipes: `propose_from_job` + confirmation-gated `save` on the HTTP surface; Run in Recipes; Save-as-a-recipe on Work; fixed the short-milestone-id bug in `propose_from_job`; journey all-true `9c35f66`
  - **D11 core** — cross-device continuity: session-gated `/kel` gateway on the web-host (bearer server-side; cookie stripped; 503/502 fail-closed), renderer bridge fallback, both launchers wired; real-stack journey all-green `242f4b8`
  - **D12 core** — routing transparency: `/api/state` exposes the engine's `run.claimed` decision per active job; Work page renders one plain sentence; fixed the D11 bodyless-GET gap; live journey all-green `879804e`
  - **D13 core** — remote failure language: gateway codes become sentences; network drops read as device problems; raw codes can no longer surface as UI copy `879804e`
  - **D14 core** — optional Activity view: quiet `/activity` page composed from existing state; internals banned by pin; shared `workLanguage.ts` keeps Work and Activity sentences identical `1ca5eb7`
  - **D15 core** — containment verified end to end (~20 pinned autonomy/boundary behaviours) + emergency stop made deliberate (arm → confirm; engine call only in the confirmed branch); live journey all-green `8b67cdf`
  - **D16 core** — live capability revision verified over HTTP 9/9 (revocation narrows the next check; pending requests change nothing; one-time grants do not stick); fixed the silent dead-grant bug (unknown boundary scope now refused); autonomy 32 OK, engine full suite 1025 OK (this commit)
  - **D17 core** — integrations overview on Providers from the engine's own capability inventory (Connected / Needs setup / Unavailable + reason; Set up → Settings → Tools); live journey all-green (this commit)
- COMPLETED PHASES: intake/lane-open · D0 · ENG-001 · D1 · D2 · D3 · D4 · D5 · D6 · D7 · D8 · D9 · D10 · D11 · D12 · D13 · D14 · D15 · D16 · D17 (all committed, tree clean).
- CURRENT PHASE: **D18 — Synthetic daily-driver dogfood journeys** (`MARATHON_DIRECTIVE.md` §D18) — journeys recorded, continuation open.
- CURRENT ITEM: D18 — all ten journeys are recorded in `DOGFOOD_JOURNEYS.md` (6 live, 3 engine-live/partial needing a provider key, 1 pinned); the friction ledger's ten fixes are committed. Remaining: complete journeys 1–3 wherever a provider key exists and re-run the battery on the installed candidate (package phase).
- EXACT NEXT ACTION: proceed to **D19 — full regression → fresh package → installed candidate** (`MARATHON_DIRECTIVE.md` §39–42); re-run every suite, build the installer, install to `C:\Users\Nick\KelDailyDriverCandidate`, and run the installed battery. D18 stays open for the provider-dependent journeys in the same pass.
- REMAINING QUEUE: D18 dogfood journeys → D19 full regression → fresh package → installed candidate + final battery. (`ROADMAP.md` keeps the compact table.)
- LATEST TESTS: desktop tsc exit 0 · Vitest 33 files / 258 PASS · engine **1025 OK** (full suite, post-D16) · D3 real-stack matrix green · D4 live transcription E2E green · D5 transition-core green · D6 live restart/resume all-true · D7 orphan/route-block classification green · D8 staffing + team pins green · D9 learning pins + live loop all-true · D10 recipe pins + live loop all-true · D11 gateway + pins + real-stack journey all-green · D12 route pins + engine suite + live journey all-green · D13 failure-language pins green · D14 activity pins green · D15 pins + live journey all-green · D16 autonomy 32 + pins + live journey 9/9 + engine 1025 OK · D17 pins + live journey all-green
- LATEST PACKAGE: none yet — package phase pending; checklist ready in `PACKAGE_EVIDENCE.md`
- BLOCKERS: none
- UNAVAILABLE EXTERNAL CREDENTIALS: no provider keys in this environment; live provider validation impossible (fixture/local validation documented)
- DAILY-DRIVER CANDIDATE STATUS: NOT STARTED (implementation ongoing; reserved install/data roots recorded in RESUME.md)

## Rules in force

- Disk is durable state; update this file at every checkpoint. Do not rely on chat history.
- Protected refs (do not modify): `main`, `repair/v16-human-visual`, `repair/v16-final`, `audit/v16-human-visual-final`, `audit/v16-postrepair-final`, `audit/v16-final`, `ux/v15-journeys`, protected tags (`v1.2.0`…`v1.6.0-pre1`).
- No publishing, no release tag, no history rewrites. Development identity: `1.7.0-dev`.
- One lane: `dev/daily-driver`. Per-phase loop: understand → narrow design → implement → self-review → test → realistic journey → record → commit → continue.
