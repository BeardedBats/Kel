# VISUAL_EVIDENCE_INDEX — visual findings, batches, acceptance, human gate

updated: 2026-09-18T16:05Z
authority: `kel-v16-visual-audit/docs/v1.6-visual-ux/VISUAL_STATUS.md` (the schema block there is
authoritative; this index mirrors it for the audit corpus). Implementation branch
`ux/v16-visual-fix` @ `ac85eb3`; integration into Main: **NOT YET** (Campaign A §44 goal).

## Batch ledger

| Batch | Finding source | Original severity (as recorded) | Implementation commit | Automated acceptance | Packaged acceptance | Screenshots | Human review | Main integration |
|---|---|---|---|---|---|---|---|---|
| 1 — design tokens | visual plan set §tokens | — | `8dd21f9` | 39/39 WCAG contrast checks; tsc 0; vitest 76/76 | package-visual5 (probe a) | visual5 captures 1–23 (probe a) | OPEN | PENDING |
| 2 — settings shell | finding S1-1 + Tools route | — | `3d9202c` | tsc 0; 76/76 | package-visual5 (probe a) | as above | OPEN | PENDING |
| 3 — Work / Projects / Permissions | held | — | — | — | — | — | — | HELD (Main surface release needed) |
| 4 — transcription IA | finding 2/3 baseline caveat | — | `83af16f` | tsc 0; 76/76 | package-visual5 (probe a) | as above | OPEN | PENDING |
| 5 — sidebar rows (action gutter + leading mark) | findings S2/S3 (03 §2, 03 §4 · 04 §4.2) | — | `ac85eb3` | tsc 0; **79/79** (+3 unit tests) | package-visual5 probe c: overlapPx −4 (was +12), 32px gutter, marks correct | package-visual5 captures (probe c) | OPEN | PENDING |
| 5 (Team half) | team terminology / entry merge | — | — | — | — | — | — | HELD |
| 6 — engine loss / error translation / supervision | findings 16/17 reproduced by probe b | HIGH (raw `TypeError: fetch failed` surfaces) | — | — | — | — | — | PENDING |
| 7 — composer / Model / Tools | gated by coordinator | — | — | — | — | — | — | HELD |
| 8 — final normalization (settings half) | — | — | — | — | — | — | — | HELD |

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
- **Integration**: commit lineage must be preserved on merge (§44); every conflict resolution is
  an audit target (AUDIT_TARGETS §29).
- **Main edit notice (2026-09-18):** Phase 6 (`22f4a3e`) touched `KelWorkPanel.tsx` (Knowledge tab
  only) — the HELD visual batches (3, 5-team half) are not affected by this edit; the Visual thread
  revalidates against current Main before editing per protocol.
