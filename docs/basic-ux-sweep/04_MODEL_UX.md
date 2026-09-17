# Model UX

## What existed (audit)

- Provider configuration (Settings · Model) with DPAPI-encrypted keys, health check, clear states.
- ACP chats have a per-conversation model selector; **Kel chats show a read-only “Automatic”**.
- No explicit “Default Kel model” control and no per-chat choice for Kel conversations.

## Implemented

- **Engine** `kel/model_prefs.py` (migration 13): `default` and `conversation:<id>` scopes with
  plain-label validation. `/api/model` actions: `list`, `get`, `set_default`, `set_conversation`,
  `clear_conversation`.
- **Routing**: the choice is a soft preference — `router.select(..., prefer=)` orders the preferred
  provider first and keeps every fallback; `Auto` keeps the original deterministic order. The run
  records the preferred model for provenance when that provider executes.
- **Settings · Model** → “Default Kel model”: Auto (Kel picks what is available) or a specific
  model; availability chips (“Available” / “Needs setup”); saved immediately.
- **Chat header** (Kel chats): a “Kel model” pill with *Use global default*, *Automatic*, and the
  model list; “Details” shows what will answer; a link opens the settings card.
- **Persistence**: choices live in the engine store and survive restart; switching back to Auto
  clears the preference in one click.

## Honest boundary

No usable provider exists on this machine, so “the selected model actually answered” cannot be
observed live. Covered instead: preference round-trip and precedence (11 unit tests), the selector
honouring the preference when usable while keeping fallbacks (unit-tested), persistence and UI
states in the packaged app (`sweep3`).
