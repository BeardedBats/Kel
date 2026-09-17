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
and execution paths that only know a job resolve it through `submissions.conversation_id`
(`_conversation_for_job`) — one mapping, no duplicated identity rules.

## Failure behaviour

- Unknown capability → `PolicyError('That is not a Kel capability.')` (plain, no ids echoed).
- Empty conversation id → `PolicyError('Open a conversation before choosing what Kel may use here.')`.
- Unknown state → plain refusal listing the three real choices.
- KeyError/DB trouble surfaced as ordinary errors; the UI shows "Kel could not change that just now."
