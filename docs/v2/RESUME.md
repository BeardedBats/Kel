# RESUME — exact continuation

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

**Resume here.** Read `KEL_CANONICAL_HANDOFF.md`, `DECISIONS.md` D-53..D-72 and the three design docs
in `design/`. Verify with `cd desktop && bunx tsc --noEmit && bun run test` and
`cd runtime && python -m pytest tests -q`; build with `cd desktop && bun run package`. Nick may be using
the installed App: never touch `App` or `Data`; test on copies (see the worker brief pattern: copy Data,
run `App\Kel.exe` with `KEL_DATA_DIR`/`AIONUI_DATA_DIR`/`KEL_HOST_DATA_DIR`, `KEL_PROJECTS_ROOT` on a
scratch folder so no project lands in the real `Documents\Kel Projects` (General follows it;
`KEL_GENERAL_ROOT` overrides General alone), `AIONUI_MULTI_INSTANCE=1`, `KEL_BACKGROUND_WINDOW=1`).

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

[Task field rhythm](evidence/figma-full-audit/DESKTOP_TASK_FIELDS_SOURCE.md) now measures 600×614px at y70 in Dark/Light, 1440/800px. Label/field/prompt/gap metrics, unsaved Cancel/reopen, Dark Weekly and Light Advanced/Manual/Custom pass without overflow/errors. Light minimum sampled contrast 5.39:1. TypeScript/build and 12 focused tests pass. Two owned synthetic configuration records were removed after an enabled catalog probe failed; model choice is not accepted. Task icons/glass/disabled variants and live catalog remain open. Package with the next larger milestone; App 8c67121/Data untouched; mobile paused.

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

## Desktop reply actions checkpoint (2026-09-26)

## Desktop populated Chat type checkpoint (2026-09-26)

[Populated Chat type](evidence/figma-full-audit/DESKTOP_POPULATED_CHAT_TYPE_SOURCE.md) passes five list rows at 14px gaps, 13px/16px timestamps, 24px avatar slot/22×23 mark and last-turn wheel scroll at 1440/800px in Dark/Light. User alignment/390px width already matched. Native synthetic messages were journaled/restored; source legacy prefix intercepted. TypeScript/build and six focused tests passed. Full frame placement/rhythm/sidebar/footer facts remain open. Package by the next larger milestone. App/Data untouched; mobile paused.


## Desktop Light Ramble dialogs checkpoint (2026-09-26)

[Light Ramble dialogs](evidence/figma-full-audit/DESKTOP_RAMBLE_LIGHT_DIALOGS_SOURCE.md) pass API key, Merge and Vetting at 1440/800px with minimum sampled label contrast 4.76:1, zero overflow/errors. Key Cancel/reopen, radio/arrow controls and real preview rechecks passed. No key/merge/accept/process mutation occurred; owned synthetic recordings removed and saved transcript preserved. TypeScript/build and 14 focused tests passed. Package by the next larger milestone. App/Data untouched; mobile paused.


## Desktop Workspace header and Light surfaces checkpoint (2026-09-26)

[Workspace/Light source checks](evidence/figma-full-audit/DESKTOP_WORKSPACE_LIGHT_SOURCE.md) repair the legacy header/native-control overlap and narrow collapsed-panel width. Real titlebar collapse/reopen passed Dark/Light at 1440/800px. Light file tree, SCM tabs, heading menu, preview/code/status/action menu and read-only/split controls pass; 74 labels measured at least 5.39:1. TypeScript/build and 11 focused tests passed. Prior isolated panel preferences and Dark restored; no file mutation. Package by the next larger milestone. App/Data untouched; mobile paused.


## Desktop Setup retention checkpoint (2026-09-26)

[Setup retention](evidence/figma-full-audit/DESKTOP_SETUP_RETENTION_SOURCE.md) passes real isolated folder-draft write/reload, canceled picker, Work setup-return banner and Chat gate at 1440/800px. Prior client preferences/history restored; zero overflow/errors. TypeScript/build, seven focused tests and full 63-file/443-test regression passed. Native picker intercepted; no provider/job/authority change. Package proof waits for the next larger milestone. Autonomy selection still awaits Nick. *(Superseded 2026-09-28: settled by D-64, Full access with an Ask first switch)* App/Data untouched; mobile paused.


[Desktop reply actions](evidence/figma-full-audit/DESKTOP_REPLY_ACTIONS_SOURCE.md) now follow tool rows at 1440/800px in Dark/Light. Original-message clipboard handoff and real isolated reaction writes passed; prior reaction was restored. TypeScript/build and full 63-file/440-test regression passed. No provider/fork/tool execution ran. Package proof and broader populated Chat remain open; App/Data untouched.

## Desktop Chat plan and Light states checkpoint (2026-09-26)

[Desktop Chat plan/Light states](evidence/figma-full-audit/DESKTOP_CHAT_PLAN_LIGHT_STATES_SOURCE.md) pass tool/plan collapsed/expanded in Dark/Light and Light error/reconnecting at 1440/800px. Plan geometry and narrow current-step space are repaired. Minimum measured Light label contrast is 4.86:1; zero overflow/errors. Fourteen focused tests and source build passed. Legacy prefix and runtime states were intercepted/injected. Package proof, reply-action order, broader Chat/right-panel states remain open. App/Data untouched.

## Desktop Light dialogs checkpoint (2026-09-26)

[Desktop Light startup/shared dialogs](evidence/figma-full-audit/DESKTOP_LIGHT_DIALOGS_SOURCE.md) pass five states at 1440/800px with minimum measured label contrast 4.86:1, no overflow/errors, ten focused tests, and source build. Update/Delete geometry and stopped-engine surfaces are repaired. Startup/failure/update/task records were injected/intercepted. No restart/export/download/delete ran. Package proof remains open; App/Data remain untouched.

## Desktop Light menus checkpoint (2026-09-26)

