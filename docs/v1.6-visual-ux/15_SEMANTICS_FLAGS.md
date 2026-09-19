# 15 — Semantics-Altering Proposals (flagged for coordinator review)

Everything in this file **changes product behaviour, capability, or vocabulary** rather than visual
presentation. None of it should be implemented inside a visual pass without an explicit decision. Each item
states the proposal, why it is semantic, the options, and a recommendation with reasoning.

---

## F1 — New Chat: eager draft conversation (finding 11)

**Proposal (from the user's report):** create a temporary conversation immediately on New Chat, remove it if
abandoned empty.
**Why semantic:** it introduces a conversation lifecycle with create-and-garbage-collect semantics that does not
exist today (measured: New Chat creates nothing — rows 5 → 5 → 5). It changes what the store contains, what the
sidebar shows, and what `reconcileHistory` will import on the next boot.
**Options:** (a) keep navigation-only; (b) local draft that is never persisted until the first message;
(c) eager persisted conversation with an abandonment sweep.
**Recommendation:** (a) + make the empty composer state explicit ("Nothing here yet — your first message starts
the conversation"), then revisit (b) as its own change with its own tests. (b) is the only option that gives the
user the "something started" feel without creating garbage; (c) is what produced finding 12.
**Do not implement in the visual pass.**

## F2 — Hiding message-less conversations from the sidebar (finding 12)

**Proposal:** do not render sidebar rows for conversations with zero messages.
**Why semantic:** it changes *visibility of user data*. The audited store holds 6 of 9 conversations with zero
messages, **including `main`** — the conversation the Work surfaces use (`kelWork('main')`). A naive filter could
hide a conversation the product itself depends on, or hide a conversation a user believes exists.
**Options:** (a) filter rows where `message_count === 0` **and** the id is not a system conversation;
(b) mark them ("empty draft") instead of hiding; (c) leave as-is.
**Recommendation:** (a) with an explicit allow-list/deny-list for system conversations, or (b) if any doubt.
**Needs:** confirmation of the rule from the coordinator before editing the sidebar.

## F3 — Permissions: the "Ask the engine about a scope" panel (finding 7)

**Why semantic:** it is a **capability**, not decoration — the only user-reachable way to ask the policy engine
about a scope (`kelAutonomy.check`).
**Options:** (a) delete; (b) relocate to Diagnostics; (c) collapse behind a disclosure on Permissions.
**Recommendation:** (b) or (c). Deleting a capability to make a page look calmer is out of scope for a visual
pass. Relocating keeps the ability while removing the jargon from the primary surface.

## F4 — Permissions: Emergency stop placement (finding 7)

**Why semantic:** moving a global safety control into an overflow menu changes its **availability under stress**.
**Options:** (a) keep in the header, visually separated and confirmed; (b) overflow menu with a confirm; (c) leave.
**Recommendation:** (a) — separate it from `Reload`, add a confirmation that states the consequence
("revokes every active permission and pauses all work; completed effects are not undone"). Hiding a stop control
is a safety decision, not a spacing decision.

## F5 — Where Team / Permissions / Tools live (findings 3, 14, 15)

**Why semantic:** the settings entries `Agents`, `Team roles`, `Tools` are currently the *only* route to those
surfaces, and they eject the user from Settings. Any fix chooses an information architecture.
**Options:** (a) keep the destinations inside the Settings shell; (b) move Team/Permissions into the primary
nav; (c) remove the settings entries and add a "Team" entry to the sidebar.
**Recommendation:** (a) for Tools/Permissions-as-settings, and (b) for **Team**, because Team is a workspace
(a place you use) rather than a preference. **Must be decided together with Phase 4**, which proposes removing
the **Butler** entry points that live in exactly these settings areas
(`ModelModalContent.tsx`, `ToolsModalContent.tsx`, `AgentSettings`, `AssistantSettings`, `SkillsSettings` —
measured present in those files).

## F6 — Retiring the word "Agent" (finding 15)

**Why semantic:** it is user-facing vocabulary, and it overlaps Phase 4's donor-string cleanup.
**Options:** (a) retire "Agent" until agents are creatable; (b) keep it and add creation later.
**Recommendation:** (a) — the only "agent" objects reachable today are engine-seeded role templates. Route the
wording decision through Phase 4 so one lane owns terminology.

## F7 — Removing per-row conversation icons (finding 13)

**Why semantic:** the leading mark is not purely decorative — it carries preset-assistant emoji/logo,
cron status, waiting state, generating spinner, and fork lineage.
**Options:** (a) remove the whole leading slot; (b) remove only the undifferentiated branches (generic robot /
generic message) and keep every informative one.
**Recommendation:** (b). (a) would silently drop real state signals; (b) reclaims the 30px for titles without
losing information.

## F8 — Transcription "Source" → "API Key" (finding 6)

**Status: already decided by the user** ("API Key is clickable TEXT, not a gear. It opens the Meta API key
modal") — no new decision needed. Recorded here only because the label makes a claim: it names the provider.
If Kel ever transcribes through a second provider, the label must generalise. Note also that Kel's current
modal has *no helper paragraph* either way, matching the decision.

## F9 — Not rendering empty sections on Work (finding 9)

**Why semantic (mild):** the "Team assignments" section teaches a new user that specialists exist; removing it
entirely on an empty account removes that discovery.
**Recommendation:** remove the *cards*, keep the teaching as one line of plain text inside the page-level empty
state ("Kel assigns a specialist only when a step actually runs"). Presentation-level, listed for completeness.

## F10 — `TeamSiderSection.tsx`: delete vs wire (extra defect X2)

**Why semantic:** *wiring* it introduces user-created teams (a new feature, out of scope). *Deleting* it removes
dead code (no user-visible change).
**Recommendation:** deletion in a **separate, clearly-scoped** cleanup commit — **not** inside the visual pass,
and never wired without a product decision.

## F11 — System page buttons: contrast vs disabled state (finding 4)

**Why semantic:** `Back up now` measured 1.23:1 and `Restore from this backup` 1.50:1. If those states are
intentionally *disabled*, "fixing" the colours could imply an available action.
**Recommendation:** first confirm whether the controls are disabled (read `SystemSettings.tsx` state), then fix
the **disabled** treatment to be legible-but-clearly-inactive rather than making it look primary. Flag to the
coordinator because it touches apparent capability.

## F12 — Two approval surfaces (finding 7 vs Phase 3)

**Why semantic:** Permissions (Allow once / Allow for this project / Deny) and the Phase 3 in-chat approval card
are two UIs for the same decision on the same durable record.
**Options:** (a) chat is primary and Permissions shows a read-only decision log; (b) both interactive;
(c) Permissions is primary and chat links to it.
**Recommendation:** (a) — with the Phase 3 owner in the room, since Phase 3 was just committed. A visual pass must
not decide where approval authority lives.

## F13 — Kel console pages are not localized

**Observation, not a proposal:** every string I propose changing in `pages/kel/**` is a **hard-coded English
literal** (`grep` of `en-US/*.json` finds none of: "could not be loaded", "Autonomy state", "Projects"). The rest
of the app carries 12 locale catalogs. Phase 4 owns localization; the visual pass should avoid *adding* new
hard-coded copy, and should not attempt localization (scope).
