# V2-19 r33 — Figma full UI audit and bounded packaged regression

**Source:** `integration/v2` at `c6d47ea4253391d15386cb2b2a177f77c9b38790` (pushed). **Candidate:** `C:\Users\Nick\KelV2Candidate.r33` (staged; not promoted). This candidate contains the complete unpacked runtime. Its launcher is `Run-Kel-V2-Candidate-r33.cmd` and uses separate host, store, and engine roots under `C:\Users\Nick\KelV2Runs\prepared\r33`.

| Candidate file | SHA-256 |
| --- | --- |
| `resources\app.asar` | `D3978ED3254C3256F8AFB78E6467DE474EB1F9DA47BECBF657E0D63EAF41BB4E` |
| `Kel.exe` | `418753A8E3F75EFF1E6BD923B80F8EF549B964F9F298BD6A432F5B6F4B83BB8C` |
| `resources\kel-engine\KelEngine.exe` | `D168F20A9A272A7A4E39707A67BBEBEF77829BC525FBAA96FD99ECEC417D5F47` |
| `Run-Kel-V2-Candidate-r33.cmd` | `EE607D10B5DB5A94CD86197EE72D1864C5B36FA83EF0E94EACA148EFB0F34DDF` |

## Scope and checks

- [Full audit](../figma-full-audit/README.md): 23 FINAL desktop frames, 28 mobile frames, Foundations `139:2`, Components `136:2`, and mobile Components `213:3`. The pair map and contact sheets preserve every visual comparison. Exact parity is not claimed.
- Source changes: five-tab phone navigation, Settings and Projects phone indexes, wider chat drawer, narrow theme rows, bottom Add Model sheet, shared image chip and lightbox. The route gate still presents the setup notice. The existing **Start using Kel** action was used only on the disposable r33 profile.
- Checks: `bunx tsc --noEmit -p tsconfig.json` passed; `bunx vitest run tests/unit --reporter=dot` passed **44 files, 295 tests**; `bun run package` and `npx electron-builder --config kel-builder.json --x64 --dir` passed. `python C:\tmp\verify_asar.py` passed manifest, renderer bundles, main, and index equality. `git diff --check` passed.
- Packaged 393px navigation: [nine checks](../figma-full-audit/r33-navigation.json) passed, including Cancel, Escape, Back, Settings and Projects root routes, and no overflow. Add Model measured 393×476; its buttons stayed inside the viewport.
- Packaged Dark Appearance: [393, 800, and 1440px measurements](../figma-full-audit/r33-appearance-layout.json). The 393px theme tiles share one row. Every color row fits a swatch, label, and hex field on one line. At 800px the third theme tile wraps. The 23-route [mobile sweep](../figma-full-audit/r33-mobile-ui-manifest.json) found no document overflow after setup.
- Packaged image: a real 393×852 PNG was pasted through the isolated composer. The [lightbox screenshot](../figma-full-audit/key/r33-lightbox.png) placed the 960px panel at Figma's desktop position. [Click results](../figma-full-audit/r33-lightbox-check.json) show PNG clipboard data, scrim closure, and a Download event named `audit-sample.png`. Escape also closed the lightbox in a separate click check. The unit test pins its dialog controls and Escape/scrim behavior.

## Ownership and remaining work

At the final ownership check, the user's r20 root `Kel.exe` was PID 6356 with engine PID 10848. The stable engine was PID 26544. The isolated r33 root was PID 65908 with engine PID 69844 during checks. r30–r33 test processes were stopped only after executable paths confirmed their candidate folders. The final process list contains only the r20 tree and stable engine. No stable data, shortcut, rollback copy, Astra branch, or r20 process was changed. PIDs can change on later runs.

Remaining Figma gaps are listed screen by screen in the [audit](../figma-full-audit/README.md). Compact phone cards, dropdown and context menu sheets, populated chat/task/transcript states, and exact text for unmatched sample data remain unverified or different. The native color picker has r29 evidence for two adjustments in one popup; this pass did not repeat it. Faint Light-mode labels stayed outside this Dark pass. Google sign-in, live services, fresh Muse audio, remote response, and a physical iPhone remain pending for access or hardware. The web-host suite needs all Kel instances stopped and was not run. `request_review` was unavailable; no independent review occurred.

**Next action:** use an isolated profile with representative populated chat, tasks, recordings, and menu states. Compare those r33 screens against their paired FINAL frames, then repair only confirmed gaps. Keep r20 and the stable app protected; do not promote or rename r33 while r20 runs.
