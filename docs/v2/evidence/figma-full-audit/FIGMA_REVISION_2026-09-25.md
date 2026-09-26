# Current Figma revision inventory — 2026-09-25

**Source:** live [Kel Design System](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System), desktop page `319:2`, mobile page `319:3858`, Foundations `139:2`, Components `136:2`, mobile components `213:3`. Read directly through Figma on 2026-09-25. Figma did not expose a revision SHA through this read.

**Prior baseline:** [pair-map.json](pair-map.json) lists 23 desktop and 28 mobile frames on deleted desktop/mobile pages `185:2` and `213:2`. The live pages contain 75 desktop and 50 mobile 1440×900/393×852 frames. Frame IDs establish source replacement or retention only; they do not prove whether pixels inside retained nodes changed. All prior image comparisons require revalidation against current source.

**Status key:** `READ` means current Figma frame was inspected at high fidelity; `PENDING` means structure only. Neither means production parity.

## Exact deltas confirmed so far

- Desktop Tools `313:2441` replaces `188:1956`. It shows four MCP rows: `local-audit-mcp` (`Check failed` with inline warning and checked time), `chrome-devtools` (`Connected`), `linear-mcp` (`Sign in needed`), and `Kel Browser` (`Not tested`). It also shows `Generate images` off, `Needs an image model first`, and `Image model / Set up a model`. Production now uses these labels and roles. Disposable packaged checks at 1440 and 800px used three real local rows; the unavailable sign-in row was not fabricated. See [scoped Tools evidence](TOOLS_CURRENT_REVISION.md).
- Mobile Tools `315:2842` replaces `219:767`. It shows four condensed MCP rows with right chevrons and the same four statuses, plus a separate image card with `Generate images` off and `Image model / Set up`. Production now uses this layout. Disposable packaged checks at 393 and 320px did not overflow. Nick resolved the Kibble entry through Settings → Tools; [current navigation evidence](MOBILE_NAV_CURRENT_REVISION.md) supersedes earlier five-tab captures.
- Mobile MCP detail `315:3004` is newly explicit: a status card, error note, tools list, and bottom Test again / Report issue / Delete server actions. Production now has a data-driven detail view. The synthetic server reported no tools, so populated tool rows remain unverified.
- Desktop Tools overlay nodes `313:2923`, `313:3413`, `313:3911`, `313:4441`, and `313:4940` were read directly. Add and row menus, JSON, CLI import, report, and delete dialogs have source repairs. The CLI and report dialogs have scoped package captures; real import and report delivery were not invoked.
- Desktop Connections `269:5`, `269:501`, `269:971`, and `269:1419` were read directly. The populated Services rows and inline credential editor now have [scoped package captures](DESKTOP_CONNECTIONS_CURRENT_REVISION.md). Confirmation placement has a DOM test; no packaged mutating action exists in the current engine catalog.
- Current mobile Chat `299:11571`, drawer `299:11583`, and Tools `315:2842` show four bottom tabs: Chats, Ramble, Projects, Settings. Nick chose Settings → Tools → Kibble. The [disposable package](MOBILE_NAV_CURRENT_REVISION.md) now has those four tabs and a tested Kibble path; older five-tab captures are superseded for navigation.
- Desktop Chat `185:4284` and mobile Chat/drawer were read and compared with a two-turn disposable package fixture. Mobile message width, reply actions, composer height, and drawer controls were repaired. [The scoped Chat record](CHAT_CURRENT_REVISION.md) shows captures and measured limits; desktop plan, project metrics, and phone chrome remain open. Four-tab placement has a later [package record](MOBILE_NAV_CURRENT_REVISION.md).
- Desktop approval `273:1911` and mobile approval `299:11950` were read and compared with an isolated engine approval. The full-width pending card, command box, responsive actions, and settled strip have [scoped package evidence](CHAT_APPROVAL_CURRENT_REVISION.md). Approval resolution was covered by focused tests, not a packaged click.
- Desktop tool-call/plan `273:12914` and mobile `299:12459` were read and compared with an isolated package. Three synthetic ACP calls and a processing plan have [scoped package evidence](CHAT_TOOL_PLAN_CURRENT_REVISION.md); real model tool output remains open.
- Desktop Chat agent error `273:13090` and mobile `299:12494` were read and compared with an isolated package. The timeout card matches its 920×114 and 361×200 frame bounds; model choice and diagnostic details opened. See [scoped error evidence](CHAT_AGENT_ERROR_CURRENT_REVISION.md). A live provider timeout and retry remain unverified.
- Desktop reconnecting `273:12681` and mobile `299:12515` were read and compared with a disposable package. The composer notice matches 920×60 desktop and 361×48 mobile frame bounds. See [scoped reconnecting evidence](CHAT_RECONNECTING_CURRENT_REVISION.md). The renderer state was injected; no real engine restart was invoked.
- Mobile model picker `299:12372` was read and compared with an isolated package. The 393×410 bottom sheet matches Figma's x0/y442 bounds, glass and 20px top radius. Per-chat choice and reset worked against an isolated engine record. See [scoped picker evidence](CHAT_MODEL_PICKER_CURRENT_REVISION.md). The model labels depend on live configuration; default-choice persistence remains open.
- Mobile approval details `299:12281` was read and compared with an isolated pending approval. The 393×433 sheet matches Figma's x0/y419 bounds and x17/y723 Approve button. See [scoped details evidence](CHAT_APPROVAL_DETAILS_CURRENT_REVISION.md). The decision buttons were not clicked.
- Long Transcriptions frame `189:4032` remains on the new desktop page. Its populated document and four footer actions have a [scoped disposable package comparison](TRANSCRIPTIONS_CURRENT_REVISION.md) at 1440 and 800px. The selected text and audio are synthetic; live Muse content remains unverified.
- Mobile Ramble list `299:12588` and transcript `299:12782` have a [scoped disposable package comparison](RAMBLE_MOBILE_CURRENT_REVISION.md) at 393 and 320px. Search, folder card, recording card, record action, document, and footer bounds were measured. Vetting sheet `299:12871` now has a separate [engine-backed package comparison](RAMBLE_VETTING_CURRENT_REVISION.md). Synthetic content, mobile folder actions, native titlebar, and font rasterization limit pixel parity. Earlier five-tab screenshots are superseded for navigation.
- Mobile Permissions `299:14218` has a [scoped disposable package comparison](PERMISSIONS_CURRENT_REVISION.md) at 393 and 320px. Its three card bounds match within 1px; the real isolated digest opens the existing check controls. Populated grants and access requests remain open.
- Mobile Knowledge `299:14371` was read directly and now has a [scoped engine-backed package comparison](KNOWLEDGE_CURRENT_REVISION.md) with two proposals and five map sections. The first card begins at Figma's x16/y114. The data-dependent row count, choice order, font, and phone chrome limit pixel parity.
- The live desktop page adds explicit overlay, error, loading, populated, startup, Connections, Recipes, and task-detail frames. The live mobile page likewise adds explicit row-action, approval, memory, model-picker, permission, error, reconnecting, Recipes, Connections, and populated Tools states. The old pair map had no direct frame for these states.

