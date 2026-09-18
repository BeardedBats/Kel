# Increment — R1: the delegation authority ceiling is executable

increment_id: V16-R1-AUTHORITY-CEILING
invariant: **AUTH-DELEGATION** — delegation may narrow authority; delegation must never create
authority (`effective_child_authority ⊆ effective_delegator_authority`)
requirement: `REQ-R25-R1` (roadmap R2.5 §R1; marathon directive §9)
phase: Campaign A — R1
base_commit: `4440a90`
production_commit: `dc65fbc`
status: complete (full engine regression at this increment — TEST_EVIDENCE_INDEX A-21)

## R1.A — audit of the real current issuance path (before any check was written)

What actually exists (verified in code, not assumed):

- `workforce.py` owns the vocabulary: `AUTHORITY_CLASSES = (read-only, workspace-write,
  leased-write, external-effect)` and `AUTHORITY_RANK`.
- `Team.resolve_role(...)` resolves the role fields (`authority_max`, `tool_policy`) per
  project/task; `assignment.registry_ceilings(...)` turns the seeded archetype registry into a
  role→class table that `validate_task_contract(ceilings=…)` uses.
- `contracts.ROLE_MAX_AUTHORITY` is the static fallback table (`builder` leased-write,
  `verifier` read-only, `release` external-effect, …), and `_enum` refuses a class above the role
  ceiling ('Role X may not hold Y authority (ceiling Z)').
- `delegation._authority_for(role_fields, scope)` derives the contract authority **from the role**;
  `allowed_tools` come from `role_fields['tool_policy']['allow']`; `write_boundaries` = the request
  scope; `parent_task` is **always None** — the design deliberately has no nesting (doc 03; R1.C).
- `assignment.grants_for` / `require_grants` refuse any tool above the authority ceiling via the
  `TOOL_AUTHORITY` mapping (fail-closed, every denial named).
- D1 `delegate()` and D2 `pods.run_d2` are the two issuers; both call `issue_task_contract(...)`
  which validates and appends the frozen row.
- Budget: `core.py` refuses a new milestone when the job envelope is nearly exhausted, and
  `reserve_budget` created the delegation's reservation — but the reservation was never compared
  against the envelope.

Gaps found (each one is a dimension of the invariant that was *not* executable):

1. Nothing tied a child issuance to the issuing context's authority beyond the **class** ceiling:
   write scope, write boundaries, external effects and tool grants had no delegator dimension.
2. A contract could contradict itself: `write_scope` was never checked against `write_boundaries`.
3. `reserve_budget` accepted a cost reservation larger than the remaining job budget, so a
   delegated mission could create budget authority the delegator did not hold.

## Implementation (existing primitives only — no RBAC, no second ACL, no delegation database)

- **`workforce.authority_within(child, parent)`** — pure containment over the contract-carried
  dimensions: authority class rank, write scope, write boundaries (path-prefix containment with
  `./`/backslash normalization; a `.` root contains everything), external effects (`'none'` is the
  empty set), allowed tools (set containment). Absent parent dimensions place no ceiling; an empty
  delegator write scope is a real ceiling. Returns the offending dimension as a human sentence.
- **`contracts.validate_task_contract(..., parent_authority=None)`** — refuses a child that is not
  contained ('Delegation may narrow authority but never create it: <dimension>'), refuses a
  self-contradictory `write_scope`/`write_boundaries` pair, and refuses a contract that declares a
  `parent_task` without a delegator envelope (R1.C: the ceiling survives the day nesting exists).
- **Issuance wiring** — `delegate()` and `issue_task_contract()` accept `parent_authority` and pass
  it through; `pods.run_d2` issues the **verifier inside the mission envelope** (class, write scope
  and effects taken from the builder's frozen authority; tool grants stay role-local so the verifier
  keeps its own read-only tool set). Callers that pass nothing keep the previous behavior exactly.
- **`assignment.reserve_budget`** — refuses a reservation whose cost exceeds
  `job.budget − job.spent − job.reserved` (the budget dimension of the same invariant).

## Previous vs new behavior

| Situation | Before | After |
|---|---|---|
| Child contract class above the issuing context | refused by the **role** ceiling only | refused by role ceiling **and** delegator envelope |
| Child write scope outside the delegator's | accepted | refused (path containment) |
| Child external effect the delegator does not hold | accepted (class permitting) | refused |
| Tool grant outside the delegator's | accepted | refused at issuance (grants path unchanged) |
| `write_scope` outside the contract's own `write_boundaries` | accepted | refused (self-contradiction) |
| Nested contract (`parent_task` set) without a delegator envelope | accepted | refused |
| Reservation larger than the remaining job budget | accepted (caught later at a milestone boundary) | refused at reservation time |

## Failure mode addressed

A delegated mission (or a future nested one) could hold authority its delegator never held —
class, scope, effects, tools or budget — and the only guard was the static role ceiling. Now the
invariant is enforced where authority is actually issued, and the protection survives the addition
of nesting: a `parent_task` cannot be issued without naming the envelope it stays inside.

## Security / privacy / persistence / migration impact

- Security: strictly narrowing — three new refusal classes; no new authority path, no new secret,
  no new network surface.
- Persistence: none (no schema change, no new table, no new column). Frozen contract rows are
  unchanged in shape; only issuance-time validation is stricter.
- Migration: none.

## Tests (evidence-bound)

- `tests/test_v16_r1_authority.py` — **21 new**: primitive (equal/narrow accepted; wider class,
  escaping scope, unheld effect, unheld tool refused; empty scope is a real ceiling; unconstrained
  dimension places none; unknown class), contract-level (narrowing accepted; class/scope/effects/
  tool widening refused with the 'never create it' sentence; self-contradictory scope/boundaries
  refused; nested-without-delegator refused; the plain contract still validates), issuance wiring
  (D1/D2 path carries the envelope; widening refused; unchanged without a parent), budget envelope
  (inside accepted, beyond refused).
- Workforce family: `test_workforce_schemas` / `assignment` / `d1` / `d2` / `learning` /
  `parallel` / `assurance` — 269 passed together (zero regressions from the new checks).
- Full engine: TEST_EVIDENCE_INDEX A-21.

## Limitations / audit questions / repair hints

- **No arbitrary nested spawning was added** (R1.C): `parent_task` remains None in every production
  path; the new refusal is the future-proofing, not a new capability.
- Token/wallclock reservation caps are not enforced against the job envelope — the job record
  carries a single cost-like `budget` float (`core.py:302` compares the same figure), so only cost
  has a delegator-side primitive. Recorded honestly rather than invented; R3 revisits budget
  accounting.
- Audit questions for Campaign B: (1) can any caller construct a contract without passing through
  `validate_task_contract`? (2) does `registry_ceilings` cover every archetype in every project
  scope? (3) is `tool_policy.allow` the right tool-grant source for the *delegator* dimension, or
  should the parent contract's frozen `allowed_tools` be the ceiling instead (it is here when a
  parent envelope is supplied)? (4) `_path_within` treats a `.` root as universal — is that the
  intended meaning of an empty/rooted scope?
- Repair hints: none open from this increment.
