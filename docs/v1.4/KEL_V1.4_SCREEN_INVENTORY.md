# KEL V1.4 — SCREEN INVENTORY (v0, source-derived)

Status: v0 — derived from source paths only. **No packaged capture yet** (no window was opened this
session). The screenshot harness lands next; this file will be replaced by the verified inventory
with real captures per resolution and state.

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

- No packaged screenshots; no state matrix (empty / loading / error / populated / blocked / …).
- No resolution set captured (1280×720, 1440×900, 1920×1080, 2560×1440, narrow window).
- Kel-specific settings pages (Providers / Autonomy / Permissions / Team / Memory / Diagnostics / Updates / About) do not exist yet as gathered settings pages (V1.4 scope, brief §17).
