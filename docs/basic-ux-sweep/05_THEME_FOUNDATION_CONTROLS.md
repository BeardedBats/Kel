# Theme foundation controls

## What existed (audit)

- Theme gallery (Light / Dark / Follow System) with live switching; user CSS themes for power
  users; per-region fonts and a scale control.
- **No semantic color controls**: `colorInputs = 0`, no “Theme colors” surface (audit).

## Implemented

- **Storage**: `theme.overrides` config — `{ themeId: { '--token': '#rrggbb' } }`. Built-in theme
  definitions are never mutated; overrides are a third layer over
  `selected theme → base tokens → user overrides → resolved theme`.
- **Application**: `applyTheme` merges overrides for the active theme into the token CSS and
  re-applies immediately on change; Electron windows receive the same resolved theme.
- **UI**: Settings · Appearance → “Theme colors”: ten semantic rows (App background, Panels,
  Elevated surfaces, Primary text, Secondary text, Borders, Accent, Success, Warning, Error) with a
  color picker, hex field, per-token Reset, a “More colors” disclosure for the remaining tokens,
  and “Restore all colors”. Changes apply instantly and are saved to the selected theme only.
- **Safety**: live contrast checks warn (never block, never rewrite) when text tokens fall below
  comfortable ratios, and when Success/Warning/Error stop being distinguishable. Focus and
  selected-state colours come from the same tokens, so they follow the user's palette.

Unchanged (and honoured): per-region font family/size steppers and the zoom scale control already
existed — verified, not rebuilt. Density presets stay optional (`01_EXPECTATION_MATRIX.md`).
