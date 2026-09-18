# Increment — R4: canonical approval binding (APPROVAL-EXACT)

increment_id: V16-R4-APPROVAL-EXACT
invariant: **APPROVAL-EXACT** — approval authorizes an exact canonical runtime action under
explicit relevant preconditions (and only inside its window)
requirement: `REQ-R25-R4` (roadmap R2.5 §R4; marathon directive §12)
phase: Campaign A — R4
base_commit: `1a9f538`
production_commit: `8c899c8`
status: complete

## R4.A — the real approval producers and consumers (inventory first)

Producers:

| Producer | Canonical action it binds | Extra safety |
|---|---|---|
| `Store.request_approval(job_id, run_id, action, seconds=300)` (`core.py:698-708`) | `digest(action)` stored on the row + `approval.requested` event | requires a matching RUNNING run; sets the run `WAITING_APPROVAL`; the job goes `AWAITING_USER` |
| `coding.CodingAdapter.approval(...)` (`coding.py:120-155`) | method + workspace + command + permissions + grantRoot + network, **delivery ids and timestamps excluded by construction**; file changes carry the patch | a file-change request without patch details is marked `unrepeatable_request` (no reusable wildcard); an identical prior action for the same run reuses its approval id; a lapsed wait resolves DENIED |
| `Authorizer._expansion(...)` (`authorize.py:298+`) | `boundary_expansion_requests(request_id, lease_id, scope, target, status)` | outside the lease: reuse a pending request, honour a denial, or ask once |
| `Context.grant(project_id, action, seconds=86400)` (`context.py:90-100`) | `(project_id, action_digest)` unique row with expiry + `revoked` | a remembered grant never outlives its window and is revocable per project |

Consumers / execution-time revalidation:

| Consumer | What it validates immediately before the effect |
|---|---|
| `Store.resolve_approval` (`core.py:711-722`) | actor is the user; row exists; status `PENDING`; `action_digest == digest(action)`; run is `WAITING_APPROVAL`; sets `EXPIRED` when the window already closed |
| `Authorizer._approval_ok` (`authorize.py:275-296`) | status `APPROVED`; `action_digest == digest(action from the intent)`; matching job; **and (repaired here) still inside the approval window** |
| `Context.allowed(project, action)` | grant row for the exact digest, not revoked, not expired |
| `coding.approval` wait loop | re-reads the row; a non-PENDING status decides; expiry while waiting resolves DENIED |

## The one gap (and the minimal repair)

`Authorizer._approval_ok` checked status, digest and job but **not the window**: a decision taken
shortly before `expires` kept authorizing the same action afterwards. The invariant says an approval
authorizes an action *under its preconditions* — the window is one of them.

Repair: the row must still be inside its window at the moment of execution. Nothing else changed: the
digest binding, the job binding and the user-only resolution stay exactly as they were. No HMAC, no
signature, no second approval system (the directive's R4.D: digest matching inside Kel's trusted
local runtime is sufficient).

## Hostile tests (this increment)

`tests/test_v16_r4_approval_exact.py` — **7 new**:

1. An approval authorizes only its exact action (a changed command is refused; a changed workspace —
   the "equivalent path spelling" attack — is refused).
2. An approval copied to another job is refused.
3. A PENDING approval never authorizes execution.
4. An approval outside its window is refused (the repaired check).
5. Resolving after the window records `EXPIRED`, never `APPROVED`.
6. A second resolution is refused.
7. A remembered grant is project-scoped, digest-exact, and revocation takes effect immediately.

Focused: the authorization family (authorize, coding boundaries, coding recovery, coding transport,
approvals) + R4 = **96 passed**. Full engine: TEST_EVIDENCE_INDEX A-23.

## Limitations / audit questions / repair hints

- `_approval_ok` is the boundary/authorize consumer; the coding path consumes through
  `resolve_approval` (window checked at resolution) and the wait loop (window checked while waiting).
  Campaign B should attempt: an approval resolved 1 ms before expiry consumed 1 s after (refused
  now); a remembered grant restored by re-approving the same action (by design — the grant is the
  memory of an explicit decision, and it is revocable).
- Expiry comparison uses wall-clock time in the same process; clock jumps are out of scope for V1.6.
- Audit questions: (a) is `seconds=300` the right default for coding asks, and is the card's declared
  window what the engine stores (yes — one field); (b) should a DENIED decision be re-askable
  immediately (today a denial is honoured by `_expansion` for the same target); (c) is the
  `approval_actions` table the only place the human-readable action lives (the card reads it)?
- Repair hints: none open from this increment.
