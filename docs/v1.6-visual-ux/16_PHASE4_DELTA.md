# 16 — Phase 4 Delta / Revalidation Prep (read-only, standby)

**Purpose:** satisfy the standby instruction "revalidate before editing": classify every original Visual finding
against the current **committed** Main head so that implementation can begin immediately and correctly when
`visual_clean_head` is published.

| | |
|---|---|
| Audit baseline (my evidence set) | `ffeef73` |
| Main committed head examined | `60b2322` (`ux/v15-journeys`) — `docs(v1.6): MAIN_STATUS — Worktree reviewed state` |
| Phase 4 production commit | `fd04c00` — *"Phase 4 complete — donor identity out of the product, all 12 locales clean"* |
| Method | read-only `git diff`/`git show` against the integration worktree; **no files written in Main** |
| Date of this pass | 2026-09-17 (standby) |

## Repo-truth verification (the 7 start conditions)

| # | Condition | Result |
|---|---|---|
| 1 | `visual_clean_head` exists | **NO — `visual_clean_head: NONE`** → start condition **not met** |
| 2 | Reachable from `ux/v15-journeys` | `60b2322` YES · `fd04c00` YES |
| 3 | Main worktree clean when published | `git status --porcelain` → **0 entries** (clean) |
| 4 | Contains every Visual integration dependency | Cannot be assessed until a clean head is published |
| 5 | Not revoked/superseded by a later status | Status currently reads `state: WAITING_FOR_AUDIT`, `visual_required: true` |
| 6 | Main not actively modifying my files | Clean tree, but Main is **gated on the Independent Audit's CONTINUE** before Phase 5, so renderer work may resume at any time |
| 7 | Frozen releases untouched | Zero files under `Kel Releases/` modified since 12:00; `v1.6.0-pre1` still peels to `f24d9c2` (see note) |

**Annotated-tag note (checked, not assumed):** `git rev-parse v1.6.0-pre1` returns `ceac727…`, which is the
**annotated tag object**, not a moved tag. It still targets commit `f24d9c28…` = `f24d9c2`. No integrity issue.

## What Phase 4 actually changed (evidence, not assumption)

* **142 files, +1517 / −2142.** The overwhelming majority are the 12 locale catalogs
  (`i18n/locales/<lang>/{common,settings,conversation,cron,login,preview,team,update}.json`).
* **Butler surfaces were DELETED** (status `D`): `components/base/ButlerDiagnoseButton.tsx`,
  `components/base/TalkToButlerButton.tsx`, `hooks/assistant/useTalkToButler.ts`.
* Butler references were also edited in `ModelModalContent.tsx`, `ToolsModalContent.tsx`, `LocalAgents.tsx`,
  `AssistantListPanel.tsx`, `AssistantHomeTabs.tsx`, `MyAssistantsList.tsx`, `OfficialAssistantsGrid.tsx`,
  `SkillDetailPage.tsx`, `SkillsHubSettings.tsx`.
* **Not touched by Phase 4:** `pages/settings/components/SettingsSider.tsx`, `components/layout/Router.tsx`,
  `styles/kel-tokens.css`, all five `pages/kel/**` surfaces, transcription page + CSS,
  `GroupedHistory/**`, `ConversationRow.tsx`, `Sider/**`, `components/kel/**`,
  `AppearanceSettings/CssThemeSettings.tsx`, `SystemSettings.tsx`, `ThemeColorsSection.tsx`,
  `ChatConversation.tsx`, `SendBox/index.tsx`.

**Consequence:** my conflict-map concern about a *Butler-removal race* in the Settings entries is **resolved** —
Main already did that work. The remaining coordination item is the routing decision itself (below).

## ERrata — path correction carried forward (important for implementation)

In `11_CONFLICT_MAP.md` and `13_IMPLEMENTATION_DEPENDENCIES.md` the settings sider is written in two places as
`components/settings/SettingsSider.tsx`. **That path does not exist at either commit.** The correct file is:

```
desktop/packages/desktop/src/renderer/pages/settings/components/SettingsSider.tsx
```

Same for its siblings (`SettingsPageWrapper.tsx`, `SettingsPageHeader.tsx`) — they live under
`pages/settings/components/`. (Verified with `git cat-file -e` at both `ffeef73` and `60b2322`.)

## Per-finding revalidation classification

Legend: **STILL_PRESENT** (governing file unchanged → root cause stands) · **CHANGED_ROOT_CAUSE** (the file that
produces the defect was edited upstream) · **FIXED_UPSTREAM** · **STALE** · **NEEDS_NEW_EVIDENCE** (cannot be
classified from source alone; must re-measure at the clean head).

| # | Finding | Governing file(s) at `60b2322` | Class | Note |
|---|---|---|---|---|
| S1-1 | Settings navigation ejects from Settings | `Router.tsx` (unchanged — redirects to `/team/roster`, `/autonomy` verified present at lines 114–132), `pages/settings/components/SettingsSider.tsx` (unchanged) | **STILL_PRESENT** | Root cause intact at the new head. Phase 4 did not fix it. |
| S1-2 | Engine loss / raw errors / no supervision | `KelService.ts` **CHANGED** (+34/−2 since `ffeef73`); `kelApi.ts` + the five Kel pages unchanged | **STILL_PRESENT (copy layer) + NEEDS_NEW_EVIDENCE (transport layer)** | The raw-string leak in page copy is unchanged; the boot/spawn/descriptor path **must be re-read at the clean head** and re-reproduced before implementing batch 6. |
| S2-3 | Theme colour picker remount/focus loss | `ThemeColorsSection.tsx` (unchanged) | **STILL_PRESENT** | Keys `${token}:…:${rev}` / `${themeId}:${refresh}` unchanged. |
| S2-4 | Hover actions overlap titles | `ConversationRow.tsx` (unchanged) | **STILL_PRESENT** | `pe-16px` vs 28px occupied — unchanged. |
| S2-5 | Permissions technical/oversized | `pages/kel/autonomy/index.tsx` (unchanged) | **STILL_PRESENT** | 3 615-char baseline still valid pending a fresh measure. |
| S2-6 | Work oversized/card-heavy | `pages/kel/work/index.tsx` (unchanged) | **STILL_PRESENT** | |
| S2-7 | Projects oversized/card-heavy | `pages/kel/projects/index.tsx` (unchanged) | **STILL_PRESENT** | |
| S2-8 | Transcription diverges from authoritative IA | `pages/kel/transcription/*` (unchanged) | **STILL_PRESENT** | |
| S2-9 | Readability/contrast on donor surfaces | `CssThemeSettings.tsx`, `SystemSettings.tsx`, `ThemeColorsSection.tsx` (all unchanged) | **STILL_PRESENT (3 of 4 surfaces)** | **Exception:** the `/settings/model` "Needs setup" chip lives in `ModelModalContent.tsx`, which Phase 4 **CHANGED** → that one offender is **NEEDS_NEW_EVIDENCE**; re-measure before editing. |
| S2-10 | Model/Tools detached from composer | `ChatConversation.tsx`, `SendBox/index.tsx`, `KelModelPill`/`KelToolsControl` (unchanged) | **STILL_PRESENT** | |
| S3-11 | Projects naming/semantics mismatch | `pages/kel/projects/index.tsx` + nav labels (unchanged) | **STILL_PRESENT** | |
| S3-12 | Redundant conversation-row icons | `ConversationRow.tsx`, `conversationAssistantIdentity.ts` (both unchanged) | **STILL_PRESENT** | |
| S3-13 | Project/folder semantics collide | `GroupedHistory/index.tsx`, `KelNavEntries.tsx` (unchanged) | **STILL_PRESENT** | |
| S3-14 | "Add Agent" terminology/behaviour | `pages/kel/team/index.tsx` (unchanged); settings area **changed** by Phase 4 | **STILL_PRESENT + NEEDS_NEW_EVIDENCE** | No creation path exists in the Team page. Settings-area wording shifted in Phase 4 (Butler removal + locale values) → re-read the rendered settings entries before changing terminology. |
| X-15 | Team → Office "Seed the default roster" no-op | `pages/kel/team/index.tsx` (unchanged) | **STILL_PRESENT** | `onAction={() => void load()}` unchanged. |
| X-16 | `TeamSiderSection` dead/unmounted | `components/layout/Sider/TeamSiderSection.tsx`, `Sider/index.tsx` (unchanged) | **STILL_PRESENT** | Still no importer. |
| D-17 | New Chat temporary-conversation behaviour | `Sider/index.tsx` (unchanged) | **STILL_PRESENT** | Awaiting the semantics decision (see `15_SEMANTICS_FLAGS.md` F1). |
| D-18 | Empty-conversation cleanup | `GroupedHistory/**`, `Sider/index.tsx` (unchanged) | **STILL_PRESENT** | Awaiting the rule decision (F2). |

