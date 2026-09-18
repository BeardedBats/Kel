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

## Open items

- **Two missing baseline captures** for findings 2 and 3 (before those surfaces are touched).
- **Human pixel review**: OPEN — no image perception in agent threads; prepared index stands ready.
- **Integration**: commit lineage must be preserved on merge (§44); every conflict resolution is
  an audit target (AUDIT_TARGETS §29).
- **Main edit notice (2026-09-18):** Phase 6 (`22f4a3e`) touched `KelWorkPanel.tsx` (Knowledge tab
  only) — the HELD visual batches (3, 5-team half) are not affected by this edit; the Visual thread
  revalidates against current Main before editing per protocol.
