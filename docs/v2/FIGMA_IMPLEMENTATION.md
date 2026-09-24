# Kel V2 shell implementation — audit 2

**2026-09-23 update:** this is the prior shell record. The [current 51-screen audit](evidence/figma-full-audit/README.md) covers desktop FINAL `185:2` and mobile FINAL `213:2`. Its mobile page and component findings supersede this record's “no mobile frame” statement.

September 22 amendment: [plain status text](STATUS_TEXT_POLISH.md) replaces chip containers, following the user's latest reference.

Base dev/v2: `772b2c357943cf9793639bbf660171c49d809c38`.
Branch: `ux/v2-shell`. Worktree: `C:/Users/Nick/Desktop/Kel/kel-v2-shell`.

[Audit and delivery record](SHELL_AUDIT_2.md) · [Current gaps](FIGMA_GAPS.md) · [Source tokens](FIGMA_TOKENS.md) · [Architecture](SHELL_ARCHITECTURE.md)

## Source authority

[Figma: Kel Design System](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=76-2).
File `BlpVvZGuc9j9HhxUojIiJI`; final screens `76:2`; components `136:2`; foundations `139:2`.
The final page has 22 desktop frames, including two System variants. There is no mobile frame.

The user's latest instructions control conflicts: Instrument Sans/SF Pro Text, Settings `#FFD497`, New Chat status dots/checkmark, exact sidebar, no top chat ellipsis, and literal visible source text.

The earlier extraction included hidden component defaults. Audit 2 checks ancestor visibility. Repeated theme/GPU descriptions and Add Theme actions are not rendered where hidden in Figma. [Visible copy extraction](evidence/audit-2/figma-visible-copy.json) is the current authority. No Figma content was edited.

## Current surface map

Production captures use the built renderer and isolated engine state. Named fixtures exist only in browser tests. Live data replaces source sample data; missing measurements remain unknown.

| Source | Production surface | Evidence / status |
|---|---|---|
| Home `94:1585` | `/guid` | [Home](evidence/audit-2/1440-home.png). Source attention rows, status colors and composer/footer. Actual history and readiness. |
| Chat `76:3001` | `/conversation/:id` | [Fixture](evidence/audit-2/1440-chat-fixture.png). Model selector inside composer, body type and copy controls. |
| Appearance `76:3154` | `/settings/appearance` | [Appearance](evidence/audit-2/1440-appearance.png). Theme panel 180px and Colors panel 458px; source rows and controls. |
| Model `76:3222` | `/settings/model` | [Model](evidence/audit-2/1440-model.png), [dialog](evidence/audit-2/1440-model-dialog.png). Actual models; four default fields, provider-specific requirements retained. |
| Tools `76:3318` | `/settings/tools` | [Tools](evidence/audit-2/1440-tools.png). Source sections and real toggles. |
| WebUI `76:3357` | `/settings/webui` | [Native](evidence/audit-2/electron-remote.png). Source setup/credential rows. Browser retains runtime support restrictions. |
| Pet `76:3401` | `/settings/pet` | [Native](evidence/audit-2/electron-pet.png). Browser states its desktop requirement. |
| Archived `76:3445` | `/settings/archived` | [Archived](evidence/audit-2/1440-archived.png). Source empty layout; existing archived actions retained. |
| Assistants `76:3474` | Retired route | Existing redirect remains. Known unimplemented frame. |
| Skills `76:3503` | Retired route | Existing redirect remains. Known unimplemented frame. |
| About `76:3540` | `/settings/about` | [Native](evidence/audit-2/electron-about.png). Actual version, runtime and data folder. |
| Work `76:3578` | `/work` | [Work](evidence/audit-2/1440-work.png). Three source cards and real job actions. |
| Permissions `76:3789` | `/autonomy` | [Permissions](evidence/audit-2/1440-permissions.png). Three source cards; Run check exposes existing advanced controls. |
| Projects `76:3893` | `/projects` | [Projects](evidence/audit-2/1440-projects.png). Knowledge, map and recipes; deep links remain. |
| Providers `76:3996` | `/providers` | [Providers](evidence/audit-2/1440-providers.png). Compact expandable integrations and real preflight/credential state. |
| Diagnostics `76:4130` | `/diagnostics` | [Diagnostics](evidence/audit-2/1440-diagnostics.png). Three source cards. Clear/Restart disabled; report export uses existing handler. |
| Scheduled `76:4389` | `/scheduled` | [Selected fixture](evidence/audit-2/1440-scheduled-fixture.png). Stacked list/detail, stored instructions and existing conversation link. |
| Ramble `76:4603` | `/transcription` | [Ramble](evidence/audit-2/1440-ramble.png). Source library/document layout; existing recording/upload/copy/download/combine. |
| Activity `84:1399` | `/activity` | [Activity](evidence/audit-2/1440-activity.png). Three source cards and actual state. |
| System `124:2028` | `/settings/system` | [Native](evidence/audit-2/electron-system.png). Data & backup and General; Keep computer awake inline. |
| Earlier System `112:10259` | Same route | Superseded by `124:2028` for this audit. |
| Setup `123:1789` | `/onboarding` | [Setup](evidence/audit-2/1440-onboarding.png). Five sections. Existing completion persistence and provider/project/permission routes. |
| No source | `/dogfood`, `/connections` | [Kibble](evidence/audit-2/1440-kibble.png), [Connections](evidence/audit-2/1440-connections.png). Shared shell styling; existing handlers. |

## Components and behavior

Source exports provide the canvas, Kel mark, settings icons, composer icons and status checkmark. Existing source tokens remain. `ShellSourceCardHeader` applies visible card copy; `ShellComposerMetrics` renders reported usage or an em dash.

New Chat, Settings, Pinned and Recent follow the latest sidebar reference. The added Tools group, footer and extra primary navigation are removed. Ramble and Kibble routes and the Kibble capture shortcut remain. This follows the newer sidebar instruction over the original Tools-group requirement.

Model/mode, attachments, draft/IME/paste, queue and message handlers remain connected. Default views omit source-absent controls. Backup folder paths and export choices open dialogs. Scheduled rows now select an inline detail card; existing detail routes remain available. No engine, provider or permissions architecture changed in audit 2.

## Verification and limits

[Audit 2](SHELL_AUDIT_2.md) records exact test counts and runner reports. Screenshots include desktop, responsive widths, theme changes, keyboard states, model dialog, chat and scheduled fixtures, and native Electron Settings. Geometry sidecars accompany browser captures.

TypeScript, build, full desktop tests, browser checks and native checks have separate evidence. No live model/Muse request, restore, cache clear or runtime restart was executed. No installer was created. Protected Dogfood directories were not changed.

Exact pixel parity is not claimed. The source panel raster is unavailable through the connector; two retired frames remain unimplemented. Live data, unknown telemetry, native window controls and runtime support can differ from the source sample. The current gap table records these limits and the intermittent anonymous WebUI startup issue.

Historical evidence remains under `evidence/shell` and `evidence/figma`. Current audit captures are under `evidence/audit-2`.
