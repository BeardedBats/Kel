# Kel shell audit 2

Worktree: `C:\Users\Nick\Desktop\Kel\kel-v2-shell`
Branch: `ux/v2-shell`
Source: [Kel Design System](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=76-2), final screens, plus the user's Foundations and New Chat images.

## Authority and audit correction

The latest request controls presentation: match the screen layout and sidebar, use Settings `#FFD497`, use New Chat amber/ice-blue dots and green check, remove the top three-dot action, and copy visible text literally. Instrument Sans and SF Pro Text remain mandatory.

The initial text extraction included hidden Figma component defaults. This caused the misleading clarification about “Select or customize a theme”, “Add Theme” and GPU descriptions. The user selected literal copy. A subsequent screenshot and ancestor-visibility audit established that these repeated strings are hidden. The final implementation copies the actual visible source text and respects source visibility. No Figma content was edited.

- [Visible source text](evidence/audit-2/figma-visible-copy.json) is the current copy authority.
- `figma-copy.json` is the initial raw extraction, including hidden layers. It is retained only as audit history.
- [Current Work source screenshot](evidence/audit-2/figma-work-current.png) confirms the hidden descriptions/actions.
- [User's New Chat authority](evidence/audit-2/new-chat-authority.png).

## Changes

- Sidebar now contains the source New Chat, Settings, Pinned and Recent structure. Extra navigation, project grouping, sidebar footer and top batch ellipsis are removed.
- Settings sidebar uses the source 32px Back row, 28px menu rows and 2px gaps. Model begins at y151 and Appearance at y245 at 1440 x 900.
- Home uses source attention rows and the requested status colors/checkmark. Its card begins at x388/y112, width 920.
- Workspace headers and cards use source spacing. Work begins at x388/y112; its Jobs title is x409/y129.
- Work, Projects, Permissions, Activity and Providers remove extra summary cards and copy. Existing state and route handlers remain.
- Appearance uses source title-only sections, 200 x 116 theme tiles, color controls and font-size rows. Font family/weight selectors absent from the reference are removed from this view.
- System uses Data & backup plus General, with Keep computer awake inside General. Backup/restore folder inputs move into a dialog.
- WebUI uses the source setup label and credential-field layout. Passwords remain masked.
- Model uses compact availability rows and a compact custom-model empty state. The default dialog keeps the four source fields.
- Diagnostics uses Health, Measured performance and Maintenance. Export opens its existing report controls in a dialog.
- Scheduled tasks uses a source list plus selected detail card, connected to the existing scheduler and history.
- Ramble removes extra visible toolbar/document actions. Existing recording, upload, download, copy and combine handlers remain.
- Composer footer includes cost, tokens, cache and remaining-context fields. Unknown measurements show “—”. No source sample values were added to live data.
- Aionrs chat model selection moves into the composer; permission mode moves into its footer. The existing model and mode handlers remain. The empty draft-queue button stays hidden until a draft can be queued.

## Verification

- TypeScript and production build pass. The existing large-chunk build warning remains.
- Full desktop suite: 367 tests across 47 files pass. After the final chat move, the affected unit suite passed again: 280 tests across 41 files.
- Browser: 14/14 checks pass in `browser-audit.txt`. After the final scheduled spacing and composer button repair, both affected checks pass again in `browser-final-polish.txt`.
- Native: 1/1 final Electron check passes in `native-audit.txt`, including native Settings centering at x388.

An intermittent blank page occurred on a fresh unauthenticated WebUI direct route. No JavaScript error explained it. The authenticated audit now starts at `/login`; this does not establish a fix for anonymous direct-route startup. The limitation remains tracked in FIGMA_GAPS.

Screenshots cover 20 production routes, responsive widths 1920, 1024, 393 and 360, conversation fixtures, selected scheduled-task fixtures, theme changes, the model dialog, keyboard focus and native Settings. Fixture data exists only in automated tests.

## Limits

This is a presentation pass, not a claim that every reference is fully implemented. [FIGMA_GAPS.md](FIGMA_GAPS.md) lists the remaining gaps, including retired Assistants/Skills routes, native-only browser controls, unknown telemetry, disabled Diagnostics maintenance actions, and the unavailable source raster fill.

No live model request, Muse request, backup restore, cache clear or runtime restart was executed. No install package was produced. The protected Dogfood candidate and prepared directories were not modified.

## Required delivery record

| Item | Result |
|---|---|
| Base dev/v2 SHA | `772b2c357943cf9793639bbf660171c49d809c38` |
| Shell branch | `ux/v2-shell`; final SHA is reported with delivery |
| Figma source | `BlpVvZGuc9j9HhxUojIiJI`, final screens `76:2`, components `136:2`, foundations `139:2`; user typography and New Chat images override conflicts |
| Major surfaces | Home, Chat, Work, Projects, Activity, Permissions, Providers, Diagnostics, Scheduled, Ramble, Setup, Appearance, Model, Tools, WebUI, System, Pet, Archived and About |
| Shared components/tokens | Existing source exports and tokens; new `ShellSourceCardHeader`, `ShellComposerMetrics` and source checkmark; shared card/header/sidebar/composer styles |
| Tools, Ramble, Kibble | Latest exact-sidebar instruction removes the added Tools group. Ramble and Kibble routes and capture shortcut remain. No new backend behavior |
| Responsive result | Chromium at 1920, 1440, 1024, 393 and 360; drawer, composer sheet and no-page-overflow checks. No mobile Figma frame exists |
| Gaps | See the explicit current gap table, including unavailable raster fill and retired Assistants/Skills |
| Shared behavior | Existing APIs remain; scheduled selection shows existing task detail; backup paths and export options open dialogs; source-absent controls leave default views |
| Automated checks | Runner reports in `evidence/audit-2` distinguish full suite, final unit checks, browser and native checks |
| Visual evidence | Production captures and geometry sidecars for 20 routes plus fixture, theme, focus and native states |
| Known deviations | Exact pixel parity is not claimed: raster fill, live data, native chrome, retired routes and capability gaps remain |
| Package/install | No new installer or permanent candidate was created |
| GitHub | Normal push to `origin/ux/v2-shell`; no merge or force push |
| Disk/worktree | One existing shell worktree. No new clone, installer or node_modules. Existing scratch and build output remain because cleanup was blocked |

## Delivery and cleanup

Implementation commits:
- `8c31a91` — shell sidebar, source card header and composer.
- `4f0203136860012b291dfa630e54a29bb126b847` — Settings and workspace source layouts/copy.

The following audit commit contains the final test fixtures, reports, captures and this delivery record. Its SHA and remote confirmation are reported with delivery. Push target: `origin/ux/v2-shell`. No merge into `dev/v2`.

The owned gateway and engine sessions were stopped after verification. At handoff, scratch uses about 243 MiB, build output 14.4 MiB and this audit's evidence 35.3 MiB. Scratch is locally ignored; evidence is intentionally tracked. No extra install or dependency tree was created.

The earlier automatic approval review rejected deletion of the generated `.shell-run` and build-output directories. That cleanup was not retried through another method. Scratch and local logs are excluded from the commit.
