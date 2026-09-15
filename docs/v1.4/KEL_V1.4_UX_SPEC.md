# KEL V1.4 — UX SPEC (information architecture, surfaces, migration)

Status: v1 (2026-09-15) · Gate 2 design document. Companions: `KEL_V1.4_DESIGN_SYSTEM.md`,
`KEL_V1.4_INTERACTION_PATTERNS.md`, `KEL_V1.4_VISUAL_ACCEPTANCE_MATRIX.md`.

## 1. Information architecture

Primary navigation: **Chat · Work · Team · Projects · Recipes · Search · Settings**

- **Team:** Office (real assignments) · Roster (role templates) · Studio (role configuration).
- **Projects:** Overview · Knowledge (memory) · Map · Work · Team · Recipes · Settings.
- **Settings:** General · Appearance · Providers · Team · Projects · Autonomy · Permissions · Memory ·
  Notifications · Updates · Privacy · Diagnostics · Advanced · About.
- Rules: no navigation entry without backing data (empty entries are hidden, not stubbed); contextual
  detail uses sheets (chat-adjacent) rather than new pages; deep links are stable and shareable
  (`#/work?job=…`, `#/team/office?assignment=…`, `#/settings/providers`).

## 2. Surface rules

Page = durable, listable objects (jobs, roles, projects, settings sections). Sheet = one object in
context (job detail, approval, specialist detail, role draft). Dialog = destructive/irreversible
confirmation only, at most one at a time. Drawer = the in-chat Work panel (existing pattern),
restyled with the design system but unchanged in role.

## 3. Surface specs (concise)

- **Chat:** one Kel voice; conversation list; composer; suggestions row; work-context drawer with
  Work · Continue work · Project knowledge · Project map · Recipes · Saved context · Saved history;
  approvals badge (count) that opens the Approval Inbox.
- **Work Center:** verdict line (“N jobs · M waiting on you”), filter pills (All/Running/Waiting/
  Verified/Uncertain/Failed), job rows/cards with current step, milestone checklist (frozen accepted
  steps marked), scope chip, budget meter, wait reason, retry/escalation history, artifacts, apply
  state; dense mode ≥10 jobs; detail sheet with pause/resume/cancel, evidence, receipt.
- **Team → Office:** live + historical assignments only (see Team model); columns: specialist, role,
  assignment, state, elapsed, tools, budget; activity timeline per assignment; artifacts/evidence
  drawer; empty state points to Roster.
- **Team → Roster:** role templates with current version, department grouping, status
  (active/draft/retired); “used by N assignments”.
- **Team → Studio:** structured role editor (goal/inputs/outputs/quality bar/boundaries/locked block);
  version list, diff, rollback; tool policy, model preference, budget controls; locked block always
  visually distinct and read-only.
- **Providers:** one card per provider per Provider spec §3–§8; test connection; role preferences;
  fallback rules; usage history; DeepSeek card.
- **Autonomy & Permissions:** autonomy profile, live lease viewer (roots/repos/domains/tools/external
  actions/expiry with revoke), Approval Inbox (allow once / allow for project / deny with reason),
  red-line summary (read-only, “why locked” explanation).
- **Projects → Knowledge / Map:** memory list with type + trust badges, source links,
  confirm/edit/retract/forget, conflict resolver, supersession, stale warnings; map with freshness,
  manual refresh, incremental changes; context preview with why-included and size/source mix.
- **Continuation:** continue-last, chooser (numbered), resume summary, exact-session status, bounded
  fallback message, wrong-project block, source-change warning, recovered-work banner.
- **Verification & evidence:** worker-reported vs Kel-verified as two distinct steps; evidence viewer
  with classes/freshness/digests; reviewer independence; failed/flaky detail; coverage matrix; receipt.
- **Recipes:** library, preview (steps, required inputs, permission preview), progress with frozen
  steps, retries, terminal states, dry run, project-local recipes.
- **Settings migration:** the donor’s `agent/skills/tools/model` routes currently redirect to `#/guid`
  (audited); V1.4 replaces them with real sections (Team/Providers) or hides them — no dead entries.
- **Onboarding (first run):** welcome → local/private → provider setup (CLI vs API) → project
  location → Broad Autonomy explanation → locked guardrails → Team explanation → harmless test task →
  readiness result. Migrated users do not see it.
- **Search & palette:** global search across conversations, jobs, memory, recipes, roles;
  `Ctrl+K` palette with commands (open Work, start recipe, revoke lease…), `/` focuses search.
- **Diagnostics:** health overview, startup timeline, provider latency/quota, context/memory metrics,
  task cost/time, process ownership, orphan detector, DB health/compaction, sanitized export,
  issue-report draft.
- **Tray / notifications / pet / startup:** tray quick actions; restraint rule (one OS notification
  per job state change; approvals persist in-app); pet states reflect real engine state only;
  startup health screen with recovery explanation.

## 4. Old-surface migration strategy

| Surface (donor) | Decision |
|---|---|
| Chat, composer, conversation list, guid start page | Keep; restyle with Kel tokens + wrappers |
| Work panel (`KelWorkPanel.tsx`) | Keep behaviour; restyle to design system (tables/cards, chips, focus) |
| Settings shell (modal/pages, 11 donor pages) | Keep the shell; regroup into the 14 Kel sections; restyle |
| `pages/team/TeamPage.tsx` (Aion teams) | **Replace** with Office/Roster/Studio |
| Login, extension/skills pages, cron | Keep; restyle; dead entries removed |
| Pet windows, tray, auto-update, PWA | Keep; tokenize colours/typography; no behaviour change |
| Login/guid empty states | Keep; restyle to Design “empty state” pattern |

## 5. Keyboard, states, and copy

Keyboard map: skip link → nav → content → sheet; `Esc` closes overlays; `Ctrl+K` palette; `/`
search; arrows within tables/menus. Every surface renders the states in the acceptance matrix §2;
status wording comes from the design system’s status-language table; errors state cause + fix +
evidence; destructive actions confirm with consequence + rollback.

## 6. Screenshot and visual-regression strategy

1. **Baseline** = frozen V1.3 captures (`screenshots/baseline/`, 2 × 30 views, five widths).
2. **Directions** = rendered comps + audit (`screenshots/directions/`).
3. **Final** = packaged V1.4 captures with the same harness and tags per surface; deterministic
   fixtures (existing `seed_ui_fixture.py`; extend with team/providers/autonomy fixtures).
4. **Comparisons** = `screenshots/comparisons/<surface>-<width>.png` (baseline vs final, same state).
5. Determinism rules: fresh data root per run, fixed widths, settle waits, offscreen windows,
   zero-orphan check; manifests + text dumps committed as evidence.
6. Gate rule: no surface is accepted without baseline + final + comparison + independent verdict.
