# KEL V1.4 — VISUAL ACCEPTANCE MATRIX

Status: v1 (2026-09-15). The per-surface acceptance ledger consumed at **G4, G5, G7, G9, G10**.
A surface is accepted only with the evidence listed here; source inspection alone never suffices.
Companions: `KEL_V1.4_DESIGN_SYSTEM.md`, `KEL_V1.4_INTERACTION_PATTERNS.md`,
`KEL_V1.4_ACCESSIBILITY_STANDARD.md`, `docs/v1.4/screenshots/**`.

## 0. Columns

Each row: **Surface** · baseline evidence (V1.3) · required states · keyboard · a11y · resize ·
dark mode · final evidence · verdict · gate. Verdict values: `pending` → `accepted` /
`accepted-with-notes` / `rejected`.

## 1. Global gates (apply to every surface)

1. Values come from design-system tokens only (no ad-hoc color/size/space).
2. Zero items from the design-system do-not-ship list (gradients, eyebrow headers, single-edge
   accent borders, card soup, emoji icons, bounce, shimmer, color-only status, uppercase labels, …).
3. Focus ring present on 100% of interactive elements; first tab stop is the skip link.
4. 0 contrast failures on the rendered surface (probe), muted floor respected.
5. Five widths captured (1280×720, 1440×900, 1920×1080, 2560×1440, 1024-class) with no clipping and
   no horizontal scroll.
6. All required states rendered and captured (see §2), including empty, loading, error, and blocked.
7. Before/after screenshots exist (baseline vs final) in `screenshots/comparisons/`.
8. Independent visual reviewer verdict recorded (not the implementer).

## 2. Surface matrix

| Surface | Baseline evidence (V1.3) | Required states | Gate |
|---|---|---|---|
| Main chat + composer + conversation list | `baseline/v13-{empty,fixture}-*.png` (guid/chat) | empty · populated · long · dense · provider-unavailable | G7/G9 |
| Work Center (drawer + tabs; later unified page) | `baseline/…02/03/04/05/06/07*` | empty · running · waiting · verified · uncertain · failed · blocked · dense (>10 jobs) | G4/G9 |
| Approvals (badge + sheet) | `baseline/…02-work-drawer` (badge "1" evidence) | no-approvals · pending · resolved-receipt · expired | G4/G9 |
| Project selection / switcher | `baseline/…01-boot-chat` (project chip) | single project · many · no project | G5/G7 |
| Project knowledge (memory) | `baseline/…04-knowledge` | empty · populated · conflicts · stale · superseded | G5/G9 |
| Project map | `baseline/…05-map`, `…07b` (refresh) | empty · built · stale · refresh-error | G5/G9 |
| Continuation | `baseline/…03-continue` | none · one candidate · chooser · resumed · wrong-project block | G5/G9 |
| Verification & evidence | not captured (engine-side evidence exists) | worker-reported · verified · uncertain · failed-check · flaky · stale · receipt | G5/G9 |
| Recipes | `baseline/…06-recipes`, `…07-recipe-preview` | empty · library · preview · inputs-missing · running · frozen steps · terminal | G5/G9 |
| Team — Office | — (new) | no team · one specialist · many · historical | G4/G9 |
| Team — Roster | — (new) | templates only · template detail | G4/G9 |
| Team — Studio (roles) | — (new) | view · edit · locked sections · version diff · rollback | G4/G9 |
| Providers | donor provider settings (`baseline/…09-settings-*`) | no provider · CLI-only · API-key · installed-not-authed · quota-unknown · unhealthy | G6/G9 |
| Autonomy & Permissions | — (new) | default profile · lease detail · boundary request · revoked · locked-guardrail view | G6/G9 |
| Settings (reorganized) + About | `baseline/…09-settings-*` (11 pages) | each page · unsaved changes · dangerous actions | G7/G9 |
| Onboarding / first-run | `baseline/…01-boot-chat` (donor first state) | fresh install · migrated user (no forced onboarding) | G7/G9 |
| Search + command palette | — (new) | idle · results · no results · keyboard-only | G7/G9 |
| Diagnostics | — (new) | healthy · degraded · export progress · export receipt · orphan found | G8/G9 |
| Tray / notifications / pet / startup-recovery | baseline: `discovery.json` + tests (no window captures) | tray menu · one notification · pet states · recovery banner | G7/G9 |

## 3. Screenshot standards

- Naming: `<tag>-<index>-<view>.png` (existing harness convention) + `manifest.json` with view,
  requested size, actual inner size, route hash, bytes, text sample, and renderer errors.
- Light and dark captured for key surfaces once the dark token set lands (design system §2).
- Captures run through `packaging/capture-screens.cjs` (offscreen, isolated, bounded shutdown,
  zero-orphan check in the manifest). Window captures never steal focus.
- Optional companions: `*-texts.jsonl` (innerText evidence) and `discovery.json` (interactive elements).

## 4. Comparisons

`docs/v1.4/screenshots/comparisons/<surface>-<width>.png` must place baseline and final side by side
(or stacked) with the same state; generated at G9 with a scripted pass, not by hand.

## 5. Verification commands

| Purpose | Command |
|---|---|
| Baseline/final captures | `node packaging/capture-screens.cjs <appDir> <dataDir> <outDir> --tag <tag> --widths …` |
| Direction/mockup renders + audit | `node packaging/render-directions.cjs <outDir> <file.html> …` |
| A11y + keyboard probe | `node packaging/a11y-probe.cjs <appDir> <dataDir> <outDir>` |

## 6. Sign-off protocol

1. UI/UX Expert (role template staffed at G3) inspects the rendered surface and files findings.
2. A separate reviewer (independent visual reviewer + the Sonnet reviewer relay) accepts or returns it.
3. The row is updated with verdict, reviewer, date, and evidence paths.
4. `rejected` rows block the gate they belong to.

## 7. Current roll-up (end of G1)

- V1.3 baseline captured for every surface that exists today (2 × 30 views, five widths, zero errors).
- Direction artifacts rendered + audited (0 contrast failures, 12px floor, 13 focusables each).
- Automated a11y/keyboard probe of V1.3 completed (findings in `KEL_V1.4_UI_AUDIT.md` §5 and the
  accessibility standard §7).
- Implementation verdicts: **pending** (surfaces above land at their gates).
