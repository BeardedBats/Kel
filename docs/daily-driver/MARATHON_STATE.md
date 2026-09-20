# MARATHON_STATE — Kel Daily Driver Expansion Marathon

Last updated: 2026-09-20 (**D3–D14 landed and verified; D15 in progress**)

- MARATHON_MODE: ACTIVE — implementation marathon; no independent audit, no release, no freeze.
- LANE: branch `dev/daily-driver` · worktree `C:\Users\Nick\Desktop\Kel\kel-daily-driver`
- directive: `docs/daily-driver/MARATHON_DIRECTIVE.md` — the complete governing program (D3–D19, package, install). Read it before acting; it outranks chat history.
- BASE SHA: `37b1f27faf02dfa5feb96449fc3768c0ec4e9692` (production tree == `6d957ee9…`; diff was records/evidence only)
- CURRENT HEAD: the D14 commit (see `git log --oneline`; prior: `879804e` (D12+D13), `242f4b8` (D11), `9c35f66` (D10), `6493275` (D9), `82ff501` (D8 closure), `daafd36` (D8 slice 1), `1374fcd` (D7), `43cf675` (D6), `a8c27ba` (directive), `dde6c1e` (D5), `e57d4a3` (D4), `78d8f1d` (D3))
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
  - **D12 core** — routing transparency: `/api/state` exposes the engine's `run.claimed` decision per active job; Work page renders one plain sentence (cheapest-eligible, fallback offer, up to 3 skipped providers with translated reasons, honest unknowns); fixed the D11 bodyless-GET gap; live journey all-green `879804e`
  - **D13 core** — remote failure language: gateway codes become sentences in the remote browser; network drops read as device problems; raw codes can no longer surface as UI copy `879804e`
  - **D14 core** — optional Activity view: quiet `/activity` page composed from existing state (Happening now + routing sentence, Waiting on you, Recently finished, provider count); internals banned by pin; shared `workLanguage.ts` keeps Work and Activity sentences identical (this commit)
- COMPLETED PHASES: intake/lane-open · D0 · ENG-001 · D1 · D2 · D3 · D4 · D5 · D6 · D7 · D8 · D9 · D10 · D11 · D12 · D13 · D14 (all committed, tree clean).
- CURRENT PHASE: **D15 — Security / sandbox boundary improvements** (`MARATHON_DIRECTIVE.md` §D15) — starting recon.
- CURRENT ITEM: D15 recon — verify the existing containment end to end (guardrails block, boundary requests, permission leases, secret handling) and close the smallest honest gap without a bespoke hypervisor.
- EXACT NEXT ACTION: recon `runtime/kel/autonomy.py` + guardrails + `/api/autonomy` + the Permissions page wiring; decide the increment.
- REMAINING QUEUE: D15 security/containment → D16 live capability revision → D17 integration/dev surface → D18 dogfood journeys → D19 full regression → fresh package → installed candidate + final battery. (`ROADMAP.md` keeps the compact table.)
- LATEST TESTS: desktop tsc exit 0 · Vitest 30 files / 249 PASS · engine **1023 OK** (full suite, post-D12) · D3 real-stack matrix green · D4 live transcription E2E green · D5 transition-core green · D6 live restart/resume all-true · D7 orphan/route-block classification green · D8 staffing + team pins green · D9 learning pins + live loop all-true · D10 recipe pins + live loop all-true · D11 gateway unit + pins + real-stack journey all-green · D12 route pins + engine suite + live journey all-green · D13 failure-language pins green · D14 activity pins green
- LATEST PACKAGE: none yet — package phase pending; checklist ready in `PACKAGE_EVIDENCE.md`
- BLOCKERS: none
- UNAVAILABLE EXTERNAL CREDENTIALS: no provider keys in this environment; live provider validation impossible (fixture/local validation documented)
- DAILY-DRIVER CANDIDATE STATUS: NOT STARTED (implementation ongoing; reserved install/data roots recorded in RESUME.md)

## Rules in force

- Disk is durable state; update this file at every checkpoint. Do not rely on chat history.
- Protected refs (do not modify): `main`, `repair/v16-human-visual`, `repair/v16-final`, `audit/v16-human-visual-final`, `audit/v16-postrepair-final`, `audit/v16-final`, `ux/v15-journeys`, protected tags (`v1.2.0`…`v1.6.0-pre1`).
- No publishing, no release tag, no history rewrites. Development identity: `1.7.0-dev`.
- One lane: `dev/daily-driver`. Per-phase loop: understand → narrow design → implement → self-review → test → realistic journey → record → commit → continue.
