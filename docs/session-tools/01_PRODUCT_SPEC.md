# Product spec — conversation-scoped tool controls

## Problem

Kel's capability policy is global. A user who wants "no browsing in this chat" or "use GitHub here"
has to change Kel for every conversation, or not at all. The donors solved this with per-session
tool grants; Kel's version must stay conversational, not become an orchestration panel.

## User-facing behaviour

One control beside the model pill in a conversation: **Tools**. It lists capabilities by plain
name — Web, Files, Terminal, GitHub, Google Drive, Connected apps — each with its availability
("Available", "Needs setup") and one of three states:

- **Use default** — follows Kel's usual setting (the global policy)
- **Enabled for this chat**
- **Disabled for this chat**

Plus **Allow once (next request only)** for a capability that is off here, and **Reset this
conversation to your usual settings**.

The same state is reachable in words: *"Use GitHub for this conversation."*, *"Don't browse the web
in this chat."*, *"No terminal commands here."* Kel answers with one plain sentence and continues.

## What the user never sees

MCP server names, tool ids, runtime adapters, leases, policy rules. The menu is checked to contain no
such words (`menuHidesMachinery` in the packaged scenario); the reason line for an unavailable
capability is a user sentence ("Connect it in Settings · Tools first"), and the action it offers is
"Connect".

## Non-goals

- No full Smart Capability Recommendations feature (a future suggestion must reuse this same policy —
  see 04 and the release docket).
- No per-runtime configuration (the capability is configured once, at the Kel level).
- No new Settings page: this is a conversation-level control.
