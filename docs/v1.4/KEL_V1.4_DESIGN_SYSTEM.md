# KEL V1.4 — DESIGN SYSTEM

Status: v1 (2026-09-15) · Base direction: **B — “Desk”** (light neutral + emerald), with the compact
density mode absorbed from Direction A. Product specification: this file (plus the `--kel-*` token
names). A machine-readable token board will be generated when the design tooling is available
in-session. Rendered references: `docs/v1.4/directions/*.html` and
`docs/v1.4/screenshots/directions/*.png`.

Everything below is normative: implementation at G4/G5/G7/G9 must derive values from these tokens,
not from ad-hoc values. Token names are the contract (`--kel-*`).

## 1. Principles

1. **One voice.** Kel speaks in one consistent, plain voice across chat, panel, sheets, and errors.
2. **Evidence over decoration.** No gradient, glow, or ornament that does not carry meaning.
   Evidence, receipts, and frozen steps are the visual language of trust.
3. **Calm under density.** Let whitespace and hierarchy carry structure; use borders sparingly;
   never nest cards. High-density data uses the compact density mode, not smaller fonts.
4. **Keyboard-first.** Every action reachable and visible by keyboard; focus always visible.
5. **Language carries meaning.** Status words (running, waiting on you, frozen, verified, uncertain,
   blocked) are part of the design system, not free copy.

## 2. Color tokens

**Light (default).** Surfaces: `--kel-surface-0 #FAFAFB` (app), `--kel-surface-1 #FFFFFF` (cards/panels),
`--kel-surface-2 #F2F3F5` (insets, table headers), `--kel-border #E5E7EB`, `--kel-border-strong #D1D5DB`.
Text: `--kel-text-1 #14161A`, `--kel-text-2 #5A6270`, `--kel-text-3 #6B7280` (meta only, ≥4.5:1 on
surface-0/1), `--kel-text-inverse #FFFFFF`. Accent: `--kel-accent #0E7C5A`, `--kel-accent-hover #0B6849`,
`--kel-accent-soft #E8F5EF`.

**Dark (supported via token set).** `--kel-surface-0 #101418`, `--kel-surface-1 #161B22`,
`--kel-surface-2 #1C232C`, `--kel-border #263040`; text `#E6EDF3 / #A9B6C6 / #7D8B9E`;
accent stays emerald `#2FA37C` for dark surfaces. Dark mode is a token swap; components do not branch.

**Semantic status** (each = fill + border + text + icon + label; never color alone):

| Status | Light text | Light fill | Meaning |
|---|---|---|---|
| Running | `#0B6849` | `#E8F5EF` | worker active, evidence pending |
| Waiting on you | `#7A4A00` | `#FEF3C7` | approval or decision required |
| Verified | `#0B6849` | `#E8F5EF` (with check icon) | evidence accepted by Kel |
| Uncertain | `#5A4200` | `#FFF7E0` (dashed border) | evidence thin; explanation required |
| Failed | `#B42318` | `#FEF3F2` | check failed; cause + fix attached |
| Blocked | `#B42318` | `#FFFFFF` (strong border) | guardrail or dependency stop |

**Contrast rules.** Muted text floor 4.5:1 on its own surface; large text 3:1 minimum; non-text
indicators (borders, dots, meters) 3:1 against adjacent surfaces. The V1.3 failures this replaces:
`rgb(169,174,184)` on `#F2F3F5` (2.0:1) → `--kel-text-3 #6B7280`; `rgb(134,144,156)` (2.92/3.1:1) →
`--kel-text-2 #5A6270`; muted-on-muted buttons (“Work in a project”) get `--kel-text-2` minimum.

## 3. Typography

Stack: `"Segoe UI Variable Text","Segoe UI",system-ui,sans-serif`; mono:
`"Cascadia Code",Consolas,monospace` (commands, digests, evidence). Numerals: tabular for metrics.

| Token | Size / line-height | Weight | Usage |
|---|---|---|---|
| `--kel-type-h1` | 32 / 40 | 650 | page titles (Work, Team, Settings) |
| `--kel-type-h2` | 24 / 32 | 620 | section titles, sheet titles |
| `--kel-type-h3` | 18 / 26 | 600 | card titles, group headers |
| `--kel-type-body` | 16 / 25 | 400 | body copy, cards, chat |
| `--kel-type-label` | 14 / 20 | 500 | nav, buttons, field labels, table cells |
| `--kel-type-meta` | 12 / 16 | 500 | timestamps, ids, counts (never for decisions) |

