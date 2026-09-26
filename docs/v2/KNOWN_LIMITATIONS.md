# KEL V2.0 — KNOWN LIMITATIONS

## Desktop Kibble build variants (2026-09-26)

[Kibble build variants](evidence/figma-full-audit/DESKTOP_KIBBLE_BUILD_VARIANTS_SOURCE.md) now have 1440/800px source checks for Running, Cancelled, and candidate review. Progress uses actual reported state/counts; details remain expandable. Intercepted Approve/Reject handoffs passed; no actual build or installation ran. TypeScript/build, seven focused tests, and the full 63-file/437-test suite passed. Worker execution, mission recovery, and package proof remain open. App/Data remain untouched.

## Desktop Pet and remote sign-in (2026-09-26)

[Desktop Pet off/settings and remote sign-in](evidence/figma-full-audit/DESKTOP_PET_SIGNIN_CURRENT_REVISION.md) pass current 1440/800px source checks. Pet refusal/reload used real isolated IPC and kept Off. Sign-in is 420×330 with 34px fields and viewport-positioned language; input/show-hide/remember/invalid-login handoff passed with intercepted auth. TypeScript/build, 11 policy tests, and the full 62-file/433-test suite passed. Pet enable, real sign-in, measured Light parity, and package proof remain open. App/Data remain untouched.

## Desktop Setup (2026-09-26)

[Desktop Setup](evidence/figma-full-audit/DESKTOP_SETUP_CURRENT_REVISION.md) now uses actual model state, accessible progress, and real folder selection/composer handoff. Isolated model/config writes and 1440/800px source checks passed. The warm setup-return banner passed on Knowledge; Work remains gated until setup finishes. The native picker result was intercepted. TypeScript/build, four focused tests, and 62 files / 433 desktop tests passed. Setup policy selection and broader persistence/parity remain open. App/Data remain untouched.

## Desktop Kibble (2026-09-26)

[Desktop Kibble](evidence/figma-full-audit/DESKTOP_KIBBLE_CURRENT_REVISION.md) now has current 1440/800px source evidence for its panels, finding selection, direct status actions, and screenshot/quote details. Real isolated Mark fixed, Reopen, and selected prompt/Batched writes passed; fixtures were dismissed. TypeScript/source build, 35 focused tests, and the full 61-file/431-test suite passed. Running build/candidate presentation remains open. Canonical App and Data remain untouched; package proof waits for the next larger milestone.

## Runtime and Ramble packaged milestone (2026-09-26)

[Runtime and Ramble milestone package](evidence/figma-full-audit/DESKTOP_RUNTIME_RAMBLE_MILESTONE_PACKAGE.md) at `0b4a583` passed seven packaged probes at 1440/800px, with zero renderer errors or overflow. All 265 renderer files match the archive. Real isolated restart, sanitized export, Merge, and Vetting preview passed; injected/intercepted limits are recorded. Canonical App stays `8c67121`; Data remains untouched. Desktop implementation and acceptance remain partial.

## Desktop Ramble and complete frame inspection (2026-09-26)

[Desktop Ramble](evidence/figma-full-audit/DESKTOP_RAMBLE_CURRENT_REVISION.md) now has current 1440/800px source evidence for its transcript, connected-key replacement input, Merge list, and Vetting modal. Real isolated merge and preview rechecks passed; new recordings were cleaned up and the saved vetting transcript remained unchanged. TypeScript/source build, 35 runtime transcription tests, four transcription-policy tests, four Ramble DOM tests, and the final 60-file/428-test desktop suite passed. [Desktop Figma context inspection](evidence/figma-full-audit/DESKTOP_CURRENT_AUDIT_COVERAGE.md) covers 75/75 current frames; this is not accepted parity. Canonical App stays 8c67121, Data is untouched, and mobile stays paused.


## Desktop shared dialogs (2026-09-26)

[Desktop Update available and task delete confirmation](evidence/figma-full-audit/DESKTOP_SHARED_DIALOGS_SOURCE.md) pass source checks at 1440/800px. Update uses actual versions/release notes and existing download authority. Delete now uses the Figma modal; Keep/Escape and intercepted deletion handoff passed. TypeScript, source build, and three update-policy tests passed. Stopped-engine inner surface styling was corrected and rechecked. These changes await the next larger package. Canonical App and Data remain untouched. Current desktop context coverage is 66 READ / 9 PENDING; READ does not mean complete parity.


## Desktop milestone and runtime views (2026-09-26)

[Combined desktop milestone](evidence/figma-full-audit/DESKTOP_COMPLETION_MILESTONE_PACKAGE.md) passed packaged 1440/800px checks at `f8e6d86`: Work, Permissions, Knowledge, saved recipes, and chat menus. [Starting, stopped engine, and diagnostics export](evidence/figma-full-audit/DESKTOP_RUNTIME_VIEWS_SOURCE.md) now pass source checks at both widths. Real isolated restart and sanitized local export passed. TypeScript, source build, 17 runtime diagnostics tests, and the final 60-file/427-test desktop suite passed. These latest runtime views await the next larger package. Canonical App remains `8c67121`; durable Data was untouched.


## Desktop Knowledge (2026-09-26)

[Desktop Knowledge and project recipes](evidence/figma-full-audit/DESKTOP_KNOWLEDGE_CURRENT_REVISION.md) now have 1440/800px source evidence. Proposal labels/order, row icons, card rhythm, map columns, saved-record scrolling, valid memory actions, and saved recipe links are implemented. Real isolated-engine mutations passed. TypeScript, ten focused Work/recipe tests, and 60 files / 427 desktop tests pass. The later combined milestone package passed; App and Data remain unchanged.

## Desktop Work and Permissions (2026-09-26)

[Active/waiting Work and populated Permissions](evidence/figma-full-audit/DESKTOP_WORK_PERMISSIONS_STATES.md) pass real isolated-engine checks at 1440/800px. Job selection, current step, continuation instructions, wrapping, and scrolling are repaired. Answer request, Allow once, and Revoke passed through real engine routes. Auto Edit and Add a file labels match live Figma. TypeScript, source build, 19 Work/attention tests, and four menu DOM tests passed. App and Data were untouched. The later combined milestone package passed.

