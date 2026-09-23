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

## Integrated into `integration/v2` (PR #4)

The CSS repair was reviewed and **cherry-picked** from PR #4's `6a3df71` onto
`integration/v2` as `e96df91` (the PR branch itself lagged `integration/v2` by the r19
manifest fix and carried two now-redundant merge commits, so the branch was not merged
wholesale). The same commit is part of the combined candidate **r20**
(`docs/v2/evidence/v2-19/CANDIDATE_R20.md`), which carries both this repair and the r19
manifest fix.

What is **superseded** in the records above:

- The hashes in the table above describe `C:\Users\Nick\KelV2CanvasCandidate` — the
  verification copy of the original PR. That copy is preserved for reference, but it is
  no longer the newest candidate; r20 is.
- "r18 remains at `C:\Users\Nick\KelV2Candidate`" described the state at PR time. The
  candidate at that path is now r20 (`b4235af7…` r18 is at `…\.r18`, `75ef03c0…` r17 at
  `…\.r17`).
- The PR branch's own copy of this document stopped at the section above; this section is
  the integration record.

Still open after the repair (unchanged by it): the theme-card wrapping visible in the
comparison screenshot, and the V2-16 conversation-open / project-switch timings that need
a signed-in session.
