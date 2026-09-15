# KEL V1.4 — SCREEN INVENTORY (v1, source + captured routes)

Status: v1 (2026-09-15). Source inventory below plus **verified captures** of the frozen V1.3 package
(see `docs/v1.4/screenshots/baseline/`; 30 views × 2 data states, five widths, zero renderer errors).

## 0. Captured routes and views (verified by the harness)

| Route / view | Captured as | Notes |
|---|---|---|
| `#/guid` (start / chat) | `01-boot-chat`, `10-boot-chat-at-*` | empty greeting state + populated conversation list (fixture run) |
| Work & context drawer | `02-work-drawer`, `02b-work-tab-default` | drawer open over chat |
| Drawer tabs | `03-continue`, `04-knowledge`, `05-map`, `06-recipes` | per-tab captures in both data states |
| Recipe preview | `07-recipe-preview` | preview opened from the recipes tab |
| Map refresh | `07b-map-after-refresh` | refresh attempt + result |
| `#/settings/appearance`, `system`, `pet`, `webui`, `archived`, `about` | `09-settings-*` | real settings routes (from `Router.tsx`); v2 re-run records actual behavior |
| `#/settings/model`, `agent`, `skills`, `tools` | `09-settings-*` | route behavior recorded in manifests (redirects visible where they occur) |
| Resize passes | `10/11-*` | boot at 1280/1920/2560/1024 (1440×900 = primary); drawer re-open captured at 1280 (repeated-drawer capture lands in harness v3) |

Machine-readable companions: `v13-empty-manifest.json`, `v13-fixture-manifest.json`,
`v13-empty-texts.jsonl`, `v13-fixture-texts.jsonl`, `v13-empty-discovery.json`,
`v13-fixture-discovery.json`.

## 1. Window surfaces (Electron shell — `desktop/packages/desktop/src`)

| Surface | Source | Notes |
|---|---|---|
| Conversation (chat) | `renderer/pages/conversation/*` | `ChatLayout`, `Messages`, `GroupedHistory` (conversation list), `PlanBar`, `anchorRail`, `explorer` (file tree + search), `platforms` (acp / aionrs / gemini) |
| Kel Work drawer (in-chat) | `renderer/components/chat/KelWorkPanel.tsx` | Tabs: Work / Knowledge / Map / Recipes — V1.3 work-context UI; drives engine API (state/work/memory/map/recipes/control/apply/approval) |
| Scheduled tasks (cron) | `renderer/pages/cron/ScheduledTasksPage/*` | includes `TaskDetailPage` |
| Guid page | `renderer/pages/guid/GuidPage.tsx` | donor surface |
| Login | `renderer/pages/login/LoginPage.*` | donor surface |
| Settings | `renderer/pages/settings/*` | AgentSettings, AppearanceSettings, ArchivedSettings, AssistantSettings, ExtensionSettingsPage, ModeSettings, PetSettings, SkillsSettings, SystemSettings, ToolsSettings, WebuiSettings |
| Team page | `renderer/pages/team/TeamPage.tsx` | donor team UI — to assess against Kel's Office model (not yet Kel's Team workspace) |
| Pet windows | `renderer/pet/*` (`pet.html`, `pet-confirm.html`, `pet-hit.html`) + `process/pet/*` | ambient pet states; state machine + confirm/hit windows |
| Web companion (PWA) | `desktop/public/pwa/*`; packaged `pwa/` + `sw.js` | served by the shell |

## 2. Engine-served surfaces (`runtime/kel`)

| Surface | Source | Notes |
|---|---|---|
| Loopback API | `runtime/kel/service.py` | `/api/state`, `/api/work`, `/api/artifact`, `/api/send`, `/api/memory`, `/api/map`, `/api/recipes`, `/api/control`, `/api/approval`, `/api/apply`, `/api/retry`, `/api/project`, `/api/conversation`, `/api/attach`, `/api/revoke`, `/api/shutdown-idle` — bearer-token authorized |
| Engine web assets | `runtime/kel/web/*` | served on loopback (used by packaged UI pieces) |

## 3. Process-level surfaces

- Tray (`process/utils/tray.ts`), close-to-tray setting (`process/utils/closeToTraySetting.ts`).
- Auto-updater (`process/services/autoUpdaterService.ts`, `updateFeed.ts`, `autoUpdateDiagnostics.ts`) + update UI components.
- Startup sequence (`process/startup/*`), backend bridge (`process/backend/*`).

## 4. Known gaps vs brief §11.1 (to capture next)

- Captured now: boot/chat, work drawer + tabs, recipe preview, map refresh, settings routes, five widths.
- Still to capture: provider-unavailable, dialogs beyond the drawer, pet windows, offline/recovery
  screens, dense/long content at 2560 (v3 harness pass).
- Kel-specific settings pages (Providers / Autonomy / Permissions / Team / Memory / Diagnostics /
  Updates / About) do not exist yet as gathered settings pages (V1.4 scope, brief §17).
