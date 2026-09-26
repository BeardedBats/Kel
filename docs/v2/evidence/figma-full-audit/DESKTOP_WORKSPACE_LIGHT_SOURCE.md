# Desktop Workspace header and Light file surfaces — 2026-09-26

Current Figma Workspace `273:13249` and File preview `273:13459` were refreshed directly. Dark geometry and existing assets remain in place. Light uses the existing semantic palette; current Figma Foundations provide no complete Light palette.

The older folder-chat header now says Workspace on desktop and uses the existing 16px/20px heading role. It reserves 48px for native Windows controls. Narrow rail CSS now excludes the right workspace. Previously it forced a closed workspace to remain 180px wide at 800px. The right panel now follows its real layout width and collapses to zero. The left rail remains 180px at the narrow desktop width. Mobile headers and behavior remain unchanged.

Real isolated folder-chat checks passed Dark and Light at 1440px and 800px. The header starts at y48 below the controls ending at y42. Expanded panels measure 340px and 260px; Close and Reopen pass through the actual titlebar control. Document overflow and renderer errors are zero. Prior workspace preferences were restored.

Light Workspace now has readable file rows, Files/Changes controls, changed-file labels, selected rows, heading actions and footer buttons. Light File preview now has readable file tabs, view controls, action menus, status, CodeMirror gutters and code backgrounds. Neutral assets retain their original geometry and receive the existing Light tint. CodeMirror retains its Light syntax colors and behavior. All surfaces use full neutral borders; no accent rails were added.

The existing synthetic project supplied actual files and three SCM changes. Light Workspace Files/Changes and heading action menu passed both widths. A real file read supplied the preview. Read-only Preview resisted input; Code/split controls passed. No file was edited or saved, attached to chat, downloaded or revealed through the OS. Legacy history was intercepted only for the isolated conversation in the source preview; file/SCM reads remained real.

Measured Light label contrast was at least 5.39:1 across 74 sampled labels, including syntax spans and gutter labels. Disabled controls and pixel-level icon contrast are excluded. Preview buttons stay inside the pane at both widths; overflow and renderer errors are zero. Isolated panel/preview preferences were restored and Dark was restored. All probe apps closed.

TypeScript, source build and 11 focused Workspace/theme/input tests across three files passed. The latest broader suite remains 63 files / 443 tests from the preceding Setup behavior batch; it was not repeated for these presentation changes. Package proof waits for the next larger milestone. Canonical App remains `8c67121`; Data untouched. Mobile paused. Broader populated Chat placement/typography and retained Tools/task/Light dialog states remain open. `request_review` was unavailable; no independent review is claimed.

Captures: [legacy Dark 1440](DESKTOP_LEGACY_WORKSPACE_DARK_1440.png), [800](DESKTOP_LEGACY_WORKSPACE_DARK_800.png); [legacy Light 1440](DESKTOP_LEGACY_WORKSPACE_LIGHT_1440.png), [800](DESKTOP_LEGACY_WORKSPACE_LIGHT_800.png); [Light Files 1440](DESKTOP_LIGHT_WORKSPACE_SOURCE_1440.png), [800](DESKTOP_LIGHT_WORKSPACE_SOURCE_800.png); [Light preview 1440](DESKTOP_LIGHT_FILE_PREVIEW_SOURCE_1440.png), [800](DESKTOP_LIGHT_FILE_PREVIEW_SOURCE_800.png).
