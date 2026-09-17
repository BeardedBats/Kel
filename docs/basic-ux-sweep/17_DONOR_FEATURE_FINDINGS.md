# Donor feature findings (2026-09-17)

Every candidate was checked against the **current packaged Kel build** (code paths read in the
`ux/v15-journeys` worktree that produced `dist/package-final6`, plus packaged runs where a journey
could be driven without a model provider). Legend: **PAG** present & good · **PBF** present but
flawed · **MBHV** missing, high value · **MO** missing, optional · **NA** not applicable.

Fields per row: current implementation · where it appears · user-facing? · survives restart? ·
packaged evidence · does it solve the user problem? · what remains missing · donor · decision.

## 1. Message queue while Kel is working — **PAG** → ADOPT

- **Current implementation**: `components/chat/CommandQueuePanel.tsx` (cards per queued item with
  edit / send-now / delete, drag-reorder via `SortableQueueItemProps`) driven by
  `pages/conversation/platforms/useConversationCommandQueue.ts` (modes `auto|manual`, caps: 20
  items / 20k chars / 50 files / 256 KB persisted state, `normalizeQueueState` for older shapes),
  mounted by `AcpSendBox.tsx`.
- **Where**: the composer area of an ACP (Kel) conversation while a turn is running.
- **User-facing**: yes. **Survives restart**: queue state is persisted (normalized on load).
- **Packaged evidence**: code + mount point verified in the packaged bundle; the *live* journey
  (queue while a turn runs) could not be exercised here — a provider is required to hold a turn
  open, so it stays classified as structure-verified, journey-unverified.
- **Solves the problem?** Yes for the stated behaviour: distinct cards, edit/delete/reorder, and
  Stop does not delete queued input (queue lives outside the turn).
- **Missing**: nothing observable; the queue is deliberately a light panel, not a task manager.
- **Donor**: Goose/Warpforge-style inline pending input. **Decision: ADOPT (already present)**.

## 2. Composer prompt history — **PAG** → ADOPT