[Desktop Light menus](evidence/figma-full-audit/DESKTOP_LIGHT_MENUS_SOURCE.md) pass six menus at 1440/800px, with zero overflow/clipping/errors. Minimum measured word contrast is 4.81:1; marks 4.76:1. Gradient-backed Accept and pixel-level icon contrast are excluded. Source build passed. Memory/catalog/native picker actions were intercepted; no live provider ran. Package proof waits for the larger milestone. App/Data remain untouched.

### Original heading: RESUME — exact continuation

## Desktop Kibble recovery / Light / Chat package checkpoint (2026-09-26)

[Milestone package](evidence/figma-full-audit/DESKTOP_KIBBLE_LIGHT_CHAT_MILESTONE_PACKAGE.md) at `0b49b56` passed 1440/800px bundled-renderer checks for Kibble recovery, Light menus/dialogs, Chat plan/reply actions, error and reconnecting. All 266 renderer files matched; zero renderer errors/overflow. Real isolated pointer/reaction writes passed and were restored; runtime/mission states and clipboard were injected/intercepted. No worker/provider/restart/export/download/delete ran. Broader Chat/right-panel and Light Workspace/icon states remain open. The next Setup increment is not in this package. Canonical App remains `8c67121`; Data untouched. Mobile paused.

Desktop first: complete populated Chat/right-panel and retained Tools/task and Light Workspace/dialog/icon states. Latest disposable package is `0b49b56`. Latest full desktop suite is 63 files / 443 tests. Canonical App stays `8c67121`; Data untouched. Mobile stays paused. Autonomy selection awaits Nick; Pet enable needs AUD-MINOR-008; live services need credentials. *(Superseded 2026-09-28: Autonomy is settled by D-64 and the Pet is removed by D-56; live services still need credentials)*

## CURRENT FIGMA REVISION (2026-09-25, `main`)

The live Kel Figma now uses desktop page `319:2` with 75 frames and mobile page `319:3858` with 50 frames. The old FINAL pages and most old frame IDs no longer resolve. [The current inventory](evidence/figma-full-audit/FIGMA_REVISION_2026-09-25.md) records the replacement IDs. All older Figma parity screenshots are **SUPERSEDED BY FIGMA REVISION** until compared with current frames. The canonical App still packages `8c67121`; do not cite it as proof for the new revision. Current Tools, Chat/drawer, approval, tool-call/plan, error, reconnecting, mobile model picker, mobile approval details, populated Transcriptions, mobile Ramble list/detail/vetting, mobile Projects, mobile Work empty state, mobile Activity running state, and mobile Permissions empty state have linked scoped package checks in the inventory.

**Next item:** Desktop first: implement populated Kibble, current setup and setup-still-open states, then Pet off/settings and remote sign-in presentation. Current runtime dialogs and Ramble need one larger milestone package. Finish remaining populated variants and Light-mode labels before canonical App promotion. Keep mobile paused. Pet enable needs Nick’s AUD-MINOR-008 decision. *(Superseded 2026-09-28: the Pet is removed (D-56))* Desktop context inspection is 75/75; accepted parity remains scoped.

[Desktop Ramble](evidence/figma-full-audit/DESKTOP_RAMBLE_CURRENT_REVISION.md) now has current 1440/800px source evidence for its transcript, connected-key replacement input, Merge list, and Vetting modal. Real isolated merge and preview rechecks passed; new recordings were cleaned up and the saved vetting transcript remained unchanged. TypeScript/source build, 35 runtime transcription tests, four transcription-policy tests, four Ramble DOM tests, and the final 60-file/428-test desktop suite passed. [Desktop Figma context inspection](evidence/figma-full-audit/DESKTOP_CURRENT_AUDIT_COVERAGE.md) covers 75/75 current frames; this is not accepted parity. Canonical App stays 8c67121, Data is untouched, and mobile stays paused.

[Desktop Update available and task delete confirmation](evidence/figma-full-audit/DESKTOP_SHARED_DIALOGS_SOURCE.md) pass source checks at 1440/800px. Update uses actual versions/release notes and existing download authority. *(Superseded 2026-09-28: the updater and its dialogs are removed (D-56))* Delete now uses the Figma modal; Keep/Escape and intercepted deletion handoff passed. TypeScript, source build, and three update-policy tests passed. Stopped-engine inner surface styling was corrected and rechecked. These changes await the next larger package. Canonical App and Data remain untouched. Current desktop context coverage is 66 READ / 9 PENDING; READ does not mean complete parity.

[Combined desktop milestone](evidence/figma-full-audit/DESKTOP_COMPLETION_MILESTONE_PACKAGE.md) passed packaged 1440/800px checks at `f8e6d86`: Work, Permissions, Knowledge, saved recipes, and chat menus. [Starting, stopped engine, and diagnostics export](evidence/figma-full-audit/DESKTOP_RUNTIME_VIEWS_SOURCE.md) now pass source checks at both widths. Real isolated restart and sanitized local export passed. TypeScript, source build, 17 runtime diagnostics tests, and the final 60-file/427-test desktop suite passed. These latest runtime views await the next larger package. Canonical App remains `8c67121`; durable Data was untouched.

---

## CURRENT CANONICAL CHECKPOINT (2026-09-24, `main`) — supersedes candidate checkpoints below

Consolidation is complete at `docs/CONSOLIDATION_STATUS.md`. The only source is `C:\Users\Nick\Desktop\Kel\Kel` on `main`; `App`, `Data`, and `Tools` are its siblings. The installed app now packages source `8c67121`. The r61 System and r62 Appearance evidence is in `evidence/figma-full-audit/`; old rXX candidate locations and separate V2 data roots have been removed. Do not recreate them for ordinary development.

V2-00 through V2-04, V2-06 through V2-14, and V2-17 are built. V2-05, V2-16, V2-18, and V2-19 remain partial. V2-15 and V2-20 remain planned. The first local source increment after consolidation fixed two measured V2-18 state defects: cancelled Build Update missions report `CANCELLED` with no candidate, and requests answered without a job settle as `SETTLED`. A follow-up corrected Kibble's candidate readout to use the engine's nested `evidence.verified` and `artifact_location`. The canonical App now includes these source changes.

