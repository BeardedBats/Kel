# KEL V1.4 — UI AUDIT (v0)

Status: v0 — method + preliminary source-level observations. **No rendered capture yet.** Per brief
§11.6, source inspection alone never proves UI quality — nothing here is a verdict, and the audit
is not complete until packaged screenshots, state matrix, keyboard, resizing, and accessibility
checks have run.

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

- [ ] Packaged audit at all five widths
- [ ] State matrix captured (all states above)
- [ ] Defect list with severity + screenshot evidence
- [ ] Inherited-Aion surface list vs Kel-identity target
- [ ] Keyboard/focus audit
- [ ] Accessibility audit (contrast, labels, non-color states)
- [ ] Baseline screenshot set committed under `docs/v1.4/screenshots/baseline/`
