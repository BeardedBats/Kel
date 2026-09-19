# VISUAL_EVIDENCE_INDEX — visual findings, batches, acceptance, human gate

updated: 2026-09-18T00:20Z
authority: `kel-v16-visual-audit/docs/v1.6-visual-ux/VISUAL_STATUS.md` (the schema block there is
authoritative; this index mirrors it for the audit corpus). Implementation branch
`ux/v16-visual-fix` @ `fa66f04` (code) / `bc92f7f` (evidence); integration into Main:
**DONE** — merge commit `7267630` (R11; before-mutation record in `increments/R11-INTEGRATION.md`,
zero overlapping files, no conflict resolutions).

## Batch ledger

| Batch | Finding source | Original severity (as recorded) | Implementation commit | Automated acceptance | Packaged acceptance | Screenshots | Human review | Main integration |
|---|---|---|---|---|---|---|---|---|
| 1 — design tokens | visual plan set §tokens | — | `8dd21f9` | 39/39 WCAG contrast checks; tsc 0; vitest 76/76 | package-visual5 (probe a) | visual5 captures 1–23 (probe a) | OPEN | PENDING |
| 2 — settings shell | finding S1-1 + Tools route | — | `3d9202c` | tsc 0; 76/76 | package-visual5 (probe a) | as above | OPEN | PENDING |
| 6 — engine loss / error translation / supervision | findings 16/17 reproduced by probe b | HIGH (raw `TypeError: fetch failed` surfaces) | `2897207` (+ `645898a`, `fa66f04` fail-fast follow-ups) | tsc 0; vitest 114→122 (classifier + health-machine suites) | **R10 packaged journey PASS** — `ux-audit/runs/r10-{f,g}/` (r10-g full journey; r10-f fast-fail cannot-restart); 7 screenshots; DOM leak scan clean | `r10-g/r10-0{0..4}*.png`, `r10-f/r10d-0*.png` | OPEN | **DONE** (`7267630`) |
| 7 — composer / Model / Tools | finding 2 (03 §2) | — | `0e7d21a` | tsc 0; vitest 114 | covered by r10-g boot/connected captures | `r10-g/r10-00-connected.png` | OPEN | **DONE** (`7267630`) |
| 8 — final normalization | directive §8 | — | `c911d81` | tsc 0; vitest 114 | covered by r10-g captures | as above | OPEN | **DONE** (`7267630`) |
| R9.D — Needs Your Attention | directive §9 / roadmap item N | — | `938dc9b` | tsc 0; vitest 122 (hostile isolation suite) | R12 battery (Work-surface capture) | — | OPEN | **DONE** (`7267630`) |
| 3 — Work / Projects / Permissions (full rebuild) | visual plan set | — | — | — | — | — | — | NOT ORDERED (normalization-only scope applied in batch 8) |
| 5 (Team half full redesign) | team terminology / entry merge | — | — | — | — | — | — | NOT ORDERED (normalization-only) |

## Packaged acceptance detail (package-visual5, 2026-09-18)

- Build provenance: `ux/v16-visual-fix` @ `ac85eb3`; renderer fresh via electron-vite; KelEngine
  fresh from this branch via `scripts/build-runtime.ps1`; packaged to
  `kel-v16-visual-fix/dist/package-visual5/win-unpacked`.
- Probe a (shell sweep, 21 surfaces): 0 console errors; first paint 3.03s; theme toggle + close
  clean; 23 screenshots.
- Probe b (color control / New Chat / engine-loss): 0 console errors; engine-loss reproduces raw
  failure surfaces — **open findings 16/17, Batch 6 scope**.
- Probe c (populated sidebar): hover `overlapPx = −4`; `rowPaddingRight: 32px`; leading-mark
  semantics exactly as specified.
- Screenshot review index (authoritative mapping of all 35 captures to findings):
  `kel-v16-visual-audit/docs/v1.6-visual-ux/packaged-visual5/SCREENSHOT_REVIEW_INDEX.md`.
- Raw evidence: `ux-audit/visual/runs/visual5-{a,b,c}/`.

## Branding — canonical logo (2026-09-18, Nick directive)

The donor AionUi mark is replaced everywhere by the exact Nick-supplied folded-ribbon K
(sha256 `7418a42f…`; record `docs/v1.6/branding/CANONICAL_LOGO.md`).

| Surface | Asset (derived from the canonical source) | Automated evidence | Human gate |
|---|---|---|---|
| exe / installer / shortcuts | `resources/app.ico` (16–256) | packaged exe icon extraction (PACKAGED_EVIDENCE_INDEX `package-logo`) | 16 px legibility OPEN |
| tray / notifications | `resources/app.png` (1024 → 32/16) | derivative corners transparent; same-art check | tray legibility OPEN |
| window/dock (dev) | `app.ico` / `app_dev.png` | tsc 0; boot check | — |
| favicon / apple-touch / PWA | `public/pwa/icon-180/192/512.png` | `renderer/index.html` + `manifest.webmanifest` reference exactly these files | — |
| login brand mark | `renderer/assets/logos/brand/app.png` | tsc 0; vitest 90 | placement/density OPEN |
| About | same asset, new `<img data-testid='kel-about-logo'>` | tsc 0; vitest 90 | placement/density OPEN |
| linux / macOS | `resources/app.png` / `resources/app.icns` | `kel-builder.json` keys set; ICNS chunk map recorded in the record §2 | macOS untestable here (LIM-9) |

Supersedes the donor mark on the login screen (was AionUi art at the same import path).

Automated render check: `python scripts/verify-brand-render.py <captures>` matches the canonical
artwork inside the packaged About capture at **0.960** masked NCC (other captures ≤ 0.51 baseline).
Committed captures + reproduction commands: `docs/v1.6/branding/evidence/`.

## Open items

- **Two missing baseline captures** for findings 2 and 3 (before those surfaces are touched).
- **Human pixel review**: OPEN — no image perception in agent threads; prepared index stands ready.
- **Integration DONE** (`7267630`): zero overlapping files at integration time; no conflict
  resolutions were required (audit target §29 therefore records "no resolutions"). R9/R10 lineage
  preserved in `docs/v1.6-visual-ux/17–19` and the corpus rows of `increments/R11-INTEGRATION.md`.
- **Main edit notice (2026-09-18):** Phase 6 (`22f4a3e`) touched `KelWorkPanel.tsx` (Knowledge tab
  only) — resolved during R9.A by re-anchoring the lane on Main `05608e6` (pure-union merge); the
  pre-existing `KelModelControl` / `KelApprovalCard` / `KelCapabilityCard` behavior was preserved
  exactly as Main shipped it.