**Next item:** audit the remaining populated desktop Tools, chat, task, and transcript states against paired FINAL frames. Measure Light-mode label contrast. The canonical App at `8c67121` passed packaged 1440/800 checks for the failed-status glass popover and enabled Image Model with disposable data ([record](evidence/figma-full-audit/DESKTOP_TOOLS_STATUS_CANONICAL.md)). An isolated WebUI run reached step 2; its local page returned 200 and its unauthenticated API returned 401. Pet enabling was refused by V1.6 policy AUD-MINOR-008. The full engine regression passed 1,289 tests and 14 subtests; desktop tests passed 396. The long Tools diagnostic still covers the heading at 800px. Exact product-wide parity is open. Live personal services, remote first response, Google sign-in, fresh Muse speech, and a physical iPhone need separate acceptance.

---

## CURRENT INTEGRATION CHECKPOINT (2026-09-24, r59) — supersedes r57 below

`integration/v2` has pushed desktop Dark source `96d2b5d55185d5ec0bc112132c82ba7edac4932e`. The latest staged candidate is `C:\Users\Nick\KelV2Candidate.r59` (archive `40CD6EB857BACC1D`). [The r59 record](evidence/v2-19/CANDIDATE_R59.md) has hashes, typecheck, package and archive gates, packaged Model checks, process ownership, and limits. [The desktop comparison](evidence/figma-full-audit/DESKTOP_MODEL_R59.md) matches FINAL `188:1327` at 1440px, checks 800px, and repairs Add Model fields and error messages against Components. r58 remains a preserved intermediate. The r59 test tree was stopped after ownership checks; only the protected stable engine remained. Recheck ownership before stopping any process.

**Next action:** compare desktop Dark System and Appearance field states with FINAL and Components. Continue bounded V2-19 regression on an isolated candidate. Preserve the stable app, any live r20 session, shortcuts, rollback copies, and Astra's branch. Exact product-wide Figma parity remains open. Google sign-in, live services, remote model response, fresh Muse audio, and physical iPhone checks remain pending for access or hardware. Keep faint Light-mode labels and phone layout work outside this pass. `request_review` was unavailable; no independent review occurred.

---

## CURRENT INTEGRATION CHECKPOINT (2026-09-24, r57) — supersedes r54 below

`integration/v2` has pushed desktop Dark source `cafe10e32abcf53f4d65ca00fb9814c4f44865c8`. The latest staged candidate is `C:\Users\Nick\KelV2Candidate.r57` (archive `8BFB8503A4433668`). [The r57 record](evidence/v2-19/CANDIDATE_R57.md) has hashes, build and archive gates, packaged WebUI checks, process ownership, and limits. [The desktop comparison](evidence/figma-full-audit/DESKTOP_WEBUI_R57.md) matches FINAL `188:2240` at 1440px and checks 800px. It repairs the step strip, first-step copy, card spacing, and Dark username/password overlays. r55 and r56 remain preserved intermediates. The r57 test tree was stopped after ownership checks; only the protected stable engine remained. Recheck ownership before stopping any process.

**Next action:** compare the next desktop Dark Settings overlay and field state with Components. Continue bounded V2-19 regression on an isolated candidate. Preserve the stable app, any live r20 session, shortcuts, rollback copies, and Astra's branch. Exact product-wide Figma parity remains open. Google sign-in, live services, remote model response, fresh Muse audio, and physical iPhone checks remain pending for access or hardware. Keep faint Light-mode labels and phone layout work outside this pass. `request_review` was unavailable; no independent review occurred.

---

## CURRENT INTEGRATION CHECKPOINT (2026-09-24, r54) — supersedes r51 below

`integration/v2` has desktop Dark source `58a0533a3d66e183775c7d756c00d3cc91eadd88`. The latest staged candidate is `C:\Users\Nick\KelV2Candidate.r54` (archive `817B0DE3D6342942`). [The r54 record](evidence/v2-19/CANDIDATE_R54.md) has hashes, typecheck, package and archive gates, packaged chat checks, process ownership, and limits. [The chat comparison](evidence/figma-full-audit/DESKTOP_CHAT_R54.md) matches a populated desktop fixture against FINAL `185:1050`. It repairs timestamp format, numbered-list rhythm and color, and the three reply actions. r52 and r53 remain preserved intermediates. The r54 test tree was stopped after ownership checks; only the protected stable engine remained. Recheck ownership before stopping any process.

**Next action:** compare desktop Dark WebUI and populated Settings overlays with FINAL and Components. Fix measured gaps, then continue bounded V2-19 regression on an isolated candidate. Preserve the stable app, any live r20 session, shortcuts, rollback copies, and Astra's branch. Exact product-wide Figma parity remains open. Google sign-in, live services, remote model response, fresh Muse audio, and physical iPhone checks remain pending for access or hardware. Keep faint Light-mode labels and phone layout work outside this pass. `request_review` was unavailable; no independent review occurred.

---

## CURRENT INTEGRATION CHECKPOINT (2026-09-24, r51) — supersedes r47 below

`integration/v2` has desktop Dark source `56df3742ca6d9734f1771230d0dbee05e2874300`. The latest staged candidate is `C:\Users\Nick\KelV2Candidate.r51` (archive `F564D5B2C876612B`). [The r51 record](evidence/v2-19/CANDIDATE_R51.md) has hashes, typecheck, package and archive gates, packaged 1440/800/768px desktop checks, process ownership, and limits. [The scoped polish record](evidence/figma-full-audit/DESKTOP_POLISH_R51.md) compares populated Scheduled tasks and Diagnostics with FINAL frames and the New task dialog with Components. It repairs desktop row dividers, instruction copy placement, narrow desktop rails, Dark task fields, and opaque select popups. r47–r50 remain preserved; no candidate was renamed or promoted. The r51 test tree was stopped after path checks. The final process list showed only the protected stable engine; the earlier r20 PID was absent. Recheck ownership before stopping any process.

