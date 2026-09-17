# Policy model — precedence actually implemented

Every decision goes through one function: `kel.capabilities.resolve(store, capability, conversation,
job, consume)`. The authorization boundary calls it as **layer 3c** in `kel.authorize.Authorizer.decide`,
which is the single entry point every effect-capable path already used. The implemented order is:

| # | Layer | Where | May do | May never do |
|---|---|---|---|---|
| 1 | Hard safety / product guardrails | `kel.guardrails`, `BLOCKED_KINDS`, frozen/system paths, destructive snapshot | deny unconditionally | be overridden by anything below |
| 2 | Global availability | `capabilities.availability()` — what is actually configured on this computer | report `available` / `needs_setup` / `unavailable` | be pretended by an override |
| 3 | Conversation override | `conversation_capabilities` (this conversation only) | disable anything; enable what is available; allow once | bypass (1), invent availability (2), change the global default |
| 4 | Role / runtime policy | `kel.team` tool policy (narrowing only) | deny further | broaden (3) |
| 5 | Execution authorization | capability lease, boundary expansion, user approval (`kel.autonomy`) | deny, expire, require approval | be skipped for an effect |

## Rules the implementation enforces

- **The override never mutates the global default.** `set_override` writes only
  `conversation_capabilities`; the global row is written only by an explicit `set_global`.
- **A new conversation inherits the global default** — absence of a row means `default`, which
  resolves to the global state.
- **Removing an override returns the conversation to global behaviour** (`state: default` deletes the row).
- **An unavailable capability cannot be switched on**: `resolve` returns
  `allowed: false, rule: capability-unavailable | capability-needs-setup` with a plain reason, even
  when the override says `on`. The UI shows the row as "Needs setup" and offers Connect instead.
- **Enable once** writes a `capability_grants` row (single use, 15-minute TTL). The effect-time
  authorization spends it (`kel.authorize` passes `consume=bool(intent.consume, default True)`), so
  the grant covers exactly one effect; a pre-flight check that passes `consume=False` sees the same
  grant without spending it. Regression test:
  `test_allow_once_is_spent_by_the_authorization_path` (pre-flight passes, the effect spends it, the
  next request is refused again) - found by independent review, fixed before the artifact was cut.
- **Only narrowing on the effect side**: the capability layer can only *remove* permission before the
  role policy and the lease run. It never grants a lease, never satisfies an approval, never widens a
  scope — it sits above those gates so they still decide.

## Predecessor check (documented honestly)

The engine already refused to broaden authority ("No layer broadens authority granted by a stricter
layer") — this layer keeps that invariant and adds a per-conversation factor. The
`guardrail_decisions` audit record keeps its shape; a capability denial is recorded with
`rule = capability-conversation-off | capability-once | capability-unavailable | capability-needs-setup`.
