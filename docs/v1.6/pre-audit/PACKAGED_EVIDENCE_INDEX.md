# PACKAGED_EVIDENCE_INDEX — packaged-app proof per build

updated: 2026-09-18T16:05Z
rule: source-passed is never packaged-passed. Every row must name a real packaged build.
Build convention: `desktop`, `bunx electron-builder --config kel-builder.json --win --x64
--config.directories.output=../dist/package-NAME`; builds take ~5–8 min. Engine built by
`scripts/build-runtime.ps1` (PyInstaller). Evidence bundles live under `ux-audit/` (build logs,
`runs/<name>/`), not in this repo.

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

## Known pending packaged work (carry-forward)

- Packaged migration assertions 16/17/18/19 on a packaged boot are **not yet asserted**
  (carry-forward). Campaign A: assert `schema_migrations` max = current + correct rows on the RC
  package.
- Packaged engine-loss/recovery behavior: current raw failure surfaces are reproduced by probe b
  (findings 16/17) — Campaign A closes this behavior (visual batch 6 + engine supervision work).
- RC package: `package-prea` (name reserved) — full battery + migration assertions + journeys at
  PRE_AUDIT_V1_6_HEAD. Recorded here when built.
- Phase 7 capability card: seed a blocked milestone carrying a `recommendation` in a packaged app;
  assert the card renders in the Work panel, the actions hit the engine (`/api/capabilities`), and
  dismissal works (no provider in this environment — audit target 45; LIM-14).
- Canonical logo: exe/shortcut/tray icon re-verification on the RC package (16/32/48 legibility and
  exact transparency — audit target 50), plus a human pixel pass on the About/login placements.

## Maintenance rules

- One row per packaged build that produced acceptance evidence; never delete a row (annotate
  supersession).
- `Engine identity` must state how it was verified (hash comparison to fresh build, or which
  probe asserted it).
