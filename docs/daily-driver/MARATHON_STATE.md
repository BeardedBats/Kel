# MARATHON_STATE - Kel Daily Driver Expansion Marathon

Last updated: 2026-09-20 (**marathon complete — D3–D19 landed, fresh package built + installed, installed GUI battery all PASS; only environment-limited items remain**) 

- MARATHON_MODE: ACTIVE - implementation marathon; no independent audit, no release, no freeze.
- LANE: branch `dev/daily-driver` · worktree `C:\Users\Nick\Desktop\Kel\kel-daily-driver`
- directive: `docs/daily-driver/MARATHON_DIRECTIVE.md` - the complete governing program (D3-D19, package, install). Read it before acting; it outranks chat history.
- BASE SHA: `37b1f27faf02dfa5feb96449fc3768c0ec4e9692` (production tree == `6d957ee9...`; diff was records/evidence only)
- CURRENT HEAD: the commit that carries this update (prior: `cc3e859` record pointer, `3e6b544` interrupted-run continuation fix, `9cfb087` upgrade preservation, `db46cf4` candidate record, `9d6ce53` boot probe + tooling, `89f2f23` D19 residual + package, `b28e91b` D19 regression checkpoint, `5ae5bd0` D18 slice, `8216e48` D16+D17, `8b67cdf` D15, `1ca5eb7` D14, `879804e` D12+D13, `242f4b8` D11, `9c35f66` D10, `6493275` D9, `82ff501` D8 closure)
- COMPLETED:
  - intake + lane open `3f83be7` · **D0 closed** (`9bdf338` · `777fefe` · `cce55d0` · `f594282` · records `288a53c`) · **ENG-001** `80c4ba2`
  - **D1** providers speak user language `0279a1d` · **D2** donor CDN feed severed `7c9df63` · **D3** gateway session enforcement + real-browser verification `78d8f1d` (wrong-layer attempt reverted `b13301a`)
  - **D4** transcription live + recents `e57d4a3` · **D5** attention + restrained notifications `dde6c1e` · **D6** resumption brief + live restart/resume `43cf675` · **D7** orphaned runs reach Needs You `1374fcd`
  - **D8** plain staffing language `daafd36` + Kel manages its own roster + Team page developer surface `82ff501` (D0-D3 evidence 277 workforce tests OK)
  - **D9** learning promotion ("Kel suggests") + live loop `6493275` · **D10** recipes loop + engine bug fixed `9c35f66` · **D11** cross-device `/kel` gateway + real-stack journey `242f4b8` · **D12** routing transparency + bodyless-GET fix + **D13** remote failure language `879804e` · **D14** Activity view `1ca5eb7` · **D15** deliberate emergency stop + verified containment `8b67cdf` · **D16** live revision 9/9 + dead-grant fix + **D17** integrations overview `8216e48`
  - **D18 (all ten journeys recorded)** `5ae5bd0` - DOGFOOD_JOURNEYS.md: 6 live (transcription, remote, recipes, learning, continuity, routing), 3 engine-live/partial (conversation/coding/autonomy - model turn needs a provider key), 1 pinned (update; packaged re-verify now done at the installer-metadata level). Friction ledger: ten journey-driven fixes.
  - **D19 regression gate GREEN** `b28e91b` - engine **1025 OK** (324.1s) · desktop tsc 0 + Vitest 34 files / 260 PASS · all seven live journeys re-run green on fresh data dirs · transcription E2E pass · workforce 277+ OK
  - **Fresh package built + installed** — engine bundled (PyInstaller, 51/51 OK), installer metadata Kel/1.7.0-dev, asar donor-org sweep **0 hits** (two donor links removed in the D19 residual fix), installed candidate live (engine answers `/api/state`); install incident + repair recorded in PACKAGE_EVIDENCE
  - **Interrupted runs can be continued again** `3e6b544` — the person's "continue" re-arms a fenced (orphaned/uncertain) milestone instead of attaching a link and waiting forever, and the Work page no longer promises an automatic continuation for that state; engine **1029 OK**, desktop 36 files / 268 PASS
  - **D18 journeys 1–3 closed with a synthetic provider turn** — `packaging/verify_synthetic_journeys.py` **all green (16/16)**: durable conversation turn, a real task to CLOSED/VERIFIED with a publication, a real child killed mid-run → fenced → the person's continuation finishes the same job, pause/resume, and a failing provider landing terminal + needs-you with a bounded ladder
  - **Provider ids no longer reach user copy** — the route sentence, the provider save confirmation and the readiness choices name providers from the engine's inventory labels (engine id `internal` is recorded debt); pinned by `provider-language.test.ts`
  - **Re-cut package installed + full installed battery GREEN** — every installed surface and all four GUI replays pass, upgrade preservation re-proven, no orphaned processes (PACKAGE_EVIDENCE + `evidence/d19/installed-battery.json`)