**Nothing was FIXED_UPSTREAM** and **nothing is STALE** — every visual root cause survived Phase 4 intact,
because Phase 4 was strictly donor-string/locale work and none of it reached my surfaces.

## Indirect-effect watchlist (re-measure, do not assume)

1. **Rendered strings on settings surfaces changed** (12 locales × `settings.json`, `common.json`). Any
   readability/contrast claim that was tied to a *label's* presence or width must be re-measured
   (`/settings/model`, `/settings/system`, `/settings/appearance`).
2. **`SettingsSider` labels resolve through `settings.*` keys** whose values just changed in Phase 4 → capture
   the rendered Settings list again before deciding the routing fix (the entries are the same; the text may not be).
3. **Desktop is still `1.5.0`** in the packaged build I audited; a fresh package must be built from the
   eventual `visual_clean_head` before any packaged acceptance claim.
4. `KelService.ts` carries Phase 3 + later changes; batch 6 must re-read it fully and re-run the kill-engine
   reproduction rather than trusting the recorded mechanism.

## Readiness checklist for the moment `READY_FOR_VISUAL` appears

1. `git rev-parse visual_clean_head` == value in MAIN_STATUS; reachable from `ux/v15-journeys`.
2. Re-run the `git cat-file -e` existence + `git diff` clean test used above, over the **full** planned file list
   (this pass covered 19 files; the batch plans reference ~25).
3. Re-read `KelService.ts`, `KelWorkPanel.tsx`, `MessageList.tsx`, `Messages/hooks.ts`, `chatLib.ts` at that head.
4. Build a fresh package from that head (baseline), then run `probe-a/b/c` to refresh every recorded baseline
   number in `12_ACCEPTANCE_CRITERIA.md`.
5. Capture the two missing baseline states (findings 2 and 3) **before** touching those surfaces.
6. Create `kel-v16-visual-fix` on `ux/v16-visual-fix` at exactly that commit; carry `docs/v1.6-visual-ux/`.
7. Write `active_owned_files` into `VISUAL_STATUS.md` **before** the first production edit.

## Standby state

`VISUAL_STATUS.md` records `state: STANDBY`, `base_main_head: NONE`, `implementation_worktree: NONE`.
A read-only dependency watch runs at the **30-second cadence** (the earlier 300-second watcher was retired):
script `C:\Users\Nick\Desktop\Kel\ux-audit\visual\watch-main-status.sh`, log
`...\visual\main-status-watch-30s.log`, handoff marker `...\visual\READY_FOR_VISUAL.detected`.
It stops the waiting loop the moment `READY_FOR_VISUAL` + a real `visual_clean_head` are published, treats a
partial signal as PARTIAL (never as readiness), and writes nothing in Main.
