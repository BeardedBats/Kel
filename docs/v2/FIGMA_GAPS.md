# Active Figma gaps after audit 2

**2026-09-23 update:** this file is a historical audit of the older `76:2` page. The current FINAL desktop page is `185:2`, and Figma now has 28 mobile screens on `213:2`. The [51-screen audit](evidence/figma-full-audit/README.md) supersedes the “No mobile final frame” row and tracks current gaps.

Source: Kel Design System `BlpVvZGuc9j9HhxUojIiJI`, final screens on page `76:2`.
Audit 2 supersedes the earlier sidebar, extra-card, and placeholder-copy decisions.

| State | Source | Current decision / limit | Location |
|---|---|---|---|
| Hidden template descriptions and Add Theme actions | Effective visibility through every ancestor of final frames | Copy visible strings literally. Do not render hidden component defaults. The earlier question incorrectly described hidden layers as visible copy; the audit corrected that error. | `ShellSourceCardHeader.tsx`, `evidence/audit-2/figma-visible-copy.json` |
| Typography conflict with older Inter frames | User's DS v2 Foundations image | Instrument Sans for headings, navigation and controls; SF Pro Text for body/meta. No Inter. | `kelFonts.ts`, `kel-shell.css` |
| Sidebar entry points absent from the reference | Home `94:1585` | Latest instruction governs: remove extra primary navigation, Tools, project groups and footer. Preserve route implementations and Kibble shortcut. | `Sider/index.tsx`, `GroupedHistory/index.tsx` |
| Empty and populated live data differ from sample data | Home, Work, Projects, Providers and Scheduled frames | Read existing state. No sample conversations, fake provider readiness, sample tasks, prices, token counts or context percentages in production. | Existing state hooks, `ShellComposerMetrics.tsx` |
| Usage not reported by runtime | Home/Chat footer | Keep the source field arrangement and show an em dash. Remaining context is unknown without a reported limit. | `ShellComposerMetrics.tsx` |
| No mobile final frame | Desktop 1440 x 900 frames | Retain the existing drawer and control sheet. Wrap footer fields and controls; retain 44px touch targets. | `kel-shell.css` |
| Native window controls absent from screenshot | Existing desktop titlebar | Keep window and navigation controls. Ramble's document returns to the source y68 position. | Existing titlebar, `kel-shell.css` |
| Native-only Settings operations in WebUI | WebUI and Pet frames | Desktop-only controls retain runtime support rules. Browser Pet reports its native requirement. | `WebuiModalContent.tsx`, `PetSettings.tsx` |
| Diagnostics Clear and Restart have no matching safe runtime operations | Diagnostics `76:4130` | Source controls are present and disabled. Do not relabel unrelated destructive purge/compaction operations. | `diagnostics/index.tsx` |
| Onboarding autonomy selector has no matching writable mode contract | Setup `123:1789` | Source label opens existing Permissions. Completion remains persisted. Change opens existing Projects. No new permissions engine. | `onboarding/index.tsx` |
| Backup and restore require folder input | System `124:2028` | Source row buttons open a folder-path dialog and retain existing backup/inspect/restore handlers and confirmation. | `KelDataCard.tsx` |
| Populated integrations require setup details | Providers `76:3996` | Compact source rows expand to real credential controls. No separate extra-tools card. | `providers/index.tsx` |
| Model provider-specific required fields | Model `76:3222` | Default modal uses four source fields. Bedrock/New API may show required provider-specific fields. Existing validation remains. | `AddPlatformModal.tsx` |
| Retired Assistants and Skills routes | `76:3474`, `76:3503` | Existing redirects remain. These two frames are not restored by this presentation pass and remain a known scope gap. | Existing `Router.tsx` |
| Source panel raster cannot be recovered through the connector | Theme panel `76:3173` | Connector returned a transparent 32px placeholder for the image fill. The shell uses source canvas assets and mapped glass fills. Exact raster parity is not claimed. | `assets/figma/canvas.svg`, `kel-shell.css` |
| Anonymous direct-route WebUI startup | Fresh unauthenticated `/guid` | Intermittent blank startup was observed without a page error. The visual audit starts through `/login`; this startup issue is not claimed fixed. | Existing WebUI authentication/startup |
| No reference for Kibble or Connections | Nearest DS cards/buttons | Existing routes retain their behavior with shared shell styling. | `dogfood/index.tsx`, Connections |

Audit evidence and checks: [SHELL_AUDIT_2.md](SHELL_AUDIT_2.md).
