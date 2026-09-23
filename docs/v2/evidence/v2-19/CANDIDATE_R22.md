# Kel V2 candidate r22 — typed hex, opaque Dark palette, one-row theme cards

Built from `integration/v2` @ **`11928da`**, packed 2026-09-23 by **one** packer
(`electron-builder --config kel-builder.json --x64 --dir`, `PACK22_EXIT=0`, signed). Before the build:
typecheck clean (`bunx tsc --noEmit -p tsconfig.json`), desktop unit suite **42 files / 291 tests passed**
(`npx vitest run tests/unit`). The web-host suite was **not** re-run: its package is unchanged, and the
suite needs every Kel instance stopped while the user's r20 session is running.

**Review:** `AGENTS.md` asks for `request_review` checkpoints. That tool was **not available** in this
session, so **no independent review was performed** on this change or this candidate.

## What changed

| defect (from `UI_ACCEPTANCE_R21.md`) | file | change |
| --- | --- | --- |
| **D1** typing `#7a1f1f` saved `#77aa11` | `components/kel/ThemeColorsSection.tsx` | typing saves only a complete six-digit code; `#rgb` / `rgb()` are accepted on **Enter** or **blur**; an unparseable draft reverts without saving. Paste and Reset unchanged |
| **D2** palette see-through in Dark | `components/kel/KelCommandPalette.tsx`, `styles/kel-shell.css` | the palette gets `.kel-palette`; in Dark it paints `var(--bg-2)` (Elevated surfaces, "Menus and raised cards"), opaque, still following that Settings row. Light unchanged |
| theme-card wrap (known gap) | `pages/settings/AppearanceSettings/CssThemeSettings.tsx` | cards are `flex: 1 1 180px; max-width: 200px` (was a fixed 200px that could not shrink): Figma's 200px where there is room, down to 180px before a row wraps |

Figma reference: file `BlpVvZGuc9j9HhxUojIiJI`, Appearance frame `76:3154`, Theme panel `76:3173`
(920×180): Light / Dark / Follow System on **one row**, ~200px cards, left-aligned. Export saved at
`C:\Users\Nick\KelV2Runs\prepared\r22-ui\figma\76-3173-theme-panel.png`. The app nests its Settings nav
inside the card, so the panel is 622px wide against Figma's 920; three 200px cards plus two 14px gaps
(628px) wrapped Follow System onto its own row.

Tests: `tests/unit/kel-theme-color-input.dom.test.tsx` — 4 hex-field tests (typed six-digit, `#rgb` on
Enter, `#rgb` on blur + invalid revert, paste then Reset) and 1 pin for the palette rule. Run against the
**old** field, the three typing/commit tests fail and paste/Reset pass: the regression is caught and the
preserved behaviour is unchanged.

## Archive gate

| check | r22 |
| --- | --- |
| `app.asar` | 1 copy, 300,586,349 B, `f1b68169c67a502be9d779b19591813f7983fdc1ba88b04fb288da58c47f0e47` |
| `Kel.exe` | 1 copy, `61f9ef10b77386d2` |
| `electron.exe` / stray `*unpacked*` | 0 / none |
| DLL set | 15, identical relative paths to r21 |
| frozen engine / donor aioncore | `00846a7e64fdaa95` / `67eb02774bab3855` — unchanged |
| archive marks | r21's (`data-theme="dark"`, `arco-theme="dark"`, `color-mix`, manifest) + `kel-card kel-palette`, `1 1 180px`, `.kel-palette[role=dialog]{background:var(--bg-2` (minified form) |

## Packaged click-through — **[UI]**

