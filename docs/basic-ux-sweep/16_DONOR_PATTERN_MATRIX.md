# Donor pattern matrix (2026-09-17)

Second donor pass on the shipped Kel candidate (`dist/package-final6` at audit time, `final7` after
the remediation below). The first pass lived in `docs/product/UX_DONOR_SIMPLICITY_MATRIX.md`
(structural patterns: navigation shape, settings, search reach, approval phrasing); this pass asks a
different question — **which mature user-journey features the donors solved that Kel still lacks** —
and classifies each candidate against the current build.

Classification vocabulary: `PRESENT_AND_GOOD` · `PRESENT_BUT_FLAWED` · `MISSING_BUT_HIGH_VALUE` ·
`MISSING_OPTIONAL` · `NOT_APPLICABLE`. Decisions: `ADOPT` / `ADAPT` / `REJECT`.

Legend for evidence: **[code]** inspected in the current tree, **[pkg]** exercised in the packaged
app by a harness run, **[doc]** recorded in an existing Kel doc.

## Candidates from the donor brief

| # | Candidate | Class | Donor / source | Kel evidence | Decision |
|---|---|---|---|---|---|
| 1 | Message queue while Kel is working | PRESENT_AND_GOOD (live journey unverifiable here — see 17) | AionUI donor stack (queue panel), Warpforge task rows | `components/chat/CommandQueuePanel.tsx`, `platforms/useConversationCommandQueue.ts` (edit / send-now / drag-reorder, persisted state, 20-item + 256 KB caps), mounted by `AcpSendBox` **[code]** | ADOPT |
| 2 | Composer prompt history (Up/Down) | PRESENT_AND_GOOD | Hermes CLI recall, Goose composer | `SendBox/index.tsx:1401-1464` — `getConversationInputHistory(messageList, conversationId)`: conversation-scoped, first-line guard for multiline, Escape restores the draft, modifiers ignored **[code]** | ADOPT |
| 3 | Find in current conversation | PRESENT_AND_GOOD | Warpforge sidebar search, Orkas `search.js` | Ctrl/Cmd+F → conversation-title minimap panel (`components/ConversationTitleMinimap/`, `useMinimapPanel.ts`: filtered results, active-result index, next/prev, Escape) **[code]** | ADOPT |
| 4 | Conversation timeline / jump rail | PRESENT_AND_GOOD | Pioneer session view, AO attention zones | `Messages/anchorRail/MessageAnchorRail.tsx` — one tick per user turn, hover-select, click-to-jump, hidden when there is nowhere to jump, search button in the rail **[code][pkg: header inventory in sweep2/sweep3 runs]** | ADOPT |
| 5 | Side-by-side preview rail | PRESENT_AND_GOOD | Goose side panels, Orkas preview modules | `pages/conversation/Preview/` (PreviewPanel, HTMLRenderer, browser tab, file utilities) + `ChatSlider` right sider, opened from the conversation header ("Files", "Changes") **[code]** | ADOPT |
| 6 | Keep computer awake during long work | **PRESENT_BUT_FLAWED → REMEDIATED** | Hermes long-run ergonomics (donor Cron page shipped the switch) | Toggle existed on the donor `/scheduled` page only, wrote a config value **nothing read**; `preventSleep/allowSleep` had no callers; tooltip named the donor **[code]** → see `18_DONOR_FEATURE_REMEDIATION.md` **[pkg]** | ADAPT (done) |
| 7 | Session-scoped tool controls | MISSING_BUT_HIGH_VALUE (deferred) | Goose per-session tool toggles, Hermes approval profiles | Capability policy is global (Autonomy page + Tools settings); no per-conversation override and no engine contract for one **[code]** | ADAPT (release docket) |
| 8 | Smart capability recommendations | PARTIAL → MISSING_OPTIONAL | Goose "extensions" prompts, AO capability hints | The provider case is covered by the plain in-chat notice with one action ("Open Providers") **[pkg: guid dump in every run]**; there is no task→capability detector for GitHub/Drive/browser, and building one without evidence would risk nagging **[code]** | ADAPT (defer) |
| 9 | Interactive in-chat tool UI | PARTIAL | Goose `ToolApprovalButtons`, AO inline decisions | Vetting answers/decisions/greyboxes are fully interactive inside the chat **[pkg: `vetting`, `voice-vetting` scenarios]**; approval prompts live on Work, not inline; simple tool forms do not exist **[code]** | ADAPT (defer) |
| 10 | Compact tool activity | PRESENT_AND_GOOD | Warpforge status tokens, Hermes status bar | `MessageToolGroupSummary` ("View Steps · N") collapses tool calls; `MessageAcpToolCall` keeps raw detail behind the group; Kel job states map to plain labels (`JOB_STATE_LABEL`) **[code][pkg: hardening `jargonOffenders: []`]** | ADOPT |
| 11 | Long-conversation virtualization / paging | PRESENT_AND_GOOD (measured — see 17) | Warpforge task lists, Pioneer transcript | Message list renders per-message testid nodes; no virtualizer library in the tree **[code]**; stress numbers recorded in `17_DONOR_FEATURE_FINDINGS.md` **[pkg: long-conversation probe]** | ADOPT |
| 12 | Advanced worker view | MISSING_OPTIONAL | Pioneer shell/domain split, Warpforge worker panes | Diagnostics page + Work page cover the honest need; a raw worker/session view would expose runtime machinery to normal users **[code]** | REJECT for this release |
| 13 | Work inspector | PRESENT_AND_GOOD | AO session presentation, Pioneer run results | Work page (jobs, waiting-on-you), conversation "Files / Changes" panel, Vetting drawer, artifact surfaces **[pkg: work/maintext dumps]** | ADOPT |
| 14 | Session evidence / replay | PRESENT (evidence) / replay MISSING_OPTIONAL | Pioneer task timeline, Hermes transcripts | Engine stores durable evidence (`diagnostics.py`, jobs, reviews, test evidence) and the Diagnostics page surfaces it **[code][doc: `docs/basic-ux-sweep/README` evidence]**. A scrub-able replay is optional and would be a new surface | ADAPT (defer replay) |
| 15 | Shared knowledge across runtimes | PRESENT_AND_GOOD | Hermes `SOUL.md`, Goose memory, AO sessions | Memory, project map and context are owned by the engine (`memory.py`, `context.py`, `projectmap.py`), which every ACP runtime talks to; no per-runtime knowledge store exists in the tree **[code][doc: `docs/v1.3/KEL_V1.3_MEMORY_MODEL.md`]** | ADOPT |
| 16 | Memory change proposals | PRESENT_BUT_FLAWED (engine protection present, review surface missing) | Hermes durable-notes review, AO session memory | The engine records conflicts and supersession and never silently overwrites authoritative records (`memory.py` trust levels 1-7, supersession history) **[code+tests]**; there is no user-facing "review this proposed change" card | ADAPT (defer surface) |
| 17 | Workflow checkpoints (Plan → Implement → Review → Fix) | PRESENT_AND_GOOD | Pioneer task stages, AO review zones | `recipes.py` + `ConversationPlanBar` (stage bar in chat) + engine review gates and completion authority **[code][doc: `docs/v1.3/KEL_V1.3_CONTINUATION_SPEC.md`]** | ADOPT |
| 18 | Artifact lineage | PARTIAL (records exist, surface missing) | Pioneer/Pioneer-style provenance, Kel's own evidence ledger | Engine stores artifacts at `artifacts/<job>/<run>/<file>` with job/run identity (`core.py`), and the renderer carries `IConversationArtifact` (id, status, created_at, conversation) **[code]**; no "where did this come from?" affordance in the UI | ADAPT (release docket) |
| 19 | Auto-detect installed runtimes | PRESENT_AND_GOOD | Goose provider list, Hermes provider checks | Providers page maps `installed_not_authenticated` / `not_installed` to plain chips ("Needs setup", "needs you to sign in") and the model card shows availability chips **[pkg: sweep3 `modelPillMenu` / availability chips]** | ADOPT |
| 20 | Unified tool / MCP setup | PRESENT_AND_GOOD (one config surface; per-worker inheritance is engine-side) | Goose extensions, AO integrations | `ToolsSettings/McpManagement.tsx` backed by the single `useMcpServers()` store (+ JSON import, OAuth); credentials live in OS-backed custody; assistant editors do not carry a second MCP list **[code]** | ADOPT |
| 21 | Profiles / isolated workspaces | MISSING_OPTIONAL | Warpforge workspaces, Pioneer gateways | Projects already scope conversations, files, knowledge, artifacts and recipes **[code][pkg: projects/maintext dumps]**. A Profile concept would mostly duplicate Projects plus per-profile providers/theme; the justifying use case (two unrelated lives with different provider accounts) is real but narrow | REJECT (Projects are the simpler answer) |
| 22 | Remote status / approval | MISSING_OPTIONAL (future) | AO remote zones | A web host exists (`startWebHost`, `/api/settings/client` used by the renderer) but there is no remote status/approval surface **[code]** | REJECT for this release |

