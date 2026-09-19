# PACKAGED_EVIDENCE_INDEX — packaged-app proof per build

updated: 2026-09-19T00:55Z
rule: source-passed is never packaged-passed. Every row must name a real packaged build.
Build convention: `desktop`, `bunx electron-builder --config kel-builder.json --win --x64
--config.directories.output=../dist/package-NAME`; builds take ~5–8 min. Engine built by
`scripts/build-runtime.ps1` (PyInstaller). Evidence bundles live under `ux-audit/` (build logs,
`runs/<name>/`), not in this repo. **R12 note:** the RC installer build additionally requires
(a) the generated `resources/windows/support/_sentry-dsn.generated.nsh`, (b) the stock NSIS
`installUtil.nsh` (the fork's optional patch references donor includes and is NOT part of the Kel
path — audit target 48), and (c) `companyName`/`author.name` = Kel in `desktop/package.json`
(appInfo.companyName reads `author.name`).

| Package | Source commit | Engine identity | Migration @ boot | Probes / journeys | Result | Evidence | Notes |
|---|---|---|---|---|---|---|---|
| `package-final11` | pre1 era | fresh build | ≤15 | pre-checkpoint battery | PASS | ux-audit/run-precheckpoint-*.sh; `Kel-V1.6.0-Pre1-Frozen` 3/3 verifier | byte-identical to the frozen pre1 folder |
| `package-final12` | — | — | — | — | **UB — never cite** | — | superseded intermediate (UI bug) |
| `package-final13` | Phase 1 era | fresh | 15 | memoryprops journey | PASS | ux-audit/run-memoryprops.sh; memoryprops-db-probe.py | memory proposal surface |
| `package-final15` | Phase 2 era | fresh | 15 | lineage probe | PASS | ux-audit/run-lineage-probe.sh | artifact lineage |
| `package-final16` | Phase 3 era | fresh | 15 | approvals journey + lineage re-run | PASS | ux-audit/run-approvals.sh; verify-approvals.py | in-chat approvals |
| `package-final17` | `fd04c00` | fresh (PyInstaller 6.19.0 / Python 3.14.3) | 15 | copy-scan over reachable routes + approvals + lineage journeys | PASS | ux-audit/run-phase4.sh; package-final17-build.log | Phase 4 completion evidence |
| `package-p1cap` | `75d1f68` era | fresh (hash == fresh `dist/runtime`) | 15 | sessiontools journey + packaged-engine capability probe | PASS | ux-audit/run-p1-capabilities.sh; p1-capability-engine-probe.py | CAP-01 regression check; real transport reached (401 w/ dummy key) |
| `package-p1cap2` | `327e5b2` era | fresh | 15 | sessiontools (bracket-clause steps) + CAP2 forwarded-text probe + engine regression | PASS | ux-audit/run-cap2-clause.sh | clause grammar |
| `package-p1cap3` | `631881a` era | fresh | 15 | sessiontools (reserved/ residual steps) + residual db probe + engine regression | PASS | ux-audit/run-cap2-residual.sh | reserved `[kel:...]` grammar |
| `package-visual5` | `ac85eb3` (visual branch) | fresh from visual branch | 15 | probe a: shell sweep 21 surfaces (0 console errors; first paint 3.03s; 23 screenshots); probe b: color control/New Chat/engine-loss (reproduces findings 16/17); probe c: populated sidebar (overlapPx −4, gutter 32px, leading marks correct) | PASS | ux-audit/visual/runs/visual5-{a,b,c}/; `kel-v16-visual-audit/docs/v1.6-visual-ux/packaged-visual5/SCREENSHOT_REVIEW_INDEX.md` | batches 1–5 acceptance; 35 screenshots indexed |
| `package-logo` | `edd50de` + canonical-logo change | fresh (`dist/runtime` unchanged; identity recorded in the row's log) | 15 (engine identity untouched — no engine change) | packaged boot + UI capture (`packaging/ux-audit.cjs` `first-run`) with an isolated profile; icon extraction from `Kel.exe` and the NSIS installer | PASS | exe icon = shipped `app.ico` 32 px frame (mean abs diff **0.0**); installer icon = **0.0**; old package was **not** the K (73.2); exe identity `Kel · Kel · AionUi · 1.5.0` (was Electron's own); packaged `resources/pwa/icon-*`+`app.png` byte-identical to the shipped K assets; captures in `dist/logo-evidence/ux-audit/` + committed selection under `docs/v1.6/branding/evidence/`; harness `errors: []` for both scenarios; About capture matches the canonical artwork at **0.960** masked NCC (`scripts/verify-brand-render.py`) | REQ-LOGO-1 | first packaged build whose exe/installer icons are the canonical K |

