# KEL V2.0 — MARATHON STATE

## Current state — 2026-09-28 (read this first; CP-20)

This block is the current truth. Everything under **History** below is the dated record as it was
written; it is kept, not rewritten. Where a later decision or build changed a statement, the statement is
marked *(Superseded 2026-09-28: …)*. Blanket supersessions for the history: every "App stays / still
packages `8c67121`" or "App contains `6b90dbe`" line is superseded by the install below; the **Work page**
is retired (D-70 — work cards and Activity replace it, `/work` redirects to Home); the word
**Workspace** left the UI (D-54 — "Projects"); the **Desktop Pet**, the **updater** and "Update
available" are gone (D-56); the **language selector** is gone (D-61, English only); reply **reactions**
are gone (D-59); the **Autonomy** choice is settled as Full access with an "Ask first" switch (D-64); the
donor **cron** scheduler is retired (D-57).

**Source.** `main` at `C:\Users\Nick\Desktop\Kel\Kel`, pushed to `github.com/BeardedBats/Kel`.

**Installed App.** Source **`5294c27`**, installed 2026-09-28 (`App\kel-install-provenance.json`):
an `electron-builder --dir` package whose `resources/app.asar`, `app.asar.unpacked` and `kel-engine`
replaced the previous ones (Kel.exe, bundled AionCore, hub and fonts kept). Previous install `44d4115`;
rollback copy `Tools\.app-rollback-44d4115-to-5294c27`; Data backup
`Data\backups\pre-install-2026-09-28-5294c27`; migrations 36+ applied on first launch. Checks recorded
at install: desktop typecheck clean and 112 files / 866 tests; engine 1,645 passed; the packaged build
ran a real coding job off-screen on a copy of real Data (Claude Opus 5.5 built it, GPT-6 Astra verified
it, the original-tests gate passed, it was applied on its own with Undo); the installed app launched
off-screen on real Data (engine up, Full access, 10 staff roles, Staff & models page, no console errors).

**On `main`, not installed yet** (after `5294c27`): D-72 recorded and applied in the engine
(`0577e58`, `1c97fbe`); off-screen test runs never raise desktop notifications (`edf999b`); usage shown
for each reply and piece of work (`b96f713`); the result card names the project and folder once
(`7eb8285`); Nick chooses when Kel scopes first, and typed scoping answers reach the open card
(`4f64e2a`, `f46da65`); Staff & models shows per-role fall-backs and how Kel picks models, and a card
stopped on its budget offers Raise budget (`5cda011`, `74d490a`); and the 2026-09-28 leftovers batch — "Create scheduled task" from a chat opens
the D-57 editor filled in (`d2b65b4`), plain Connections wording (`40f6ae5`), e2e/packaged checks on
today's screens (`c42533d`), engine messages name the work card instead of "Work context" (`eda6f27`,
`2b4fa14`), dead code and the unused Monaco dependency removed (`5683226`), and this docs
consolidation. Since then: the motion language was approved (D-77) and its stage-2 library
`renderer/motion/` built (`design/MOTION.md` §11); the §10 moments are not wired to it yet.

**Workforce live (D-66, D-67, D-69).** Every real-work job is staffed; each staff role runs on its own
model with a real reasoning level (D-67 table, changeable per role in Settings → Staff & models); a
model picked in a chat applies only to Kel's own replies; the pod's lens review and the Oracle (a
different model family where possible, reduced independence recorded) run before anything is applied;
`/api/office` feeds the work cards. Design: `design/D-66_WORKFORCE_LIVE.md`.