**Next action:** continue a bounded desktop Dark comparison on chat, Settings controls, and populated overlays. Use matched Figma and packaged captures before editing. Preserve the stable app, any live r20 session, shortcuts, rollback copies, and Astra's branch. Exact product-wide Figma parity remains open. Google sign-in, live services, remote model response, fresh Muse audio, and physical iPhone checks remain pending for access or hardware. Keep faint Light-mode labels and phone layout work outside this pass. `request_review` was unavailable; no independent review occurred.

---

## PREVIOUS CHECKPOINT (2026-09-24, r47) — superseded by r51

`integration/v2` has desktop Dark source `54ce43fa08295799cddb0101816369e22d872bd2`. The latest staged candidate is `C:\Users\Nick\KelV2Candidate.r47` (archive `B216B4FB082DD3B6`). [The r47 record](evidence/v2-19/CANDIDATE_R47.md) has hashes, typecheck, 296 desktop tests, package and archive gates, and packaged 1440/800px desktop checks. [The scoped polish record](evidence/figma-full-audit/DESKTOP_POLISH_R47.md) shows matched Tools and Transcriptions before/after captures. MCP rows now use Figma's 40px desktop rhythm; Add MCP fits at 800px; the embedded Transcriptions route opens the newest saved item. No phone layout work occurred. Exact product-wide Figma parity is **not** established. r46 remains preserved; no candidate was promoted or renamed. The r47 test tree was stopped after path checks. The final process list showed only the protected stable engine; the earlier r20 PID was absent. Recheck ownership before stopping any process.

**Next action:** continue desktop Dark comparison on populated Scheduled tasks, chat, Providers, and Diagnostics. Repair measured token, text, alignment, and control gaps. Preserve the stable app, any live r20 session, shortcuts, rollback copies, and Astra's branch. Google sign-in, live services, remote model response, fresh Muse audio, and physical iPhone checks remain pending for access or hardware. Keep faint Light-mode labels and phone layout work outside this pass. `request_review` was unavailable; no independent review occurred.

---

## PREVIOUS CHECKPOINT (2026-09-23, r46) — superseded by r47

`integration/v2` has UI source commit `70248659853d71e2b97a07ccc16b165526b6636f`. The latest staged candidate is `C:\Users\Nick\KelV2Candidate.r46` (archive `1E6ACC2F412CB977`). [The r46 record](evidence/v2-19/CANDIDATE_R46.md) has hashes, 295 desktop tests, typecheck, package and archive gates, 23 post-setup phone routes, and populated Tools, Scheduled, chat, and Ramble evidence. It fixes the saved Ramble mobile detail found in r45. [The full Figma audit](evidence/figma-full-audit/README.md) retains all 51 screen pairs and exact remaining gaps. Exact UI parity is **not** established. r44/r45 are preserved intermediates. No promotion or rename occurred. The r46 test tree was stopped after path checks. The final process list contained only the stable engine; the earlier r20 PID was absent. Recheck ownership before stopping any process.

**Next action:** compare populated desktop Scheduled tasks, Transcriptions, Tools, and chat with FINAL frames. Repair confirmed copy, icon, alignment, and component-state gaps, then package only after a source change. Keep any live r20 and the stable app protected. Google sign-in, live services, remote model response, fresh Muse audio, enabled WebUI/Pet, and physical iPhone checks remain pending for access or hardware. The web-host suite needs all Kel instances stopped. Keep faint Light-mode labels outside this Dark pass. `request_review` was unavailable; no independent review occurred.

---

## PREVIOUS CHECKPOINT (2026-09-23, r43) — superseded by r46

`integration/v2` has pushed UI source `8bde9aa`. The latest staged candidate is `C:\Users\Nick\KelV2Candidate.r43` (archive `65F4C64D927A9ACB`). [The r43 record](evidence/v2-19/CANDIDATE_R43.md) contains hashes, 295 desktop tests, typecheck, package and archive gates, and measured mobile WebUI and Pet checks. [The full Figma audit](evidence/figma-full-audit/README.md) pairs 23 desktop FINAL and 28 mobile screens. r43 builds on r41's Model/System and r39's About/Archived/Skills/notices fixes. Exact UI parity is **not** established. r42 is a preserved intermediate candidate. r20 and stable remain protected. No promotion or rename occurred.

**Next action:** use a disposable populated profile for chat, tasks, recordings, Tools, and menu states. Compare these against paired FINAL frames, then fix measured copy, control, and spacing differences. Preserve r20, stable data, shortcuts, rollback copies, and Astra's branch. Google sign-in, live services, remote model response, fresh Muse audio, and a physical iPhone remain pending for access or hardware. The web-host suite needs all Kel instances stopped. Keep faint Light-mode labels outside this Dark pass. `request_review` was unavailable; no independent review occurred.

---

## PREVIOUS CHECKPOINT (2026-09-23, r41) — superseded by r43

`integration/v2` has pushed UI source `ea054bf`. The latest staged candidate is `C:\Users\Nick\KelV2Candidate.r41` (archive `6C670D7ADE06C5C8`). [The r41 record](evidence/v2-19/CANDIDATE_R41.md) contains hashes, 295 desktop tests, typecheck, package and archive gates, phone Model/System/Pet checks, backup/restore dialogs, and 23 post-setup phone routes without overflow or redirect. [The full Figma audit](evidence/figma-full-audit/README.md) pairs 23 desktop FINAL and 28 mobile screens. r41 builds on r39's About, Archived, Skills Hub, and notices fixes. Exact UI parity is **not** established. r40 is a preserved intermediate candidate. r20 and stable remain protected. No promotion or rename occurred.

**Next action:** use a disposable populated profile for chat, tasks, recordings, and menu states. Compare these against their paired FINAL frames, then fix measured Tools, WebUI, Pet height, row, copy, and component differences. Preserve r20, stable data, shortcuts, rollback copies, and Astra's branch. Google sign-in, live services, remote model response, fresh Muse audio, and a physical iPhone remain pending for access or hardware. The web-host suite needs all Kel instances stopped. Keep faint Light-mode labels outside this Dark pass. `request_review` was unavailable; no independent review occurred.

