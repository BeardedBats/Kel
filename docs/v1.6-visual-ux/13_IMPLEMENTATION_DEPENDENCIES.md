# 13 — Implementation Dependency Map and Commit Grouping

## 13.1 Classes of work

| Class | Definition | Members |
|---|---|---|
| **Independent** | No other planned fix and no Main/P1/Phase-4 work touches the region. Can land first, in any order among themselves. | hover/title overlap (#5) · Projects retitle + de-grid (#8) · Team seed-button defect (X1) · sidebar icon policy (#13) · readability sweep on donor surfaces (#4) · contrast gate |
| **Settings-routing dependent** | Anything that decides *where* Team / Permissions / Tools live must follow the routing decision, not precede it. | the settings-shell fix (#3) itself · Team terminology + settings entries (#14, #15) · any "render Team inside Settings" variant · Phase 4's Butler entry removal (same files) |
| **Engine/lifecycle sensitive** | Touches boot, spawn, descriptor, or the error path. Must come from the clean Main HEAD and must not race P1. | error translation (#16) · supervision/recovery (#17) · the `KelService.ts` readiness gate · boot-failure copy (also Phase 4 `common.json`) |
| **Renderer-only, but token-coupled** | Purely visual, but every pixel shifts when the token layer changes, so they must land *after* the density pass or be re-verified. | Work / Projects / Permissions de-carding (#7, #9, #10) · transcription IA (#6) · empty-state policy |
| **Shared-with-Main** | Main has committed changes here since `ffeef73`; re-read before editing and serialize. | `process/services/kel/KelService.ts` · `components/chat/KelWorkPanel.tsx` · `pages/conversation/Messages/MessageList.tsx` · `pages/conversation/Messages/hooks.ts` · `common/chat/chatLib.ts` (+ new `components/kel/KelApprovalCard.tsx`) |

## 13.2 Dependency edges (what must exist before what)

```
tokens + density (batch 1, alone)
   ├─> Work / Projects / Permissions rework (batch 3)
   ├─> transcription IA (batch 4)
   └─> any new "empty state" policy

settings routing decision (batch 2)
   ├─> Team terminology + settings entries (batch 5)
   ├─> Permissions/Team placement in nav
   └─> must be agreed WITH Phase 4 (Butler entry removal touches the same settings areas)

clean Main HEAD  +  P1 (runtime) landed
   ├─> error translation (batch 6)
   └─> engine supervision (batch 6)   [isolated; lifecycle code]

Phase 3 HEAD stable  +  conversation screenshots captured
   └─> composer/model relocation (batch 7)

independent → can go immediately after batch 1: hover overlap, sidebar icons, readability sweep
```

## 13.3 Commit grouping (each batch = one reviewable change set)

| Batch | Name | Contains | Must NOT contain | Pre-condition | Verify with |
|---|---|---|---|---|---|
| **1** | **Design tokens + density** | `styles/kel-tokens.css`, `styles/arco-override.css`, radius/scale consolidation | any component restructuring | clean HEAD | `probe-a` all surfaces: contrast not worse, histograms shifted down, screenshots regenerated |
| **2** | **Settings shell routing** | `components/layout/Router.tsx`, `components/settings/SettingsSider.tsx`, `pages/settings/components/SettingsPageWrapper.tsx` | token values, Team page internals | routing decision recorded; Phase 4 Butler scope agreed | `probe-a` → `settingsNav` for every settings entry |
| **3** | **Kel console pages** | `pages/kel/work/index.tsx`, `projects/index.tsx`, `autonomy/index.tsx`, `components/kel/KelPrimitives.tsx` (card/empty/chip primitives) | `KelService.ts`, any lifecycle code | batch 1 | `probe-a` char counts + nesting + heading sizes |
| **4** | **Transcription IA** | `pages/kel/transcription/index.tsx`, `index.module.css` | engine API, composer mic path | batch 1 + the API-Key semantics flag resolved | `probe-a` transcription assertions; the main thread's `transcription` scenario must still pass |
| **5** | **Sidebar + row ergonomics** | `pages/conversation/GroupedHistory/ConversationRow.tsx`, `Sider/index.tsx` (icon policy only), `pages/kel/team/index.tsx` (seed button), i18n keys if any | `KelWorkPanel` (Main owns it) | batch 2 decision | `probe-c` → `hover.overlapPx <= 0`, `newChat`, `sidebar.inventory` |
| **6** | **Engine reachability UX + supervision** | `process/services/kel/KelService.ts`, `components/kel/kelApi.ts`, the five `pages/kel/**` error sites, a new error-class module | anything else | clean HEAD + P1 landed; Phase 4 boot-copy coordination | `probe-b` kill-engine scenario; `desktop.log` collected |
| **7** | **Composer ergonomics** | `pages/conversation/components/ChatConversation.tsx`, `components/chat/SendBox/index.tsx`, the pill/tools components | `MessageList.tsx` / `KelWorkPanel.tsx` / `chatLib.ts` unless re-read post-Phase-3 | Phase 3 stable + conversation screenshots exist | `probe-a` on a conversation route; header/composer node assertions |
| **8** | **Readability sweep + contrast gate** | `CssThemeSettings.tsx`, `SystemSettings.tsx`, `ThemeColorsSection.tsx`, transcription CSS (if not done in 4) | token values | batch 1 (to avoid double reflow) | `probe-a` offenders === 0 on those surfaces, both themes |

**Must remain isolated (never bundled):** engine supervision (lifecycle; a bad merge here breaks startup),
transcription (1109-line file; large diff), tokens (global reflow), settings routing (changes navigation).
Bundling any of these with another batch makes bisecting a regression impractical.

## 13.4 Re-validation checklist before the first edit (per the hold conditions)

1. `git rev-parse <CLEAN_MAIN_HEAD>` matches the coordinator's value.
2. Confirm `KelService.ts`, `KelWorkPanel.tsx`, `MessageList.tsx`, `hooks.ts`, `chatLib.ts` are byte-identical
   to the versions read here; if not, re-read **and re-validate the root cause** of findings 2/5/16/17.
3. Confirm `pages/kel/**`, `styles/kel-tokens.css`, `Sider/**`, `Router.tsx`, `SettingsSider.tsx` are still
   unchanged since `ffeef73` (they were clean at the time of writing).
4. Re-run `probe-a` against a package built from that HEAD to refresh every baseline number in
   `12_ACCEPTANCE_CRITERIA.md` before claiming any improvement.
5. Re-check whether Phase 4 (i18n) has started; if it has, take the settings copy/entries coordination first.
