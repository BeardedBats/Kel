# 11 — Design System / Product Quality (Kel V1.5, G7 record)

Status: **G7 donor-sunset pass complete for engine + shell surfaces**; advanced donor surfaces and
the full visual acceptance run at G10, packaged smoke at G11.

## Donor identity sweep (this pass, verified)

| Site | Change | Verification |
|---|---|---|
| `[AionUi]` / `[AionUi:*]` log prefixes | renamed to `[Kel]` across 21 source files | `grep -rn "\[AionUi" src` → zero |
| Tray tooltip | `setToolTip('Kel')` | source + grep |
| Browser notification title | `new Notification('Kel', …)` | source + grep |
| App-name fallback (`appConfig`) | `'Kel'` when config lacks a name | source |
| Provider API `X-Title` header (×2) | `'Kel'` | source |
| Updater user agent + temp filename | `'Kel'` / `Kel-update-…` | source |
| In-app-browser + macOS architecture copy | `Kel` wording | source |

Claims discipline: the Autonomy page copy no longer says enforcement is "not yet implemented";
the claims test (`test_v141_claims.py`) now pins the shipped truth —
"Kel enforces that scope on the worker execution path" and "denied before anything runs" — and
passes 2/2.

## Default-chat purity audit

- `renderer/pages/kel/**` and `renderer/components/kel/**`: **zero** `AionUi` strings (grepped).
- The normal conversation does not expose model, worker, provider, or agent selection; those live
  in the Providers/Diagnostics/Autonomy surfaces reached deliberately.
- One-assistant framing is unchanged: chat is one thread; work details stay in Work context.

## Kept donor infrastructure (deliberate, with reasons)

- App-data path segment `AionUi` and the `AionUi-Dev` userData variant — changing them would strand
  existing user state; kept for compatibility (documented here, not silently).
- Legacy builtin-skill alias `AionUi Image Generation` — recognition of existing installs.
- Updater repo `iOfficeAI/AionUi` and the `static.aionui.com` feed — release infrastructure.
- Copyright headers — license attribution, not product identity.
- **Advanced donor surfaces still carrying donor naming** (settings channels/butler/about/feedback/
  skills/update dialogs): functional donor features, no normal-chat leak; queued for retirement or
  relabeling at G10 with the visual acceptance pass. Recorded rather than blanket-renamed, because
  renaming live donor features without a visual pass would be guesswork.

## Verification plan for the remainder

- G10: visual acceptance over the retained surfaces (light/dark, empty/loading/error states,
  reduced motion, keyboard) with captures; donor-surface retirement decisions applied there.
- G11: packaged smoke proves the shipped copy (tray tooltip, notification title, Autonomy text)
  in the assembled release.
