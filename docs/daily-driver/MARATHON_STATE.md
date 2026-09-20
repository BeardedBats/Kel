# MARATHON_STATE — Kel Daily Driver Expansion Marathon

Last updated: 2026-09-20 (**D3–D18 landed; D19 regression green; fresh package built + installed as the daily-driver candidate; installed GUI battery remains**)

- MARATHON_MODE: ACTIVE — implementation marathon; no independent audit, no release, no freeze.
- LANE: branch `dev/daily-driver` · worktree `C:\Users\Nick\Desktop\Kel\kel-daily-driver`
- directive: `docs/daily-driver/MARATHON_DIRECTIVE.md` — the complete governing program (D3–D19, package, install). Read it before acting; it outranks chat history.
- BASE SHA: `37b1f27faf02dfa5feb96449fc3768c0ec4e9692` (production tree == `6d957ee9…`; diff was records/evidence only)
- CURRENT HEAD: the D19 donor-residual + package-records commit (this commit; prior: `b28e91b` D19 regression checkpoint, `5ae5bd0` D18 slice, `8216e48` D16+D17, `8b67cdf` D15, `1ca5eb7` D14, `879804e` D12+D13, `242f4b8` D11, `9c35f66` D10, `6493275` D9, `82ff501` D8 closure)
- COMPLETED:
  - intake + lane open `3f83be7` · **D0 closed** (`9bdf338` · `777fefe` · `cce55d0` · `f594282` · records `288a53c`) · **ENG-001** `80c4ba2`
  - **D1** providers speak user language `0279a1d` · **D2** donor CDN feed severed `7c9df63` · **D3** gateway session enforcement + real-browser verification `78d8f1d` (wrong-layer attempt reverted `b13301a`)
  - **D4** transcription live + recents `e57d4a3` · **D5** attention + restrained notifications `dde6c1e` · **D6** resumption brief + live restart/resume `43cf675` · **D7** orphaned runs reach Needs You `1374fcd`
  - **D8** plain staffing language `daafd36` + Kel manages its own roster + Team page developer surface `82ff501` (D0–D3 evidence 277 workforce tests OK)
  - **D9** learning promotion ("Kel suggests") + live loop `6493275` · **D10** recipes loop + engine bug fixed `9c35f66` · **D11** cross-device `/kel` gateway + real-stack journey `242f4b8` · **D12** routing transparency + bodyless-GET fix + **D13** remote failure language `879804e` · **D14** Activity view `1ca5eb7` · **D15** deliberate emergency stop + verified containment `8b67cdf` · **D16** live revision 9/9 + dead-grant fix + **D17** integrations overview `8216e48`
  - **D18 (all ten journeys recorded)** `5ae5bd0` — DOGFOOD_JOURNEYS.md: 6 live (transcription, remote, recipes, learning, continuity, routing), 3 engine-live/partial (conversation/coding/autonomy — model turn needs a provider key), 1 pinned (update; packaged re-verify now done at the installer-metadata level). Friction ledger: ten journey-driven fixes.
  - **D19 regression gate GREEN** `b28e91b` — engine **1025 OK** (324.1s) · desktop tsc 0 + Vitest 34 files / 260 PASS · all seven live journeys re-run green on fresh data dirs · transcription E2E pass · workforce 277+ OK
  - **Fresh package built + installed (this commit)** — engine bundled (PyInstaller, 51/51 OK), installer metadata Kel/1.7.0-dev, asar donor-org sweep **0 hits** (two donor links removed in the D19 residual fix), installed candidate live (engine answers `/api/state`); install incident + repair recorded in PACKAGE_EVIDENCE
- COMPLETED PHASES: intake/lane-open · D0 · ENG-001 · D1 · D2 · D3 · D4 · D5 · D6 · D7 · D8 · D9 · D10 · D11 · D12 · D13 · D14 · D15 · D16 · D17 · D18 (recorded) · D19 regression + package + install (battery partially done).
- CURRENT PHASE: **D19 — installed battery completion** (`MARATHON_DIRECTIVE.md` §39–42).
- CURRENT ITEM: GUI-driven installed probes on `C:\Users\Nick\KelDailyDriverCandidate`: D0-001 (Permissions Work column shows the work's request), D0-004 (Desktop-Pet refusal shows exactly one toast), D1 (providers Set up → Save + Verify), D2 (update fails closed), upgrade preservation.
- EXACT NEXT ACTION: launch the installed candidate against `C:\Users\Nick\KelDailyDriverRuns\prepared`, run the four installed probes + upgrade preservation, record them in PACKAGE_EVIDENCE, then write `DAILY_DRIVER_CANDIDATE.md` (the candidate head record) and close the marathon.
- REMAINING QUEUE: installed GUI battery → DAILY_DRIVER_CANDIDATE record → (D18 provider-dependent journeys if a key exists).
- LATEST TESTS: desktop tsc exit 0 · Vitest 34 files / 260 PASS · engine **1025 OK** (full suite) · all seven live journeys green · transcription E2E pass · workforce 277+ OK · installed engine live (1.7.0-dev)
- LATEST PACKAGE: **BUILT + INSTALLED** — installer `Kel-1.7.0-dev-win-x64.exe` sha256 `364065d3…` (213,622,841 B); Kel.exe `019e4f47…`; engine `17c08c57…` (3,329,912 B); installed at `C:\Users\Nick\KelDailyDriverCandidate` (engine hash verified in the install; registration points there). `KelVisualFixInstall` restored to its V1.6 record after the update-mode incident (documented).
- BLOCKERS: none
- UNAVAILABLE EXTERNAL CREDENTIALS: no provider keys in this environment; the model-turn journeys (1–3) stay partial by design
- DAILY-DRIVER CANDIDATE STATUS: **INSTALLED, battery completing** — candidate head record pending (`DAILY_DRIVER_CANDIDATE.md`)

## Rules in force

- Disk is durable state; update this file at every checkpoint. Do not rely on chat history.
- Protected refs (do not modify): `main`, `repair/v16-human-visual`, `repair/v16-final`, `audit/v16-human-visual-final`, `audit/v16-postrepair-final`, `audit/v16-final`, `ux/v15-journeys`, protected tags (`v1.2.0`…`v1.6.0-pre1`).
- No publishing, no release tag, no history rewrites. Development identity: `1.7.0-dev`.
- One lane: `dev/daily-driver`. Per-phase loop: understand → narrow design → implement → self-review → test → realistic journey → record → commit → continue.