## Additional donor patterns (beyond the 22 candidates)

These come from the first pass (`UX_DONOR_SIMPLICITY_MATRIX.md`) and are still open; they are listed
so the next release can pick them up without re-reading the donors.

| Donor | Pattern | User problem | Kel today | Decision |
|---|---|---|---|---|
| Hermes | "idle since last answer" line on Work | A finished background job is invisible until you go looking | Work page states exist; no quiet idle line | ADAPT (release docket) |
| Hermes | Four-key approval vocabulary ("Allow once / Allow always / Deny / Deny always") | Bespoke wording per prompt makes safety decisions slower | Work-page prompts; wording not fixed | ADAPT (with item 9) |
| Agent Orchestrator | Fixed five-word attention vocabulary + attention-ordered lists | "Working" can bury "Needs you" | Work orders by recency; states are plain but not ranked by attention | ADAPT (release docket) |
| Pioneer | Produced vs delivered, and `reviewRequired` as a third terminal state | "It ran" misread as "you were told"; no "needs your review" outcome | Work shows states and waiting-on-you; no produced/delivered split | ADAPT (release docket) |
| Warpforge | Status tokens named after the user's next action | Status must answer "what do I do next" | Status words are plain but system-shaped in places | ADAPT (release docket) |
| Goose | Onboarding re-runnable as a route | Users cannot revisit first-run help | Onboarding is one-shot (declared out of scope earlier) | REJECT for this release |
| Orkas | Search ranking extracted into its own module | Search quality unreviewable inside a 281-line component | Palette now has search groups; ranking still inline | ADAPT (defer) |

Nothing in this pass justified a new *visual* adoption: every pattern above is either already Kel's,
adopted as behaviour, or rejected with a reason.
