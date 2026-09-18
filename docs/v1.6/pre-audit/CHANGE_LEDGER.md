# CHANGE_LEDGER — product-behavior changes in the unaudited range

updated: 2026-09-18T16:05Z

Organized by PRODUCT BEHAVIOR, not commits. One entry per behavior change that Campaign A (or the
pending visual integration) delivers. Earlier, already-audited V1.6 arcs are traced in
REQUIREMENTS_TRACEABILITY.md instead — this ledger is what Campaign B must read closely.

Template (all fields required; write `none` explicitly rather than leaving blanks):

```
ID:            CHG-###
Title:
Phase:
User-visible impact:
Internal impact:
Previous behavior:
New behavior:
Primary files:
Primary symbols/functions/classes:
Data/schema changes:
Failure paths:
Security/privacy implications:
Persistence implications:
Expected invariants:        (pointer into INVARIANT_LEDGER.md)
Tests:                      (what proves it, incl. discriminating coverage)
Packaged evidence:          (or `-`)
Known concerns:
Audit questions:            (what should Campaign B attack on this change)
Repair hints:               (pointer into REPAIR_HINTS.md, if any)
```

## Entries

### CHG-001 — Work-panel knowledge actions follow the record's state (+ tombstone placeholder)

ID: CHG-001 · Phase: 6 · Commit: `22f4a3e` · Date: 2026-09-18

- **User-visible impact:** the records list in the Work-panel Knowledge tab shows only actions that
  apply to the record; refused-action errors are no longer reachable; a forgotten record shows
  "Content removed." instead of a blank line.
- **Internal impact:** new pure helper `memoryRecordActions` mirrors the engine guards; the panel
  uses it for the confirm/edit/retract/forget buttons.
- **Previous behavior:** every record rendered all four buttons; the engine refused non-active
  records ("Only an active memory can be corrected/confirmed/retracted") and the error surfaced in
  the panel; forget re-purged tombstones.
- **New behavior:** confirm = active ∧ unconfirmed ∧ 3≤trust≤6; edit = active; retract = active or
  stale; forget = any record except an already-purged tombstone.
- **Primary files:** `desktop/.../chat/KelWorkPanel.tsx`, `desktop/.../kel/memoryRecordActions.ts`,
  `desktop/tests/unit/memory-record-actions.test.ts`.
- **Primary symbols:** `memoryRecordActions`.
- **Data/schema changes:** none.
- **Failure paths:** none added; engine-side refusals remain as defense in depth and are now
  unreachable from these buttons.
- **Security/privacy implications:** none (no capability or scope change).
- **Persistence implications:** none.
- **Expected invariants:** INV-MEM-001; added note — UI guard parity with engine guards.
- **Tests:** 7 unit tests (action matrix); tsc 0; vitest 76→83.
- **Packaged evidence:** — (RC battery asserts the Knowledge tab; recorded gap).
- **Known concerns:** the helper must follow future engine-guard changes (audit target).
- **Audit questions:** can any refused action still be triggered from the UI? Are active-record
  actions unchanged? Does the packaged app render the gated matrix correctly?
- **Repair hints:** `KelWorkPanel.tsx` records map; `memoryRecordActions.ts`.

### CHG-002 — Forget asks for confirmation

ID: CHG-002 · Phase: 6 · Commit: `22f4a3e` · Date: 2026-09-18

