# Known limitations

Recorded honestly; each is either an environment limit or a deliberate next increment.

1. **No provider on this machine.** The end-to-end effect of "Disabled for this chat" on a *live*
   model run cannot be exercised here: work never reaches a model, so the effect paths that consult
   the boundary (coding runs, browser use) are proven by unit test plus the boundary wiring in
   `kel.coding`, not by a live turn. The conversation state, its isolation, its persistence and the
   natural-language path are all exercised in the packaged app.
2. **Conflict card.** Disabling a capability and then asking for something that needs it is answered
   by the engine's plain refusal reason and by the Tools menu's "Allow once" — there is no
   message-level card offering Enable once / Enable for this chat / Keep disabled inline. The three
   actions exist; two live in the control instead of the transcript. Next increment per the docket.
3. **Connector-backed capabilities.** Google Drive and Connected apps report "Needs setup" until a
   Kel-level connector owns them; the control offers the settings surface that exists today. This is
   an honest state, not a stub that pretends readiness.
4. **Availability probing is deliberately coarse.** Terminal/GitHub availability is "a usable coding
   runtime exists on this machine". Finer per-tool probing (e.g. git present but claude not) would
   leak machinery into the surface and is out of scope.
5. **Enable once TTL.** A one-shot grant is consumed by the first authorized effect of that
   capability in that conversation and expires unused after 15 minutes. It is *not* a policy bypass:
   the lease/approval gates still run after it. (The first implementation only *checked* the grant at
   the boundary and never spent it, which made it fifteen minutes of standing consent; independent
   review caught it and `kel.authorize` now spends it, with a regression test.)
6. **Localisation.** The control is Kel-native and uses plain English strings, like the other Kel
   cards; it is not wired into the 13 donor locale bundles.
7. **Assistant-level tool lists.** Per-assistant tool configuration (donor surface) is unchanged and
   is not merged into capabilities; the conversation control governs Kel's effects, not an
   assistant's own settings.