**Routing 2** (`design/ROUTING_2.md`): §5.0–§5.7 built — task classes and dispatch tiers, measured
tokens/time/cost per staffed call, outcome-aware promotion and demotion, a budget governor that
reserves before each step, model-primary classification with regex floors, DeepSeek Flash with
OpenRouter as a second route, and an advisory calibration harness. D-72 adopted the recommended defaults
(they are recommendations, not Nick's explicit picks). Still open: per-model overlays, local-only mission
routing beyond the privacy filter, quota-pace projection and a live calibration campaign. The renderer's "How Kel picks models" table
and "Raise budget" button are on `main` (`5cda011`, `74d490a`), not installed.

**Decisions D-53..D-72 — where each stands** (text in `DECISIONS.md`):

| Decision | State |
| --- | --- |
| D-53 background hand-off, chat stays usable | Built (`daa510c`), installed |
| D-54 "Projects" is the one term; engine-backed Project switcher | Built (`d1857cc`, `a676200`), installed |
| D-55 ask before starting; restart running work with a change | Built (`586ee8d`), installed |
| D-56 no consumer updater, no Desktop Pet | Built (`b3b4ad2`, `6039891`, `5ca82a6`), installed |
| D-57 scheduled tasks are scheduled Recipes in the engine | Built (`1384716`, `e72ef40`), installed; chat-menu entry opens the editor on `main` (`d2b65b4`) |
| D-58 Data and repository clean-up | Done (`549969f`, `1ecc462`) |
| D-59 reactions removed | Built (`150765b`), installed |
| D-60 Settings show only what Kel has built | Built (`23f2b1a`), installed |
| D-61 English only | Built (`35c1cf4`), installed; the preload's leftover initial-language hand-off removed on `main` |
| D-62 General gets a default folder | Built (`a5b8684`), installed |
| D-63 history rewrite and branch pruning | **Approved, not done** — old branches (`audit/*`, `dev/*`, `fix/*`, `integration/v2`) still exist and no backup bundle is in `Tools` |
| D-64 Full access by default | Built (`a5b8684`, `ddcfcad`), installed |
| D-65 Full access applies verified changes, with Undo | Built (`5b5b6ea`), installed |
| D-66/D-67/D-69 live workforce, role models, Oracle | Built (`4ee8a61`, `5472836`, `1edb4d6`, `61c73ff`), installed |
| D-68 work cards across the top of the chat | Built (`26196ea`), installed |
| D-70 answer on the card, one live view, Staff & models, scoping, navigation clean-up | Built (`a728c4b`, `1adf219`, `da8d6e3`), installed; scoping threshold choice on `main` (`4f64e2a`) |
| D-71 "existing tests preserved" = original tests still pass | Built (`f75c7aa`), installed |
| D-72 routing defaults | Recorded and applied on `main` (`0577e58`, `1c97fbe`), not installed |

**Phase table (unchanged by D-53..D-72).** Built: V2-00–V2-04 (with V2-04a and V2-04b), V2-06–V2-14,
V2-17. Partial: V2-05, V2-16, V2-18, V2-19. Planned: V2-15, V2-20. Mobile stays paused; desktop first.

**Open, and what needs Nick.**
- **"Ask first" has no Apply button today.** A verified change that waits only because the mode is Ask
  first has no Apply control: "Apply checked changes" lived in the Work & context drawer, which has not
  been mounted since 2026-09-21, and the work card offers "Apply anyway" only when Kel had its own reason
  to wait. The result text in that case still mentions "Download the change report" and "Apply checked
  changes". Full access (the default) is unaffected.
- **The Work & context drawer is dead code with no other home for some of its parts**
  (`components/chat/KelWorkPanel.tsx`: its Vetting tab — the command palette still says "Vetting lives
  in the Work panel" — and the change-report download). Decide: re-home those parts or delete it.
- D-66's open questions: a schedule's model is Kel's own, not staff's; work from before staffing never
  becomes a card.
- D-72's six values are recommendations; D-63 is not executed.
- Live acceptance still open: a physical iPhone, real personal services (Google Drive needs Nick's own
  Google OAuth client — see `CONNECTION_FRAMEWORK.md`), fresh Muse audio, remote first response.

**Next.** Nick decides the Ask first / Work & context questions above. Install `main` at the next
meaningful milestone (the D-72 defaults, usage, scoping choice and the leftovers are waiting). Then the
Routing 2 renderer surfaces, D-63 when no agent is committing, and live acceptance.

## History

The dated record below is kept as written (newest checkpoints were prepended above older ones, so the
order is roughly newest first). Read it for evidence and provenance, not for current state.

## Desktop installed milestone (2026-09-26)

[Installed milestone](evidence/figma-full-audit/DESKTOP_INSTALLED_MILESTONE.md): App now contains desktop source 6b90dbe; main also has packaging-only alignment 9d5a1bf. All 265 renderer and 2,655 installed package files match. Chat/task/Tools and real isolated Work/Permissions passed bundled checks; installed Tools/task and 32 core route checks passed at 1440/800px. TypeScript/build and 65 files / 448 tests passed. All 2,949 canonical Data files stayed unchanged. [All 75 desktop frame dispositions](evidence/figma-full-audit/DESKTOP_FRAME_DISPOSITIONS.md) distinguish proof from limits. Autonomy/Pet decisions, live acceptance, exact Light palette and documented deviations remain open *(Superseded 2026-09-28: Autonomy is settled as Full access (D-64) and the Pet is removed (D-56); live acceptance and Light palette remain open)*; V2-16/18/19 remain partial and mobile paused. Temporary deletion was policy-blocked; tracked source clean, known packages/ cache preserved.

## Desktop Chat/task/Tools batch (2026-09-26)

[Batch evidence](evidence/figma-full-audit/DESKTOP_FINAL_IMPLEMENTATION_BATCH.md) closes scoped source checks for sidebar variants, confirmed Planning subtitle, Chat artwork/material, task picker/glass/disabled variants, failed-status detail and enabled Image Model selection. Dark/Light 1440/800px passed; TypeScript/build and 65 files / 448 tests passed. Supplied runtime/task catalogs are presentation evidence; real isolated Image Model selection/enable/reload was restored. One larger package is next. App remains 8c67121; Data untouched; mobile paused.

## Desktop ACP Chat footer checkpoint (2026-09-26)

[ACP Chat footer](evidence/figma-full-audit/DESKTOP_CHAT_FOOTER_SOURCE.md) now reads actual usage/window state and retains permission callbacks/availability guards. Dark/Light 1440/800px pass footer/chip bounds, missing values, populated turn/list/avatar checks, scrolling and 24px inset without overflow/errors. Sidebar bottom/icon sizing repaired. TypeScript/build, nine focused tests and full 64-file/446-test regression pass. Native fixture restored; no provider/send/permission change ran. Full sidebar status variants, Planning subtitle, exact icons/glass and live catalog/usage remain open. Package with the next larger milestone; App 8c67121/Data untouched; mobile paused.

## Desktop Chat bottom inset checkpoint (2026-09-26)

[Chat bottom inset](evidence/figma-full-audit/DESKTOP_CHAT_BOTTOM_INSET_SOURCE.md) passes exactly 24px in Dark/Light at 1440/800px. Short threads have no scrollbar; hover/focus/Copy remain accessible. Three-turn wheel access and mixed tool/plan/reply controls pass. Fixture messages/reaction restored; zero overflow/errors. TypeScript/build, six focused tests and combined full 63-file/443-test regression pass. Full Chat/sidebar/footer and task icons/glass/catalog remain open. Package at the next larger milestone; App 8c67121/Data untouched; mobile paused.

## Desktop task field rhythm checkpoint (2026-09-26)

[Task field rhythm](evidence/figma-full-audit/DESKTOP_TASK_FIELDS_SOURCE.md) now measures 600Ã—614px at y70 in Dark/Light, 1440/800px. Label/field/prompt/gap metrics, unsaved Cancel/reopen, Dark Weekly and Light Advanced/Manual/Custom pass without overflow/errors. Light minimum sampled contrast 5.39:1. TypeScript/build and 12 focused tests pass. Two owned synthetic configuration records were removed after an enabled catalog probe failed; model choice is not accepted. Task icons/glass/disabled variants and live catalog remain open. Package with the next larger milestone; App 8c67121/Data untouched; mobile paused.

## Desktop task Model/Time row checkpoint (2026-09-26)

[Task Model/Time row](evidence/figma-full-audit/DESKTOP_TASK_MODEL_ROW_SOURCE.md) now uses the existing selector beside Time on desktop; mobile retains Advanced placement and edit guards stay unchanged. Dark/Light pass 1440/800px alignment, y70/600px bounds, zero overflow/errors and unsaved Cancel/reopen behavior. Weekly does not overlap. The isolated assistant has no model catalog; only the existing read-only Automatic fallback was verified. TypeScript/build and final 63-file/443-test regression pass. Full field type/spacing/height and enabled catalog state remain open. Package with the next larger milestone. App 8c67121/Data untouched; mobile paused.

## Desktop Chat turn rhythm checkpoint (2026-09-26)

[Chat turn rhythm](evidence/figma-full-audit/DESKTOP_CHAT_TURN_RHYTHM_SOURCE.md) passes 30px row gaps, short-thread bottom placement without scrollbar, long-thread wheel access and mixed tool/reply order in Dark/Light at 1440/800px. Native fixture messages/reaction restored; zero overflow/errors. TypeScript/build and six focused tests passed. The 32px retained-control bottom gap differs from Figma's 24px thread padding and remains open. Full Chat/sidebar/footer and task field/model parity remain open. Package by the next larger milestone. Latest disposable package b8c84ae; App 8c67121/Data untouched; mobile paused.

## Desktop source completion milestone package checkpoint (2026-09-26)

[Milestone package](evidence/figma-full-audit/DESKTOP_SOURCE_COMPLETION_MILESTONE_PACKAGE.md) at b8c84ae passes eight grouped 1440/800px probes: Setup retention, legacy Workspace, Light Workspace/File, Light Ramble key/Merge/Vetting, populated Chat type, Light Tools and Light task form. All 266 renderer files match; native rebuilding and full 63-file/443-test regression pass. Normal bundled renderer, no Vite/history interception. Scoped real isolated actions and injected/intercepted limits are recorded; settings/messages restored and apps closed. Canonical App remains 8c67121; Data untouched. Full Chat/task/icon acceptance, live journeys and V2-19 remain partial. Mobile paused.

## Desktop Light task form checkpoint (2026-09-26)

[Light task form](evidence/figma-full-audit/DESKTOP_LIGHT_TASK_FORM_SOURCE.md) passes 1440/800px at 600px width/y70, 16px radius/24px blur, minimum sampled label contrast 5.39:1 and zero overflow/errors. Unsaved fields, Weekdays, skip switch, Cancel/reopen and Escape passed; no task/provider ran. TypeScript/build and 12 focused tests passed. Full task field/model parity and milestone package proof remain open. App/Data untouched; mobile paused.

## Desktop Light Tools dialogs checkpoint (2026-09-26)

[Light Tools dialogs](evidence/figma-full-audit/DESKTOP_LIGHT_TOOLS_DIALOGS_SOURCE.md) pass JSON, CLI import, report and delete at 1440/800px with Figma geometry, 16px radius/24px blur, minimum sampled contrast 5.38:1 and zero overflow/errors. Valid input, selection/count, Back/Cancel and Keep passed; no import/report/delete/provider ran. TypeScript/build and seven focused tests passed. Package by the next larger milestone. App/Data untouched; mobile paused.

### Original heading: KEL V2.0 — MARATHON STATE

## Desktop populated Chat type checkpoint (2026-09-26)

[Populated Chat type](evidence/figma-full-audit/DESKTOP_POPULATED_CHAT_TYPE_SOURCE.md) passes five list rows at 14px gaps, 13px/16px timestamps, 24px avatar slot/22Ã—23 mark and last-turn wheel scroll at 1440/800px in Dark/Light. User alignment/390px width already matched. Native synthetic messages were journaled/restored; source legacy prefix intercepted. TypeScript/build and six focused tests passed. Full frame placement/rhythm/sidebar/footer facts remain open. Package by the next larger milestone. App/Data untouched; mobile paused.


## Desktop Light Ramble dialogs checkpoint (2026-09-26)

[Light Ramble dialogs](evidence/figma-full-audit/DESKTOP_RAMBLE_LIGHT_DIALOGS_SOURCE.md) pass API key, Merge and Vetting at 1440/800px with minimum sampled label contrast 4.76:1, zero overflow/errors. Key Cancel/reopen, radio/arrow controls and real preview rechecks passed. No key/merge/accept/process mutation occurred; owned synthetic recordings removed and saved transcript preserved. TypeScript/build and 14 focused tests passed. Package by the next larger milestone. App/Data untouched; mobile paused.


## Desktop Workspace header and Light surfaces checkpoint (2026-09-26)

[Workspace/Light source checks](evidence/figma-full-audit/DESKTOP_WORKSPACE_LIGHT_SOURCE.md) repair the legacy header/native-control overlap and narrow collapsed-panel width. Real titlebar collapse/reopen passed Dark/Light at 1440/800px. Light file tree, SCM tabs, heading menu, preview/code/status/action menu and read-only/split controls pass; 74 labels measured at least 5.39:1. TypeScript/build and 11 focused tests passed. Prior isolated panel preferences and Dark restored; no file mutation. Package by the next larger milestone. App/Data untouched; mobile paused.


## Desktop Setup retention checkpoint (2026-09-26)

[Setup retention](evidence/figma-full-audit/DESKTOP_SETUP_RETENTION_SOURCE.md) passes real isolated folder-draft write/reload, canceled picker, Work setup-return banner and Chat gate at 1440/800px. Prior client preferences/history restored; zero overflow/errors. TypeScript/build, seven focused tests and full 63-file/443-test regression passed. Native picker intercepted; no provider/job/authority change. Package proof waits for the next larger milestone. Autonomy selection still awaits Nick. *(Superseded 2026-09-28: settled by D-64, Full access with an Ask first switch)* App/Data untouched; mobile paused.


## Desktop Kibble recovery / Light / Chat package checkpoint (2026-09-26)

[Milestone package](evidence/figma-full-audit/DESKTOP_KIBBLE_LIGHT_CHAT_MILESTONE_PACKAGE.md) at `0b49b56` passed 1440/800px bundled-renderer checks for Kibble recovery, Light menus/dialogs, Chat plan/reply actions, error and reconnecting. All 266 renderer files matched; zero renderer errors/overflow. Real isolated pointer/reaction writes passed and were restored; runtime/mission states and clipboard were injected/intercepted. No worker/provider/restart/export/download/delete ran. Broader Chat/right-panel and Light Workspace/icon states remain open. The next Setup increment is not in this package. Canonical App remains `8c67121`; Data untouched. Mobile paused.


Machine-readable-ish program state. A resume run reads `MARATHON_DIRECTIVE.md` â†’ this file â†’ `RESUME.md`
and then continues the exact `current_item`. Update this file whenever a phase starts or closes.

```yaml
program: kel-v2.0
line: v2
branch: main                 # one canonical source repository after consolidation
base_commit: a471e17ac25590369e74824ebed0dd7b54e4b00b   # V2.0 base (dev/daily-driver head at setup)
setup_commit: 47eb3b49322a7cfbe85bbee7a0674c77037b127f   # V2 program initialization; this file's hash record is the records commit
remote: https://github.com/BeardedBats/Kel

phase: V2-19                # bounded product and Figma regression; release candidate still pending
next_item: Nick decisions for Setup Autonomy and Pet, then one authorized desktop batch and live desktop acceptance. Installed App source 6b90dbe; main packaging alignment 9d5a1bf; Data hashes unchanged; mobile paused. See DESKTOP_INSTALLED_MILESTONE and DESKTOP_FRAME_DISPOSITIONS. Temporary cleanup policy-blocked.

status: partial
# [Desktop reply actions](evidence/figma-full-audit/DESKTOP_REPLY_ACTIONS_SOURCE.md) now follow tool rows at 1440/800px in Dark/Light. Original-message clipboard handoff and real isolated reaction writes passed; prior reaction was restored. TypeScript/build and full 63-file/440-test regression passed. No provider/fork/tool execution ran. Package proof and broader populated Chat remain open; App/Data untouched.
# [Desktop Chat plan/Light states](evidence/figma-full-audit/DESKTOP_CHAT_PLAN_LIGHT_STATES_SOURCE.md) pass tool/plan collapsed/expanded in Dark/Light and Light error/reconnecting at 1440/800px. Plan geometry and narrow current-step space are repaired. Minimum measured Light label contrast is 4.86:1; zero overflow/errors. Fourteen focused tests and source build passed. Legacy prefix and runtime states were intercepted/injected. Package proof, reply-action order, broader Chat/right-panel states remain open. App/Data untouched.
# [Desktop Light startup/shared dialogs](evidence/figma-full-audit/DESKTOP_LIGHT_DIALOGS_SOURCE.md) pass five states at 1440/800px with minimum measured label contrast 4.86:1, no overflow/errors, ten focused tests, and source build. Update/Delete geometry and stopped-engine surfaces are repaired. Startup/failure/update/task records were injected/intercepted. No restart/export/download/delete ran. Package proof remains open; App/Data remain untouched.
# [Desktop Light menus](evidence/figma-full-audit/DESKTOP_LIGHT_MENUS_SOURCE.md) pass six menus at 1440/800px, with zero overflow/clipping/errors. Minimum measured word contrast is 4.81:1; marks 4.76:1. Gradient-backed Accept and pixel-level icon contrast are excluded. Source build passed. Memory/catalog/native picker actions were intercepted; no live provider ran. Package proof waits for the larger milestone. App/Data remain untouched.
# [Kibble recovery](evidence/figma-full-audit/DESKTOP_KIBBLE_RECOVERY_SOURCE.md) passes 1440/800px navigation/reload and approved-state source checks, real isolated pointer persistence, TypeScript/build, ten focused tests, and 63 files / 440 tests. Engine mission records were intercepted; no worker ran. Panel sheen is repaired. Package proof remains open for this increment; App/Data remain untouched.
# [Kibble/Setup/Pet/Skills/Light milestone](evidence/figma-full-audit/DESKTOP_KIBBLE_SETUP_LIGHT_MILESTONE_PACKAGE.md) at 41a73f5 passed six packaged Electron probes and archive-browser sign-in at 1440/800px. All 266 renderer files match. Real isolated actions and injected/intercepted limits are recorded. Canonical App remains 8c67121; Data remains untouched. Mission recovery/panel sheen and broader desktop acceptance remain open.
# [Desktop Light labels](evidence/figma-full-audit/DESKTOP_LIGHT_LABELS_SOURCE.md) now pass eight source routes at 1440/800px with minimum measured enabled-label contrast 4.86:1, zero overflow/errors, seven theme tests, and a source build. Dark was restored in the isolated profile. Exact Light palette parity, icons/popups, and package proof remain open. App/Data remain untouched.
# [Populated Skills](evidence/figma-full-audit/DESKTOP_SKILLS_POPULATED_SOURCE.md) pass real isolated import/list/reload and measured 1440/800px source checks. The desktop fill is repaired and long text wraps. Owned imports were removed. TypeScript/source build passed. Package proof and detail/import-history routes remain open. App/Data remain untouched.
# [Kibble build variants](evidence/figma-full-audit/DESKTOP_KIBBLE_BUILD_VARIANTS_SOURCE.md) now have 1440/800px source checks for Running, Cancelled, and candidate review. Progress uses actual reported state/counts; details remain expandable. Intercepted Approve/Reject handoffs passed; no actual build or installation ran. TypeScript/build, seven focused tests, and the full 63-file/437-test suite passed. Worker execution, mission recovery, and package proof remain open. App/Data remain untouched.
# [Desktop Pet off/settings and remote sign-in](evidence/figma-full-audit/DESKTOP_PET_SIGNIN_CURRENT_REVISION.md) pass current 1440/800px source checks. Pet refusal/reload used real isolated IPC and kept Off. Sign-in is 420Ã—330 with 34px fields and viewport-positioned language; input/show-hide/remember/invalid-login handoff passed with intercepted auth. TypeScript/build, 11 policy tests, and the full 62-file/433-test suite passed. Pet enable, real sign-in, measured Light parity, and package proof remain open. *(Superseded 2026-09-28: the Pet is removed (D-56); real sign-in and Light parity remain open)* App/Data remain untouched.
# [Desktop Setup](evidence/figma-full-audit/DESKTOP_SETUP_CURRENT_REVISION.md) now uses actual model state, accessible progress, and real folder selection/composer handoff. Isolated model/config writes and 1440/800px source checks passed. The warm setup-return banner passed on Knowledge; Work remains gated until setup finishes. *(Superseded 2026-09-28: the Work page is retired (D-70))* The native picker result was intercepted. TypeScript/build, four focused tests, and 62 files / 433 desktop tests passed. Setup policy selection and broader persistence/parity remain open. App/Data remain untouched.
# [Desktop Kibble](evidence/figma-full-audit/DESKTOP_KIBBLE_CURRENT_REVISION.md) now has current 1440/800px source evidence for its panels, finding selection, direct status actions, and screenshot/quote details. Real isolated Mark fixed, Reopen, and selected prompt/Batched writes passed; fixtures were dismissed. TypeScript/source build, 35 focused tests, and the full 61-file/431-test suite passed. Running build/candidate presentation remains open. Canonical App and Data remain untouched; package proof waits for the next larger milestone.
# [Runtime and Ramble milestone package](evidence/figma-full-audit/DESKTOP_RUNTIME_RAMBLE_MILESTONE_PACKAGE.md) at `0b4a583` passed seven packaged probes at 1440/800px, with zero renderer errors or overflow. All 265 renderer files match the archive. Real isolated restart, sanitized export, Merge, and Vetting preview passed; injected/intercepted limits are recorded. Canonical App stays `8c67121`; Data remains untouched. Desktop implementation and acceptance remain partial.
# [Desktop Ramble](evidence/figma-full-audit/DESKTOP_RAMBLE_CURRENT_REVISION.md) now has current 1440/800px source evidence for its transcript, connected-key replacement input, Merge list, and Vetting modal. Real isolated merge and preview rechecks passed; new recordings were cleaned up and the saved vetting transcript remained unchanged. TypeScript/source build, 35 runtime transcription tests, four transcription-policy tests, four Ramble DOM tests, and the final 60-file/428-test desktop suite passed. [Desktop Figma context inspection](evidence/figma-full-audit/DESKTOP_CURRENT_AUDIT_COVERAGE.md) covers 75/75 current frames; this is not accepted parity. Canonical App stays 8c67121, Data is untouched, and mobile stays paused.
# [Desktop Update available and task delete confirmation](evidence/figma-full-audit/DESKTOP_SHARED_DIALOGS_SOURCE.md) pass source checks at 1440/800px. Update uses actual versions/release notes and existing download authority. *(Superseded 2026-09-28: the updater and its dialogs are removed (D-56))* Delete now uses the Figma modal; Keep/Escape and intercepted deletion handoff passed. TypeScript, source build, and three update-policy tests passed. Stopped-engine inner surface styling was corrected and rechecked. These changes await the next larger package. Canonical App and Data remain untouched. Current desktop context coverage is 66 READ / 9 PENDING; READ does not mean complete parity.
# [Combined desktop milestone](evidence/figma-full-audit/DESKTOP_COMPLETION_MILESTONE_PACKAGE.md) passed packaged 1440/800px checks at `f8e6d86`: Work, Permissions, Knowledge, saved recipes, and chat menus. [Starting, stopped engine, and diagnostics export](evidence/figma-full-audit/DESKTOP_RUNTIME_VIEWS_SOURCE.md) now pass source checks at both widths. Real isolated restart and sanitized local export passed. TypeScript, source build, 17 runtime diagnostics tests, and the final 60-file/427-test desktop suite passed. These latest runtime views await the next larger package. Canonical App remains `8c67121`; durable Data was untouched.
# [Desktop Knowledge and project recipes](evidence/figma-full-audit/DESKTOP_KNOWLEDGE_CURRENT_REVISION.md) now have 1440/800px source evidence. Proposal labels/order, row icons, card rhythm, map columns, saved-record scrolling, valid memory actions, and saved recipe links are implemented. Real isolated-engine mutations passed. TypeScript, ten focused Work/recipe tests, and 60 files / 427 desktop tests pass. The later combined milestone package passed; App and Data remain unchanged.
# [Active/waiting Work and populated Permissions](evidence/figma-full-audit/DESKTOP_WORK_PERMISSIONS_STATES.md) pass real isolated-engine checks at 1440/800px. Job selection, current step, continuation instructions, wrapping, and scrolling are repaired. Answer request, Allow once, and Revoke passed through real engine routes. Auto Edit and Add a file labels match live Figma. TypeScript, source build, 19 Work/attention tests, and four menu DOM tests passed. App and Data were untouched. The later combined milestone package passed.
# Populated canceled Work and project proposals/map now have 1440/800px source checks. Narrow desktop text and table overflow were repaired; keyboard scrolling passes. Active/waiting Work, populated permissions, saved knowledge, and project recipes remain open. See evidence/figma-full-audit/DESKTOP_POPULATED_LAYOUT_SOURCE.md.
# Desktop Memory review, Permission, Slash, and Attach menus pass 1440/800px source-render checks, TypeScript, source build, and nine focused tests. Memory is 440Ã—236; Permission is 300Ã—286. Catalog availability and actions remain unchanged. Package proof waits for the larger milestone. See evidence/figma-full-audit/DESKTOP_CHAT_MENUS_CURRENT_REVISION.md.
# Nick chose larger desktop milestones for packaging on 2026-09-26. Use source/render checks and focused tests between milestones. Commit and push verified source increments. Do not package each small component batch.
# Desktop Activity loading and Providers error have final 1440/800px package checks at source 98387fc. Pending/error states were injected; retry recovered through the real isolated engine. Diagnostics copy and reduced motion passed. All 417 desktop tests passed. See evidence/figma-full-audit/DESKTOP_PENDING_STATES_CURRENT_REVISION.md.
# Desktop Workspace and File preview have final 1440/800px package checks at source e77f8bb. Real SCM/search, read-only mode, split, file attachment, save and restoration passed. All 415 desktop tests passed. Synthetic fixture deletion was policy-blocked. See evidence/figma-full-audit/DESKTOP_WORKSPACE_CURRENT_REVISION.md.
# Desktop Model and Project pickers now have isolated 1440/800px package checks. Scope writes, preference restoration, project search/select/clear, Escape, and Add Model passed. Browse used an injected native dialog result. All 408 desktop tests passed. See evidence/figma-full-audit/DESKTOP_PICKERS_CURRENT_REVISION.md.
# Desktop Fix Capture Select/Recording/Review now have isolated 1440/800px package checks. Recording measures 380Ã—181 and Review 420Ã—232. Synthetic audio drove retry, Record Again, and cancellation; no fix was saved. The palette focus ring and delayed search results also passed. See evidence/figma-full-audit/DESKTOP_FIX_CAPTURE_CURRENT_REVISION.md.
# Command palette, Chat row menu, and Rename chat now have isolated 1440/800px package checks. Their frames measure 640Ã—429, 232Ã—227, and 440Ã—168. Escape and Capture a fix cancellation passed. Chat Markdown content passed an intercepted renderer probe; native save-dialog completion remains untested. The final palette-input focus-ring repair is source-render checked and awaits the next batch package. See evidence/figma-full-audit/DESKTOP_CHAT_OVERLAYS_CURRENT_REVISION.md.
# Current Figma overlays New scheduled task 273:1586 and Approval details 273:2125 now have isolated 1440/800px package checks. The form was filled but not saved; the pending approval was opened but not decided. Bounds match their Figma frames. See evidence/figma-full-audit/DESKTOP_OVERLAYS_CURRENT_REVISION.md.
# Nick prioritised complete desktop implementation on 2026-09-25. He will test desktop while mobile UI/UX implementation continues. Desktop Recipes list, Preview, and Run are implemented with isolated package evidence. Desktop Home, Work empty, Activity empty/running, Permissions empty, Projects empty, Scheduled tasks list/detail, Connections empty/populated/credential, Providers, Diagnostics, Model, Assistants, Skills, Appearance, System, Restore, About, Archived/Select, and enabled WebUI/Change password have current scoped package checks. Archived used synthetic sidebar rows; WebUI started and stopped with isolated data. System and About card bounds match scaled Figma at 1440px; a real isolated backup reached and canceled the Restore confirmation. Appearance's Add theme save/select/reload path passed with isolated data. Assistants uses its one actual Kel row. Skills showed a truthful empty state; populated custom skills remain open. Activity's separator-space correction was included in the later Projects package. Scheduled task detail has real toggle/pause/edit/confirmation checks and synthetic History layout. Scheduled list controls open the real edit dialog. Populated Work, Permissions, Projects, and Scheduled tasks remain open. Model has a compact Add model flow and populated custom-model rows package-checked with isolated fake configuration. Providers has three truthful readiness rows; a real model reply is untested. Diagnostics maintenance controls remain open because matching runtime operations do not exist. Connections mutating action confirmation is DOM-tested but has no packaged state because the engine catalogs read actions only. Package by coherent desktop feature groups instead of per Figma frame. Canonical App packages source 8c67121; promotion awaits desktop completion. Current Tools, selected Chat states, Transcriptions, and selected mobile states have scoped disposable package checks. Older visual results are historical. See evidence/figma-full-audit/FIGMA_REVISION_2026-09-25.md and its linked scoped records.
# V2-04 (the Connection Framework) is closed; its two open needs are carried as V2-04a/V2-04b in FEATURE_LEDGER.md.

deferred:
  - "Physical iPhone acceptance needs Nick's device. Remote sign-in, live services, and first response need a signed-in session."
  - "Enabled Desktop Pet needs Nick's decision on V1.6 policy AUD-MINOR-008; the canonical App correctly refuses enable."

paths:
  source: C:\Users\Nick\Desktop\Kel\Kel
  app: C:\Users\Nick\Desktop\Kel\App
  data: C:\Users\Nick\Desktop\Kel\Data
  tools: C:\Users\Nick\Desktop\Kel\Tools

protected_paths:
  - C:\Users\Nick\Desktop\Kel\App
  - C:\Users\Nick\Desktop\Kel\Data

phases:
  V2-00: done        # developer line + durable program state (this setup commit)
  V2-01: done        # Connections model + central management (migration 23, /connections surface)
  V2-02: done        # Generic REST Connection + Test Connection (migration 24, perform_request choke point)
  V2-03: done        # Personal Connections: the eight services as data (migration 25, auth_prefix)
  V2-04: done        # framework, callable actions (04a), and OAuth flow (04b) built; real external sign-in pending
  V2-05: partial     # browser phone journeys proved; physical iPhone acceptance pending
  V2-06: done        # Needs Your Attention 2.0 â€” attention rows on the existing Work surface (priority/age/reason/related/one direct action/grouping) + the row for a real ask answered in one action (D-50; journey J-ATTN)
  V2-07: done        # Recipes 2.0 â€” the recipe library's own surfaces (search/favourites/recent/categories/history/last result/duplicate/project attachment/run again), migration 30 `v2-recipe-library` (D-50; journey J-RECIPE)
  V2-08: done        # Activity 2.0 â€” /api/activity over the records the line already keeps (D-50; journey J-ACTIVITY)
  V2-09: done        # Routing intelligence â€” decayed outcome evidence, evidence-aware Automatic ordering (floor-protected), read-back "Why this model?", tool requests become real work turns
  V2-10: done        # Learning 2.0 â€” evidence-thresholded suggestions (existing proposal queue), off/on without deletion, explain, authority fence
  V2-11: done        # Long-running work 2.0 â€” runtime fencing of abandoned runs (never re-played), the Work brief (shipped/open/why/next + needs_you)
  V2-12: done        # Adaptive staffing 2.0 â€” one bounded step of outcome-history advice on the existing staffing paths (advice recorded on every staffing.decided)
  V2-13: done        # Local execution isolation â€” sensitive-root refusal at the autonomous seams, disposable per-run sessions, secret-shape env scrub (no VM, no sandbox rewrite)
  V2-14: done        # Network permissions â€” modes + per-tool/per-Project rules behind the one seam, ask-before-a-new-domain, access history
  V2-15: queued      # Real dogfood integration pass
  V2-16: partial     # Dark Settings/setup repaired; r29 local conversation-open median 112.4 ms, project switch median 114.9 ms; remote/first response pending
  V2-17: done        # Manual upgrade reliability â€” inventory before/after, and the V2 state proved to survive backupâ†’restore exactly (no updater infra)

  V2-18: partial     # Backend journeys and the F1 rechecks passed; J-REMOTE and Shell/phone journeys remain
  V2-19: partial     # canonical full engine 1289 pass + 14 subtests and desktop 448 pass; exact visual parity and live paths remain

  V2-20: queued      # V2 release candidate

invariants:
  - "one capable personal assistant with hidden orchestration â€” Nick never learns workers, leases, scopes, staffing graphs, runtime topology, routing internals, event streams, MCP plumbing or execution packets"
  - "Fix Capture stays exactly as built (OPEN / BATCHED / FIXED / DISMISSED); it is not Jira and is never rebuilt"
  - "no second system of anything: no second memory, workflow, auth, permission or task database"
  - "never single-side colored borders or accent rails; typography, spacing, background tone, subtle full-perimeter neutral borders only"
  - "desktop Kel may stay on; cloud Kel is V2.5 and does not start here"
  - "disk hygiene: no indefinite temporary worktrees, no obsolete node_modules/build copies, no duplicate installers, no accumulating data roots"

temporary_worktrees: []
```

The state below this line is historical phase evidence. Its old candidate, worktree, and data paths
were removed during consolidation. Use the YAML above and `docs/CONSOLIDATION_STATUS.md` for current paths.

## Integration line (2026-09-22) â€” historical

`C:\Users\Nick\Desktop\Kel\kel-v2-integration` on branch `integration/v2` @ `fe5e6b7` merges
`dev/v2` @ `7b18618` with Astra's committed Shell baseline `ux/v2-shell` @ `0052075` (verified from the
merge's own second parent; the merge commit's own message still says `681e005`, which was her tip
earlier in the turn â€” a pushed merge is never rewritten, so this section is the accurate record). One
conflict was resolved in the web-host unit suite; see `docs/v2/evidence/integration/README.md`. The
worktree exists because the packaged candidate must be built from the union, not from either line
alone. Its `desktop/node_modules` is a junction to `dev/v2`'s (bun cannot resolve nested packages
through it, so a real `bun install` is needed before any build there). Remove this worktree once the
candidate is packaged and reviewed, or once Astra's line absorbs the merge â€” whichever comes first,
and record it here when it goes.