Rules: body never below 16px on reading surfaces; labels never below 14px; 12px restricted to
non-meaningful meta; no uppercase transforms; headings tighten (`letter-spacing:-0.1px`), body
stays default; no more than 3 weights in one view (400/500/600–650).

## 4. Spacing, layout, responsive bands

Spacing scale (6px base): 6 / 12 / 18 / 24 / 32 / 48 / 64. Page gutter 32px; card padding 24px;
control padding 12/16px; rail width 216px; rail collapses to 64px icon rail below 1280px; detail
sheet 400px (overlay ≤1440, side-by-side >1440 only if the reading column still fits).

| Width band | Behavior |
|---|---|
| ≥1920 | reading column widens to 1200px; optional side-by-side sheet |
| 1440–1919 | 1040px column; sheet overlays with scrim |
| 1280–1439 | rail collapses to icons on demand; sheet overlays; no horizontal scroll |
| 1024–1279 | single column; nav as overlay; tables switch to compact mode automatically |
| <1024 | not a supported product target (desktop-first); layout degrades without clipping |

Tables never require horizontal scrolling at supported widths; they lose columns progressively
(Updated → Budget → Current step) rather than scroll.

## 5. Shape and elevation

Radius: `--kel-radius-card 10px`, `--kel-radius-control 8px`, `--kel-radius-chip 999px`.
Borders: 1px `--kel-border` for separation; `--kel-border-strong` only for inputs and focus-adjacent
surfaces. Decorative single-edge accent borders are prohibited. Elevation: exactly two shadows —
`--kel-shadow-card 0 1px 2px rgba(20,22,26,.05)`, `--kel-shadow-sheet 0 12px 32px rgba(20,22,26,.16)`;
dialogs reuse the sheet shadow. No glows, no gradients.

## 6. Density modes

Same components; tokens flip only.

- **Comfortable (default)**: row height 44px, cell text 14px, card padding 24px, section gap 24px.
- **Compact** (`data-density="compact"`, used by Work Center tables, Diagnostics, logs):
  row height 36px, cell text 14px with 12px meta, padding 12/16px, section gap 12px,
  tabular numerals required. Compact mode never reduces below the type-scale minimums.

## 7. Components (normative briefs)

- **Buttons.** Sizes 32px (default) / 28px (compact tables); variants: primary (accent bg, white
  text), secondary (surface-1 + border), quiet (text-only), danger (surface-1, danger border/text;
  filled danger only inside destructive dialogs). States: rest/hover/active/focus/disabled/loading
  (label + inline spinner, width stable). Exactly one primary action per view.
- **Status chips.** Dot + label; 14px text (12px in compact); never color alone.
- **Inputs.** Label above (14px/500), control 36px (32 compact), helper 12px, error = icon + text +
  `aria-describedby`. Never placeholder-as-label.
- **Tables.** Sticky header (`surface-2`, 14px label); row hover `surface-2`; sortable columns with
  caret; row actions on hover/focus and always keyboard reachable; compact mode for >10 rows;
  pagination ≥50 rows; empty state rendered inside the table body.
- **Cards.** One card = one discrete object (job, project, specialist); never nested. Card header
  (title + status chip), body (2–4 facts), footer (meta + actions).
- **Sheets (right side).** 400px, scrim `rgba(20,22,26,.32)`, Escape closes, focus trapped,
  focus returns to the invoker. Used for approvals, job detail, specialist detail, settings forms.
- **Dialogs.** Only for destructive/irreversible confirmation and first-run flows; max one at a
  time; destructive confirm uses danger styling and states the rollback.
- **Toasts.** Bottom-right, max 2 stacked; 4s auto-dismiss for info; errors persist with an action
  (“Open receipt”). A required decision is never toast-only.
- **Meters.** Budget bar (fill on `surface-2`, 3:1 border) plus numeric label; thresholds are never
  color-only.
- **Empty states.** Title + one-line why + one action (“No unfinished work in this project.”).
- **Loading.** Static skeletons that match the final layout (no shimmer), preserving row rhythm and
  never reflowing when data arrives; long operations show a status line with elapsed time.
- **Error states.** Cause + fix + evidence link, failed-pair tokens + icon; never a bare toast.
- **Blocked states.** Strong-border card naming the guardrail, the plain reason, and what would unblock.
- **Status language (exact strings).** `Running…` · `Waiting on you` · `Frozen` · `Verified` ·
  `Uncertain — needs evidence` · `Failed — see cause` · `Blocked by guardrail`. Sentence case, no
  jargon, no exclamation marks.