---

## PREVIOUS CHECKPOINT (2026-09-23, r39) — superseded by r41

`integration/v2` has pushed UI source `61db8d5`. The latest staged candidate is `C:\Users\Nick\KelV2Candidate.r39` (archive `F2C73B0B58B4C158`). [The r39 record](evidence/v2-19/CANDIDATE_R39.md) contains hashes, 295 desktop tests, typecheck, package and archive gates, and a fresh packaged Dark UI pass. [The full Figma audit](evidence/figma-full-audit/README.md) pairs 23 desktop FINAL and 28 mobile screens with package captures. r39 closes the mobile About, Archived, Skills Hub, and notices gaps in addition to r33's frame, theme rows, sheet, and lightbox. Exact UI parity is **not** established. r34–r38 remain intermediate candidates. r20 and the stable app remain protected. No promotion or rename occurred.

**Next action:** use a disposable populated profile for chat, tasks, recordings, and menu states. Compare these against their paired FINAL frames, then repair confirmed copy, control, and spacing differences. Preserve r20, stable data, shortcuts, rollback copies, and Astra's branch. Google sign-in, live services, remote model response, fresh Muse audio, and a physical iPhone remain pending for access or hardware. The web-host suite needs all Kel instances stopped. Keep faint Light-mode labels outside this Dark pass. `request_review` was unavailable; no independent review occurred.

---

## PREVIOUS CHECKPOINT (2026-09-23, r33) — superseded by r39

`integration/v2` has pushed UI source `c6d47ea`. The latest staged candidate is `C:\Users\Nick\KelV2Candidate.r33` (archive `D3978ED3254C3256`). [The r33 record](evidence/v2-19/CANDIDATE_R33.md) contains its full hashes, 295-test suite, typecheck, archive gate, packaged sheet and lightbox clicks, 23-route phone sweep, and process ownership. [The full Figma audit](evidence/figma-full-audit/README.md) pairs all 23 desktop FINAL frames and 28 mobile frames with package captures, and checks Foundations and Components. Exact UI parity is **not** established; use its screen rows as the gap list. r30–r32 were failed intermediate candidates. r20 and the stable app remain protected. No promotion or rename occurred.

**Next action:** build a disposable populated profile for chat, task, transcript, and overlay states. Compare each against its paired FINAL frame, then repair confirmed copy, control, and spacing differences. Preserve live r20, stable data, shortcuts, rollback copies, and Astra's branch. Google sign-in, live services, remote model response, fresh Muse audio, and a physical iPhone remain pending for access or hardware. The web-host suite cannot run while r20 remains live. Keep faint Light-mode labels outside this Dark pass. `request_review` was unavailable; no independent review occurred.

---

## PREVIOUS CHECKPOINT (2026-09-23, r29) — superseded by r33

`integration/v2` has pushed source `41b2bf6`. The latest staged candidate is `C:\Users\Nick\KelV2Candidate.r29` (archive `6ae8b552e6cf1676`). [`CANDIDATE_R29.md`](evidence/v2-19/CANDIDATE_R29.md) records the repaired blank Recent title; packaged local conversation opening (median 112.4 ms); two disposable project contexts (switch median 114.9 ms); two native picker adjustments in one open popup; Dark Settings at 1440/800/390; and the 294-test desktop suite. r20 and stable remain protected. No promotion or rename occurred. Read r29, r28, r26, and r23 records before changing or packing.

**Next action:** obtain a signed-in isolated candidate session for remote load, first response, Google sign-in, and live service checks. Fresh Muse audio and a physical iPhone still need their inputs. The web-host suite needs all Kel instances stopped and therefore cannot run while r20 remains live. V2-20 promotion stays gated; do not rename a candidate while r20 runs. Keep faint Light-mode labels outside this Dark pass. No independent review occurred because `request_review` was unavailable.

---

## PREVIOUS CHECKPOINT (2026-09-23, r28) — superseded by r29

`integration/v2` has pushed source `6b81ffa`. The latest staged candidate is `C:\Users\Nick\KelV2Candidate.r28` (archive `f6d8620cdd33c42a`). [`CANDIDATE_R28.md`](evidence/v2-19/CANDIDATE_R28.md) records the visible map actions, narrow Connections and Projects tables, r26–r28 packaged checks, archive gate, and isolated journeys. r20 and stable remain protected. No promotion or rename occurred. Read r28, r26, and r23 records before changing or packing.

**Next action:** measure V2-16 conversation-open and project-switch against fully loaded content where accessible, then continue bounded V2-19 on an isolated r28 root. Keep remote and live service claims pending without account access. Test a second native colour-picker adjustment when native control is available. Keep faint Light-mode labels outside this Dark pass. Fresh Muse audio and physical iPhone checks still need their inputs. No independent review occurred because `request_review` was unavailable.

---

## PREVIOUS CHECKPOINT (2026-09-23, r26) — superseded by r28

`integration/v2` in `C:\Users\Nick\Desktop\Kel\kel-v2-integration` has pushed source `c0391b6`. The latest staged candidate is `C:\Users\Nick\KelV2Candidate.r26` (archive `5749e1a92cc25837`). `docs/v2/evidence/v2-19/CANDIDATE_R26.md` records the recipe and Work fixes, the refreshed frozen engine, packaged UI checks, archive gate, and five isolated journeys. Read it and `CANDIDATE_R23.md` before changing or packing anything. r23–r26 test processes are stopped. The user's r20 session and protected stable app remain running. No promotion or rename occurred.

**Next action:** continue V2-19 on an isolated r26 root with packaged Projects/Knowledge/Map, Kibble, Connections, Permissions, and transcription actions. Record exact UI and engine outcomes; fix reproduced defects. Then measure V2-16 conversation-open, project-switch, and remote paths where accessible. Keep Light-mode faint labels outside the Dark pass. The second native picker adjustment remains unverified. Google sign-in, live services, fresh Muse audio, and physical iPhone checks stay pending until their inputs are available. `request_review` was unavailable; no independent review occurred.

