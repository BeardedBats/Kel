# Kel - User Journey History

Permanent ledger of user-journey defects, their fixes, and the rule each one created or satisfied.
Rules live in `USER_JOURNEY_STANDARD.md`. Hard rule: **every fixed UX defect either maps to an existing
`JR-n` rule or creates a new one** - so the same class of defect cannot ship twice.

Record shape: `Problem found → Concrete fix → Generalized lesson → Rule (created/updated) → Regression evidence`.

**Batch 1 status (2026-09-16):** committed on branch `ux/v15-journeys`; every item below carries an explicit
verification line. The Settings-sider expansion was attempted, crashed at render, and was **reverted before
commit** — see open item O8.

---

## V1.5 - first journey pass (2026-09-16, branch `ux/v15-journeys`)

Baseline subject: frozen V1.5 (`v1.5.0` / `5e76b21`), audited by driving the packaged app as a user.
Baseline evidence: `docs/product/evidence/v15-ux-fixes/baseline/` (raw runs also at
`Kel/ux-audit/runs/{fresh,seeded3}`). Fixed-build evidence: `.../fixed/` (+ `Kel/ux-audit/runs/fixed3`).

### H1 - Setup ended somewhere you cannot type (blocker) → JR-1
- **Problem:** completing the 5-step onboarding landed on `/work` ("0 jobs...", composer absent); only
  *skipping* landed in chat. A fresh user's first screen after setup had nowhere to type.
- **Fix:** `pages/kel/onboarding/index.tsx` - both finish paths now `navigate('/guid')`.
- **Lesson:** setup must end at the moment of first usefulness (the composer), never at a browsing surface.
- **Rule:** JR-1 (created), JR-2.
- **Evidence:** baseline `runs/fresh/ux-first-run.json` (`hashAfterOnboarding: #/work`, `timeToComposerMs: null`)
  → fixed `runs/fixed3/ux-first-run.json`.

### H2 - Onboarding spoke infrastructure (high) → JR-4
- **Problem:** step 2 listed providers with "Queued · quota not reported · installed not authenticated";
  step 4 said "scope/grant/guardrails/Agents"; step 5 showed "Engine: 1.5.0 · Providers registered: 4
  (none healthy yet) · Locked guardrails: loaded" and a guardrail digest.