## V2-01 notes for the next run

- **What exists now:** `runtime/kel/connections.py` (migration 23 `v20-connections`) with
  `/api/connections` (`list` / `get` / `save` / `remove` / `set_credential` / `delete_credential`), the
  `/connections` page in the desktop renderer, and credential custody under the `connection:<id>`
  namespace in the existing OS-backed store. The engine stores field names plus a `kel:connection:<id>`
  pointer and never a value.
- **Deliberately absent (do not "fix" it):** no built-in service list, no per-service module or table, no
  network call of any kind, no Test Connection, and no seeded rows. `test_endpoint` is stored for V2-02.
- **V2-02 starts from:** the Generic REST Connection (fields + Test Connection). The store already has
  every field that phase needs; the missing piece is the request layer, the permission gate in front of
  it, and an honest result state (there is no test-result column yet).
- **Evidence:** `docs/v2/TEST_EVIDENCE.md` (V2-01 block); engine 1085 OK; desktop 334 pass; `tsc` clean.
- **No candidate was installed** for V2-01 â€” `C:\Users\Nick\KelV2Candidate` still does not exist.

## V2-02 notes for the next run

- **What exists now:** `Connections.test(id, credentials)` in `runtime/kel/connections.py` with
  `perform_request` as the single outbound choke point, migration 24 (`v20-connection-tests`) holding the
  last check's state/status/duration/sentence, the `test` action on `/api/connections`, the privileged
  `kel:connection-test` channel (sender-guarded; returns the record and never a value), and a
  `Test connection` button on the page.