---

## PREVIOUS CHECKPOINT (2026-09-23, r23) — superseded by r26

`407f5a3` produced the staged r23 candidate (archive `1c3bde1f4ab0b162`). Its packaged setup and Dark Settings pass, archive gate, 294 desktop tests, typecheck, and first V2-19 navigation pass are in `docs/v2/evidence/v2-19/CANDIDATE_R23.md`.

---

## PREVIOUS CHECKPOINT (2026-09-23, night) — superseded by the r23 integration checkpoint

**Where:** `integration/v2` in `C:\Users\Nick\Desktop\Kel\kel-v2-integration` @ **`fe6edec`**
(pushed): `8117742` = the F1 repair, `ea7de07` = Astra's Figma refresh merged in.

**F1 is fixed at the source.** The packaged `--webui` branch handed `startWebHost` the *store*
directory while the engine writes `desktop-session.json` into its own root
(`KEL_DATA_DIR || appData/kel-desktop/work`), so `/kel/*` never reached an engine and every Kel
surface rendered its failure card. Now `KelService` exports the one resolver (`kelDataRoot()`) and
the WebUI passes it as `kelDataDir`; the gateway's explicit failures (503 `KEL_ENGINE_UNAVAILABLE`
when the descriptor is missing, 502 when the engine is not listening) are pinned by
`kel-gateway.unit.test.ts`, so `/kel/api/*` can never answer SPA HTML. The same branch now honours
`AIONUI_DATA_DIR` for the WebUI's own store.

**Merged:** `ux/v2-figma-refresh` @ `ea7de07` (dark V2 layouts, dark settings empty states,
Assistants + Skills settings — Nick confirmed those belong in Settings). Astra's branch is untouched.

**Verified this checkpoint:** the five affected V2-18 journeys all **PASS** on the V2 test root
(`docs/v2/evidence/v2-18/runs/2026-09-23-r17-f1-repair.json`): J-WORK, J-RECOV, J-ATTN, J-RECIPE,
J-ACTIVITY. Candidate **r16** is preserved and verified (`88f34373…`); an **r17 pack from `fe6edec`
was still running when this block was written** — it will be installed only after the archive gate
passes *and* it launches on isolated data, and its hashes plus the packaged re-checks (engine,
gateway JSON, isolated roots, Work/Projects/Recipes/Activity/Kibble, dark Settings, phone width,
V2-16 numbers) go into `docs/v2/evidence/CANDIDATE_R17.md`. Until that file exists, **r17 is not a
candidate** and r16 is the one to use.

**Do not** promote, install over the stable app, or touch `C:\Users\Nick\KelDogfoodCandidate` /
`C:\Users\Nick\KelDogfoodRuns\prepared`. The stable engine may stay running; stop only this line's
own stacks (candidate apps, V2 engines, gateways).

---

## PREVIOUS CHECKPOINT (2026-09-22, evening) — superseded by the block above

**Where the work is:** `C:\Users\Nick\Desktop\Kel\kel-v2-integration` on `integration/v2`. The commit
that carries this block is the checkpoint (the one before it is `8cdefd0`).

**The candidate exists and launches.** `C:\Users\Nick\KelV2Candidate` holds the complete unpacked
runtime; `Run-Kel-V2-Candidate.cmd` in that folder starts it on the isolated data root
`C:\Users\Nick\KelV2Runs\prepared\candidate` (it exports `KEL_DATA_DIR`, then `Start-Process`es
`Kel.exe`; it never touches the stable install or the stable data root). Verified on the packaged app:
window titled **Kel**, its own engine
(`…\KelV2Candidate\resources\kel-engine\KelEngine.exe --data C:/Users/Nick/KelV2Runs/prepared/candidate`),
its own `aioncore`, its own `kel.sqlite3`, shutdown and relaunch intact.

**Measured and repaired this checkpoint** (evidence: `docs/v2/evidence/V2_05_DEEPLINK_RETENTION.md`,
`ASAR_PACK_DEFECT.md`):
- deep-link destination retention through sign-in (link → sign-in → that conversation → refresh) —
  the destination is now remembered in `sessionStorage` because the history entry that carried it was
  replaced during the session check;
- a deep link to an unknown conversation now says so on the route (Arco `Result` + the id) instead of
  toasting and silently replacing the route with home;
- the loopback-only local password recovery and the remote-refusal boundary (30 web-host tests);
- `J-WORK` and `J-RECOV` PASS with the corrected action semantics, plus a new pin that a FAILED
  request recovers through `/api/retry` once with no duplicate work
  (`tests/test_v2_attention.py`, 18 tests with the long-run fencing suite).

**Before copying any future pack:** run `python C:\tmp\verify_asar.py` (minimum archive check:
manifest parses, renderer bundles present, `out/main/index.js` + `out/renderer/index.html` byte-identical
to the build). The pack produced a corrupt archive twice today (`ASAR_PACK_DEFECT.md`); never extract
archive entries into a source checkout — use `C:\tmp\…`.

**Open, in this order:** (1) when the SPA believes it is signed in while the session is gone, protected
calls 401 and the app can land on home instead of the sign-in gate (the gate itself now remembers the
destination) — the trigger is the stale session state; (2) the browser/phone flows that were not yet
exercised on the packaged build (recipe run + reopen its result, attention resolution, Build Update
progress in the UI); (3) the V2-19 bounded regression groups and the remaining V2-16 numbers on the
integration branch; (4) a physical iPhone pass stays separately pending.

**Processes:** the stable engine (`KelDogfoodCandidate`, pid 26544) must keep running untouched; the V2
dev engine and the candidate app are stopped unless the checkpoint that follows says otherwise.

---

1. Work in `C:\Users\Nick\Desktop\Kel\kel-v2` on branch `dev/v2` (shared object database lives in
   `Kel-Repo\.git`; never clone, never touch `main`).
