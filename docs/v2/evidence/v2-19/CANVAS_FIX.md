# Dark canvas repair

The installed r18 candidate showed a flat gray canvas when its Dark theme had a saved
`App background` color of `#282a34`. The Figma Settings reference shows a layered navy
canvas and an `App background` value of `#0a1e42`. The user's saved value remains untouched.

## Preservation contract

The Figma canvas artwork, dark typography, navigation, glass surfaces, chat state,
theme controls, and stored theme overrides remain in place. This repair changes only
the dark shell background composition.

## Cause and change

`applyTheme` maps a saved `--bg-base` color to `--kel-shell-custom-canvas`. The old
`background: var(--kel-shell-custom-canvas, <Figma layers>)` selected that solid color
instead of every Figma layer. The shell now paints the original SVG and gradients in
all cases. A saved color supplies the fallback base and a 20% tint. Clearing the
override restores the original untinted canvas. No preference is migrated or erased.

## Checks

| Check | Result |
| --- | --- |
| Focused theme test | 1 passed |
| Renderer production build after the data-root repair | passed |
| Archive gate | manifest parsed; 7 referenced bundles present; `out/main/index.js` and `out/renderer/index.html` match the build; canvas CSS and SVG are present |
| Installed-copy launch | window title `Kel`; dark theme and `#282a34` override; computed background retains SVG and gradients |
| Background sample at right edge | installed copy `(29,38,67)` versus Figma `(29,35,64)` at normalized `(0.95,0.1)`; `(34,39,63)` versus `(32,40,67)` at `(0.95,0.9)` |

Local screenshots are under `C:\Users\Nick\KelV2Runs\prepared\canvas-evidence`.
The installed-app capture stays out of Git because it contains conversation titles.

The installed copy is `C:\Users\Nick\KelV2CanvasCandidate`. Its launcher uses the
same V2 candidate data roots as r18, and refuses to start while another `Kel.exe`
runs. r18 remains at `C:\Users\Nick\KelV2Candidate`.

| File | SHA-256 |
| --- | --- |
| `Kel.exe` | `7db1c8832c352e98a32f7ec67711e51019ef7a7a8986ca6d035b278955c314ae` |
| `resources/app.asar` | `01088642639d804f44b4f9d0576325ab170c1e65c1510191f763471eb342d167` |
| `resources/kel-engine/KelEngine.exe` | `00846a7e64fdaa9589a22abcf225340f254fd16a963725255019d66cb17ebd52` |

This is a targeted background repair. It does not change the saved `#282a34` color
to Figma's `#0a1e42`, and it does not address the separate theme-card wrapping
visible in the comparison screenshot.