- **The rule to keep:** nothing calls a service except a click on Test connection. V2-14's network rules
  belong inside `perform_request`; do not add a second HTTP client, and do not add network code to the
  renderer.
- **V2-03 starts from:** the eight personal services still need no code â€” a service is a Connection Nick
  adds, and what Kel can *do* with it is a tool (V2-04). What V2-03 adds is a real, live check against
  each service and the smallest useful action for each; nothing about the model should change to make
  that possible.
- **Evidence:** `docs/v2/TEST_EVIDENCE.md` (V2-02 block); engine 1101 OK; desktop 338 pass; `tsc` clean.
- **No candidate was installed** for V2-02 either, and no real service has been contacted by a test yet.

## V2-03 notes for the next run

- **What exists now:** `runtime/kel/connection_services.py` (the eight services as rows: address, header,
  how the credential is presented, docs, test endpoint, what to fetch, and how sure Kel is), `auth_prefix`
  on a connection (migration 25: `null` = Kel works it out, `''` = exactly as it is, a word = added in
  front), the `catalogue` action on `/api/connections`, and "Set up <service>" rows on the page that fill
  the form in.
- **The rule to keep:** a service is data. No module, table, worker or workflow per service, no branching
  on a service id, and `connections.py` must stay free of service names (a test pins that). Anything Kel
  *does* with a service is a tool â€” V2-04.
