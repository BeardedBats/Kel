# Kel — User Journey Standard

Permanent release checklist for Kel's user-facing experience. Every release must pass this checklist before it can be called "simple to use". Rules have stable IDs; defects map to rules, and every fixed defect either matches an existing rule or creates a new one (see `USER_JOURNEY_HISTORY.md`).

North star: **One extraordinarily capable assistant that is simple to talk to and easy to navigate.**
Core law: **Expose goals, work, results, and decisions. Hide machinery behind progressive disclosure.**

Provenance: distilled from the V1.5 real-user journey audit (`UX_AUDIT_V1.5.md`, 2026-09-16) and the donor simplicity matrix (`UX_DONOR_SIMPLICITY_MATRIX.md`).

---

## 1. Landing and first run

**JR-1 — The composer is the landing.** After onboarding (completed or skipped) the user lands on the chat composer. Work and other surfaces are destinations, never the default. Verify: finish onboarding → hash is the chat route and a text input is visible within 1s.
**JR-2 — Useful work within moments.** From launch, a fresh user can send a message without configuring anything. Non-blocking notices (e.g. "no model connected yet") may be shown, but the composer must accept input. Verify: fresh profile → composer reachable in ≤ 3 interactions.
**JR-3 — Returning users are not re-onboarded.** A profile with existing conversations is treated as onboarded (flag auto-set), even if the flag is absent (upgraded installs). Onboarding must remain re-openable from Settings for anyone who wants it.

## 2. Onboarding content

**JR-4 — No infrastructure vocabulary in onboarding.** Onboarding may mention "model", "connect", "your project", and "what Kel may do on its own". It must not show engine versions, registration counts, health states, quotas, "scope/grant/guardrails/agents/leases", or raw provider statuses. Verify: scan every onboarding step's visible text.
**JR-5 — Skippable at every step, with honest consequences.** A visible "Skip setup" on each step; skipping goes to the composer (never a dead end). Completing setup states plainly where the user will land next.

## 3. Chat surface (the primary experience)

**JR-6 — Where to type is unmistakable.** The composer is visible, centered, and the largest control on the chat surface. Placeholder text is plain and complete (no typewriter truncation of meaning). No provider/model/worker controls appear in the default view except one quiet model indicator.
**JR-7 — One assistant voice.** Replies read as one assistant. No engine/worker/agent/lease vocabulary in messages or message chrome. Internal activity rows ("Kel work: …") use human language and expose machine detail only behind "Details".

## 4. Failure and waiting states (highest severity rules)

**JR-8 — Failures are four-part answers.** Every failure or blockage states, in order: (1) what happened, (2) whether Kel is handling it, (3) whether the user must do something, (4) what happens next. Raw exceptions/states stay behind "Details".
**JR-9 — Silence is a defect.** If Kel cannot answer or run (no usable model, no route, quota exhausted, missing auth), the chat must say so within 30s with a next step (e.g. "Open Settings → Providers"). A message that produces no reply and no explanation is a release blocker.
**JR-10 — Waiting work is self-explanatory.** Queued/parked work shows a human status ("Waiting for an available model"), the user's own words as the item title (never a UUID), and an explicit resume path.

## 5. Work surface

**JR-11 — Work speaks in user decisions.** Headings and states use plain words (queued, running, waiting for you, done, needs review, stopped). "Verdict/continuation/milestone/lease/claim" never appear in the default view.
**JR-12 — Counts never contradict the list.** Summary lines (e.g. "0 jobs in this project") must be consistent with what is rendered below them.
**JR-13 — Waiting-on-you is first.** Anything that needs a user decision is ordered first and visually distinct; recency is the tiebreak (attention-ordered lists).

## 6. Navigation structure

**JR-14 — Primary navigation is for doing; Settings is for configuring.** Primary nav contains only surfaces a user acts in day to day: chat/new chat, Work, Projects, and one place for decisions Kel must ask for (Permissions). Providers, Team/roles, Diagnostics, system/about are configuration → Settings. Rule of thumb: if the surface's main verb is "configure", it lives in Settings.
**JR-15 — Every configuration page is reachable.** No settings route may exist without a visible entry point (settings sider, or a link from the surface that needs it).

## 7. Vocabulary and identity hygiene

