# KEL V1.4 — UI AUDIT (v0.2 — capture evidence collected)

Status: v0.3 (2026-09-15) — Gate 1. Packaged baseline captures are **complete** (2 × 30 views, five
widths, zero renderer errors) and an **automated accessibility/keyboard probe** has run (§5). This audit
is still NOT a visual verdict: the aesthetic review requires a vision-capable pass (§4). Gate 1 design
directions and the design system are built on these findings (`KEL_V1.4_VISUAL_DIRECTIONS.md`,
`KEL_V1.4_DESIGN_SYSTEM.md`).

## 1. Method (executes with the screenshot harness)

1. Launch the packaged V1.3 app with an isolated data root; keep windows hidden/minimized; never steal focus.
2. Capture every route and major surface; capture every important state: empty, loading, populated, active work, waiting, approval required, success, uncertain, failed, blocked, offline, provider unavailable, no project, first run, settings, drawers, dialogs, long content, dense content.
3. Capture at 1280×720, 1440×900, 1920×1080, 2560×1440, and a narrow resized window.
4. Inventory navigation, pages, drawers, cards, tables, forms, buttons, alerts, badges, tooltips, menus, dialogs, states, typography, spacing, colors, icons, motion (brief §11.1 item 4).
5. Record defects with evidence; build the before/after set in `docs/v1.4/screenshots/`.

## 2. Preliminary source-level observations (to verify visually next)

1. **Donor inheritance is visible in code** — AionUI i18n namespaces, `@aionui/*` package names, donor settings/login/guid/team pages. Kel-specific surface today = chat + Kel Work panel + engine web assets. Expect the audit to confirm which donor surfaces feel "accidentally untouched".
2. **Kel Work panel reuses donor styling** — header comment: "Kel work controls, using AionUI's Arco components and theme tokens." This is the natural hook for the V1.4 design system; assess whether it reads as Kel or as Aion.
3. **Kel-specific settings are absent** — no gathered pages for Providers, Autonomy, Permissions, Team, Memory, Diagnostics (V1.4 scope per brief §17). The gap is expected; the audit should note current navigation as baseline.
4. **Harness built (G0)** — `packaging/capture-screens.cjs` (captures), `packaging/a11y-probe.cjs`
   (contrast/focus/type), `packaging/render-directions.cjs` (mockups). The packaged app renders with
   **zero page errors** in both data states.

## 3. Checklist for the full audit (brief §11.1 + §11.7)

- [x] Packaged audit at five widths (boot + drawer views; per-view matrix widens in Gate 1) — captures committed
- [~] State matrix: empty + populated + approval-visible + paused-work captured; provider-unavailable, dialogs, pet windows pending
- [x] Baseline defect list with measurements (see §5; repairs tracked at G4/G7/G9)
- [~] Inherited-Aion surface list vs Kel-identity target (G1 direction work; full list at G9)
- [x] Keyboard/focus audit — baseline probe run (§5); re-verified per surface at G7/G9
- [x] Accessibility audit — baseline contrast/type probe run (§5); target standard in the accessibility doc
- [x] Baseline screenshot set committed under `docs/v1.4/screenshots/baseline/`

## 4. Known limitations (honest)

1. **No vision-based review yet.** This runtime has no image-viewing capability, so this pass is
   text/structural (route, size, innerText, discovery dump) + raw captures. A vision-capable review is
   a flagged capability opportunity for visual acceptance; until then, captures are evidence and
   before/after material, not an approved aesthetic judgement.
2. Some settings routes recorded redirects in earlier sweeps; the v2 captures record their real
   behavior (see manifests).
3. Not yet captured: provider-unavailable, dialogs beyond the work drawer, pet windows,
   offline/recovery screens, dense/long content.

## 5. Measured findings — automated probe of the packaged V1.3 app

(Command: `node packaging/a11y-probe.cjs <pkg> <data> docs/v1.4/screenshots/audit`; evidence:
`screenshots/audit/v13-a11y.json` + `v13-a11y-focus-1..3.png`; 0 renderer errors; clean shutdown.)

| Finding | Measurement | Severity |
|---|---|---|
| Contrast failures (muted-on-muted) | 6 — e.g. `rgb(169,174,184)` on `rgb(242,243,245)` = **2.0:1** (“No chat history”); `rgb(134,144,156)` = 2.92–3.1:1 (“Work in a project”, “Try these instructions”) | high |
| Focus indicator missing | **0 of 30** tab stops expose an outline or box-shadow | high |
| Type scale | smallest 12px; a 12.5px oddity; 14px dominant body; single 16px and 21px | medium |
| Tab order | starts inside the docked drawer; includes tabbable static text (“No saved work in this conversation”) | medium |
| Emoji icons | 0 (clean) | — |
| Palette | surfaces `#FFFFFF / #F9FAFB / #F2F3F5`; text `#000000 / #454D5F / #86909C / #A9AEB8` | info |

Scope note: the probe samples two surfaces (boot + work drawer) at 1440×900 in one data state
(~80 text samples per screen). G4/G5/G7 expand the probe to every new surface, both density modes,
and both themes; the pass criteria live in the accessibility standard §6.

## 6. Defects carried into the V1.4 repair list

1. Contrast: replace muted pairs with the `--kel-text-2/3` floors (G4, G9).
2. Focus: global focus ring; 30/30 stops (G4).
3. Type scale: normalize to 12/14/16 + headings (G4, G9).
4. Tab order/structure: skip link; no tabbable static text; nav-first order (G7).
5. Settings redirects (`agent/skills/tools/model` → `#/guid`): replace with real pages or hide the
   entries so keyboard users are never dropped into an unrelated surface (G7).
6. Verification copy: worker-reported vs Kel-verified must be visibly distinct in the UI (G5).
