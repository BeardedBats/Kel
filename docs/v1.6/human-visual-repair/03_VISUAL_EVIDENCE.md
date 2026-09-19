# 03 — VISUAL EVIDENCE (Kel V1.6 human visual repair)

Evidence root: `docs/v1.6/human-visual-repair/evidence/`
Machine-readable results: `kelvis-verify.json` in each capture set.

## Source-level matrix (packaged build, unpacked dir)

Runner: `ux-audit/kelvis-verify.cjs` against `dist/package-r12/win-unpacked` with the isolated seeded profile.
Final run (`evidence/matrix-final/`, probe log `evidence/probe-final3.log`): **all 25 gates PASS — 0 failures, 0 warnings, 0 console errors.**

Screens captured at 1440×960 (files in `evidence/matrix-final/`): chat/home, work, permissions (top/mid/bottom),
model, system (+checked), appearance, tools, pet, webui, about (+checked), archived, conversation, drawer.
Permissions top/mid/bottom also captured at 1366×768, 1440×900, 1920×1080, 1100×800.

Gates (final run):

- boot — engine 1.6.0; profile ready (`#/guid`)
- sidebar mark — canonical logo image loads (asset from app.asar)
- attention badge — fully inside the sider (badge right 250.0 ≤ sider 261.0)
- contrast — 0 elements below 2.5:1 (3 sub-4.5 informational findings; scanner skips disabled styles and gradient scrims)
- donor scan — no donor strings in visible text on any screen
- Permissions scroll ×5 sizes — wheel moves, `End` reaches max, `Home` returns to 0 (e.g. 1366×768: wheel=150 end=150/150 home=0)
- work language — no raw enums; Work → Open the chat → `#/conversation/e59b9c7f` (the referenced conversation)
- drawer — plain language statuses (translated), scrolled content reachable
- model — "custom models" framing present; availability badges present
- system — advanced folders section present; work directory hidden by default
- tools — "Kel Browser" label present (never `aionui-browser`)
- pet — enable refused: reverts to OFF with "The desktop pet is not available in this build, so it stays off."; still OFF after reload
- team — `#/team/office` redirects Home (workforce surface hidden)
- about — canonical logo naturalWidth 1024
- narrow overflow — none at 1100×800

## Installed matrix

Runner: same battery against `C:\Users\Nick\KelVisualFixInstall` with `C:\Users\Nick\KelVisualFixRuns\prepared`
(fresh-seeded review profile). Log: `evidence/probe-installed.log`; JSON: `evidence/installed/kelvis-verify-installed.json`; screenshots: `evidence/installed/`.
**All 25 gates PASS — 0 failures, 0 console errors.** Work → Open the chat → `#/conversation/3bdaab68`.

## Audit battery (installed)

`ux-audit/r12-installed-probe.cjs` against the installed build: **GATE: PASS** — attention true, about logo true,
leaks [], errors 0, no horizontal overflow on `/work`, `/settings/about`, `/`, `/settings/appearance`, `/autonomy`
(`KelVisualFixRuns/captures-installed-r12/r12-installed.json`).

## Permissions scrolling — explicit evidence

`kel-scope` owns scrolling on Kel pages (single scroll owner). Wheel, PageDown/PageUp, End/Home verified at
1366×768, 1440×900, 1440×960, 1920×1080 and 1100×800, in both the source-level and installed runs; screenshots
top/mid/bottom for each size in `evidence/matrix-final/`.

## Console

Zero unexplained renderer errors in all final runs (source + installed; `consoleErrors: []`).