## Desktop FINAL frames

| Current node | Frame | Production counterpart | Source delta against prior pair map | Status |
| --- | --- | --- | --- | --- |
| `185:4284` | Kel / Chat | `/chat` | Retained node; current populated frame read and small-fixture comparison recorded. | READ |
| `185:2658` | Kel / Home | `/home` | Current heading, Needs you card, and composer compared in isolated package at 1440px. [Scoped evidence](DESKTOP_HOME_CURRENT_REVISION.md). | READ |
| `189:907` | Kel / Work | `/work` | Current empty cards measured at 1440 and 800px. Active/waiting states have [source evidence](DESKTOP_WORK_PERMISSIONS_STATES.md); live Pause/Cancel remains open. [Scoped evidence](DESKTOP_WORK_CURRENT_REVISION.md). | READ |
| `189:1342` | Kel / Activity | `/activity` | Current frame read; empty cards checked in a package. Populated active work remains open. [Scoped evidence](DESKTOP_ACTIVITY_CURRENT_REVISION.md). | READ |
| `189:1758` | Kel / Permissions | `/autonomy` | Current empty cards measured at 1440 and 800px. Real isolated grants/requests have [source evidence](DESKTOP_WORK_PERMISSIONS_STATES.md); grant/revoke passed. [Scoped evidence](DESKTOP_PERMISSIONS_CURRENT_REVISION.md). | READ |
| `189:2193` | Kel / Projects | `/projects` | Empty cards now match Figma at 1440 and 800px; Refresh map remains accessible on hover/focus. [Scoped evidence](DESKTOP_PROJECTS_CURRENT_REVISION.md). | READ |
| `189:2628` | Kel / Scheduled tasks | `/scheduled` | Selected card controls implemented and package-checked. Three sample tasks and history remain open. [Scoped evidence](DESKTOP_SCHEDULED_LIST_CURRENT_REVISION.md). | READ |
| `189:3098` | Kel / Providers | `/providers` | Real catalog and three truthful readiness rows package-checked; live model response remains open. [Scoped evidence](DESKTOP_PROVIDERS_CURRENT_REVISION.md). | READ |
| `189:3564` | Kel / Diagnostics | `/diagnostics` | Data-driven cards package-checked; two maintenance actions remain disabled. [Scoped evidence](DESKTOP_DIAGNOSTICS_CURRENT_REVISION.md). | READ |
| `189:4032` | Kel / Transcriptions | `/transcription/library` | Current populated panel and four footer actions compared in isolated package. | READ |
| `189:4492` | Kel / Set up Kel | `/onboarding` | [Context inspected](DESKTOP_CURRENT_AUDIT_COVERAGE.md); implementation comparison remains open. | READ |
| `194:1366` | Kel / Ramble | `/transcription` | [Ramble source evidence](DESKTOP_RAMBLE_CURRENT_REVISION.md); package pending. | READ |
| `271:247` | Kel / Knowledge — Suggestions & map | `/projects/knowledge` | [Source implementation and real engine actions at 1440/800px](DESKTOP_KNOWLEDGE_CURRENT_REVISION.md); milestone package pending. | READ |
| `284:8148` | Kel / Recipes | `/recipes` | Current list implemented and compared in isolated package. [Scoped evidence](DESKTOP_RECIPES_CURRENT_REVISION.md). | READ |
| `284:8489` | Kel / Recipes — Run | `/recipes` | Real input form implemented and compared in isolated package; no submission. [Scoped evidence](DESKTOP_RECIPES_CURRENT_REVISION.md). | READ |
| `284:8847` | Kel / Recipes — Preview | `/recipes` | Engine steps and history surface implemented and compared in isolated package. [Scoped evidence](DESKTOP_RECIPES_CURRENT_REVISION.md). | READ |
| `272:7932` | Kel / Sign in (remote) | `shared shell / overlay` | [Context inspected](DESKTOP_CURRENT_AUDIT_COVERAGE.md); implementation comparison remains open. | READ |
| `272:739` | Kel / Scheduled task — Detail | `/scheduled` | Details and History implemented and measured at 1440 and 800px. [Scoped evidence](DESKTOP_SCHEDULED_TASK_DETAIL_CURRENT_REVISION.md). | READ |
| `272:1087` | Kel / Kibble | `/kibble` | [Context inspected](DESKTOP_CURRENT_AUDIT_COVERAGE.md); implementation comparison remains open. | READ |
| `272:8149` | Kel / Startup — Starting up | `shared shell / overlay` | [Runtime source checks](DESKTOP_RUNTIME_VIEWS_SOURCE.md); milestone package pending. | READ |
| `272:8364` | Kel / Startup — Engine not running | `shared shell / overlay` | [Runtime source checks](DESKTOP_RUNTIME_VIEWS_SOURCE.md); milestone package pending. | READ |
| `269:5` | Kel / Connections | `/connections` | Populated Services rows measured in an isolated package at 1440 and 800px. [Scoped evidence](DESKTOP_CONNECTIONS_CURRENT_REVISION.md). | READ |
| `269:501` | Kel / Connections — Add a service | `/connections` | Six main fields in two columns; extra options and taller card remain. [Scoped evidence](DESKTOP_CONNECTIONS_CURRENT_REVISION.md). | READ |
| `269:971` | Kel / Connections — Add credential | `/connections` | Inline editor captured in an isolated package; secure-store value never submitted. [Scoped evidence](DESKTOP_CONNECTIONS_CURRENT_REVISION.md). | READ |
| `269:1419` | Kel / Connections — Run an action | `/connections` | Confirmation placement tested in DOM; no real mutating catalog action exists for package capture. [Scoped evidence](DESKTOP_CONNECTIONS_CURRENT_REVISION.md). | READ |
| `311:2239` | Kel / Settings — Model | `/settings/model` | Default and populated custom-model rows with real actions package-checked at 1440/800; healthy remote response remains open. [Scoped evidence](DESKTOP_MODEL_CURRENT_REVISION.md). | READ |
| `311:2730` | Kel / Settings — Model — Add model | `/settings/model` | Compact multi-model dialog implemented and package-checked; blank credential differs from Figma's successful sample. [Scoped evidence](DESKTOP_MODEL_CURRENT_REVISION.md). | READ |
| `311:3140` | Kel / Settings — Assistants | `/settings/assistants` | Actual Kel row and single-card layout package-checked at 1440/800; sample extra assistants absent. [Scoped evidence](DESKTOP_CATALOG_CURRENT_REVISION.md). | READ |
| `311:3536` | Kel / Settings — Skills | `/settings/skills` | Heading and catalog row source aligned; truthful empty package state checked at 1440/800. Populated custom-skill package state open. [Scoped evidence](DESKTOP_CATALOG_CURRENT_REVISION.md). | READ |
| `313:2441` | Kel / Settings — Tools | `/settings/tools` | Replaces `188:1956`; four MCP status rows and image-off card confirmed. | READ |
| `313:2923` | Kel / Settings — Tools — Add menu and row menu | `/settings/tools` | Read menu labels and actions; source now uses Paste JSON / Import from a CLI. | READ |
| `313:3413` | Kel / Settings — Tools — Paste JSON | `/settings/tools` | Read 600px glass dialog, sample JSON, hint and buttons; source repaired and packaged at 1440px. | READ |
| `313:3911` | Kel / Settings — Tools — Import from a CLI | `/settings/tools` | Five-row selectable example; repaired and checked in disposable package with intercepted rows. | READ |
| `313:4441` | Kel / Settings — Tools — Report issue | `/settings/tools` | Failure-specific report dialog repaired and checked in disposable package; no report sent. | READ |
| `313:4940` | Kel / Settings — Tools — Delete server | `/settings/tools` | Read 460px danger dialog; source copy and style repaired; disposable package check passed. | READ |
| `314:2863` | Kel / Settings — Appearance | `/settings/appearance` | Four-slot theme gallery, six primary colors, and text/zoom card package-checked at 1440/800. [Scoped evidence](DESKTOP_APPEARANCE_CURRENT_REVISION.md). | READ |
| `314:3373` | Kel / Settings — Appearance — Add theme | `/settings/appearance` | Compact dialog package-checked; save/select/reload worked in an isolated profile. [Scoped evidence](DESKTOP_APPEARANCE_CURRENT_REVISION.md). | READ |
| `314:3912` | Kel / Settings — System | `/settings/system` | Data and backup and General package-checked at 1440/800; real preference values retained. [Scoped evidence](DESKTOP_SYSTEM_ABOUT_CURRENT_REVISION.md). | READ |
| `314:4383` | Kel / Settings — System — Restore | `/settings/system` | Real isolated backup inspection opened the compact confirmation; canceled without restore. [Scoped evidence](DESKTOP_SYSTEM_ABOUT_CURRENT_REVISION.md). | READ |
| `314:4871` | Kel / Settings — About | `/settings/about` | Header update action and four rows package-checked at 1440/800; notices opened. [Scoped evidence](DESKTOP_SYSTEM_ABOUT_CURRENT_REVISION.md). | READ |
| `314:5271` | Kel / Settings — Desktop Pet | `/settings/pet` | [Context inspected](DESKTOP_CURRENT_AUDIT_COVERAGE.md); implementation comparison remains open. | READ |
| `314:18314` | Kel / Settings — WebUI | `/settings/webui` | Real isolated running and remote-enabled states package-checked at 1440/800. [Scoped evidence](DESKTOP_WEBUI_CURRENT_REVISION.md). | READ |
| `314:18753` | Kel / Settings — WebUI — Change password | `/settings/webui` | Mismatch error and compact dialog package-checked; no password changed. [Scoped evidence](DESKTOP_WEBUI_CURRENT_REVISION.md). | READ |
| `314:19219` | Kel / Settings — Archived | `/settings/archived` | Synthetic three-chat project grouping package-checked at 1440/800. [Scoped evidence](DESKTOP_ARCHIVED_CURRENT_REVISION.md). | READ |
| `314:19647` | Kel / Settings — Archived — Select | `/settings/archived` | Two-row selection and delete confirmation package-checked and canceled. [Scoped evidence](DESKTOP_ARCHIVED_CURRENT_REVISION.md). | READ |
| `273:595` | Kel / Overlay — Command palette | `shared shell / overlay` | 640×429 package at both widths; focus/Escape/Capture action pass. Final focus-ring CSS has source-render proof. [Evidence](DESKTOP_CHAT_OVERLAYS_CURRENT_REVISION.md). | READ |
| `273:906` | Kel / Overlay — Fix Capture · Select | `shared shell / overlay` | Scoped isolated 1440/800px package comparison; synthetic recording lifecycle. [Evidence](DESKTOP_FIX_CAPTURE_CURRENT_REVISION.md). | READ |
| `273:1091` | Kel / Overlay — Fix Capture · Recording | `shared shell / overlay` | Scoped isolated 1440/800px package comparison; synthetic recording lifecycle. [Evidence](DESKTOP_FIX_CAPTURE_CURRENT_REVISION.md). | READ |
| `273:1338` | Kel / Overlay — Fix Capture · Review | `shared shell / overlay` | Scoped isolated 1440/800px package comparison; synthetic recording lifecycle. [Evidence](DESKTOP_FIX_CAPTURE_CURRENT_REVISION.md). | READ |
| `273:1586` | Kel / Overlay — New scheduled task | `/scheduled` | Filled unsaved form matched x420/y70, 600×614 in disposable desktop package. [Scoped evidence](DESKTOP_OVERLAYS_CURRENT_REVISION.md). | READ |
| `273:2125` | Kel / Overlay — Approval details | `shared shell / overlay` | Synthetic pending approval opened real details; x440/y109.5, 560×401. [Scoped evidence](DESKTOP_OVERLAYS_CURRENT_REVISION.md). | READ |
| `273:8389` | Kel / Overlay — Memory review | `shared shell / overlay` | [440×236 source render; actions checked](DESKTOP_CHAT_MENUS_CURRENT_REVISION.md). Milestone package pending. | READ |
| `273:8648` | Kel / Overlay — Chat row menu | `/chat` | Six actual actions, 232×227 package; intercepted export-content probe. [Evidence](DESKTOP_CHAT_OVERLAYS_CURRENT_REVISION.md). | READ |
| `273:8854` | Kel / Overlay — Rename chat | `/chat` | 440×168 package, x500/y280 at 1440px; canceled at both widths. [Evidence](DESKTOP_CHAT_OVERLAYS_CURRENT_REVISION.md). | READ |
| `273:9098` | Kel / Overlay — Permission menu | `shared shell / overlay` | [300×286 source render; injected modes](DESKTOP_CHAT_MENUS_CURRENT_REVISION.md). Labels now match; milestone package pending. | READ |
| `273:9301` | Kel / Overlay — Model picker | `chat composer` | 280px glass menu, scoped engine writes, Add Model, and Escape checked at 1440/800px. [Evidence](DESKTOP_PICKERS_CURRENT_REVISION.md). | READ |
| `273:9512` | Kel / Overlay — Project picker | `shared shell / overlay` | 320px search menu, select/clear, Escape, and injected browse result checked at 1440/800px. [Evidence](DESKTOP_PICKERS_CURRENT_REVISION.md). | READ |
| `273:9737` | Kel / Overlay — Slash menu | `shared shell / overlay` | [340px source render; actual commands](DESKTOP_CHAT_MENUS_CURRENT_REVISION.md). Labels now match; milestone package pending. | READ |
| `273:9951` | Kel / Overlay — Attach menu | `shared shell / overlay` | [220px source render; both file paths](DESKTOP_CHAT_MENUS_CURRENT_REVISION.md). Actual catalog controls retained; milestone package pending. | READ |
| `273:10383` | Kel / Overlay — Ramble API key | `/transcription` | [Ramble source evidence](DESKTOP_RAMBLE_CURRENT_REVISION.md); package pending. | READ |
| `273:10168` | Kel / Overlay — Update available | `shared shell / overlay` | [Shared dialog source checks](DESKTOP_SHARED_DIALOGS_SOURCE.md); milestone package pending. | READ |
| `273:10599` | Kel / Overlay — Ramble merge | `/transcription` | [Ramble source evidence](DESKTOP_RAMBLE_CURRENT_REVISION.md); package pending. | READ |
| `273:10837` | Kel / Overlay — Ramble vetting answers | `/transcription` | [Ramble source evidence](DESKTOP_RAMBLE_CURRENT_REVISION.md); package pending. | READ |
| `273:11082` | Kel / Overlay — Export diagnostics | `/diagnostics` | [Runtime source checks](DESKTOP_RUNTIME_VIEWS_SOURCE.md); milestone package pending. | READ |
| `273:11796` | Kel / Overlay — Confirm delete | `shared shell / overlay` | [Shared dialog source checks](DESKTOP_SHARED_DIALOGS_SOURCE.md); deletion handoff intercepted. | READ |
| `273:1911` | Kel / Chat — Approval card | `/chat` | Current pending and settled shapes compared in isolated package at 1440px. | READ |
| `273:12085` | Kel / State — Empty (Connections) | `/connections` | Current empty card implemented and compared in isolated package at 1440 and 800px. [Scoped evidence](DESKTOP_CONNECTIONS_CURRENT_REVISION.md). | READ |
| `273:12291` | Kel / State — Loading (Activity) | `/activity` | [Isolated package checks](DESKTOP_PENDING_STATES_CURRENT_REVISION.md), source `98387fc`. | READ |
| `273:12486` | Kel / State — Error (Providers) | `/providers` | [Isolated package checks](DESKTOP_PENDING_STATES_CURRENT_REVISION.md), source `98387fc`. | READ |
| `273:12681` | Kel / State — Reconnecting | `/chat` | Current composer notice read and scoped package comparison recorded. | READ |
| `273:12914` | Kel / Chat — Tool calls and plan | `/chat` | Three tool rows and compact plan compared in isolated package at 1440px. | READ |
| `273:13090` | Kel / Chat — Agent error | `/chat` | Current timeout card read and scoped package comparison recorded. | READ |
| `273:13249` | Kel / Chat — Workspace panel | `/chat` project panel | Real SCM/search, folder actions, 28px rows and narrow composer checked at 1440/800px. [Evidence](DESKTOP_WORKSPACE_CURRENT_REVISION.md). | READ |
| `273:13459` | Kel / Chat — File preview | `/chat` | 560px pane, real file tabs, read-only/split/edit/save/restore/attach checked at 1440/800px. [Evidence](DESKTOP_WORKSPACE_CURRENT_REVISION.md). | READ |
| `273:13646` | Kel / State — Setup still open + toast | `/onboarding` | [Context inspected](DESKTOP_CURRENT_AUDIT_COVERAGE.md); implementation comparison remains open. | READ |