- **Fix:** onboarding copy rewritten in plain language (Connect a model / "ready, usage not reported" /
  "needs you to sign in"; "Rules that are always on"; "Kel 1.5.0"; "No model is connected yet - you can add
  one anytime in Settings › Providers"); raw auth modes and digests removed from the flow.
- **Lesson:** onboarding may name the model and the decision; it must never expose the registry.
- **Rule:** JR-4, JR-5.
- **Evidence:** baseline vs fixed `ux-first-run.json` onboarding step texts.

### H3 - Kel can go silent, and nothing says why (release blocker) → JR-8/9
- **Problem:** with no usable model, two chat messages produced **no reply, no error, no guidance**; a work
  request in chat surfaced only a raw "Kel work: READY / UNCERTAIN" activity row; "0 usable right now" lived
  only on the Providers page.
- **Fix:** new `KelProviderNotice` banner on the chat landing (same "usable" rule as the Providers page:
  `healthy|quota`) with one action → Providers; palette job hints humanized; Work `WAIT_REASON` text documents
  waiting states in human words ("Waiting for an available model - Kel will continue automatically.").
- **Lesson:** if Kel cannot answer, the chat itself must say what happened and what to do - silence is a defect.
- **Rule:** JR-8, JR-9 (release blocker), JR-10.
- **Evidence:** baseline `runs/seeded3/ux-compose-*.json` (user messages with no assistant reply; raw activity
  rows) → fixed `runs/fixed3/ux-maintext.json` (`/guid` shows the banner text). See open item O1.
- **Verified (rebuilt build):** `/guid` renders “None of your connected models is available right now, so Kel will
  wait instead of guessing.” with an **Open Providers** action (`fixed/ux-maintext.json`).

### H4 - The Work list contradicted itself; UUID titles; a fabricated timestamp (high) → JR-11/12
- **Problem:** header read "0 jobs in this project · 0 waiting on you" while "Continuation" listed two parked
  jobs titled by raw job UUID; rows said "verdict: UNCERTAIN · durable state only - no hidden reasoning"; the
  Jobs table "Updated" column rendered `Date.now()` for every row (always "now"); an empty state rendered next
  to a non-empty section.
- **Fix:** counts now `${jobs} active · ${continuation} waiting to continue · ${waiting} need you`; continuation
  titles fall back to the job's own request text; verdict labels are words ("not verified yet"); resume line in
  plain language; empty state only when both lists are empty; `formatWhen(job.updated ?? null)`; extended
  `WAIT_REASON`; "workers" → "specialists".
- **Lesson:** every count and timestamp must be derived from the same data as the list under it; never
  synthesize "now".
- **Rule:** JR-11, JR-12, JR-17.
- **Evidence:** baseline vs fixed `ux-tour.json` `/work` main text.
- **Verified (rebuilt build):** `/work` reads `0 active · 2 waiting to continue · 0 need you`, titled by the task
  text (no UUIDs), with “verdict:” and “durable state only” gone (`fixed/ux-tour.json`, `fixed/ux-maintext.json`).

### H5 - Primary navigation carried configuration (high) → JR-14
- **Problem:** six primary entries; Team (assignments, role templates, role editor), Providers (model
  matrices, credential forms) and Diagnostics (engine metrics, orphan candidates) are configure/review
  surfaces; "Autonomy" was an abstract name for permissions.
- **Fix:** primary nav = **Work, Projects, Permissions** (`KelNavEntries.tsx`); Providers/Team/Diagnostics now
  live in the Settings sider under an "Advanced" group; System settings got a "System" group; page title and
  palette label renamed to Permissions; routes unchanged so deep links and the palette still reach everything.
- **Lesson:** primary navigation is for verbs; if a surface's main verb is "configure", it belongs to Settings.
- **Rule:** JR-14, JR-15, JR-19.
- **Evidence:** baseline `ux-tour.json` navClicks (6 entries) vs fixed; fixed `ux-settings.json` sider items.
- **Verified (rebuilt build):** the primary sider renders `New Chat / Work / Projects / Permissions`; the removed
  nav entries are absent; the Permissions page title and count verify (`fixed/ux-sider.json`, `fixed/ux-maintext.json`).
  The Settings-sider half (Providers/Team/Diagnostics/System entries) is **incomplete** — see H6 and O8.

### H6 — Orphaned settings pages and donor remnants (high) → JR-20 / JR-30
- **Problem:** System, About, WebUI and Pet existed with **no entry point** (including real user settings:
  language, start on boot, notifications, work directory); WebUI copy said “Let the butler set it up”; About
  carried donor links (AionUI wiki/releases, x.com/WailiVery, aionui.com).
- **Attempted fix:** settings-sider expansion (Providers/Team/Diagnostics/System) + WebUI string replaced
  (“Set up secure remote access”).
- **Outcome:** the sider expansion **crashed at render** (`TypeError: Cannot read properties of undefined
  (reading 'id')`) because the donor shell keeps a second registry (`SettingsPageWrapper.tsx`) that does not know
  the new ids. The change was **reverted before commit**; the WebUI string change is committed but was not
  visually re-verified (the settings surface crashed in the verification build). About stays URL-only.
- **Lesson:** a settings entry is not added until **every consumer** of the registry knows it — and the journey
  harness's `settings` scenario (non-empty sider, zero console errors) is the gate that catches this class.
- **Rule:** JR-20 (open), JR-30 (created).
- **Evidence:** fixed `ux-settings.json`/`ux-maintext.json` capture the crash (`consoleErrors: ["TypeError…"]`,
  empty sider list); see open item O8 for the exact next step.

### H7 - Command palette spoke machine (medium) → JR-23
- **Problem:** palette header "Run a command or jump to a surface"; hints "job center", "live assignments",
  "role templates", "leases and guardrails"; raw job states in hints; "Loading engine results...".
- **Fix:** "Search or jump to..."; human hints ("jobs and what needs you", "who is working", "connect a model",
  "what Kel can access"); job-state label map for hints; "Loading...".
- **Lesson:** search chrome is primary UI and carries the same plain-language bar as navigation.
- **Rule:** JR-23.
- **Evidence:** baseline vs fixed palette option/hint capture.
- **Verified (rebuilt build):** palette label “Search or jump to…”, hints “jobs and what needs you”, “connect a
  model”, “what Kel can access”; Enter → `/projects/knowledge`; Escape closes (`fixed/ux-palette.json`, `fixed/ux-sider.json`).

### H8 - A live control looked disabled and failed AA contrast (medium) → JR-25
- **Problem:** the assistant chip "Kel" on the chat landing rendered at `opacity-75` → measured **2.72:1**
  (AA needs 4.5:1 for 13px), reading as a disabled control.
- **Fix:** inactive chips use the full secondary tone with hover emphasis (and the overflow "More" button
  likewise).
- **Lesson:** an unselected-but-interactive control is not "disabled"; it still owes AA contrast.
- **Rule:** JR-25.
- **Evidence:** baseline `ux-readability.json` offenders → fixed `ux-readability.json`.
- **Verified (partial):** providers/projects/work/settings-appearance now measure zero offenders < 4.4; the two
  assistant-chip classes were changed. One 13 px “Kel” element on `/guid` **still measures 2.72:1** in the fixed
  build — its exact element is not yet identified (open item O10).

### H9 - Groups named by UUIDs; the project named "default" (medium) → JR-17
- **Problem:** the conversation workspace group header displayed `7c2c2250-291f-4f13-9c62-83edf8fe44f4`;
  the Projects header displayed "default".
- **Fix:** `getWorkspaceDisplayName` maps UUID-shaped directory names to "Workspace"; the default project is
  shown as "General" (Projects header and onboarding step 3).
- **Lesson:** identifiers are not names - every group/label users read must be a name or a generic word.
- **Rule:** JR-17.
- **Evidence:** baseline vs fixed sider/main text captures.
- **Verified (partial):** the UUID no longer appears (`uuid-visible: false`), but the label currently renders the
  raw i18n key `conversation.workspace.unnamedSpace` because the locale entry was not added before the batch
  stopped (open item O9). The Projects header and onboarding step 3 show “General” correctly.

### H10 - Duplicate action on the Project map (low) → JR-29
- **Problem:** "Refresh map" rendered twice (card action + empty-state action).
- **Fix:** card action only when a map exists; the empty state keeps its single action.
- **Rule:** JR-29.
- **Evidence:** baseline vs fixed `ux-maintext.json` `/projects/map`.
- **Verified (rebuilt build):** the map empty state shows exactly one “Refresh map” action (`fixed/ux-tour.json`,
  `fixed/ux-maintext.json`).

### H11 - The progress line argued with the user's own effort (medium) → JR-31
- **Problem:** after answering a whole batch, including `not sure` and `skip`, the line still read
  "Recorded: 10 of 12" — the counter counted only strict answers, so the user's work looked unfinished
  and the "process answers" prompt never appeared.
- **Fix:** progress counts *recorded* (handled) states — answered, unsure, needs-examples, awaiting
  visual, skipped, deferred — while the spec keeps strict answered coverage. Shown as
  "Recorded: 12 of 12 recorded.".
- **Lesson:** a counter that disagrees with what the user just did is a lie; counters must count what
  the user handled, and specs must keep the strict number.
- **Rule:** JR-31 (created).
- **Evidence:** `runtime/tests/test_vetting.py::RapidAnsweringTests::test_rapid_answering_ten_plus_without_synthesis`.

### H12 - One interruption path forgot to bring the prompts back (medium) → JR-32
- **Problem:** during a vetting session, an unrelated question whose planning *failed* exited the reply
  path before the resurface hook — the user's open questions silently disappeared from the screen
  (they were still in the session, but nothing on screen said so).
- **Fix:** the resurface hook now runs on every normal-path exit — dispatched replies, terminal jobs,
  and failed/interrupted planning.
- **Lesson:** every exit path of a conversation turn is a user-visible path; guidance attached to "the
  normal path" must be attached to all of them, including failures.
- **Rule:** JR-32 (created).
- **Evidence:** `test_vetting.py::VettingChatPathTests::test_interruption_answers_normally_and_prompts_come_back`
  (fails against the pre-fix host; passes after).

### H13 - The product advertised commands the engine rejected (medium) → JR-33
- **Problem:** the vetting batch footer told users to type `explain 12` and `challenge 12`, but the
  control parser matched only "explain simply" / "challenge this"; the advertised commands fell
  through as unmatched chat.
- **Fix:** the control patterns accept the numeric forms the UI advertises; unit tests now parse every
  advertised command in its advertised form.
- **Lesson:** a hint the parser doesn't accept is a silence defect (JR-9 family) — every advertised
  command needs a parse test.
- **Rule:** JR-33 (created).
- **Evidence:** `test_vetting.py::HelpTests` (three tests, one per advertised help command).

### H14 - A new engine route was invisible to the whole UI (high) → JR-34
- **Problem:** in the packaged app the vetting panel always showed its start form even though a live
  session existed. The renderer bridge (`process/services/kel/KelService.ts`) whitelists route names
  for `kel:request`; `/api/vetting` was missing, so every panel call threw "Unknown Kel action" and the
  panel's catch left the view empty. The engine and the chat path had worked the whole time — proven by
  the session, answers, conflict, greyboxes and spec snapshot in the engine database, and by the full
  alternating transcript in the donor's own store.
- **Fix:** added `vetting` to the bridge whitelist; the same live scenario now shows the panel session
  (topic, FINISHED, recorded progress, decisions, spec preview).
- **Lesson:** a route exists only when *every* consumer can reach it — engine action, renderer call,
  and the main-process bridge whitelist. Grep the whitelist whenever a surface is added.
- **Rule:** JR-34 (created).
- **Evidence:** `paneldump` run (drawer showed the start form, no response recorded) → bridge fix →
  `b2-vetting-live` (panel booleans true); `docs/vetting/evidence/live/`.

### H15 - The settings registry listed 2 of 10 tabs (medium) → JR-30
- **Problem:** `BUILTIN_TAB_IDS` — the ordered list both the settings sider and `SettingsPageWrapper`
  map over — contained only `appearance` and `archived` while both presentation maps defined ten tabs;
  the settings nav rendered a two-item shell and extension tabs anchored to the other ids silently fell
  to "unanchored".
- **Fix:** the registry now holds the full ordered set (model, agent, skills, tools, appearance, webui,
  pet, system, archived, about) with the single-registry rule stated in the file; the browser filter
  for desktop-only tabs is unchanged.
- **Lesson:** a registry that lists only part of reality is worse than duplication — consumers look
  correct while rendering a fraction of the product.
- **Rule:** JR-30 (applied).
- **Evidence:** `settings` scenario on the rebuilt package (`b2-settings`): every tab visits clean,
  zero console errors.

### H16 - The workspace label rendered a raw translation key (low) → JR-17
- **Problem:** `getWorkspaceDisplayName` called `t('conversation.workspace.unnamedSpace')`, but the
  namespace bundles resolve `workspace.*` (the sibling `temporarySpace` key lives at
  `conversation.json` → `workspace.temporarySpace`), so unnamed workspaces surfaced as a raw key.
- **Fix:** the helper resolves both key paths and never returns a raw key (falls back to the
  product-visible literal); the key was added next to its sibling in the conversation bundle for
  en-US and zh-CN (and to the common bundle for the full-path callers).
- **Lesson:** every `t()` key the code calls must exist in the namespace the caller actually uses, or
  the fallback must be the product-visible string.
- **Rule:** JR-17 (applied).
- **Evidence:** `sider` scenario (`final-sider`): the workspace group label reads "Workspace",
  no raw key in `siderText`.

### H17 - Dark-mode chip failed contrast; the probe mis-read SVG paint (medium) → JR-25
- **Problem:** the inactive assistant chip painted `text-t-secondary` (#4E5969 — pinned to light values
  in this colour scheme) on the dark base: 2.72:1 at 13px. The readability probe also flagged the
  white-on-black Kel logo as 1:1 because it measured CSS `color` on SVG `<text>` instead of `fill`.
- **Fix:** the chip paints with the theme-aware `--aou-9` token (light #262c41 / dark #e5e7f0); the
  probe measures `fill` for SVG text and no longer stringifies `SVGAnimatedString` class names.
- **Lesson:** a token that is not redefined per theme silently inherits light values in dark mode; and
  a measuring tool that guesses the paint source reports phantom defects — fix the tool and the
  product.
- **Rule:** JR-25 (applied).
- **Evidence:** readability runs (`b2-readability`, `final-readability`, `final3-readability`): the
  packaged app reports zero offenders on `/guid`; the earlier 2.72:1 entry is gone
  (`evidence/v15-ux-fixes/fixed2/readability`).

### H18 - The composer's speech button was a donor dead end (medium) -> JR-35/JR-9
- **Problem:** the chat composer reserved its speech slot for the donor's browser-speech control,
  which depends on a network speech service and fails silently in packaged builds - a control that
  looks live and does nothing (the JR-9 family of defects).
- **Fix:** the slot now hosts Kel's own microphone (`KelMicButton`) wired to `/api/transcription`:
  recording state with a stop square, label and timer, explicit Cancel, Escape to cancel, and a
  transcript that lands in the composer as editable text.
- **Lesson:** a control that cannot work in the shipped runtime is worse than no control; replace it
  with the product's own path instead of porting the donor's.
- **Rule:** JR-35 (created), JR-9.
- **Evidence:** packaged E2E `transcription` (runs/transcription{,2}): `composerRecording=true`,
  `composerText` non-empty, `composerCleared=true`, zero console errors.

### H19 - Dictation must never become an accidental message -> JR-36
- **Problem (risk removed):** with voice input, auto-send turns every misheard word into a committed
  chat message; the program brief makes editable-before-send the default.
- **Design:** the composer mic inserts text (appending to what is already there); the Transcription
  page's "Send to chat" hands the text over through a one-shot draft the composer consumes and
  clears; nothing in the feature sends on the user's behalf.
- **Lesson:** machine-written text is a draft until the user acts; the composer is the review step.
- **Rule:** JR-36 (created).
- **Evidence:** E2E `composerText` + `composerCleared`; `GuidPage` draft-consumption effect.

### H20 - Provider machinery stays one sentence away from the user -> JR-37
- **Problem (risk removed):** transcription invites endpoint/model/websocket vocabulary into the UI;
  the donor showed key handling in a settings sheet and errors as raw reasons.
- **Design:** the page shows one plain status ("Practice mode" or "Muse (Meta)") with a single
  "Source" entry; every failure is one plain sentence (microphone denied/busy/missing, unreadable
  file, provider rejection); no provider term appears in any surface copy.
- **Lesson:** providers are implementation; the interface speaks about the user's recording, not the
  vendor's protocol.
- **Rule:** JR-37 (created).
- **Evidence:** `docs/transcription/10_KNOWN_LIMITATIONS.md` copy table; E2E `invalid-copy` and mode
  label assertions.

---

## Open items (recorded, not fixed in this pass)

| # | Item | Why open | Rule |
|---|---|---|---|
| O1 | Happy-path chat/work/approval journeys (J-2/3/4 live) | No usable provider on this machine (codex quota exhausted; others unauthenticated). Re-run `ux-audit.cjs ... compose` once a model is connected. | JR-8/9 verification |
| O2 | About page donor links; WebUI/Pet donor pages remain (URL-only) | Needs product-owned equivalents or removal with an approved plan. | JR-20 |
| O3 | Migrated installs see onboarding once (flag-only rule) | Needs a previous-install signal; measured cost is one click ("Skip setup"), re-entry point not implemented. | JR-3 |
| O4 | Conversation "Files / Changes" tab title `acp-temp-<id>` | Donor conversation shell; id should be replaced with the workspace folder name. | JR-17 |
| O5 | Diagnostics maintenance actions lack confirmations/explanations ("Purge...", "Compact...", "Problems: N recorded process(es)...") | Advanced surface; low priority, one pass does not cover it. | JR-8 |
| O6 | Settings pages show two "Back to Chat" affordances and a theme toggle in the footer | Donor shell; cosmetic, but a JR-21 violation. | JR-21 |
| O7 | Provider notice shows on the chat landing but not inside an open conversation | Requires a conversation-level mount; follow-up. | JR-9 |
| O8 | ~~Settings registry listed 2 of 10 tabs~~ **Fixed & verified in batch 2 (H15)** - `BUILTIN_TAB_IDS` is the single full registry both consumers derive from; `b2-settings` visits every tab with zero console errors. | - | JR-30 |
| O9 | ~~Workspace group label renders the raw key~~ **Fixed & verified in batch 2 (H16)** - `getWorkspaceDisplayName` resolves both namespace paths and never returns a raw key; keys added to the conversation and common bundles. | - | JR-17 |
| O10 | ~~13px Kel at 2.72:1~~ **Fixed & verified in batch 2 (H17)** - the chip paints with the theme-aware `--aou-9` token; the readability probe measures SVG fill and no longer reports the logo false positive. | - | JR-25 |

---

## Process (permanent)

1. Run the journey harness (packaged build, fresh + seeded roots) before tagging any release.
2. Every defect found is written here with a rule id (existing or new) **before** the fix lands.
3. Regression evidence is archived under `docs/product/evidence/<release>/` (JSON + key screenshots).
4. Rules change only with a history entry; silently dropping a rule is not allowed.
