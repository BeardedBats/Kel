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
