# UI and copy

## Placement

`KelToolsControl` sits in the conversation header beside the Kel model pill
(`pages/conversation/components/ChatConversation.tsx`), i.e. inside the conversation, one click from
the work — not a Settings page. The button reads `Tools`, or `Tools · N` when the conversation
differs from the usual settings, so the scope is visible without opening anything.

## Menu structure (per capability)

```
Web — Available
  Use default                       (Current)
  Enabled for this chat
  Disabled for this chat
  Allow once (next request only)    (only when Disabled for this chat)
Google Drive — Needs setup
  Connect it in Settings · Tools first
…
Reset this conversation to your usual settings
```

- Availability words: **Available** / **Needs setup** / **Unavailable**.
- A capability that is off for everyone says so in plain words ("Off for all chats (change it in
  Settings)") instead of pretending a chat override is possible.
- Test ids: `kel-tools-pill`, `kel-tools-menu`, `kel-tool-<id>-default|on|off|once|setup`,
  `kel-tools-reset`.

## Copy rules applied

- Capability names are the user's words; no tool ids, MCP names, server names or runtime words
  (asserted by `menuHidesMachinery` in the packaged scenario).
- Success toasts state the scope: "GitHub is on for this conversation.", "Web is off for this
  conversation.", "Web follows your usual setting here again."
- Failure is one plain sentence: "Kel could not change that just now."

## Conversational control (same state)

The ACP host checks directive-shaped text before dispatching work and answers inline, exactly like
Vetting answers:

| The user says | Kel does | Kel replies |
|---|---|---|
| "Use GitHub for this conversation." | `github = on` | "Okay - I can use GitHub in this conversation." |
| "Don't browse the web in this chat." | `web = off` | "Okay - I won't use Web in this conversation. Say \"use Web here\" when you want it back." |
| "Use the default for the web here." | row deleted | "Web follows your usual setting again in this conversation." |

A cheap local prefilter means ordinary messages still take exactly one engine round-trip; the parser
requires both a capability word and a scope phrase ("in this chat", "for this conversation", "here"),
so prose like "write a note about the weather" is not mistaken for a directive (unit-tested).

## Honest limit

The conflict case ("you disabled Web but asked for the weather") is answered by the engine's plain
refusal reason and by this control's **Allow once** action — there is no separate message-level card
in this pass. The task's actions (Enable once / Enable for this chat / Keep disabled) all exist; two
of them live in the Tools menu rather than in the transcript. Recorded in 08 as the next increment.
