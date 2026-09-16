# Kel V1.5 — User Journey Audit (baseline)

Date: 2026-09-16 · Auditor: independent user-journey pass (not the implementing agent)
Subject: released V1.5 — tag `v1.5.0`, release commit `5e76b21` (product commit `270e3cc`, G12 remediation `ed0b35e`)
Frozen build audited: `C:\Users\Nick\Desktop\Kel\Kel Releases\Kel-V1.5-Frozen` (never modified)
Method: the packaged app was launched through Playwright-Electron (`packaging/ux-audit.cjs` in the `ux/v15-journeys` worktree) and driven like a normal user — fresh profile and a seeded realistic profile (copy of the real install: engine store + donor store, no isolated-harness shortcuts beyond data-dir redirection).

Evidence (raw, machine-readable):
- `ux-audit/runs/fresh/…` — fresh-profile first-run (`ux-first-run.json`, screenshots)
- `ux-audit/runs/seeded3/…` — seeded 14-journey pass (`ux-tour.json`, `ux-settings.json`, `ux-palette.json`, `ux-keyboard.json`, `ux-readability.json`, `ux-sider.json`, `ux-maintext.json`, `ux-compose-*.json`, screenshots)
- Engine-side truth read from the seeded copy with `bun:sqlite` (jobs/messages/leases) — see "Engine truth" notes per journey.

Environment limitation (stated honestly): at audit time **no model provider was usable in this environment** ("4 providers · 0 usable right now"; codex quota exhausted, others not authenticated). Journeys that require a live model (chat answer, a run completing) could therefore not be observed end-to-end; their *failure* experience was observed instead, and the completed-work experience was evaluated on the seeded profile's previously finished jobs. Journey 4 (live permission prompt) could not be triggered for the same reason; its surfaces were evaluated from the shipped UI inventory and the V1.5 authorization documentation.

---

## Journey records

### J1 — Fresh launch
- **Goal**: do something useful within moments of first start.
- **First instinct**: find a text box.
- **Actual path**: boot → 5-step onboarding ≈ 21 s (+4.4 s launch) → "Start using Kel" → **landed on Work (empty project board)**, not the chat. Skipping setup lands on the chat instead. `first-run` evidence: `finishedHash #/work`, `hashAfterOnboarding #/work`; skip path → `#/guid`.
- **Steps/clicks**: 5 forward clicks (or 1 skip). After finishing: one extra click ("New Chat", +0.4 s) to reach a composer.
- **Confusing moments**: step 2 talks providers ("Queued", "quota not reported", "installed not authenticated"); step 4 uses "scope", "grant", "guardrails", "Agents"; final step says "Engine: 1.5.0 · Providers registered: 4 (none healthy yet)".
- **Dead ends**: none hard; but "where do I type?" is answered late if you complete setup.
- **Jargon**: "work engine", "scope", "grant", "guardrails", "Engine 1.5.0", "registered", "healthy".
- **Readability**: onboarding type is comfortable (16–20 px; step copy ≤ 60 ch lines).
- **What felt easy**: skip is offered on every step; progress is 5 short steps; window opens fitted and centered.
- **What should change**: finish → chat composer; plain-language onboarding; don't show engine/registration status on the final step.

### J2 — Simple conversation
- **Goal**: ask a simple question.
- **Actual path**: New Chat → type → send; conversation `#/conversation/…` created instantly; message shown at once.
- **Observed**: **no reply ever arrives, no error, no spinner, no guidance** (engine `messages`: user row only; Providers page: "0 usable right now"). The conversation sits silent.
- **Confusing moments**: nothing tells the user whether Kel is thinking, stuck, or unable.
- **Readability**: user bubble 14 px; timestamps and "Automatic" model row are 12–13 px (model row: "Kel" label measured 2.72:1 contrast, below AA).
- **What felt easy**: composer focus, send, message echo, conversation title created from text.
- **What should change**: surface "no model available" in chat with a next step.