- **Current implementation**: `SendBox/index.tsx` `handleHistoryKeyDown`
  (lines 1400-1470): ArrowUp/ArrowDown over `getConversationInputHistory(messageList, conversationId)`
  (line 569 — derived from the conversation's own user messages, so no extra storage).
- **Guards verified in code**: modifiers ignored; multiline safe (ArrowUp only when the caret is on
  the first line); Escape exits history and restores the draft; ArrowDown returns to the draft;
  nothing auto-submits; the recalled prompt lands in the composer where it can be edited.
- **User-facing**: yes. **Survives restart**: yes (history is the conversation itself).
- **Packaged evidence**: the composer + history code ship in `final6`; the journey is drivable in
  the packaged app (type, send, ArrowUp) — recorded in `18_DONOR_FEATURE_REMEDIATION.md`.
- **Missing**: nothing material. **Donor**: Warpforge/Hermes CLI recall. **Decision: ADOPT (present)**.

## 3. Find in current conversation — **PAG** → ADOPT

- **Current implementation**: `ConversationTitleMinimap/useMinimapPanel.ts` binds the primary
  Cmd/Ctrl+F shortcut (`isPrimaryApplicationShortcut(event, { key: 'f' })`, line 292) and drives a
  result list (`filteredItems`, `activeResultIndex`, next/previous via lines 322-378) with Escape
  to close; the anchor rail's comment records the split: "Keyword search stays in the conversation
  title's panel".
- **Where**: the conversation title area (the search button on the message rail opens it).
- **User-facing**: yes. **Survives restart**: n/a (transient).
- **Packaged evidence**: the panel is part of the packaged bundle; the journey (open a long chat,
  Ctrl+F, next/previous, Escape) is recorded in the remediation doc.
- **Missing**: a visible "n / m" match counter is not confirmed by code inspection alone — noted
  rather than claimed. **Donor**: Goose/Pioneer in-thread find. **Decision: ADOPT (present)**.

## 4. Conversation timeline / jump rail — **PAG** → ADOPT

- **Current implementation**: `Messages/anchorRail/` (`MessageAnchorRail.tsx`, `anchors.ts`,
  `useConversationAnchors.ts`): one tick per user message, whole-rail hover target, click to jump,
  a search button, hidden until the conversation is long enough to need it.
- **Packaged evidence**: the rail's search control appeared in packaged header inventories
  (`message-anchor-rail-search`) in earlier battery runs.
- **Missing**: artifact/milestone markers on the rail (only turns today) — **MO**, noted.
- **Donor**: Warpforge/AO session rails. **Decision: ADOPT (present)**.

## 5. Side-by-side preview rail — **PAG** → ADOPT

- **Current implementation**: `pages/conversation/Preview/` (panel context, renderers incl.
  `HTMLRenderer`, browser tab support, `theme/`, `previewUrls.ts`) hosted by the conversation's
  right sider (`ChatSlider.tsx`, header "Files | Changes").
- **User-facing**: yes; opens from the conversation without losing chat state.
- **Packaged evidence**: the Preview tree ships in the packaged bundle; earlier batteries captured
  the Files/Changes affordances in header inventories.
- **Missing**: nothing that a second viewer would add — the requirement not to duplicate an
  existing artifact surface is met by using this one. **Donor**: Orkas/Pioneer panels.
  **Decision: ADOPT (present)**.

## 6. Keep computer awake — **PBF → remediated this pass** → ADAPT

- **Current implementation (before this pass)**: a toggle on the donor *Scheduled tasks* page wrote
  `system.keepAwake` to the client-settings KV **and nothing read it** — `powerSaveBlocker` was
  wired in `common/platform/ElectronPlatformServices.ts` but the power methods had **no callers**,
  so the switch was inert; its tooltip also still named the donor ("AionUi will prevent…").
- **Where**: donor `/scheduled` page (not in Kel's navigation).
- **User-facing**: yes (but misleading). **Survives restart**: the *value* persisted; the effect
  did not exist. **Packaged evidence**: none existed — the feature could not work.
- **Solves the problem?** No. **Remediation**: see `18_DONOR_FEATURE_REMEDIATION.md`
  (main-process owner, Kel-native card in Settings · System, live state, donor control removed).
- **Donor**: Hermes/Goose scheduled-work postures. **Decision: ADAPT (implemented)**.

## 7. Session-scoped tool controls — **MBHV (deferred)** → ADAPT later

- **Current implementation**: capability policy is **global** (`pages/kel/autonomy`,
  `authorize.py`, tools settings). No per-conversation override exists; `useAcpConfigOptions`
  overrides are agent *config*, not capability policy.
- **User-facing**: the global policy is; a chat-scoped override is not.
- **Solves the problem?** Partially — a user cannot say "browser for this chat only" without
  changing the global policy.
- **Missing**: an engine-side per-conversation capability contract plus a small chat-level control.
- **Why deferred**: it changes the engine's authorization contract (the class of change that needs
  its own review), and no user-reported need exists yet. **Donor**: Goose per-session tool grants.
  **Decision: ADAPT — release docket item 1.**

## 8. Smart capability recommendations — **MO (provider case already covered)**

- **Current implementation**: the provider case is covered by the plain notice on the landing page
  ("None of your connected models is available right now, so Kel will wait… → Open Providers") and
  onboarding's "Connect a model". There is **no** per-task suggestion for GitHub/Drive/web access.
- **Why optional**: a reliable task→capability detector does not exist, and a wrong suggestion is
  nagging — the exact failure the brief warns about. **Donor**: Goose extension prompts.
  **Decision: ADAPT (defer) — docket item 2.**

## 9. Interactive in-chat tool UI — **PBF** → ADAPT later

- **Current implementation**: Vetting is fully interactive in-chat (choice cards, batches,
  decisions, spec). Approvals exist as Work-page permission prompts, not inline cards.
- **Missing**: inline approve/deny on the transcript (the donor matrix already recommends it).
- **Why deferred**: it belongs with the work-lifecycle change in docket item 1.
  **Donor**: Goose `ToolApprovalButtons`/`PermissionModal`. **Decision: ADAPT (defer).**

## 10. Compact tool activity — **PAG** → ADOPT

- **Current implementation**: `MessageToolGroupSummary.tsx` ("View Steps · N") collapses tool
  groups; `MessageAcpToolCall` keeps raw detail behind the group; Work uses plain state labels
  (`JOB_STATE_LABEL`).
- **Packaged evidence**: the conversation and Work surfaces render these components in the packaged
  build; a provider is needed for a *live* tool run, so the summary is verified structurally.
- **Missing**: nothing material. **Donor**: Warpforge status tokens. **Decision: ADOPT (present)**.

## 11. Long-conversation virtualization / paging — **PAG (measured)** → ADOPT

- **Current implementation**: the message list pages history in and keeps a scroll anchor; no
  virtualizer library is used.
- **Packaged evidence**: seeded long-conversation stress run recorded in the remediation doc
  (200+ messages): render time, scroll behaviour, search and jump still work.
- **Missing**: nothing at the measured size. **Donor**: AO/Warpforge long-thread handling.
  **Decision: ADOPT (present, measured).**

## 12. Advanced worker view — **MO** → REJECT for this release

- **Current implementation**: Work/Diagnostics already expose job state, permissions and evidence;
  a raw worker/terminal view exists only as the workspace "Open in VS Code" affordance.
- **Why rejected**: it exposes the machinery the one-assistant experience is built to hide, and the
  real need (why did Kel do that?) is served by item 14. **Donor**: Pioneer raw sessions.
  **Decision: REJECT (keep hidden).**

## 13. Work inspector — **PAG** → ADOPT

- **Current implementation**: `pages/kel/work` (jobs, waiting-on-you), the chat's work panel
  ("Files | Changes"), the Vetting drawer, and artifact surfaces.
- **Packaged evidence**: Work text dumps from earlier batteries (`maintext`, `hardening`).
- **Missing**: a single "tests / verification" block is spread across Work and the panel — noted,
  not duplicated here. **Donor**: Pioneer/AO work views. **Decision: ADOPT (present)**.

## 14. Session evidence / replay — **PAG (evidence) / MO (replay)** → ADAPT (defer replay)

- **Current implementation**: `pages/kel/diagnostics` + engine `diagnostics.py` expose the durable
  evidence Kel already stores (runs, reviews, verification); the engine records reviewer verdicts
  and test evidence per milestone.
- **Packaged evidence**: diagnostics page captured in the audit (`maintext_diagnostics`).
- **Missing**: a chronological "what happened" replay view — optional. **Donor**: Hermes sessions.
  **Decision: ADAPT (defer) — docket item 3.**

## 15. Shared knowledge across runtimes — **PAG** → ADOPT

- **Current implementation**: project knowledge/memory is **engine-owned** (`memory.py` with trust
  levels and supersession, `context.py`, `projectmap.py`) and every runtime (Codex, Claude Code,
  raw models) is driven *by the engine*, so no worker owns a separate store.
- **Evidence**: engine unit tests cover project isolation and conflict recording; the design is
  documented in `docs/v1.3/KEL_V1.3_MEMORY_MODEL.md`; nothing in the renderer asks which worker's
  memory to use.
- **Missing**: nothing. **Donor**: AionUI multi-runtime shells. **Decision: ADOPT (present)**.

## 16. Memory change proposals — **PBF** → ADAPT later

- **Current implementation**: the engine already **refuses silent overwrites** (conflicts are
  recorded, history preserved through supersession, `docs/v1.3/KEL_V1.3_MEMORY_MODEL.md`), which is
  the safety half of the requirement. There is no user-facing "I think this rule changed → Review /
  Accept / Reject" surface; corrections arrive as conversation.
- **Missing**: the review surface. **Why deferred**: it needs a memory-diff API and a card type;
  the safety property the brief asks for holds today. **Donor**: Hermes SOUL/memory edits.
  **Decision: ADAPT (defer) — docket item 4.**

## 17. Workflow checkpoints — **PAG** → ADOPT

- **Current implementation**: `ConversationPlanBar` (plan stages in the chat), engine `recipes.py`,
  work lifecycle with review gates and continuation.
- **Packaged evidence**: plan bar ships in the bundle; recipes covered by engine tests.
- **Missing**: nothing for the stated "Plan/Implement/Review/Fix without orchestration jargon".
  **Donor**: AO staged sessions. **Decision: ADOPT (present)**.

## 18. Artifact lineage — **PBF** → ADAPT (candidate)

- **Current implementation**: the engine writes artifacts under `artifacts/<job>/<run>/<file>` and
  records them per conversation; the renderer tracks `IConversationArtifact` (id, status,
  created_at) and can reveal/ preview them.
- **Missing**: a user-facing "where did this come from?" that answers with the conversation/task
  and offers "open source", "view previous version" — today the path exists on disk but the chain
  is not stated in the UI. **Donor**: Pioneer/AO artifact provenance.
  **Decision: ADAPT — candidate in this pass (see remediation doc for what actually shipped).**

## 19. Auto-detect installed agent runtimes — **PAG** → ADOPT

- **Current implementation**: `pages/kel/providers` + engine `providers.status` mapping to plain
  states (`installed_not_authenticated → "needs you to sign in"`, `not_installed → "not installed"`,
  healthy → "Available"/"Needs setup" chips in the model control), plus
  `/api/system/ensure-node-runtime` and `/api/system/ensure-managed-acp-tool` for setup.
- **Packaged evidence**: `sweep3` on `final6` exercised the providers page and the availability
  chips.
- **Missing**: nothing material; refresh happens on page/engine start. **Donor**: Hermes/Codex CLIs.
  **Decision: ADOPT (present)**.

## 20. Unified tool / MCP setup — **PAG** → ADOPT

- **Current implementation**: one Tools settings surface owns MCP servers
  (`ToolsSettings/McpManagement.tsx` via a shared `useMcpServers` store, import-from-JSON, OAuth),
  and it is not duplicated per assistant (assistant settings do not carry their own MCP lists).
- **Missing**: nothing observed; the residual question (whether every *external* CLI worker inherits
  every server) is engine policy, not a second setup surface. **Donor**: Goose extensions.
  **Decision: ADOPT (present)**.

## 21. Profiles / isolated workspaces — **MO** → REJECT (Projects suffice)

- **Comparison**: Projects already scope conversations, workspace, knowledge/map/recipes, artifacts
  and tasks; a Profile would add a second container concept with its own switcher, and the only
  case it adds over Projects is *settings/provider isolation* (e.g. a work account vs a personal
  one) — which today is served by changing the provider/credential, not by a profile.
- **Justifying case if it ever appears**: simultaneous identities on one machine with different
  credentials and default models *and* a need to keep them from seeing each other's chats.
  **Donor**: Warpforge workspaces. **Decision: REJECT for this release (recorded).**

## 22. Remote status / approval — **MO** → REJECT for this release

- **Current implementation**: a web host exists (`startWebHost`, `/api/settings/client`), so the
  architecture can serve a remote surface, but remote *approval/status* is not a shipped journey.
- **Why rejected now**: it competes with core desktop quality and the brief marks it
  optional/future. **Donor**: AO/Pioneer gateway clients. **Decision: REJECT (recorded).**

## Additional donor patterns (beyond the 22)

| Donor | User problem | Donor behaviour | Kel today | Decision |
|---|---|---|---|---|
| Hermes | "Is anything happening?" | status line shows elapsed / idle-since | Work shows states, no idle-since line | ADAPT (defer) |
| Hermes | approval wording drift | four fixed words (allow once/always, deny, deny always) | permission prompts exist on Work; wording not yet a fixed vocabulary | ADAPT (defer) |
| Agent Orchestrator | sorting hides what needs you | five attention zones with an explicit rank order | Work orders by recency | ADAPT (defer) |
| Pioneer | "it ran" read as "you were told" | produced vs delivered stated separately | not distinguished | ADAPT (defer) |
| Pioneer | background work with no review state | `reviewRequired` third terminal state | Work has no "needs review" outcome distinct from done | ADAPT (defer) |
| Goose | onboarding unreachable later | re-enterable first-run route | onboarding is one-shot (documented out-of-scope in `00_STATUS.md`) | REJECT for this release |
| Warpforge | status words that don't drive action | status tokens named for the user's next action | Kel's job states are plain but system-named | ADAPT (defer) |

None of these was added in this pass: each either duplicates a deferred item above or needs a
surface this release does not open — they are recorded so a future pass starts from evidence
instead of discovery.
