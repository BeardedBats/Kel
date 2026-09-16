# Design Vetting Sessions — User Journey rules applied

This feature was built under `docs/product/USER_JOURNEY_STANDARD.md`. Three defects were found while
implementing it; each created a generalized rule (see `docs/product/USER_JOURNEY_HISTORY.md`, H11–H13).

## Defects found during implementation

1. **A progress counter argued with the user.** After "11: not sure" and "12: skip" the line still
   read "Recorded: 10 of 12" while every question had been handled — the counter counted only strict
   answers. Fixed by counting *recorded* (handled) states for progress, while the spec keeps strict
   `answered` coverage. → **JR-31.**
2. **An interruption path forgot to bring the prompts back.** Resurfacing was wired into the
   job-terminal and dispatched branches, but not into the failed-planning branch — an interruption
   that failed to plan left the user without the open questions. Fixed by calling the resurface hook
   on every normal-path exit. → **JR-32.**
4. **A new engine route was unreachable from the UI.** The Vetting panel never showed a live
   session because the renderer bridge whitelist lacked `/api/vetting`; every panel call was
   rejected as "Unknown Kel action" and silently swallowed. Fixed and re-verified live: the
   panel now shows the session. -> **JR-34.**

3. **The UI advertised commands the parser did not understand.** The batch footer promised
   `explain 12` and `challenge 12`, but the control patterns only matched "explain simply" and
   "challenge this" — the advertised commands fell through as unmatched chat. Fixed by accepting the
   numeric forms. → **JR-33.**

## Rules applied from the existing standard (examples)

- **JR-4/JR-16 (no machinery nouns in primary UI):** the batch, the panel and the progress lines never
  say "lease", "verdict", "milestone", "provider" or "backend"; question ids are numbers; statuses
  are recorded/unsure/skip/awaiting.
- **JR-9 (silence is a defect):** every answered message gets one short acknowledgement, controls get
  an immediate reply, and an unanswerable interruption still returns with the prompts.
- **JR-22/JR-23 (find by meaning, plain palette language):** controls are conversational English and
  mirrored by panel buttons; nothing requires knowing storage concepts.
- **JR-25 (readability):** panel text reuses Kel's existing type scale; SVG wireframes are for shape,
  not copy.
- **JR-28 (empty states teach):** with no session the panel explains the flow in two sentences and one
  primary action ("Start vetting session").
- **JR-30 (one registry, every consumer):** the panel is a mirror; every action calls the same
  `/api/vetting` surface the chat uses, so chat and panel can never disagree.