2. Read `docs/v2/MARATHON_DIRECTIVE.md`, then `docs/v2/MARATHON_STATE.md`, then this file.
3. Reconcile git (`git status`, `git log --oneline -3`, `git worktree list`); preserve any coherent
   uncommitted work you find — do not reset, discard, stash or restart it.
4. Continue the exact `next_item` from `MARATHON_STATE.md` — now **V2-18 synthetic V2 acceptance
   journeys, IN PROGRESS**: the checklist is `docs/v2/evidence/v2-18/ACCEPTANCE_MATRIX.md` and the
   executable journeys are `runtime/tools/acceptance_journeys.py` (it attaches to an engine only after
   proving the recorded pid is alive, its command line names the data root, and the recorded port is
   owned by that pid — `desktop-session.json` is a file, not a fact). Start one owned engine with the
   desktop's protection set:
   `KEL_PROTECTED_PATHS='C:\Users\Nick\KelDogfoodCandidate;C:\Users\Nick\KelDogfoodRuns\prepared'
   python -m kel.service --data C:/Users/Nick/KelV2Runs/prepared/engine` (from `runtime/`), then
   `python tools/acceptance_journeys.py --root <root> --journeys <ids> --out <evidence json>`.
   **State at this checkpoint (2026-09-22, `dev/v2` @ `492b9a0` + `7b18618`):** V2-06, V2-07 and
   V2-08 are BUILT (D-50) — attention rows, the recipe library's own surfaces (migration 30
   `v2-recipe-library`) and `/api/activity` — and the journeys J-FIX, J-UPGRADE, J-SEC, J-KBU
   (C1–C4 + negatives), J-PROJ, J-MEM, J-NET, J-CONN, J-TRANS, J-CONV, J-MODEL, J-RECIPE and
   J-ACTIVITY have all PASSED on the real root (evidence under `docs/v2/evidence/v2-18/runs/`).
   **Remaining unchecked journeys: none that a backend can reach.** J-WORK, J-RECOV, J-ATTN and
   J-REMOTE all PASSED on 2026-09-23 (slice 5, `runs/2026-09-23-slice5-r3.json`); what is left of §27
   needs Shell integration (Astra: phone/renderer) or Nick's real credentials/Muse audio, and is never
   claimed from a backend journey. Two measured limits are recorded in `KNOWN_LIMITATIONS.md` instead of
   passes: real work settles `UNCERTAIN` here because the reviewer answers nothing usable, and a request
   that produces no job stays `DISPATCHED` with no job. The web-host deep-link cause is fixed and pinned
   (`packages/web-host/src/static-server.unit.test.ts`, 15 tests on the merged line). The integration
   line `integration/v2` @ `fe5e6b7` in `C:\Users\Nick\Desktop\Kel\kel-v2-integration` merges Astra's
   committed Shell baseline `ux/v2-shell` @ `0052075` (verified from the merge's second parent; the rest
   of this file's line list is unchanged); its renderer suites (`desktop/tests/**`, `tsc`)
   and a packaged candidate are **not** verified yet — `desktop/node_modules` there is a junction and
   needs a real `bun install`. See `docs/v2/evidence/integration/README.md`.

   **NEXT ACTION, in order:** (1) the three remaining backend journeys on a fresh owned engine;
   (2) `bun install` in the integration worktree, then its bounded renderer suites; (3) package a
   candidate at `C:\Users\Nick\KelV2Candidate` — the path does not exist yet, so nothing has to be
   preserved or rolled back, and installation stays behind Nick's explicit decision.
   **DONE on the integration line this turn (`integration/v2` @ `3f8e1de`):** `bun install
   --frozen-lockfile` + the production renderer build ran *there*; **J-WORK, J-RECOV and J-ATTN all
   PASSED** on an engine started from that worktree's `runtime/` (evidence
   `docs/v2/evidence/v2-18/runs/2026-09-22-slice5|6|7.json`); the gateway's local password recovery
   was repaired (loopback-only, 17 web-host tests pass) and browser-verified (deep link → 302 →
   `#/conversation/<id>`, sign-in loads the shell, refresh keeps the session).
   **THE EXACT CONTINUATION:**
   (a) the candidate pack was still running when the turn ended:
   `cd C:\Users\Nick\Desktop\Kel\kel-v2-integration\desktop` then
   `AIONUI_BACKEND_LOCAL_BUNDLE_DIR="C:/Users/Nick/KelDogfoodCandidate/resources/bundled-aioncore/win32-x64"
   NODE_OPTIONS="--max-old-space-size=8192" node scripts/build-with-builder.js auto --skip-native`
   → the app lands in `kel-v2-integration\dist\package-r12\win-unpacked` (this was the second
   attempt; `--pack-only` skips the distributable entirely — that mistake is recorded). When it
   finishes: copy the unpacked app to `C:\Users\Nick\KelV2Candidate` (absent at the time of
   writing; preserve anything unknown) and launch `Kel.exe` with isolated V2 data to verify the
   packaged runtime, then record the exe path;
   (b) rebuild the renderer (`bun run package`) and re-check the **destination retention** fix in the
   browser (sign-in should now return to the deep link; measured NOT retained before the fix, root
   cause = `ProtectedLayout`'s guard dropping the location);
   (c) then the remaining verification: `desktop/tests/**`, a browser phone-viewport pass, V2-19
   bounded regression, V2-16 timings.
   **PROCESSES LEFT RUNNING (recorded):** the V2 engine on `C:/Users/Nick/KelV2Runs/prepared/engine`
   (owned; identity proven) and the candidate pack (background session `9a8bpdrh`). The gateway on
   port 33100 was stopped with its aioncore child.
   **PASSED (2026-09-22):** J-FIX, J-UPGRADE, J-SEC, J-KBU (claims C1–C4, including a real codex-code
   repair inside the isolated `repositories/<job_id>` copy and a candidate whose revision has the
   baseline as an ancestor), and the negatives (a cancelled mission claims nothing; a mission whose
   tests can never pass never claims a verified build — D-49). **THE NEXT UNCHECKED JOURNEY IS
   J-MODEL** (drive one real turn, then read the stored route back through `/api/model {action:'why'}`
   and assert the sentence matches the stored decision), then in order J-WORK, J-MEM, J-RECIPE,
   J-ATTN, J-RECOV, J-NET, then the labelled fixtures J-CONN and J-TRANS. Phone/renderer journeys stay
   PENDING for Shell integration. Read `ROADMAP.md`'s V2-18 line and the directive before designing;
   do not build Astra-owned presentation. **Kibble Build Update is BUILT**

   (D-46 corrected D-44; D-47; `docs/v2/evidence/kibble-build-update/README.md`): the mission and
   candidate contract on the existing machinery, `promote()` always refusing, the UI contract recorded
   in `PARALLEL_SHELL_TOUCHES.md`. **V2-17 upgrade reliability, V2-14 network permissions, V2-13
   isolation, V2-12 staffing, V2-11 long-running work, V2-10 learning, V2-09 routing, V2-04b and the
   V2-04 execution hardening are BUILT** (D-34…D-49; evidence under `docs/v2/evidence/`) — do not
   rebuild them. V2-15 needs Nick's real dogfood batches (his Kibble feedback arrives only after
   integrated V2 testing — never block synthetic acceptance on it); V2-16 is largely renderer/Shell;
   V2-19/V2-20 are whole-system phases whose promotion gate is Nick's.
   **V2-05-history is temporarily DEFERRED
   FOR SHELL INTEGRATION** — Astra owns the
   phone drawer/history presentation on `ux/v2-shell`, and implementing it now would overlap; V2-05
   stays PARTIAL and items (c)/(d) below remain requirements, not removed. The phone surface, the PWA
   contract, the gateway blocker, **mobile voice** (real browser → gateway → engine → Muse, the
   transcript landing in the composer) and **send** are done and evidenced in
   `docs/v2/evidence/v2-05/README.md`; what remains, in order:
   (a) **browser voice — done.** `KelMicButton` now uses the shared `kelRequest` transport (preload on the
       desktop, the `/kel` gateway in a browser) and never swallows a failed `stream_start`. Keep both
       properties if you touch it again. Follow-up only: multi-utterance dictation (see
       `KNOWN_LIMITATIONS.md`).
   (b) **send with a model connected — done.** The real blocker was the profile, not the composer: the
       `kel` assistant was seeded only by Electron main (`initializeKel`), so the standalone `bun run
       webui` profile had no assistant the guid page could select and send could never enable (measured:
       zero pills while `/api/assistants` answered). `bun run webui` now performs the same bootstrap
       (`packages/web-host/src/kel-integration.ts`), and the ACP agent registers in module form
       (`-m kel.acp_host` — the script-path form cannot resolve the host's relative imports during
       `initialize`; the desktop source branch got the same fix; packed engines never hit it). Journey H
       proves the round trip: one `kel` pill (auto-selected) → send enables → real reply → settle →
       second turn → second reply ("still here"), post-auth watch clean. Keep both properties if you
       touch either.
   (c) **job-driven attention actions on the phone** — approvals, grants, resume, stop and review need
       real job state; create it honestly (no fixture providers) and exercise the phone's offers.
   (d) **conversation history from the phone — DEFERRED for shell integration (Astra owns the phone
       drawer/history presentation).** The drawer that lists history was not opened in this increment,
       and a full-page load of `/conversation/<id>` rendered a blank body in one authed probe (measured).
       Tapping the home's recent entry text timed out once — try the drawer path first. Pick this up only
       after the Shell integration lands (see `MARATHON_STATE.md`, parallel-ownership section); the
       requirement is kept, not dropped.
   The Connections program (V2-01 … V2-04) is closed; V2-04a (the assistant bridge) and V2-04b (the
   OAuth sign-in flow) are both built and evidenced (`docs/v2/evidence/v2-04a/README.md`,
   `docs/v2/evidence/v2-04b/README.md`) — do not rebuild them; a real Google sign-in still needs
   Nick's own client ID and a browser visit.
