# Conversation overrides — storage, lifecycle, isolation

## Storage (migration 14, `kel.capabilities`)

| Table | Columns | Meaning |
|---|---|---|
| `conversation_capabilities` | `conversation_id, capability, state, updated` (PK: conversation+capability) | one row per override; **absence means "use default"** |
| `capability_global` | `capability, state, updated` | the user's usual setting for new conversations (absent = `on` for what is configured) |
| `capability_grants` | `grant_id, conversation_id, capability, created, expires, used` | "Allow once" — single use, 15-minute TTL |

`state` is `on` or `off`; the third user choice, "Use default", *deletes* the row rather than storing
a third value, so a conversation can never carry a stale opinion after the user resets it.

## Lifecycle

- **Created** when the user picks Enabled/Disabled in the Tools control, or says it in words.
- **Survives restart**: rows live in the engine database (`GET /api/capabilities` after a relaunch
  returns them; packaged scenario `sessiontools` proves it).
- **Isolated**: every read/write is keyed by the conversation; no code path writes one conversation's
  row from another conversation's request.
- **Removed** by that conversation's "Reset to your usual settings" (`action: reset`) or by choosing
  "Use default" for one capability.
- **Grants** expire on their own TTL or when spent; `reset` clears them too.

## Which conversation id

The engine identifies a conversation by its Kel conversation id. The renderer holds the desktop id,
so the control resolves it the same way the model pill does (`window.kelAPI.conversation(desktopId)`),
and execution paths that only know a job resolve it through `submissions.conversation_id` with a
fallback to the job's own conversation (`_conversation_for_job`) — one mapping, no duplicated
identity rules.

## V1.6 P1 remediation (2026-09-17)

- **The real web effect is gated.** `kel.research.ResearchAdapter.execute` passes the conversation's
  capability decision (`capabilities.resolve(..., consume=True)`) before the external request is
  sent: Web = Disabled for a conversation stops research with the plain reason ("Kel paused this
  research before any external request: Web is disabled for this conversation"), and an "Allow once"
  grant is spent by that real effect. Same decision function the authorization boundary uses — no
  second policy.
- **Explicit commands only.** A whole message may be one command (`web: use default`, `terminal: off`,
  "don't use the browser here", "use GitHub for this conversation"). Inside a larger request, only
  the reserved Kel namespace counts (`[kel:terminal=off]`, `[kel:web=default]`, `[kel:github=on]`):
  canonical capability names and canonical states only, applied in source order, with only the
  reserved token removed from the forwarded request. Ordinary and technical content never mutates
  state and is never altered — generic brackets (`[web: off]`, also in paths, logs or nested
  `[[web: off]]`), quoted or code text, URLs, unknown names/states and malformed tokens are forwarded
  byte-identical, and anything ambiguous (unpaired quote, unclosed fence) matches nothing.
  (CAP2-CLAUSE remediation 2026-09-17 removed the substring scan; CAP2-RESIDUAL 2026-09-17 replaced
  the generic bracket form with the reserved namespace after the audit reproduced technical-string
  false positives such as `Use C:/projects/[web: off] as the path.`)
- **Google Drive and Connected apps are not offered.** No production effect path in this release can
  honour them, so they are not shown as switches that could not be kept; a stale caller is refused
  plainly and their chat aliases are ordinary text.

## Failure behaviour

- Unknown capability → `PolicyError('That is not a Kel capability.')` (plain, no ids echoed).
- Empty conversation id → `PolicyError('Open a conversation before choosing what Kel may use here.')`.
- Unknown state → plain refusal listing the three real choices.
- KeyError/DB trouble surfaced as ordinary errors; the UI shows "Kel could not change that just now."