- **Button loading vs disabled.** Loading = spinner + unchanged label + stable width. Disabled =
  `opacity .55` + `cursor:not-allowed`. Use `aria-disabled` (focus retained) only for toolbars that
  must keep focus; loading and disabled must never look identical.
- **Overlay sizing.** Sheets/dialogs cap at `min(720px, 100vh - 96px)`, scroll internally, and never
  grow the page; sheet width 400px (420px at ≥1920).
- **Meter thresholds.** Meters always pair the bar with a numeric label (`3 of 8 steps used`); a
  near-limit state adds a text warning + icon, never color alone.
- **Contrast modes.** Under `prefers-contrast: more` or forced-colors, borders switch to
  `--kel-border-strong`, the focus ring uses `CanvasText`/`Highlight`, and every semantic fill keeps
  its text label.

## 8. Iconography

Library: `@icon-park/react` (already in the donor shell) — one library only. Sizes 16/20/24 (button
16, nav 20, page header 24), stroke 1.6, `currentColor`. No emoji anywhere in product UI (baseline
0). Nav items always keep a label or an `aria-label` when the rail collapses.

## 9. Motion

Durations: 120ms (state), 160ms (entrance), 200ms (sheet/dialog). Easing `cubic-bezier(.2,0,.2,1)`.
**No** bounce, elastic, or overshoot. Entrance = fade + ≤8px translate; no hover movement of layout;
no shimmer; no animated gradients. `prefers-reduced-motion: reduce` disables all transitions.

## 10. Focus and keyboard

- Focus ring: `2px #0E7C5A` outline + `2px` offset (dark: `#2FA37C`); on filled accent controls use
  a white inner ring plus accent outer. Applies to every interactive element — this is the fix for
  the V1.3 audit (0 of 30 tab stops had a detectable ring).
- Skip link is the first tab stop (“Skip to main content”), visible on focus.
- Tab order: global nav → page content → open sheet/dialog (trapped) → back. Chips and static text
  are never tabbable.
- Keys: Escape closes sheet/dialog/drawer; Enter/Space activate; arrows navigate tables/menus;
  `/` focuses search; `Ctrl+K` opens the command palette (G7).

## 11. Accessibility

Normative details: `KEL_V1.4_ACCESSIBILITY_STANDARD.md`. The system guarantees the inputs:
AA-verified tokens, visible focus, non-color-only status, ≥24px targets, reduced motion, no text
below 12px.

## 12. Do-not-ship list (review checklist)

No gradients · no glassmorphism/glow · no eyebrow headers · no decorative single-edge accent borders ·
no card soup or nested cards · no emoji icons · no bounce/elastic easing · no shimmer · no
low-contrast secondary text · no color-only status · no tiny metadata pressed into poor layouts ·
no uppercase labels · no horizontal scroll at supported widths · no modal spam · no dead navigation ·
no fake live data · no placeholder screen shipped as “done”.

## 13. Implementation notes

- Tokens live as CSS custom properties (`--kel-*`) plus a TS object for the renderer. Arco mapping:
  `primary` → `--kel-accent`; `warning` → waiting pair; `danger` → failed pair; radius → control
  radius; font sizes → the type table.
- Density switch: `data-density` on the app root; both modes are screenshot-verified.
- A machine-readable token board (`DESIGN.md` at the repo root) will be generated when the design
  tooling is available in-session; until then this document plus the `--kel-*` token names are the
  source of truth, and the two must not disagree once the board exists.
- Screenshot verification standard: five widths × states (empty/loading/error/populated/waiting/
  verified/uncertain/failed/blocked) captured by `packaging/capture-screens.cjs` with manifests.

## 14. Verification and V1.3 → V1.4 delta

| Measure | V1.3 (audited) | V1.4 target | Evidence |
|---|---|---|---|
| Contrast failures (sampled) | 6 | 0 | `render-directions.cjs`, `a11y-probe.cjs` |
| Tab stops with focus ring | 0 / 30 | 30 / 30 | focus probe + screenshots |
| Smallest text | 12px | 12px (meta only) | font histogram |
| Body text | 14px dominant | 16px body / 14px labels | font histogram |
| Emoji icons | 0 | 0 | audit |
| First tab stop | docked drawer | global nav + skip link | focus probe |

Gate: implementation passes only when `packaging/a11y-probe.cjs` reports 0 contrast failures,
0 missing focus rings, and a type histogram matching the scale above.