Populated Figma frames are absent; existing components define their layout. Pause/Cancel were inspected, not clicked. Revoked lease history remains visible. Saved Knowledge and project recipe checks have since passed. Other desktop frames remain open. The mistakenly generated root-level packages/ renderer cache remains after policy blocked removal. Earlier empty-fixture and label limitations below are historical.

[Populated desktop layout](evidence/figma-full-audit/DESKTOP_POPULATED_LAYOUT_SOURCE.md) has source proof for canceled Work jobs and project proposals/map sections. Current Figma supplies empty Work/Permissions/Projects frames, so no exact populated-frame match is claimed. The isolated host has no active permission leases, boundary requests, saved knowledge records, or scheduled tasks. Those states and live Work actions remain open. The combined package check is pending.

[Desktop chat menus](evidence/figma-full-audit/DESKTOP_CHAT_MENUS_CURRENT_REVISION.md) have source render proof, with package proof deferred to the larger desktop milestone. Permission used an injected five-option catalog. Its supplied Auto Edit label now matches Figma. The actual slash catalog only exposes `/open`, whose description now matches Add a file. Attach retains actual Skills/MCP controls, making it taller than Figma's two-row example. Memory decisions and native file selection were intercepted; no live provider capability or user-memory mutation is claimed.

[Desktop Activity loading and Providers error](evidence/figma-full-audit/DESKTOP_PENDING_STATES_CURRENT_REVISION.md) have package evidence at 1440/800px. Holds and failures were injected through the isolated desktop bridge; no live outage is claimed. Diagnostics contain actual isolated engine details rather than Figma's sample PID/heartbeat. Canonical App remains `8c67121`; desktop completion still gates its promotion.

Workspace and File preview retain native window controls, actual roots/sort, syntax highlighting, and truthful file attribution. Their final desktop package checks pass. The existing editor normalizes CRLF saves to LF; the check restored original bytes. Fixture deletion was rejected by automatic approval review as blocked by policy. Its synthetic files remain inside the existing temporary audit stack. OS launches and folder reveal were intercepted; Add folder was canceled through an injected native dialog result. These are bridge checks, not physical OS acceptance.

[Desktop pickers](evidence/figma-full-audit/DESKTOP_PICKERS_CURRENT_REVISION.md) have isolated 1440/800px package evidence. The engine catalog makes Model taller than Figma's sample. The no-accent-rail rule replaces the scope underline with warm text and subtle full fill. Folder browse used an injected OS-dialog result, not physical acceptance. No live model response was requested. Workspace and File preview now have final package checks. Installed App still packages `8c67121`.

[Desktop Fix Capture](evidence/figma-full-audit/DESKTOP_FIX_CAPTURE_CURRENT_REVISION.md) has isolated 1440/800px package evidence. Audio and transcription were synthetic; real microphone/Muse acceptance remains open. The real screenshot capture/discard path ran only against isolated data. No fix was saved. The palette focus-ring repair and asynchronous search refresh now have package proof. Installed App remains on `8c67121`.

[Desktop command palette and chat overlays](evidence/figma-full-audit/DESKTOP_CHAT_OVERLAYS_CURRENT_REVISION.md) have isolated 1440/800px package evidence. Chat Export's content/download handoff passed an intercepted renderer probe; native save-dialog completion remains untested. Rename was opened and canceled. The final palette-input focus-ring repair now has package proof from the Fix Capture batch. Installed App remains on `8c67121`.

[Desktop new task and approval details](evidence/figma-full-audit/DESKTOP_OVERLAYS_CURRENT_REVISION.md) match the current overlay bounds at 1440px and fit 800px. The new-task capture used unsaved sample inputs, and no task ran. The approval was a pending isolated engine record; no decision was submitted. Action approvals do not supply the specific purpose and reason pictured in Figma. The dialog uses truthful generic explanations until the engine can provide specific ones. Mobile layout was not audited in this desktop batch. Canonical App still packages `8c67121`.

[Desktop Archived](evidence/figma-full-audit/DESKTOP_ARCHIVED_CURRENT_REVISION.md) has populated and selected package captures from an intercepted synthetic sidebar response. Real archive mutation was not performed. The backend may omit `archived_at`; those rows correctly show a Created time. [Enabled WebUI](evidence/figma-full-audit/DESKTOP_WEBUI_CURRENT_REVISION.md) was started and stopped with isolated data. The real QR rendered, but phone sign-in and successful credential changes remain untested. Its one-time token was not committed. Canonical App still packages `8c67121`.

[Desktop System, Restore, and About](evidence/figma-full-audit/DESKTOP_SYSTEM_ABOUT_CURRENT_REVISION.md) match current Figma structure and measured 1440px card/dialog bounds. The isolated 800px data path wraps, making its System card taller. The backup summary came from disposable data; the restore was canceled. System switches, timeouts, version, and runtime display actual settings and package values, which differ from Figma's sample. The canonical App still packages `8c67121`.

[Desktop Appearance](evidence/figma-full-audit/DESKTOP_APPEARANCE_CURRENT_REVISION.md) now follows the current Theme, colors, text/zoom, and Add theme structure at 1440 and 800px. The tested Midnight theme had no custom CSS or color override, so its preview and values differ from Figma's illustrative edited theme. More colors and font Reset controls remain accessible. The Add theme dialog is 14px shorter than the scaled Figma sample. Canonical App still packages `8c67121`.

[Desktop Assistants and Skills](evidence/figma-full-audit/DESKTOP_CATALOG_CURRENT_REVISION.md) have current Figma headings and row layouts. The isolated package contained one real assistant and no custom skills. It therefore cannot prove a three-row populated Skills state. Kel retains its actual stored description instead of Figma's sample copy. The canonical installed App still packages `8c67121`.

## Desktop Work and scheduled task detail (2026-09-25)

