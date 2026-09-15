# KEL V1.4 — VISUAL DIRECTIONS & SELECTION (Gate 1)

Status: v1 (2026-09-15). Two materially different directions developed, rendered, audited, and
compared through the Best Solution Gate; one direction selected for the Kel design system.

## 0. Inputs and method

- V1.3 packaged baseline: `docs/v1.4/screenshots/baseline/**` (2 × 30 views, five widths, zero renderer errors).
- Automated audit of the packaged V1.3 app (`packaging/a11y-probe.cjs` → `docs/v1.4/screenshots/audit/v13-a11y.json`):
  **6 contrast failures** (muted-on-muted, e.g. `rgb(169,174,184)` on `rgb(242,243,245)` = 2.0:1),
  **smallest text 12px**, **focus indicator missing on 30/30 tab stops** (no outline/box-shadow),
  tab order starts inside the docked drawer and includes tabbable static text, **0 emoji**.
- Brief §11–§12 quality bar (no gradients, no eyebrow headers, no decorative single-edge borders,
  no card soup, no bounce, real type scale, non-color-only states, keyboard + visible focus).
- Craft rules from the design-system skill (no cream/sand defaults, no purple→blue gradients,
  no nested cards, WCAG AA contrast, reduced-motion support).

Both directions were built as static HTML artifacts rendered to PNG at 1440 and 1280 widths, and
audited in-page by `packaging/render-directions.cjs` — same scenario (Work Center + the
waiting-approval job detail + a components strip), so the comparison is apples-to-apples.

| Artifact | File | Rendered |
|---|---|---|
| Direction A (Console) | `docs/v1.4/directions/direction-a-console.html` | `screenshots/directions/direction-a-console-1440.png`, `-1280.png` |
| Direction B (Desk) | `docs/v1.4/directions/direction-b-desk.html` | `screenshots/directions/direction-b-desk-1440.png`, `-1280.png` |
| Audit of both | `screenshots/directions/directions-audit.json` | — |

Measured (same scenario, full page; asserted by the renderer): **both 0 contrast failures, smallest
text 12px, 14 focusable controls, 0 focus-ring failures — every tab stop shows a ring and the first
stop is the skip link — 0 emoji icons, AA-compliant status/action pairs by construction.**

## 1. Direction A — “Console” (dense operator surface, dark graphite + cyan)

**Model.** A professional operations console: permanent left rail, a table-first main column, and an
always-available right inspector. Built for someone who keeps Kel open all day and scans dense work
state without switching context.

- **Layout.** 40px title bar (brand, project chip, local badge, search, window controls) · 196px rail
  (Chat, Work, Team, Projects, Recipes, Search, Settings; count badges) · fluid table column ·
  384px inspector for the selected job.
- **Density.** Row height 36px, 4px spacing base, 12–14px type, tabular numerals everywhere,
  inline state chips, milestone progress as compact bars.
- **Work Center.** One table: Job · State · Current step · Progress · Budget · Updated. Selection
  drives the inspector (milestones, frozen accepted steps, evidence, approval card, budget meter,
  pause/resume, receipt).
- **Tone.** Dark graphite (`#101418 / #161B22 / #1C232C`), text `#E6EDF3 / #A9B6C6`, cyan accent
  `#22B8CF`, ok/warn/danger `#3FB950 / #D29922 / #F85149`.
- **Motion.** 120ms fades only; hover reveals row actions; no bounce, no layout shift.
- **Strengths.** Highest information density; genuine pro-tool feel; excellent for the Work Center,
  Diagnostics, and long logs; one screen answers “what is running, what needs me, what is proven”.
- **Risks / costs.** Dark-first is a heavier migration from the donor’s light surfaces; 13px labels
  and 12px meta sit **below** the brief’s §12 readability bar (body ≥16px, labels ≥14px); a
  permanent inspector consumes ~25% of width at 1280 and needs a collapse rule; scanning many rows
  is efficient but the interface can read as “machine UI” rather than a product a person hosts.

## 2. Direction B — “Desk” (calm workspace, light neutral + emerald)

