# Basic UX expectation matrix

Audited on the pre-fix packaged RC (`dist/package-final`, 2026-09-16) by exercising the app
(`sweep-seed` / `sweep-a` / `sweep-b` harness runs), then re-verified on the shipped artifact
(`dist/package-final6/win-unpacked`, 2026-09-17) with the as-built battery
(`sweep2` / `sweep3` / `sweep4`, regression set, first-run, a11y probes) — see `15_FINAL_VERDICT.md`.
Legend: **PAG** present & good · **PBF** present but flawed · **MBHV** missing, high value ·
**MO** missing, optional · **NA** not applicable.

| # | Area | Class (before → after) | Evidence / notes |
|---|---|---|---|
| 1a | Composer focus, Enter sends, Shift+Enter newline | PAG | sweep-a: `composerFocused`, `shiftEnterNewline` true |
| 1b | Sending state + failure surface | PBF → PAG | without a provider the app says “Kel is waiting for a model to continue.” (verified in `sweep2`); the failed-turn card and Stop exist in code but need a provider to appear |
| 1c | Retry a failed request without retyping | wired, not live-verified | `/api/retry` is whitelisted and the Retry affordance sits on the failed-turn card; a failed turn needs a provider, so the live click is classified honestly as unverified |
| 1d | Markdown / tables / code / links render | verified in `sweep2` (shipped artifact) | the seeded rich reply renders through `MarkdownView`; the probe walks the shadow root and counts **1 table, 1 pre, 2 code, 1 link** |
| 1e | Copy response / code copy / feedback | PAG (affordance) / feedback not observed | the copy icon button is present in the message row and clickable; its success feedback is an inline “copied” state that this probe does not observe |
| 1f | Scroll up freely / return to newest | PBF | user scroll is never hijacked; no dedicated "jump to newest" button found → **MO** (noted, not built) |
| 2a | Rename / delete conversation with confirmation | PBF → rename verified in `sweep2` | row menu opens and the rename flow completes (`renameWorked` true); the delete-confirm flow exists in the same menu but the probe's delete-item capture returned nothing, so it is not claimed here |
| 2b | Search conversations (partial, no-result, clear) | PAG | sweep-a: `searchPartialHit`, `searchNoResult` true |
| 2c | Switch / current obvious / survives restart | PAG | sweep-a: 3 chats independent; restart keeps the list |
| 2d | Archive / pin (existing) | PAG | `conversations.pinned`/`archived_at` + Archived settings page |
| 3 | **Default Kel model (Auto + models)** | MBHV → **built** | `/api/model` + `KelDefaultModelCard` in Settings · Model; persists engine-side; sweep3 exercises it |
| 4 | **Per-chat model override** | MBHV → **built** | Kel chats now show the `KelModelPill` ("Kel model: …") instead of a read-only "Automatic"; "Use global default" restores routing; Details explains the effective choice |
| 5 | Model/provider status language | PBF → PAG | availability chips "Available"/"Needs setup"; no routing internals on chat surfaces; raw detail stays behind Details/settings |
| 6 | **Theme foundation controls** | MBHV → **built** | `ThemeColorsSection` (Settings · Appearance → Theme colors) exposes 10 semantic colors + "More colors" over the token contract; built-ins are never mutated |
| 7 | Color interaction (picker, hex, live, reset) | MBHV → **built** | swatch + hex + per-token Reset + "Restore all colors"; changes apply live and save instantly (stated in the section) |
| 8 | Theme safety (contrast warnings, restore) | MBHV → **built** | inline contrast warnings for primary/secondary text vs backgrounds; no silent rewrites |
| 9 | Theme scope + persistence | MBHV → **built** | overrides keyed per theme id; switching themes keeps each theme's choices; survives restart (sweep3) |
| 10 | Theme presets (save/duplicate/delete) | MO | per-theme overrides cover the core need; the existing user-theme CSS editor remains for power users |
| 11 | Text size / density | PAG / MO | the Appearance text-size steppers drive the window zoom factor (verified: `0.95 → 1 → 0.95` in `sweep3`); per-region font family + size steppers ship too; a density toggle is optional and not built |
| 12 | Zoom (Ctrl +/−/0) | verified in `sweep3` | Ctrl+= and Ctrl+0 driven through Electron's input path change the real zoom factor (`0.95 → 1 → 0.95`), and the choice persists |
| 13 | Universal vertical scrolling | PBF → verified per surface | 16-route matrix + seeded long chat; see `10_LAYOUT_AND_SCROLLING.md` |
| 14 | **Draft preservation** | PBF → **built** | drafts were in-memory only; now mirrored per conversation and restored after restart (sweep2) |
| 15 | Attachments (mention/file, remove, errors) | verified in sweep2 | `@` mention popup probe; transcription upload path already covers unsupported-file messages |
| 16 | Generated artifacts discoverability | MO | `conversation_artifacts` + reveal-in-folder exist, but artifacts need provider work; classified optional with the architecture noted |
| 17 | **Data location (open / copy path)** | MBHV → **built** | `/api/data-path` + Settings · System "Data folder" card (Copy path, Show in folder) |
| 18 | **Backup / restore** | MBHV → **built** | engine `Backup` (credentials stripped, BACKUP-INFO.json): a live backup carries `kel.sqlite3` **and** the chat database under `host/aionui`, skips runtime state, and records anything unreadable instead of failing; staged restore applies at the next start with a `.pre-restore-*` rollback — `sweep4` deletes a transcript, restores, restarts and gets it back (`restoreRecovered` true) |
| 19 | Clear / reset controls | PAG | theme restore; delete/archive confirmations proportional; no full-reset button (documented) |
| 20 | Navigation / back | PAG | back/forward controls; settings return keeps context; no dead routes in tour/maintext |
| 21 | Settings behavior (autosave, persistence, scroll) | PAG | settings save immediately; persist across restart; every settings page scrolls (system now longer with the data cards) |
| 22 | Credential UX | PAG | DPAPI-encrypted, masked, replacement/removal flows, provider health check; never in logs/backups |
| 23 | Failure / recovery | PBF → PAG | plain sentences everywhere (envelope stripped); failed sends keep history and offer retry; input preserved via drafts |
| 24 | Crash / restart recovery | PAG | engine kill → app continues; no phantom "working" jobs (`phantomWorkSeen=false`); drafts survive; long-job restart is provider-dependent |
| 25 | Offline / degraded mode | PAG | local capabilities (transcription practice, vetting, search) work without a provider; chat shows "waiting for a model" |
| 26 | Background work / notifications | PBF / MO | Work page states + await-you surface exist; desktop notifications have a setting but could not be live-verified without running work |
| 27 | Recent activity | PAG | Work page ("Waiting to continue", job list) is the activity surface; no raw telemetry |
| 28 | Work cancellation | PBF | cancel path exists; live verification needs a running job (provider) |
| 29 | Undo / reversible actions | MO | transcript move has no undo (drag + move-select, no confirmation needed); archive has restore; destructive deletes confirm |
| 30 | **Global search** | MBHV → **built (core)** | `/api/search` over chats + transcripts + vetting, surfaced as `Found` groups in the palette (Ctrl+K, `/`); work/knowledge/artifacts remain on their surfaces (documented) |
| 31 | Search within existing surfaces | PAG | conversation search + palette content search verified |
| 32 | Conversation branch/duplicate | MO | not built (would touch conversation storage); classified optional |
| 33 | Pin / favorite | PAG | chat pin/archive exist; projects pinning not built (optional) |
| 34 | Command palette completeness | PBF → **built** | New Chat, Work, Transcription, Settings (+Appearance/System) destinations; Actions: theme switch and "Start design vetting" (prefills the chat); only working entries appear |
| 35 | Keyboard shortcut reference | MO | shortcuts are listed in the palette footer; a full reference page is optional, not built |
| 36 | Focus / keyboard fundamentals | PAG | focus rings verified (keyboard scenario), skip link, Escape behaviors; focus return after dialogs standard Arco behavior |
| 37 | Accessibility preferences | PAG | OS dark/light honoured ("Follow System"); font scaling; reduced-motion is respected by Arco transitions |
| 38 | Empty / loading / error states | PAG | every empty state answers what/why/next (hardening + sweep evidence); loading shows real states |
| 39 | Project context | PAG | project selector + knowledge/map/recipes; workspaces named |
| 40 | Human work states | PAG | Thinking/Working/Waiting for you/Finished/Failed surface in Work + chat cards; JOB_STATE_LABEL maps raw states |
| 41 | Update / restart UX | PAG | About: version 1.5.0, "Check for updates", prerelease toggle; update failure paths exist in the controller |
| 42 | Multi-window | NA | single primary window by design; actions do not spawn duplicates |
| 43 | Usage / cost awareness | MO | no trustworthy local data source; classified optional |
| 44 | Window / layout fundamentals | verified per surface | matrix + narrow/keyboard/light/dark/zoom sweeps; see `10_LAYOUT_AND_SCROLLING.md` |