[Work empty](evidence/figma-full-audit/DESKTOP_WORK_CURRENT_REVISION.md) matches Figma's three card bounds at 1440 and 800px. Populated Work and its actions remain open. [Scheduled tasks list](evidence/figma-full-audit/DESKTOP_SCHEDULED_LIST_CURRENT_REVISION.md) uses real saved execution modes, so it does not show Figma's illustrative “Queue” as an execution mode. Its setting controls open the edit dialog rather than an inline menu. [Scheduled task detail](evidence/figma-full-audit/DESKTOP_SCHEDULED_TASK_DETAIL_CURRENT_REVISION.md) matches the Details card dimensions and has tested controls. History rows were synthetic, not real runs. The scheduler has no project label or per-run outcome record, so the screen shows a dash for Project and only displays the latest task status on the latest run. The canonical installed App still packages `8c67121`.
[Desktop Activity](evidence/figma-full-audit/DESKTOP_ACTIVITY_CURRENT_REVISION.md) now has an isolated running-job package check. No model worker executed, and waiting and finished outcomes remain open. The final separator-space CSS correction was packaged later but the running row was not recaptured. [Desktop Permissions](evidence/figma-full-audit/DESKTOP_PERMISSIONS_CURRENT_REVISION.md) covers empty cards only; populated grants, requests, and Run check remain open.
[Desktop Projects](evidence/figma-full-audit/DESKTOP_PROJECTS_CURRENT_REVISION.md) now matches the empty three-card geometry. Populated knowledge, map sections, and recipes remain open. [Desktop Providers](evidence/figma-full-audit/DESKTOP_PROVIDERS_CURRENT_REVISION.md) has real catalog rows and three honest readiness rows; the default model has not answered a live test. [Desktop Model](evidence/figma-full-audit/DESKTOP_MODEL_CURRENT_REVISION.md) has Figma-style default and populated custom-model rows, real actions, and a compact Add model dialog. The isolated key was fake and its loopback health check failed. A successful real provider check remains open. [Desktop Diagnostics](evidence/figma-full-audit/DESKTOP_DIAGNOSTICS_CURRENT_REVISION.md) has live health and performance values. Clear caches and Restart runtime remain disabled because the existing operations do not match their stated behavior. The canonical installed App still packages `8c67121`.

## Desktop Home and Connections (2026-09-25)

[Home](evidence/figma-full-audit/DESKTOP_HOME_CURRENT_REVISION.md) matches the current heading, card, and composer geometry at 1440px. Its isolated state has one provider setup need; Figma's two work updates were not fabricated. [Connections](evidence/figma-full-audit/DESKTOP_CONNECTIONS_CURRENT_REVISION.md) now has packaged empty and populated Services states and an inline credential editor. The populated card measures 670×244 at 1440px; Figma shows about 670×240. The credential card remains taller than Figma because Kel keeps service options and a secure-storage note visible. The Add form has extra options. The current engine catalogs read actions only, so Figma's mutating Linear issue confirmation has a DOM test but no packaged visual proof. A final 800px action-label CSS repair also awaits package proof. No live credential or service call was used. The canonical installed App still packages `8c67121`.

## Desktop Recipes (2026-09-25)

The [desktop Recipes implementation](evidence/figma-full-audit/DESKTOP_RECIPES_CURRENT_REVISION.md) uses five real engine built-ins instead of Figma's sample names. The isolated engine has no saved runs, so the Preview history shown in Figma is absent. The Run form uses actual engine inputs, and no recipe was submitted. The package reproduces the current inner card geometry at 1440px and fits 800px. The canonical installed App still packages `8c67121`; this desktop increment remains source-only until the desktop completion install.

## Latest Figma revision (2026-09-25)

The [current mobile Chat Permission sheet](evidence/figma-full-audit/CHAT_PERMISSION_CURRENT_REVISION.md) matches the frame bounds and option geometry at 393px and fits 320px. Its isolated ACP session did not return a mode catalog; session-gated sample options verified presentation only. A live mode switch and provider support remain unverified. The Windows titlebar and font rendering differ from the phone frame.

The [current mobile Permissions empty state](evidence/figma-full-audit/PERMISSIONS_CURRENT_REVISION.md) matches all three card bounds at 393px and fits 320px. Its digest comes from isolated engine data and opens the real check controls. Populated grants and access requests remain unverified. Windows phone chrome and font rendering differ. Earlier five-tab captures are superseded by the [four-tab package](evidence/figma-full-audit/MOBILE_NAV_CURRENT_REVISION.md).

The [current mobile Knowledge check](evidence/figma-full-audit/KNOWLEDGE_CURRENT_REVISION.md) uses two bounded engine proposals and five map sections. Its first card starts at the current Figma bounds, and defer/refresh worked. Figma pictures three sample map rows; the package keeps all five real sections. Accept and Reject were not submitted. Windows font and phone chrome still differ.

The live desktop and mobile FINAL pages were replaced. The old 23 desktop / 28 mobile pair audit is **SUPERSEDED BY FIGMA REVISION**. Current Figma has 75 desktop and 50 mobile frames. The current Tools layout, mobile failure detail, and JSON, CLI, report, and delete dialogs have a [scoped disposable package check](evidence/figma-full-audit/TOOLS_CURRENT_REVISION.md). The installed App still packages `8c67121`. Product-wide parity, current component variants, real CLI import and report delivery, the sign-in-needed Tools row, and populated mobile tools remain open. Nick's four-tab Kibble placement is [packaged and tested](evidence/figma-full-audit/MOBILE_NAV_CURRENT_REVISION.md). Do not use the older Tools captures below as evidence for the new frames.

The [mobile Ramble list/detail check](evidence/figma-full-audit/RAMBLE_MOBILE_CURRENT_REVISION.md) matched the current 393px geometry and kept controls inside 320px. An [isolated vetting preview](evidence/figma-full-audit/RAMBLE_VETTING_CURRENT_REVISION.md) also matched sheet bounds, but Accept all and Process batch were not submitted. Real audio remains unverified. Folder rename/delete icons remain visible beyond the sample frame so those actions stay reachable. Five synthetic recordings differ from the four pictured. Windows font rasterization, native titlebar, and the unresolved fifth Kibble tab prevent exact mobile pixel parity.

The [current mobile Projects index](evidence/figma-full-audit/PROJECTS_CURRENT_REVISION.md) matches the two-card layout and routes without overflow. With several projects, its heading remains generic because the current Work and Knowledge routes do not accept a selected project scope. The index does not claim project-specific data behavior. A project selector and scoped routes remain open.

