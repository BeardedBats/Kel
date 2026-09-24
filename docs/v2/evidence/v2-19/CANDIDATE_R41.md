# V2-19 r41 — Dark phone Settings regression

**Source:** `integration/v2` at pushed `ea054bf34b85fca2f691fb0cf736a365e6a03e81`. **Candidate:** `C:\Users\Nick\KelV2Candidate.r41`, staged and not promoted. The full unpacked runtime and `Run-Kel-V2-Candidate-r41.cmd` are present. Its launcher uses separate roots under `C:\Users\Nick\KelV2Runs\prepared\r41`.

| Candidate file | SHA-256 |
| --- | --- |
| `resources\app.asar` | `6C670D7ADE06C5C8A7002114098A0E96FF612B1EA1FD366E521E87CB15203AFF` |
| `Kel.exe` | `2060C36DDDF075F381F6B5BA8AB72C17D59D049536AB98ED0D56B3EBC1B27718` |
| `resources\kel-engine\KelEngine.exe` | `D168F20A9A272A7A4E39707A67BBEBEF77829BC525FBAA96FD99ECEC417D5F47` |
| `Run-Kel-V2-Candidate-r41.cmd` | `5970EA536EE733A09A7CC41C96B3E91E98E338A7402BB2789033D7EF3E308CC0` |

## Checks

- [Full Figma audit](../figma-full-audit/README.md) covers 23 desktop FINAL frames, 28 mobile frames, Foundations `139:2`, Components `136:2`, and Mobile Components `213:3`. Exact parity remains open. r40 is a preserved intermediate candidate; r41 includes its Model and System source fixes.
- `bunx tsc --noEmit -p tsconfig.json` passed. `bunx vitest run tests/unit --reporter=dot` passed 44 files and 295 tests. `bun run package`, `npx electron-builder --config kel-builder.json --x64 --dir`, and `python C:\tmp\verify_asar.py` passed. The archive gate verified manifest, renderer bundles, main build, and renderer index. `git diff --check` passed.
- Fresh packaged root `C:\Users\Nick\KelV2Runs\prepared\r41-figma-final`: [phone Settings check](../figma-full-audit/r41-mobile-settings-check.json) measured 393px document and pane width. Model's first card was 361×306, System's first card 361×204, Pet 361×229, and About cards 361×214 and 361×109. Model uses FINAL text and list rows. System uses compact actions; both backup and restore dialogs opened. Pet shows the disabled Medium value while off. About retains the notices and Licenses rows.
- [Fresh profile route sweep](../figma-full-audit/r41-route-sweep.json) recorded expected setup redirects on eight gated routes, with no horizontal overflow. After clicking the existing **Start using Kel** action in this disposable profile, the [23-route sweep](../figma-full-audit/r41-post-setup-route-sweep.json) had no redirects or horizontal overflow. This did not bypass setup in source.
- The packaged Pet enable action returned off in this isolated build; its enabled size selector remains unverified. The source reconciles a refused enable with the authoritative state. r29 previously recorded two native theme colour-picker adjustments in one popup; r41 did not repeat that check.
- Prior [r39](CANDIDATE_R39.md) checks cover mobile About, Archived, Skills Hub, first-open notices and Escape; desktop About; r33 covers mobile navigation, Add Model sheet, Dark Appearance, and real PNG lightbox actions.

## Ownership and remaining work

During this pass, the r41 root `Kel.exe` was PID 70116, its engine PID 71076, and its aioncore PID 19116. r40 and r41 test trees were stopped only after their executable paths matched their candidate folders. The final process list showed the user's r20 root PID 6356 and engine PID 10848, plus stable engine PID 26544. PIDs can change. Stable data, shortcuts, rollback copies, Astra's clean `ux/v2-shell` branch, and live r20 were untouched. No candidate was renamed or promoted.

Exact UI parity is **not established**. The [audit](../figma-full-audit/README.md) lists remaining Tools, WebUI, compact mobile, desktop component, menu, and populated-data differences. Sample text cannot be compared against empty real data without a matching fixture. Faint Light-mode labels stayed outside this Dark pass. Google sign-in, live services, remote model response, fresh Muse audio, and physical iPhone checks remain pending for access or hardware. The web-host suite requires all Kel instances stopped and was not run while r20 stayed live. `request_review` was unavailable; no independent review occurred.

**Next action:** use a disposable profile with representative populated chat, task, recording, and menu states. Compare each against its paired FINAL frame. Fix measured Tools, WebUI, Pet height, row, copy, and component differences. Preserve r20 and stable; do not rename or promote r41 while r20 runs.