**Model.** A calm workspace where work objects are cards and every decision opens one focused
sheet with plain language. Built for daily use by one accountable owner who wants to understand,
approve, and trust — not to operate a control room.

- **Layout.** 48px title bar (brand, project picker, “Local · private”, ⌘K hint) · 216px labelled nav
  (Chat, Work, Team, Projects, Recipes / Search, Settings) · single reading column (max 1040px,
  32px gutters) · right-side sheet for detail and approvals.
- **Density.** Comfortable by default: 16px body, 14px labels/controls, 12px meta only for
  timestamps/ids; 6px spacing base (6/12/18/24/32/48); cards only for discrete objects (one card =
  one job), never nested; activity feed as compact airy rows.
- **Work Center.** Verdict-first: h1 “Work”, a one-line summary (“3 jobs in this project · 1 waiting
  on you”), quiet filter pills, then job cards with current-step emphasis, an inline milestone
  checklist (accepted steps marked *frozen*), and a footer with scope/budget/updated plus one
  primary action per state.
- **Approvals.** A dedicated sheet: plain-language summary, the exact pending command in mono,
  Allow once / Deny, and a plain statement of what changes afterwards — the single most important
  trust surface in Kel.
- **Tone.** Neutral light (`#FAFAFB`, cards `#FFFFFF`, borders `#E5E7EB`), text `#14161A / #5A6270 /
  #6B7280`, emerald accent `#0E7C5A`, amber `#B45309` on `#FEF3C7`, danger `#B42318`.
- **Motion.** 160ms ease-out, entrances only; `prefers-reduced-motion` disables all transitions.
- **Strengths.** Meets the readability bar as designed; calm under high information density because
  hierarchy (not borders) carries structure; closest to the donor’s light surfaces → lowest
  migration risk; the approval sheet directly serves the “trustworthy, evidence-backed” doctrine.
- **Risks / costs.** Lower maximum density than A (Work Center shows fewer rows per screen; heavy
  log/diagnostic surfaces need a compact mode); sheets add a step for power users who want parallel
  detail; long lists need pagination/virtualization sooner.

## 3. Best Solution Gate — comparison

Criteria per brief §11.2. Verdicts: **✔** met, **~** partial, **✖** miss.

| Criterion | A — Console | B — Desk |
|---|---|---|
| Clarity (hierarchy, focus) | ~ dense, state-scanning first | ✔ verdict-first summary + one primary action per state |
| Usability for the accountable owner | ~ expert-oriented | ✔ decisions and approvals in plain language |
| Scalability (10–100 jobs, long logs) | ✔ table + inspector scale | ~ needs compact mode + pagination for logs |
| Accessibility (AA, keyboard, focus) | ~ AA contrast held, but 13px labels | ✔ 16/14/12 scale, focus spec, light default |
| Information density | ✔ highest | ✔ comfortable + compact mode |
| Consistency with the Kel model (one voice, evidence, approvals) | ~ reads machine-first | ✔ matches “single accountable manager” doctrine |
| Implementation complexity | ~ new dark theme + inspector + table system | ✔ closest to donor light surfaces + Arco components |
| Fit with existing architecture (AionUI/Arco, theme tokens) | ~ dark token set across all screens | ✔ reuses existing tokens; smallest diff |
| Future extensibility (Team, Providers, Diagnostics) | ✔ console patterns extend naturally | ✔ cards/sheets extend; Team = list + sheet |
| Visual distinctiveness (unmistakably Kel) | ~ distinct but reads “generic dark ops tool” | ✔ distinct through language + hierarchy |
| Risk of clutter | ~ rail + table + inspector crowd 1280 | ✔ one column; detail contained in sheets |
| Dense-data handling | ✔ best in class | ~ good with compact mode |

Tally: A — 5 ✔ / 7 ~ · B — 9 ✔ / 3 ~.

## 4. Decision

**Selected: Direction B — “Desk”, with a documented compact density mode absorbed from A.**

