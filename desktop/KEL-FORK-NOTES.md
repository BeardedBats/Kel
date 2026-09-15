# Kel fork notes (desktop / Aion Donor Shell)

- Upstream: https://github.com/iOfficeAI/AionUi
- Fork base revision: 6744099b279b991c17e31c243f0920477bd31cb6 (source version 2.2.2)
- License: Apache-2.0 (`desktop/LICENSE`). This is a Kel adaptation, not an official AionUI release.
- Role: the desktop shell source used to build the Kel 0.5.0 (V1.x) application.

## Kel modifications relative to upstream

These were working-tree changes at fork time; they are now plain files in this repository:

- Engine bridge: `packages/desktop/src/process/services/kel/KelService.ts` (engine launch and
  staging, ACP agent registration, drain-on-quit) plus related preload/renderer changes.
- Branding: product name "Kel", window title, About copy; donor agent/team/skill surfaces hidden;
  retained settings only.
- Renderer: Work-context drawer (`KelWorkPanel`), approval badge, history recovery, ACP tool-card
  merge (`pages/conversation/Messages/hooks.ts` - getMessageMergeKey by tool_call_id), keyboard
  access.
- Builder configs: `kel-builder.json`, `kel-runtime-builder.json` (repo-relative here; outputs to
  `../dist/*`).

## Repository-relative adjustments made during consolidation

- `KelService.ts`: dev fallback source root is now `../runtime` (previously an absolute
  recovery-workspace path); `KEL_PYTHON` fallback is `python` (previously an absolute path).
- Builder configs: `electronDist` -> `node_modules/electron/dist`; stage -> `../shell-stage`;
  outputs -> `../dist/package[-final]`; engine input -> `../dist/runtime/KelEngine`.
- Donor media files, nested `node_modules`, build outputs and agent/CI config files were removed
  from this repository copy.

## Packaging prerequisites

The full packaged release also needs the AionCore binary
(`resources/bundled-aioncore/win32-x64/aioncore.exe`, not stored in git) and the built Kel
Runtime. See the root README ("Building the desktop shell" and "Packaging app.asar").

## Local fonts (licensed; not committed)

The shell loads two local font families at runtime:

- **Sohne** — header/display font (weights 400/500/600/700) from `public/fonts/sohne/`.
- **SF Pro Text** — body font (weights 400/500/600/700) from `public/fonts/sf-pro-text/`.

The files are deliberately git-ignored (`desktop/public/fonts/**/*.otf`): Söhne is © Klim
Type Foundry and SF Pro is © Apple Inc., licensed for local use only — never commit them.
Copy the font files into those folders (see `public/fonts/README.md`) before building; without
them the app still builds and runs with the system fallback stack. Registration happens in
`packages/desktop/src/renderer/utils/theme/kelFonts.ts`; the display token
(`--kel-font-display`) and the `h1–h6` rule live in
`packages/desktop/src/renderer/styles/arco-override.css`.
