# Increment — LOGO-CANONICAL

increment_id: LOGO-CANONICAL
phase: Campaign A — canonical logo requirement (Nick directive, 2026-09-18)
base_commit: edd50de (published Phase 8–11 checkpoint)
target_commit: the branding commit + this docs commit
status: complete (source + packaged validation; human pixel gate on placement remains)

## Objective

Adopt the exact Nick-supplied folded-ribbon K as the canonical Kel logo and make it appear
consistently across every production-reachable Kel branding surface — no regeneration, no
redraw, no recolour, no crop, no distortion, no leftover donor mark.

## Requirement Sources

- Nick's directive of 2026-09-18 (canonical logo; surfaces list; validation list).
- Existing branding surfaces discovered by repository audit (see the record's §3/§4).

## Implementation Summary

1. Canonical source identified and preserved: `Kel Logo.png`
   (sha256 `7418a42f…`) → byte-identical copy at `desktop/resources/branding/kel-logo.png`.
2. Reproducible derivatives via `scripts/make-brand-assets.py` (premultiplied-alpha resampling;
   uniform scale; transparent square canvases; refuses any source whose hash differs).
3. Wired: exe/installer/shortcut icons (`app.ico` + `kel-builder.json` icons +
   `signAndEditExecutable: true`), tray/notification (`app.png`), dev window/dock
   (`app.ico`/`app_dev.png`), linux/mac icons, favicon/PWA icons, login mark, About logo (new).
4. Audited out: donor marketing images (not reachable), dead `logo.svg`, dormant NSIS text,
   package.json attribution metadata — each recorded with rationale instead of being touched.

## Files Changed

- `scripts/make-brand-assets.py` (new)
- `desktop/resources/branding/kel-logo.png` (new; canonical copy)
- `desktop/resources/app.ico`, `app.png`, `app_dev.png`, `icon.png`, `app.icns`
- `desktop/public/pwa/icon-180.png`, `icon-192.png`, `icon-512.png`
- `desktop/packages/desktop/src/renderer/assets/logos/brand/app.png`
- `desktop/packages/desktop/src/renderer/components/settings/SettingsModal/contents/AboutModalContent.tsx`
- `desktop/kel-builder.json`

## Symbols Changed

`AboutModalContent` render (brand `<img>`); electron-builder config keys (win/nsis/mac/linux icons,
signAndEditExecutable).

## Schema/Migrations

None.

## User-Facing Behavior

Every Kel mark the user can see is now the canonical K (exe/taskbar/tray/favicon/login/About).

## Internal Behavior

electron-builder now edits the Windows executable (icon + version metadata) instead of skipping it.

## Error Paths

Asset generator refuses a mismatched source (`sha256` guard) — no wrong-image derivatives possible.

## Lifecycle Considerations

None.

## Persistence / Isolation

None.

## Security / Privacy

None (no new inputs; image assets only).

## Self-Review Findings

- The previous packaged exe carried **Electron's own identity and icon** — `ProductName=Electron`,
  `CompanyName=GitHub, Inc.`, version `37.10.3` — because executable editing was disabled
  (`signAndEditExecutable: false`). Enabling it gives `Kel · Kel · AionUi · 1.5.0` and the K icon
  (extraction-verified). This was a real, previously unrecorded shipped-branding defect.
- 16 px legibility of the K is inherently limited by the artwork; recorded as human pixel-gate.

## Tests Run

- `python scripts/make-brand-assets.py "/c/Users/Nick/Desktop/Kel Logo.png"` (generation) and
  `--check` (determinism).
- `cd desktop && bunx tsc --noEmit` → 0.
- `cd desktop && bun run test` → 90 passed.
- Packaged build: `bunx electron-builder --config kel-builder.json --win --x64` → exit 0 (`dir` +
  NSIS installer).
- Packaged icons: extracted exe/installer icons are pixel-identical to the shipped `app.ico` 32 px
  frame (mean abs diff **0.0**); the previous package was **not** the K (73.2) and reported Electron's
  own identity (`ProductName=Electron`, `CompanyName=GitHub, Inc.`).
- Packaged UI capture: `packaging/ux-audit.cjs` `first-run` + `settings` on an isolated profile →
  `errors: []` for both; app booted and rendered.
- In-app render: `python scripts/verify-brand-render.py dist/logo-evidence/ux-audit --sizes
  40,48,56,64,72,80` → the About capture matches the canonical artwork at **0.960** masked NCC.

## Results

PASS (source + packaged; see the record and packaged index for exact evidence).

## Packaged Verification

`package-logo` build (exit 0) + exe/installer icon extraction (mad 0.0 vs the shipped K frame) +
packaged UI capture (`first-run`, `settings`; `errors: []`) + in-app render match (0.960 NCC on the
About capture). Recorded in PACKAGED_EVIDENCE_INDEX; committed captures in
`docs/v1.6/branding/evidence/`.

## Known Weaknesses

- The shipped `Kel.exe` still reports `CompanyName=AionUi` in its version metadata (from
  `package.json` `author`) — branding-adjacent, deliberately not changed (audit target 49).
- The donor `resources/windows/*.nsh` installer messages remain in the repo; they are **not included**
  by the builder config, so the shipped NSIS installer uses electron-builder's Kel-named template
  (audit target 48).
- Dead donor `logo.svg` remains in assets (unreferenced; audit target 47).
- No separate capture of the packaged login screen (needs an authenticated account this environment
  cannot configure); it renders the same asset proven on the About screen.

## Deferred Questions

- Audit targets 47–52 (dead donor svg, installer path, shipped metadata, icon quality, reachability
  sweep, derivative integrity).

## Audit Targets

AUDIT_TARGETS § 47–52.

## Repair Hints

`scripts/make-brand-assets.py` is the single regeneration path; any icon finding repairs there
plus the affected surface row in the record.

## Evidence Paths

- `docs/v1.6/branding/CANONICAL_LOGO.md`
- corpus rows (REQUIREMENTS_TRACEABILITY REQ-LOGO-1, CHANGE_LEDGER CHG-004, COMMIT_LEDGER,
  VISUAL_EVIDENCE_INDEX, TEST_EVIDENCE_INDEX, PACKAGED_EVIDENCE_INDEX, AUDIT_TARGETS)

## Commit Chain

`edd50de` → branding commit → this docs commit.
