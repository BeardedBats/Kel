# Kel V2 shell implementation

Base dev/v2: `772b2c357943cf9793639bbf660171c49d809c38`.
Branch: `ux/v2-shell`. Worktree: `C:/Users/Nick/Desktop/Kel/kel-v2-shell`.
The base was the clean live dev/v2 HEAD when work began. The earlier coordination SHA was not used.
The worktree shares the repository object database. No merge or force push is part of this work.

## Source and method

[Figma: Kel Design System](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=136-2).
File `BlpVvZGuc9j9HhxUojIiJI`; final-screen page `76:2`; components `136:2`; foundations `139:2`.
The final-screen page contains 22 desktop frames at 1440 × 900. It contains no phone or tablet frame.

Source component code, dimensions and variable values were read through Figma tools before implementation.
Original extractions and reference screenshots are in [evidence/figma](evidence/figma).
The canvas, Kel mark, composer icons and eight settings icons use source exports.
[Figma tokens](FIGMA_TOKENS.md) records source variable IDs and code values.
[Architecture](SHELL_ARCHITECTURE.md) records the renderer audit and behavior boundary.

The user explicitly selected DS v2 Foundations typography over older screen instances. Instrument Sans governs headings, labels and buttons; SF Pro Text governs body, metadata and transcripts. Inter is not used or bundled. The lighter final card fill remains unchanged. Instrument Sans includes its OFL license. Existing SF Pro Text files remain in the repository.

## Surface map

Screenshots below use the built production renderer and isolated real engine state, except the named conversation fixture.
A source sample is not production data. Empty history, missing setup, built-in recipes and unavailable capabilities are shown honestly.

| Source frame | Production surface | Implementation and evidence | State differences |
|---|---|---|---|
| Home `94:1585` | `/guid` | [Home](evidence/shell/1440-home.png), [native](evidence/shell/electron-home.png) | Real attention, model hold, prompt actions and workspace control; no fake usage totals |
| Chat `76:3001` | `/conversation/:id` | [Chat fixture](evidence/shell/1440-chat-fixture.png), [phone](evidence/shell/393-chat-fixture.png) | Isolated test messages and pinned/recent rows; live send hooks retained |
| Appearance `76:3154` | `/settings/appearance` | [Appearance](evidence/shell/1440-appearance.png) | Existing fonts, custom CSS, theme additions and all color controls retained |
| Model `76:3222` | `/settings/model` | [Model](evidence/shell/1440-model.png), [modal](evidence/shell/1440-model-dialog.png) | Required provider controls make modal height content-dependent |
| Tools `76:3318` | `/settings/tools` | [Tools settings](evidence/shell/1440-tools.png) | Real capability state and existing toggles |
| WebUI `76:3357` | `/settings/webui` | [Browser](evidence/shell/1440-remote.png), [native](evidence/shell/electron-remote.png) | Desktop-only server controls, read/copy/edit credentials and remote-access explanation retained; cards grow with these controls |
| Desktop Pet `76:3401` | `/settings/pet` | [Native pet](evidence/shell/electron-pet.png) | Existing runtime support rules retained |
| Archived `76:3445` | `/settings/archived` | [Archived](evidence/shell/1440-archived.png) | Real empty state in isolated data |
| Assistants `76:3474` | Existing retired route | Existing redirect retained | No restoration of a retired product surface |
| Skills `76:3503` | Existing retired route | Existing redirect retained | Skills controls remain in existing supported flows |
| About `76:3540` | `/settings/about` | [Native About](evidence/shell/electron-about.png) | Actual version, runtime and license; Open System for folder actions |
| Work `76:3578` | `/work` | [Work](evidence/shell/1440-work.png) | Real attention can add a card; job actions and recovery retained |
| Permissions `76:3789` | `/autonomy` | [Permissions](evidence/shell/1440-permissions.png) | Real guardrail digest, emergency stop and advanced checks retained |
| Projects `76:3893` | `/projects`, knowledge/map/recipes links | [Projects](evidence/shell/1440-projects.png) | All three panels; real built-in recipes replace the source empty sample |
| Providers `76:3996` | `/providers` | [Providers](evidence/shell/1440-providers.png) | Compact expandable integrations; no invented passing preflight results |
| Diagnostics `76:4130` | `/diagnostics` | [Diagnostics](evidence/shell/1440-diagnostics.png) | Real diagnostic rows and actions; content exceeds the sample |
| Scheduled `76:4389` | `/scheduled` | [Scheduled](evidence/shell/1440-scheduled.png) | Existing list/detail routes and scheduling controls retained |
| Transcriptions `76:4603` | `/transcription` → Ramble | [Ramble](evidence/shell/1440-ramble.png) | Source library/document layout; real empty library and key controls; 22px toolbar clearance for window controls |
| Activity `84:1399` | `/activity` | [Activity](evidence/shell/1440-activity.png) | Real active/waiting/completed state; no invented running job |
| System `112:10259` | `/settings/system` | [Native System](evidence/shell/electron-system.png) | Amber-title source chosen; real backup and restore path fields retained |
| Onboarding `123:1789` | `/onboarding` | [Setup](evidence/shell/1440-onboarding.png) | Five sections, real providers and project; existing Permissions route replaces unsupported mode select |
| System alternative `124:2028` | Same System route | Conflicting alternate recorded | Not a second production screen; amber-title frame governs |
| No source frame | `/dogfood` → Kibble | [Kibble](evidence/shell/1440-kibble.png) | Canonical cards and buttons; existing capture review and prompt preparation |
| No source frame | `/connections` | [Connections](evidence/shell/1440-connections.png) | Existing actions and real state with shared shell tokens |

## Shared components and states