- COMPLETED PHASES: intake/lane-open · D0 · ENG-001 · D1 · D2 · D3 · D4 · D5 · D6 · D7 · D8 · D9 · D10 · D11 · D12 · D13 · D14 · D15 · D16 · D17 · D18 (all ten journeys recorded) · D19 regression · package · install · installed battery. **Program complete.**
- CURRENT PHASE: **D19 CLOSED** (`MARATHON_DIRECTIVE.md` §39–42); the marathon's endpoint (D19, fresh package, installed Daily Driver Candidate) is reached and recorded.
- CURRENT ITEM: nothing in flight. The installed candidate at `C:\Users\Nick\KelDailyDriverCandidate` (data root `C:\Users\Nick\KelDailyDriverRuns\prepared`) passes the installed battery: nine surfaces with no raw errors / no overflow / no donor terms, D0-001, D0-004, D1, D2, automatic routing (readiness answered `Chosen: Claude (Claude Code)` with the full chain in words), upgrade preservation, and zero orphaned engine processes.
- EXACT NEXT ACTION: none required. If a provider credential ever appears on this machine, re-run `node packaging/verify-installed-battery.cjs` and the provider-dependent journeys (1–3) with a live model turn; the remote browser half additionally needs a phone for the QR login.
- REMAINING QUEUE: empty except environment-limited items (no provider key → no live model turn; no phone → no QR login for the remote browser half). Both are listed in `KNOWN_LIMITATIONS.md` as current, not as regressions.
- LATEST TESTS: desktop tsc exit 0 · Vitest 36 files / 269 PASS · engine **1029 OK** (full suite) · synthetic journeys 16/16 · all seven live journeys green · transcription E2E pass · workforce 277+ OK · installed battery all PASS
- LATEST PACKAGE: **BUILT + INSTALLED (final re-cut)** — installer `Kel-1.7.0-dev-win-x64.exe` sha256 `0add7bc4…` (213,631,660 B); Kel.exe `e1d62c5f…`; engine `01c58bdf…` (3,330,256 B); installed at `C:\Users\Nick\KelDailyDriverCandidate` (hashes verified in place; registration points there; `Uninstall Kel.exe` metadata Kel / 1.7.0-dev). `KelVisualFixInstall` restored to its V1.6 record after the update-mode incident (documented).
- BLOCKERS: none
- UNAVAILABLE EXTERNAL CREDENTIALS: no provider keys in this environment; journeys 1–3 carry synthetic-provider evidence instead of a live model turn
- DAILY-DRIVER CANDIDATE STATUS: **INSTALLED · VERIFIED · RECORDED** — `DAILY_DRIVER_CANDIDATE.md` carries the identity, bind chain, hashes, the installed-battery results, and the honest open items.
- DAILY_DRIVER_CANDIDATE_HEAD: `6c9d1a1d69016a3c8c307b157d7998521b355011` (local marker tag `DAILY_DRIVER_CANDIDATE_HEAD`; the source tree the final installer was built from and the installed battery verified)

## Rules in force

- Disk is durable state; update this file at every checkpoint. Do not rely on chat history.
- Protected refs (do not modify): `main`, `repair/v16-human-visual`, `repair/v16-final`, `audit/v16-human-visual-final`, `audit/v16-postrepair-final`, `audit/v16-final`, `ux/v15-journeys`, protected tags (`v1.2.0`...`v1.6.0-pre1`).
- No publishing, no release tag, no history rewrites. Development identity: `1.7.0-dev`.
- One lane: `dev/daily-driver`. Per-phase loop: understand → narrow design → implement → self-review → test → realistic journey → record → commit → continue.