**JR-16 — No machinery nouns in primary UI.** Ban list for primary surfaces: lease, scope, guardrail, digest, routing, milestone, verdict, continuation, claim, worker, agent (as a noun for Kel's helpers in primary copy), engine version strings, job UUIDs, contract hashes, absolute paths. Advanced pages may use precise terms; primary pages must translate.
**JR-17 — Human labels for human things.** Titles come from the user's words (first line of their request, conversation title), never raw ids. Workspace/group labels are readable names, not UUID directories. Tabs like "Files/Changes" must not be suffixed with internal ids.
**JR-18 — Permissions in human language.** Permission moments say what access is needed and why ("Kel needs access to this folder to finish the task"), with the three decisions in plain words: Allow once / Allow for this project / Deny. Leases/scopes/policy explain themselves only under Details.
**JR-19 — "Autonomy" is presented as Permissions.** The user-facing name is **Permissions** (what Kel may do). Route may remain `/autonomy` internally.

## 8. Settings hygiene

**JR-20 — No orphaned or duplicate pages.** Every settings page has an entry point; every entry point has exactly one target; duplicates (double back buttons, repeated actions) are defects. Donor remnants (unrelated brand names, "butler", pet/game surfaces, third-party support links) must not ship.
**JR-21 — "Back to chat" exists once per settings page.** One obvious way out of settings; theme controls live in Appearance, not in the settings footer.

## 9. Search, palette, and findability

**JR-22 — Find by meaning.** Users can find previous work without knowing Kel's storage model: conversations searchable (title/message), plus work/knowledge/recipes/roles via the palette. Search scope is stated in plain words.
**JR-23 — Palette language is plain.** Palette title/hints use user words ("Jump to…", "Jobs", "Saved knowledge"), not internals. Palette shows at most one section of fixed "Go to" rows, and dynamic sections (jobs/knowledge/recipes/roles) must not drown it.
**JR-24 — Keyboard contract.** Ctrl+K opens the palette; `/` opens search; typing filters; Enter runs the top visible result; Escape closes without side effects. All verified keyboard-only.

## 10. Readability and accessibility

**JR-25 — Primary text ≥ 13px, AA contrast.** Body/nav text ≥ 13px; 12px only for secondary meta, and only at ≥ 4.5:1 contrast (large text ≥ 3:1). No primary label under 13px.
**JR-26 — Focus and skip.** Skip-to-content is the first tab stop with a visible focus ring; focus outline is visible (≥2px, ≥3:1) on every interactive element; Escape closes overlays; the app is fully operable without a mouse.
**JR-27 — Scroll truth.** No primary content clipped without an affordance; scrollable regions show they scroll; long pages collapse advanced sections.

## 11. Empty states and duplicates

**JR-28 — Empty states teach.** Every empty surface answers: what is this, what will appear here, how to make it happen — in one or two plain sentences (and at most one primary action).
**JR-29 — One action, one place.** No duplicated primary buttons on a surface (e.g. two "Refresh map"); one visible affordance per action.

## 12. Release gate

Before tagging any release, run the journey harness against the packaged build (fresh profile + seeded profile) and the existing acceptance probes:

```
node packaging/ux-audit.cjs <appDir> <freshRoot>  <out> first-run
node packaging/ux-audit.cjs <appDir> <freshRoot>  <out> tour
node packaging/ux-audit.cjs <appDir> <seededRoot> <out> tour,settings,palette,keyboard,readability,sider,maintext
node packaging/verify-skip-link.cjs ... ; node packaging/a11y-probe.cjs ...
```

Pass = no JR-* violation in the JSON evidence; screenshots archived under `docs/product/evidence/<release>/`. Any new defect found must be added to `USER_JOURNEY_HISTORY.md` with a rule (new or existing) that would catch it. Evidence for the current branch lives in `docs/product/evidence/v15-ux-fixes/` (baseline and fixed runs side by side).

**JR-30 — One registry, every consumer.** Navigation and settings registries are consumed by more than one component (sider, page shell, router). Adding an entry to one registry while another still lacks it must fail the build or the journey harness's `settings` scenario — never ship a renderer that crashes on a registry lookup. Verify: add/remove a setting id in one place matches every consumer; the `settings` scenario must produce zero console errors and a non-empty sider item list.

**JR-31 — Progress counters count what the user has handled.** A progress line may never argue with the user's effort: statuses the user has acted on (answered, not sure, needs examples, awaiting visual selection, skipped, deferred) count as *recorded*; only strictly resolved answers count as *answered* for coverage and specs. After handling every question in a batch the line must read like "12 of 12 recorded", never "10 of 12". Verify: answer a full batch including `not sure` and `skip`; the progress line reaches n of n and the next-step hint appears.
**JR-32 — Every conversation exit path returns to the pending guided work.** Any assistant reply that interrupts a guided flow (chat answer, job completion, cancelled or *failed* planning) must end by re-surfacing the flow's open prompts; a silent exit path that drops them is a defect. Verify: trigger an interruption on each terminal branch, including failure, and assert the open prompts reappear.
**JR-33 — Advertised commands must parse exactly as advertised.** Every command a product surface lists ("explain 12", "challenge 12", "more options for 12") needs a test that parses that exact form; a hint the parser rejects is a JR-9-class silence defect. Verify: one test per advertised command that dispatches the literal string.

**JR-34 - A new engine route is wired for every consumer.** Adding an engine route means adding it to the renderer bridge whitelist (`KelService.ts` `kel:request` allowlist) and any other consumer registry in the same change; verify by driving the surface in the packaged app, never only by unit tests. A route that exists but cannot be reached is invisible work.

**JR-35 - Recording is loud, stoppable, and never hidden.** Any capture state must be unmistakable (visible mark + plain label + elapsed time), have an explicit stop **and** an explicit cancel, be cancellable with Escape, and must never be triggered by a hidden or global shortcut (no spacebar recording, no hint for one, no setting for one). Verify: record, watch the state, stop, cancel; confirm a hidden shortcut does nothing.

**JR-36 - Machine-written text lands editable before it acts.** Dictated or generated text enters the composer as text the user can edit or clear; it is never auto-sent and never replaces what the user already typed (it appends). Hand-offs between surfaces use a one-shot draft the receiving surface consumes and clears. Verify: dictate, edit, clear; confirm no message was sent.

**JR-37 - One plain status hides every provider.** A feature that talks to an external provider exposes exactly one human status ("Practice mode", "Muse (Meta)") with a single settings entry; endpoints, model names, protocol states, quota math, and socket errors stay out of the interface. Verify: no raw provider term appears in any surface copy.

**JR-38 - Live regions finalize exactly once.** Any live or placeholder region inserted into user-editable text (dictation previews, template inserts) must be cleared and replaced by the final value exactly once when the session ends, and cancel must restore the pre-session text. A stale region may never duplicate or overwrite what the user has. Verify: dictate with live text, stop, and confirm exactly one copy lands; cancel mid-session and confirm the original text returns.

**JR-39 - Every engine capability has a door or an honest label.** A capability that ships in the engine must be reachable from a user surface, or explicitly documented as API-only in the feature's status and limitations docs. Shipping neither is invisible work. Verify: for each action in a feature's engine family, either find the control that calls it or the doc line that says API-only.

**JR-40 - Superseded donor controls are removed everywhere.** When a Kel-native control replaces a donor control, every mount point of the donor control is swapped in the same change: no second path to the same capability, no hidden global shortcut left behind. Verify: grep the donor component's mount points; only the native control remains mounted.

**JR-41 - Every vertically growing surface has one scroll owner.** Each main-content surface must own exactly one vertical scroll container; a fixed frame, a draw over, and the page body never compete. Content that exists in the DOM is not proof of usability: verify with more than one viewport of content, scroll physically to the bottom, and confirm the last interactive control is visible, focusable and usable at small laptop heights and after resizing. No per-screen magic heights when the cause is the shared shell.

**JR-42 - The model Kel uses is a plain, explicit choice.** The user can choose Kel's normal conversational model (Auto, or a specific available model) and, per conversation, fall back to that default or pick their own. Availability is stated in plain words ("Available" / "Needs setup"); switching back to Auto restores routing completely; choices persist; provider and routing machinery stay out of the surface. An unavailable choice is a preference, never a dead end: Kel falls back and says so.

**JR-43 - Substantial unsent text survives.** A draft belongs to its conversation and survives navigation, switching and restart; only sending (or explicitly clearing) removes it. Recovery flows that restart the app must not be the first time a user learns their draft was in memory only.

**JR-44 - Theme foundation colors are the user's, per theme.** The selected theme exposes semantic color controls (background, surfaces, text, accent, border, success/warning/error) with picker, hex entry and per-token reset plus "restore defaults". Changes apply live, stay scoped to that theme, never mutate built-in defaults, and warn - without blocking or silently rewriting - when a combination becomes hard to read.

**JR-45 - Backups describe themselves before they overwrite.** A local backup is a folder with a human-readable description (what it covers, when, how much), credentials are excluded and that is stated. A restore validates the backup first, shows what will be replaced, keeps the current data beside it, and only completes after a restart so a failed copy can never half-replace the user's data.

**JR-46 - Search reaches the user's own content.** One search experience covers at least chats, transcripts and guided sessions with human partial terms and snippets, never internal ids; anything not yet covered is documented instead of implied. Every command surface (palette) lists only actions that actually run.

**JR-47 - An unexpected payload degrades in place; the shell never blanks.** Every surface that renders engine data must survive an absent, empty or differently-shaped field: the affected control says in plain words what is unavailable and the rest of the app - navigation, the current route's frame, other surfaces - stays usable. An uncaught render error that unmounts the whole application is a release blocker, not a cosmetic defect. Verify: load each engine-backed surface against a payload missing its optional fields (or force the failure) and confirm the shell and navigation remain usable.

**JR-48 - A control that promises a system effect must deliver it, and say so.** Any user-facing control that claims an effect on the machine or on the work (keep this computer awake, prevent sleep, block a capability, notify when done) must actually perform it, report the live state in plain words instead of mirroring the switch, persist where the promise is per computer, and release the effect when the app closes or the setting is switched off. Nothing on disk may keep the effect alive after Kel is gone. Verify: toggle it, read the reported state, restart the app, confirm the stored choice is re-applied, switch it off, and confirm the effect is released.

**JR-49 - Presence is proven by the journey, not by the primitive.** A capability counts as present only when the packaged app completes its user journey; an engine route, a mounted component, a persisted config key, or a control that does nothing counts as missing. A donor-derived capability is classified from the packaged build, never from the fact that a related primitive exists or that the feature has been discussed. Verify: run the journey in the packaged build and keep the resulting artifact with the classification.

**JR-50 - Conversation-scoped preferences state their scope, never leak, and never rewrite the global.** A preference that applies to one conversation must say so where it is set and where it applies, must be stored with that conversation, must survive navigation and restart, must not change any other conversation's setting, and must return to the shared default when reset. Verify: set it in one conversation, confirm a second conversation is untouched, restart, confirm both, reset the first, confirm it follows the global again.

**JR-51 - Capability controls express intent; machinery stays behind Details.** A user-facing capability control names what the user wants to do (Web, GitHub, Files, Terminal), never what Kel uses to do it (tool ids, connected-server names, runtimes, leases); an unavailable capability is stated in plain words with the action that makes it available, and cannot be switched on to look ready. Verify: read every string the control and its menu can show - no internal name appears - and switch on an unavailable capability to confirm it stays unusable with a plain reason.

**JR-52 - Saved knowledge changes only through the user's judgment.** When Kel believes saved project knowledge changed - a Design Vetting decision disagrees with a stored rule, two confirmed choices conflict, or a source behind a record changed - the change appears as a review with Current, Proposed and a plain reason plus Accept, Reject, Defer and Details. Nothing is overwritten until the user accepts; the previous value is preserved in the record's history; the same unchanged evidence never asks again after a rejection; the queue is scoped to the project it belongs to (no cross-project leakage). Verify: drive a disagreeing Design Vetting answer in the packaged app, accept one proposal (old value kept as superseded, new record user-confirmed), reject another and repeat the identical answer (no re-ask), defer a third and restart (state kept), and probe that another project's same-topic rule is untouched.

**JR-53 - "What changed" answers in plain words, not logs.** A project's knowledge history says what changed in Kel's understanding of this project in plain sentences with previous values (Added / You changed "old" to "new" / You accepted the change / You turned the change down / Out of date / Forgotten a record). No raw event or database dumps, no internal ids. Verify: in the packaged app, accept and reject proposals, then read the Work panel's Project knowledge tab and confirm the entries are plain sentences; the engine history formatter is pinned by test.

**JR-54 - A generated file can always say where it came from.** Every produced work artifact records its project, conversation, task, originating user request and time, together with its version chain; the Work surface offers a plain "Where from?" view with the earlier versions and the actions Open (any version), Show in folder and Copy path. Earlier versions stay readable after replacement (including renames) and a changed file on disk is refused instead of shown; provenance survives reopens (engine-pinned). No internal ids appear in the view. Verify: run a two-version job in the packaged app, open Where from?, view the older version, and reveal the file; the engine suite pins chain/rename/tamper behavior.


## Rule maintenance

- Adding a rule: give it the next `JR-n` id, one statement, one verification.
- Changing behavior that a rule covers: update the rule and note it in the history ledger.
- Removing a rule requires evidence that it is obsolete; silently dropping rules is not allowed.
