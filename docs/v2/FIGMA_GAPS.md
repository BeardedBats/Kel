# Active Figma gaps after audit 2

## Desktop inferences — 2026-09-26 (UI unification pass)

States Nick asked for that have no Figma frame. Each reuses the nearest component family; none is claimed as exact parity.

| State | Nearest Figma source | Inference | Implementation |
| --- | --- | --- | --- |
| Working / thinking indicator | Chat turn meta row (K mark + 13px heading type) in `185:4284` | Pulsing Kel mark + shimmering "Thinking…" + muted elapsed seconds, no card or spinner; reduced motion stops animation. Replaces the donor "Processing" bar. | `KelThinkingIndicator.tsx`, `ThoughtDisplay.tsx`, `MessageThinking.tsx` |
| Header Workspace menu | Header `Workspace ⌄` chip; Project picker `273:9512` | The chip opens a project-picker-style menu: engine Projects (plumbing projects for scratch/temp/data folders hidden), active check, "No workspace", "New workspace" (name + optional folder), "Open Projects". Workspace = engine Project; no new abstraction. Chip label shows the active name. | `ShellWorkspaceLink.tsx`, `activeWorkspace.ts` |
| Per-chat Tools control | Composer footer crumbs in `185:4284` | Moved from an extra row above the composer into the footer beside mode, styled as a footer crumb. | `AcpSendBox.tsx` |
| Draft button | none | Shown only while Kel is busy; Ctrl+Enter still drafts any time. Styled like the plain + button. | `SendBox/index.tsx` |
| Scratch-folder footer label | Footer project crumb | Auto-created `*-temp-*` folders read "No project" (JR-17). | `AcpSendBox.tsx` |
| Donor toasts / notifications / confirm dialogs | Toast in `273:13646`; Confirm delete `273:11796` | All Arco Message/Notification/Modal.confirm/Popconfirm take the Toast v2 and modal values in both themes; toasts sit bottom-centre above the composer. | `kel-shell.css` |
| Engine start failure in chat | Chat — Agent error `273:13090` | Plain-text engine failures render as the agent-error card with a plain reason, Pick another model, Try again, raw reason under Details. | `KelEngineFailureCard.tsx` |
| Background work card | Tool-call rows `273:12914` | D-53 hand-off card: live phase, View in Activity, confirmed Stop. | `KelWorkCard.tsx` |
| Scheduled task: recipe picker and project (D-57) | New scheduled task `273:1586` (no recipe or project field) | Settled policy 5: under the dialog's collapsed **Advanced settings** — a Project select and a "Run a recipe instead" switch that swaps Instructions for a Recipe select plus that recipe's inputs (text, choice, on/off). Same field, select and label styles as Name/Model; nothing shown until Advanced is opened. | `CreateTaskDialog.tsx` |
| Scheduled task: timing preview | `273:1586` (no preview line) | One muted line under Time/Model with the engine's sentence and next run ("Every weekday at 9:00 AM. Next: …"); the engine's reason in the error colour when it cannot use the timing. | `CreateTaskDialog.tsx`, `kel-shell.css` |
| Scheduled task: needs attention, footer, delete choice | List `189:2628`, detail `272:739` | A paused-with-problem task shows the failed chip "Needs attention" and a problem banner above Details; the list ends with "Scheduled tasks run while Kel is open on this computer."; the delete confirm offers "Keep the chats its runs opened". The detail's "Select runs" batch delete is dropped: runs are engine records, not deletable chats. | `ScheduledTasksPage/*`, `kel-shell.css` |

## Work cards across the top of the chat (D-68) — 2026-09-27

Source: page "Office — D-66 explorations", row 4 — 4a `474:332`, 4b `476:388`, 4c `477:543`, 4d `476:806`.
Checked off-screen at 1440×900 against those frames with fixture Office data (the engine's `/api/office` had
not landed); geometry matches (row at x 388 / y 90, 198px cards 8 apart, 88px overflow, 920px detail 8px
under the row, 340px menu right-aligned 6px under it). Differences that remain, each deliberate:

| State / element | Figma | What the app does | Implementation |
| --- | --- | --- | --- |
| Typeface | Instrument Sans (stand-in) | The app's SF Pro body face at the same size and weight; SF Pro is wider, so a long step label can wrap where Figma fits on one line. | `KelWorkCards.css` |
| "X of Y" and the bar | Sample numbers ("3 of 5" while step 3 runs; fills that do not equal the count) | Accepted steps of the engine's real milestones, and the bar is exactly that fraction (D-66: never a percentage or an invented number). The detail's "Step N of M" is the step in progress. | `workCardModel.ts` |
| Failed label | "Didn't pass its checks" (menu sample) | "Failed" on the card; the detail says why in the engine's words. The Office list does not say whether a failure was a failed check. | `workCardModel.ts` |
| Stopped | not drawn | Grey: the Figma stop icon in muted `#8FA9D6`, grey bar and ring (`#6F86AD`), label "Stopped". | `icon-stop-muted.svg`, `KelWorkCards.css` |
| Card hover, menu entry hover | not drawn (the first menu entry's tint is read as hover) | Card: the 0.22 blue tint between default and selected; menu entry: the 0.16 tint from 4c on hover/focus. | `KelWorkCards.css` |
| "Needs you" detail | not drawn | The engine's why/next in the Result box, headed "Needs you" with the amber dot. | `KelOfficeDetail.tsx` |
| Review header count ("2 of 4 passed"), file stats ("+86") | sample data | Omitted: the Office contract has no check count or line stats. Verification shows the engine's result and summary. | `KelOfficeDetail.tsx` |
| Model honesty | always one model | "Asked for X · ran Y" when the runtime ran another model; "Asked for X · not confirmed yet" until the runtime reports it (D-66). Long lines wrap. | `workCardModel.ts` |
| Result line for an applied change | "Applied to Documents › Receipts › 2026 at 9:40 AM. You can undo it." | The shared D-65 sentence ("Applied automatically to <folder> (N files). The earlier files are saved.") so the card, Work and this detail say the same thing. | `changeApplication.ts` |
| Stop confirmation | not drawn | The in-chat work card's confirm ("Stop this work? Anything already checked is kept." · Keep going · Stop it) in the header, with a red-outlined Stop it. | `KelOfficeDetail.tsx` |
| Focus | not drawn | Opening the detail focuses the dialog (no button looks pre-selected); Tab stays inside; Escape returns focus to the card. | `KelOfficeDetail.tsx` |
| Narrow windows / phone | desktop 1440 only | The row fits as many cards as the measured width allows; below 1100px the detail's columns wrap. The row is desktop-only (no phone frame). | `KelWorkCardRow.tsx`, `KelWorkCards.css` |

## Staff & models and the navigation clean-up (D-70 items 3 and 5) — 2026-09-27

D-70 says items 3 and 5 "follow existing patterns" (no new Figma frames). What was inferred, and from where:

| State / element | Nearest Figma source | Inference | Implementation |
| --- | --- | --- | --- |
| Settings → Kel → **Staff & models** page | Settings — Model `311:2239` (source card, rows, green/amber status words); the retired Assistants row (`311:3140`) for the nav slot and its person icon | One "Staff" source card with a muted note, then one row per role: name over a 12px one-line description, three `.kel-select` controls (Mode, Model, Reasoning), and a foot line with the status word (Available / Can't run here / Kel chooses), the engine's reason plus what Kel does instead, "Default: …" and a quiet "Reset to default". Rows are split by a neutral full-width hairline (no one-side coloured border). The nav row sits right after Model where Assistants was. | `pages/settings/StaffModelsSettings/*`, `KelInChatFrame.tsx` |
| Composer model picker labelled as Kel's own (D-69) | Overlay — Model picker `273:9301` | A 12px muted caption above the scope tabs: "Kel's model — staff use their own (Settings → Staff & models)", the same sentence as the trigger's tooltip and the phone sheet's caption; one extra menu row "Staff & models" under "Open model settings". The trigger label is unchanged. | `KelDesktopModelMenu.tsx`, `KelModelControl.tsx`, `KelMobileModelPicker.tsx` |
| Settings nav order with the moved pages | Settings nav in `311:2239` | Kel group: Model, Staff & models, Permissions, Providers, Tools, Skills, Connections, Set up Kel. Diagnostics goes in Application after System (it is about the app's health, next to backup/restore). Permissions, Providers and Diagnostics keep their Projects-nav icons. | `KelInChatFrame.tsx` |
| Projects nav after the clean-up | Projects `189:2193`, Recipes `284:8148` (both still draw Work, Permissions, Recipes, Providers, Diagnostics in the Projects nav) | Projects lists All projects, Activity, Knowledge, Scheduled tasks. Recipes keeps its one entry in the sidebar; its page keeps the Projects frame with no inner row selected — exactly as Figma's Recipes frame `284:8148` draws it. The Project page drops the "Recipes" summary card that `189:2193` draws (it only linked to the sidebar Recipes page). | `KelInChatFrame.tsx`, `projects/index.tsx` |
| Scheduled tasks from Recipes | Recipes `284:8148` (no link drawn) | A link-style "Scheduled tasks" button after the "N available here" count in the Recipes card header. | `projects/index.tsx` |
| Activity rows with Pause / Resume / Save as a recipe | Activity `189:1342` (rows with one secondary action) | The retired Work page's Pause, Resume and "Save as a recipe" (with its confirm step) sit on the job's own Activity row as a quiet or secondary button; notes and the recipe draft render under that row in a neutral outlined box. The route sentence ("Running on …") shows under running rows as a muted line. | `activity/index.tsx`, `kel-work.css` |
| Work frame `189:907` | D-70 item 5 | Retired: `/work` (any query or sub-path) redirects to the chat home. Do not restore it from Figma. | `Router.tsx` |

## Answer on the card, one live view, scoping (D-70 items 1, 2 and 4) — 2026-09-27

Source: page "Office — D-66 explorations", row 5 — 5a `480:603`, 5b `480:1096`, 5c `481:743`, 5d
`481:1098`, 5e `482:870`, 5f `482:1282` (approved by Nick 2026-09-27). Fills, borders, radii, gaps and
type sizes are the Figma values; assets were exported from the file (new: chat, sparkle, the 12px chip
check, the result chevron and the 13px folder; the rest were already in `assets/figma/work-cards`).
The scoping colour ice/300 `#CFE7FF` is now a token (`--kel-figma-color-ice-300`,
`--kel-figma-color-status-scoping`). Differences that remain, each deliberate:

| State / element | Figma | What the app does | Implementation |
| --- | --- | --- | --- |
| Typeface | Instrument Sans (stand-in) | The app's SF Pro body face at the same size and weight. | `KelWorkCardsRow5.css` |
| Chips and the answer box | drawn per frame | Two reusable components: `KelChoiceChips` (quick picks, picked = blue fill with the 12px check, dashed "Something else…") and `KelAnswerBox` (36px box + primary Send; Enter sends). The same two serve 5a and 5e. | `KelChoiceChips.tsx`, `KelAnswerBox.tsx` |
| 5a quick picks | three sample budgets | The picks the engine exposes for that wait: Allow / Don't allow for an approval, Apply anyway / Leave it for a checked change Kel held back (or an Oracle blocker), Continue for paused work. A clarification without engine-known options shows the answer box only (the engine has no option list for a free question). A pick sends at once; there is no separate confirm. | `needs_answer.py`, `KelNeedsAnswer.tsx` |
| 5a detail line | not drawn | When the engine has a reason (the Oracle's finding, why Kel held a change back) it sits under the question in 13px secondary text. | `KelNeedsAnswer.tsx` |
| 5b follow-up words | "Kel is continuing" | Truthful per answer: "Kel is continuing", or "Kel won't take that step" (Don't allow), or "Kel left it as it is" (Leave it). The line stays until the panel closes or Kel asks something new; the header takes the new state from the next read. | `needsAnswer.ts` |
| 5c line state words | "Working · 2 of 5" | The top card's own state (`office_state` on `/api/handoff`) and the engine's accepted-of-total count; "In review · N of M", "Needs you", "Stopped — see it above", "Didn't pass its checks — result below". Before the job exists: "Getting started". | `KelWorkLine.tsx` |
| 5d result sentence | a product summary ("A tray app that…") | The first sentence of Kel's published result after its lead-in (the engine has no separate one-line summary). For coding work that is often the D-65 sentence about what was applied. | `KelDoneCard.tsx` |
| 5d checks line | "4 of 4 checks passed" | Counted from the checks recorded with the result message; omitted when none were recorded. | `KelDoneCard.tsx` |
| 5d applied line | "Applied to Projects › mic-mute at 10:31 AM · you can undo it" | The folder path the engine records and the finish time; D-65 wording for undone / waiting states. | `KelDoneCard.tsx`, `changeApplication.ts` |
| 5d Details | link-style button | Opens the same top card's panel (never a second copy). The chevron on the 5d line scrolls to the done card. | `workCardEvents.ts` |
| 5e questions and "I'll build" | Kel's tailored questions and summary | From Kel's turn model when it gives them (bounded: 1–3 questions, 2–4 short answers); otherwise Kel's own two or three questions for that kind of work. The summary is the model's, else "I'll build/write/find out: <title>". | `scoping.py` |
| 5f collapsed line | "Scoped · <answers> · Started 10:04 AM" | Same; a best-guess start says "Scoped · best guess". | `KelScopingCard.tsx` |
| 5f second acknowledgement | "Starting now. An Architect is planning the pages while a Designer works from the van logo." | "Starting now with your answers. I'll post the result here once it's been checked." (the team is decided after Start, so Kel cannot name it yet) or, for best guess, the assumptions it used. | `scoping.py` |
| Scoping top card click | not drawn | Scrolls to the scoping card in the thread (or opens its chat); no detail panel, since nothing has started. | `KelWorkCardRow.tsx` |
| Needs you (home) | "Needs you" card lists only what needs you | Finished ("Done and checked") and still-running work no longer appear there; a job that has a card is answered on it ("Answer on its card" opens the chat with that card's panel open). | `resumptionBrief.ts`, `needsAttention.ts` |

## Polish batch after D-72 — 2026-09-28

No new Figma frames were drawn for these; each reuses the nearest existing component.

| State / element | Nearest Figma source | Inference | Implementation |
| --- | --- | --- | --- |
| Usage chips under a Kel reply | Composer footer stat chips in Chat `185:4284` (cost / tokens icons + muted text) | The same icons and muted text at the 12px secondary-meta size, 14px icons, 16px gaps: cost ("Included in your plan" for a subscription call, never "$0.00"; "~" for an estimate), tokens, time, model. Unknown numbers are left out. No cache or context chip (those are the conversation's, not the reply's). | `usage/KelUsageChips.tsx`, `usage/usageWords.ts` |
| Cost and time in a work card's detail header | Detail header state meta in 4b/4d | One more line in the state meta's type under the state row: cost (or plan), tokens, "N min of model time". | `KelOfficeDetail.tsx`, `KelWorkCards.css` |
| "Questions before big work" (the scoping threshold) | The Staff & models row (itself inferred from Settings — Model `311:2239`) | A second source card on Staff & models with one row: name, one-line description, a 256px `.kel-select` ("Always for bigger work" default, "Only for very big work", "Never") and the chosen option's meaning as the foot line. | `StaffModelsSettings/index.tsx`, `scoping.py` |
| "Fell back to X last time" on a staff row | Staff row foot line (inferred, above) | One 12px line in the attention colour under the row's foot, only when the role's last run ran a different model than it asked for: "Fell back to Codex last time (asked for Claude Opus 5.5): <the engine's reason>." | `StaffModelsSettings/index.tsx`, `role_models.last_runs` |
| "How Kel picks models" | Settings source card; no table drawn anywhere in the file | A read-only table in a third source card: Work · Decided by (role · mode) · Effort (Quick / Standard / Thorough / Most careful for the engine's tiers) · Kel tries (the first three runnable models, the first one's reason, and how many can't run here). Rows split by the neutral hairline; header in the 12px muted field-label type; scrolls sideways on a phone. | `StaffModelsSettings/index.tsx`, `staffModels.css` |
| Scoping answers typed in the chat | Scoping card 5e | The card pre-picks what Kel understood from the message (chips selected; "Something else…" filled) and says so in one 13px line under the heading: "Filled in from your message (2 of 3). Change any, then Start — or say “start” in the chat." | `KelScopingCard.tsx`, `KelWorkCardsRow5.css` |
| A card stopped on its budget, "Raise budget" | "Needs you" result box (inferred for D-68, above) | The same amber-dot box headed "Stopped on its budget": what it used against its budget in plain numbers, a primary "Raise budget" and the next size ("Next size: large — up to 8M tokens, 4 hours of run time and $30 of model use"). After raising, one plain line says the new size and that Kel is continuing. Budget classes read small / standard / large / largest. | `KelBudgetStop.tsx`, `KelOfficeDetail.tsx` |
| Where a change was applied (done card, result message) | 5d "Applied to Projects › mic-mute at 10:31 AM · you can undo it" | The project's name and its folder once — "Applied to Calc demo (folder R6Proj) at 10:31 AM · you can undo it", or just the folder when the project is named after it; the full path is the line's tooltip and stays behind Open folder. The done card's sentence drops the result's own "Applied to …:" lead ("Changed calc.py (1 file)."), and the engine's result message names the place the same way. | `KelDoneCard.tsx`, `changeApplication.ts`, `auto_apply.py` |

## Visual-audit fixes (VIS, D-73) — 2026-09-28

Where the app now differs from, or goes beyond, a Figma frame after the visual audit's fixes.

| State / element | Figma | What the app does | Implementation |
| --- | --- | --- | --- |
| Notifications switch (D-73.1) | System `314:3912` has no such row | One more General row after Close to tray, same row and toggle: "Notifications — Tell you on the desktop when work finishes or Kel needs you while its window is in the background." Keep computer awake is back as the first General row, as drawn. | `SystemModalContent/index.tsx` |
| About build row (D-56) | About `314:4871` shows Check for updates, no build | A "Build" row under Version with the source commit the package was made from. | `AboutModalContent.tsx`, `electron.vite.config.ts` |
| Back up / Restore folder dialog | Restore confirm `314:4383` (the later "Restore this backup?" step) | The folder-picking step takes that dialog's styling: 16px glass card, left 18px title, link-style Cancel, one blue primary. The confirm step itself is unchanged. | `KelDataCard.tsx`, `kel-shell.css` (`.kel-shell-dialog-modal`) |
| One primary per view on Set up Kel | Setup `189:4492` draws three primaries (Add Model, Change, Start using Kel) | Add model stays primary; Change and Start using Kel are secondary. Figma's button rule ("Secondary for any boxed action") and the audit's one-primary rule outrank the frame. | `onboarding/index.tsx` |
| Recipes filter words | Recipes `284:8148` says "Favourites" | en-US (D-61): "Favorites", "Uncategorized". Preview takes the link style (14px semibold, link blue) as drawn. | `projects/index.tsx`, `recipes.py` |
| Reconnect on the error card | Chat — Agent error `273:13090` has Pick another model / Try again only | A link-style "Reconnect" beside them restarts Kel's chat connection; the permanent title-bar restart icon (not in any frame) is gone. | `MessageTips.tsx` |
| Ramble with recordings but none open | Ramble `194:1366` always shows an open transcript | The main pane lists the recordings (name, date, length) under "Your recordings"; the first-run empty state is kept for an empty library, without a second Upload button. | `transcription/index.tsx` |
| Keyboard focus in menus (JR-26) | No focus frames for the row, model, attach or reply menus | Focus moves to the first item on open and follows the arrows; the focused item uses the existing 2px focus ring. The row's ⋯ button is shown while the row has focus. | `useMenuKeyboard.ts`, `ConversationRow.tsx` |
| Markdown lists in replies | Chat `185:4284` | List items use the paragraph's primary colour, font and line height; bold stays in the body face. | `kel-shell.css` |

## Frames retired by decisions D-59..D-64 — 2026-09-27 (trim and harden pass)

Figma still draws these; the product no longer has them. Do not restore them from Figma.

| Figma frame | Decision | What the app does now | Implementation |
| --- | --- | --- | --- |
| Desktop Settings — Assistants `311:3140`; mobile `300:15057` | D-60 (Kel is the only assistant) | No Assistants page or nav row; `/settings/assistants` and `/settings/agent*` go to Model, `/assistants` and `/team/:id` go Home. | `Router.tsx`, `KelInChatFrame.tsx` |
| Desktop Settings — Skills `311:3536`; mobile `300:15176` ("Skills Hub" title, "enable on an assistant" tip) | D-60 (no hub or store) | Skills lists "Built into Kel" and "Added by you" with a plain tip; the phone title is "Skills". Hub, detail and import-history routes go to Skills. | `SkillsOverviewSettings/index.tsx` |
| Extension settings tabs (any `Extensions` nav group) | D-60 | No extension group or `/settings/ext/*` page (redirects to System); Tools lists no extension-contributed MCP servers. | `KelInChatFrame.tsx`, `useMcpServers.ts` |
| Reply actions in Chat `185:4284` / `299:11571` (thumbs up/down) | D-59 | Replies keep Copy (in the ⋯ menu, direct on the phone), Fork when available, and Details. | `MessageText.tsx` |
| Language row in System `314:3912` / `300:2816`; language picker on the WebUI sign-in page | D-61 (English only) | No language row or picker. | `SystemModalContent/index.tsx`, `pages/login/index.tsx` |
| Set up Kel — Autonomy step ("Ask before edits" button) | D-64 (Full access by default) | The step shows the Full access / Ask first card also used on Permissions and Settings → System. No Figma frame for the card itself; it reuses the Card + preference-row + Toggle components. | `KelAuthorityCard.tsx` |
| WebUI sign-out | CP-12 | The hidden Ctrl/Cmd+Shift+L chord is gone; in a browser, Settings → Remote / WebUI shows a "This browser — Sign out" card (Card + Button components; no Figma frame). | `WebuiSettings.tsx` |

## Current revision gaps (2026-09-25)

The live desktop page is `319:2`; the live mobile page is `319:3858`. The older source IDs and findings below are **SUPERSEDED BY FIGMA REVISION** where they describe presentation. Keep them as history. The [current frame inventory](evidence/figma-full-audit/FIGMA_REVISION_2026-09-25.md) tracks the new source.

| State | Closest current Figma source | Inference or open decision | Implementation |
| --- | --- | --- | --- |
| MCP server reports no tools | Mobile detail `315:3004` and mobile Card/List row components `213:3` | Show a neutral `No tools reported` line in the same card. Do not invent tool names. | `ToolsModalContent.tsx` |
| Runtime MCP error text and check time vary | Desktop Tools `313:2441`; mobile detail `315:3004` | Use the Figma warning surface and real check time. Keep the longer diagnostic in the existing status popover. | `McpServerItem.tsx`, `ToolsModalContent.tsx` |
| Mobile Kibble entry | Current mobile Chat `299:11571` and Tools `315:2842` show four tabs without Kibble; current Components page still includes an older five-tab variant. | Nick chose Settings → Tools → Kibble. The four-tab package and navigation pass are [recorded](evidence/figma-full-audit/MOBILE_NAV_CURRENT_REVISION.md). The additive Tools row has no Figma sample frame. | `KelMobileTabs.tsx`, `ToolsSettings/index.tsx` |
| CLI discovery and import | Desktop Tools `313:3911` | The selectable list is packaged with intercepted rows. Real CLI discovery and import were not submitted; this remains a behavior check. | `OneClickImportModal.tsx` |
| Failed-server report delivery | Desktop Tools `313:4441` | The focused dialog is packaged. Figma's filled text is sample data, and “3 days of logs are attached” cannot be promised before collection. The source uses blank input and accurate availability copy. No report was sent. | `FeedbackReportModal.tsx`, feedback service |
| Sign-in-needed Tools row | Desktop `313:2441`, mobile `315:2842` | A real OAuth-required local fixture was not created. The row uses existing OAuth state, but the current revision's populated sign-in state lacks packaged proof. | `McpServerHeader.tsx` |
| Populated mobile server tools | Mobile detail `315:3004` | The isolated failing server reports zero tools. The neutral empty line is an inference; verify live tool rows with a safe fixture. | `ToolsModalContent.tsx` |
| Mobile Ramble folder management | Mobile Ramble `299:12588`, mobile Card/List row components `213:3` | The sample folder card has no rename/delete affordance. Existing mobile actions stay visible until a safe mobile action pattern is verified; hiding them would make folder management unreachable. | `transcription/index.tsx`, `kel-shell.css` |
| Mobile Ramble vetting preview | Mobile sheet `299:12871` | An isolated engine preview now feeds the sheet. The engine returned one proposal for the whole synthetic text, not Figma's one-row “Check” state. Do not infer that badge without row-level confidence. Accept/process submission and physical phone rendering remain open. | `transcription/index.tsx` |
| Mobile Projects with multiple projects | Mobile index `299:13686` | The scoped package uses one synthetic project. With several projects, keep the heading generic until a real selector can scope Work and Knowledge; never imply the first project owns global content. | `KelInChatFrame.tsx`, Work/Knowledge routes |
| Mobile Work with real jobs | Mobile Work `299:13910` shows only empty cards | Keep the existing job actions and render the same Card language for populated rows. Do not invent a sample job merely for visual parity. | `work/index.tsx`, `kel-shell.css` |
| Mobile Activity states beyond one running job | Mobile Activity `299:14061` | Use the same Card and row components for multiple, paused, failed, and finished jobs. A synthetic engine claim verified the one running row only; a real model worker was not started. | `activity/index.tsx`, `kel-shell.css` |
| Populated mobile Permissions | Mobile Permissions `299:14218` shows empty grants and requests | The empty cards and dynamic digest match the current frame. Keep real grants and requests; their populated rows need a separate direct Figma comparison. | `autonomy/index.tsx`, `kel-shell.css` |
| Populated mobile Knowledge | Mobile Knowledge `299:14371` shows two suggestions and three map rows | A bounded engine fixture now shows two proposals and five map sections in a scoped package. Accept and Reject were not submitted; row count and order depend on real data. | `projects/index.tsx`, engine memory and project map |
| Chat Permission runtime modes | Mobile sheet `299:12418` shows five choices, Plan Mode selected | The sheet geometry and material match in a disposable package using session-gated injected options. Its isolated ACP session returned no mode catalog. Runtime mode discovery and a real switch remain open. | `MobileActionSheet.tsx`, `useAcpConfigOptions.ts` |


**2026-09-23 update:** this file is a historical audit of the older `76:2` page. The current FINAL desktop page is `185:2`, and Figma now has 28 mobile screens on `213:2`. The [51-screen audit](evidence/figma-full-audit/README.md) supersedes the “No mobile final frame” row and tracks current gaps.

Source: Kel Design System `BlpVvZGuc9j9HhxUojIiJI`, final screens on page `76:2`.
Audit 2 supersedes the earlier sidebar, extra-card, and placeholder-copy decisions.

| State | Source | Current decision / limit | Location |
|---|---|---|---|
| Hidden template descriptions and Add Theme actions | Effective visibility through every ancestor of final frames | Copy visible strings literally. Do not render hidden component defaults. The earlier question incorrectly described hidden layers as visible copy; the audit corrected that error. | `ShellSourceCardHeader.tsx`, `evidence/audit-2/figma-visible-copy.json` |
| Typography conflict with older Inter frames | User's DS v2 Foundations image | Instrument Sans for headings, navigation and controls; SF Pro Text for body/meta. No Inter. | `kelFonts.ts`, `kel-shell.css` |
| Sidebar entry points absent from the reference | Home `94:1585` | Latest instruction governs: remove extra primary navigation, Tools, project groups and footer. Preserve route implementations and Kibble shortcut. | `Sider/index.tsx`, `GroupedHistory/index.tsx` |
| Empty and populated live data differ from sample data | Home, Work, Projects, Providers and Scheduled frames | Read existing state. No sample conversations, fake provider readiness, sample tasks, prices, token counts or context percentages in production. | Existing state hooks, `ShellComposerMetrics.tsx` |
| Usage not reported by runtime | Home/Chat footer | Keep the source field arrangement and show an em dash. Remaining context is unknown without a reported limit. | `ShellComposerMetrics.tsx` |
| No mobile final frame | Desktop 1440 x 900 frames | Retain the existing drawer and control sheet. Wrap footer fields and controls; retain 44px touch targets. | `kel-shell.css` |
| Native window controls absent from screenshot | Existing desktop titlebar | Keep window and navigation controls. Ramble's document returns to the source y68 position. | Existing titlebar, `kel-shell.css` |
| Native-only Settings operations in WebUI | WebUI and Pet frames | Desktop-only controls retain runtime support rules. Browser Pet reports its native requirement. | `WebuiModalContent.tsx`, `PetSettings.tsx` |
| Diagnostics Clear and Restart have no matching safe runtime operations | Diagnostics `76:4130` | Source controls are present and disabled. Do not relabel unrelated destructive purge/compaction operations. | `diagnostics/index.tsx` |
| Onboarding autonomy selector has no matching writable mode contract | Setup `123:1789` | Source label opens existing Permissions. Completion remains persisted. Change opens existing Projects. No new permissions engine. | `onboarding/index.tsx` |
| Backup and restore require folder input | System `124:2028` | Source row buttons open a folder-path dialog and retain existing backup/inspect/restore handlers and confirmation. | `KelDataCard.tsx` |
| Populated integrations require setup details | Providers `76:3996` | Compact source rows expand to real credential controls. No separate extra-tools card. | `providers/index.tsx` |
| Model provider-specific required fields | Model `76:3222` | Default modal uses four source fields. Bedrock/New API may show required provider-specific fields. Existing validation remains. | `AddPlatformModal.tsx` |
| Retired Assistants and Skills routes | `76:3474`, `76:3503` | Existing redirects remain. These two frames are not restored by this presentation pass and remain a known scope gap. | Existing `Router.tsx` |
| Source panel raster cannot be recovered through the connector | Theme panel `76:3173` | Connector returned a transparent 32px placeholder for the image fill. The shell uses source canvas assets and mapped glass fills. Exact raster parity is not claimed. | `assets/figma/canvas.svg`, `kel-shell.css` |
| Anonymous direct-route WebUI startup | Fresh unauthenticated `/guid` | Intermittent blank startup was observed without a page error. The visual audit starts through `/login`; this startup issue is not claimed fixed. | Existing WebUI authentication/startup |
| No reference for Kibble or Connections | Nearest DS cards/buttons | Existing routes retain their behavior with shared shell styling. | `dogfood/index.tsx`, Connections |

Audit evidence and checks: [SHELL_AUDIT_2.md](SHELL_AUDIT_2.md).
