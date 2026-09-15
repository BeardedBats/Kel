# Kel 0.5.0: AionUI source adoption

Kel now runs the real AionUI React interface. The old 0.4.0 interface was a separate implementation based on screenshots.

## Source and ownership

- AionUI repository: https://github.com/iOfficeAI/AionUi
- Pinned revision: `6744099b279b991c17e31c243f0920477bd31cb6` (source version 2.2.2).
- AionCore: bundled Windows v0.2.2, source revision `47e66d0d151123e973b3fd1e77afcb5671b3f8c5`.
- Both donor licenses are Apache-2.0. Their license files accompany the application. Original source notices remain intact.
- Kel retains its existing Python work engine. AionCore provides donor interface services, conversation storage and file operations.
- Kel is registered as the only enabled ACP assistant. AionCore does not select a replacement assistant for Kel work.

## Reused implementation

These are actual donor components, styles and behavior:

| Feature | Donor source area |
| --- | --- |
| Window layout and navigation | `packages/desktop/src/renderer/components/layout/` |
| Conversation groups, rename, pin, archive, search | `pages/conversation/GroupedHistory/` |
| Composer, drafts, attachments, mentions | `components/chat/SendBox*`, `pages/guid/`, `pages/conversation/platforms/acp/` |
| Messages, markdown, copy, activity rows | `pages/conversation/Messages/` |
| Workspace tree, preview tabs, editor and resize | `pages/conversation/Preview/`, `pages/conversation/components/ChatSlider*` |
| Appearance and theme settings | `pages/settings/`, donor styles and theme providers |
| Native file dialogs and filesystem operations | Donor main/preload bridge and bundled AionCore |

Paths in this table are relative to AionUI's renderer except where the full prefix is shown.

## Kel changes

Kel branding replaces the donor branding. Agent catalogs, teams, schedules, pets, remote-service settings and donor support links are outside this release.

The default window opens normally at up to 1440×960, fitted to the active screen. It does not start maximized. User messages remain on the right.

A Work & context drawer exposes Kel progress, approvals, project notes, test commands, reports and checked apply. The report uses the donor markdown renderer and drawer controls.

`KelService.ts` connects the donor host to Kel. The authentication token stays in the main process. `kel/acp_host.py` handles ACP requests, session continuity, attachments and cancellation. Windows ACP text uses UTF-8.

Existing Kel chats retain their original Kel conversation IDs. Donor history combines imported records with donor messages. Recovery adds replies completed while the window was closed. It also refreshes stale work progress. Ordered matching consumes repeated native replies once; imported message IDs remain stable.

Kel's durable engine remains active when the window closes. VERIFIED comes from Kel's tests, evidence and review. ACP end-of-turn does not establish success.

Keyboard access was added to retained donor New Chat, conversation and Settings controls. Nested report Escape closes only the report.

## Boundaries

This is a Windows desktop build. It keeps Kel's single-assistant scope. Personal-life features remain outside V1.

Donor transcript export is not exposed by this upstream version. Checked reports can be viewed and downloaded. Native file picking was tested; paste and drop attachment branches were not tested.

The package uses Electron 44.3.0, matching the runtime already used by Kel. It includes bundled AionCore and the Kel engine. Installed provider tools and sign-in remain necessary. No credentials are packaged.

The prior 0.4.0 app remains available for rollback. Its visual reviews do not establish the quality of this release. See the current QA log and independent review.

## Modified donor files

- `package.json`
- `packages/desktop/src/index.ts`
- `packages/desktop/src/preload/main.ts`
- `packages/desktop/src/process/utils/configureChromium.ts`
- `packages/desktop/src/process/utils/deepLink.ts`
- `packages/desktop/src/process/utils/windowBounds.ts`
- `packages/desktop/src/renderer/components/agent/AcpModelSelector.tsx`
- `packages/desktop/src/renderer/components/layout/Layout.tsx`
- `packages/desktop/src/renderer/components/layout/Sider/SiderFooter.tsx`
- `packages/desktop/src/renderer/components/layout/Sider/SiderNav/SiderToolbar.tsx`
- `packages/desktop/src/renderer/components/layout/Sider/index.tsx`
- `packages/desktop/src/renderer/components/layout/Titlebar/index.tsx`
- `packages/desktop/src/renderer/pages/conversation/GroupedHistory/ConversationRow.tsx`
- `packages/desktop/src/renderer/pages/conversation/GroupedHistory/ConversationSearchPopover.tsx`
- `packages/desktop/src/renderer/pages/conversation/Messages/hooks.ts`
- `packages/desktop/src/renderer/pages/conversation/components/ChatConversation.tsx`
- `packages/desktop/src/renderer/pages/guid/GuidPage.tsx`
- `packages/desktop/src/renderer/pages/guid/hooks/useCustomAgentsLoader.ts`
- `packages/desktop/src/renderer/pages/settings/components/SettingsSider.tsx`
- `packages/desktop/src/renderer/services/i18n/i18n-keys.d.ts`
- `packages/desktop/src/renderer/services/i18n/locales/de-DE/common.json`
- `packages/desktop/src/renderer/services/i18n/locales/en-US/common.json`
- `packages/desktop/src/renderer/services/i18n/locales/en-US/conversation.json`
- `packages/desktop/src/renderer/services/i18n/locales/es-ES/common.json`
- `packages/desktop/src/renderer/services/i18n/locales/fa-IR/common.json`
- `packages/desktop/src/renderer/services/i18n/locales/fr-FR/common.json`
- `packages/desktop/src/renderer/services/i18n/locales/ja-JP/common.json`
- `packages/desktop/src/renderer/services/i18n/locales/ko-KR/common.json`
- `packages/desktop/src/renderer/services/i18n/locales/pt-BR/common.json`
- `packages/desktop/src/renderer/services/i18n/locales/ru-RU/common.json`
- `packages/desktop/src/renderer/services/i18n/locales/tr-TR/common.json`
- `packages/desktop/src/renderer/services/i18n/locales/uk-UA/common.json`
- `packages/desktop/src/renderer/services/i18n/locales/zh-CN/common.json`
- `packages/desktop/src/renderer/services/i18n/locales/zh-TW/common.json`
- `packages/desktop/src/renderer/utils/chat/messagePagination.ts`
- `packages/desktop/src/process/services/kel/KelService.ts`
- `packages/desktop/src/process/services/kel/reconcileHistory.ts`
- `packages/desktop/src/renderer/components/chat/KelWorkPanel.tsx`
- `packages/desktop/src/renderer/utils/chat/kelHistory.ts`
- `packages/desktop/src/renderer/utils/chat/kelHistorySearch.ts`
- `tests/unit/kelHistory.test.ts`
- `tests/unit/kelHistorySearch.test.ts`
- `tests/unit/kelRecoveryHistory.test.ts`
