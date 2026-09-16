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

## Rule maintenance

- Adding a rule: give it the next `JR-n` id, one statement, one verification.
- Changing behavior that a rule covers: update the rule and note it in the history ledger.
- Removing a rule requires evidence that it is obsolete; silently dropping rules is not allowed.
