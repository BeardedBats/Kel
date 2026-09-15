# Local UI fonts (licensed — not committed to git)

Kel's shell loads two font families at runtime (see
`packages/desktop/src/renderer/utils/theme/kelFonts.ts` and the rules in
`packages/desktop/src/renderer/styles/arco-override.css`):

| Region | Family | Files expected here | Weights |
|---|---|---|---|
| Headers / display | `Sohne` | `sohne/Sohne-Buch.otf`, `Sohne-Kraftig.otf`, `Sohne-Halbfett.otf`, `Sohne-Dreiviertelfett.otf` | 400 / 500 / 600 / 700 |
| Body text | `SF Pro Text` | `sf-pro-text/SF-Pro-Text-Regular.otf`, `Medium`, `Semibold`, `Bold` | 400 / 500 / 600 / 700 |

**These files are intentionally git-ignored** (`desktop/public/fonts/**/*.otf` etc.):
Söhne is © Klim Type Foundry and SF Pro is © Apple Inc. — they are licensed for the
machine owner's local use, not for redistribution in this public repository.

Copy the fonts into the folders above (same file names) before building to get the
intended look. Without them, the app builds and runs normally and falls back to the
system font stack.

Current local installs are Klim's trial cuts of Söhne: full A–Z/a–z/0–9 coverage,
but only basic punctuation — other punctuation in headers automatically falls back
to SF Pro Text. Dropping in full Söhne OTFs with the same file names upgrades the
headers automatically.
