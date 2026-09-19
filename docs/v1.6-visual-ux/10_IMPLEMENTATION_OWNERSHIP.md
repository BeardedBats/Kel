# 10 — Implementation Ownership, Sequence, and Phase-3 Conflict Analysis

This audit stops before touching production code. What follows is the exact plan to execute once the
Integration Coordinator provides the committed Phase 3 HEAD.

## Branch / worktree

| Item | Value |
|---|---|
| Audit branch (already exists) | `audit/v16-visual-ux` @ `ffeef73`, worktree `C:\Users\Nick\Desktop\Kel\kel-v16-visual-audit` — holds these docs |
| **Proposed implementation branch** | `ux/v16-visual-remediation` |
| **Proposed implementation worktree** | `C:\Users\Nick\Desktop\Kel\kel-v16-visual-fix` |
| Base commit | **The Phase 3 committed HEAD** (not `ffeef73`) |
| Why not `ffeef73` | Phase 3 already changed four files this work also needs to touch (see below). Branching from Phase 3 means one clean merge instead of a conflict resolution. |
| Docs carry-over | `git checkout audit/v16-visual-ux -- docs/v1.6-visual-ux` in the new worktree |

Do not write to `kel-ux-v15`, do not touch `Kel Releases/*`, and keep `v1.6.0-pre1` byte-identical.

## Phase 3 conflict analysis (this is the important part)

Phase 3 (`85e99fb`, *"feat(approvals): decisions answer in the conversation, on one durable record"*) touches:

```
common/chat/chatLib.ts                              ← shared
process/services/kel/KelService.ts                  ← SHARED, high risk
process/services/kel/reconcileHistory.ts
renderer/components/chat/KelWorkPanel.tsx           ← SHARED
renderer/components/kel/KelApprovalCard.tsx         (new)
renderer/pages/conversation/Messages/MessageList.tsx ← SHARED
renderer/pages/conversation/Messages/hooks.ts       ← shared
runtime/kel/** (chat_approvals.py, authorize.py, service.py, core.py, engine.py, apply_changes.py, coding.py)
runtime/tests/test_v16_approvals.py
docs/in-chat-approvals/**, docs/product/**
```

**Direct overlaps with this audit's recommendations:**

| Shared file | Why both need it | Protocol |
|---|---|---|
| `process/services/kel/KelService.ts` | Phase 3 added 34 lines here. My engine-supervision + error-classification work (`09_ERROR_STATES.md`) also lives here. | **Serialize.** Land Phase 3 first; my changes go on top in a separate, small, reviewable commit. Never edit this file in parallel. |
| `components/chat/KelWorkPanel.tsx` | Phase 3 added 104 lines (approval surface in the Work & context panel). I propose replacing that panel's visual treatment. | **Serialize**, same rule. Whoever holds it, says so. |
| `pages/conversation/Messages/MessageList.tsx` + `hooks.ts` | Phase 3 adds the in-chat approval card; I propose the assistant-prose/composer changes and card policy. | **Serialize.** Card policy must be agreed once so the approval card is designed *as* a special interaction card (which the direction explicitly allows) rather than reverting to a generic card. |
| `common/chat/chatLib.ts` | Phase 3 added the approval message kind; I would touch types only if needed. | Coordinate; likely no change needed from me. |

**No overlap at all** (safe to do in parallel, they are untouched by Phase 3): the sidebar (`components/layout/Sider/**`),
the settings shell (`components/layout/Router.tsx`, `pages/settings/**`, `components/settings/SettingsSider.tsx`),
all five `pages/kel/**` surfaces, the transcription page + CSS, `styles/kel-tokens.css`, and
`pages/conversation/GroupedHistory/**`.

## Exact implementation sequence

Ordered by severity, and deliberately front-loading work with **zero** Phase-3 overlap.