- **V2-04 starts from:** the Connection Framework and its three templates (API Key, OAuth, Bot/webhook),
  standardising credentials, authenticated requests, actions/tools, permissions, Test Connection, errors,
  retries and tests. The OAuth template is what Google Drive needs â€” its entry knows the address, but the
  account sign-in step does not exist yet, and its note says so. *(Superseded 2026-09-28: the sign-in step was built in V2-04b; Drive needs Nick's own Google OAuth client)* V2-14's network rules belong inside
  `perform_request` in `connections.py`.
- **Evidence:** `docs/v2/TEST_EVIDENCE.md` (V2-03 block); engine 1110 OK; desktop 340 pass; `tsc` clean.
- **Still not verified:** no installed-app check, and no real service has been contacted â€” that needs
  Nick's credentials and stays V2-15's evidence.

## V2-04 closed, and V2-05 notes for the next run

- **V2-04 is closed as the framework** â€” templates, one request path, data-declared actions, the
  confirmation gate, honest errors, bounded retries, the access history, and the developer page
  `docs/v2/CONNECTION_FRAMEWORK.md`. Two things it needs are carried as follow-ups in
  `FEATURE_LEDGER.md` instead of being claimed: **V2-04a** (a tool the assistant could call an action
  through â€” the bridge to the coding runtime the desktop agent runs; no Connections capability switch may
  be added before it exists) and **V2-04b** (the OAuth account sign-in flow).
- **V2-05 is the iPhone Kel PWA V1** (login, history, create/continue a conversation, text/paste, voice
  through Muse, Project switching and routing, home showing running/recent/failed work and Needs Your
  Attention, and answering/approving/denying/granting/reviewing/resuming/stopping â€” nothing else). The
  gateway it grows already exists: the web-host serves the same renderer away from the desktop
  (session-gated, server-side bearer), so V2-05 is about the PWA surface and its journeys, not a second
  backend. No uploads, camera, share sheet, push, or native apps.
- **Carry into V2-05:** the Connections work exposes `/api/connections` (list / get / save / remove /
  set_credential / delete_credential / test / run / actions / events / catalogue). If the PWA surfaces any
  of it, the mutating-confirmation rule and the one-request rule apply there too, and the credential stays
  in the shell â€” a remote client never receives a value.
- **Reconnaissance done (do not rebuild this):** installability already exists from the donor line and is
  sound â€” `desktop/public/manifest.webmanifest` (name/short_name/display standalone/theme + background
  colour, 192 and 512 icons), icons at `desktop/public/pwa/icon-180|192|512.png`, and a careful service
  worker at `desktop/public/sw.js` that never caches `/api/`, keeps script/style network-fresh with a
  content-type guard against the SPA fallback, is network-first for navigation, and is version-bumped with
  the old cache deleted on activate. It is registered by `renderer/services/registerPwa.ts`, which skips
  Electron and non-secure origins. V2-05's work is the *surface*, not this machinery; `desktop/tests/
  unit/pwa-install.test.ts` now pins the contract so it cannot quietly rot.
- **What the phone already reaches:** the web-host serves the same renderer (SPA fallback to index.html)
  with the engine behind `/kel/` (session-gated, bearer kept server-side). Routes that exist today:
  `/login`, `/guid`, `/conversation/:id`, `/work` (the Kel work center, which already renders attention
  rows), `/scheduled`, `/activity`, `/transcription`, `/providers`, `/connections`, `/team`, `/settings/*`.
- **So the real V2-05 increment is:** a mobile-first pass over those journeys (viewport and safe-area
  insets, touch targets, no desktop-only affordances), making the home screen's running/recent/failed work
  and Needs Your Attention usable one-handed with answer/approve/deny/grant/review/resume/stop, and voice
  through Muse from the phone on the existing transcription path. Verification is synthetic (a desktop
  browser at a phone viewport over the gateway) plus the installed-app tether check; real iOS Safari
  behaviour can only be confirmed by Nick â€” recorded in `KNOWN_LIMITATIONS.md`.
- **Layout audit done (so the next run does not go looking):** the shell already handles the notch and
  home indicator â€” `viewport-fit=cover` is declared in the renderer shell and `env(safe-area-inset-*)` is
  used in `styles/layout.css`, `styles/themes/base.css`, the guid page and the chat action sheet. The Kel
  surfaces' own CSS has no phone-breaking widths: `kel-tokens.css` contains one 132px element, one 560px
  max-width, and `min-width: 0` on the flex children (the pattern that stops a row overflowing). So the
  remaining V2-05 work is **not** a CSS rescue: it is the phone *journeys* â€” a home screen that shows
  running/recent/failed work and Needs Your Attention one-handed with answer/approve/deny/grant/review/
  resume/stop, and voice through Muse from the phone â€” and verifying them in a real browser at a phone
  viewport against the built app (which needs a build + the gateway, so it is its own increment, not a
  quick check).

## V2-05 send â€” closed; the phone sends for real (next: history, attention, routing)

- **The measured blocker is gone and the round trip is proved.** The phone profile had no assistant to
  choose because the `kel` assistant is seeded by the Electron main process (`initializeKel`) and the
  standalone `bun run webui` host never ran that path. The webui now performs the same integration at
  start-up (register the Kel ACP agent in **module form** â€” `python -m kel.acp_host`; the script-path form
  cannot resolve the ACP host's relative imports during `initialize` â€” create the single `kel` assistant,
  leave exactly it enabled). The desktop's source branch got the same module-form fix; its packed engine
  never hit this.
- **Journey H now proves the positive path** (real browser 393x852 â†’ gateway â†’ aioncore â†’ Kel engine
  (ACP) â†’ CLI model): one `kel` pill (auto-selected) â†’ send enables â†’ turn lands â†’ real reply ("Phone
  send check received.") â†’ settle â†’ second thumb-typed turn â†’ second reply ("still here"); post-auth
  watch clean (no failed reads, no dead sockets, no console errors). Evidence:
  `docs/v2/evidence/v2-05/` (findings-H.json, H1-H3 PNGs).
- **Write-ups a next run needs:** assistant replies render markdown inside a shadow root (`ShadowView`),
  so `innerText` cannot see them â€” read `.markdown-shadow-body` text explicitly; the conversation's send
  control read as disabled even when it accepted the next send (recorded, not gated on); a full-page load
  of `/conversation/<id>` on the phone rendered a blank body in one authed probe; tapping the home's
  recent entry text timed out once (try the drawer path first).
- **V2-05 remains open as:** (c) job-driven attention actions (real job state, no fixtures), (d)
  conversation history / the drawer from the phone above all, and conversational project routing.
  V2-04a/V2-04b remain the next deliberate program items per the directive priorities.
- **Evidence:** `TEST_EVIDENCE.md` (V2-05 third pass); desktop 358 pass (43 files); `tsc` clean; 4 new unit
  tests (`kel-integration.unit.test.ts`).

## V2-04a reconnaissance for the next run (source-backed; no code changed)

The assistant bridge's landing points, read from the tree:

- **The runtime's tools are not MCP.** The shipped coding runtime is Claude Code, invoked with
  `--strict-mcp-config --mcp-config '{"mcpServers":{}}'` (`runtime/kel/native.py:92`), and a test asserts
  no capability row speaks of MCP (`runtime/tests/test_capabilities.py:40`). The bridge must ride the
  existing capability/tool plumbing, not a second MCP server.
- **The capability layer already declares a tool surface.** `runtime/kel/capabilities.py` maps each
  capability to the runtime's real tool names (â‰ˆ43â€“52) and feeds `_TOOL_MAP` / `capability_for_tool`. Its
  docstring carries the binding rule this bridge flips: *"Google Drive and Connected apps are
  deliberately absent: this release has no production effect path that could honour them, so they are not
  offered as switches that could not be kept."* â€” the bridge lands first, the switch second.
- **The action side is data and ready to call.** `runtime/kel/connection_actions.py`: `actions()` (121),
  `actions_for(service_id)` (126), `action(action_id)` (132); the mutating rule sits in the module header
  (line 14: a mutating action is refused unless Nick confirmed â€” none ship yet). `runtime/kel/connections.py`
  owns schema/run/history (migrations incl. `_add_actions_table` 134; `ensure_schema` 149).
- **A mid-turn confirmation pathway exists.** `runtime/kel/acp_host.py` is poll-based
  (`Host(client, emit, poll_interval=.25)`: 156), emits `agent_message_chunk` (167), and already has
  `_resurface()` (188) â€” *"After an interruption, bring the active vetting prompts back into view"* â€” a
  user-prompt/vetting mechanism the bridge's confirmation can build on. `ServiceClient.call()` (129) is
  the engine transport (reads `desktop-session.json`).
- **Open questions the next run must answer before designing:** the direction of `_TOOL_MAP` (does the
  engine observe the runtime's tool calls or provide tools to it?), where Projects state lives for
  per-Project gating (V2-02), and how the access-history writer receives call facts (V2-04's
  connection/action/domain/status/duration shape).

## Parallel-ownership change (2026-09-21) â€” V2-05-history deferred for shell integration

Astra is actively implementing the Figma Shell on `ux/v2-shell` and now owns the phone drawer/history
presentation, the conversation shell, the composer, the responsive/mobile shell, Tools and Ramble/Kibble
presentation, and the global visual tokens. Implementing V2-05-history (the phone drawer and conversation
opening) now would collide with that work, so it is **temporarily deferred for shell integration**:

- **V2-05 stays PARTIAL.** Its history/attention/routing requirements are kept in this record and in
  `RESUME.md` â€” they are not dropped, and the phase is not marked complete.
- The measured notes for the history increment (the blank `/conversation/<id>` deep load, the inert rail
  at phone width, the home-entry tap timeout, the drawer as the phone's real navigation) remain valid;
  they are recorded in `KNOWN_LIMITATIONS.md` and stay the checklist for the Shell integration pass.
- **The next safe backend item is V2-04a** (assistant-callable Connection action bridge), whose
  reconnaissance is committed at `7a82996`. Do not start V2-05-history without a fresh recorded decision
  that the Shell integration has landed.
- If a backend change needs a renderer contract Astra will eventually absorb, write it in
  `docs/v2/PARALLEL_SHELL_TOUCHES.md` instead of editing renderer files.

## V2-04b â€” BUILT (2026-09-21)

The OAuth foundation is done: providers as data (`kel.connection_oauth`), the flow in `oauth_flows`
(migration 28 â€” single-use state + PKCE verifier, never a token), the trade through
`perform_request`, tokens in the same in-memory custody (`auth_state`/`auth_scopes`/`auth_expires`/
`oauth_provider` on the row in plain words), the shell claims a finished sign-in once into the
OS-backed custody, refresh on expiry (`needs_reconnect` when it fails), revoke through the provider.
The only public route is `/oauth/callback`, protected by the single-use state (D-34, D-35). Google
Drive is the reference (`gdrive-files`). Evidence: `docs/v2/evidence/v2-04b/README.md` â€” engine
suite 10/10 incl. a real-HTTP lifecycle with a real S256 PKCE check, desktop 363 passed, tsc clean.
Honest limits: real Google sign-in needs Nick's client ID + browser; the phone cannot finish a
sign-in yet (loopback callback); the sign-in between callback and claim lives in engine memory only.
`next_item` moves to Connection execution hardening, then routing intelligence.

## V2-04 hardening â€” BUILT (2026-09-21)

The choke point now carries its own rules (D-36): one opener built once; a bounded redirect chain;
a service's `Retry-After` honoured but capped; the V2-14 network-rule seam asked **before** anything
leaves the computer (and again for a redirect's host, failing closed when the rule source errors);
an answer past the reading cap labelled as cut short; and a choke-point refusal reaching the person
as its own sentence. Six new tests in `ExecutionHardeningTests` (all green). No rules are configured
yet, so behaviour is unchanged until V2-14 fills the seam. `next_item` moves to routing intelligence.

## V2-04a â€” BUILT and proved live (2026-09-21, `dev/v2` @ `d3bbf65`)

The assistant-callable Connection action bridge is done: the `connections` capability, the
`kel.connection_tools` bridge, the `kel.conn` helper the runtime runs as a shell command, engine
memory custody pushed by the shell (D-33), mutating confirmation through the existing approval rows
(D-32), and `source` provenance (migration 27). Evidence: `docs/v2/evidence/v2-04a/README.md` â€”
the engine journey (16 tests) plus the **live** run where a real runtime found the connector, called
`github-whoami`, used the bounded login, and the access history recorded `source: runtime`. The same
run measured two honest limits: Claude Code is quota-blocked on this machine today (codex carried
the work), and the phone's turns are conversational by design, so the bridge is reachable from the
phone only once the Shell's Work route exists (Journey J held, recorded in
`KNOWN_LIMITATIONS.md`). It also found and fixed a real defect: the engine now exports
`python -m kel` to its runtimes (`d3bbf65`). `next_item` moves to V2-04b (the OAuth foundation).

## V2-04 build notes (historical â€” the phase is closed)

- **Built:** `runtime/kel/connection_framework.py` (the three templates: labels, hints, credential field
  names, what a check does, plus the request policy's numbers) and bounded, honest retries inside
  `connections.perform_request` (retry a 429/5xx or a dropped connection; never a 401/403/404; bounded by
  the timeout and a budget; the record says how many tries). The renderer's own kind vocabulary was
  deleted â€” labels, hints and credential field names come with the list.
- **Not built, and not claimed:** (a) a chat tool that lets the assistant use a connection â€” the engine and
  the surface can run an action when Nick asks, but nothing in conversation can (now carried as follow-up
  V2-04a, and the reason no Connections capability switch exists yet); (b) the OAuth account sign-in step,
  which is what Google Drive needs (its catalogue note says so; carried as follow-up V2-04b). *(Superseded 2026-09-28: V2-04a and V2-04b are both built)*
- **Actions (built since the note above):** `runtime/kel/connection_actions.py` holds eight actions as rows
  over six services; `connections.run()` reads a row, makes the request through the single choke point,
  leaves the payload nowhere and records the fact of the call (domain, status, duration) in
  `connection_events` (migration 26); `events()` reads that history back. Every catalogue action is a read,
  and a `mutating` action is refused unless Nick confirmed. The page has a "What Kel can do" card.
- **If follow-up V2-04a is picked up:** expose an action as a tool the assistant can call â€” with the same
  permission rule (mutating actions ask first) and the same one-request rule â€” and keep V2-14's network
  rules inside `perform_request`. Add the capability switch only once that path can honour it.
- **Evidence:** `docs/v2/TEST_EVIDENCE.md` (V2-04 blocks); engine 1126 OK; desktop 344 pass; `tsc` clean.
- **Still not verified:** no installed-app check; no real service contacted; the retries are proven against
  a local stand-in only.

## Model preferences recorded at setup

- Nick works from the iPhone for chat, voice, status, approvals, Project routing and stop/resume (Â§5 of
  the directive); the desktop may remain on.
- Real dogfood feedback from the stable candidate outranks synthetic tests and can change priorities;
  every priority change is recorded in `DOGFOOD_FINDINGS.md`.
