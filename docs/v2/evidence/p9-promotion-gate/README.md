# Priority 9 — Kibble Build Update: scope resolution and the promotion gate's door (2026-09-21)

## The measured problem: the item is undefined in the durable directive

`Kibble` appears **nowhere** in `MARATHON_DIRECTIVE.md` or `ROADMAP.md`, and nowhere in the runtime
or desktop source. Its only in-repo placement is the parallel-ownership section of
`MARATHON_STATE.md`, where **Ramble/Kibble presentation is Astra's Shell lane**. The queue line this
marathon has been carrying (“Kibble Build Update backend foundation: dev mission schema, candidate
model, promotion gate”) is therefore the only definition that exists, and two of its three terms —
what a *dev mission* is and what a *candidate* is — describe a product concept, not a backend
contract. Guessing them would invent a subsystem the directive never asked for.

## What the queue line's third term already has (measured)

- **The promotion gate exists**: `learning.queue_promotion` records a `proposal.queued` event with
  the request and its basis, and the module's own rule is *“recorded, never applied: promotion is
  gated on the doc-13 evaluation campaign and explicit user judgment.”*
- **Shadow proposals exist**: `learning.shadow_proposal` records a `staffing.proposed` event with its
  prediction and confidence — also never applied.
- **What was missing**: a door to *see* them. Nothing in `service.py` referenced either queue.

## What this increment added (bounded, read-only)

| Piece | Where | What it does now |
|---|---|---|
| Promotions door | `Team.apply({action:'promotions', project_id})` | The queued promotion requests, project-scoped, newest-first, with the honest note “Recorded, never applied: promotion needs your explicit decision.” |
| Shadow door | `Team.apply({action:'shadow', project_id, mission_id})` | The shadow staffing proposals with their predictions, filterable by mission, with “Recorded with predictions; nothing here has been applied.” |

Both are reads over the existing append-only event streams; they write nothing (pinned).

## Verification

- `tests/test_v2_kibble_gate.py` (new, 5 tests) — an empty queue reads as zero with the honest note;
  a queued promotion is visible and **project-scoped**; a shadow proposal is visible with its
  prediction and mission filter; **the door is read-only** (team_events and memories counts
  unchanged by reads); and with the shadow flag off nothing is recorded, so the door stays empty
  (the existing parity rule).
- Bounded group on the final code: `test_v2_kibble_gate test_workforce_learning test_v14_team
  test_v2_staffing test_v15_roles` → **67 OK** (19 s).

## What is deferred, and why (recorded, not removed)

- **The dev-mission schema and the candidate model** wait on Nick's definition of a Kibble Build
  Update (what a dev mission *is*, what a candidate *is*, what “build update” means for the product).
  This is a genuine user-required definition, not an engineering gap: the durable directive does not
  contain it, and Ramble/Kibble presentation belongs to Astra's Shell lane. **The requirement stays
  in `MARATHON_STATE.md` and `RESUME.md`; the KIBBLE item is NOT marked complete.**
- What a later run may do without that definition: nothing that invents the concept. When Nick
  defines it, the shape is already waiting — a dev mission recorded through the existing
  mission/event streams, candidates as shadow-style proposals with predictions, and promotion through
  this same gate and its door.

## D-44 (recorded in DECISIONS.md)

The decision text lives in `docs/v2/DECISIONS.md` as D-44: the scope resolution, the read-only door,
and the explicit deferral with its reason.