Same method as `UI_ACCEPTANCE_R21.md`: `C:\tmp\run-r22-ui.cmd` (fresh isolated profile/store/engine under
`C:\Users\Nick\KelV2Runs\prepared\r22-ui\`, `AIONUI_MULTI_INSTANCE=1`, `--remote-debugging-port=9333`),
Playwright `connectOverCDP`, **all changes by mouse/keyboard input** (paste = `fill`, a single
`insertText`); `page.evaluate` only reads; the store is read read-only. Shots in `r22-ui\shots\`.

| # | interaction | observed | store | verdict |
| --- | --- | --- | --- | --- |
| 1 | fresh launch → Start using Kel → Settings | Dark checked; cards Light/Dark/Follow System at y=230, **198×116 each, one row** in a 622px row (`u2-settings`) | none | PASS |
| 2 | App background: click, Ctrl+A, **type** `#7a1f1f` | `--bg-base` `#7a1f1f` (`u3-typed-6`) | `{"dark":{"--bg-base":"#7a1f1f"}}` | **PASS — D1 fixed** (r21 saved `#77aa11`) |
| 3 | **Reset** | default restored (`u4-reset`) | `{}` | PASS |
| 4 | type `#a33` (no Enter) | unchanged (`u5-typed-3`) | `{}` | PASS — nothing saved mid-word |
| 5 | **Enter** | `#aa3333` (`u6-enter`) | `#aa3333` | PASS |
| 6 | Reset, type `#3a5`, click the "Theme colors" heading (**blur**) | `#33aa55` (`u7-blur`) | `#33aa55` | PASS |
| 7 | Reset; **Ctrl+K**, `theme` — **default** background | palette paints `rgb(27,53,104)` (= `--bg-2`), no image (`p1-palette-default`) | — | **PASS — D2 fixed** |
| 8 | Escape; **paste** `#7a1f1f` | `#7a1f1f`, row Changed (`u8-pasted`) | `#7a1f1f` | PASS |
| 9 | Ctrl+K, `theme` — **custom** background | still `rgb(27,53,104)`, rows readable (`p2-palette-custom`) | — | PASS |
| 10 | **Enter** ("Switch to Light theme") | `light`; open Settings follows live (`p3-light`) | `theme.activeId="light"`, dark override kept | PASS |
| 11 | Ctrl+K, `theme` in Light | palette `rgb(249,250,251)` (unchanged Light fill); cards still one row, 198px (`p4-palette-light`) | — | PASS |
| 12 | **Enter** ("Switch to Dark theme") | `dark`, `#7a1f1f` back (`p5-dark`) | `theme.activeId="dark"` | PASS |
| 13 | **restart** r22, open Settings | `dark`, `#7a1f1f`, row Changed, cards one row 198×116 (`u9-restart`, `u10-restart-settings`) | unchanged | PASS |

Not driven: the native `<input type=color>` OS dialog; narrow-window wrapping of the cards (the rule
still wraps below three 180px cards, but it was not measured here).

## Candidate layout — staged, not promoted

| path | asar | note |
| --- | --- | --- |
| `C:\Users\Nick\KelV2Candidate` | `baaab70ae30b6462` | **r20**, live in the user's session (6 processes, untouched) |
| `C:\Users\Nick\KelV2Candidate.r22` | `f1b68169c67a502b` | **r22, staged**, launcher `Run-Kel-V2-Candidate.cmd` (same content as r21's) |
| `C:\Users\Nick\KelV2Candidate.r21` | `84212ebe805e4bb0` | r21, kept as a rollback |
| `.r19` … `.r14`, `KelV2CanvasCandidate` | unchanged | hash-verified after staging |

Stable install `KelDogfoodCandidate` (`4f23c9ae…c9e41`), stable engine `26544`, both `Kel.lnk` shortcuts,
the user's store (`…\prepared\candidate\desktop-store`, last written 10:08 by r20) and Astra's
`ux/v2-shell` @ `0052075` were not touched.

To promote once Nick closes r20 (no rebuild):

```powershell
Rename-Item C:\Users\Nick\KelV2Candidate     C:\Users\Nick\KelV2Candidate.r20
Rename-Item C:\Users\Nick\KelV2Candidate.r22 C:\Users\Nick\KelV2Candidate
```

## Still open

- O1 (Settings bounces to setup before it is finished, silently) and O2 (faint labels in Light) from
  `UI_ACCEPTANCE_R21.md` — not changed.
- V2-16 timings; Electron profile/log location sharing — unchanged.