### J3 — Real project work
- **Goal**: get a real file created.
- **Actual path**: ask in chat → engine accepts, creates a project folder (`Documents\Kel Projects\write-a-tiny-python-script-sum-py-in-1094`), issues a lease, parks the job (`READY`/`WAITING_RESOURCE`); chat shows a single activity row "Kel work: READY / UNCERTAIN" / "…WAITING_RESOURCE / UNCERTAIN" (raw vocabulary, hidden under "View Steps").
- **Confusing moments**: no plain sentence explains that work is parked because no model can run; "UN" wait status is invisible outside the row; the Files/Changes tabs are labeled `acp-temp-<id>`.
- **Visibility**: the Work page top line reads "0 jobs in this project · 0 waiting on you" while the Continuation section below lists both parked jobs **titled by raw job UUIDs**.
- **What should change**: plain status line + next step in chat; human job titles/states on Work; no internal ids in tab labels.

### J4 — Permission request (not triggerable in this environment)
- **Goal**: see a boundary/permission prompt and approve it.
- **Actual path**: work cannot reach the boundary stage without a usable model; `approvals` and `boundary_expansion_requests` tables are empty; the lease for the parked coding job was granted silently (policy-allowed).
- **Surfaces evaluated from the shipped UI**: `Autonomy` page ("1 active lease · 0 boundary requests waiting on you", lease table, "Emergency stop"), Work drawer approvals badge.
- **Findings carried**: see F9 (vocabulary) and F5 (no plain-language explanation of what Kel needs).
- **Left to verify when a provider is available**: Allow once / Allow for this project / Deny wording and auto-resume after approval.

### J5 — Failure
- **Goal**: understand what happened when something breaks.
- **Observed (provider unavailable — real)**: chat: silence (worst case). Work: one raw state row. Providers page: "4 providers · 0 usable right now" with per-provider infra labels. Diagnostics: "Problems: 2 recorded process(es) are no longer alive — database health is reported, not guessed."
- **A user can answer**: "what happened?" — only by opening Providers/Diagnostics and interpreting them. "Is Kel handling it?" — unclear. "Do I need to do anything?" — not stated. "What next?" — not stated.
- **What should change**: a single human sentence in the place where the failure happened, with one action.

### J6 — Find previous work
- **Goal**: find an old chat and an old result.
- **Actual path**: sider history (18 rows) — two sections: "Project conversations" (group header = raw workspace UUID `7c2c2250-291f-4f13-9c62-83edf8fe44f4`, rows "Badge chat", "status", "main", …) and "Conversations" (titles include the full first line, e.g. "I want to create a little app that allows me to control my microphone's mute button…").
- **Search**: titlebar "Search messages" (chats only); Ctrl+K palette scope = "work, knowledge, recipes and roles" (no chats). Two different searches; neither is discoverable from the other.
- **What felt easy**: titles echo the first message; groups keep projects apart.
- **What should change**: readable group labels; one obvious search entry point that covers chats + work.

### J7 — Work surface (as a non-engineer)
- **Observed copy**: "0 jobs in this project · 0 waiting on you"; "Continuation"; "Team assignments"; "verdict: UNCERTAIN · durable state only — no hidden reasoning · Continue from chat (say "continue", or pick a number)"; "there are never decorative workers".
- **Challenge terms**: milestone, verdict, continuation, artifact, acceptance, claim, run — surfaced raw (verdict, continuation) or in engine tables.
- **What should change**: user-decision vocabulary (Needs you / Working / Waiting on a model / Done), human titles, counter that matches the list.

### J8 — Projects (Knowledge / Map / Recipes)
- **Knowledge**: "No saved knowledge in this project yet. Kel records what it learns while working — with its source and a trust score." ("trust score" is internal-ish; fine as meta once records exist).
- **Map**: "Project map" + two identical "Refresh map" buttons; "No map built yet."
- **Recipes**: 5 builtins with "Preview (dry run)"; header "default · 0 knowledge records · map — · 5 recipes" ("default" = project name; "map —" = no map).
- **Names**: "Map" is not self-explanatory; "Recipes" is defensible but benefits from "what is this?"; header metadata is a debug line.
- **What should change**: rename header to plain status; single refresh action; explain Map in one line.

