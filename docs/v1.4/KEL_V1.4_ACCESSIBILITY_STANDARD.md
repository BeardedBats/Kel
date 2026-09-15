# KEL V1.4 — ACCESSIBILITY STANDARD

Status: v1 (2026-09-15) · Target: **WCAG 2.2 AA** for every Kel surface (new and inherited) ·
Normative for G4–G10; verified by `packaging/a11y-probe.cjs` + `packaging/render-directions.cjs`
and recorded in `KEL_V1.4_VISUAL_ACCEPTANCE_MATRIX.md`.

## 1. Perceivable

- **Contrast.** Body/label text ≥ 4.5:1 against its actual background; ≥ 3:1 for ≥24px text or
  ≥18.66px bold; non-text indicators (borders, dots, meters, focus rings) ≥ 3:1. Use design-system
  tokens only; the muted-text floor is `--kel-text-2` for anything that carries meaning.
- **Never color alone.** Status = dot + label + color (+ icon where space allows). Budget meters
  include a numeric label. Diff/apply states include words.
- **Icons.** Decorative icons are `aria-hidden`; icon-only controls require an accessible name
  (`aria-label` or tooltip + `aria-label`). No text baked into images.
- **Reflow & zoom.** At 200% zoom and at the 1024px floor, no content is lost and no horizontal
  scrolling is required on supported surfaces (tables drop columns per the density rules).
- **Text spacing** overrides (line-height 1.5, paragraph spacing 2×) must not clip content.

## 2. Operable

- **Full keyboard access.** Every interactive element is reachable in a logical order and operable
  with Enter/Space/Arrows; this includes job controls, approvals, sheet contents, table row actions,
  filters, settings forms, and the tray/notification actions that exist in-window.
- **Visible focus.** Every focusable element shows the focus ring (`2px #0E7C5A`, 2px offset; dark
  `#2FA37C`). The V1.3 audit measured **0 of 30** tab stops with a detectable ring — V1.4 requires
  30/30 with a ring and a screenshot of the first three stops (`screenshots/audit/*-focus-*.png`).
- **No keyboard traps.** Sheets/dialogs trap focus only while open and always release on Escape or
  close; focus returns to the invoking control.
- **Skip link.** First tab stop is “Skip to main content”.
- **Order.** Global nav → page content → open overlay. Static text and chips are never tabbable
  (V1.3 had tabbable static text in the drawer).
- **Targets.** Interactive targets ≥ 24×24px CSS (controls are 32/36px; icon buttons 28px minimum).
- **Time.** Approvals show expiry but never auto-resolve destructively; a job waits. No timed tasks
  that require a decision under 20 seconds.
- **Motion.** `prefers-reduced-motion: reduce` disables transitions/animations; no parallax, no
  auto-play, no shimmer.
- **Pointer alternatives.** Nothing requires hover or drag to complete; hover reveals are also
  reachable by focus.

## 3. Understandable

- Plain sentence-case language; the exact status strings are fixed by the design system
  (`Running…`, `Waiting on you`, `Frozen`, `Verified`, `Uncertain — needs evidence`,
  `Failed — see cause`, `Blocked by guardrail`).
- Consistent navigation and naming across old and new surfaces; the same object has the same name
  everywhere (job, milestone, step, evidence, receipt, lease).
- **Errors** state which field/step failed, the cause, and the fix; never a bare toast. Validation
  messages persist until resolved.
- **Destructive actions** (cancel job, delete memory, revoke lease/credential, discard recipe run)
  require explicit confirmation naming the consequence and the rollback.
- No duplicated status copy; each fact appears once per surface.

## 4. Robust

- Semantic structure: `nav`, `main`, `header`, real `table`/`th scope`, real `button`, real `input`
  with `label`. Components prefer native elements over ARIA (see the design-system component briefs).
- Job state changes announce via a polite live region; **approval required** may announce once,
  assertively, and must also be visible persistently (badge + Work).
- Sheets/dialogs set initial focus to the title or first control, and restore focus on close.
- Icon-only buttons always expose a name; counts/badges include text (`aria-label="3 jobs"`).
- No ARIA that overrides native semantics; no `tabindex` on static text.

## 5. Role-based acceptance walkthroughs

1. **Keyboard-only user**: launch → skip link → nav → Work → open a job → approve a waiting job →
   open receipt → open Team Office → open Studio → edit a role field → save → close sheet. All with
   visible focus throughout.
2. **Screen-reader user**: same walkthrough with names announced for every control; job state change
   announced once; approval sheet announces its purpose on open.
3. **Low-vision user**: at 200% zoom and at 1024px floor, all of the above remains operable with no
   clipping or horizontal scroll, and muted text remains AA.

## 6. Verification protocol (per gate)

| Check | Method | Pass criteria | Evidence |
|---|---|---|---|
| Contrast | `a11y-probe.cjs` (in-page WCAG math) | 0 failures; muted floor respected | `screenshots/audit/v13-a11y.json` (V1.3), V1.4 equivalent |
| Focus visibility | probe + focus screenshots | 30/30 stops ringed; first stop = skip link | focus PNGs + probe JSON |
| Type scale | probe font histogram | body 16 / labels 14 / meta 12 only | probe JSON |
| Keyboard paths | walkthrough #1 scripted in Playwright at G9 | all steps reachable; Escape/Enter behave | G9 evidence bundle |
| Non-color status | visual + DOM check | dot + label present for every status | acceptance matrix rows |
| Zoom/reflow | 200% zoom + 1024px run captured at G9 | no loss/scroll | G9 captures |

## 7. V1.3 gaps → required fixes

| Gap (measured) | Required fix | Owner gate |
|---|---|---|
| 6 contrast failures (muted-on-muted, 2.0–3.1:1) | adopt `--kel-text-2/3` floors | G4, G9 |
| 0/30 tab stops with focus ring | global focus-ring token + per-component rule | G4 |
| Tabbable static text; tab order starts in drawer | structural order fix + skip link | G7 |
| 12px minimum text; 12.5px oddity | normalize to the 12/14/16 scale | G4, G9 |
| Settings redirects (`agent/skills/tools/model` → guid) confuse keyboard users | explicit nav semantics; redirects replaced by real pages or hidden entries | G7 |

## 8. Exceptions

None. Any future exception must be recorded here with reason, user impact, and mitigation, and it
must be approved at the gate where it appears.