Rationale (evidence-based):
1. The brief’s readability bar (body ≥16px, labels ≥14px) is non-negotiable; A as drawn violates it.
2. Accessibility must be designed, not patched: the V1.3 audit shows 30/30 tab stops without a
   detectable focus ring, 6 contrast failures, and 12px minimum text. B ships AA pairs, a focus
   specification, and reduced-motion by construction.
3. Migration risk: B aligns with the donor’s light surfaces and Arco components — the smallest
   coherent diff across ~30 screens. A would require a full dark token set plus a table redesign.
4. Doctrine fit: approvals, evidence, and plain language matter more than row throughput; B’s
   approval sheet is the trust centerpiece of Kel V1.4.
5. Distinctiveness comes from Kel’s language and hierarchy (frozen steps, wait reasons, receipts,
   evidence classes) rather than a novel color theme.

**Absorbed from A:** compact density mode (same components, tighter spacing/type rows) for the Work
Center table, Diagnostics, and logs; tabular numerals for metrics; inline state chips; row hover
actions; budget meter as a compact bar; monospace treatment for commands/evidence.

**Rejected from A (with reasons):** dark-first default (migration cost, no user mandate); 13px
label scale (below bar); permanent inspector (crowds 1280); cyan-on-graphite identity (generic
ops-tool look).

## 5. Evidence that would change this decision

- An explicit owner preference for a dark console as the daily driver (single decisive signal).
- A rendered B that fails real Work Center/Diagnostics density even with compact mode.
- Implementation-time audit failures inside B at G4/G5 (forces iteration, not reversal).
- 2560-width usability evidence that the reading column wastes space (mitigation: 1040→1200px
  column, not a redesign).

## 6. Constraints honored by both artifacts

No gradients · no emoji icons · no bounce/elastic easing · no nested cards · AA contrast verified
in-page · status never color-only (dot + label + chip text) · reduced-motion rule present · 12px
floor for meta text · real type scale · running / waiting / verified / uncertain states all
represented in the components strip.

## 7. Reproduction

    PLAYWRIGHT_MODULE=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/node_modules/playwright \
    PLAYWRIGHT_BROWSERS_PATH=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/browsers \
    node packaging/render-directions.cjs docs/v1.4/screenshots/directions \
      docs/v1.4/directions/direction-a-console.html docs/v1.4/directions/direction-b-desk.html

## 8. Reviewer disposition

- Gate 1 checkpoint (independent design critique + Sonnet reviewer relay) is recorded in
  `KEL_V1.4_STATUS.md` on completion of Gate 1.

## 9. Independent review record (Gate 1)

Independent design reviewer (delegated, 2026-09-15) verdicts:

| Question | Verdict | Resolution |
|---|---|---|
| Materially different directions? | **PASS** | dark table + inspector vs light cards + sheet — layout model, density, and tone differ |
| B + compact the better choice? | **PASS** | B targets the audit failures (16/14/12 scale), reuses donor/Arco light surfaces, approval sheet serves the doctrine |
| Generic AI tells? | **PASS after fixes** | removed A’s decorative inset accent bar; replaced B’s 12px “Workspace/System” rail labels with neutral dividers; sentence-cased the uppercase strip label |
| Design-system completeness | **CONCERN → addressed** | added loading-vs-disabled button spec, overlay height/scroll caps, meter threshold labels, `prefers-contrast`/forced-colors rules |
| Risk 1 — Uncertain styled like Verified | **FIXED** | B’s Uncertain chip now uses the amber/dashed pair (`#5A4200` on `#FFF7E0`) and the string “Uncertain — needs evidence” |
| Risk 2 — focus claim not asserted | **FIXED** | `render-directions.cjs` now presses Tab and fails unless every stop has a computed ring and the first stop is the skip link; both directions pass (0 failures) |
| Risk 3 — audit breadth (2 screens, 1 state) | **RECORDED** | scope note added to `KEL_V1.4_UI_AUDIT.md`; the probe expands at G4/G5/G7 across surfaces, densities, and themes |

The review’s required-before-close item (focus assertion + re-render + attached result) is satisfied:
`screenshots/directions/directions-audit.json` reports `focus.focusRingFailures = 0` and
`focus.firstStopIsSkipLink = true` for both directions.