The [current mobile Work empty state](evidence/figma-full-audit/WORK_CURRENT_REVISION.md) matches the three card bounds and current labels at 393 and 320px. A populated job was not run in this package. Windows font and titlebar still differ from the phone frame. The isolated card pixels differ slightly despite using Figma's CSS fill and border values.

The [current mobile Activity running state](evidence/figma-full-audit/ACTIVITY_CURRENT_REVISION.md) uses a synthetic engine claim, not a live model worker. It matches the three current card bounds and fixes the incorrect “Waiting on you” entry for a RUNNING job. Other Activity states, project scope, and phone chrome remain open. Its five-tab capture predates the [four-tab update](evidence/figma-full-audit/MOBILE_NAV_CURRENT_REVISION.md).

The [current Chat package check](evidence/figma-full-audit/CHAT_CURRENT_REVISION.md) repaired the mobile two-line user turn, four reply actions, composer height, and drawer layout. Its synthetic conversation has no real project metrics or agent plan. The Windows title bar differs from Figma's iPhone status/home chrome. Attachment and mic controls remain visible in the mobile composer. The older fifth Kibble tab is superseded by the [four-tab update](evidence/figma-full-audit/MOBILE_NAV_CURRENT_REVISION.md). Desktop Chat and mobile drawer screenshots are scoped comparison evidence, not full Chat parity.

The [current populated Transcriptions check](evidence/figma-full-audit/TRANSCRIPTIONS_CURRENT_REVISION.md) uses synthetic text and one-second local WAV files. It confirms the panel, actions, and 800px scroll path, but it does not prove live Muse transcription, a real download, clipboard write, or a merge. Windows font rendering and dynamic transcript line breaks still prevent a claim of exact pixel parity for a real recording.

The [current approval package check](evidence/figma-full-audit/CHAT_APPROVAL_CURRENT_REVISION.md) covers pending and settled visual states with isolated engine records. The separate [mobile approval-details check](evidence/figma-full-audit/CHAT_APPROVAL_DETAILS_CURRENT_REVISION.md) matches the current sheet frame. Neither proves a packaged approval decision or the expired state. The [tool-call and plan check](evidence/figma-full-audit/CHAT_TOOL_PLAN_CURRENT_REVISION.md) uses synthetic ACP rows and a test-only processing state; it does not prove a live model tool run. The [Chat error check](evidence/figma-full-audit/CHAT_AGENT_ERROR_CURRENT_REVISION.md) uses a synthetic timeout. It does not prove a live provider timeout, a retry, or the illustrative fallback toast. The [mobile model picker](evidence/figma-full-audit/CHAT_MODEL_PICKER_CURRENT_REVISION.md) matches the sheet geometry and supports an isolated per-chat choice; its labels depend on real configuration, and default-choice persistence was not exercised. The [reconnecting check](evidence/figma-full-audit/CHAT_RECONNECTING_CURRENT_REVISION.md) injected a renderer state. It does not prove a real engine outage, restart, or queued-message delivery. The desktop Project metrics footer remains absent in its scoped ACP fixture.

## Current canonical limits (2026-09-24)

The older r29 limits below are historical. The canonical app and durable data paths are in `docs/CONSOLIDATION_STATUS.md`. r61 System and r62 Appearance have scoped packaged evidence. Exact Figma parity remains open, including Tools status and interactive states, populated and enabled states, Light labels, and real phone rendering. Live Google sign-in, personal services, remote first response, fresh Muse speech, and a physical iPhone remain unverified.

The V2-18 cancelled Build Update reading and no-job `DISPATCHED` defect described later in this file were fixed in source during this continuation. Older stored submissions may still carry `DISPATCHED` with no job. The canonical App includes these fixes at package source `8c67121`.

The canonical App's Tools failure and enabled Image Model states ran on disposable data at 1440 and 800px. The status detail now has Components `156:159` ice-glass material. Its long diagnostic still covers the Tools heading and card title while open at 800px. The short Figma tooltip does not specify this longer runtime content. The Image Model field and menu match the measured Components `146:52` material, and the enabled switch persisted after reload. A fake key and loopback endpoint verified only local configuration. No real image generation, live MCP, or personal credential was used. Keyboard and assistive-technology checks remain open.

WebUI was enabled in an isolated packaged App. Its local page loaded and its API required login. This does not prove remote access, authenticated phone use, or a model response. The available FINAL frame shows step 1; step-2 pixel parity is not claimed.

The installed App still refuses Desktop Pet enable. The switch returns off, shows a clear refusal, and stays off after reload. `petPolicy.ts` sets `KEL_PET_SUBSYSTEM_ENABLED = false` under V1.6 finding AUD-MINOR-008. Enabling it requires a product and safety decision; changing a Figma control alone cannot verify the enabled state.

## Current r29 acceptance limits (2026-09-23)

Packaged local conversation opening, two disposable project contexts, Dark widths, and two native picker adjustments are verified in `docs/v2/evidence/v2-19/CANDIDATE_R29.md`. Remote load, first response, Google sign-in, and live personal services need a signed-in isolated candidate session and a model request. Fresh Muse audio needs a new recording; physical iPhone checks need the device. The web-host suite requires stopping all Kel instances, which is excluded while r20 runs. V2-20 promotion remains gated. Faint Light-mode labels remain outside this Dark pass.

Honest, current limits at the V2 base — things a later run must not pretend are solved. Phase-specific
limits are appended as phases land.

## Inherited from the predecessor line (still true)

- **Verification audio is synthetic where a person would speak.** The Muse verification runs fed Windows
  TTS WAVs into the capture path (`--use-fake-device-for-media-stream` + `--use-file-for-fake-audio-capture`);
  the real-device run shows the app opening the actual microphone with no error, but the room is silent
  (peak ≈ 0.001) because nobody can speak during an automated run.
- **The shared meta credential is Windows-only.** `shared_muse_key()` reads Windows Credential Manager,
  so on another platform transcription reports `unavailable` unless a key is supplied through the
  environment or Kel's own setting.
- **Muse realtime endpointing returns the utterances it closed before Stop**, so a long phrase can arrive
  in parts ("…verification orange"; "…blue baseball 83" for "eighty-three"). That is ASR behaviour, not
  Kel copy.