- **User-visible impact:** clicking Forget opens a confirmation ("Forget this record? Its saved
  content is removed and cannot be recovered. A blank placeholder stays in the history.") with
  Forget/Cancel; confirming purges as before.
- **Internal impact:** the button is wrapped in an Arco `Popconfirm`; the same `/api/memory`
  action fires on confirm.
- **Previous behavior:** one click purged content irreversibly.
- **New behavior:** two steps; cancel is the default escape.
- **Primary files:** `desktop/.../chat/KelWorkPanel.tsx`.
- **Primary symbols:** records-list render block.
- **Data/schema changes:** none.
- **Failure paths:** none added; errors still surface via the panel's error state.
- **Security/privacy implications:** none; reduces accidental destructive purge.
- **Persistence implications:** none.
- **Expected invariants:** none changed.
- **Tests:** matrix covered by the CHG-001 unit tests; the dialog itself is UI-only (noted).
- **Packaged evidence:** — (RC battery).
- **Known concerns:** dialog copy is English (locale pass owns translations — DEF-013).
- **Audit questions:** verify no bypass path purges without confirmation; verify copy truthfulness.
- **Repair hints:** `KelWorkPanel.tsx` forget button.

### CHG-003 — Capability recommendations (real capabilities, real actions, no nagging)

ID: CHG-003 · Phase: 7 · Commit: `df87903` · Date: 2026-09-18

- **User-visible impact:** when Kel is blocked because a capability is off here, the Work panel
  shows a card: what was paused, why, and Allow once / Enable for this chat / Keep it off. Keeping
  it off changes nothing and dismisses (no re-nag).
- **Internal impact:** new `capabilities.recommendation()` vocabulary; research + coding blocked
  outcomes carry `capability` + `recommendation`; `core` records it on the job milestone (cleared on
  success); `/api/state` carries it to the shell; `KelCapabilityCard` + helpers render/act.
- **Previous behavior:** refusals were a plain sentence; the three actions existed only in the
  Tools control.
- **New behavior:** refusals from the two real effect paths carry the structured recommendation; the
  card renders exactly the engine's actions and nothing else.
- **Primary files:** `runtime/kel/capabilities.py`, `research.py`, `coding.py`, `core.py`;
  `desktop/.../kel/capabilityRecommendation.ts`, `KelCapabilityCard.tsx`, `chat/KelWorkPanel.tsx`.
- **Primary symbols:** `recommendation()`, `capabilityCardActions`, `capabilityActionRequest`.
- **Data/schema changes:** none.
- **Failure paths:** unknown action ids drop; failed API call shows one plain sentence; unavailable
  capabilities produce no card; a live grant suppresses the recommendation.
- **Security/privacy implications:** none added — no state change without the user's action; the
  session-tools gates are unchanged.
- **Persistence implications:** recommendations are milestone data only; nothing new at the policy layer.
- **Expected invariants:** INV-CAPREC-001 (new); INV-CAP-001/002 preserved.
- **Tests:** engine focused 83; engine full 885 (+10 subtests, was 878); tsc 0; vitest 90 (was 83).
- **Packaged evidence:** — deferred (no provider in this environment; LIM-14; audit target 45).
- **Known concerns:** coding-path attachment lacks a dedicated blocked-run test (audit target 44).
- **Audit questions:** can a forged recommendation create a fake action? Does dismissal persist? Does
  the card ever change state without a click?
- **Repair hints:** guard drift vs `capabilities.recommendation`; card request wiring.

### CHG-004 — Canonical Kel logo across every production-reachable branding surface

ID: CHG-004 · Phase: Campaign A branding requirement (Nick directive 2026-09-18) · Commit: branding commit · Date: 2026-09-18

- **User-visible impact:** every mark the user can see is now the exact Nick-supplied folded-ribbon
  K: exe/installer/shortcut icon, taskbar/window, tray + notifications, favicon/apple-touch/PWA,
  login mark, and a new About-screen mark.
- **Internal impact:** `scripts/make-brand-assets.py` derives all sizes from the canonical source
  (sha256-guarded); `resources/app.ico|app.png|app_dev.png|icon.png|app.icns` and
  `public/pwa/icon-180/192/512.png` + the renderer brand mark replace donor art;
  `kel-builder.json` pins the icon per platform/installer and enables `signAndEditExecutable`
  (which also patches the exe icon — it previously never reached `Kel.exe`).
- **Previous behavior:** donor AionUi mark everywhere; the packaged exe carried no patched icon
  (executable editing was disabled).
- **New behavior:** the K everywhere; exe icon verified by extraction from the built package.
- **Primary files:** `scripts/make-brand-assets.py`, `desktop/resources/*` (icons),
  `desktop/public/pwa/*`, `desktop/packages/desktop/src/renderer/assets/logos/brand/app.png`,
  `AboutModalContent.tsx`, `desktop/kel-builder.json`.
- **Primary symbols:** `make-brand-assets.py` (render/write_ico/write_icns); About `brandMark` img.
- **Data/schema changes:** none.
- **Failure paths:** generation refuses a source whose sha256 ≠ canonical (no wrong-image output).
- **Security/privacy implications:** none (static assets).
- **Persistence implications:** none.
- **Expected invariants:** INV-BRAND-001 (new).
- **Tests:** `make-brand-assets.py --check` determinism; tsc 0; vitest 90; packaged exe-icon
  extraction + boot (PACKAGED_EVIDENCE_INDEX `package-logo`).
- **Packaged evidence:** `package-logo`.
- **Known concerns:** dormant NSIS installer text/identifiers and the dead donor `logo.svg` are
  untouched by policy (audit targets 47–49); `package.json` description/author may be intended
  attribution (audit target 49).
- **Audit questions:** any reachable surface still showing the donor mark? Is the 16 px derivative
  legible? Does the extracted exe icon match the shipped `app.ico` frame exactly?
- **Repair hints:** regenerate via the script; the surface table in `docs/v1.6/branding/CANONICAL_LOGO.md`.

Planned Phase-to-CHG mapping (kept current as work lands):

| Phase | Expected CHGs | Status |
|---|---|---|
| 6 — memory reality audit + bounded fixes | CHG-001, CHG-002 delivered (`22f4a3e`); audit record `docs/v1.6/phase6/` | DONE |
| 7 — smart capability recommendations | CHG-003 delivered (`df87903`); record `docs/v1.6/phase7/` | DONE |
| 8 — Advanced Worker View decision | none (decision only; FINAL: deferred beyond V1.6 — `docs/v1.6/phase8/ADVANCED_WORKER_VIEW_DECISION.md`) | DONE |
| 9 — Profiles vs Projects decision/fixes | none (decision only; FINAL: no Profiles concept — Projects remain; `docs/v1.6/phase9/PROFILES_VS_PROJECTS_DECISION.md`) | DONE |
| Canonical logo (Nick directive 2026-09-18) | CHG-004 delivered (branding commit); record `docs/v1.6/branding/` | DONE |
| 10 — real provider validation | none (evidence only; PROVIDER_VALIDATION_MATRIX.md) | PENDING |
| 11/12 — Rust freshness / migration | none expected (verification only) | PENDING |
| F4 real-artifact binding wiring | CHG-0xx | PENDING |
| resolution-kind semantics | CHG-0xx | PENDING |
| P2/P3 sweep | CHG-0xx per fixed finding | PENDING |
| Visual batches 6–8 + integration | CHG-0xx (per batch; see VISUAL_EVIDENCE_INDEX.md) | PENDING |
| Engine-loss/recovery behavior | CHG-0xx | PENDING |