## Donor-derived rows (2026-09-17 pass)

Classification for the second donor pass; full per-item evidence in `17_DONOR_FEATURE_FINDINGS.md`
and the pattern sources in `16_DONOR_PATTERN_MATRIX.md`. The same legend applies (PAG / PBF /
MBHV / MO / NA).

| # | Donor-derived capability | Class | Where it lives / evidence |
|---|---|---|---|
| D1 | Queue messages while Kel is working | PAG | `CommandQueuePanel` + `useConversationCommandQueue` (edit, send-now, reorder, persisted, 20-item cap) |
| D2 | Composer prompt history (Up/Down) | PAG | `SendBox/index.tsx` - first-line guard, Escape restores the draft, history scoped to the conversation from its messages |
| D3 | Find in the current conversation | PAG | Ctrl+F → conversation-title minimap panel (results, next/prev, Escape); works over a 314-message chat |
| D4 | Conversation timeline / jump rail | PAG | `MessageAnchorRail` (user-turn ticks, hover select, click to jump, hidden on short chats) |
| D5 | Side-by-side preview rail | PAG | `pages/conversation/Preview/*` + chat slider: HTML, images, files, browser, theme previews |
| D6 | **Keep the computer awake** | PBF → **built** | was an inert donor-page switch; now a real `prevent-app-suspension` inhibition, live state, Settings · System, released on close (`runs/kaw/out/ux-keepawake.json`) |
| D7 | Session-scoped tool controls | MBHV (deferred) | only global policy exists (Autonomy + Tools); needs an engine capability contract |
| D8 | Smart capability recommendations | MO | provider case covered by the plain "Open Providers" notice; no reliable task→capability detector |
| D9 | Interactive in-chat tool UI | PBF | Vetting is fully interactive; approvals live on Work rather than in the transcript |
| D10 | Compact tool activity | PAG | tool-group "View Steps · N", plain job-state labels, raw detail behind the group |
| D11 | Long-conversation virtualization | PAG (measured) | 314 messages: 259 ms to first node, 100 mounted nodes, 61 MB heap, search + rail work, 0 console errors |
| D12 | Advanced worker view | MO | no strong real use case; Diagnostics covers the need |
| D13 | Work inspector | PAG | Work page + "Files/Changes" panel + vetting drawer |
| D14 | Session evidence / replay | PAG / MO | Diagnostics page answers "why"; replay is optional and not built |
| D15 | Shared knowledge across runtimes | PAG | project memory/context is engine-owned and runtime-agnostic (no per-worker stores) |
| D16 | Memory change proposals | PBF | engine already refuses silent overwrites and records supersession; a review surface is missing |
| D17 | Workflow checkpoints | PAG | recipes + conversation plan bar + review gates with completion authority |
| D18 | Artifact lineage | PBF | records exist (`artifacts/<job>/<run>/…`); no user-facing "where did this come from?" yet |
| D19 | Auto-detect installed runtimes | PAG | plain availability states ("Available" / "Needs setup" / "needs you to sign in") from `providers.status` |
| D20 | Unified tool / MCP setup | PAG | one Tools settings surface (`McpManagement`) over a shared store; no per-agent duplication observed |
| D21 | Profiles / isolated workspaces | MO (rejected) | Projects already scope chats, context, artifacts and knowledge; Profiles would add a concept without a use case |
| D22 | Remote status / approval | MO | WebUI exists but remote approval is future-facing; not part of this release |