### J9 — Team
- **Observed**: Office (empty; "real assignments only"; "Seed the default roster"), Roster (9 roles, "v1 · 0 assignments", "Open in Studio"), Studio ("structured instructions, tool policy, budget, and version history").
- **Assessment**: this is role-template configuration/orchestration — power-user surface. Nothing here helps a normal user talk to Kel or navigate their work.
- **What should change**: not primary navigation; move behind Settings with a discoverable entry, keep routes.

### J10 — Providers
- **Observed**: 4 provider cards; mixed infra vocabulary ("quota not reported", "CLI present", "CLI session present", "installed not authenticated", "API key needed", "Model Capabilities", capability chips "text · tools · edit · shell"); "Readiness preflight" (what Kel would use per capability — genuinely useful, buried); credential form ("Store credential" disabled) with a long OS-backed explanation paragraph.
- **Assessment**: a configuration surface; something a normal user touches rarely, but *must* be able to find when chat stalls (see J2/F4).
- **What should change**: move to Settings; keep the readiness check and elevate "fix my model access" as an action from the stall banner; shorten the credential explainer.

### J11 — Autonomy
- **Observed**: name "Autonomy"; "0 active leases · 0 boundary requests waiting on you"; lease table with 64-char contract digest in "Review" and an "Expires" cell rendering "0s ago"; "Ask the engine about a scope" + paragraph with "fails closed", "snapshot reference"; "Locked guardrails · digest e666e7c59873"; Emergency stop with a good, honest sentence.
- **What should change**: rename user-facing to "Permissions"; human labels for lease state/expiry; move digests behind details; keep Emergency stop where it is.

