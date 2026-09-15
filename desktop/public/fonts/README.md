# UI fonts (Söhne / SF Pro Text)

Kel's shell loads two font families at runtime (see
`packages/desktop/src/renderer/utils/theme/kelFonts.ts` and the rules in
`packages/desktop/src/renderer/styles/arco-override.css`):

| Region | Family | Files | Weights |
|---|---|---|---|
| Headers / display | `Sohne` | `sohne/Sohne-Buch.otf`, `Sohne-Kraftig.otf`, `Sohne-Halbfett.otf`, `Sohne-Dreiviertelfett.otf` | 400 / 500 / 600 / 700 |
| Body text | `SF Pro Text` | `sf-pro-text/SF-Pro-Text-Regular.otf`, `Medium`, `Semibold`, `Bold` | 400 / 500 / 600 / 700 |

These files are **committed in this repository** at the owner's decision: it is a
private-use distribution point for the owner's own builds, not a public fork target.
The families remain the property of their foundries — Söhne is © Klim Type Foundry,
SF Pro is © Apple Inc. — and these are the owner's licensed copies; keep them within
this setup.

The app still builds and runs if the files are missing: the loader simply falls back
to the system font stack.

Current Söhne files are Klim's trial cuts: full A–Z/a–z/0–9 coverage, basic
punctuation only — other punctuation in headers automatically falls back to
SF Pro Text. Dropping in full Söhne OTFs with the same file names upgrades the
headers automatically.