## Mobile FINAL frames

| Current node | Frame | Production counterpart | Source delta against prior pair map | Status |
| --- | --- | --- | --- | --- |
| `299:11571` | M / Chat | `/chat` | Replaced page/node; populated chat and four-tab footer read. | READ |
| `299:11583` | M / Chat — Drawer open | `/chat` | Replaced page/node; drawer and four-tab footer read. | READ |
| `299:11619` | M / Home | `/home` | Replaced page/node; prior pair absent. | PENDING |
| `299:11692` | M / Chats | `/chat` | Replaced page/node; prior pair absent. | PENDING |
| `299:11879` | M / Chats — Row actions | `/chat` | Replaced page/node; prior pair absent. | PENDING |
| `299:11950` | M / Chat — Approval card | `/chat` | Current pending card compared in isolated package at 393 and 320px. | READ |
| `299:12281` | M / Approval details | `/chat` bottom sheet | Current detail sheet compared in isolated package at 393 and 320px. | READ |
| `299:12336` | M / Memory review | `shared shell / overlay` | Replaced page/node; prior pair absent. | PENDING |
| `299:12372` | M / Model picker | `/chat` bottom sheet | Current bottom sheet compared in isolated package at 393 and 320px. | READ |
| `299:12418` | M / Permission | `/chat` bottom sheet | [Current package comparison](CHAT_PERMISSION_CURRENT_REVISION.md) at 393 and 320px with injected mode choices; live switch remains open. | READ |
| `299:12459` | M / Chat — Tool calls and plan | `/chat` | Three tool rows and compact plan compared in isolated package at 393 and 320px. | READ |
| `299:12494` | M / Chat — Agent error | `/chat` | Current timeout card read and scoped package comparison recorded. | READ |
| `299:12515` | M / Chat — Reconnecting | `/chat` | Current composer notice read and scoped package comparison recorded. | READ |
| `299:12588` | M / Ramble | `/transcription` | Current list compared in isolated package at 393 and 320px. | READ |
| `299:12782` | M / Ramble — Transcript | `/transcription` | Current detail compared in isolated package at 393 and 320px. | READ |
| `299:12871` | M / Ramble — Vetting answers | `/transcription` | Current sheet compared with an isolated engine preview at 393 and 320px. | READ |
| `299:12936` | M / Sign in | `shared shell / overlay` | Replaced page/node; prior pair absent. | PENDING |
| `299:13626` | M / Startup — Starting up | `shared shell / overlay` | Replaced page/node; prior pair absent. | PENDING |
| `299:13662` | M / Startup — Engine stopped | `shared shell / overlay` | Replaced page/node; prior pair absent. | PENDING |
| `299:13686` | M / Projects | `/projects` | Current two-card index compared in an isolated package at 393 and 320px. | READ |
| `299:13910` | M / Work | `/work` | Current three-card empty state compared in an isolated package at 393 and 320px; populated work remains open. | READ |
| `299:14061` | M / Activity | `/activity` | Current populated running row and three cards compared with an isolated engine fixture at 393 and 320px. | READ |
| `299:14218` | M / Permissions | `/autonomy` | Current empty-state cards and dynamic digest compared in an isolated package at 393 and 320px. | READ |
| `299:14371` | M / Knowledge | `/projects/knowledge` | Current populated suggestions and map compared in isolated package at 393 and 320px. | READ |
| `299:14428` | M / Recipes | `/projects/recipes` | [Current list implementation](MOBILE_RECIPES_CURRENT_REVISION.md) uses real engine data and fits 393/320px. | READ |
| `299:14477` | M / Recipes — Preview | `/projects/recipes` | [Current preview implementation](MOBILE_RECIPES_CURRENT_REVISION.md) reads actual steps and fits 393/320px. | READ |
| `299:14544` | M / Scheduled tasks | `/scheduled` | Replaced page/node; prior pair absent. | PENDING |
| `299:14704` | M / Scheduled task — Detail | `/scheduled` | Replaced page/node; prior pair absent. | PENDING |
| `299:14804` | M / New scheduled task | `/scheduled` | Replaced page/node; prior pair absent. | PENDING |
| `300:1703` | M / Providers | `/providers` | Replaced page/node; prior pair absent. | PENDING |
| `300:1902` | M / Providers — Error | `/providers` | Replaced page/node; prior pair absent. | PENDING |
| `300:1936` | M / Diagnostics | `/diagnostics` | Replaced page/node; prior pair absent. | PENDING |
| `300:2113` | M / Settings | `shared shell / overlay` | Replaced page/node; prior pair absent. | PENDING |
| `300:2336` | M / Settings — Appearance | `/settings/appearance` | Replaced page/node; prior pair absent. | PENDING |
| `300:2515` | M / Settings — Model | `/settings/model` | Replaced page/node; prior pair absent. | PENDING |
| `300:2658` | M / Settings — Model — Add model | `/settings/model` | Replaced page/node; prior pair absent. | PENDING |
| `300:2816` | M / Settings — System | `/settings/system` | Replaced page/node; prior pair absent. | PENDING |
| `315:2842` | M / Settings — Tools | `/settings/tools` | Replaces `219:767`; four condensed MCP rows and image-off card confirmed. | READ |
| `315:3148` | M / Settings — WebUI | `/settings/webui` | Replaced page/node; prior pair absent. | PENDING |
| `300:3264` | M / Settings — Desktop Pet | `/settings/pet` | Replaced page/node; prior pair absent. | PENDING |
| `315:3295` | M / Settings — Archived | `/settings/archived` | Replaced page/node; prior pair absent. | PENDING |
| `300:15057` | M / Settings — Assistants | `/settings/assistants` | Replaced page/node; prior pair absent. | PENDING |
| `300:15176` | M / Settings — Skills | `/settings/skills` | Replaced page/node; prior pair absent. | PENDING |
| `300:15296` | M / Settings — About | `/settings/about` | Replaced page/node; prior pair absent. | PENDING |
| `300:15426` | M / Set up Kel | `/onboarding` | Replaced page/node; prior pair absent. | PENDING |
| `300:15565` | M / Connections | `/connections` | Replaced page/node; prior pair absent. | PENDING |
| `300:15641` | M / Connections — Empty | `/connections` | Replaced page/node; prior pair absent. | PENDING |
| `300:15660` | M / Connections — Add a service | `/connections` | Replaced page/node; prior pair absent. | PENDING |
| `300:15698` | M / Connections — Notion | `/connections` | Replaced page/node; prior pair absent. | PENDING |
| `315:3004` | M / Settings — Tools — local-audit-mcp | `/settings/tools` | New populated server detail with status, warning, tools, and actions. | READ |

