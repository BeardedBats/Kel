# 03 — Chat and Composer

Scope: conversation surface, composer, model/tool placement, hover actions, New Chat / empty conversations,
per-row icons. Source: audit worktree @ `ffeef73`; runtime evidence from `package-final16` + Phase 3 WIP.

Measured shell facts (1440×900, populated profile, `evidence-visual-c.json`):

* conversation rows: **34px high, 244px wide, x=8, padding-left 10px**, 2px vertical gap
* primary nav buttons: **34px high**, 36px vertical pitch (Work 127 → Projects 163 → Permissions 199 → Transcription 235)
* titlebar row (y=3): Collapse / Search messages / Back / Forward, each 36×36, radius 6px
* "New Chat": **34px high, 208px wide, radius 7px**, 14px label

---

## 1. Model and tool selection are detached from the composer — **S2 · source-mapped**

`pages/conversation/components/ChatConversation.tsx:443–462` builds `headerExtraNode` containing, in order:

1. `CronJobManager` (only when the assistant is not `kel`)
2. `modelSelector` — which for Kel conversations resolves to a fragment containing
   `KelModelPill`, `KelToolsControl`, `KelMemoryProposalControl` (`ChatConversation.tsx:377–411`)
3. `AcpRuntimeRestartButton`

That node is passed to `ChatLayout` as **`headerExtra`** (`ChatConversation.tsx:462–466`). So model, tools
and the memory-proposal control all live in the conversation **header**, not the composer.

Two further details matter:

* **Mobile already does what the user wants.** `modelSelector` returns `undefined` when `isMobile`
  (`ChatConversation.tsx:369–370`, comment: *"Mobile: model selection moves into the sendbox `+` action
  sheet, so the header selector is suppressed to free up vertical space"*). The composer already owns a
  model entry point on mobile — desktop is the inconsistent platform, not the reverse.
* **The donor selector stays mounted but invisible** to warm the runtime: *"The donor selector stays mounted
  (invisible): its warmup drives the sendbox/mic readiness. The Kel pill replaces it visually"*
  (`ChatConversation.tsx:380–391`, `display:none` + `aria-hidden`). Any relocation must preserve that warmup
  side-effect or the mic/readiness signal breaks. This is the single largest hidden risk in this change.

**Recommendation.** Move `KelModelPill` + `KelToolsControl` (+ memory proposal) into the composer's tool row
(`components/chat/SendBox/index.tsx`, `sendbox-tools` container around lines 2119–2127), keeping the header
for the conversation title only. Keep the hidden warmup selector mounted exactly as is. This is a
*relocation*, not a rewrite: same components, same handlers, no new state.

## 2. Hover actions overlap conversation titles — **S2 · reproduced by measurement**

`pages/conversation/GroupedHistory/ConversationRow.tsx`:

* the row is `... pe-16px` (line ~199) — **16px reserved** on the end side
* the actions container is `absolute end-8px top-1/2 -translate-y-1/2` holding a **20px** menu button
  (`ConversationRow.tsx:307–312`, `size-20px`) plus the `Dropdown` trigger (`:352–380`)

20 + 8 = **28px needed vs 16px reserved**. Measured on a real row:

```
rowRight 252 · nameRight 236 · actionLeft 224 · actionWidth 20 · rowPaddingRight "16px"
overlapPx = nameRight − actionLeft = 12
```

So the hover-revealed menu covers the last **12px** of the title's box. In this capture the row's title was
short enough (text ended at 177) that the collision was not visible; **any title long enough to use its
available width is occluded on hover**, which is exactly when the user is reaching for the menu.

**Recommendation.** Reserve the action area unconditionally: change the row's end padding to
`pe-32px` (8 + 20 + 4) whenever the row can show actions, and/or wrap the title in a container whose right
edge stops at the action area, and add a short horizontal fade on the title edge so truncation reads
deliberately. Do not "fix" it by hiding the menu — the menu is the only rename/pin/archive path.

## 3. New Chat creates nothing; empty conversations still exist in the store — **S2 · reproduced + measured**

Measured on a populated profile (`evidence-visual-c.json`):

```
rows before New Chat : 5
click New Chat       : hash → #/guid
rows after click     : 5
rows after round trip: 5
```

`Sider/index.tsx:60–75` (`handleNewChat`) only navigates: it cleans tooltips, blurs, closes the preview and
`navigate('/guid', { state: { resetAssistant: true } })`. **No conversation is created, so there is nothing
to auto-remove.** The user's proposed solution ("create a temporary conversation immediately, remove it if
abandoned") therefore addresses a mechanism that does not exist in this build.

The *related* complaint is real, with a different cause. The engine store for the audited profile held:

```
conversations: 9 · with 0 messages: 6  (including 'main')
```

and 2 of the 5 rendered sidebar rows carried the generic robot fallback icon, i.e. rows exist for
conversations that never received a message. So message-less conversations **do** accumulate and render.

**Recommendation.**
1. Keep New Chat as a navigation (it is honest and cheap) — but **label the empty state so the user knows
   nothing exists yet**, and make the composer the obvious first step.
2. Fix the real defect: **do not render sidebar rows for conversations with zero messages**, or create the
   conversation row lazily on first message. Filtering on the engine's message count is the smallest correct
   change and needs no new lifecycle.
3. If the product *wants* eager creation (the user's model), that is a deliberate behaviour change: create a
   local draft on New Chat, never persist it, and drop it on leave/blur with no message. That is acceptable,
   but it is a new state machine and should be sequenced *after* the cheap filter.

## 4. Per-row robot/agent icons — **S3 · reproduced by measurement, icon is largely redundant**

`ConversationRow.renderLeadingIcon()` (`:75–122`) resolves through
`resolveConversationLeadingMark` (`pages/conversation/utils/conversationAssistantIdentity.ts:75–129`), which
returns, in priority order: preset-assistant **emoji** → preset-assistant **image** → `assistant_fallback`
(renders `<Robot>`) → agent **logo image** keyed by backend → `fallback` (renders `<MessageOne>`).

Measured in a populated sidebar of 5 rows: **2 rows rendered `i-icon-robot`, 3 rendered a 16px round image
logo** (`role="img"`). So the column carries a mix of: a per-backend logo (identical for every conversation
on the same backend) and a generic robot/message glyph (identical for all rows in that branch).

In Kel's documented one-assistant framing (*"The normal conversation does not expose model, worker, provider,
or agent selection"*, `docs/v1.5/11_DESIGN_SYSTEM.md`), that icon distinguishes nothing a user cares about:
it is either the same logo repeated or a generic glyph.

**Recommendation.** Keep icons only where they carry information:
* Hide the leading icon for plain single-assistant conversations (reclaim 22px + 8px gap of title width —
  which also relieves finding #2's pressure).
* Keep it for genuinely different kinds of row: scheduled/cron (`CronJobIndicator`), presence/status
  (generating `Spin`, `Attention` waiting), fork lineage badge, team rows.
* Do **not** delete the resolver: the emoji/image branches are meaningful for preset assistants and must
  keep working.

## 5. Composer — what is actually there (for the relocation in §1)

`components/chat/SendBox/index.tsx` is 2248 lines and already renders a tool row:
`sendbox-tools` / `sendbox-tools-mobile-compact` / `sendbox-tools-scroll-mobile` (~2119–2127). Voice input is
a real control (`KelMicButton` replaces the donor browser-speech control —
`pages/guid/components/KelMicButton.tsx`, wired at `SendBox/index.tsx:1659–1665, 1871`).

**Judgement (labelled).** The composer is the one place in this app that already has correct tool density:
a row of compact 8px-radius controls directly under the input. Moving the model pill and tools control there
removes the header clutter *and* makes the header title the dominant element, which is what a desktop user
expects. Nothing about the Kel model pill's semantics changes — "Automatic (Kel routing) plus an optional
per-chat model choice" (`ChatConversation.tsx:382–384`) reads fine in a composer.

## 6. Assistant prose is **not** carded — no change needed here

The direction says normal assistant prose must not be wrapped in cards. Chat does not violate this: the
message skeleton models assistant rows as **full-width** blocks (`bubbleWidth: '100%'`) and user rows at
78–84% (`pages/conversation/Messages/MessageList.tsx:158–166`). Keep it that way when the composer is
reworked. The card-everything problem is in the Kel console pages — see `05_WORK_PROJECTS_PERMISSIONS.md`.

## Phase 3 conflict note

Phase 3 touches exactly this area: `components/chat/KelWorkPanel.tsx`, `components/kel/KelApprovalCard.tsx`,
`Messages/MessageList.tsx`, `Messages/hooks.ts`, `common/chat/chatLib.ts`. Section 1 (headerExtra) and
section 2 (ConversationRow) are **orthogonal** to those files, but `KelWorkPanel` is mounted *inside*
`Sider/index.tsx` (line ~180) — any sidebar restructuring must not drop it. Sequence this work **after**
the Phase 3 HEAD lands and re-read those five files before editing.