5. Per increment: understand → narrow design → implement → self-review → focused tests → commit
   atomically → update durable state (`MARATHON_STATE.md`, `FEATURE_LEDGER.md`,
   `IMPLEMENTATION_STATUS.md`, `TEST_EVIDENCE.md`, `DECISIONS.md`, and `DOGFOOD_FINDINGS.md` when real
   feedback lands) → continue to the next dependency. Do not stop at a clean checkpoint.
6. Run the real thing the way this increment did (no CSS reasoning): engine at
   `C:\Users\Nick\KelV2Runs\prepared\engine`, renderer via `bun run package`, gateway via
   `bun run webui` with `KEL_DATA_DIR` + `AIONUI_STATIC_DIR`, then
   `bunx playwright test tests/e2e/kel-mobile.e2e.ts` with `KEL_DEV_PASSWORD` (mint one with a direct
   loopback POST to `/api/webui/reset-password` on the backend port — `bun run resetpass`'s fast path
   goes through the session gate and 401s, measured).
   Kill the gateway by PID when restarting it — a stopped session left the first one listening and the
   old code kept answering (that cost a full diagnosis cycle).
   Verify with **bounded groups**, never the monolithic run, and record exactly which groups passed on
   the final code (the groups V2-09 used are listed in `docs/v2/evidence/v2-09/README.md`). Inspect
   listener and process ownership before stopping anything — the engine's pid is in the data root's
   `desktop-session.json` — and stop only this run's stack; Astra's worktree processes stay untouched.

Guard rails: `C:\Users\Nick\KelDogfoodCandidate` and `C:\Users\Nick\KelDogfoodRuns\prepared` are
protected (never install/clean/modify them); V2 test data goes to `C:\Users\Nick\KelV2Runs\prepared`;
install `C:\Users\Nick\KelV2Candidate` only when a checkpoint genuinely needs installed-app
verification.
