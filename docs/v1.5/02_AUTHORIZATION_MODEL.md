# 02 — Authorization Model (V1.5)

Status: **implemented in the execution path (G1 + first G2 increment, working tree)**. This is the
design record; the gate board with evidence lives in `00_STATUS.md`.

## The invariant

An effect happens only when the central boundary allows it. The boundary is not a checker beside
the execution path; it is part of the execution path:

```text
action intent (actor bound by trusted context, never by payload)
  -> guardrail integrity + locked rules            (kel.guardrails)
  -> role tool policy (narrows only)               (kel.team)
  -> capability lease: state / expiry / scope      (kel.autonomy — one implementation)
  -> boundary expansion (asked once per target, resolved only by the user)
  -> user approval for destructive actions
  -> ALLOW -> the real effect
```

Module: `runtime/kel/authorize.py` (migration **010**, table `guardrail_decisions`; policy version
`kel-authz-1.5`). The lease decision itself stays in `kel.autonomy.check` —
`kel.authorize` adds context validation, role policy, approval, expansion, and recording, and
delegates scope/state evaluation, so scope logic is not duplicated anywhere.

Actor identities:

| Actor | Bound by | Example |
|---|---|---|
| `user` | the authenticated loopback session (`Service._action` rejects payload `actor` on every route) | Apply checked changes |
| `kel` | engine-owned work in-process | issue the execution lease; claim gate |
| `worker` | validated against the `runs` table for the named run; a stopped, cancelled, or orphaned run is not a live worker | coding dispatch, tool use |

## Where it is wired (the real effect points today)

| Path | Caller / actor | Check performed |
|---|---|---|
| Job creation | `Store.create` (`kel`) | effect-capable jobs (coding) get an execution lease bound to the compiled contract digest (`review_ref = kel-contract:<sha>`); ineligible roots (frozen/system) stay unleased and fail closed at the next gate |
| Claim gate | `Engine.tick` (`kel`) | a coding milestone cannot claim a worker without an `ALLOW` for `repo` on the project root (`consume=False` pre-flight) |
| Coding execution | `CodingAdapter.execute` (`worker`) | `repo` + tools `git` / `run_tests` before any dispatch; denial returns `BLOCKED` with no change made |
| Change application | `apply_changes.apply_checked` (`user` via `/api/apply`; `kel` on crash recovery) | `write` on the project root before any write into the user's project |
| Service identity | `Service._action` | uniform rejection of payload-supplied `actor` for every engine action family |
| Boundary grant | `Service` `/api/autonomy resolve` | a granted request wakes exactly the blocked job (`resume_after_grant`); work continues without the user orchestrating anything |

## Decision outcomes

`ALLOW` · `DENY` · `REQUIRES_BOUNDARY_EXPANSION` · `REQUIRES_USER_APPROVAL` · `EXPIRED_LEASE` ·
`REVOKED_LEASE` · `INVALID_CONTEXT` · `GUARDRAIL_TAMPERED`

Strict intersection: system guardrails ∩ role policy ∩ lease scope ∩ approval state. No layer
broadens authority granted by a stricter layer; each layer only narrows.

## Decisions and their consequences (recorded so they cannot drift)

1. **Kel issues its own execution leases.** Issuance is Kel's decision for work Kel owns; the
   reviewed plan reference is the compiled CompletionContract digest. Independent review remains a
   separate verification gate and is unaffected by this.
2. **Renewal vs. revocation.** An expired lease is renewed at claim time. A lease revoked for a
   *system* reason — `emergency stop` that the user has resumed past, or `contract revised` — is
   renewed with a recorded decision. A *targeted* revoke is never silently undone: the job is
   blocked (`AWAITING_USER`) with the reason shown until the user decides again.
3. **One-time grants consume exactly once.** Pre-flight checks run with `consume=False`; the
   effect-point check consumes. A spent one-time grant denies (`grant-used`) and Kel does not
   silently re-ask; a denied boundary target stays denied (`boundary-denied`).
4. **Boundary expansion is asked once per target.** Out of scope → `REQUIRES_BOUNDARY_EXPANSION`
   with a durable request (pending requests are reused, never duplicated). Grants are `once`
   (used-once) or `project` (repeatable, scoped). Only the user resolves a request. On grant, the
   blocked job resumes automatically.
5. **Every decision is durable.** `guardrail_decisions` records decision_id, timestamp, actor,
   worker, role, project, job, milestone, lease, action kind, tool, target, decision, rule, reason,
   policy version, guardrail digest, boundary request id, approval id, and evidence refs.
   Identical repeat checks inside 300 s collapse into one record; `lease_events` dedupe identical
   allow/deny events inside 60 s, so supervision polls stay signal instead of noise.
6. **Blocked work is visible, never silent.** `authorization.blocked` sets the milestone error and
   an assistant message (with the request id when one exists), and moves the job to
   `AWAITING_USER` once no run is active. The Autonomy page remains the user's decision surface.

## What is enforced now vs. known limits (truthful)

Enforced today on the execution path: lease issuance/state/expiry/scope at every point above;
frozen-release and system-path denial (shared predicates in `kel.guardrails`); locked action kinds;
destructive snapshot + explicit-approval rules; role tool policy whenever a run carries an assigned
role; service-level actor binding for all action families; guardrail tamper refusal at every
decision (`GUARDRAIL_TAMPERED`).

Not yet part of this increment (tracked in `16_KNOWN_LIMITATIONS.md`, gates noted):

- model/provider inference calls (read-only native adapters, internal worker) are not lease-gated;
  those adapters perform no repository or filesystem effects;
- `browser` and `external` kinds have no calling runtime today — policy for them is authored here
  so any future caller already passes the boundary;
- `no-screen-takeover` and `firefox-only` remain checker-level rules because no current action
  family synthesizes input or drives a browser; closure requires a real gate or a truthful scope
  statement (G2 review decision);
- role enforcement applies when an assignment exists; automatically attaching roles to every run
  is a later G3 step;
- the desktop copy on the Autonomy page still carries the V1.4.1 "not yet" wording — a G7 item;
  since this change, the engine is the truth and the copy must catch up before release.