### J12 — Settings
- **Observed**: sider shows only **Appearance** and **Archived**. Orphaned but fully built routes: `/settings/system` (language, start on boot, notifications, **work directory**, log directory, idle timeouts, cross-conversation messages, in-app browser, speech to text, clear browsing data), `/settings/about` (donor links: Update Log, Report Issue, Contact Me, Official Website), `/settings/webui` ("24/7 Remote Assistant", "Let the butler set it up", admin/******), `/settings/pet` (Desktop Pet). Redirects still work (`/settings/model → /providers`, `/settings/agent → /team/roster`, …).
- **Duplicates/dead**: two "Back to Chat" affordances; theme toggle inside settings footer; a person looking for notifications or language has no route.
- **What should change**: settings must own configuration (Providers, Team, Diagnostics, System, About); orphaned user-level settings must be reachable; donor-only pages either rewritten in Kel words or hidden.

### J13 — Diagnostics
- **Observed**: sections Health / Measured performance / Providers / Process ownership / Maintenance / Export and issue report; engine metrics in milliseconds; "orphan candidate past deadline"; maintenance buttons (Observe now, Purge expired observations, Compact database, Export sanitized diagnostics, Write local draft) with no confirmation observed (destructive ones were not triggered).
- **Assessment**: correctly deep and jargon-tolerant, but too prominent in primary navigation.
- **What should change**: keep as an advanced surface under Settings; no other changes this pass.

### J14 — Command palette (keyboard only)
- **Ctrl+K** opens ("Run a command or jump to a surface"); results grouped "Go to" (9), "Recipes" (5), "Roles" (9); **"/"** opens the same palette in search mode ("Search work, knowledge, recipes and roles"); typed filter "providers" narrows and Enter navigates; **Escape** closes; no-match shows "Nothing matches …". Not reachable: chats, settings sections, individual knowledge records.
- **Jargon in hints**: "job center", "live assignments", "role templates", "role editor", "memory", "project map", "library", "models and credentials", "leases and guardrails".
- **What should change**: plain-language label/hints; include settings targets; keep the one-palette model.

---

## Findings register (baseline)

| # | Severity | Finding | Rule |
|---|---|---|---|
| F1 | High | Completing onboarding lands on Work (empty) instead of chat; skipping lands in chat — inconsistent "where do I type" | UJS-1 |
| F2 | Med | Onboarding exposes infrastructure early ("Providers… none healthy", "Engine 1.5.0", "scope/grant/guardrails") | UJS-2 |
| F3 | Med | Profiles migrated from pre-onboarding Kel are forced through the full 5-step flow once (measured on a real profile with 18 conversations) | UJS-3 |
| F4 | High | No usable model → chat message gets no reply, no error, no guidance (silent dead conversation) | UJS-4 |
| F5 | High | Parked work shows only raw state rows ("Kel work: READY / UNCERTAIN"); no plain explanation or next step | UJS-4,UJS-5 |
| F6 | High | Work page counter says "0 jobs in this project" while Continuation lists those jobs, titled by raw UUIDs | UJS-6 |
| F7 | Med | Providers sits in primary nav; heavy infra vocabulary; "0 usable" not reflected elsewhere | UJS-7 |
| F8 | Med | Team (Office/Roster/Studio) is configuration/orchestration in primary nav | UJS-7 |
| F9 | Med | Autonomy vocabulary (leases/scopes/guardrails/digest); "Expires 0s ago"; abstract name | UJS-8 |
| F10 | Low | Diagnostics in primary nav (advanced surface) | UJS-7 |
| F11 | High | Settings sider hides genuinely user-level settings (System/About) with no entry point | UJS-9 |
| F12 | Med | Donor remnants in shipped UI: "butler", "Desktop Pet", donor support links, "Kill idle agent processes", "@@ mention" | UJS-10 |
| F13 | Med | Palette/copy jargon ("surface", "job center", "leases and guardrails"); palette can't find chats/settings | UJS-11 |
| F14 | Low | Readability: guid "Kel" label 2.72:1 (AA fail); 12 px meta on Providers; code size default 12 px | UJS-12 |
| F15 | Med | Conversation group header shows raw workspace UUID | UJS-6 |
| F16 | Low | Duplicate affordances (two "Refresh map", two "Back to Chat"); header line "default · … · map —" is a debug string | UJS-13 |
| F17 | Low | "Work & context" drawer label; "Files/Changes" tabs named `acp-temp-<id>` | UJS-6 |
| F18 | Low | Onboarding final step reports engine/registration status rather than user state | UJS-2 |
| F19 | Info | Onboarding skip offered on every step (keep); Emergency stop copy is exemplary (keep) | — |
| F20 | Info | "Readiness preflight" is a strong hidden tool; elevate as an action from stall states | UJS-4 |

## Interaction inventory (Phase 3 — primary surfaces)

Legend: works / not triggered / broken. "Not triggered" means deliberately avoided (destructive or unreachable in this environment); each is still accounted for.

| Surface | Control | Expected | Actual | Works | Keyboard | Feedback |
|---|---|---|---|---|---|---|
| Shell | Skip link | Focus main content | Moves focus to `#kel-shell-content` | yes | yes | visible 2 px focus ring |
| Sider | New Chat | Open chat composer | `#/guid`, composer focused-ready | yes | yes | instant |
| Sider | Work/Team/Projects/Providers/Autonomy/Diagnostics | Navigate | All six land on the right hash | yes | yes | instant |
| Sider | Search messages (titlebar) | Find chats | Opens chat search | yes | yes | — |
| Sider | Work & context | Open work drawer | opens drawer w/ approvals badge area | yes | yes | — |
| Sider | Settings gear | Open settings | `#/settings/appearance` | yes | yes | — |
| History | Conversation row | Open conversation | opens `#/conversation/<id>` | yes | yes | — |
| Guid | Composer | Type + send | textarea, typewriter placeholder | yes | yes | send clears input |
| Guid | Instruction chips | Prefill/send | fills composer | yes | yes | — |
| Work | Reload | Refresh state | re-fetches | yes | yes (first tab stop) | — |
| Work | Continue from chat | Resume parked work | instructs to say "continue" in chat | not triggered (no route) | — | copy only |
| Work | Emergency stop (Autonomy) | Revoke leases | disabled with reason when idle | yes (disabled state correct) | — | explanatory copy |
| Autonomy | Ask the engine | Policy check | disabled until scope typed | not triggered | — | — |
| Autonomy | Revoke lease | Revoke | enabled for active lease | not triggered | — | — |
| Providers | Check readiness | Preflight run | enabled | not triggered (would call provider) | — | — |
| Providers | Set credential metadata / Store credential | Configure auth | Store disabled until metadata set | not triggered | — | — |
| Projects·Map | Refresh map (×2) | Rebuild map | two identical buttons — duplicate | yes (duplicate) | yes | — |
| Projects·Recipes | Preview (dry run) ×5 | Dry-run recipe | enabled | not triggered | — | — |
| Team·Office | Seed the default roster | Create roles | enabled | not triggered | — | — |
| Settings | Add Theme / Light / Dark / Follow System | Theme | works, persists | yes | yes | — |
| Settings | Font steppers −/+ / Reset | Size | works | yes | yes | Reset disabled at default |
| Settings | Purge / Compact / Export diagnostics | Maintenance | present | not triggered (destructive) | — | — |
| Palette | Ctrl+K / "/" / filter / Enter / Escape | Navigate | all verified | yes | yes | no-match text |

## Verdict

The architecture is invisible-to-the-user in some places (composer, history, skip link, emergency stop) and loudly visible in others (providers, leases, verdicts, digests, engine status, raw ids). Navigation carries too many configuration surfaces and hides real user settings. Failure states are the weakest point: when Kel cannot work, it currently says nothing a human can act on. Fix list + rules: `USER_JOURNEY_STANDARD.md`; remediation ledger: `USER_JOURNEY_HISTORY.md`.

Note on rule ids: this baseline table was drafted with `UJS-n` labels; they were finalized as `JR-n` in `USER_JOURNEY_STANDARD.md`, which is authoritative.

---

## Status update — remediation batch 1 (2026-09-16, branch `ux/v15-journeys`)

Batch 1 fixed the highest-severity findings and re-ran the full harness against the rebuilt packaged app.
Full ledger with per-fix verification status: `USER_JOURNEY_HISTORY.md`. Evidence: `evidence/v15-ux-fixes/{baseline,fixed}/`.

**Verified in the rebuilt build** (fresh + seeded profiles): onboarding lands on the composer (`#/guid`) and reads
in plain language; the chat landing shows the provider-unavailable notice with an "Open Providers" action;
the Work page shows human counts (`0 active · 2 waiting to continue · 0 need you`), no UUID titles, no raw
verdict/“durable state” strings; the primary sider is `New Chat / Work / Projects / Permissions`; the palette
speaks plainly ("Search or jump to…") and reaches Permissions; the Project map has a single "Refresh map";
providers/projects/work/settings-appearance pages measure zero AA contrast offenders.

**Incomplete / reverted (recorded honestly):**
- the Settings-sider expansion (Providers/Team/Diagnostics/System entries) crashed at render because the donor
  shell keeps **two settings registries** (`SettingsSider` + `SettingsPageWrapper`) — the change was reverted
  before commit; see history item O8.
- the workspace label maps UUIDs to a friendly name but renders the raw i18n key
  `conversation.workspace.unnamedSpace` until the locale entry is added (O9).
- one 13 px "Kel" element on the chat landing still measures 2.72:1; the exact element is unidentified (O10).
- the provider notice is verified on the chat landing, not yet inside an open conversation (O7).

The happy-path chat/work/approval journeys (J-2/3/4 live) remain blocked on this machine by the absence of a
usable model provider (O1), so their *fixed* behaviors are unverified; the failure-path behaviors were exactly
what batch 1 could verify.
