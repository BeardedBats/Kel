# V2-19 r43 — Dark phone WebUI and Pet audit

**Source:** `integration/v2` at pushed `8bde9aa8f4967c7c2bcd086c4be8a7ccb356c891`. **Candidate:** `C:\Users\Nick\KelV2Candidate.r43`, staged and not promoted. Its full unpacked runtime and `Run-Kel-V2-Candidate-r43.cmd` are present. The launcher uses separate host, store, and engine roots under `C:\Users\Nick\KelV2Runs\prepared\r43`.

| Candidate file | SHA-256 |
| --- | --- |
| `resources\app.asar` | `65F4C64D927A9ACBB38D130E9363B26E6490FC7EF657404F4FBD7573F10FC137` |
| `Kel.exe` | `E05F2D764EB40E3FCA2DFD1ACFFFA511253FDD6D7AC12D850E54B9BCBA4D8DD0` |
| `resources\kel-engine\KelEngine.exe` | `D168F20A9A272A7A4E39707A67BBEBEF77829BC525FBAA96FD99ECEC417D5F47` |
| `Run-Kel-V2-Candidate-r43.cmd` | `1E2CB65300B18E2C38EFE54CE94EA835419B0D800A8C49FF022631372F805C23` |

## Checks

- The [full Figma audit](../figma-full-audit/README.md) covers 23 desktop FINAL frames, 28 mobile frames, Foundations `139:2`, Components `136:2`, and Mobile Components `213:3`. Exact parity remains open. r42 is a preserved intermediate package; r43 corrects its WebUI spacing.
- `bunx tsc --noEmit -p tsconfig.json` passed on r43 source. `bunx vitest run tests/unit --reporter=dot` passed 44 files and 295 tests. `bun run package`, `npx electron-builder --config kel-builder.json --x64 --dir`, and `python C:\tmp\verify_asar.py` passed. The archive gate verified manifest, renderer bundles, main build, and renderer index. `git diff --check` passed.
- Fresh packaged root `C:\Users\Nick\KelV2Runs\prepared\r43-figma-final`: [Dark phone checks](../figma-full-audit/r43-settings-check.json) measured 393px document width. WebUI's first card was x16/y232, 361×166, and Login Info x16/y410, 361×126. The y values include the 79px setup notice. The three-step strip, FINAL copy, compact switches, and login rows appear in the [package capture](../figma-full-audit/key/r43-webui.png). Pet's off-state card was 361×197; System's first card stayed 361×204. No checked route overflowed horizontally.
- [r41](CANDIDATE_R41.md) remains the latest broad regression: 295 tests, mobile Model/System/Pet/About, backup and restore dialogs, and 23 post-setup phone routes without redirects or overflow. [r39](CANDIDATE_R39.md) covers About, Archived, Skills Hub, notices, and desktop About. [r33](CANDIDATE_R33.md) covers the phone frame, Add Model sheet, Dark Appearance, and real PNG lightbox actions. The r29 native theme picker had two adjustments in one popup; r43 did not repeat that check.

## Ownership and remaining work

During checks the r43 root `Kel.exe` was PID 38844, its engine PID 16664, and aioncore PID 71368. The r42 and r43 test trees were stopped only after executable paths matched their candidate folders. The final process list showed the user's r20 root PID 6356 and engine PID 10848, plus stable engine PID 26544. PIDs can change. Stable data, shortcuts, rollback copies, Astra's clean `ux/v2-shell` branch, and live r20 were untouched. No candidate was renamed or promoted.

Exact UI parity is **not established**. The [audit](../figma-full-audit/README.md) lists remaining Tools status rows, other mobile and desktop controls, menus, overlays, and populated chat/task/transcript states. WebUI's enabled and later step states need a live check. The isolated build refused Pet enable, so the enabled size selector remains unverified. Faint Light-mode labels stayed outside this Dark pass. Google sign-in, live services, remote model response, fresh Muse audio, and physical iPhone checks remain pending for access or hardware. The web-host suite requires all Kel instances stopped and was not run while r20 stayed live. `request_review` was unavailable; no independent review occurred.

**Next action:** use a disposable populated profile for chat, task, recording, Tools, and menu states. Compare each against its paired FINAL frame. Fix measured copy, control, and spacing gaps. Keep r20 and stable protected; do not rename or promote r43 while r20 runs.
