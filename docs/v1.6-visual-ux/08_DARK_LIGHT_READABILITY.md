# 08 — Dark / Light Readability (measured)

## Method

For every visible text node on each surface, a WCAG 2.x ratio was computed against the nearest ancestor with an
opaque background, in **both** themes, and compared with the AA threshold (4.5:1 for normal text, 3:1 for
large/bold ≥18.66px). Raw output: `evidence-visual-a.json` → `surfaces.*.offenders`;
per-text font-size histograms in the same file.

## Result 1 — the Kel "Desk" surfaces are clean

**Zero contrast offenders** were found in both themes on:

`Work` · `Projects` · `Permissions` · `Team (office, roster)` · `Providers` · `Diagnostics`

That is a real strength and it should be stated before anything else: `styles/kel-tokens.css` is
contrast-disciplined, and its own comments show two prior fixes for exactly this class of bug. The readability
problems are **not** the Kel palette.

## Result 2 — every failure sits in donor surfaces, or in one native control

| Surface | Text | px | Colour on background | Ratio | Need | Theme |
|---|---|---|---|---|---|---|
| Theme gallery (`CssThemeSettings` card label) | `Light` | 13 | `#ffffff` on `#f7f8fa` | **1.06** | 4.5 | light |
| Theme gallery (same element) | `Dark`, `Follow System` | 13 | `#ffffff` on `#f7f8fa` | **1.06** | 4.5 | light |
| System settings (`settings_system`) | `Back up now` (**button label**) | 14 | `#ffffff` on `#e5e7f0` | **1.23** | 4.5 | light |
| System settings | `Restore from this backup` | 14 | `#c9cdd4` on `#f7f8fa` | **1.50** | 4.5 | light |
| Appearance (`ThemeColorsSection`) | `Reset` | 14 | `#94bfff` on `#f2f3f5` | **1.70** | 4.5 | light |
| Appearance (dark capture) | `Reset` | 14 | `rgba(78,89,105,.5)` on `#262626` | **2.13** | 4.5 | dark |
| Transcription sidebar | `Source` (the settings/key entry point) | 12 | `#4e5969` on `#232324` | **2.21** | 4.5 | dark |
| Model settings (`settings_model`) | `Needs setup` chip | 11 | `#86909c` on `#f2f3f5` | **2.92** | 4.5 | light |
| Transcription sidebar | `FOLDERS`, `RECENT TRANSCRIPTIONS`, meta lines | 11–12 | `#86909c` on `#ffffff` | **3.24** | 4.5 | light |
| System settings | `Clear` | 14 | `#f53f3f` on `#ffece8` | **3.25** | 4.5 | light |

Observations that matter more than the individual numbers:

1. **`--color-text-3` / `text-t-tertiary` (`#86909c`) is the single biggest offender** (transcription 3.24:1,
   model chip 2.92:1). It fails on light backgrounds and is used for the labels a user scans most: section
   headers and metadata.
2. **White text on a light/near-white surface appears three times** (theme gallery labels at 1.06:1, the
   `Back up now` primary button at 1.23:1, and `Restore from this backup` at 1.50:1). This is a *token leak*:
   a dark-theme foreground applied on a light background, or a disabled button that kept its white label.
   The backup button is the worst of these because it is an **action**, not decoration.
3. **`kel-tokens.css` already solved this exact class of bug and the donor surfaces never adopted the fix.**
   The file overrides `--bg-5`/`--bg-6` in dark with the comment *"the light value measures 2.13:1 on these
   dark surfaces, and these are the labels a user scans most"*. The same discipline needs to be applied to the
   **light** theme's muted token and to the donor surfaces.
4. The transcription page's `Reset`/`Source` failures are downstream of it not using Kel tokens at all
   (it uses `--color-*` donor variables — see `06_TRANSCRIPTION.md`).

## Result 3 — scale and small-text distribution

Total visible characters per surface, with the font-size actually used (from the live histogram):

| Surface | Total chars | Distribution |
|---|---|---|
| **Permissions** | **3615** | 14px × 2037 · 16px × 1210 · 12px × 255 · 24px × 101 |
| System settings | 2285 | **12px × 1259** · 14px × 582 · 13px × 416 |
| Diagnostics | 1851 | 14px × 1088 · 16px × 386 |
| Providers | 1775 | 16px × 878 · 14px × 449 |
| Settings → Model | 884 | 13px × 434 · 14px × 233 · 11px × 171 |
| Settings → Appearance | 695 | 14px × 386 · 12px × 177 |
| **Work** | **605** | 16px × 438 · 14px × 127 · 24px × 35 (3 card headings) |
| Transcription | 401 | 14px × 248 · 11px × 89 |
| Projects | 383 | 16px × 168 · 14px × 146 |
| Team (office) | 333 | 14px × 162 · 16px × 139 |

Two conclusions:

* **Permissions carries ~6× the text of Work and ~11× Team.** It is the single most text-heavy screen in the
  product, at 12–16px, with ~2000 characters at 14px. "Too technical and too large" is literally measurable.
* **The sparse surfaces are also the ones using the largest type.** Work renders 605 characters, of which 438
  are 16px body and three card headings are 24px, inside 24px-padded cards on a 32px-gutter page. That is the
  "sparse information at enormous visual scale" complaint in numbers: the *scale* is fixed and generous while
  the *content* is nearly empty.

## Result 4 — text smaller than 12px

11px text is present on the transcription sidebar (`89` chars), Settings → Model (`171` chars) and elsewhere
via donor components. At 11px the muted colours above are unreadable regardless of contrast, and on a
1920×1080 laptop with display scaling this is below comfortable.

## Proposed fixes (concrete)

1. **Raise the muted token floor.** In light, `--color-text-3: #86909c` → at least `#6b7280`-class (≥4.5:1 on
   `#ffffff` and on `#f2f3f5`). In dark, keep the existing overrides and extend them to every donor
   `--color-text-3` usage, not just `--bg-5/6`.
2. **Ban white-on-light.** The theme-gallery card label must not be `text-white`; put the theme name **outside**
   the preview swatch (it is a label, not part of the preview) in `text-t-primary`. Never give a disabled or
   secondary button a white label on a light surface.
3. **Fix `Back up now`** to use the Kel primary button treatment (accent fill + `--kel-accent-ink`), and re-tone
   `Restore from this backup` / `Clear` to `--kel-text-2` / a 4.5:1 red.
4. **Floor the type scale at 12px** for any text a user must read; 11px only for purely numeric metadata.
5. **Add a shipped-surface contrast gate.** `ThemeColorsSection` already computes WCAG ratios at runtime for
   user-chosen colours — reuse that maths in CI over the shipped surfaces so this class of regression cannot
   return. The audit probe (`probe-a.cjs`, `probeReadability`) is a working prototype of exactly that check.
6. **Density:** reduce the fixed scale that makes sparse pages feel enormous — see `02_VISUAL_SYSTEM.md`
   (h1 32→20–22px, card heading 24→15–16px, card padding 24→16, page gutter 32→24, row height 44→32–34).
