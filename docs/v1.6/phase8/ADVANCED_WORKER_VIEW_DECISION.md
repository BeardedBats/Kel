# Phase 8 / 5.8 — Advanced Worker View: V1.6 PRODUCT DECISION

Date: 2026-09-18 · Decider: Program Director (sole, Campaign A) · Status: **DECIDED — DEFERRED
BEYOND V1.6** · Supersedes: `docs/v1.6/phase5/5.8_DECISION_DEFERRED.md` (pending-state record)

## Decision

The Advanced Worker View is **not in V1.6 scope**. V1.6 ships with the North Star intact: **one
capable assistant with hidden orchestration**. No worker-view UI, no panels, no new endpoints are
added for this phase. The existing engine-side data (team events, jobs/milestones/runs/leases,
findings, evidence, routing outcomes — the 5.2–5.4 endpoints) stays as-is, available for a future
decision.

## Evidence considered

- **Design doc 12** (`ux-audit/workforce-os/12_ADVANCED_WORKER_VIEW.md`): "the user should never
  need this view to operate Kel"; success criterion #1 is "100% of ordinary missions complete with
  **zero visits** to the advanced view". It is a research/design package, not a product commitment.
- **Spec entry** (`15_PHASE5_IMPLEMENTATION_SPEC.md` §5.8): the exit gate is a *product decision*
  plus a *usability review* with the zero-visit default preserved. Neither exists; no user-reported
  need exists.
- **Phase 5 record**: only hidden orchestration was implemented, by design; workforce surfaces are
  engine-level with no live caller (F16-3).
- **Sprint directive §33**: "Resolve as one decision. Default North Star: ONE ASSISTANT. …
  If deferred: record exact rationale. … Do not block the sprint merely because optional worker
  visualization is not justified."
- **Sprint economics**: V1.6's remaining release-blocking work (engine-loss UX, P2/P3 sweep, visual
  batches + integration, regression, RC) outranks an optional instrument panel. The spec's own
  "no UI-first" rule forbids building panels before the product decision.

## What ships instead (V1.6)

- Normal mode only: outcome-level progress, the Work panel's existing surfaces (memory knowledge,
  job state, approvals, lineage, capability cards), and the improvements already delivered in
  Phases 0–7 and the visual batches.
- No new worker-visualization surface is referenced by any V1.6 requirement; nothing else changes
  for this phase.

## Re-entry criteria (post-V1.6, recorded for DEF-002)

1. A product decision by Nick that the view is in scope, supported by a usability review.
2. If approved: bounded UI increment behind a setting — **Advanced / Details only**, zero-visit
   default preserved, exportable mission report, derived-only data (doc 12 honesty rules: no
   invented staff, no post-hoc copy, uncertainty first-class, project isolation enforced).
3. No engine changes required beyond small derived queries (doc 12 §4).

## Related: Phase 5.7 (adaptive staffing) — confirmed position

Per sprint §34: no fabrication. The required campaign/sign-off is absent, so 5.7 stays **DEFERRED**
with its recorded activation criteria (`docs/v1.6/phase5/5.7_DECISION_DEFERRED.md`; DEF-001).
Shadow learning remains valid V1.6 behavior. Nothing is built for 5.7 in this sprint.

## Release impact

None. This decision removes an optional surface from the release conversation; it blocks nothing.
Campaign B should treat this decision as a scope disposition to verify (requirement REQ-AWV-8 /
DEF-002), not as an implementation claim.
