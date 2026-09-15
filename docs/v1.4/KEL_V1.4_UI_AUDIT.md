# KEL V1.4 — UI AUDIT (v0.2 — capture evidence collected)

Status: v0.2 (2026-09-15). Packaged baseline captures are **complete** (frozen V1.3 copy, isolated data
roots, five widths, zero renderer errors — `docs/v1.4/screenshots/baseline/`). This audit is still NOT
a visual verdict: the aesthetic review requires a vision-capable pass (see §4 limitations); keyboard and
full state-matrix checks expand in Gate 1.

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
4. **No visual harness in-repo yet** — `desktop/playwright.config.ts` exists but `desktop/node_modules` is absent; first harness run must also confirm the packaged app's zero-page-error baseline.

## 3. Checklist for the full audit (brief §11.1 + §11.7)

- [x] Packaged audit at five widths (boot + drawer views; per-view matrix widens in Gate 1) — captures committed
- [~] State matrix: empty + populated + approval-visible + paused-work captured; provider-unavailable, dialogs, pet windows pending
- [ ] Defect list with severity + screenshot evidence (Gate 1)
- [ ] Inherited-Aion surface list vs Kel-identity target (Gate 1)
- [ ] Keyboard/focus audit (Gate 1 + G7)
- [ ] Accessibility audit (contrast, labels, non-color states) (Gate 1 + G7 + G9)
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
