# V2-12 — Adaptive Staffing 2.0 (2026-09-21)

Increment: the directive's remaining clause — “**Learn from outcome history**: when solo succeeds;
when specialists help; when independent review helps; when parallelism helps; when high assurance is
unnecessary.” — as one bounded, explained step of advice over what actually happened, wired into the
existing staffing decisions. Plus the two acceptance checks this turn asked for (learning removal;
unbrokered recovery).

## What was already true (measured, not assumed)

- `staffing.decide` — the deterministic rule table: D0–D4 ladder, FEATURES/WEIGHTS/bands, hard rules
  R1–R10 (security → Sentinel ≥ D2; release → Release ≥ D2; irreversible → approval + independent
  review ≥ D2; data migration → sequential; caps R8: ≤6 workers, depth ≤2, ≤4 children/agent,
  ≤10 grandchildren/mission), budget classes. D0/D1 are the supported path; D2 exists as the pod
  path; D3/D4 are returned so a caller can refuse explicitly.
- D1 `delegation.delegate` and D2 `pods.run_d2` exist, with builder≠verifier assignment, family
  diversity preference, frozen contracts, budget reservations, and **failure states already written**
  (`team.set_state(assignment_id,'FAILED')` on worker failure in both paths; contracts stay
  append-only, so recovery is a fresh assignment — audit 12 F3).
- Assurance: 15 constitution-level lenses with gating classes; security/privacy/data-integrity/
  release-integrity/adversarial are never-gate insurance and never learned away.
- `learning.py` recorded shadow staffing proposals and performance stats — recorded, never applied.

**The measured gap:** no function read *settled outcome history across missions* into a staffing
decision. The directive's learning clause had no code path.

## What this increment added

| Piece | Where | What it does now |
|---|---|---|
| The learned step | `staffing.outcome_advice(store, features, …)` | Over settled missions at the base tier (joined from `staffing.decided` + `contract.issued` + `task.closed`, blockers from `findings`): ≥minimum (3) missions with blocker-class findings → one step **up**; all clean → one step **down**; mixed → none. One step only, never through a hard rule's floor (R3–R6), never past `tier_max`, R1 and the D3+ decomposability gate; thin history changes nothing and says so. Every outcome carries `reasons` with the counts. |
| `staffing.resolve(store, …)` | same module | `decide` plus the advice, for callers that want both applied within the floors. With no history it is exactly `decide`. |
| D1 path | `delegation.delegate` | Computes the advice, **applies a step down to D0** (“solo was enough” — returns not-delegated with the advice in the response), records any step up as advice (this path carries exactly one specialist), and writes `advice` onto the `staffing.decided` event. |
| D2 path | `pods.run_d2` | Computes the advice, applies a step down to D0/D1 (which then refuses with its explicit “use run_d1” sentence — the honest routing), and records `advice` on both builder and verifier `staffing.decided` events. |

## Rules the increment pins

- **One step, and only one**; never more; lower bounds are the rule table's own floors.
- **Thin history is not evidence** (default minimum 3 settled missions at the same tier).
- **A raise never smuggles a higher tier into a path that cannot honour it** — recorded as advice.
- **Caps and floors are untouched**: R1/R3–R6/R8 and `tier_max` win over history every time.
- **No new systems**: the join reads the events/tables that already exist; no dashboard, no roster,
  no nested delegation, no parallel staffing system.

## Acceptance checks (this turn)

1. **Learning removal beyond disable/enable — satisfied by the existing path.** Directive §15 asks
   to *inspect; correct; remove; temporarily disable; understand why*. Inspect/correct/disable/explain
   were V2-10; **removal** is the existing memory `forget` path (purge + content-free tombstone +
   audit event), reached through the same guarded `/api/memory` action every record uses. New pin:
   `test_v2_learning.SurfaceTests.test_removing_a_learning_through_the_surface_purges_it` — a
   learning recorded through the real service disappears from both the default and the
   `include_disabled` views after `forget`. No new removal path was added.
2. **Recovery evidence for an abruptly stopped, unbrokered run — proved live, distinct from
   broker-backed survival.** On a scratch data root with a real engine running: a run claimed with a
   5 s lease, no broker row, not active in the engine; after the lease expired the **live engine's own
   tick** fenced it — run `ORPHANED`, event detail `{'recovery': 'runtime'}`, job `WAITING_RESOURCE`,
   milestone `UNCERTAIN`. That is categorically different from the V2-11 probe where **seven
   broker-backed runs were adopted across a restart and none was fenced** (`orphaned` total 0): a
   broker-backed run survives because a durable supervisor owns it; an unbrokered abandoned run is
   fenced and never replayed on its own.

## Verification (on the final code of this increment)

- `tests/test_v2_staffing.py` (new, 13 tests) — thin history changes nothing; two settled missions are
  below the floor; blocker history asks for one more step (applied); clean history asks for one fewer
  specialist (applied); a hard-rule floor holds against a lower (security flag → held at D2 with the
  reason); mixed history is not evidence; a raise never breaks the rule table (R1/low-decomposition
  holds D2, `applied False`, reason names the gate); `resolve` applies the legal step and equals
  `decide` without history; graceful when workforce tables are absent; the D1 path applies a step down
  to solo; the D1 path records a raise without smuggling it; the D2 path refuses with its explicit
  routing sentence when history steps down.
- Bounded group (one stack at a time): `test_v2_staffing test_workforce_d1 test_workforce_d2
  test_workforce_parallel test_workforce_assignment test_workforce_assurance test_workforce_learning
  test_v14_team test_v15_roles` → **269 OK** (106 s).
- `test_v2_learning` after the removal pin → **20 OK**.
- Live acceptance probe for the unbrokered fence (see above), scratch root removed after the probe.
