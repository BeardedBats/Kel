# Directions — rendered artifacts (Gate 1)

Two materially different design directions for Kel V1.4, rendered from the **same scenario**
(Work Center + the waiting-approval job detail + a components strip) at 1440 and 1280 widths,
with an in-page WCAG / typography / focusability audit.

| Artifact | What it is |
|---|---|
| `direction-a-console.html` | Direction A — “Console”: dark graphite + cyan, table-first, permanent inspector |
| `direction-b-desk.html` | Direction B — “Desk”: light neutral + emerald, cards + focused sheets — **selected** as the V1.4 base |
| `direction-a-console-1440.png` / `-1280.png` | A rendered full page / viewport |
| `direction-b-desk-1440.png` / `-1280.png` | B rendered full page / viewport |
| `directions-audit.json` | Per-file contrast failures, font-size histogram, palette, emoji count, focusable count + sample |

Measured on both files: **0 contrast failures · smallest text 12px · 13 focusable controls · 0 emoji.**

Regenerate:

    PLAYWRIGHT_MODULE=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/node_modules/playwright \
    PLAYWRIGHT_BROWSERS_PATH=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/browsers \
    node packaging/render-directions.cjs docs/v1.4/screenshots/directions \
      docs/v1.4/directions/direction-a-console.html docs/v1.4/directions/direction-b-desk.html

Comparison criteria, decision, and what was absorbed/rejected: `../KEL_V1.4_VISUAL_DIRECTIONS.md`.