| `package-r12` (lane) | `fa66f04` (visual lane, re-anchored) | staged frozen **1.6.0** runtime (`kel-ux-v15/dist/runtime/KelEngine`; the worktree's stale 1.5.0 bundle was replaced — audit target 90) | fresh (empty root) | R10 engine-loss journeys `r10-f`/`r10-g` (kill → reconnecting → supervised restart → durable folder + conversations preserved → repeat → could-not-recover → manual retry) | PASS | ux-audit/runs/r10-{c,d,e,f,g}/; `docs/v1.6-visual-ux/19_R10_ENGINE_LOSS_EVIDENCE.md` | 7 screenshots; DOM leak scan clean; console 0; `[KEL-LINK]` transitions recorded |
| `package-r12` (RC, from merged Main) | `12f87a7` + packaging fixes (kel-builder output name; `companyName`/author = Kel) | staged frozen **1.6.0** runtime; installed engine SHA-256 `69123AF001B8DF7E98FD092E751437044AFF43CA085B0161E45CA08B62AA3AB1` (equals `dist/runtime` — hash comparison) | fresh + **upgrade** (populated 1.6.0 root; conversations preserved) | NSIS `Kel-1.6.0-win-x64.exe` (stock template; silent install → exit 0 → shortcuts → launch → uninstall); installed probes fresh + upgrade: healthy 1.6.0, R9.D attention present, About canonical K renders, 0 leaks / 0 console errors / 0 horizontal overflow (5 routes); exe icon extracted; Add/Remove `Kel · Kel · 1.6.0` | PASS | `ux-audit/runs/r12-*`; `ux-audit/r12-install-result.json`; `ux-audit/r12-engine-suite.log` (998+10) | first RC installer under FULL Kel identity (donor CompanyName removed); donor NSIS script set deliberately NOT included (stock template, audit target 48); install → uninstall lifecycle cleaned up |

## Known pending packaged work (carry-forward)

- ~~Packaged migration assertions on a packaged boot~~ — asserted at R12: fresh boot creates and
  upgrades all V1.6 migrations (`schema_migrations` intact); the populated 1.6.0 root boots
  unchanged; the migration chain itself is covered by `test_v16_r8_migrations` in A-29.
- ~~Packaged engine-loss/recovery behavior~~ — closed at R10 (P-8; `19_R10_ENGINE_LOSS_EVIDENCE.md`).
- ~~RC package~~ — built: this row (`package-r12`); `package-prea` name not used.
- Phase 7 capability card: seed a blocked milestone carrying a `recommendation` in a packaged app
  (no provider in this environment — audit target 45; LIM-14). STILL OPEN (audit-side).
- Canonical logo: exe icon extraction recorded on the RC; 16/32/48 legibility + exact
  transparency + the human pixel pass remain OPEN (audit target 50; human gate PENDING).
- Donor preview viewers still append a raw exception message to their translated failure line
  (audit target 89). STILL OPEN (recorded, outside Kel surfaces).

## Maintenance rules

- One row per packaged build that produced acceptance evidence; never delete a row (annotate
  supersession).
- `Engine identity` must state how it was verified (hash comparison to fresh build, or which
  probe asserted it).