- **Screenshots can contain whatever was on screen.** Fix Capture captures only Kel's own window, keeps
  everything local, and never uploads or sends them to a model during capture — but a screenshot is a
  screenshot, and they travel only inside a prompt Nick deliberately prepares.
- **Remote work needs the desktop awake.** Away-from-desktop use today depends on Nick's desktop Kel
  running; cloud Kel is V2.5 by decision, and mobile V2 deliberately has no uploads, camera, share sheet
  or push notifications.
- **The older Daily Driver / Fix Capture limits** (provider-id naming, cancellation hygiene, hotkey
  conflict resolution, and the rest) are recorded in `docs/daily-driver/KNOWN_LIMITATIONS.md` and remain
  accurate for this line.

## V2-specific unknowns and risks (to be resolved by their phases)

- **The assistant cannot use a connection yet.** V2-01 … V2-04 built the
  model, the central surface, Test Connection and the eight services as data. The framework's actions
  (rows, `run()`, the confirmation gate and the access history) are built too, but the bridge that would
  let a conversation call one is not — the
  assistant's tools come from the coding runtime the desktop agent runs, so that is deliberate work, with
  the same one-request rule and the mutating confirmation. No Connections capability switch is offered
  until it exists. None of the services' real credentials exist on this
  machine except the Muse one, and **no real service has been contacted**: every check ran against a
  local stand-in service on the loopback interface.
- **The eight services are known by address and shape, not proven.** GitHub, Stripe, Figma, ClickUp,
  Discord and Google Drive use the endpoints their own documentation publishes; Pitcher List is an
  assumption (the standard WordPress layout) and Raptive's API address is unknown to Kel until Nick
  pastes the one Raptive issues. Nothing here has been run against the real service.
- **Google Drive cannot be checked beyond a pasted token.** There is no OAuth account sign-in step yet, so
  the token has to be supplied by hand; the catalogue entry says so rather than pretending otherwise.
- **The Connections surface has not been verified in an installed app.** It is covered in jsdom through
  the shipped page components and the real bridge contract, and the connection credential namespace has
  its own tests, but no installed Kel has had its Test connection button clicked, and OS-level encryption
  of a connection credential (as opposed to the V1.4 provider credentials that store already proves) is
  untested on a real DPAPI-backed install.
- **The framework's retries are proven against a local stand-in only** — a scripted 503-then-200 service,
  never a real rate limit from a real API.
- **No mobile hardware in this environment.** iPhone PWA verification will be synthetic (the PWA driven
  in a desktop browser over the web-host gateway) plus the installed-app tether check; real-device
  behaviour (iOS Safari, add-to-home-screen, backgrounding) can only be confirmed by Nick.
- **Isolation and network rules will be verified locally and synthetically** (path probes, process-tree
  kills, blocked-domain attempts) rather than by hostile scenarios.
- **Upgrade reliability must be proven without touching the dogfood install.** V2 upgrade tests use V2
  data roots and the V2 candidate only; the protected dogfood pair is never the subject.

## V2-05 — what a phone still cannot do (measured, not assumed)

1. **Voice → Muse is not wired from the browser.** The phone records (timer, Cancel, Stop all work) but
   stopping sends no `/api/transcription` request and produces no transcript. Desktop voice was repaired
   and verified in the Daily Driver line; the browser path is still unconnected.