## Component and token audit

Foundations retains board `139:3`; current direct read confirms `#0B1734` canvas, `#1E4BB0` wash at 10%, `#0F2D64` glass card at 30%, and `#EDF2FA` primary text. These match the older [token mapping](../../FIGMA_TOKENS.md) for these values. Remaining variables, effects, and text styles need a complete value comparison before token parity can be renewed.

Components board `145:10766` and mobile component page `213:3` still resolve. Their top-level component sets include desktop Button, Card, Row, Chat turn, Composer, Toggle, Dropdown, Context menu, Toast, Lightbox, Input states, Tooltip, and mobile bars, Composer, Chat turn, List row, Section header, Card, and Sheet. Top-level IDs alone do not establish unchanged variants. Inspect each relevant child before claiming parity.

**Current implementation locations:** `desktop/packages/desktop/src/renderer/components/settings/SettingsModal/contents/ToolsModalContent.tsx`, `desktop/packages/desktop/src/renderer/pages/settings/ToolsSettings/`, and `desktop/packages/desktop/src/renderer/styles/kel-shell.css` for Tools. Other locations will be added after each source review.

**Next implementation:** finish the current desktop Recipes list, Run, and Preview frames, then the remaining desktop frames. Nick will test the accepted desktop App while mobile work continues. Keep old evidence for history and label it superseded until refreshed.