- `figma-variables.css`: original source variables; `kel-shell.css`: final instances and responsive mapping.
- `ShellNavRow`, `ShellWorkspaceLink`, `ShellSettingsIcon`: native controls and exact source assets.
- `KelToolsSection`: a small registry for Ramble and Kibble. New tools can join the same section.
- Existing Kel cards, buttons, inputs, chips, tables and Arco dialogs keep their behavior.
- New Chat maps default, hover and pressed source gradients. Keyboard focus uses the source focus color.
- History maps selected, unread, read and attention states. Pin ordering, batch actions, menus and generation stay connected.
- Messages retain copy and capability-gated fork actions. Touch users can reach both without hover.
- Composers retain draft state, attachments, IME, paste, queue, cancellation, model choice and Muse hooks.
- Empty, loading, failure, success and retry states use real API state and existing state machines.
- Reduced-motion rules suppress optional animation. Phone controls use 44px targets where required.

## Responsive evidence

[1920px](evidence/shell/1920-home.png), [1440px](evidence/shell/1440-home.png), [1024px](evidence/shell/1024-home.png),
[393px](evidence/shell/393-home.png), [360px](evidence/shell/360-home.png).

At phone widths, the existing navigation drawer and composer sheet remain in use. The later Work & context transport repair has an additional affected mobile run.
The Tools selection closes the drawer. Ramble stacks its library and document at 980px.
The library scrolls independently when controls exceed its phone area. No alternate tablet navigation was added.
Browser tests assert page overflow for every recorded view. These are Chromium viewport checks, not physical iPhone or Safari certification.

## Verification

The reports below contain the commands or runner output from the final checks.

- [TypeScript](evidence/shell-tsc.txt): `tsc --noEmit`, exit 0.
- [Desktop suite](evidence/shell-full-tests.txt): full Vitest suite: 47 files, 367 tests passed.
- [Build](evidence/shell-build.txt): `bun run package`, Electron main/preload and renderer, exit 0. The existing large-chunk warning remains.
- [Browser checks](evidence/shell-browser-tests.txt): 12 passed: built routes, five widths, navigation, copy, theme changes, modal geometry, Foundations typography and keyboard capture.
- [Native checks](evidence/shell-electron-tests.txt): 1 passed against the final build: Electron startup, isolated data root, native settings and capture shortcut.
- [Existing mobile journeys](evidence/shell-mobile-tests.txt): 5 passed, affected A/B/C/D/F flows, including the final Work & context transport repair.
- [Standalone ACP regression](evidence/shell-acp-tests.txt): 23 passing tests, including direct script initialization.

New unit regressions cover navigation, Ramble/Kibble routes, phone drawer closure, composer input/paste/IME, attachments,
Ramble/model browser transport and theme override cleanup. Browser fixtures remain isolated from production data.

Visual review compares exported source PNGs with the actual built application. Geometry sidecars accompany each browser screenshot.
Differences caused by real content are listed above and in [FIGMA_GAPS](FIGMA_GAPS.md).
Screenshots do not establish live paid-provider output, Muse service success, physical-phone behavior or every populated recovery state.
The existing mobile journey B covers paste, send bounds and Work & context. Its pre-existing Phone journey seed is absent from the isolated data root, so that populated-conversation substep is unverified; the separate browser fixture verifies message rendering and copy.
The PWA journey recorded one conversation fetch console error while its manifest, service worker, API cache exclusion and overflow assertions passed. The report preserves that diagnostic; this is not a claim of a console-clean session.
No provider keys were added for this work. No messages were sent to paid providers.

## Measured visual review

Source exports and built screenshots were inspected directly. This is a manual source comparison plus measured DOM geometry, not a zero-difference image assertion.
The user-selected typography overrides the older final-frame font instances. Real data and preserved production controls account for the documented content differences.

| Element at 1440 x 900 | Source | Built result |
|---|---|---|
| Main sidebar | 256px | 256px |
| Main content | x388, width920 | x388, width920 |
| Home composer | x388, y786, 920x60, radius12 | x388, y786, 920x60, radius12 |
| Activity card width | 600px | 600px |
| Model dialog | x588, width520, radius16 | x588, width520, radius16; extra form fields increase height |
| Ramble library | 272px | 272px |
| Ramble document | x328, y68, width1056 | x328, y90, width1056; native toolbar clearance |
| Page title | Foundations Instrument Sans 600, 26/32 | Browser assertion passes |
| Card title | Foundations Instrument Sans 700, 15/20, #FFC481 | Browser assertion passes |
| Message body | Foundations SF Pro Text 400, 16/25 | Desktop and phone assertions pass |

The default, hover, pressed and keyboard-focus New Chat states have separate captures.
The archive duplicate title, chat header fill, composer sizing, model dialog width/centering, and Ramble phone folder access were corrected during direct review.

## Runtime boundary and disk state

[Shared changes](SHELL_SHARED_CHANGES.md) records the complete behavior boundary.
The Python change repairs a standalone import used during native ACP initialization. The WebUI change keeps a socket error listener active during upgrade rejection. Both have isolated commits and regressions.
No engine architecture, security policy or storage schema was redesigned.

No installer or permanent candidate was created. Native checks launch the built `desktop/out/main/index.js` with a worktree-local Electron runtime.
Temporary engine, WebUI and Electron data remain under `.shell-run`. Reproducible `desktop/out`, test results and private `.shell-*.log` files also remain. Automatic approval review rejected both the bounded cleanup command and the explicit-path cleanup command with `blocked by policy`; no deletion ran. The owned engine and WebUI processes were stopped. These scratch files are not staged or pushed.
Cleanup is outstanding, so the final clean-worktree completion condition is not met. One active worktree dependency tree remains.
The protected KelDogfoodCandidate and KelDogfoodRuns/prepared paths were not modified.