2. **Sending needs a connected model.** With none connected the composer's send stays disabled (proved
   with both paste-shaped input and real key presses) and Kel says so plainly ("so Kel will wait instead
   of guessing" + Open Providers). Connecting one is reachable from the phone (4 providers · 2 usable),
   but no model turn was spent in this increment, so send-then-continue was not exercised end to end.
3. **Attention actions were exercised only for the kind of attention this instance actually had** — a
   connection needing setup, which opens Providers from the phone. Approval, deny, grant, resume, stop and
   review attach to job state that did not exist here.
4. **The phone's drawer was not opened by the automation.** A conversation seeded through the engine's own
   `/api/send` is authoritative and visible through `/api/state`, but the history entry was never reached
   on the phone. The collapsed rail visible at 393px is inert by design (`x=-11`, `pointer-events: none`)
   — the drawer, not the rail, is the phone's navigation.

### V2-05 voice — where the browser path actually breaks (diagnosed)

`KelMicButton.start()` starts capture, then calls `/api/transcription`
`{action:'stream_start'}` — but that call sits in a `try { … } catch { liveRef.current = false;
sessionRef.current = null }`. Every failure is swallowed: the phone shows a running recording timer and
then nothing, with no transcript and no message. In the measured run **no `/api/transcription` request
reached the gateway at all** (0 hits in the gateway log, HTTP or otherwise), so the browser's transport
for that route is the thing to connect — the engine and the gateway were both healthy at the time.
Required by V2-05 itself: when the microphone path cannot reach transcription, the phone must say so
truthfully instead of silently recording. Next run: find the browser transport for `/api/transcription`,
fix or wire it, replace the silent catch with a plain sentence, then verify against Muse.

### V2-05 voice — fixed (desktop bridge requirement removed)

The browser voice path now uses the shared Kel transport, so a phone reaches Muse through the gateway.
Verified end to end in a real browser: `stream_start` → 27 `stream_chunk` → `stream_finish`, Muse's
transcript in the composer, no practice text. The engine's 24 kHz mono PCM16 expectation is now recorded
in the evidence README (a fixture at any other rate is refused by Muse itself).

Still open after this pass, in `RESUME.md` order: send with a connected model (the phone can reach
Providers and Connections but no model was selected), conversation history from the phone's drawer,
job-driven attention actions, conversational project routing, and multi-utterance dictation (the
first utterance's partial is lost when Muse never marks it final).

### V2-05 — the "Work & context" panel is not reachable at phone width (measured)

The panel that holds Kel's conversation history, the attention-first work list and the conversation
selector is opened by the rail's footer trigger (`KelWorkPanel.tsx`, class `kel-work-context-btn`). At
393×852 that trigger sits in the collapsed rail — off-canvas and inert, exactly like the rail's named
entries — so clicking it times out and the panel never opens. Journey B records it
(`drawer-failed`, then the unchanged home text). Consequence: the phone cannot reach conversation
history, the conversation selector or the attention-first work list in this build; the phone's own
entry point for that panel (if one exists) was not identified in this increment. This is a real V2-05
gap, not a spec artifact: the trigger exists, resolves, and cannot be tapped.

### V2-05 — why the phone's composer cannot send: no assistant is selected (found, not guessed)

`useGuidSend.ts` gates the send button on `loading || !selectedAssistantId` — an *assistant* (the shell's
agent) must be chosen, and in a fresh web profile nothing is. The assistants exist and are reachable:
`GET /api/assistants` through the gateway answers with real entries (`bare:632f31d2` "Aion CLI", an
`aionrs` agent, plus the CLI-backed ones), and the Providers page already reports Claude Code and Codex
CLI as "Ready to use". What has not been done yet is choosing one **from the phone**: the assistant
selection area is where a desktop picks it, and this increment did not establish the phone's affordance
for it. Next run: select an assistant on the phone (or verify the shell persists a desktop pick into the
profile the phone uses), then prove type → send → model reply → continued context, with no model turn
spent until the send actually goes through.

### V2-05 — the phone shows no assistant to choose (measured, so send stays blocked)

`AssistantSelectionArea` renders its pills only when there are enabled assistants for the current view,
and returns nothing at all when there are none. Journey H measured the phone's home surface: **zero**
elements with `data-assistant-id` and **zero** `assistant-more-btn`, while the shell's own
`GET /api/assistants` answers with enabled entries. So a fresh phone profile has nothing to tap: the
composer's send stays disabled by `useGuidSend`'s gate and no model turn can be started from the phone
until either a desktop pick is persisted into the profile the phone uses, or the assistant area renders
at phone width. Journey H records the measurement (`findings-H.json`); nothing was faked and no model
turn was spent.

### V2-05 — where the phone's assistant choice most likely lives (source-backed next step)

`GuidActionRow` keeps the inline model/permission selectors only on desktop — `{!isMobile && configOptionCount > 0 && …}` —
and on mobile moves them into `MobileActionSheet` (`sheetEntries`). `AssistantSelectionArea`'s own pills are
therefore expected inside that sheet on a phone, which is why Journey H found none in the page body. The
selection hook itself already falls back to a default (`useGuidAssistantSelection`: saved key → generated
aionrs → any aionrs → first enabled), so the open question is only whether the sheet renders the choices
at phone width. Next run: type into the composer, open the action sheet (the composer's overflow control),
confirm the assistant entries appear there, choose one, and then prove type → send → model reply →
continued context. No model turn spent so far.

### V2-05 send — fixed (the profile had no assistant; the standalone host now seeds it)

The `kel` assistant is seeded by the Electron main process, so the standalone `bun run webui` profile the
phone uses had none — the guid page's catalog (filtered to `kel` by the shell) was empty, and no model
turn could start from the phone. `bun run webui` now performs the same integration the desktop does
(register the Kel ACP agent in module form, create the single `kel` assistant, leave exactly it enabled),
and Journey H proves the live round trip including a second turn. The desktop's source-mode agent spec
got the same module-form fix; its packed engine never hit the script-path failure.

Still open after this pass, in `RESUME.md` order: conversation history from the phone (the drawer and a
blank-body deep link — below), job-driven attention actions, conversational project routing.

### V2-05 — measured notes for the history increment (do not re-derive)

- **A `/conversation/<id>` deep load renders a blank body on the phone** (one authed probe, 9s wait;
  `body.innerText` length 0). The shell's own comment says a full-page load of a Kel route "lands back
  on the home"; measured, this route lands on nothing. Verify with the drawer/history work and fix or
  document per outcome.
- **Tapping the home's recent entry text ("Phone send check…") timed out once** (8s, actionability) —
  likely a tap-target/selector detail; try the drawer path first in the history increment.
- **Assistant replies render inside a shadow root** (`ShadowView` portals the markdown); `innerText`
  cannot see them. Journeys must read `.markdown-shadow-body` text explicitly — a reply bubble reading
  as empty text is a detector problem, not a reply problem.
- **The conversation's send control can read as `disabled` while it still accepts the next send**
  (measured: `sendEnabled false` immediately before a second turn that landed). Treat its disabled state
  as advisory; the click's own actionability is the gate.
- **`bun run resetpass`'s fast path 401s when the webui is running** (its reset goes through the
  session-gated proxy). Workarounds: direct loopback POST to `/api/webui/reset-password` on the backend
  port, or stop the webui and use the documented slow path. Operator note, not a phone defect.

## V2-04a — the bridge's honest limits (measured 2026-09-21)

- **The phone cannot reach a work turn yet.** A phone conversation turn is answered by the engine's
  conversational path (measured: a 4.8 s "saved context" reply, no job and no runtime for a turn that
  asked for a connected-service call). Work turns need a selected project (the Shell's Work surface —
  Astra's territory) or a work-verb route; until that lands, the bridge is reachable from the phone
  only through chat's controls, not through a runtime. Journey J is held for that integration.
- **Claude Code was quota-blocked on this machine** ("session limit · resets 3:50pm"); its runtime
  attempts fail instantly ("Native Claude did not finish") and the engine falls back to codex-code,
  which carried the live journey. The bridge is runtime-agnostic (a plain shell command), but the
  claude path was not exercisable today.
- **A live job can close UNCERTAIN while the bridge worked**: the codex attempt produced the change
  and reported its smoke command passing, but the milestone's full verification path shared the same
  quota, so the job closed with the honest "could not fully verify" message. The bridge evidence
  (event + bounded result + written login) stands independently.
- **The standalone webui/phone profile has no credential custody** (no shell pushes values); its
  `catalog` says so per connection in plain words, and calls refuse honestly instead of guessing.

## V2-04b — the sign-in's honest limits (measured 2026-09-21)

- **Real Google OAuth was not exercised.** The whole framework is proved against a local stand-in
  provider (real HTTP, real S256 PKCE, real callback); a real Google sign-in needs Nick's own OAuth
  client ID stored for the connection and a browser visit — that step is his to take.
- **The phone cannot finish a sign-in yet.** The callback lands on the engine's own loopback, which a
  remote browser cannot reach; the desktop (or a local browser) is the place sign-ins complete. The
  Shell work may revisit this; nothing is claimed for the phone line.
- **A sign-in that finishes while nobody claims it lives in engine memory only** — if the engine
  restarts between the callback and the shell's claim, the sign-in must be repeated (the connection
  then reads `needs_reconnect`/`disconnected`, never a stale success).
- **A pasted token still works exactly as before** for `kind: 'oauth'` connections that were never
  signed in — the framework adds the sign-in; it does not remove the manual path.

## V2-04 hardening — what is not yet a rule (2026-09-21)

- **No network rules are configured yet.** `NETWORK_RULES` (in `kel.connections`) is the seam V2-14
  will fill; with it `None`, every host is allowed exactly as before. The seam itself is tested
  (refusal before send; fail-closed when the rule source errors) — the *modes* (no internet /
  approved domains / full internet, per-tool and per-Project rules) are V2-14's work.
- **The redirect bound is three hops** (`MAX_REDIRECTS`) and the imposed pause is capped at five
  seconds (`RETRY_AFTER_CAP`); both are framework constants, not per-connection settings yet.

## V2-09 — routing intelligence: the honest edges (2026-09-21)

- **Latency is an observation, not a stopwatch.** `ms` is the span between a run’s first and last
  native event, so a run that left no events records `NULL` instead of a guess.
- **No cost source is wired yet**, so the `cost` column is present but stays `NULL`; routing still
  uses the provider state row’s own cost figure, exactly as before.
- **The window and half-life are framework constants** (30 days, 7 days), not per-connection or
  per-project settings.
- **Evidence can only reorder eligible models.** A provider whose circuit is open or whose quota is
  exhausted is still refused by the pre-existing hard filters; evidence never re-admits it.
- **Routing evidence is per run/milestone, not per project or conversation** — there is no per-project
  evidence model yet, and the preference (which *is* per conversation/default) stays a preference.
- **The phone still needs the Shell’s Work route** to *show* a job it created: this increment makes the
  tool-shaped turn become real work at the engine, and the plain-probe proof above is the engine’s;
  the presentation of that work on the phone is the Shell lane’s.

## V2-10 — learning 2.0: the honest edges (2026-09-21)

- **A correction suggestion carries the count, not the wording.** “You corrected this N times” is
  proposed as a new convention record the person accepts; it never rewrites the memory it counted.
- **Connection usage is engine-wide.** `connection_events` carry no project link, so a connection
  suggestion appears in whichever project is reviewing — its evidence says `scope: engine`.
- **Thresholds are constants** (`SUGGEST_MIN_EVIDENCE = 3`, 30-day window), not per-project settings.
- **The shadow flag still gates automatic workforce writes** (`workforce.learning.shadow`, default
  off). The person-side actions (list / explain / off / on / suggest) are never gated — they write
  nothing on their own, and a suggestion still needs an accept to become a belief.
- **Nothing suggests authority at all**: there is no learning type for permissions, spending, file
  access or irreversible actions, and the fence refuses the text even before a type is chosen.

## V2-11 — long-running work 2.0: the honest edges (2026-09-21)

- **Runtime recovery needs the engine running.** The fence runs on `Engine.tick`; a killed engine's
  abandoned runs are fenced on the next tick after a restart (or by the deliberate CLI
  `python -m kel recover`, which still fences every expired lease).
- **The lease is the clock.** A run is "abandoned" when its lease expired — 190 s for conversational
  work, 420 s for coding. A run executing in this engine is excluded even if the lease lapsed
  mid-run, so long work is never fenced out from under itself.
- **An expired *approval* is not yet its own state.** A pending approval past its TTL stays
  `AWAITING_USER` until it is resolved; the Work brief reports it as waiting on the request card. A
  dedicated "approval expired" transition is not built.
- **The Work brief is per conversation/project** — `_work(cid)` reads the jobs of that conversation,
  with closed jobs shown only for the last 24 h (at most three).
- **No progress percentages.** The brief reports facts (milestones accepted, open states, the fence
  error, the last event time), never an invented completion estimate.

## V2-12 — adaptive staffing: the honest edges (2026-09-21)

- **History is tier-level, not feature-level.** Comparability means “same decided tier” — the stored
  record keeps the decision, not the full feature vector, so the advice reads missions like the one
  in front of it only at that granularity.
- **One step, never a ladder.** The advice moves at most one tier and never more; D3/D4 remain
  returned-but-unsupported by the existing D1/D2 paths (they are recorded, not routed).
- **No automatic escalation into pods.** A raise is recorded as advice on the staffing event; no path
  auto-switches from `run_d1` to `run_d2` on advice alone.
- **The advice horizon is the whole recorded stream** (settled missions with a decided tier), with no
  decay window — unlike routing (V2-09), which decays. Counts are reported so the reader can judge.
- **Caps and budgets unchanged**: R8 caps (≤6 workers, depth ≤2, ≤4 children per agent, ≤10
  grandchildren per mission) and budget reservations are untouched by the advice.

## V2-13 — local execution isolation: the honest edges (2026-09-21)

- **The child environment is a scrubbed inherit, not an allowlist.** PATH/SystemRoot and the rest of
  the OS environment still pass through (installed CLIs depend on them); what is enforceable without
  live CLI testing — secret-shaped names dropped, provider credential kept — is what is enforced.
- **Sessions cover native CLI children.** Broker processes are Kel's own and inherit the engine
  environment; they already get per-run broker logs and locks.
- **The sensitive list is a rule at Kel's own seams, not an OS sandbox.** It refuses Kel-driven
  snapshot and apply roots; it does not constrain what an installed CLI could read on the machine
  (that would need OS-level isolation, explicitly out of scope for V2).
- **`KEL_PROTECTED_PATHS` is environment-driven.** The desktop must set it (semicolon-separated) for
  stable-app folders to be refused; with it unset, only the built-in rules apply.
- **Read-only execution is the leaf’s own mode.** Verifier-style read-only runs rely on the
  tool-disabled argv and the isolated copy; there is no separate fs-level read-only mount.

## V2-14 — network permissions: the honest edges (2026-09-21)

- **The rules govern Kel's own outbound paths**, not the operating system: an installed CLI carries
  its own network stack (the provider's sandbox governs it); §19 is about Kel's traffic, and every
  Connection path shares the one function.
- **Contacted domains are visible for Connection traffic** (`network_events` for decisions and
  `connection_events` for performed calls); traffic from an installed CLI is not enumerated here.
- **A pending ask is resolved on the Connections surface** — there is no chat notification for it yet.
- **Approval adds exactly the host a request named** (its subdomains then match); a person who wants a
  whole domain adds the parent domain on the list directly.
- **The default stays `full` until a person chooses otherwise** — V2-14 adds the controls; it does not
  silently tighten an existing install.

## Priority 9 — the Kibble item's honest edges (2026-09-21)

- **Corrected by D-46:** Kibble IS defined — it is the user-facing name for Fix Capture / Dogfood
  behavior (the definition arrived in Nick's session handoff). Internal identifiers stay unchanged;
  the earlier “undefined” conclusion in this file and in D-44 was wrong.
- **The promotion gate itself is real and now inspectable**: `queue_promotion` and the shadow
  proposals were already recorded-never-applied; the team-surface reads
  (`action:'promotions'` / `action:'shadow'`) only show them and write nothing.
- **No promotion is applied by any path.** Applying still requires the recorded explicit user
  judgment — and Team `promotions`/`shadow` are explicitly **not** candidate approval for Build
  Update; the mapping is proved by tests.

## V2-17 — manual upgrade reliability: the honest edges (2026-09-21)

- **The inventory counts tables, not content**: an equal inventory proves no row was lost, not that
  every row is semantically intact (the V2 suites cover semantics).
- **The restore is whole-database**: it replaces the database file (through SQLite) rather than merging
  rows; the `…pre-restore-<timestamp>` rollback copy is the recovery for a wrong restore.
- **Credentials are excluded by design**: after restoring onto a machine, provider keys must be
  reconnected (the backup's own notes say so) — a restore never resurrects secrets.
- **No updater infrastructure** (by directive): upgrades are manual — stop, back up, replace, start;
  the inventory is the check before and after.

## Kibble Build Update: the honest edges (2026-09-21)

- **The candidate is a record, not an installer.** Nothing in Build Update installs, promotes or
  touches the running app; `promote()` refuses by design and installation remains future work behind
  an explicit human decision.
- **Fixed findings are candidate claims.** Even verified evidence does not rewrite Fix Capture's own
  statuses; the person's review and their Fix Capture decisions stay separate.
- **The mission needs a clean, verifiable baseline** (git toplevel == the chosen root, no uncommitted
  changes). A dirty tree is refused in plain words rather than worked around — observed live while
  this increment was itself uncommitted.
- **The runtime repair is the existing coding machinery** — its own limits (provider availability,
  quota) apply to Build Update unchanged.
- **One candidate per mission**; re-assembly refreshes a BUILDING/READY candidate but never overwrites
  an APPROVED/REJECTED review.

## V2-18 acceptance: the honest edges (2026-09-22)

- **A cancelled mission keeps answering `BUILDING`.** Measured: with the job `CANCELLED` the candidate
  surface still reports the building state (no candidate, no evidence) instead of saying the mission was
  cancelled. It never claims a build, but it is silent about the cancellation — the next slice should
  give the surface a state for it, with the Shell contract updated in `PARALLEL_SHELL_TOUCHES.md` first.
- **A coding runtime can try to satisfy the test command instead of the intent.** Measured in the
  negatives journey: a mission whose command could never pass ended with the runtime adding a
  `sitecustomize.py` that monkeypatches `sys.exit` so the command exited 0. The engine's own reviewer
  caught it and the job settled `FAILED` — but it took four runtime attempts across two providers.
- **A green Kibble acceptance journey proves the machinery, not Kel's ability to repair a real Kel
  defect** — the fixture's defect is deliberate (V2-15 is where real batches land).
- **Cancelled missions leave a `BUILDING` reading and synthetic records in the real V2 root**: the
  acceptance journeys add their own findings, missions and candidates to the development root by design
  (never to the stable app or its data).

## V2-18 acceptance, slice 5 (2026-09-23)

- **Verification on the acceptance root needs a usable reviewer (measured).** A real work request
  produced a real artifact and its digest check passed, but the milestone's `manual_review` check
  answered **"The reviewer returned no usable assessment."** (provider `claude`, model `null`), so the
  job settled CLOSED/**UNCERTAIN** — with the artifact kept, the row saying "Settled: uncertain." and a
  retry on offer. The engine refusing to claim a verification it could not obtain is the contract
  working and must stay; what is missing is a reviewer that answers on this root. Next step: give the
  acceptance engine a working reviewer (a healthy provider for the reviewer role), re-run
  `--journeys J-WORK`, and expect `VERIFIED` instead of an explained `UNCERTAIN`.
- **A request that produces no job never settles (measured defect).** `/api/send` for a recipe that does
  not exist answers in the conversation ("I could not find that recipe. …") and is then recorded as
  `DISPATCHED` with `job_id: null`; it stayed there across 40 consecutive reads with no job, no error
  and no retry offered. A shell cannot tell that request settled, and `/api/retry` refuses it (it is not
  `FAILED`). A fix needs a settled state the Shell can render, so the contract comes first: recorded in
  `PARALLEL_SHELL_TOUCHES.md` (V2-18 slice 5). Same shape applies to every "answered, no job" turn.
- **Two journeys raise state through the engine's own APIs in-process, and say so.** J-ATTN's ask
  (`CodingAdapter.approval`) and J-WORK's fence leg (`Store.create/claim/recover_abandoned`) exist only
  inside the engine, so the journey enters through the same calls the runtime uses; the surfaces,
  resolution and state transitions are the engine's. Labelled in each claim's `detail`.
- **The remote journey's "unauthenticated request" assertion is on the API, not the page.** `/` answers
  200 so the sign-in surface can load; the gate is `401 {"success":false,"error":"Authentication
  required","code":"UNAUTHORIZED"}` on API routes. The renderer half of §9 stays Astra's.
