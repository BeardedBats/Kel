# User journey rules for conversation-scoped controls

Two permanent rules were added to `docs/product/USER_JOURNEY_STANDARD.md` by this workstream; history
entry **H24** in `docs/product/USER_JOURNEY_HISTORY.md` records the defects they came from.

## JR-50 — Conversation-scoped preferences state their scope, never leak, and never rewrite the global

A preference that applies to one conversation must say so where it is set and where it applies, must
be stored with that conversation, must survive navigation and restart, must not change the setting for
any other conversation, and must return to the shared default when reset. Verify: set it in one
conversation, check a second conversation is untouched, restart, check both, reset, check the first
follows the global again.

Implemented by: `conversation_capabilities` (row per conversation, absence = default), the `Tools · N`
badge on the pill, the "Reset this conversation…" action, and the packaged `sessiontools` scenario.

## JR-51 — Capability controls speak intent; machinery stays behind Details

A user-facing capability control names what the user wants to do (Web, GitHub, Files, Terminal), not
what Kel uses to do it (tool ids, MCP servers, runtimes, leases); an unavailable capability is stated
in plain words with the action that makes it available, and can never be switched on to look ready.
Verify: read every string in the control and the menu — no internal name appears; switch on an
unavailable capability and confirm it stays unusable with a plain reason.

Implemented by: `capabilities.CAPABILITIES` (labels/descriptions only), the availability words and
reasons in `availability()`, and the `menuHidesMachinery` assertion in the packaged scenario.

## Rules this workstream leaned on rather than added

- **JR-40** (superseded donor controls are swapped) — the donor semantics of "session tools" were
  replaced by this one Kel control; nothing else claims to scope tools per conversation.
- **JR-42** (the model choice is a plain, explicit choice) — the same shape is reused deliberately:
  a pill beside the model pill, "Use default / this chat", availability in plain words.
- **JR-47** (unexpected payloads degrade in place) — the control renders nothing rather than blanking
  when the engine is unreachable; the chat keeps working.
