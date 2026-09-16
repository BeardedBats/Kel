# Design Vetting Sessions — spec generation

## Honesty rule

> Kel never invents an answer. Unresolved material appears as Open / Deferred / explicit assumptions.

`finish spec now` works at any point; partial sessions produce a partial but usable spec.

## Sections (adapted to the template, not generic fluff)

Product objective · Audience and jobs-to-be-done · Design principles (visual direction) ·
Information architecture and navigation · Pages and modules · Behavior and interactions ·
Loading, empty and error states · Responsive behavior · Visual decisions (greybox choices) ·
Rejected alternatives (every considered-but-unchosen option of answered questions) ·
Decision rationale (statement + the option's own reason, notes, custom text) ·
Open decisions (unsure/needs-examples/awaiting-visual/conflicting/unanswered) ·
Deferred and skipped · Recommended assumptions (explicitly labeled, only where an open question
carries a `Recommended` option) · Implementation notes (handoff section) ·
Acceptance criteria (derived one per confirmed decision) · Coverage header
(`Decision coverage: n/m answered`).

## Sources

Decisions and answers come straight from the v15-vetting tables; the markdown builder
(`runtime/kel/vetting_spec.py: build_spec_markdown`) is deterministic and provider-free. Snapshotting
(`finish`) stores the markdown + coverage in `vetting_specs`; `preview spec` rebuilds the current
view without snapshotting.

## Quality gates applied

- A resolved section line ends with the recorded answer and, where one exists, its rationale.
- A section with no resolved answers shows an explicit "Open — …" line instead of pretending.
- The open-answer question's free text appears under its section (e.g. product objective
  deal-breakers) — proven in `tests/test_vetting.py::FinishEarlyTests::test_full_spec_after_every_question`.
- Rejected alternatives give a future reader the design space, not just the winner.
- Recommended assumptions are only emitted where the template actually carries a recommended default.

## Coverage semantics

`answered` counts `ANSWERED`/`PARTIALLY_ANSWERED` (what the spec reports); `handled` also counts
`UNSURE`, `NEEDS_*`, `AWAITING_VISUAL_SELECTION`, `SKIPPED`, `DEFERRED` (what progress shows).
Both numbers come from `coverage_summary` and `_progress` so the panel, the chat line and the spec
can never disagree.
