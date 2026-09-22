# Figma status text repair — September 22, 2026

Baseline: `c9606e064b3a3324ff1536ecb8ec1114b22ba8eb`, `ux/v2-shell`.
The user's new Active/Paused reference overrides the earlier framed tags.

| Lock | Preservation contract |
|---|---|
| Structure | Existing screen regions, rows, navigation and control positions |
| Identity | Instrument Sans / SF Pro Text and existing source palette |
| Content | Existing labels and real state; no invented statuses |
| Behavior | Existing handlers, selection, keyboard flows and state persistence |
| Repair | Replace status chip containers with semibold plain colored text |

Correction: remove fill, border, radius and horizontal padding from status labels. Use Instrument Sans 600, 14/20. Reference image pixels give positive `#8FE3B4` and attention `#FFC481`; light mode retains darker semantic colors. Failure text retains its existing error color. History/attention dots are separate indicators and retain the approved New Chat treatment.

Coverage: shared Kel status labels, model availability including dropdowns, scheduled detail status, channel plugin state labels, Diagnostics, Setup and Arco tags. Tag click/remove handlers remain. No new behavior or tests were added for this presentation repair.

Baseline evidence: the user's two attachments and audit-2 built captures. Final evidence is in `evidence/status-text`. The Model and Scheduled fixtures were inspected at 1440x900 and 393x852. Phone statuses align to the right while task metadata wraps below its name. Unavailable model names remain muted; their status labels retain full opacity.

## Verification

- TypeScript and final production build pass.
- Existing browser audit: 14/14 pass; existing model/provider/theme unit checks: 13/13 pass.
- Native Electron check: 1/1 passes.
- Focused computed-style inspection confirms transparent fill, zero border/padding/radius, 600 14/20 Instrument Sans, exact green/amber values, and full status opacity.
- Final mobile alignment check confirms both Active and Paused align to the right edge at 393px with no page overflow.
- The first ad hoc verification attempted navigation before onboarding settled. It timed out before the Appearance control. The corrected harness waits for setup before navigation and passes. No product startup fix is claimed.

## Scoped QA scorecard

| Category | Baseline | Final | Evidence |
|---|---|---|---|
| Hierarchy and comprehension | 5 | 5 | Existing rows, labels and order preserved |
| Typography and readability | 3 | 5 | 11px framed statuses replaced by 14/20 semibold text; amber remains fully opaque |
| Geometry and rhythm | 3 | 5 | Chip padding removed; phone status column remains right aligned |
| Component and interaction craft | 3 | 5 | Shared status styling; existing model and browser interaction checks pass |
| Responsive/accessibility integrity | 4 | 4 | Desktop/phone overflow and keyboard flows checked; no assistive-technology certification |
| Fidelity to approved direction | 2 | 5 | Attached plain-text reference replaces the boxed-chip defect in inspected states |

This is a self-review of the scoped status repair. Individual channel connection states were inspected in source; no external connection was changed. The final 393px scheduled-task capture uses the light theme; the model capture uses the dark theme. Earlier unrelated Figma and runtime gaps remain open.