| # | Step | Files | Severity | Verification |
|---|---|---|---|---|
| 0 | Rebase onto Phase 3 HEAD; create worktree; re-run `probe-a` on the Phase-3 build to refresh the baseline | — | — | probe JSON diff vs this audit's baseline |
| 1 | **Design tokens + density.** Dim navy/slate-navy dark surfaces, off-white primary text, restrained pale semantic accents, 8px control radius, one surface radius, type scale floor and reduction (h1 32→20–22, card heading 24→15–16, body 16→14 in panels), spacing (card pad 24→16, gutter 32→24, row 44→32–34) | `styles/kel-tokens.css`, `styles/arco-override.css` | **S1** (it is the root cause of two complaints) | re-run `probe-a`: same-or-better contrast, font histograms shifted down, no offenders added |
| 2 | **Settings shell fix.** `/settings/agent`, `/settings/skills`, `/settings/assistants`, `/settings/capabilities`, `/settings/skills-hub` must not leave `/settings`; `/settings/tools` → `/autonomy` must be reconsidered. Replace the two Team entries with one. | `components/layout/Router.tsx`, `components/settings/SettingsSider.tsx` | **S1** | `settingsNav` step in `probe-a`: every settings entry keeps the settings sider (`hasSettingsSider:true, hasMainNavWork:false`) |
| 3 | **Hover/title overlap.** Reserve the action affordance in the row's padding (`pe-16px` → space for 8px + 20px + gap) or move actions to a non-overlapping slot | `pages/conversation/GroupedHistory/ConversationRow.tsx` | **S2** | `probe-c` `overlapPx` must be ≤ 0 |
| 4 | **Error states.** Classify bridge failures (engine-not-started / engine-stopped / refused / HTTP error), map to human copy, one recovery action, raw detail behind a disclosure with "Copy diagnostics". Suppress neutral empty-state cards while an error is showing. | `components/kel/kelApi.ts` + the five `pages/kel/**` error sites | **S1** | re-run `probe-b` engine-loss scenario: **no** `TypeError:` string in any alert |
| 5 | **Engine supervision & startup.** Readiness gate (or an explicit "starting Kel" state) before engine-dependent surfaces claim failure; supervision to re-spawn/re-attach a dead engine; single-instance guard so one process quitting cannot stop a shared engine (`/api/shutdown-idle`). | `process/services/kel/KelService.ts` + main entry | **S1** | kill the engine with the app open → screens recover without restart |
| 6 | **Work / Projects / Permissions rebuild.** De-card (sections + dividers instead of 4 always-rendered cards), remove card-in-card, drop the raw `kel-code` JSON from user surfaces, retitle Projects to what it is, move Emergency stop out of the header, hide/relocate the policy checker, cut the prose. | `pages/kel/work/index.tsx`, `pages/kel/projects/index.tsx`, `pages/kel/autonomy/index.tsx`, `components/kel/KelPrimitives.tsx` | **S2** | `probe-a` char counts per surface must drop materially (Permissions 3615 → target < 1200); no card nesting |
| 7 | **Transcription IA** per the user's decision (see `06_TRANSCRIPTION.md`). | `pages/kel/transcription/index.tsx` (1109), `index.module.css` (173) | **S2** | `probe-a` transcription surface: title + API Key text present, `Record` right-most, 4 bottom actions, Kel tokens only (zero `--color-*` donor vars) |
| 8 | **Chat / composer relocation + card policy.** Model + tools into the composer; assistant prose unstyled by cards; approval card as a deliberate special card. | `pages/conversation/components/ChatConversation.tsx`, `components/chat/SendBox/index.tsx`, `KelModelPill`, `KelToolsControl`, `Messages/MessageList.tsx` | **S2** | composer contains the controls; header no longer does; both themes |
| 9 | **Readability sweep on donor surfaces** (theme gallery labels, System backup buttons, Model chips, Transcription muted text) + add the contrast gate over shipped surfaces. | `CssThemeSettings.tsx`, `SystemSettings.tsx`, `ThemeColorsSection.tsx`, transcription CSS | **S2** | zero offenders in `probe-a` for both themes |
| 10 | **Team/agents terminology** + the no-op "Seed the default roster" button. | `pages/kel/team/index.tsx`, `SettingsSider.tsx`, i18n `en-US` | **S3** | Office button either seeds or is gone |
| 11 | **Final full pass.** probe A + B + C, both themes, 1440/1280/1024, populated and empty profiles; regenerate screenshots; **a human must look at the screenshots** (this audit could not). | — | — | acceptance record in `docs/v1.6-visual-ux/` |

## Definition of done for the remediation

* No raw exception string is reachable in any user-facing copy.
* Every Settings navigation entry keeps the user inside the Settings shell.
* No hover affordance overlaps a title; no action needs a hover to be discoverable on touch-sized targets.
* No card exists that is not carrying structure; no card-in-card.
* Every shipped surface passes AA for body text in both themes at 1024×768 and above.
* A human reviewer signs off on the screenshots — explicitly as the step the mechanical checks cannot replace.

## Risks

1. **Token change blast radius.** `kel-tokens.css` is consumed by every Kel surface; the density change will
   reflow all of them. Mitigate by doing it in step 1 alone and re-measuring before anything else lands.
2. **Phase 3 serialization.** If step 4/5 is started while Phase 3 still holds `KelService.ts`, the merge will
   be painful. Enforce the protocol above.
3. **Transcription rewrite risk.** 1109 lines is a large single file; the donor's interaction architecture
   (drag-to-folder, autosave, live text, sheets) is the proven part — restructure the *shell*, not the wiring.
   The engine API is already correct and needs no change.
4. **Density vs readability.** Reducing page scale can push text below comfortable size; the 12px floor and the
   contrast gate must be enforced in the same step.
